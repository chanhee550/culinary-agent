"use client";

import { useEffect, useRef, useState } from "react";
import { ChefHat } from "lucide-react";
import { api, AuthRequired } from "@/lib/api";
import { saveAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";

type Mode = "login" | "register";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (resp: { credential: string }) => void;
            auto_select?: boolean;
            ux_mode?: "popup" | "redirect";
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: { theme?: string; size?: string; width?: number; text?: string; shape?: string; locale?: string }
          ) => void;
        };
      };
    };
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const GIS_SCRIPT = "https://accounts.google.com/gsi/client";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [googleReady, setGoogleReady] = useState(false);
  const googleBtnRef = useRef<HTMLDivElement | null>(null);

  // GIS 스크립트 로드 + 버튼 렌더
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return; // 클라이언트ID 미설정이면 Google 버튼 숨김

    const onLoad = () => {
      if (!window.google || !googleBtnRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (resp) => {
          setError(null);
          setSubmitting(true);
          try {
            const r = await api.googleLogin(resp.credential);
            saveAuth(r.access_token, r.user);
            router.replace("/");
          } catch (e) {
            setError(parseError(e, "Google 로그인 실패"));
          } finally {
            setSubmitting(false);
          }
        },
        ux_mode: "popup",
      });
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: "outline",
        size: "large",
        width: 320,
        text: "continue_with",
        shape: "pill",
        locale: "ko",
      });
      setGoogleReady(true);
    };

    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SCRIPT}"]`);
    if (existing) {
      if (window.google) onLoad();
      else existing.addEventListener("load", onLoad);
    } else {
      const s = document.createElement("script");
      s.src = GIS_SCRIPT;
      s.async = true;
      s.defer = true;
      s.addEventListener("load", onLoad);
      document.head.appendChild(s);
    }
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      const r =
        mode === "login"
          ? await api.login(email.trim().toLowerCase(), password)
          : await api.register(email.trim().toLowerCase(), password, displayName.trim());
      saveAuth(r.access_token, r.user);
      router.replace("/");
    } catch (e) {
      setError(parseError(e, mode === "login" ? "로그인 실패" : "회원가입 실패"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="px-5 pt-14">
      <header className="mb-8 flex flex-col items-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-soft">
          <ChefHat className="text-brand-dark" size={28} />
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Culinary Agent</h1>
        <p className="text-sm text-gray-500">
          {mode === "login" ? "다시 오신 걸 환영해요" : "냉장고를 정리해볼까요"}
        </p>
      </header>

      <div className="mb-5 flex rounded-2xl bg-gray-100 p-1">
        <ModeTab active={mode === "login"} onClick={() => setMode("login")}>
          로그인
        </ModeTab>
        <ModeTab active={mode === "register"} onClick={() => setMode("register")}>
          회원가입
        </ModeTab>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {mode === "register" && (
          <Field label="닉네임">
            <input
              type="text"
              required
              autoComplete="nickname"
              maxLength={40}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="앱에서 표시될 이름"
              className={inputCls}
            />
          </Field>
        )}
        <Field label="이메일">
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className={inputCls}
          />
        </Field>
        <Field label="비밀번호">
          <input
            type="password"
            required
            minLength={8}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={mode === "register" ? "8자 이상" : "비밀번호"}
            className={inputCls}
          />
        </Field>

        {error && (
          <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 h-12 w-full rounded-2xl bg-brand text-base font-semibold text-white transition-opacity active:opacity-90 disabled:opacity-50"
        >
          {submitting ? "처리 중..." : mode === "login" ? "로그인" : "가입하기"}
        </button>
      </form>

      {/* Google 로그인 영역 */}
      <div className="mt-6">
        <div className="my-4 flex items-center gap-3 text-xs text-gray-400">
          <div className="h-px flex-1 bg-gray-200" />
          또는
          <div className="h-px flex-1 bg-gray-200" />
        </div>
        {GOOGLE_CLIENT_ID ? (
          <div className="flex justify-center">
            <div ref={googleBtnRef} />
            {!googleReady && (
              <div className="h-12 w-full max-w-[320px] animate-pulse rounded-full bg-gray-100" />
            )}
          </div>
        ) : (
          <p className="text-center text-xs text-gray-400">
            Google 로그인이 비활성화되어 있습니다 (NEXT_PUBLIC_GOOGLE_CLIENT_ID 미설정)
          </p>
        )}
      </div>

      <p className="mt-8 text-center text-xs text-gray-400">
        가입 시 이메일 또는 Google 중 하나만 선택할 수 있어요
      </p>
    </div>
  );
}

function ModeTab({ active, onClick, children }: {
  active: boolean; onClick: () => void; children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-10 flex-1 rounded-xl text-sm font-medium transition-colors ${
        active ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"
      }`}
    >
      {children}
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-gray-600">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "h-12 w-full rounded-2xl border border-gray-200 bg-white px-4 text-base outline-none transition-colors focus:border-brand";

function parseError(e: unknown, fallback: string): string {
  if (e instanceof AuthRequired) return "인증이 만료되었습니다. 다시 로그인해주세요.";
  const msg = e instanceof Error ? e.message : String(e);
  if (msg.includes("email_already_exists_with_password_login"))
    return "이 이메일은 이미 비밀번호로 가입되어 있어요. 비밀번호로 로그인해주세요.";
  if (msg.includes("email_already_exists"))
    return "이미 가입된 이메일입니다. 로그인해주세요.";
  if (msg.includes("invalid_credentials"))
    return "이메일 또는 비밀번호가 올바르지 않아요.";
  if (msg.includes("invalid_google_token"))
    return "Google 인증 토큰이 유효하지 않습니다.";
  if (msg.includes("server_misconfigured"))
    return "서버 설정 문제: 관리자에게 문의해주세요.";
  return `${fallback}: ${msg}`;
}
