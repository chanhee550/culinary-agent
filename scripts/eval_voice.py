"""음성 파이프라인 정량 평가 (OpenAI Whisper 기준).

라운드트립: 평가문장 → edge-tts 합성 → /transcribe(openai-whisper small) →
claude_route(Haiku) → CER / 의도정확도 / 지연 측정.

실행:  WHISPER_MODEL=small python -m scripts.eval_voice
"""
from __future__ import annotations

import asyncio
import statistics
import time

from dotenv import load_dotenv

load_dotenv()

from services.speech import synthesize_reply, transcribe_audio  # noqa: E402
from services.voice_intent import claude_route  # noqa: E402

# 현재 단계 = 인덱스 2 ("두부를 깍둑썰기 한다")
RECIPE_CTX = {
    "name": "김치찌개",
    "ingredients": ["김치", "돼지고기", "두부", "대파", "고춧가루", "마늘"],
    "instructions": [
        "돼지고기를 한입 크기로 썰어 기름에 볶는다.",
        "김치를 넣고 함께 볶다가 물을 붓는다.",
        "두부를 깍둑썰기 한다.",
        "고춧가루와 다진 마늘을 넣고 끓인다.",
        "마지막에 두부와 대파를 넣고 5분 더 끓인다.",
    ],
    "current_step": 2,
}

# (발화, 기대 액션, 기대 seconds 또는 None)
CASES = [
    ("다음 단계로 넘어가 줘", "next", None),
    ("다음", "next", None),
    ("앞으로 가자", "next", None),
    ("이전 단계로 돌아가", "previous", None),
    ("뒤로 가 줘", "previous", None),
    ("방금 단계 다시 읽어줘", "repeat", None),
    ("한 번 더 말해줘", "repeat", None),
    ("전체 조리법 다 보여줘", "show_all", None),
    ("레시피 전부 펼쳐줘", "show_all", None),
    ("필요한 재료 알려줘", "ingredients", None),
    ("뭐가 필요해?", "ingredients", None),
    ("3분 타이머 맞춰줘", "timer", 180),
    ("타이머 10분 설정해", "timer", 600),
    ("30초 타이머", "timer", 30),
    ("두부는 언제 넣어?", "answer", None),
    ("김치찌개에 마늘 얼마나 들어가?", "answer", None),
    ("지금 단계에서 불 세기는 어떻게 해?", "answer", None),
    ("돼지고기 대신 뭘 쓰면 돼?", "answer", None),
    ("이거 몇 인분이야?", "answer", None),
    ("창문 열어줘", "unknown", None),
]


def cer(ref: str, hyp: str) -> float:
    """공백 제거 후 글자 단위 편집거리 / 원문 길이."""
    r = ref.replace(" ", "")
    h = hyp.replace(" ", "")
    if not r:
        return 0.0
    # Levenshtein
    dp = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        prev, dp[0] = dp[0], i
        for j, hc in enumerate(h, 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (rc != hc))
            prev = cur
    return dp[len(h)] / len(r)


async def main() -> None:
    cers: list[float] = []
    latencies: list[float] = []
    intent_hits = 0
    timer_total = 0
    timer_hits = 0
    rows = []

    # warm-up (모델 로드 + 첫 호출 비용 제외)
    warm = await synthesize_reply("준비")
    transcribe_audio(warm, filename="warm.mp3")

    for idx, (sentence, exp_action, exp_sec) in enumerate(CASES, 1):
        audio = await synthesize_reply(sentence)
        t0 = time.perf_counter()
        text = transcribe_audio(audio, filename=f"case{idx}.mp3")
        routed = claude_route(text, RECIPE_CTX) or {"action": "unknown"}
        dt = time.perf_counter() - t0

        c = cer(sentence, text)
        action = routed.get("action")
        hit = action == exp_action
        cers.append(c)
        latencies.append(dt)
        intent_hits += int(hit)

        sec_ok = ""
        if exp_action == "timer":
            timer_total += 1
            got = int(routed.get("seconds") or 0)
            if got == exp_sec:
                timer_hits += 1
                sec_ok = f" sec={got}OK"
            else:
                sec_ok = f" sec={got}!={exp_sec}"

        rows.append(
            f"{idx:>2} [{ '0' if hit else 'X'}] exp={exp_action:<9} got={str(action):<9}"
            f" CER={c:.3f} {dt:5.2f}s{sec_ok}  | ASR='{text}'"
        )

    print("\n".join(rows))
    n = len(CASES)
    print("\n===== SUMMARY (OpenAI Whisper small, CPU) =====")
    print(f"cases               : {n}")
    print(f"mean CER            : {statistics.mean(cers):.3f}")
    print(f"median CER          : {statistics.median(cers):.3f}")
    print(f"intent accuracy     : {intent_hits/n*100:.1f}% ({intent_hits}/{n})")
    if timer_total:
        print(f"timer sec accuracy  : {timer_hits/timer_total*100:.1f}% ({timer_hits}/{timer_total})")
    print(f"mean latency (warm) : {statistics.mean(latencies):.2f}s")
    print(f"median latency      : {statistics.median(latencies):.2f}s")
    srt = sorted(latencies)
    p95 = srt[min(len(srt) - 1, int(0.95 * len(srt)))]
    print(f"latency P95         : {p95:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
