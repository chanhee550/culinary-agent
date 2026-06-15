import json
import os
import re
from functools import lru_cache

import anthropic

from db.database import LEGACY_USER_ID
from db.repository import get_profile, get_expiring_ingredients
from services.substitution import load_substitutions, find_all_substitutable

DEFAULT_RECIPE_MODEL = "claude-haiku-4-5-20251001"


@lru_cache(maxsize=1)
def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _model() -> str:
    return os.getenv("RECIPE_MODEL", DEFAULT_RECIPE_MODEL)


# 정중한 문장으로 간주하는 종결 어미. 이 중 하나로 끝나지 않으면 반말/어색한 문장으로 본다.
_POLITE_ENDINGS = ("요", "니다", "십시오", "세요", "께요")
# 분량으로 부적절한 모호 표현.
_VAGUE_AMOUNTS = ("약간", "적당량", "적당히", "조금", "넉넉히", "기호에")


def _normalize_sentence(s: str) -> str:
    """선행 '1.' 번호와 후행 구두점을 제거해 종결 어미만 남긴다."""
    s = re.sub(r"^\s*\d+\s*[.)]\s*", "", s.strip())
    return s.rstrip(" .!~)»」』'\"”’…").strip()


def find_awkward_sentences(recipe: dict) -> list[str]:
    """레시피 출력에서 반말·어색한 문장과 모호한 분량을 찾아 반환한다.

    - description / instructions 의 각 문장이 존댓말로 끝나지 않으면 어색한 문장으로 본다.
    - amounts 값에 '약간'·'적당량' 같은 모호 표현이 있으면 함께 보고한다.
    """
    problems: list[str] = []

    texts: list[str] = [str(recipe.get("description", ""))]
    for step in recipe.get("instructions", []) or []:
        texts.extend(re.split(r"(?<=[.!?])\s+", str(step)))

    for raw in texts:
        sent = _normalize_sentence(raw)
        if len(sent) < 2:
            continue
        if not sent.endswith(_POLITE_ENDINGS):
            problems.append(sent)

    for name, amt in (recipe.get("amounts") or {}).items():
        if any(v in str(amt) for v in _VAGUE_AMOUNTS):
            problems.append(f"{name}: {amt}")

    return problems


def _refine_recipes(client: anthropic.Anthropic, recipes: list[dict]) -> list[dict]:
    """어색한 문장(반말)·모호한 분량이 하나라도 있으면 LLM으로 한 번 교정한다.

    교정 실패(API 오류·파싱 실패·개수 불일치) 시 원본을 그대로 반환한다.
    """
    if not any(find_awkward_sentences(r) for r in recipes):
        return recipes

    try:
        payload = json.dumps(recipes, ensure_ascii=False)
        msg = client.messages.create(
            model=_model(),
            max_tokens=3500,
            messages=[{
                "role": "user",
                "content": (
                    "아래는 레시피 JSON 배열입니다. JSON 구조와 키"
                    "(name, description, ingredients, amounts, missing, instructions, "
                    "difficulty, time)를 그대로 유지하면서 다음만 교정하세요.\n"
                    "1) description과 instructions의 모든 문장을 자연스러운 존댓말"
                    "(\"~하세요\", \"~합니다\", \"~해주세요\")로 고치고, 반말·어색한 표현을 없애세요.\n"
                    "2) amounts의 \"약간\"·\"적당량\" 같은 모호한 분량을 구체적인 수치로 바꾸세요.\n"
                    "3) ingredients·missing·amounts의 재료명(키)은 절대 바꾸지 마세요.\n"
                    "교정된 JSON 배열만 반환하세요(다른 텍스트 없이).\n\n"
                    f"{payload}"
                ),
            }],
        )
        if msg.content and hasattr(msg.content[0], "text"):
            m = re.search(r"\[.*\]", msg.content[0].text, re.DOTALL)
            if m:
                refined = json.loads(m.group())
                if isinstance(refined, list) and len(refined) == len(recipes):
                    return refined
    except (anthropic.APIError, json.JSONDecodeError):
        pass
    return recipes


def recommend_recipes(ingredients: list[str], max_missing: int = 2,
                      cuisine_filter: str = "", taste_filter: str = "",
                      user_id: int = LEGACY_USER_ID) -> list[dict]:
    """보유 재료 기반으로 레시피를 추천합니다. 프로필 정보를 자동 반영합니다."""
    client = _client()

    # 프로필 로드
    profile = get_profile(user_id=user_id)

    # 유통기한 임박 재료 우선 사용
    expiring = get_expiring_ingredients(days=3, user_id=user_id)
    expiring_names = [ing.name for ing in expiring if ing.name in ingredients]

    substitutions = load_substitutions()
    sub_info = "\n".join(
        f"- {name}: {data['ratio']}" for name, data in substitutions.items()
    )

    ingredient_list = ", ".join(ingredients)

    # 프로필 기반 조건 구성
    conditions = []

    # 숙련도
    skill_map = {"초보": "쉽고 간단한", "중급": "적당한 난이도의", "고급": "도전적이고 복잡한"}
    conditions.append(f"사용자의 요리 숙련도는 '{profile.skill_level}'이므로 {skill_map.get(profile.skill_level, '')} 레시피를 추천하세요.")

    # 요리 종류 선호
    cuisines = cuisine_filter or profile.cuisine_preference
    if cuisines:
        conditions.append(f"선호하는 요리 종류: {cuisines}. 이 종류를 우선적으로 추천하되, 다른 종류도 괜찮습니다.")

    # 맛 선호
    tastes = taste_filter or profile.taste_preference
    if tastes:
        conditions.append(f"선호하는 맛: {tastes}. 이 맛을 반영한 레시피를 추천하세요.")

    # 알레르기
    if profile.allergies:
        conditions.append(f"⚠️ 알레르기 재료: {profile.allergies}. 이 재료들은 절대 포함하지 마세요!")

    # 유통기한 임박
    if expiring_names:
        conditions.append(f"유통기한 임박 재료: {', '.join(expiring_names)}. 이 재료를 우선적으로 활용하는 레시피를 추천하세요.")

    conditions_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(conditions))

    message = client.messages.create(
        model=_model(),
        max_tokens=3500,  # Haiku 4.5 5개 레시피 + 상세 instructions가 1700~2000 토큰. 마진 확보.
        messages=[
            {
                "role": "user",
                "content": f"""당신은 요리 전문가입니다. 아래 재료를 기반으로 레시피를 추천해주세요.

## 보유 재료
{ingredient_list}

## 대체 가능한 재료 참고
{sub_info}

## 사용자 조건
{conditions_text}

## 규칙
1. 보유 재료를 최대한 활용하는 레시피 3~5개를 추천해주세요
2. 부족한 재료는 최대 {max_missing}개까지만 허용합니다
3. 위의 대체 재료 정보를 참고하여, 대체 가능한 재료가 있다면 부족 재료에서 제외해주세요
4. 난이도와 전체 조리시간을 정확히 표기하세요 (예: "약 25분")
5. 각 조리 단계는 구체적이고 따라하기 쉽게 작성하되, **시간이 필요한 동작에는 정확한 시간을 반드시 명시하세요** (예: "끓는 물에 8분간 삶아주세요", "중불에서 10분간 졸여주세요", "30분간 재워주세요")
6. **기본 양념은 missing에 포함하지 마세요** — 사용자 가정에 항상 있다고 가정:
   소금, 설탕, 후추, 간장, 식용유, 물, 통깨, 밥
   (단, 보유 재료 목록에 명시된 다른 양념은 그대로 사용 가능)
7. **🚫 환각 금지 — 가장 중요**:
   - instructions(조리법)에 등장하는 모든 재료는 반드시 다음 중 하나여야 합니다:
     (a) ingredients 배열에 명시된 재료
     (b) 위 6번의 기본 양념 8가지 (소금/설탕/후추/간장/식용유/물/통깨/밥)
   - ingredients에 없는 재료를 "다시마 육수", "양념장", "비법 소스" 같은
     이름으로 슬쩍 instructions에 끼워넣지 마세요
   - 전통 레시피가 추가 재료를 요구하면 → missing에 명시하거나, 그 재료
     없이 만들 수 있는 변형 레시피로 작성하세요
   - ❌ BAD: ingredients=["갈비"], instructions=["1. 다시마와 양파로 육수를 내고..."]
     (다시마, 양파가 ingredients에도 missing에도 없음)
   - ✅ GOOD: ingredients=["갈비"], missing=["다시마","양파"], instructions=["1. 다시마와 양파로 육수를 내고..."]
     (사용된 재료가 모두 ingredients+missing에 있음)
   - ✅ GOOD: ingredients=["갈비"], instructions=["1. 갈비를 물에 30분 담가 핏물을 빼고..."]
     (기본 양념 "물"만 사용, ingredients 재료만 사용)
   - 작성 후 self-check: instructions의 모든 재료가 ingredients/missing/기본양념에 있는지 확인하세요
8. **모든 문장은 존댓말로 작성하세요** — description과 instructions의 모든 문장을 정중한 존댓말("~하세요", "~합니다", "~해주세요")로 끝맺으세요. 반말("~한다", "~해라", "~하자", "~썬다")을 절대 쓰지 마세요.
9. **각 재료의 분량을 정확히 표기하세요** — amounts 객체에 ingredients와 missing의 모든 재료에 대해 구체적인 개수·양을 적으세요. "약간"·"적당량" 대신 가능한 한 구체적 수치(개, g, ml, 큰술, 작은술, 컵, 모, 줌 등)를 쓰세요. amounts의 **키는 ingredients/missing의 재료명과 정확히 동일한 문자열**이어야 하며, 분량은 값에만 넣으세요.

## 응답 형식
다음 JSON 배열로만 반환하세요 (다른 텍스트 없이):
[
  {{
    "name": "요리명",
    "description": "요리에 대한 한 줄 설명을 존댓말로 작성합니다",
    "ingredients": ["재료명만 (분량 제외)"],
    "amounts": {{"양파": "1개", "간장": "2큰술", "돼지고기": "200g"}},
    "missing": ["보유하지 않은 재료명만"],
    "instructions": ["1. 끓는 물에 파스타를 넣고 8분간 삶아주세요.", "2. 중불에서 10분간 볶아주세요."],
    "difficulty": "쉬움|보통|어려움",
    "time": "약 25분"
  }}
]""",
            }
        ],
    )

    if not message.content or not hasattr(message.content[0], "text"):
        return []

    response_text = message.content[0].text.strip()

    match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if not match:
        return []
    try:
        recipes = json.loads(match.group())
    except json.JSONDecodeError:
        return []

    # 출력 검증: 어색한 문장(반말)·모호한 분량이 있으면 한 번 교정
    recipes = _refine_recipes(client, recipes)

    # 대체 재료 정보 보강
    for recipe in recipes:
        missing = recipe.get("missing", [])
        recipe["substitutions"] = find_all_substitutable(missing, ingredients)

    return recipes
