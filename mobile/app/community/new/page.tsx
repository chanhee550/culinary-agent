"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ImagePlus, Star, X, ChefHat } from "lucide-react";
import { api, AuthRequired, ModerationBlocked } from "@/lib/api";
import type { SavedRecipe } from "@/lib/types";

const MAX_IMAGES = 3;
const MAX_BYTES = 5 * 1024 * 1024;

export default function NewPostPage() {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [rating, setRating] = useState(5);
  const [commentsEnabled, setCommentsEnabled] = useState(true);
  const [recipes, setRecipes] = useState<SavedRecipe[]>([]);
  const [recipeId, setRecipeId] = useState<number | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<{ count: number; limit: number; deleted: boolean } | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    api.listSavedRecipes()
      .then(setRecipes)
      .catch((e) => {
        if (e instanceof AuthRequired) return;
        // 레시피 로드 실패는 치명적 아님
      });
  }, []);

  function pickFiles(picked: FileList | null) {
    if (!picked) return;
    setError(null);
    const next: File[] = [...files];
    for (const f of Array.from(picked)) {
      if (next.length >= MAX_IMAGES) {
        setError(`이미지는 최대 ${MAX_IMAGES}장까지 첨부할 수 있어요.`);
        break;
      }
      if (f.size > MAX_BYTES) {
        setError("이미지 1장당 5MB까지만 첨부 가능해요.");
        continue;
      }
      next.push(f);
    }
    setFiles(next);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function removeFile(idx: number) {
    setFiles(files.filter((_, i) => i !== idx));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setError(null);
    setWarning(null);

    const trimmed = content.trim();
    if (trimmed.length === 0) {
      setError("후기 내용을 입력해주세요.");
      return;
    }

    setSubmitting(true);
    try {
      await api.createPost({
        content: trimmed,
        rating,
        comments_enabled: commentsEnabled,
        saved_recipe_id: recipeId,
        images: files,
      });
      router.replace("/community");
    } catch (e) {
      if (e instanceof AuthRequired) return;
      if (e instanceof ModerationBlocked) {
        setWarning({
          count: e.payload.warning_count,
          limit: e.payload.warning_limit,
          deleted: e.payload.account_deleted,
        });
        setError(e.payload.reason);
        if (e.payload.account_deleted) {
          // 잠시 메시지 보여준 뒤 /login으로 이동 (clearAuth는 api.ts에서 이미 처리됨)
          setTimeout(() => router.replace("/login"), 2500);
        }
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="px-5 pt-12 pb-6">
      <header className="mb-5 flex items-center gap-2">
        <button
          type="button"
          onClick={() => router.back()}
          className="-ml-2 flex h-10 w-10 items-center justify-center rounded-full text-gray-600 active:bg-gray-100"
        >
          <ChevronLeft size={22} />
        </button>
        <h1 className="text-xl font-bold">후기 작성</h1>
      </header>

      <form onSubmit={submit} className="space-y-4">
        {/* 별점 */}
        <section>
          <p className="mb-2 text-xs font-medium text-gray-600">별점</p>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => setRating(i)}
                className="p-1"
                aria-label={`${i}점`}
              >
                <Star
                  size={32}
                  className={i <= rating ? "text-yellow-400" : "text-gray-200"}
                  fill={i <= rating ? "currentColor" : "none"}
                />
              </button>
            ))}
          </div>
        </section>

        {/* 레시피 연결 */}
        <section>
          <p className="mb-2 text-xs font-medium text-gray-600">
            연결할 레시피 (선택)
          </p>
          {recipes.length === 0 ? (
            <p className="rounded-xl bg-gray-50 p-3 text-xs text-gray-500">
              저장한 레시피가 없어요. 레시피 화면에서 즐겨찾기를 먼저 해보세요.
            </p>
          ) : (
            <select
              value={recipeId ?? ""}
              onChange={(e) => setRecipeId(e.target.value ? Number(e.target.value) : null)}
              className="h-12 w-full rounded-2xl border border-gray-200 bg-white px-3 text-sm outline-none focus:border-brand"
            >
              <option value="">레시피 없이 작성</option>
              {recipes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          )}
          {recipeId != null && (
            <p className="mt-1 inline-flex items-center gap-1 text-[11px] text-brand-dark">
              <ChefHat size={12} />
              {recipes.find((r) => r.id === recipeId)?.name}
            </p>
          )}
        </section>

        {/* 본문 */}
        <section>
          <p className="mb-2 text-xs font-medium text-gray-600">후기 내용</p>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            maxLength={2000}
            placeholder="레시피를 따라 만들어본 경험을 공유해주세요."
            className="min-h-[140px] w-full rounded-2xl border border-gray-200 bg-white p-3 text-sm outline-none focus:border-brand"
          />
          <p className="mt-1 text-right text-[11px] text-gray-400">
            {content.length} / 2000
          </p>
        </section>

        {/* 사진 */}
        <section>
          <p className="mb-2 text-xs font-medium text-gray-600">
            사진 ({files.length}/{MAX_IMAGES})
          </p>
          <div className="flex gap-2 overflow-x-auto">
            {files.map((f, i) => (
              <div key={i} className="relative h-24 w-24 shrink-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={URL.createObjectURL(f)}
                  alt=""
                  className="h-full w-full rounded-xl object-cover"
                />
                <button
                  type="button"
                  onClick={() => removeFile(i)}
                  className="absolute -right-1.5 -top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-gray-900 text-white shadow"
                  aria-label="제거"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
            {files.length < MAX_IMAGES && (
              <label className="flex h-24 w-24 shrink-0 cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed border-gray-300 text-gray-500 active:bg-gray-50">
                <ImagePlus size={20} />
                <span className="text-[11px]">추가</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  className="hidden"
                  onChange={(e) => pickFiles(e.target.files)}
                />
              </label>
            )}
          </div>
        </section>

        {/* 댓글 허용 */}
        <section className="flex items-center justify-between rounded-2xl bg-gray-50 p-3">
          <div>
            <p className="text-sm font-medium">댓글 허용</p>
            <p className="text-[11px] text-gray-500">
              끄면 다른 사용자가 댓글을 남길 수 없어요.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={commentsEnabled}
            onClick={() => setCommentsEnabled((v) => !v)}
            className={`h-7 w-12 shrink-0 rounded-full transition-colors ${
              commentsEnabled ? "bg-brand" : "bg-gray-300"
            }`}
          >
            <span
              className={`block h-6 w-6 translate-y-0.5 rounded-full bg-white shadow transition-transform ${
                commentsEnabled ? "translate-x-6" : "translate-x-0.5"
              }`}
            />
          </button>
        </section>

        {warning && (
          <div className="rounded-xl bg-red-50 p-3 text-sm">
            <p className="font-semibold text-red-800">
              {warning.deleted
                ? "경고 누적으로 계정이 삭제되었습니다."
                : `경고 누적: ${warning.count} / ${warning.limit}`}
            </p>
            {!warning.deleted && (
              <p className="mt-1 text-[12px] text-red-700">
                {warning.limit}회 누적 시 계정이 자동으로 삭제됩니다.
              </p>
            )}
          </div>
        )}

        {error && !warning && (
          <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="h-12 w-full rounded-2xl bg-brand text-base font-semibold text-white active:opacity-90 disabled:opacity-50"
        >
          {submitting ? "작성 중..." : "작성 완료"}
        </button>
      </form>
    </div>
  );
}
