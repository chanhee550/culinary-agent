import type {
  Ingredient, ModerationBlockedDetail, Post, PostComment,
  Recipe, RecipeContext, ScanResult, SavedRecipe, ShoppingItem, VoiceCommand,
} from "./types";
import { getToken, clearAuth, type AuthUser } from "./auth";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BASE = API_BASE;

/** 백엔드에서 반환된 /uploads/... 상대 URL을 절대 URL로 변환. */
export function absoluteUrl(path: string): string {
  if (!path) return path;
  if (/^https?:\/\//.test(path)) return path;
  return `${BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

export class AuthRequired extends Error {
  constructor(public detail?: string) {
    super(detail || "auth_required");
    this.name = "AuthRequired";
  }
}

export class ModerationBlocked extends Error {
  constructor(public payload: ModerationBlockedDetail) {
    super(payload.reason);
    this.name = "ModerationBlocked";
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
    if (res.status === 422 && text) {
      // 모더레이션 차단 시 detail 객체가 그대로 들어옴
      try {
        const parsed = JSON.parse(text);
        const d = parsed?.detail;
        if (d && d.detail === "blocked") {
          if (d.account_deleted) clearAuth();
          throw new ModerationBlocked(d as ModerationBlockedDetail);
        }
      } catch (e) {
        if (e instanceof ModerationBlocked) throw e;
        // JSON parse 실패 — 일반 에러로 폴스루
      }
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

  voiceCommand: (audio: Blob, context?: RecipeContext) => {
    const fd = new FormData();
    fd.append("file", audio, "command.webm");
    if (context) fd.append("recipe_context", JSON.stringify(context));
    return request<VoiceCommand>("/voice/command", { method: "POST", body: fd });
  },

  tts: async (text: string) => {
    const res = await fetch(`${BASE}/voice/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`API ${res.status}: ${body || res.statusText}`);
    }
    return res.blob();
  },

  // ----- Posts (게시판) -----
  listPosts: (offset = 0, limit = 20) =>
    request<Post[]>(`/posts?offset=${offset}&limit=${limit}`),

  getPost: (id: number) => request<Post>(`/posts/${id}`),

  createPost: (input: {
    content: string;
    rating: number;
    comments_enabled: boolean;
    saved_recipe_id?: number | null;
    images: File[];
  }) => {
    const fd = new FormData();
    fd.append("content", input.content);
    fd.append("rating", String(input.rating));
    fd.append("comments_enabled", input.comments_enabled ? "true" : "false");
    if (input.saved_recipe_id != null) {
      fd.append("saved_recipe_id", String(input.saved_recipe_id));
    }
    for (const f of input.images) fd.append("images", f);
    return request<Post>("/posts", { method: "POST", body: fd });
  },

  patchPost: (id: number, body: { content?: string; comments_enabled?: boolean }) =>
    request<Post>(`/posts/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  deletePost: (id: number) =>
    request<void>(`/posts/${id}`, { method: "DELETE" }),

  toggleLike: (postId: number) =>
    request<{ liked: boolean; like_count: number }>(`/posts/${postId}/like`, {
      method: "POST",
    }),

  listComments: (postId: number) =>
    request<PostComment[]>(`/posts/${postId}/comments`),

  addComment: (postId: number, content: string) =>
    request<PostComment>(`/posts/${postId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  deleteComment: (commentId: number) =>
    request<void>(`/comments/${commentId}`, { method: "DELETE" }),

  myWarnings: () =>
    request<{ warning_count: number; warning_limit: number }>("/me/warnings"),
};
