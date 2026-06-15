"""Claude-based intent router for cooking voice commands.

regex 기반 parse_cooking_command를 확장합니다.
- 동일한 액션 어휘를 유지하되, "answer" 액션을 추가해 자유 질문에 답합니다.
- 레시피 컨텍스트(제목/재료/단계/현재 단계)가 함께 주어지면 그것을 사용합니다.
- 호출 실패/스키마 위반 시 caller에서 parse_cooking_command 로 fallback 합니다.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import anthropic

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """너는 한국어 음성으로 요리 단계를 안내하는 보조 모델이다.
사용자의 발화를 듣고 다음 액션 중 하나를 선택해 **JSON만** 응답한다.

actions:
- "next"        : 다음 단계로 진행
- "previous"    : 이전 단계로 이동
- "repeat"      : 현재 단계를 다시 안내
- "show_all"    : 전체 조리법을 펼침
- "ingredients" : 필요한 재료를 안내
- "timer"       : 타이머 설정 (seconds: int, label: str 필드 포함)
- "answer"      : 위 액션에 해당하지 않는 자유 질문 — reply 안에 한국어 답변을 직접 작성
- "unknown"     : 명령이 무엇인지 알 수 없음

응답 스키마:
{
  "action": "<위 8개 중 하나>",
  "reply":  "<한국어 한~두 문장. TTS로 자연스럽게 읽히게.>",
  "seconds": <int, action=timer 일 때만>,
  "label":   "<str, action=timer 일 때만>"
}

규칙:
- 응답은 **순수 JSON 객체만**. 코드 펜스/주석/설명 금지.
- 레시피 컨텍스트가 주어지면, "answer" 응답은 반드시 그 컨텍스트만을 근거로 한다.
  컨텍스트로 알 수 없는 내용은 추측하지 말고 "레시피에 적혀있지 않습니다" 라고 답한다.
- reply 는 두 문장 이하, 자연스러운 한국어 구어체.
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _coerce(raw: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "action" not in data:
        return None
    valid = {"next", "previous", "repeat", "show_all", "ingredients", "timer", "answer", "unknown"}
    if data["action"] not in valid:
        return None
    data.setdefault("reply", "")
    if data["action"] == "timer":
        try:
            data["seconds"] = int(data.get("seconds") or 0)
        except (TypeError, ValueError):
            return None
        if data["seconds"] <= 0:
            return None
        data.setdefault("label", f"{data['seconds']}초 타이머")
    return data


def claude_route(text: str, recipe_context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return the routed action dict, or None on failure."""
    text = (text or "").strip()
    if not text:
        return None

    user_msg = f'사용자 발화: "{text}"'
    if recipe_context:
        instructions = recipe_context.get("instructions", []) or []
        idx = int(recipe_context.get("current_step", 0) or 0)
        current_text = instructions[idx] if 0 <= idx < len(instructions) else ""
        compact = {
            "name": recipe_context.get("name"),
            "ingredients": recipe_context.get("ingredients", []),
            "instructions": instructions,
            "current_step_number": idx + 1,   # 1-based for clarity
            "total_steps": len(instructions),
            "current_step_text": current_text,
        }
        user_msg += "\n\n현재 레시피(JSON):\n" + json.dumps(compact, ensure_ascii=False)
    user_msg += "\n\n위 스키마에 맞는 JSON 객체만 출력."

    model = os.getenv("INTENT_MODEL", os.getenv("RECIPE_MODEL", DEFAULT_MODEL))
    try:
        resp = _client().messages.create(
            model=model,
            max_tokens=400,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
    except anthropic.APIError:
        return None

    raw = "".join(getattr(b, "text", "") for b in resp.content).strip()
    return _coerce(raw)
