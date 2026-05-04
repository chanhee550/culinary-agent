"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Pencil, X, Check } from "lucide-react";
import { api } from "@/lib/api";
import { CATEGORIES } from "@/lib/types";
import type { Ingredient } from "@/lib/types";

export default function IngredientsPage() {
  const [items, setItems] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterCat, setFilterCat] = useState<string>("전체");
  const [editingId, setEditingId] = useState<string | number | null>(null);

  // 추가 폼
  const [newName, setNewName] = useState("");
  const [newCat, setNewCat] = useState("기타");
  const [newQty, setNewQty] = useState("");
  const [adding, setAdding] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setItems(await api.listIngredients());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, []);

  async function add() {
    if (!newName.trim()) return;
    setAdding(true);
    try {
      await api.addIngredient({
        name: newName.trim(),
        category: newCat,
        quantity: newQty.trim() || null,
      });
      setNewName(""); setNewQty(""); setNewCat("기타");
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setAdding(false);
    }
  }

  async function remove(id: string | number | null) {
    if (id == null) return;
    if (!confirm("삭제하시겠어요?")) return;
    await api.deleteIngredient(id);
    reload();
  }

  const cats = Array.from(new Set(items.map((i) => i.category))).sort();
  const filtered = filterCat === "전체"
    ? items
    : items.filter((i) => i.category === filterCat);

  return (
    <div className="px-5 pt-10 pb-6">
      <h1 className="mb-5 text-2xl font-bold">재료 관리</h1>

      {/* 추가 */}
      <section className="mb-6 rounded-2xl border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">재료 추가</h2>
        <div className="space-y-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="재료명 (예: 당근)"
            className="block w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
          />
          <div className="flex gap-2">
            <select
              value={newCat}
              onChange={(e) => setNewCat(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
            >
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input
              value={newQty}
              onChange={(e) => setNewQty(e.target.value)}
              placeholder="수량"
              className="w-28 rounded-lg border border-gray-300 px-3 py-2.5 text-sm"
            />
          </div>
          <button
            disabled={!newName.trim() || adding}
            onClick={add}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand font-semibold text-white disabled:opacity-40"
          >
            <Plus size={18} />
            {adding ? "추가 중..." : "추가"}
          </button>
        </div>
      </section>

      {/* 필터 */}
      {cats.length > 0 && (
        <div className="mb-3 flex gap-2 overflow-x-auto pb-2">
          {["전체", ...cats].map((c) => (
            <button
              key={c}
              onClick={() => setFilterCat(c)}
              className={`shrink-0 rounded-full px-4 py-1.5 text-xs font-medium ${
                filterCat === c
                  ? "bg-gray-900 text-white"
                  : "bg-white text-gray-600 border border-gray-200"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      {/* 목록 */}
      <h2 className="mb-3 text-sm font-semibold text-gray-700">
        보유 재료 ({filtered.length}{filterCat !== "전체" && ` / ${items.length}`})
      </h2>

      {error && (
        <div className="mb-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">불러오는 중...</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          {items.length === 0
            ? "등록된 재료가 없습니다. 위에서 추가하거나 스캔해주세요."
            : "이 카테고리에는 재료가 없습니다."}
        </div>
      ) : (
        <ul className="space-y-2">
          {filtered.map((i) => (
            <IngredientRow
              key={String(i.id)}
              item={i}
              editing={editingId === i.id}
              onEditStart={() => setEditingId(i.id)}
              onEditCancel={() => setEditingId(null)}
              onSaved={() => { setEditingId(null); reload(); }}
              onDelete={() => remove(i.id)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function IngredientRow({
  item, editing, onEditStart, onEditCancel, onSaved, onDelete,
}: {
  item: Ingredient;
  editing: boolean;
  onEditStart: () => void;
  onEditCancel: () => void;
  onSaved: () => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(item.name);
  const [category, setCategory] = useState(item.category);
  const [quantity, setQuantity] = useState(item.quantity || "");
  const [busy, setBusy] = useState(false);

  if (!editing) {
    return (
      <li className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4">
        <div className="flex-1">
          <p className="text-sm font-semibold">{item.name}</p>
          <p className="text-xs text-gray-500">
            {item.category}{item.quantity ? ` · ${item.quantity}` : ""}
          </p>
        </div>
        <button
          onClick={onEditStart}
          aria-label="수정"
          className="grid h-9 w-9 place-items-center rounded-lg text-gray-500 active:bg-gray-100"
        >
          <Pencil size={16} />
        </button>
        <button
          onClick={onDelete}
          aria-label="삭제"
          className="grid h-9 w-9 place-items-center rounded-lg text-red-500 active:bg-red-50"
        >
          <Trash2 size={16} />
        </button>
      </li>
    );
  }

  async function save() {
    if (item.id == null) return;
    setBusy(true);
    try {
      await api.patchIngredient(item.id, {
        name: name.trim(),
        category,
        quantity: quantity.trim() || null,
      });
      onSaved();
    } finally { setBusy(false); }
  }

  return (
    <li className="rounded-xl border border-brand bg-brand-soft/40 p-4 space-y-2">
      <input
        value={name} onChange={(e) => setName(e.target.value)}
        className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
      />
      <div className="flex gap-2">
        <select
          value={category} onChange={(e) => setCategory(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input
          value={quantity} onChange={(e) => setQuantity(e.target.value)}
          placeholder="수량"
          className="w-28 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={onEditCancel}
          className="flex h-10 flex-1 items-center justify-center gap-1 rounded-lg border border-gray-300 bg-white text-sm font-semibold"
        >
          <X size={16} /> 취소
        </button>
        <button
          disabled={busy} onClick={save}
          className="flex h-10 flex-[2] items-center justify-center gap-1 rounded-lg bg-brand text-sm font-semibold text-white disabled:opacity-40"
        >
          <Check size={16} /> 저장
        </button>
      </div>
    </li>
  );
}
