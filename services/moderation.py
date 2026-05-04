"""Hugging Face Inference API 기반 컨텐츠 모더레이션.

텍스트(한국어): smilegate-ai/kor_unsmile — 한국어 혐오/공격성 분류
이미지(NSFW):  Falconsai/nsfw_image_detection — NSFW 분류

Fail-open 정책: HF API 키 미설정/타임아웃/네트워크 에러 시 차단하지 않음.
모더레이션 서비스 다운으로 게시판 자체가 마비되는 것을 방지. 운영 로그로 추적.

환경변수:
    HUGGINGFACE_API_KEY      — HF inference 토큰 (없으면 모더레이션 skip)
    HF_TEXT_MODEL            — 기본 smilegate-ai/kor_unsmile
    HF_IMAGE_MODEL           — 기본 Falconsai/nsfw_image_detection
    MODERATION_THRESHOLD     — 차단 임계값 (기본 0.7)
    MODERATION_TIMEOUT_SEC   — HF 호출 타임아웃 (기본 5)
"""
import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# 한국어 unsmile 라벨 중 차단 대상 — clean/individual은 안전 라벨로 제외
_KOR_BLOCK_LABELS = {"여성/가족", "남성", "성소수자", "인종/국적", "연령", "지역", "종교", "기타 혐오", "악플/욕설"}


@dataclass(frozen=True)
class ModerationResult:
    blocked: bool
    reason: str  # 사용자에게 보여줄 한국어 사유 (블록일 때만 의미)
    label: str = ""  # 디버그용 — HF가 반환한 최고점 라벨
    score: float = 0.0


_OK = ModerationResult(blocked=False, reason="")


def _api_key() -> str | None:
    return os.getenv("HUGGINGFACE_API_KEY") or None


def _threshold() -> float:
    try:
        return float(os.getenv("MODERATION_THRESHOLD", "0.7"))
    except ValueError:
        return 0.7


def _timeout() -> float:
    try:
        return float(os.getenv("MODERATION_TIMEOUT_SEC", "5"))
    except ValueError:
        return 5.0


def _text_model() -> str:
    return os.getenv("HF_TEXT_MODEL", "smilegate-ai/kor_unsmile")


def _image_model() -> str:
    return os.getenv("HF_IMAGE_MODEL", "Falconsai/nsfw_image_detection")


def _post_to_hf(model: str, payload: bytes | dict, content_type: str) -> list[dict] | None:
    """HF Inference API 호출. 실패 시 None (fail-open)."""
    api_key = _api_key()
    if not api_key:
        logger.warning("HUGGINGFACE_API_KEY 미설정 — 모더레이션 skip")
        return None

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": content_type,
    }
    try:
        with httpx.Client(timeout=_timeout()) as client:
            if isinstance(payload, dict):
                resp = client.post(url, headers=headers, json=payload)
            else:
                resp = client.post(url, headers=headers, content=payload)
        resp.raise_for_status()
        data = resp.json()
        # HF는 모델 로딩 중일 때 {"error": "..."} 반환 — fail-open
        if isinstance(data, dict) and "error" in data:
            logger.warning("HF model %s loading/error: %s", model, data.get("error"))
            return None
        # 분류 결과는 [[{label, score}, ...]] 또는 [{label, score}, ...] 형태
        if isinstance(data, list) and data and isinstance(data[0], list):
            return data[0]
        if isinstance(data, list):
            return data
        return None
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.warning("HF moderation call failed (%s): %s", model, e)
        return None


def check_text(text: str) -> ModerationResult:
    """텍스트(한국어)에 혐오/욕설 감지. 비어있으면 통과."""
    text = (text or "").strip()
    if not text:
        return _OK
    results = _post_to_hf(_text_model(), {"inputs": text}, "application/json")
    if not results:
        return _OK  # fail-open

    # smilegate-ai/kor_unsmile은 라벨별 score 반환. 차단 라벨 중 최고점 검사.
    top_block = max(
        (r for r in results if r.get("label") in _KOR_BLOCK_LABELS),
        key=lambda r: r.get("score", 0.0),
        default=None,
    )
    if top_block and top_block.get("score", 0.0) >= _threshold():
        return ModerationResult(
            blocked=True,
            reason=f"부적절한 표현이 감지되었어요 ({top_block['label']})",
            label=top_block["label"],
            score=top_block["score"],
        )
    return _OK


def check_image(image_bytes: bytes, content_type: str = "image/jpeg") -> ModerationResult:
    """이미지에서 NSFW 감지."""
    if not image_bytes:
        return _OK
    results = _post_to_hf(_image_model(), image_bytes, content_type)
    if not results:
        return _OK

    nsfw = next((r for r in results if r.get("label", "").lower() == "nsfw"), None)
    if nsfw and nsfw.get("score", 0.0) >= _threshold():
        return ModerationResult(
            blocked=True,
            reason="부적절한 이미지가 감지되었어요",
            label="nsfw",
            score=nsfw["score"],
        )
    return _OK


def check_images(images: list[tuple[bytes, str]]) -> ModerationResult:
    """이미지 여러 장 검사 — 1장이라도 차단되면 즉시 차단 결과 반환."""
    for idx, (data, ctype) in enumerate(images):
        r = check_image(data, ctype)
        if r.blocked:
            return ModerationResult(
                blocked=True,
                reason=f"{idx + 1}번째 이미지가 부적절합니다 ({r.reason})",
                label=r.label,
                score=r.score,
            )
    return _OK
