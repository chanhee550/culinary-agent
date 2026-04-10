import base64
import io
import json
import os
import re

import anthropic
from PIL import Image, ImageEnhance, ImageFilter

MAX_IMAGE_BYTES = 3_500_000  # 3.5MB (base64 인코딩 시 ~4.7MB, API 제한 5MB)


def enhance_image(image_bytes: bytes) -> bytes:
    """이미지 전처리: 밝기/대비/선명도 보정으로 인식률 향상."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")

    # 밝기 보정 (어두운 냉장고 내부 대응)
    brightness = ImageEnhance.Brightness(img)
    img = brightness.enhance(1.15)

    # 대비 강화 (재료 윤곽 부각)
    contrast = ImageEnhance.Contrast(img)
    img = contrast.enhance(1.2)

    # 선명도 강화
    sharpness = ImageEnhance.Sharpness(img)
    img = sharpness.enhance(1.3)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def compress_image(image_bytes: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> tuple[bytes, str]:
    """이미지를 API 제한 이하로 압축합니다."""
    if len(image_bytes) <= max_bytes:
        return image_bytes, "image/jpeg"

    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")

    # 해상도 축소 (긴 변 1600px 이하)
    max_dim = 1600
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # JPEG 품질을 낮춰가며 압축
    for quality in [85, 70, 55, 40]:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= max_bytes:
            return buf.getvalue(), "image/jpeg"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=30)
    return buf.getvalue(), "image/jpeg"


def analyze_fridge_image(image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict]:
    """냉장고/식재료 사진에서 재료를 감지합니다.

    Returns:
        [{"name": "당근", "category": "채소"}, ...]
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # 이미지 전처리 + 압축
    image_bytes = enhance_image(image_bytes)
    image_bytes, media_type = compress_image(image_bytes)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    message = client.messages.create(
        model="claude-opus-4-20250514",
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

## 분석 순서
1. 사진 전체를 훑어보며 큰 물체부터 확인
2. 선반별 / 구역별로 나눠서 세밀하게 확인
3. 포장재 라벨, 색상, 형태를 단서로 활용
4. 가려진 물체도 일부가 보이면 추정

## 인식 대상
- **신선식품**: 채소, 과일, 고기, 생선 (포장 여부 무관)
- **계란**: 계란판, 계란 케이스, 낱개 계란 모두 포함
- **유제품**: 우유, 요거트, 치즈, 버터 등
- **소스/양념**: 간장, 된장, 고추장, 참기름, 케첩, 마요네즈, 소금, 설탕, 식초 등
- **음료**: 물, 주스, 탄산, 차 등
- **가공식품**: 두부, 어묵, 햄, 소시지, 냉동식품 등
- **곡류**: 밥, 면, 빵 등
- **용기 속 음식**: 밀폐용기, 반찬통 안에 보이는 재료도 추정

## 규칙
- 확실하지 않아도 70% 이상 확신이면 포함
- 최대한 많이 찾으세요 (빠뜨리는 것보다 많이 찾는 게 나음)
- 같은 재료 중복 금지
- 한국어 일반 명칭 사용

## 응답 형식
JSON 배열만 반환 (다른 텍스트 없이):
[{"name": "재료명", "category": "카테고리"}]

카테고리: 채소, 과일, 육류, 해산물, 유제품, 계란, 양념/소스, 곡류/면, 음료, 냉동식품, 가공식품, 기타""",
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text.strip()

    match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return []
    return []


def analyze_multiple_images(images: list[tuple[bytes, str]]) -> tuple[list[dict], list[str]]:
    """여러 이미지에서 재료를 감지하고 중복 제거합니다.
    2회 분석 후 합산하여 인식률을 높입니다.

    Args:
        images: [(image_bytes, media_type), ...]

    Returns:
        (중복 제거된 재료 리스트, 에러 리스트)
    """
    all_ingredients = {}
    errors = []

    for idx, (image_bytes, media_type) in enumerate(images):
        # 2회 분석하여 합산
        for attempt in range(2):
            try:
                detected = analyze_fridge_image(image_bytes, media_type)
            except anthropic.APIError as e:
                if attempt == 0:
                    errors.append(f"이미지 {idx+1}: API 오류 - {e}")
                continue
            except json.JSONDecodeError as e:
                if attempt == 0:
                    errors.append(f"이미지 {idx+1}: 응답 파싱 오류 - {e}")
                continue
            except Exception as e:
                if attempt == 0:
                    errors.append(f"이미지 {idx+1}: {e}")
                continue
            for item in detected:
                name = item.get("name", "").strip()
                if name and name not in all_ingredients:
                    all_ingredients[name] = item

    return list(all_ingredients.values()), errors
