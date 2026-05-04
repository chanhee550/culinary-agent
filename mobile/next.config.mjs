import nextPWA from "next-pwa";

const withPWA = nextPWA({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 백엔드 직접 호출 시 CORS·키 노출 회피용 프록시. NEXT_PUBLIC_API_URL 미설정 시 동일 출처로 가정.
  async rewrites() {
    const target = process.env.BACKEND_URL;
    if (!target) return [];
    return [{ source: "/api/:path*", destination: `${target}/:path*` }];
  },
};

export default withPWA(nextConfig);
