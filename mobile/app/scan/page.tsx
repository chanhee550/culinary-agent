"use client";

import { useRef, useState } from "react";
import { Camera, Image as ImageIcon, Loader2, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CATEGORIES } from "@/lib/types";
import type { ScanResult } from "@/lib/types";

interface UnknownDraft {
  id: number;
  description: string;
  guess?: string;
  location?: string;
  imageIndex?: number;
  name: string;
  category: string;
  quantity: string;
}

export default function ScanPage() {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [confirmedSelected, setConfirmedSelected] = useState<Set<number>>(new Set());
  const [unknownDrafts, setUnknownDrafts] = useState<UnknownDraft[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFiles(list: FileList | null) {
    if (!list?.length) return;
    const arr = Array.from(list);
    setFiles((prev) => [...prev, ...arr]);
    setPreviews((prev) => [...prev, ...arr.map((f) => URL.createObjectURL(f))]);
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
    setPreviews((prev) => {
      URL.revokeObjectURL(prev[idx]);
      return prev.filter((_, i) => i !== idx);
    });
  }

  async function startScan() {
    if (!files.length) return;
    setScanning(true);
    setError(null);
    try {
      const r = await api.scan(files);
      setResult(r);
      setConfirmedSelected(new Set(r.confirmed.map((_, i) => i)));
      setUnknownDrafts(
        r.unknowns.map((u) => ({
          id: u.id,
          description: u.description,
          guess: u.guess,
          location: u.location,
          imageIndex: u.image_index,
          name: (u.guess || "").split(" 또는 ")[0].trim(),
          category: "양념/소스",
          quantity: "",
        }))
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setScanning(false);
    }
  }

  function toggleConfirmed(i: number) {
    setConfirmedSelected((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  function updateUnknown(id: number, patch: Partial<UnknownDraft>) {
    setUnknownDrafts((prev) =>
      prev.map((u) => (u.id === id ? { ...u, ...patch } : u))
    );
  }

  async function save() {
    if (!result) return;
    const confirmed = result.confirmed
      .filter((_, i) => confirmedSelected.has(i))
      .map((c) => ({
        name: c.name,
        category: c.category || "기타",
        quantity: c.quantity ?? null,
      }));
    const unknowns = unknownDrafts
      .filter((u) => u.name.trim())
      .map((u) => ({
        name: u.name.trim(),
        category: u.category,
        quantity: u.quantity.trim() || null,
      }));
    const items = [...confirmed, ...unknowns];
    if (!items.length) return;

    setSaving(true);
    try {
      await api.bulkUpsert(items, "scan");
      router.push("/ingredients");
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  const totalToSave =
    confirmedSelected.size + unknownDrafts.filter((u) => u.name.trim()).length;

  return (
    <div className="px-5 pt-10 pb-6">
      <h1 className="mb-1 text-2xl font-bold">냉장고 스캔</h1>
      <p className="mb-5 text-sm text-gray-500">
        사진을 올리면 AI가 재료를 자동 인식합니다. 통·병에 담긴 음식은 직접 알려주세요.
      </p>

      {/* 사진 업로드 */}
      {!result && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3">
            <button
              onClick={() => {
                fileInput.current?.setAttribute("capture", "environment");
                fileInput.current?.click();
              }}
              className="flex h-24 flex-col items-center justify-center gap-1 rounded-2xl bg-brand text-white active:opacity-90"
            >
              <Camera size={26} />
              <span className="text-sm font-semibold">사진 촬영</span>
            </button>
            <button
              onClick={() => {
                fileInput.current?.removeAttribute("capture");
                fileInput.current?.click();
              }}
              className="flex h-24 flex-col items-center justify-center gap-1 rounded-2xl border border-gray-200 bg-white active:bg-gray-50"
            >
              <ImageIcon size={26} className="text-gray-700" />
              <span className="text-sm font-semibold">갤러리에서 선택</span>
            </button>
          </div>
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />

          {previews.length > 0 && (
            <ul className="mb-4 grid grid-cols-3 gap-2">
              {previews.map((src, i) => (
                <li key={i} className="relative aspect-square">
                  <img
                    src={src}
                    alt=""
                    className="h-full w-full rounded-lg object-cover"
                  />
                  <button
                    onClick={() => removeFile(i)}
                    className="absolute right-1 top-1 grid h-7 w-7 place-items-center rounded-full bg-black/60 text-white"
                    aria-label="삭제"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <button
            disabled={!files.length || scanning}
            onClick={startScan}
            className="flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-gray-900 text-white font-semibold disabled:opacity-40"
          >
            {scanning ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                AI 분석 중...
              </>
            ) : (
              `재료 스캔 시작 (${files.length}장)`
            )}
          </button>
        </>
      )}

      {error && (
        <div className="mt-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* 결과 */}
      {result && (
        <>
          {result.confirmed.length > 0 && (
            <section className="mb-6">
              <h2 className="mb-3 text-sm font-semibold">
                ✅ 인식된 재료 ({result.confirmed.length})
              </h2>
              <ul className="space-y-2">
                {result.confirmed.map((c, i) => {
                  const checked = confirmedSelected.has(i);
                  return (
                    <li key={i}>
                      <label className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 active:bg-gray-50">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleConfirmed(i)}
                          className="h-5 w-5 accent-brand"
                        />
                        <div className="flex-1">
                          <p className="text-sm font-semibold">{c.name}</p>
                          <p className="text-xs text-gray-500">
                            {c.category}
                            {c.quantity ? ` · ${c.quantity}` : ""}
                          </p>
                        </div>
                      </label>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          {unknownDrafts.length > 0 && (
            <section className="mb-6">
              <h2 className="mb-1 text-sm font-semibold">
                ❓ 직접 알려주세요 ({unknownDrafts.length})
              </h2>
              <p className="mb-3 text-xs text-gray-500">
                통·병에 담긴 음식은 AI가 정확히 알 수 없어요. 비워두면 저장되지 않습니다.
              </p>
              <ul className="space-y-3">
                {unknownDrafts.map((u) => (
                  <li
                    key={u.id}
                    className="rounded-xl border border-gray-200 bg-white p-4"
                  >
                    <p className="text-sm font-semibold">📦 {u.description}</p>
                    {(u.location || u.imageIndex !== undefined) && (
                      <p className="mt-0.5 text-xs text-gray-500">
                        {u.location && `📍 ${u.location}`}
                        {u.imageIndex !== undefined &&
                          ` · 🖼️ 사진 #${u.imageIndex + 1}`}
                      </p>
                    )}
                    {u.guess && (
                      <p className="mt-1 text-xs text-amber-700">
                        💡 AI 추측: {u.guess}
                      </p>
                    )}
                    <div className="mt-3 space-y-2">
                      <input
                        value={u.name}
                        placeholder="예: 김치, 토마토소스"
                        onChange={(e) =>
                          updateUnknown(u.id, { name: e.target.value })
                        }
                        className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
                      />
                      <div className="flex gap-2">
                        <select
                          value={u.category}
                          onChange={(e) =>
                            updateUnknown(u.id, { category: e.target.value })
                          }
                          className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
                        >
                          {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                        <input
                          value={u.quantity}
                          placeholder="수량 (선택)"
                          onChange={(e) =>
                            updateUnknown(u.id, { quantity: e.target.value })
                          }
                          className="w-28 rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
                        />
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="sticky bottom-20 left-0 right-0 mt-4 flex gap-2">
            <button
              onClick={() => {
                setResult(null);
                setConfirmedSelected(new Set());
                setUnknownDrafts([]);
                setFiles([]);
                previews.forEach(URL.revokeObjectURL);
                setPreviews([]);
              }}
              className="h-14 flex-1 rounded-2xl border border-gray-300 bg-white font-semibold"
            >
              초기화
            </button>
            <button
              disabled={totalToSave === 0 || saving}
              onClick={save}
              className="h-14 flex-[2] rounded-2xl bg-brand font-semibold text-white disabled:opacity-40"
            >
              {saving ? "저장 중..." : `${totalToSave}개 저장`}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
