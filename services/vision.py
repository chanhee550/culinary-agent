"""Vision: 냉장고 사진 → 재료 인식 (정확도 최우선 모드).

- 적응형 이미지 전처리 (밝기/대비를 사진 통계 기반으로 결정)
- 이미지 압축 (해상도 2048, 품질 하한 75 — 라벨/디테일 최대 보존)
- Level 2 프롬프트: 확정 재료(confirmed)와 통/병 등 불확실 항목(unknowns) 분리 반환
- Extended thinking: 모델이 실제로 생각한 후 답변 (한국 식재료 디스앰비큐에이션 정확도↑)
- 2-pass 검증: confirmed 재료를 동일 사진에 대해 재검증, 의심 시 unknowns로 강등
- 다중 이미지 병렬 분석 (ThreadPoolExecutor)
- 클라이언트 인스턴스 캐싱 (TLS 핸드셰이크 절약)
- 모델 환경변수 토글 (VISION_MODEL, 기본 Opus 4.7 — vision 정확도 최우선)
"""
import base64
import io
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import anthropic
from PIL import Image, ImageEnhance, ImageFilter, ImageStat

DEFAULT_MODEL = "claude-opus-4-7"
MAX_IMAGE_BYTES = 3_500_000  # base64 인코딩 시 ~4.7MB, API 제한 5MB 이하
MAX_DIMENSION = 2048
PARALLEL_WORKERS = 5
THINKING_BUDGET = 2048  # extended thinking 토큰 예산 (vision 디스앰비큐에이션용)
MIN_RECOMMENDED_EDGE = 800

PROMPT = """당신은 한국 식재료 인식 전문가입니다. 이 사진을 주의 깊게 분석하여 보이는 모든 식재료를 분류해주세요.

## 분석 순서
1. 사진 전체를 훑어보며 큰 물체부터 확인
2. 선반별/구역별로 나눠 세밀히 확인
3. 색상·크기·텍스처·포장재 라벨을 단서로 활용
4. 가려진 물체도 일부가 보이면 추정

## ⚠️ 한국 식재료 디스앰비큐에이션 (가장 자주 헷갈림)

이런 혼동을 절대 하지 마세요. 확신이 없으면 unknowns로 보내세요.

| 흔한 오인식 | 실제 한국 식재료 |
|-------------|------------------|
| 노란 타원형 → 바나나로 단정 ❌ | **참외**일 수 있음 (세로 줄무늬 + 통통한 형태) |
| 작은 빨간 구형 → 계란/체리로 단정 ❌ | **방울토마토** (계란은 흰/베이지색이며 더 큼) |
| 작은 흰색 알맹이 → 양파로 단정 ❌ | **마늘** (껍질 결이 다름) |
| 흰색 길쭉한 채소 → 무로 단정 ❌ | 대파 흰 부분일 수도 (무는 둥글둥글 두껍음) |
| 작은 초록 잎 → 시금치로 단정 ❌ | **깻잎** (잎이 더 넓고 톱니 가장자리) |
| 빨간 양념 채소 → 김치로 단정 ❌ | 김치/깍두기/총각김치/오이무침 등 다양 → unknowns |
| 흰색 직육면체 → 두부로 단정 가능 ✅ | 단, 포장에 라벨 확인 시 더 확실 |
| 노란 액체 작은 병 → 식초/간장으로 단정 ❌ | 라벨 확인 → 안 보이면 unknowns |

## 두 그룹으로 분리해 반환

### confirmed — **85% 이상 확신**되는 재료
- 신선식품(채소·과일·고기·생선): 포장 여부 무관
- 계란: 계란판/케이스/낱개 포함
- 유제품: 우유팩, 요거트 컵, 치즈 포장 등
- 가공식품: 두부, 어묵, 햄, 라면, 통조림 등
- 음료: 라벨이 명확히 보이는 병/팩/캔
- 곡류: 봉지 라벨이 명확히 보이는 쌀/면/빵

### unknowns — 통/병/용기에 담겨 단정할 수 없는 항목
- description: 외관 단서 (예: "투명 락앤락 통, 빨간 양념 음식", "녹색 라벨 작은 유리병")
- guess: 가능성 높은 추측 1~2개 (확신 없으면 빈 문자열)
- location: 사진 내 위치 (예: "왼쪽 위 칸", "도어 포켓")

## 인식 규칙
- **85% 이상 확신**이면 confirmed에 포함, 그 미만은 unknowns
- 한국 식재료 디스앰비큐에이션 표를 항상 우선 적용
- 색상만으로 단정하지 말고 크기·모양·텍스처도 종합적으로 판단
- 낯선 통·반찬 등은 항상 unknowns로 (사용자가 직접 라벨링)
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
    """적응형 보정. 사진 통계(평균 밝기·표준편차)로 보정 강도를 결정."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    stat = ImageStat.Stat(img.convert("L"))
    mean = stat.mean[0]      # 0-255 평균 밝기
    stddev = stat.stddev[0]  # 명암 분산 = 대비 척도

    # 어두울수록 더 밝게, 이미 밝으면 그대로
    if mean < 100:
        brightness_factor = 1.30
    elif mean < 140:
        brightness_factor = 1.15
    else:
        brightness_factor = 1.00

    # 평탄(저대비)할수록 대비 강화
    if stddev < 40:
        contrast_factor = 1.30
    elif stddev < 60:
        contrast_factor = 1.15
    else:
        contrast_factor = 1.05

    img = ImageEnhance.Brightness(img).enhance(brightness_factor)
    img = ImageEnhance.Contrast(img).enhance(contrast_factor)
    img = ImageEnhance.Sharpness(img).enhance(1.30)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def compress_image(image_bytes: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> bytes:
    """API 제한 이하로 압축. 해상도 축소 후 단계적 품질 감소 (하한 75)."""
    if len(image_bytes) <= max_bytes:
        return image_bytes

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if max(img.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

    for q in (90, 85, 80, 75):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q)
        if buf.tell() <= max_bytes or q == 75:
            return buf.getvalue()
    return buf.getvalue()


def _image_quality_warnings(image_bytes: bytes) -> list[str]:
    """분석은 계속하되, 정확도를 떨어뜨릴 수 있는 촬영 문제를 사용자에게 알려준다."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return ["이미지를 열 수 없어 품질을 확인하지 못했습니다."]

    warnings: list[str] = []
    width, height = img.size
    if min(width, height) < MIN_RECOMMENDED_EDGE:
        warnings.append(
            f"해상도가 낮습니다 ({width}x{height}). 라벨과 작은 재료는 더 가까이 찍으면 좋아요."
        )

    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    contrast = stat.stddev[0]
    if mean < 55:
        warnings.append("사진이 어둡습니다. 냉장고 조명을 켜거나 한 장 더 밝게 찍어주세요.")
    if contrast < 18:
        warnings.append("대비가 낮아 포장지와 투명 용기가 흐릿하게 보일 수 있습니다.")

    # Pillow만으로 계산하는 가벼운 선명도 지표. 낮으면 흔들림/초점 문제 가능성이 큼.
    edge_stat = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
    if edge_stat.stddev[0] < 12:
        warnings.append("초점이 흐릴 수 있습니다. 손을 고정하고 선반별 근접 사진을 추가해보세요.")

    return warnings


def _extract_json_object(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def _extract_text(message) -> str:
    """Extended thinking이 활성화되면 content에 thinking 블록이 먼저 오므로 text 블록만 골라낸다."""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            return block.text.strip()
    return ""


def _verify_enabled() -> bool:
    return os.getenv("VISION_VERIFY", "true").lower() not in ("false", "0", "no")


def _thinking_enabled() -> bool:
    return os.getenv("VISION_THINKING", "true").lower() not in ("false", "0", "no")


def _create_message(image_data: str, prompt_text: str, max_tokens: int) -> object:
    """Vision API 호출 — extended thinking 토글 가능."""
    kwargs = {
        "model": _model(),
        "max_tokens": max_tokens,
        "messages": [
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
                    {"type": "text", "text": prompt_text},
                ],
            }
        ],
    }
    if _thinking_enabled():
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": THINKING_BUDGET}
    return _client().messages.create(**kwargs)


VERIFY_PROMPT_TEMPLATE = """이전 분석에서 이 사진에서 다음 재료들을 'confirmed'(85% 이상 확신)로 식별했습니다:

{confirmed_list}

각 항목을 사진과 다시 면밀히 비교해 검증하세요.

## 검증 기준
- 정말로 그 재료가 사진에 보이는가? 색상만 비슷한 다른 물체는 아닌가?
- 한국 식재료 디스앰비큐에이션 다시 확인:
  * 노란 타원형 → 바나나가 아니라 참외일 가능성
  * 작은 빨간 구형 → 계란/체리가 아니라 방울토마토일 가능성
  * 작은 흰 알맹이 → 양파가 아니라 마늘일 가능성
  * 흰 길쭉이 → 무가 아니라 대파 흰 부분일 가능성
  * 작은 초록 잎 → 시금치가 아니라 깻잎일 가능성
  * 빨간 양념 채소 → 김치 단정 금지 (깍두기/총각김치/오이무침일 수 있음)
- 통/병/포장에 가려져 라벨로만 식별한 경우, 라벨이 실제로 명확히 보이는지 재확인
- 조금이라도 의심스러우면 즉시 unknowns로 강등 (재현율보다 정밀도 우선)

## 응답 형식
JSON으로만 반환 (다른 텍스트 없이):
{{
  "verified": [
    {{"name": "재료명", "category": "카테고리", "quantity": "수량"}}
  ],
  "rejected": [
    {{"name": "원본명", "reason": "왜 의심스러운지 한 줄"}}
  ]
}}
"""


def _verify_confirmed(image_data: str, confirmed: list[dict]) -> tuple[list[dict], list[dict]]:
    """2-pass 검증: confirmed가 정말 사진에 있는지 같은 모델이 다시 본다.

    Returns:
        (verified_confirmed, rejected_as_unknowns)
        rejected는 unknowns 형식으로 변환되어 반환된다.
    """
    if not confirmed:
        return [], []

    confirmed_list_text = "\n".join(
        f"- {item.get('name', '?')} (카테고리: {item.get('category', '?')})"
        for item in confirmed
    )
    prompt_text = VERIFY_PROMPT_TEMPLATE.format(confirmed_list=confirmed_list_text)

    try:
        message = _create_message(image_data, prompt_text, max_tokens=3072)
    except anthropic.APIError:
        # 검증 실패 시 원본 confirmed 유지 (fail-safe)
        return confirmed, []

    parsed = _extract_json_object(_extract_text(message))
    if not parsed:
        return confirmed, []

    verified = parsed.get("verified", []) or []
    rejected_raw = parsed.get("rejected", []) or []
    rejected_as_unknowns = [
        {
            "description": f"{r.get('name', '')} — 검증에서 의심됨: {r.get('reason', '')}",
            "guess": r.get("name", ""),
            "location": "",
        }
        for r in rejected_raw
        if r.get("name")
    ]
    return verified, rejected_as_unknowns


def analyze_fridge_image(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """단일 이미지 분석. 전처리 → 압축 → 1차 식별 → 2차 검증.

    Returns:
        {"confirmed": [{"name", "category", "quantity"}],
         "unknowns": [{"description", "guess", "location"}]}
    """
    image_bytes = enhance_image(image_bytes)
    image_bytes = compress_image(image_bytes)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    # 1차: 식별. extended thinking 사용 시 max_tokens는 thinking 예산 + 출력 마진을 포함해야 함.
    message = _create_message(image_data, PROMPT, max_tokens=THINKING_BUDGET + 2048)
    parsed = _extract_json_object(_extract_text(message))
    if not parsed:
        return {"confirmed": [], "unknowns": []}

    confirmed = parsed.get("confirmed", []) or []
    unknowns = parsed.get("unknowns", []) or []

    # 2차: confirmed 검증. 같은 사진을 다시 보고 의심스러운 항목을 unknowns로 강등.
    if _verify_enabled() and confirmed:
        verified, rejected = _verify_confirmed(image_data, confirmed)
        confirmed = verified
        unknowns = list(unknowns) + rejected

    return {"confirmed": confirmed, "unknowns": unknowns}


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
    quality_warnings: list[str] = []

    for idx, (image_bytes, _media_type) in enumerate(images):
        for warning in _image_quality_warnings(image_bytes):
            quality_warnings.append(f"사진 {idx + 1}: {warning}")

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
        "quality_warnings": quality_warnings,
    }
