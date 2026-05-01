"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Camera, Refrigerator, ChefHat, ShoppingCart } from "lucide-react";

const TABS = [
  { href: "/", label: "홈", icon: Home },
  { href: "/scan", label: "스캔", icon: Camera },
  { href: "/ingredients", label: "재료", icon: Refrigerator },
  { href: "/recipes", label: "레시피", icon: ChefHat },
  { href: "/shopping", label: "장보기", icon: ShoppingCart },
] as const;

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-1/2 z-50 w-full max-w-screen-sm -translate-x-1/2 border-t border-gray-200 bg-white/95 backdrop-blur"
      style={{ paddingBottom: "var(--safe-bottom)" }}
    >
      <ul className="grid grid-cols-5">
        {TABS.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                className={`flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors ${
                  active ? "text-brand" : "text-gray-500"
                }`}
              >
                <Icon size={20} strokeWidth={active ? 2.4 : 1.8} />
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
