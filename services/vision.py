import base64
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import anthropic

MODEL = "claude-haiku-4-5-20251001"

PROMPT = """이 사진에서 식재료를 분석해주세요. 두 그룹으로 분리해서 반환합니다.

1) confirmed: 포장·모양·라벨로 명확히 식별 가능한 재료 (예: 계란, 우유팩, 사과)
2) unknowns: 통/병/용기에 담겨있어 내용물을 단정할 수 없는 항목
   - description: 외관 단서를 한국어로 (예: "투명 락앤락 통, 빨간 양념 음식", "녹색 라벨의 작은 유리병, 갈색 액체")
   - guess: 가능성 높은 추측 1~2개 (확신 없으면 빈 문자열)
   - location: 사진 내 대략 위치 (예: "왼쪽 위 칸", "도어 포켓")

JSON으로만 반환 (다른 텍스트 없이):
{
  "confirmed": [
    {"name": "재료명", "category": "카테고리", "quantity": "선택적 수량"}
  ],
  "unknowns": [
    {"description": "...", "guess": "...", "location": "..."}
  ]
}

카테고리: 채소, 과일, 육류, 해산물, 유제품, 양념/소스, 곡류/면, 음료, 냉동식품, 기타
중복 없이, 한국어로."""


@lru_cache(maxsize=1)
def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _extract_json_object(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def analyze_fridge_image(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """단일 이미지 분석.

    Returns:
        {"confirmed": [{"name", "category", "quantity"}], "unknowns": [{"description", "guess", "location"}]}
    """
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    message = _client().messages.create(
        model=MODEL,
        max_tokens=1536,
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
        "confirmed": parsed.get("confirmed", []),
        "unknowns": parsed.get("unknowns", []),
    }


def analyze_multiple_images(images: list[tuple[bytes, str]]) -> dict:
    """여러 이미지 병렬 분석 후 병합.

    Args:
        images: [(image_bytes, media_type), ...]

    Returns:
        confirmed는 name 기준 중복 제거, unknowns는 image_index를 부여하여 모두 보존.
    """
    def _safe(args):
        try:
            return analyze_fridge_image(*args)
        except Exception:
            return {"confirmed": [], "unknowns": []}

    with ThreadPoolExecutor(max_workers=min(len(images), 5)) as executor:
        results = list(executor.map(_safe, images))

    merged_confirmed: dict[str, dict] = {}
    merged_unknowns: list[dict] = []

    for img_idx, result in enumerate(results):
        for item in result.get("confirmed", []):
            name = item.get("name", "").strip()
            if name and name not in merged_confirmed:
                merged_confirmed[name] = item
        for unk in result.get("unknowns", []):
            unk = dict(unk)
            unk["image_index"] = img_idx
            merged_unknowns.append(unk)

    # unknowns에 안정적 id 부여
    for i, unk in enumerate(merged_unknowns):
        unk["id"] = i

    return {
        "confirmed": list(merged_confirmed.values()),
        "unknowns": merged_unknowns,
    }
