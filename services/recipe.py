import json
import os
import re

import anthropic

from services.substitution import load_substitutions, find_all_substitutable


def recommend_recipes(ingredients: list[str], max_missing: int = 2) -> list[dict]:
    """보유 재료 기반으로 레시피를 추천합니다.

    Returns:
        [
            {
                "name": "김치찌개",
                "description": "간단 설명",
                "ingredients": ["김치", "돼지고기", "두부", "대파"],
                "missing": ["돼지고기"],
                "instructions": ["1. ...", "2. ..."],
                "difficulty": "쉬움",
                "time": "30분"
            },
            ...
        ]
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    substitutions = load_substitutions()
    sub_info = "\n".join(
        f"- {name}: {data['ratio']}" for name, data in substitutions.items()
    )

    ingredient_list = ", ".join(ingredients)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""당신은 한식 전문 요리사입니다. 아래 재료를 기반으로 레시피를 추천해주세요.

## 보유 재료
{ingredient_list}

## 대체 가능한 재료 참고
{sub_info}

## 규칙
1. 보유 재료를 최대한 활용하는 레시피 3~5개를 추천해주세요
2. 부족한 재료는 최대 {max_missing}개까지만 허용합니다
3. 위의 대체 재료 정보를 참고하여, 대체 가능한 재료가 있다면 부족 재료에서 제외해주세요
4. 한식 위주로 추천하되, 재료에 맞으면 다른 요리도 괜찮습니다
5. 난이도와 조리시간도 알려주세요

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

    # JSON 배열 추출
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
