"use client";

import { useEffect, useRef, useState } from "react";
import {
  Loader2, ChefHat, Clock, Star, Bookmark, ShoppingCart, Check,
  Mic, Square, ChevronLeft, ChevronRight, ListOrdered, RotateCcw,
  Volume2, VolumeX,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Recipe, RecipeContext } from "@/lib/types";

export default function RecipesPage() {
  const [ingredients, setIngredients] = useState<string[]>([]);
  const [maxMissing, setMaxMissing] = useState(2);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openIdx, setOpenIdx] = useState(0);

  useEffect(() => {
    api.listIngredients()
      .then((items) => setIngredients(items.map((i) => i.name)))
      .catch((e) => setError(String(e)));
  }, []);

  async function recommend() {
    setLoading(true);
    setError(null);
    setRecipes([]);
    try {
      const r = await api.recipes(maxMissing);
      setRecipes(r);
      setOpenIdx(0);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="px-5 pt-10 pb-6">
      <h1 className="mb-1 text-2xl font-bold">레시피 추천</h1>
      <p className="mb-5 text-sm text-gray-500">
        보유 재료 기반으로 AI가 한식 레시피를 추천합니다.
      </p>

      {ingredients.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          등록된 재료가 없습니다. 먼저 재료를 추가해주세요.
        </div>
      ) : (
        <>
          <section className="mb-5 rounded-2xl border border-gray-200 bg-white p-4">
            <h2 className="mb-2 text-sm font-semibold">보유 재료 ({ingredients.length}개)</h2>
            <div className="flex flex-wrap gap-1.5">
              {ingredients.map((n) => (
                <span
                  key={n}
                  className="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-700"
                >
                  {n}
                </span>
              ))}
            </div>
          </section>

          <section className="mb-5 rounded-2xl border border-gray-200 bg-white p-4">
            <label className="block text-sm font-semibold">
              허용할 부족 재료 수: {maxMissing}개
            </label>
            <input
              type="range" min={0} max={5} value={maxMissing}
              onChange={(e) => setMaxMissing(Number(e.target.value))}
              className="mt-3 w-full accent-brand"
            />
          </section>

          <button
            disabled={loading}
            onClick={recommend}
            className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-brand font-semibold text-white disabled:opacity-40"
          >
            {loading ? (
              <><Loader2 className="animate-spin" size={20} /> AI가 레시피를 찾고 있어요...</>
            ) : (
              <><ChefHat size={20} /> 레시피 추천받기</>
            )}
          </button>
        </>
      )}

      {error && (
        <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {recipes.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-3 text-sm font-semibold">추천 레시피 ({recipes.length})</h2>
          <ul className="space-y-3">
            {recipes.map((r, i) => (
              <RecipeCard
                key={i} recipe={r}
                open={openIdx === i}
                onToggle={() => setOpenIdx(openIdx === i ? -1 : i)}
              />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function RecipeCard({
  recipe, open, onToggle,
}: { recipe: Recipe; open: boolean; onToggle: () => void }) {
  const missing = new Set(recipe.missing || []);
  const subs = recipe.substitutions || {};
  const amounts = recipe.amounts || {};
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [shoppingAdded, setShoppingAdded] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [showAllSteps, setShowAllSteps] = useState(false);
  const [recording, setRecording] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [voiceText, setVoiceText] = useState("");
  const [voiceHint, setVoiceHint] = useState("");
  const [narrationOn, setNarrationOn] = useState(false);
  const lastNarratedStepRef = useRef<number>(-1);
  const [timerRemaining, setTimerRemaining] = useState(0);
  const timerEndRef = useRef<number | null>(null);
  const timerIntervalRef = useRef<number | null>(null);
  const timerTimeoutRef = useRef<number | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const audioUrlRef = useRef<string | null>(null);
  // 부족 재료 항목별 처리 상태: ingredient name → 'owned' | 'shopping' | undefined
  const [perItem, setPerItem] = useState<Record<string, "owned" | "shopping">>({});
  const totalSteps = recipe.instructions.length;

  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) window.clearInterval(timerIntervalRef.current);
      if (timerTimeoutRef.current) window.clearTimeout(timerTimeoutRef.current);
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (!narrationOn) return;
    if (currentStep === lastNarratedStepRef.current) return;
    const step = recipe.instructions[currentStep];
    if (!step) return;
    lastNarratedStepRef.current = currentStep;
    speakReply(`단계 ${currentStep + 1}. ${step}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep, narrationOn]);

  async function markOwned(name: string) {
    if (perItem[name]) return;
    setActionError(null);
    try {
      await api.addIngredient({ name, category: "기타" });
      setPerItem((p) => ({ ...p, [name]: "owned" }));
    } catch (err) {
      setActionError(String(err));
    }
  }

  async function markShopping(name: string) {
    if (perItem[name]) return;
    setActionError(null);
    try {
      await api.shoppingFromMissing([name]);
      setPerItem((p) => ({ ...p, [name]: "shopping" }));
    } catch (err) {
      setActionError(String(err));
    }
  }

  const stars =
    recipe.difficulty === "쉬움" ? 3 :
    recipe.difficulty === "어려움" ? 1 : 2;

  async function handleSave(e: React.MouseEvent) {
    e.stopPropagation();
    if (saved || saving) return;
    setSaving(true);
    setActionError(null);
    try {
      await api.saveRecipe(recipe);
      setSaved(true);
    } catch (err) {
      setActionError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleAddMissing(e: React.MouseEvent) {
    e.stopPropagation();
    if (shoppingAdded || !recipe.missing?.length) return;
    setActionError(null);
    try {
      await api.shoppingFromMissing(recipe.missing);
      setShoppingAdded(true);
    } catch (err) {
      setActionError(String(err));
    }
  }

  async function speakReply(text: string) {
    if (!text) return;
    try {
      const audio = await api.tts(text);
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
      const url = URL.createObjectURL(audio);
      audioUrlRef.current = url;
      await new Audio(url).play();
    } catch (err) {
      setActionError(String(err));
    }
  }

  function clearCookingTimer() {
    if (timerIntervalRef.current) window.clearInterval(timerIntervalRef.current);
    if (timerTimeoutRef.current) window.clearTimeout(timerTimeoutRef.current);
    timerIntervalRef.current = null;
    timerTimeoutRef.current = null;
    timerEndRef.current = null;
    setTimerRemaining(0);
  }

  function startCookingTimer(seconds: number, label?: string) {
    clearCookingTimer();
    const duration = Math.max(1, seconds);
    timerEndRef.current = Date.now() + duration * 1000;
    setTimerRemaining(duration);

    timerIntervalRef.current = window.setInterval(() => {
      if (!timerEndRef.current) return;
      const remaining = Math.max(0, Math.ceil((timerEndRef.current - Date.now()) / 1000));
      setTimerRemaining(remaining);
      if (remaining <= 0 && timerIntervalRef.current) {
        window.clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    }, 250);

    timerTimeoutRef.current = window.setTimeout(() => {
      clearCookingTimer();
      setVoiceHint(`${label || "타이머"}가 끝났습니다.`);
      speakReply("타이머가 끝났습니다.");
    }, duration * 1000);
  }

  function formatTimer(seconds: number) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function applyVoiceAction(action: string, label?: string, seconds?: number, reply?: string) {
    if (action === "next") {
      setCurrentStep((s) => Math.min(s + 1, Math.max(totalSteps - 1, 0)));
      setVoiceHint(reply || "다음 단계로 이동하겠습니다.");
      return;
    }
    if (action === "previous") {
      setCurrentStep((s) => Math.max(s - 1, 0));
      setVoiceHint(reply || "이전 단계로 이동하겠습니다.");
      return;
    }
    if (action === "repeat") {
      const step = recipe.instructions[currentStep];
      if (step) speakReply(`단계 ${currentStep + 1}. ${step}`);
      setVoiceHint(reply || "현재 단계를 다시 안내합니다.");
      return;
    }
    if (action === "show_all") {
      setShowAllSteps(true);
      setVoiceHint(reply || "전체 조리법을 펼치겠습니다.");
      return;
    }
    if (action === "ingredients") {
      setVoiceHint(reply || "필요한 재료를 알려드리겠습니다.");
      return;
    }
    if (action === "timer" && seconds) {
      startCookingTimer(seconds, label);
      setVoiceHint(reply || `${label || "타이머"}를 설정하겠습니다.`);
      return;
    }
    if (action === "answer") {
      setVoiceHint(reply || "");
      return;
    }
    setVoiceHint(reply || "명령을 이해하지 못했습니다. 다시 말씀해 주세요.");
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setActionError("이 브라우저는 음성 녹음을 지원하지 않습니다.");
      return;
    }

    setActionError(null);
    setVoiceHint("");
    setVoiceText("");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    chunksRef.current = [];

    const mimeType = MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "";
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = async () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
      if (!blob.size) return;

      setVoiceBusy(true);
      try {
        const context: RecipeContext = {
          name: recipe.name,
          ingredients: recipe.ingredients,
          instructions: recipe.instructions,
          current_step: currentStep,
        };
        const result = await api.voiceCommand(blob, context);
        setVoiceText(result.text);
        applyVoiceAction(
          result.command.action,
          result.command.label,
          result.command.seconds,
          result.command.reply,
        );
        await speakReply(result.command.reply || "명령을 확인했습니다.");
      } catch (err) {
        setActionError(String(err));
      } finally {
        setVoiceBusy(false);
      }
    };

    mediaRecorderRef.current = recorder;
    recorder.start();
    setRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setRecording(false);
  }

  function toggleRecording(e: React.MouseEvent) {
    e.stopPropagation();
    if (recording) stopRecording();
    else startRecording().catch((err) => setActionError(String(err)));
  }

  return (
    <li className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
      <button
        onClick={onToggle}
        className="flex w-full items-start gap-3 p-4 text-left active:bg-gray-50"
      >
        <div className="flex-1">
          <p className="font-semibold">{recipe.name}</p>
          <p className="mt-0.5 text-xs text-gray-500">{recipe.description}</p>
          <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              {Array.from({ length: 3 }).map((_, k) => (
                <Star
                  key={k} size={12}
                  className={k < stars ? "fill-amber-400 text-amber-400" : "text-gray-300"}
                />
              ))}
            </span>
            <span>{recipe.difficulty}</span>
            <span className="flex items-center gap-1">
              <Clock size={12} /> {recipe.time}
            </span>
          </div>
        </div>
        <span className={`text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}>▾</span>
      </button>

      {/* 액션 버튼들 */}
      <div className="flex gap-2 border-t border-gray-100 px-4 py-2.5">
        <button
          onClick={handleSave}
          disabled={saved || saving}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition-colors ${
            saved
              ? "bg-brand-soft text-brand-dark"
              : "border border-gray-200 text-gray-700 active:bg-gray-50"
          } disabled:opacity-50`}
        >
          {saved ? <Check size={14} /> : <Bookmark size={14} />}
          {saving ? "저장 중..." : saved ? "저장됨" : "레시피 저장"}
        </button>
        {recipe.missing?.length > 0 && (
          <button
            onClick={handleAddMissing}
            disabled={shoppingAdded}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition-colors ${
              shoppingAdded
                ? "bg-amber-50 text-amber-700"
                : "border border-gray-200 text-gray-700 active:bg-gray-50"
            } disabled:opacity-50`}
          >
            {shoppingAdded ? <Check size={14} /> : <ShoppingCart size={14} />}
            {shoppingAdded ? "장보기 추가됨" : `부족 ${recipe.missing.length}개 → 장보기`}
          </button>
        )}
      </div>
      {actionError && (
        <p className="border-t border-gray-100 px-4 py-2 text-xs text-red-600">{actionError}</p>
      )}

      {open && (
        <div className="space-y-4 border-t border-gray-100 p-4">
          <div>
            <h3 className="mb-2 text-xs font-semibold text-gray-700">재료</h3>
            <ul className="space-y-1.5 text-sm">
              {recipe.ingredients.map((ing) => {
                const isMissing = missing.has(ing);
                const hasSub = isMissing && subs[ing];
                const handled = perItem[ing];
                return (
                  <li key={ing} className="flex items-center gap-2 flex-wrap">
                    <span>{hasSub ? "🟡" : isMissing ? (handled ? "✓" : "🔴") : "🟢"}</span>
                    <span className={isMissing && !handled ? "text-gray-500" : ""}>
                      {hasSub ? <s>{ing}</s> : ing}
                      {amounts[ing] && (
                        <span className="ml-1 text-xs text-gray-400">· {amounts[ing]}</span>
                      )}
                      {hasSub && " → 대체 가능"}
                      {isMissing && !hasSub && !handled && " (부족)"}
                      {handled === "owned" && (
                        <span className="ml-1 text-xs text-brand-dark">→ 보유 재료에 추가됨</span>
                      )}
                      {handled === "shopping" && (
                        <span className="ml-1 text-xs text-amber-700">→ 장보기에 추가됨</span>
                      )}
                    </span>
                    {/* 부족 + 대체불가 + 미처리 → 두 액션 버튼 */}
                    {isMissing && !hasSub && !handled && (
                      <span className="ml-auto flex gap-1.5">
                        <button
                          onClick={() => markOwned(ing)}
                          className="rounded-md border border-brand bg-brand-soft px-2 py-1 text-[11px] font-medium text-brand-dark active:bg-brand active:text-white"
                          title={`${ing}를 보유 재료에 추가`}
                        >
                          ✓ 있음
                        </button>
                        <button
                          onClick={() => markShopping(ing)}
                          className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700 active:bg-amber-500 active:text-white"
                          title={`${ing}를 장보기에 추가`}
                        >
                          🛒 장보기
                        </button>
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>

          {Object.keys(subs).length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold text-gray-700">대체 재료</h3>
              <ul className="space-y-1 text-xs text-gray-700">
                {Object.entries(subs).map(([k, v]) => (
                  <li
                    key={k}
                    dangerouslySetInnerHTML={{
                      __html: v.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"),
                    }}
                  />
                ))}
              </ul>
            </div>
          )}

          <div>
            <h3 className="mb-2 text-xs font-semibold text-gray-700">조리법</h3>
            {totalSteps > 0 && (
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <div className="mb-3 flex items-center justify-between text-xs text-gray-500">
                  <span>단계 {currentStep + 1} / {totalSteps}</span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => {
                        const next = !narrationOn;
                        setNarrationOn(next);
                        if (next) {
                          lastNarratedStepRef.current = -1; // force narration of current step
                          // trigger effect by no-op state nudge
                          setCurrentStep((s) => s);
                          speakReply(`단계 ${currentStep + 1}. ${recipe.instructions[currentStep]}`);
                          lastNarratedStepRef.current = currentStep;
                        }
                      }}
                      className={`flex items-center gap-1 rounded-md px-2 py-1 font-medium active:bg-gray-100 ${
                        narrationOn ? "text-brand-dark" : "text-gray-700"
                      }`}
                      title={narrationOn ? "낭독 끄기" : "단계마다 자동 낭독"}
                    >
                      {narrationOn ? <Volume2 size={14} /> : <VolumeX size={14} />}
                      {narrationOn ? "낭독 ON" : "낭독"}
                    </button>
                    <button
                      onClick={() => setShowAllSteps((v) => !v)}
                      className="flex items-center gap-1 rounded-md px-2 py-1 font-medium text-gray-700 active:bg-gray-100"
                    >
                      <ListOrdered size={14} />
                      {showAllSteps ? "접기" : "전체"}
                    </button>
                  </div>
                </div>

                <p className="min-h-20 text-sm leading-relaxed text-gray-800">
                  {recipe.instructions[currentStep]}
                </p>

                <div className="mt-4 grid grid-cols-3 gap-2">
                  <button
                    onClick={() => setCurrentStep((s) => Math.max(s - 1, 0))}
                    disabled={currentStep === 0}
                    className="flex h-11 items-center justify-center gap-1 rounded-lg border border-gray-200 bg-white text-sm font-semibold disabled:opacity-40"
                  >
                    <ChevronLeft size={16} /> 이전
                  </button>
                  <button
                    onClick={() => {
                      const step = recipe.instructions[currentStep];
                      if (step) speakReply(`단계 ${currentStep + 1}. ${step}`);
                      setVoiceHint("현재 단계를 다시 안내합니다.");
                    }}
                    className="flex h-11 items-center justify-center gap-1 rounded-lg border border-gray-200 bg-white text-sm font-semibold"
                  >
                    <RotateCcw size={15} /> 다시
                  </button>
                  <button
                    onClick={() => setCurrentStep((s) => Math.min(s + 1, totalSteps - 1))}
                    disabled={currentStep >= totalSteps - 1}
                    className="flex h-11 items-center justify-center gap-1 rounded-lg border border-gray-200 bg-white text-sm font-semibold disabled:opacity-40"
                  >
                    다음 <ChevronRight size={16} />
                  </button>
                </div>

                <button
                  onClick={toggleRecording}
                  disabled={voiceBusy}
                  className={`mt-3 flex h-12 w-full items-center justify-center gap-2 rounded-xl font-semibold ${
                    recording
                      ? "bg-red-500 text-white"
                      : "bg-gray-900 text-white"
                  } disabled:opacity-50`}
                >
                  {voiceBusy ? (
                    <><Loader2 className="animate-spin" size={18} /> 음성 분석 중...</>
                  ) : recording ? (
                    <><Square size={18} /> 말 끝났어요</>
                  ) : (
                    <><Mic size={18} /> 음성 명령</>
                  )}
                </button>

                {(voiceText || voiceHint) && (
                  <div className="mt-3 rounded-lg bg-white p-3 text-xs text-gray-600">
                    {voiceText && <p>들은 말: {voiceText}</p>}
                    {voiceHint && <p className="mt-1 font-medium text-gray-800">{voiceHint}</p>}
                  </div>
                )}

                {timerRemaining > 0 && (
                  <div className="mt-3 flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 p-3">
                    <div>
                      <p className="text-xs font-medium text-amber-700">조리 타이머</p>
                      <p className="mt-0.5 font-mono text-2xl font-bold text-amber-800">
                        {formatTimer(timerRemaining)}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        clearCookingTimer();
                        setVoiceHint("타이머를 취소했습니다.");
                      }}
                      className="rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm font-semibold text-amber-800 active:bg-amber-100"
                    >
                      취소
                    </button>
                  </div>
                )}
              </div>
            )}

            {showAllSteps && (
              <ol className="mt-3 space-y-1.5 text-sm leading-relaxed">
                {recipe.instructions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </li>
  );
}
