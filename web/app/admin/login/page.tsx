/**
 * 관리자 로그인 페이지
 * 비번 입력 폼 → POST /admin/login
 */

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "관리자 로그인",
  robots: { index: false, follow: false },
};

interface LoginPageProps {
  searchParams: Promise<{ error?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const hasError = params.error === "1";

  return (
    <main className="container mx-auto max-w-sm px-4 py-20">
      <div className="border rounded-lg p-8 bg-card text-card-foreground shadow-sm">
        <h1 className="text-xl font-bold mb-2">관리자 로그인</h1>
        <p className="text-sm text-muted-foreground mb-6">
          관리자 비밀번호를 입력하세요.
        </p>

        <form method="POST" action="/api/admin/login" className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="password" className="text-sm font-medium">
              비밀번호
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              autoFocus
              autoComplete="current-password"
              placeholder="관리자 비밀번호"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring transition-colors"
            />
          </div>

          {hasError && (
            <p className="text-sm text-destructive" role="alert">
              비밀번호가 올바르지 않습니다.
            </p>
          )}

          <button
            type="submit"
            className="w-full h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            로그인
          </button>
        </form>
      </div>
    </main>
  );
}
