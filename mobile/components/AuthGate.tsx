"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const PUBLIC_PATHS = ["/login"];

/**
 * 미인증 사용자를 /login으로 보내고, 이미 로그인된 사용자가 /login으로 가면
 * 홈으로 되돌립니다. localStorage 동기 호출이 SSR에서 문제 안 일으키도록
 * 마운트 후에만 분기 처리합니다.
 */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthed, ready } = useAuth();
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));

  useEffect(() => {
    if (!ready) return;
    if (!isAuthed && !isPublic) router.replace("/login");
    if (isAuthed && isPublic) router.replace("/");
  }, [ready, isAuthed, isPublic, router]);

  // 첫 렌더(SSR 또는 ready 전)는 살짝 빈 상태로. 인증 필요한 페이지가
  // 잠깐이라도 데이터를 호출하지 않게.
  if (!ready) return null;
  if (!isAuthed && !isPublic) return null;
  return <>{children}</>;
}
