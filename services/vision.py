import base64
import json
import os
import re

import anthropic


def analyze_fridge_image(image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict]:
    """냉장고/식재료 사진에서 재료를 감지합니다.

    Returns:
        [{"name": "당근", "category": "채소"}, ...]
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": """당신은 식재료 인식 전문가입니다. 이 사진을 주의 깊게 분석하여 보이는 모든 식재료를 찾아주세요.

## 인식 가이드라인
1. **직접 보이는 재료**: 포장 없이 보이는 채소, 과일, 고기 등
2. **포장된 재료**: 패키지, 봉지, 병에 담긴 것도 라벨이나 형태로 추정하여 포함
3. **용기 속 재료**: 반찬통, 밀폐용기 안에 보이는 재료도 추정하여 포함
4. **부분적으로 보이는 재료**: 일부만 보여도 추정 가능하면 포함
5. **기본 양념류**: 냉장고에 흔히 있는 기본 양념(간장, 된장, 고추장, 참기름, 소금, 설탕, 식초 등)이 보이면 반드시 포함
6. **음료/유제품**: 우유, 주스, 물, 음료수도 포함
7. **계란**: 계란판이나 계란이 보이면 반드시 포함

## 주의사항
- 확실하지 않아도 합리적으로 추정 가능하면 포함하세요
- 최대한 많은 재료를 찾아주세요
- 같은 재료가 여러 개 있어도 한 번만 포함
- 한국어 일반 명칭 사용 (예: "청경채" 대신 "배추", "scallion" 대신 "대파")

## 응답 형식
다음 JSON 배열로만 반환하세요 (다른 텍스트 없이):
[{"name": "재료명", "category": "카테고리"}]

카테고리: 채소, 과일, 육류, 해산물, 유제품, 계란, 양념/소스, 곡류/면, 음료, 냉동식품, 기타""",
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # JSON 배열 추출 (LLM이 부가 텍스트를 포함할 수 있으므로 정규식으로 추출)
    match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return []
    return []


def analyze_multiple_images(images: list[tuple[bytes, str]]) -> list[dict]:
    """여러 이미지에서 재료를 감지하고 중복 제거합니다.

    Args:
        images: [(image_bytes, media_type), ...]

    Returns:
        중복 제거된 재료 리스트
    """
    all_ingredients = {}

    errors = []

    for idx, (image_bytes, media_type) in enumerate(images):
        try:
            detected = analyze_fridge_image(image_bytes, media_type)
        except anthropic.APIError as e:
            errors.append(f"이미지 {idx+1}: API 오류 - {e}")
            continue
        except json.JSONDecodeError as e:
            errors.append(f"이미지 {idx+1}: 응답 파싱 오류 - {e}")
            continue
        except Exception as e:
            errors.append(f"이미지 {idx+1}: {e}")
            continue
        for item in detected:
            name = item.get("name", "").strip()
            if name and name not in all_ingredients:
                all_ingredients[name] = item

    return list(all_ingredients.values()), errors
