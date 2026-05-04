import type {
  Ingredient, Recipe, ScanResult, SavedRecipe, ShoppingItem,
} from "./types";
import { getToken, clearAuth, type AuthUser } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class AuthRequired extends Error {
  constructor(public detail?: string) {
    super(detail || "auth_required");
    this.name = "AuthRequired";
  }
}

async function request<T>(path: string, init?: RequestInit, opts?: { auth?: boolean }): Promise<T> {
  const auth = opts?.auth !== false; // 기본값: 인증 헤더 포함
  const token = auth ? getToken() : null;

  const headers: Record<string, string> = {
    ...(init?.body && !(init.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    if (res.status === 401 && auth) {
      // 토큰 만료/무효 → 저장된 자격 정리. UI는 useAuth로 감지해 /login 리다이렉트.
      clearAuth();
      throw new AuthRequired(text);
    }
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  // 204 No Content (예: 계정 삭제) — body 파싱 시도하면 throw
  if (res.status === 204) return undefined as T;
  return res.json();
}

type TokenResponse = { access_token: string; token_type: string; user: AuthUser };

export const api = {
  health: () => request<{ status: string }>("/health", undefined, { auth: false }),

  // ----- Auth -----
  register: (email: string, password: string, display_name: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    }, { auth: false }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, { auth: false }),

  googleLogin: (id_token: string) =>
    request<TokenResponse>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token }),
    }, { auth: false }),

  me: () => request<AuthUser>("/auth/me"),

  patchDisplayName: (display_name: string) =>
    request<AuthUser>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ display_name }),
    }),

  deleteAccount: () =>
    request<void>("/auth/me", { method: "DELETE" }),

  // ----- Ingredients -----
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
