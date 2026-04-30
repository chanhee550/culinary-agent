"""Vision: 냉장고 사진 → 재료 인식.

통합 (master + v0-mobile):
- 이미지 전처리 (밝기/대비/선명도 보정) — 어두운 냉장고 내부 인식률 향상
- 이미지 압축 (5MB API 제한 대응)
- Level 2 프롬프트: 확정 재료(confirmed)와 통/병 등 불확실 항목(unknowns) 분리 반환
- 다중 이미지 병렬 분석 (ThreadPoolExecutor)
- 클라이언트 인스턴스 캐싱 (TLS 핸드셰이크 절약)
- 모델 환경변수 토글 (VISION_MODEL, 기본 Haiku 4.5)
"""
import base64
import io
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import anthropic
from PIL import Image, ImageEnhance

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_IMAGE_BYTES = 3_500_000  # base64 인코딩 시 ~4.7MB, API 제한 5MB 이하
MAX_DIMENSION = 1600
PARALLEL_WORKERS = 5

PROMPT = """당신은 식재료 인식 전문가입니다. 이 사진을 주의 깊게 분석하여 보이는 모든 식재료를 분류해주세요.

## 분석 순서
1. 사진 전체를 훑어보며 큰 물체부터 확인
2. 선반별/구역별로 나눠 세밀히 확인
3. 포장재 라벨, 색상, 형태를 단서로 활용
4. 가려진 물체도 일부가 보이면 추정

## 두 그룹으로 분리해 반환

### confirmed — 명확히 식별 가능한 재료
- 신선식품(채소·과일·고기·생선): 포장 여부 무관
- 계란: 계란판/케이스/낱개 포함
- 유제품: 우유팩, 요거트 컵, 치즈 포장 등
- 가공식품: 두부, 어묵, 햄, 라면, 통조림 등
- 음료: 라벨 보이는 병/팩/캔
- 곡류: 봉지 라벨이 보이는 쌀/면/빵

### unknowns — 통/병/용기에 담겨 단정할 수 없는 항목
- description: 외관 단서 (예: "투명 락앤락 통, 빨간 양념 음식", "녹색 라벨 작은 유리병")
- guess: 가능성 높은 추측 1~2개 (확신 없으면 빈 문자열)
- location: 사진 내 위치 (예: "왼쪽 위 칸", "도어 포켓")

## 인식 규칙
- 70% 이상 확신이면 confirmed에 포함
- 낯선 통·반찬 등 단정 어려우면 unknowns로 보냄 (사용자가 직접 라벨링)
- 같은 재료 중복 금지
- 한국어 일반 명칭 사용

## 응답 형식
JSON으로만 반환 (다른 텍스트 없이):
{
  "confirmed": [
    {"name": "재료명", "category": "카테고리", "quantity": "선택적 수량"}
  ],
  "unknowns": [
    {"description": "...", "guess": "...", "location": "..."}
  ]
}

카테고리: 채소, 과일, 육류, 해산물, 유제품, 계란, 양념/소스, 곡류/면, 음료, 냉동식품, 가공식품, 기타
"""


@lru_cache(maxsize=1)
def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _model() -> str:
    return os.getenv("VISION_MODEL", DEFAULT_MODEL)


def enhance_image(image_bytes: bytes) -> bytes:
    """밝기/대비/선명도 보정으로 인식률 향상."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = ImageEnhance.Brightness(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.20)
    img = ImageEnhance.Sharpness(img).enhance(1.30)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def compress_image(image_bytes: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    """API 제한 이하로 압축. 해상도 축소 후 단계적 품질 감소."""
    if len(image_bytes) <= max_bytes:
        return image_bytes

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if max(img.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

    for q in (85, 70, 55, 40, 30):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q)
        if buf.tell() <= max_bytes or q == 30:
            return buf.getvalue()
    return buf.getvalue()


def _extract_json_object(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def analyze_fridge_image(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """단일 이미지 분석. 전처리 → 압축 → API 호출 → JSON 파싱.

    Returns:
        {"confirmed": [{"name", "category", "quantity"}],
         "unknowns": [{"description", "guess", "location"}]}
    """
    image_bytes = enhance_image(image_bytes)
    image_bytes = compress_image(image_bytes)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    message = _client().messages.create(
        model=_model(),
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )

    response_text = message.content[0].text.strip()
    parsed = _extract_json_object(response_text)
    if not parsed:
        return {"confirmed": [], "unknowns": []}

    return {
        "confirmed": parsed.get("confirmed", []) or [],
        "unknowns": parsed.get("unknowns", []) or [],
    }


def analyze_multiple_images(images: list[tuple[bytes, str]]) -> dict:
    """다중 이미지 병렬 분석 + 결과 병합.

    Args:
        images: [(image_bytes, media_type), ...]

    Returns:
        {
          "confirmed": [...]   # name 기준 중복 제거
          "unknowns":  [...]   # 모두 보존, 안정적 id + image_index 부여
          "errors":    [...]   # 이미지별 실패 메시지
        }
    """
    errors: list[str] = []

    def _safe(args: tuple[int, tuple[bytes, str]]) -> dict:
        idx, payload = args
        try:
            return analyze_fridge_image(*payload)
        except anthropic.APIError as e:
            errors.append(f"이미지 {idx + 1}: API 오류 - {e}")
        except Exception as e:
            errors.append(f"이미지 {idx + 1}: {e}")
        return {"confirmed": [], "unknowns": []}

    workers = min(len(images), PARALLEL_WORKERS) or 1
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_safe, list(enumerate(images))))

    merged_confirmed: dict[str, dict] = {}
    merged_unknowns: list[dict] = []

    for img_idx, result in enumerate(results):
        for item in result.get("confirmed", []):
            name = (item.get("name") or "").strip()
            if name and name not in merged_confirmed:
                merged_confirmed[name] = item
        for unk in result.get("unknowns", []):
            unk = dict(unk)
            unk["image_index"] = img_idx
            merged_unknowns.append(unk)

    for i, unk in enumerate(merged_unknowns):
        unk["id"] = i

    return {
        "confirmed": list(merged_confirmed.values()),
        "unknowns": merged_unknowns,
        "errors": errors,
    }
