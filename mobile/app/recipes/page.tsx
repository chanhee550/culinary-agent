"use client";

import { useEffect, useState } from "react";
import { Loader2, ChefHat, Clock, Star } from "lucide-react";
import { api } from "@/lib/api";
import type { Recipe } from "@/lib/types";

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

  const stars =
    recipe.difficulty === "쉬움" ? 3 :
    recipe.difficulty === "어려움" ? 1 : 2;

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

      {open && (
        <div className="space-y-4 border-t border-gray-100 p-4">
          <div>
            <h3 className="mb-2 text-xs font-semibold text-gray-700">재료</h3>
            <ul className="space-y-1 text-sm">
              {recipe.ingredients.map((ing) => {
                const isMissing = missing.has(ing);
                const hasSub = isMissing && subs[ing];
                return (
                  <li key={ing} className="flex items-start gap-2">
                    <span>
                      {hasSub ? "🟡" : isMissing ? "🔴" : "🟢"}
                    </span>
                    <span className={isMissing ? "text-gray-500" : ""}>
                      {hasSub ? <s>{ing}</s> : ing}
                      {hasSub && " → 대체 가능"}
                      {isMissing && !hasSub && " (부족)"}
                    </span>
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
            <ol className="space-y-1.5 text-sm leading-relaxed">
              {recipe.instructions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </li>
  );
}
