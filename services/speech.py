"""Voice services for the culinary agent.

ASR: faster-whisper (local, CPU/int8) — no API key needed.
TTS: edge-tts (free Microsoft Edge online voices) — Korean Sun-Hi by default.

환경변수:
    WHISPER_MODEL          (default: small)   tiny/base/small/medium/large-v3
    WHISPER_DEVICE         (default: cpu)
    WHISPER_COMPUTE_TYPE   (default: int8)    int8/int8_float16/float16/float32
    EDGE_TTS_VOICE         (default: ko-KR-SunHiNeural)
"""
import io
import os
import re
import tempfile
from functools import lru_cache

import edge_tts
from faster_whisper import WhisperModel

DEFAULT_WHISPER_MODEL = "small"
DEFAULT_TTS_VOICE = "ko-KR-SunHiNeural"


@lru_cache(maxsize=1)
def _whisper_model() -> WhisperModel:
    name = os.getenv("WHISPER_MODEL", DEFAULT_WHISPER_MODEL)
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    return WhisperModel(name, device=device, compute_type=compute_type)


def transcribe_audio(audio_bytes: bytes, filename: str = "command.webm") -> str:
    """Transcribe a short cooking command recording (Korean)."""
    suffix = os.path.splitext(filename or "")[1] or ".webm"
    # faster-whisper decodes via PyAV; needs a real file path for non-WAV containers.
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        segments, _info = _whisper_model().transcribe(
            tmp_path,
            language="ko",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text for seg in segments).strip()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def parse_cooking_command(text: str) -> dict:
    """Map Korean voice text into deterministic cooking guide actions."""
    normalized = re.sub(r"\s+", "", text.lower())

    timer_match = re.search(r"(\d+)\s*(분|초)", text)
    if "타이머" in normalized and timer_match:
        amount = int(timer_match.group(1))
        unit = timer_match.group(2)
        return {
            "action": "timer",
            "seconds": amount * 60 if unit == "분" else amount,
            "label": f"{amount}{unit} 타이머",
            "reply": f"{amount}{unit} 타이머를 설정하겠습니다.",
        }

    if any(word in normalized for word in ("다음", "넘어가", "넘겨", "앞으로", "다음단계")):
        return {"action": "next", "reply": "다음 단계로 이동하겠습니다."}

    if any(word in normalized for word in ("이전", "전단계", "뒤로", "앞단계")):
        return {"action": "previous", "reply": "이전 단계로 이동하겠습니다."}

    if any(word in normalized for word in ("다시", "반복", "한번더", "다시읽", "읽어줘")):
        return {"action": "repeat", "reply": "현재 단계를 다시 확인하겠습니다."}

    if any(word in normalized for word in ("전체", "전부", "모두", "전체보기")):
        return {"action": "show_all", "reply": "전체 조리법을 펼치겠습니다."}

    if any(word in normalized for word in ("재료", "준비물", "필요한거", "필요한것")):
        return {"action": "ingredients", "reply": "필요한 재료를 알려드리겠습니다."}

    return {
        "action": "unknown",
        "reply": "명령을 이해하지 못했습니다. 다시 말씀해 주세요.",
    }


async def synthesize_reply(text: str) -> bytes:
    """Create short Korean TTS audio using free edge-tts voices."""
    voice = os.getenv("EDGE_TTS_VOICE", DEFAULT_TTS_VOICE)
    communicate = edge_tts.Communicate(text=text, voice=voice)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)
