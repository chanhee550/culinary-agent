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
4. 난이도와 조리시간도 알려주세요
5. 각 조리 단계는 구체적이고 따라하기 쉽게 작성하세요
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

## 응답 형식
다음 JSON 배열로만 반환하세요 (다른 텍스트 없이):
[
  {{
    "name": "요리명",
    "description": "한줄 설명",
    "ingredients": ["필요한 모든 재료"],
    "missing": ["보유하지 않은 재료만"],
    "instructions": ["1. 첫번째 단계", "2. 두번째 단계"],
    "difficulty": "쉬움|보통|어려움",
    "time": "예상 조리시간"
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

    # 대체 재료 정보 보강
    for recipe in recipes:
        missing = recipe.get("missing", [])
        recipe["substitutions"] = find_all_substitutable(missing, ingredients)

    return recipes
