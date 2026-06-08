import Link from "next/link";
import { RssIcon } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

// 공통 헤더 — 사이트명 + 홈 링크 + 다크모드 토글
export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
      <div className="container mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 font-bold text-lg hover:text-primary transition-colors"
        >
          <RssIcon className="w-5 h-5" />
          <span>하루하루의 IT 이슈</span>
        </Link>

        {/* 헤더 우측: 다크모드 토글 */}
        <ThemeToggle />
      </div>
    </header>
  );
}
