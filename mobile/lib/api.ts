import type {
  Ingredient, Recipe, ScanResult, SavedRecipe, ShoppingItem,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  listIngredients: () => request<Ingredient[]>("/ingredients"),

  addIngredient: (item: { name: string; category?: string; quantity?: string | null }) =>
    request<Ingredient>("/ingredients", {
      method: "POST",
      body: JSON.stringify(item),
    }),

  bulkUpsert: (items: { name: string; category: string; quantity?: string | null }[],
               source = "scan") =>
    request<{ saved: number }>("/ingredients/bulk", {
      method: "POST",
      body: JSON.stringify({ items, source }),
    }),

  patchIngredient: (id: string | number,
                    body: { name?: string; category?: string; quantity?: string | null }) =>
    request<{ updated: string }>(`/ingredients/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteIngredient: (id: string | number) =>
    request<{ deleted: string }>(`/ingredients/${id}`, { method: "DELETE" }),

  clearAll: () =>
    request<{ cleared: boolean }>("/ingredients", { method: "DELETE" }),

  scan: (files: File[]) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    return request<ScanResult>("/scan", { method: "POST", body: fd });
  },

  recipes: (max_missing = 2, ingredients?: string[]) =>
    request<Recipe[]>("/recipes", {
      method: "POST",
      body: JSON.stringify({ max_missing, ingredients }),
    }),

  // ----- Saved Recipes -----
  listSavedRecipes: () => request<SavedRecipe[]>("/saved_recipes"),

  saveRecipe: (recipe: Recipe) =>
    request<{ id: number }>("/saved_recipes", {
      method: "POST",
      body: JSON.stringify(recipe),
    }),

  rateRecipe: (id: number, rating: number) =>
    request<{ updated: number; rating: number }>(`/saved_recipes/${id}/rating`, {
      method: "PATCH",
      body: JSON.stringify({ rating }),
    }),

  deleteSavedRecipe: (id: number) =>
    request<{ deleted: number }>(`/saved_recipes/${id}`, { method: "DELETE" }),

  // ----- Shopping List -----
  listShopping: () => request<ShoppingItem[]>("/shopping"),

  addShopping: (item: { name: string; quantity?: string | null; category?: string }) =>
    request<{ added: string }>("/shopping", {
      method: "POST",
      body: JSON.stringify(item),
    }),

  toggleShopping: (id: number) =>
    request<{ toggled: number }>(`/shopping/${id}/toggle`, { method: "PATCH" }),

  deleteShopping: (id: number) =>
    request<{ deleted: number }>(`/shopping/${id}`, { method: "DELETE" }),

  clearCheckedShopping: () =>
    request<{ cleared: boolean }>("/shopping/checked/all", { method: "DELETE" }),

  shoppingFromMissing: (items: string[]) =>
    request<{ added: number }>("/shopping/from_missing", {
      method: "POST",
      body: JSON.stringify({ items }),
    }),
};
