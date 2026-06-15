"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  Camera, ChefHat, Refrigerator, BookmarkCheck, ShoppingCart,
  UserCircle, LogOut, Pencil, Check, X, Trash2,
} from "lucide-react";
import { api, AuthRequired } from "@/lib/api";
import { useAuth, saveAuth, clearAuth } from "@/lib/auth";
import type { Ingredient } from "@/lib/types";

export default function HomePage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listIngredients()
      .then(setItems)
      .catch((e) => {
        if (e instanceof AuthRequired) return; // AuthGate가 /login으로 보낼 것
        setError(String(e));
      })
      .finally(() => setLoading(false));
  }, []);

  const byCategory = items.reduce<Record<string, string[]>>((acc, i) => {
    (acc[i.category] ||= []).push(i.name);
    return acc;
  }, {});

  return (
    <div className="px-5 pt-12">
      <header className="mb-6 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-gray-500">🍳 오셰 · O'CHEF</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">
            {user?.display_name ? `안녕하세요, ${user.display_name}님` : "오늘 뭐 해 먹지?"}
          </h1>
        </div>
        <UserMenu />
      </header>

      <section className="mb-6 rounded-2xl bg-brand-soft p-5">
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-brand-dark">보유 재료</span>
          <span className="text-3xl font-bold text-brand-dark">{items.length}</span>
        </div>
        <p className="mt-1 text-xs text-brand-dark/80">
          {items.length === 0
            ? "냉장고를 스캔하거나 직접 추가해보세요"
            : `${Object.keys(byCategory).length}개 카테고리`}
        </p>
      </section>

      <section className="mb-6 grid grid-cols-2 gap-3">
        <QuickAction href="/scan" icon={Camera} label="냉장고 스캔" tone="brand" />
        <QuickAction href="/recipes" icon={ChefHat} label="레시피 추천" tone="amber" />
        <Link
          href="/ingredients"
          className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-4 active:bg-gray-50"
        >
          <Refrigerator className="text-gray-700" size={22} />
          <div className="flex-1">
            <p className="text-sm font-semibold">재료 관리</p>
            <p className="text-xs text-gray-500">유통기한까지</p>
          </div>
          <span className="text-gray-400">›</span>
        </Link>
        <Link
          href="/saved"
          className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-4 active:bg-gray-50"
        >
          <BookmarkCheck className="text-gray-700" size={22} />
          <div className="flex-1">
            <p className="text-sm font-semibold">저장 레시피</p>
            <p className="text-xs text-gray-500">즐겨찾기 + 별점</p>
          </div>
          <span className="text-gray-400">›</span>
        </Link>
        <Link
          href="/shopping"
          className="col-span-2 flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-4 active:bg-gray-50"
        >
          <ShoppingCart className="text-gray-700" size={22} />
          <div className="flex-1">
            <p className="text-sm font-semibold">장보기 목록</p>
            <p className="text-xs text-gray-500">사야 할 재료 모아보기</p>
          </div>
          <span className="text-gray-400">›</span>
        </Link>
      </section>

      {error && (
        <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          백엔드 연결 실패: {error}
          <p className="mt-1 text-xs">
            <code className="rounded bg-red-100 px-1">uvicorn backend.main:app --reload</code> 가 떠 있는지 확인하세요.
          </p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <section className="mt-2">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">카테고리별 재료</h2>
          <ul className="space-y-2">
            {Object.entries(byCategory).sort().map(([cat, names]) => (
              <li
                key={cat}
                className="rounded-xl border border-gray-200 bg-white p-4"
              >
                <p className="text-xs font-semibold text-brand-dark">{cat}</p>
                <p className="mt-1 text-sm text-gray-700">{names.join(", ")}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function QuickAction({
  href, icon: Icon, label, tone,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
  tone: "brand" | "amber";
}) {
  const styles = tone === "brand"
    ? "bg-brand text-white"
    : "bg-amber-500 text-white";
  return (
    <Link
      href={href}
      className={`flex h-24 flex-col items-start justify-between rounded-2xl p-4 active:opacity-90 ${styles}`}
    >
      <Icon size={24} className="opacity-90" />
      <span className="text-base font-semibold">{label}</span>
    </Link>
  );
}

function UserMenu() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleteText, setDeleteText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
        setEditing(false);
        setConfirmingDelete(false);
        setDeleteText("");
        setDeleteError(null);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  if (!user) return null;

  async function saveName() {
    if (!user) return;
    const next = draft.trim();
    if (!next || next === user.display_name) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await api.patchDisplayName(next);
      // 토큰은 그대로, user만 갱신
      const token = (await import("@/lib/auth")).getToken();
      if (token) saveAuth(token, updated);
    } catch {
      // 에러 시 무음 — 추후 toast 추가 여지
    } finally {
      setSaving(false);
      setEditing(false);
    }
  }

  function logout() {
    clearAuth();
    // AuthGate가 /login으로 redirect
  }

  async function deleteAccount() {
    if (deleting) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteAccount();
      // 토큰 정리 — AuthGate가 /login으로 보냄
      clearAuth();
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : String(e));
      setDeleting(false);
    }
  }

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700 active:bg-gray-50"
        aria-label="계정 메뉴"
      >
        <UserCircle size={22} />
      </button>

      {open && (
        <div className="absolute right-0 top-12 z-30 w-64 rounded-2xl border border-gray-200 bg-white p-3 shadow-lg">
          <div className="border-b border-gray-100 px-2 pb-3">
            {editing ? (
              <div className="flex items-center gap-2">
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  maxLength={40}
                  className="h-9 flex-1 rounded-lg border border-gray-200 px-2 text-sm outline-none focus:border-brand"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveName();
                    if (e.key === "Escape") setEditing(false);
                  }}
                />
                <button
                  onClick={saveName}
                  disabled={saving}
                  className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand text-white disabled:opacity-50"
                  aria-label="저장"
                >
                  <Check size={16} />
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 text-gray-600"
                  aria-label="취소"
                >
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-gray-900">
                    {user.display_name || "닉네임 없음"}
                  </p>
                  <p className="truncate text-xs text-gray-500">{user.email}</p>
                  <p className="mt-0.5 text-[10px] uppercase tracking-wider text-gray-400">
                    {user.auth_provider === "google" ? "Google 계정" : "이메일 계정"}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setDraft(user.display_name || "");
                    setEditing(true);
                  }}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100"
                  aria-label="닉네임 수정"
                >
                  <Pencil size={14} />
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={logout}
            className="mt-2 flex h-10 w-full items-center gap-2 rounded-xl px-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <LogOut size={16} />
            로그아웃
          </button>

          {!confirmingDelete ? (
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="mt-1 flex h-10 w-full items-center gap-2 rounded-xl px-3 text-sm font-medium text-red-600 hover:bg-red-50"
            >
              <Trash2 size={16} />
              계정 삭제
            </button>
          ) : (
            <div className="mt-2 rounded-xl bg-red-50 p-3">
              <p className="text-xs font-semibold text-red-800">
                정말 계정을 삭제할까요?
              </p>
              <p className="mt-1 text-[11px] leading-relaxed text-red-700">
                재료·저장 레시피·장보기 목록·프로필이 모두 영구 삭제되며
                복구할 수 없어요.
              </p>
              <input
                type="text"
                autoFocus
                value={deleteText}
                onChange={(e) => setDeleteText(e.target.value)}
                placeholder="확인을 위해 '삭제'를 입력"
                className="mt-2 h-9 w-full rounded-lg border border-red-200 bg-white px-2 text-sm outline-none focus:border-red-500"
              />
              {deleteError && (
                <p className="mt-2 text-[11px] text-red-700">실패: {deleteError}</p>
              )}
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setConfirmingDelete(false);
                    setDeleteText("");
                    setDeleteError(null);
                  }}
                  disabled={deleting}
                  className="h-9 flex-1 rounded-lg bg-white text-xs font-medium text-gray-700 disabled:opacity-50"
                >
                  취소
                </button>
                <button
                  type="button"
                  onClick={deleteAccount}
                  disabled={deleting || deleteText.trim() !== "삭제"}
                  className="h-9 flex-1 rounded-lg bg-red-600 text-xs font-semibold text-white disabled:opacity-40"
                >
                  {deleting ? "삭제 중..." : "영구 삭제"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
