"use client";

import { useEffect, useState, useCallback } from "react";

const TOKEN_KEY = "culinary.token";
const USER_KEY = "culinary.user";

export type AuthUser = {
  id: number;
  email: string;
  display_name: string | null;
  auth_provider: "email" | "google";
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function saveAuth(token: string, user: AuthUser) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  // 다른 탭/구독자에게 변경 알림
  window.dispatchEvent(new CustomEvent("culinary:auth-changed"));
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new CustomEvent("culinary:auth-changed"));
}

/** 클라이언트 컴포넌트에서 현재 로그인 상태를 구독하는 훅. */
export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(() => {
    setUser(getStoredUser());
    setReady(true);
  }, []);

  useEffect(() => {
    refresh();
    const onChange = () => refresh();
    window.addEventListener("culinary:auth-changed", onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener("culinary:auth-changed", onChange);
      window.removeEventListener("storage", onChange);
    };
  }, [refresh]);

  return { user, ready, isAuthed: !!user };
}
