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
        max_tokens=1024,
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
                        "text": """이 사진에서 보이는 식재료를 모두 찾아주세요.
다음 JSON 형식으로만 반환하세요 (다른 텍스트 없이):
[{"name": "재료명", "category": "카테고리"}]

카테고리는 다음 중 하나를 사용하세요:
채소, 과일, 육류, 해산물, 유제품, 양념/소스, 곡류/면, 음료, 냉동식품, 기타

중복 없이, 한국어로 작성해주세요.""",
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # JSON 배열 추출 (LLM이 부가 텍스트를 포함할 수 있으므로 정규식으로 추출)
    match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return []


def analyze_multiple_images(images: list[tuple[bytes, str]]) -> list[dict]:
    """여러 이미지에서 재료를 감지하고 중복 제거합니다.

    Args:
        images: [(image_bytes, media_type), ...]

    Returns:
        중복 제거된 재료 리스트
    """
    all_ingredients = {}

    for image_bytes, media_type in images:
        try:
            detected = analyze_fridge_image(image_bytes, media_type)
        except (json.JSONDecodeError, anthropic.APIError):
            continue
        for item in detected:
            name = item["name"].strip()
            if name not in all_ingredients:
                all_ingredients[name] = item

    return list(all_ingredients.values())
