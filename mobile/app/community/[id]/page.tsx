"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ChevronLeft, Heart, MessageCircle, Star, Trash2, ChefHat, Send,
} from "lucide-react";
import {
  api, AuthRequired, absoluteUrl, ModerationBlocked,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Post, PostComment } from "@/lib/types";

export default function PostDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const postId = Number(params.id);
  const { user } = useAuth();

  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<PostComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [posting, setPosting] = useState(false);
  const [warning, setWarning] = useState<{ count: number; limit: number; deleted: boolean } | null>(null);

  useEffect(() => {
    if (!postId) return;
    Promise.all([api.getPost(postId), api.listComments(postId)])
      .then(([p, c]) => {
        setPost(p);
        setComments(c);
      })
      .catch((e) => {
        if (e instanceof AuthRequired) return;
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => setLoading(false));
  }, [postId]);

  async function onLike() {
    if (!post) return;
    const optimistic = {
      ...post,
      my_liked: !post.my_liked,
      like_count: post.like_count + (post.my_liked ? -1 : 1),
    };
    setPost(optimistic);
    try {
      const r = await api.toggleLike(post.id);
      setPost({ ...post, my_liked: r.liked, like_count: r.like_count });
    } catch {
      setPost(post);
    }
  }

  async function onSubmitComment(e: React.FormEvent) {
    e.preventDefault();
    if (!post || posting) return;
    const text = draft.trim();
    if (!text) return;
    setPosting(true);
    setError(null);
    setWarning(null);
    try {
      const c = await api.addComment(post.id, text);
      setComments([...comments, c]);
      setPost({ ...post, comment_count: post.comment_count + 1 });
      setDraft("");
    } catch (e) {
      if (e instanceof AuthRequired) return;
      if (e instanceof ModerationBlocked) {
        setWarning({
          count: e.payload.warning_count,
          limit: e.payload.warning_limit,
          deleted: e.payload.account_deleted,
        });
        if (e.payload.account_deleted) {
          setTimeout(() => router.replace("/login"), 2500);
        }
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setPosting(false);
    }
  }

  async function onDeleteComment(c: PostComment) {
    if (!post) return;
    if (!confirm("댓글을 삭제할까요?")) return;
    try {
      await api.deleteComment(c.id);
      setComments(comments.filter((x) => x.id !== c.id));
      setPost({ ...post, comment_count: Math.max(0, post.comment_count - 1) });
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }

  async function onDeletePost() {
    if (!post) return;
    if (!confirm("이 후기를 삭제할까요?\n첨부 사진도 함께 사라집니다.")) return;
    try {
      await api.deletePost(post.id);
      router.replace("/community");
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }

  if (loading) {
    return <p className="px-5 pt-20 text-center text-sm text-gray-500">불러오는 중...</p>;
  }
  if (error || !post) {
    return (
      <div className="px-5 pt-20 text-center">
        <p className="text-sm text-red-600">{error || "글을 찾을 수 없어요."}</p>
        <button
          onClick={() => router.replace("/community")}
          className="mt-4 text-sm text-brand underline"
        >
          목록으로
        </button>
      </div>
    );
  }

  return (
    <div className="px-5 pt-12 pb-6">
      <header className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => router.back()}
          className="-ml-2 flex h-10 w-10 items-center justify-center rounded-full text-gray-600 active:bg-gray-100"
        >
          <ChevronLeft size={22} />
        </button>
        {post.is_mine && (
          <button
            type="button"
            onClick={onDeletePost}
            className="flex h-10 items-center gap-1 rounded-full px-3 text-sm font-medium text-red-600 active:bg-red-50"
          >
            <Trash2 size={16} /> 삭제
          </button>
        )}
      </header>

      <article className="rounded-2xl border border-gray-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-soft text-sm font-semibold text-brand-dark">
              {(post.author_name || "?").charAt(0)}
            </div>
            <div>
              <p className="text-sm font-semibold">{post.author_name || "익명"}</p>
              <p className="text-[11px] text-gray-400">{formatDate(post.created_at)}</p>
            </div>
          </div>
          <Stars value={post.rating} />
        </div>

        {post.saved_recipe_name && (
          <div className="mb-3 inline-flex items-center gap-1 rounded-lg bg-brand-soft px-2 py-1 text-[12px] font-medium text-brand-dark">
            <ChefHat size={13} /> {post.saved_recipe_name}
          </div>
        )}

        <p className="mb-3 whitespace-pre-line text-sm text-gray-800">{post.content}</p>

        {post.images.length > 0 && (
          <div className="-mx-4 mb-3 flex gap-2 overflow-x-auto px-4">
            {post.images.map((src, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={i}
                src={absoluteUrl(src)}
                alt=""
                className="h-64 w-64 shrink-0 rounded-xl object-cover"
              />
            ))}
          </div>
        )}

        <div className="flex items-center gap-4 border-t border-gray-100 pt-3 text-sm">
          <button
            type="button"
            onClick={onLike}
            className={`flex items-center gap-1 ${
              post.my_liked ? "text-red-500" : "text-gray-500"
            }`}
          >
            <Heart size={18} fill={post.my_liked ? "currentColor" : "none"} />
            <span>{post.like_count}</span>
          </button>
          <div className="flex items-center gap-1 text-gray-500">
            <MessageCircle size={18} />
            <span>{post.comment_count}</span>
          </div>
        </div>
      </article>

      {/* 댓글 */}
      <section className="mt-5">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">
          댓글 {post.comment_count}
        </h2>

        {comments.length === 0 && post.comments_enabled && (
          <p className="rounded-xl bg-gray-50 p-3 text-center text-xs text-gray-500">
            첫 댓글을 남겨보세요.
          </p>
        )}
        {!post.comments_enabled && (
          <p className="rounded-xl bg-gray-50 p-3 text-center text-xs text-gray-500">
            작성자가 댓글을 비활성화한 게시글이에요.
          </p>
        )}

        <ul className="space-y-2">
          {comments.map((c) => (
            <li
              key={c.id}
              className="rounded-xl border border-gray-100 bg-white p-3"
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="text-xs font-semibold">
                  {c.author_name || "익명"}
                  <span className="ml-2 font-normal text-gray-400">
                    {formatDate(c.created_at)}
                  </span>
                </p>
                {user && c.user_id === user.id && (
                  <button
                    type="button"
                    onClick={() => onDeleteComment(c)}
                    className="text-[11px] text-gray-400 active:text-red-500"
                    aria-label="댓글 삭제"
                  >
                    삭제
                  </button>
                )}
              </div>
              <p className="whitespace-pre-line text-sm text-gray-800">{c.content}</p>
            </li>
          ))}
        </ul>

        {post.comments_enabled && (
          <form onSubmit={onSubmitComment} className="mt-3">
            <div className="flex gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                maxLength={1000}
                placeholder="댓글을 입력하세요"
                className="h-11 flex-1 rounded-2xl border border-gray-200 bg-white px-3 text-sm outline-none focus:border-brand"
              />
              <button
                type="submit"
                disabled={posting || !draft.trim()}
                className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand text-white disabled:opacity-50"
                aria-label="등록"
              >
                <Send size={16} />
              </button>
            </div>
            {warning && (
              <div className="mt-2 rounded-xl bg-red-50 p-2 text-xs">
                <p className="font-semibold text-red-800">
                  {warning.deleted
                    ? "경고 누적으로 계정이 삭제되었습니다."
                    : `경고 누적: ${warning.count} / ${warning.limit}`}
                </p>
              </div>
            )}
          </form>
        )}
      </section>
    </div>
  );
}

function Stars({ value }: { value: number }) {
  return (
    <div className="flex">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          size={16}
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
  return d.toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
