"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Heart, MessageCircle, Plus, Star, ChefHat } from "lucide-react";
import { api, AuthRequired, absoluteUrl } from "@/lib/api";
import type { Post } from "@/lib/types";

export default function CommunityListPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listPosts();
      setPosts(data);
    } catch (e) {
      if (e instanceof AuthRequired) return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function onLike(p: Post) {
    // optimistic
    setPosts((cur) =>
      cur.map((x) =>
        x.id === p.id
          ? { ...x, my_liked: !x.my_liked, like_count: x.like_count + (x.my_liked ? -1 : 1) }
          : x,
      ),
    );
    try {
      const r = await api.toggleLike(p.id);
      setPosts((cur) =>
        cur.map((x) =>
          x.id === p.id ? { ...x, my_liked: r.liked, like_count: r.like_count } : x,
        ),
      );
    } catch {
      // revert
      setPosts((cur) =>
        cur.map((x) =>
          x.id === p.id
            ? { ...x, my_liked: p.my_liked, like_count: p.like_count }
            : x,
        ),
      );
    }
  }

  return (
    <div className="px-5 pt-12">
      <header className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">커뮤니티</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">레시피 후기</h1>
        </div>
        <Link
          href="/community/new"
          className="flex h-11 items-center gap-1.5 rounded-2xl bg-brand px-4 text-sm font-semibold text-white active:opacity-90"
        >
          <Plus size={16} /> 작성
        </Link>
      </header>

      {loading && <p className="mt-10 text-center text-sm text-gray-500">불러오는 중...</p>}
      {error && (
        <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}
      {!loading && !error && posts.length === 0 && (
        <div className="mt-12 text-center text-sm text-gray-500">
          아직 후기가 없어요. <br />첫 후기를 작성해보세요!
        </div>
      )}

      <ul className="space-y-3 pb-6">
        {posts.map((p) => (
          <li key={p.id}>
            <article className="rounded-2xl border border-gray-200 bg-white p-4">
              <Link href={`/community/${p.id}`} className="block">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-semibold text-brand-dark">
                      {(p.author_name || "?").charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">
                        {p.author_name || "익명"}
                      </p>
                      <p className="truncate text-[11px] text-gray-400">
                        {formatDate(p.created_at)}
                      </p>
                    </div>
                  </div>
                  <Stars value={p.rating} />
                </div>

                {p.saved_recipe_name && (
                  <div className="mb-2 inline-flex items-center gap-1 rounded-lg bg-brand-soft px-2 py-1 text-[11px] font-medium text-brand-dark">
                    <ChefHat size={12} /> {p.saved_recipe_name}
                  </div>
                )}

                <p className="mb-2 line-clamp-3 whitespace-pre-line text-sm text-gray-800">
                  {p.content}
                </p>

                {p.images.length > 0 && (
                  <div className="mb-3 flex gap-1.5 overflow-x-auto">
                    {p.images.map((src, i) => (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        key={i}
                        src={absoluteUrl(src)}
                        alt=""
                        className="h-24 w-24 shrink-0 rounded-xl object-cover"
                      />
                    ))}
                  </div>
                )}
              </Link>

              <div className="flex items-center gap-4 text-xs">
                <button
                  type="button"
                  onClick={() => onLike(p)}
                  className={`flex items-center gap-1 ${
                    p.my_liked ? "text-red-500" : "text-gray-500"
                  }`}
                >
                  <Heart size={16} fill={p.my_liked ? "currentColor" : "none"} />
                  <span>{p.like_count}</span>
                </button>
                <Link
                  href={`/community/${p.id}`}
                  className="flex items-center gap-1 text-gray-500"
                >
                  <MessageCircle size={16} />
                  <span>{p.comment_count}</span>
                  {!p.comments_enabled && (
                    <span className="ml-1 text-[10px] text-gray-400">(비활성)</span>
                  )}
                </Link>
              </div>
            </article>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Stars({ value }: { value: number }) {
  return (
    <div className="flex">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          size={14}
          className={i <= value ? "text-yellow-400" : "text-gray-200"}
          fill={i <= value ? "currentColor" : "none"}
        />
      ))}
    </div>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso.replace(" ", "T") + (iso.endsWith("Z") ? "" : "Z"));
  if (isNaN(d.getTime())) return iso;
  const now = Date.now();
  const diff = (now - d.getTime()) / 1000;
  if (diff < 60) return "방금 전";
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}일 전`;
  return d.toLocaleDateString("ko-KR");
}

