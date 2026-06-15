import type { Metadata, Viewport } from "next";
import "./globals.css";
import BottomNav from "@/components/BottomNav";
import AuthGate from "@/components/AuthGate";

export const metadata: Metadata = {
  title: "오셰 (O'CHEF)",
  description: "냉장고 속 재료를 관리하고 AI 레시피를 추천받으세요",
  manifest: "/manifest.json",
  applicationName: "O'CHEF",
  appleWebApp: {
    capable: true,
    title: "O'CHEF",
    statusBarStyle: "default",
  },
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/icon-192.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#10b981",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <main className="mx-auto min-h-dvh max-w-screen-sm pb-24">
          <AuthGate>{children}</AuthGate>
        </main>
        <BottomNav />
      </body>
    </html>
  );
}
