"use client";

import { useEffect, useState } from "react";
import { Trash2, Star, Clock, BookmarkCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { SavedRecipe } from "@/lib/types";

export default function SavedRecipesPage() {
  const [items, setItems] = useState<SavedRecipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);

  async function reload() {
    setLoading(true);
    try {
      setItems(await api.listSavedRecipes());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, []);

  async function rate(id: number, rating: number) {
    try {
      await api.rateRecipe(id, rating);
      setItems((prev) => prev.map((r) => (r.id === id ? { ...r, rating } : r)));
    } catch (e) {
      setError(String(e));
    }
  }

  async function remove(id: number) {
    if (!confirm("이 레시피를 삭제하시겠어요?")) return;
    try {
      await api.deleteSavedRecipe(id);
      setItems((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="px-5 pt-10 pb-6">
      <h1 className="mb-1 flex items-center gap-2 text-2xl font-bold">
        <BookmarkCheck className="text-brand" size={26} />
        저장 레시피
      </h1>
      <p className="mb-5 text-sm text-gray-500">
        마음에 든 레시피를 보관하고 별점을 매겨보세요.
      </p>

      {error && (
        <div className="mb-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">불러오는 중...</p>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          저장된 레시피가 없습니다.
          <br />
          레시피 추천 화면에서 마음에 든 레시피의 ⭐ 버튼을 눌러보세요.
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((r) => (
            <SavedRecipeCard
              key={r.id}
              recipe={r}
              open={openId === r.id}
              onToggle={() => setOpenId(openId === r.id ? null : r.id)}
              onRate={(rating) => rate(r.id, rating)}
              onDelete={() => remove(r.id)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function SavedRecipeCard({
  recipe, open, onToggle, onRate, onDelete,
}: {
  recipe: SavedRecipe;
  open: boolean;
  onToggle: () => void;
  onRate: (rating: number) => void;
  onDelete: () => void;
}) {
  return (
    <li className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
      <div className="flex items-start gap-3 p-4">
        <button onClick={onToggle} className="flex-1 text-left">
          <p className="font-semibold">{recipe.name}</p>
          {recipe.description && (
            <p className="mt-0.5 text-xs text-gray-500">{recipe.description}</p>
          )}
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
            <span>{recipe.difficulty}</span>
            {recipe.time && (
              <>
                <span>·</span>
                <span className="flex items-center gap-1">
                  <Clock size={11} /> {recipe.time}
                </span>
              </>
            )}
            <span>·</span>
            <span>{new Date(recipe.saved_at).toLocaleDateString("ko-KR")}</span>
          </div>
        </button>
        <button
          onClick={onDelete}
          aria-label="삭제"
          className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-red-500 active:bg-red-50"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {/* 별점 */}
      <div className="flex items-center gap-1 border-t border-gray-100 px-4 py-2.5">
        <span className="mr-2 text-xs text-gray-500">평가:</span>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            onClick={() => onRate(n)}
            aria-label={`${n}점`}
            className="grid h-7 w-7 place-items-center"
          >
            <Star
              size={18}
              className={
                recipe.rating !== null && n <= recipe.rating
                  ? "fill-amber-400 text-amber-400"
                  : "text-gray-300"
              }
            />
          </button>
        ))}
      </div>

      {open && (
        <div className="space-y-3 border-t border-gray-100 p-4 text-sm">
          {recipe.ingredients.length > 0 && (
            <div>
              <h3 className="mb-1.5 text-xs font-semibold text-gray-700">재료</h3>
              <p className="text-gray-600">{recipe.ingredients.join(", ")}</p>
            </div>
          )}
          {recipe.missing.length > 0 && (
            <div>
              <h3 className="mb-1.5 text-xs font-semibold text-gray-700">부족 재료</h3>
              <p className="text-red-600">{recipe.missing.join(", ")}</p>
            </div>
          )}
          {recipe.instructions.length > 0 && (
            <div>
              <h3 className="mb-1.5 text-xs font-semibold text-gray-700">조리법</h3>
              <ol className="space-y-1 leading-relaxed text-gray-700">
                {recipe.instructions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
