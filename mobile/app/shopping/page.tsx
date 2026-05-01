"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, ShoppingCart, Eraser } from "lucide-react";
import { api } from "@/lib/api";
import { CATEGORIES } from "@/lib/types";
import type { ShoppingItem } from "@/lib/types";

export default function ShoppingPage() {
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 추가 폼
  const [newName, setNewName] = useState("");
  const [newQty, setNewQty] = useState("");
  const [newCat, setNewCat] = useState("기타");
  const [adding, setAdding] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setItems(await api.listShopping());
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
      await api.addShopping({
        name: newName.trim(),
        quantity: newQty.trim() || null,
        category: newCat,
      });
      setNewName("");
      setNewQty("");
      setNewCat("기타");
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setAdding(false);
    }
  }

  async function toggle(id: number) {
    try {
      // 낙관적 업데이트
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, checked: !i.checked } : i)));
      await api.toggleShopping(id);
    } catch (e) {
      setError(String(e));
      reload();
    }
  }

  async function remove(id: number) {
    try {
      setItems((prev) => prev.filter((i) => i.id !== id));
      await api.deleteShopping(id);
    } catch (e) {
      setError(String(e));
      reload();
    }
  }

  async function clearChecked() {
    if (!confirm("체크된 항목을 모두 삭제하시겠어요?")) return;
    try {
      await api.clearCheckedShopping();
      reload();
    } catch (e) {
      setError(String(e));
    }
  }

  const checkedCount = items.filter((i) => i.checked).length;
  const unchecked = items.filter((i) => !i.checked);
  const checked = items.filter((i) => i.checked);

  return (
    <div className="px-5 pt-10 pb-6">
      <h1 className="mb-1 flex items-center gap-2 text-2xl font-bold">
        <ShoppingCart className="text-brand" size={26} />
        장보기 목록
      </h1>
      <p className="mb-5 text-sm text-gray-500">
        사야 할 재료를 모아두고 마트에서 체크하세요.
      </p>

      {/* 추가 */}
      <section className="mb-5 rounded-2xl border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">항목 추가</h2>
        <div className="space-y-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && newName.trim()) add(); }}
            placeholder="재료명 (예: 우유)"
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

      {error && (
        <div className="mb-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">불러오는 중...</p>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          장보기 목록이 비어있습니다.
          <br />
          위에서 항목을 추가하거나, 레시피 화면에서 부족 재료를 일괄 추가할 수 있어요.
        </div>
      ) : (
        <>
          {/* 체크 안 된 항목 */}
          {unchecked.length > 0 && (
            <section className="mb-5">
              <h2 className="mb-2 text-sm font-semibold text-gray-700">
                살 것 ({unchecked.length})
              </h2>
              <ul className="space-y-2">
                {unchecked.map((it) => (
                  <ShoppingRow
                    key={it.id} item={it}
                    onToggle={() => toggle(it.id)}
                    onDelete={() => remove(it.id)}
                  />
                ))}
              </ul>
            </section>
          )}

          {/* 완료된 항목 */}
          {checked.length > 0 && (
            <section className="mb-5">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-700">
                  완료 ({checked.length})
                </h2>
                <button
                  onClick={clearChecked}
                  className="flex items-center gap-1 text-xs font-medium text-red-500"
                >
                  <Eraser size={14} /> 모두 삭제
                </button>
              </div>
              <ul className="space-y-2">
                {checked.map((it) => (
                  <ShoppingRow
                    key={it.id} item={it}
                    onToggle={() => toggle(it.id)}
                    onDelete={() => remove(it.id)}
                  />
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function ShoppingRow({
  item, onToggle, onDelete,
}: { item: ShoppingItem; onToggle: () => void; onDelete: () => void }) {
  return (
    <li className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-3">
      <input
        type="checkbox"
        checked={item.checked}
        onChange={onToggle}
        className="h-5 w-5 accent-brand"
        aria-label={`${item.name} 토글`}
      />
      <div className={`flex-1 ${item.checked ? "text-gray-400 line-through" : ""}`}>
        <p className="text-sm font-medium">{item.name}</p>
        <p className="text-xs text-gray-500">
          {item.category}{item.quantity ? ` · ${item.quantity}` : ""}
        </p>
      </div>
      <button
        onClick={onDelete}
        aria-label="삭제"
        className="grid h-9 w-9 place-items-center rounded-lg text-gray-400 active:bg-gray-100"
      >
        <Trash2 size={16} />
      </button>
    </li>
  );
}
