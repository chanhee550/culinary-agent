"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Camera, ChefHat, Refrigerator, BookmarkCheck, ShoppingCart } from "lucide-react";
import { api } from "@/lib/api";
import type { Ingredient } from "@/lib/types";

export default function HomePage() {
  const [items, setItems] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listIngredients()
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const byCategory = items.reduce<Record<string, string[]>>((acc, i) => {
    (acc[i.category] ||= []).push(i.name);
    return acc;
  }, {});

  return (
    <div className="px-5 pt-12">
      <header className="mb-6">
        <p className="text-sm text-gray-500">🍳 Culinary Agent</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">
          오늘 뭐 해 먹지?
        </h1>
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
