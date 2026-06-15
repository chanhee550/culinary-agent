"""음성 조리 가이드 — ASR + LLM 의도분석 + TTS.

엔드포인트는 레시피 컨텍스트(요청 본문)만으로 동작하는 무상태 헬퍼라 사용자 DB를
건드리지 않는다. 따라서 인증을 요구하지 않는다(모바일 tts()도 토큰 없이 호출).

체인:
    오디오 → transcribe_audio(faster-whisper) → claude_route(Haiku, 실패 시
    regex parse_cooking_command 로 fallback) → 액션 → synthesize_reply(edge-tts)
"""
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from services.speech import parse_cooking_command, synthesize_reply, transcribe_audio
from services.voice_intent import claude_route

router = APIRouter(tags=["voice"])


# ---------- Schemas ----------

class VoiceCommandOut(BaseModel):
    text: str
    command: dict


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200)


# ---------- Endpoints ----------

@router.post("/voice/command", response_model=VoiceCommandOut)
async def voice_command(
    file: UploadFile = File(...),
    recipe_context: str | None = Form(default=None),
):
    """Short voice command → transcription → cooking guide action.

    Claude 라우터를 먼저 시도하고, 실패 시 regex parser 로 fallback 합니다.
    recipe_context (JSON 문자열) 가 주어지면 자유 질문에 답할 수 있습니다.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="오디오 파일이 필요합니다.")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="오디오 파일은 25MB 이하여야 합니다.")

    filename = file.filename or "command.webm"
    text = transcribe_audio(content, filename=filename)

    ctx: dict | None = None
    if recipe_context:
        try:
            parsed = json.loads(recipe_context)
            if isinstance(parsed, dict):
                ctx = parsed
        except json.JSONDecodeError:
            ctx = None

    command = claude_route(text, ctx) or parse_cooking_command(text)
    return VoiceCommandOut(text=text, command=command)


@router.post("/voice/tts")
async def voice_tts(req: TTSRequest):
    """Short confirmation text → mp3 audio via edge-tts."""
    audio = await synthesize_reply(req.text)
    if not audio:
        raise HTTPException(status_code=502, detail="TTS 음성 생성에 실패했습니다.")
    return Response(content=audio, media_type="audio/mpeg")
