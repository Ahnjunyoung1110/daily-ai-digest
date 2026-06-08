/**
 * 관리자 대시보드 (읽기 전용)
 * - 인증: httpOnly 쿠키 admin_auth 검증 → 없으면 로그인 리다이렉트
 * - 데이터: getAllPosts() — 번역필요 포함 전체
 * - 내용: 요약 카드, 토픽/출처 분포, 번역필요 목록, 중요 항목 목록
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import { getAllPosts } from "@/lib/notion";
import type { NotionPost } from "@/types/notion";

export const metadata: Metadata = {
  title: "관리자 대시보드",
  robots: { index: false, follow: false },
};

// ISR 비활성화 (관리자 페이지는 항상 최신 데이터)
export const revalidate = 0;

const COOKIE_NAME = "admin_auth";

// 인증 검증 (쿠키값 == ADMIN_PASSWORD)
async function checkAuth(): Promise<boolean> {
  const adminPassword = process.env.ADMIN_PASSWORD;
  if (!adminPassword) return false;
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  return token === adminPassword;
}

// 배열 → 카운트맵 (내림차순 정렬)
function countBy(items: string[]): [string, number][] {
  const map: Record<string, number> = {};
  for (const item of items) {
    map[item] = (map[item] ?? 0) + 1;
  }
  return Object.entries(map).sort((a, b) => b[1] - a[1]);
}

// 최근 수집일 포맷
function formatDate(d: string | null): string {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function AdminPage() {
  const authed = await checkAuth();
  if (!authed) {
    redirect("/admin/login");
  }

  const posts = await getAllPosts();

  // 집계
  const total = posts.length;
  const completedCount = posts.filter((p) => p.status === "수집완료").length;
  const needsTranslationCount = posts.filter((p) => p.status === "번역필요").length;
  const importantCount = posts.filter((p) => p.important).length;

  const sortedByDate = [...posts].sort((a, b) => {
    const aD = a.collectedDate ?? "";
    const bD = b.collectedDate ?? "";
    return bD.localeCompare(aD);
  });
  const latestDate = sortedByDate[0]?.collectedDate ?? null;

  const topicCounts = countBy(posts.map((p) => p.topic));
  const sourceCounts = countBy(posts.map((p) => p.source).filter(Boolean)).slice(0, 10);
  const needsTranslation = posts.filter((p) => p.status === "번역필요");
  const importantPosts = posts.filter((p) => p.important);

  return (
    <main className="container mx-auto max-w-5xl px-4 py-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">관리자 대시보드</h1>
          <p className="text-sm text-muted-foreground mt-1">읽기 전용 · Notion DB 현황</p>
        </div>
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground underline"
        >
          ← 홈으로
        </Link>
      </div>

      {/* 요약 카드 4종 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard label="전체 항목" value={total} />
        <StatCard label="수집완료" value={completedCount} />
        <StatCard label="번역필요" value={needsTranslationCount} highlight={needsTranslationCount > 0} />
        <StatCard label="중요 표시" value={importantCount} highlight={importantCount > 0} />
      </div>

      <p className="text-xs text-muted-foreground mb-8">
        최근 수집일: {formatDate(latestDate)}
      </p>

      {/* 중요 항목 상태 */}
      <Section title={`중요 항목 (${importantCount}개)`}>
        {importantPosts.length === 0 ? (
          <p className="text-sm text-muted-foreground">중요 항목 없음</p>
        ) : (
          <div className="space-y-2">
            {importantPosts.map((p) => (
              <AdminRow key={p.id} post={p} />
            ))}
          </div>
        )}
        {importantCount < 3 || importantCount > 5 ? (
          <p className="mt-3 text-xs text-destructive">
            ⚠️ 중요 항목은 3~5개여야 합니다. 현재 {importantCount}개.
            다음 Notion 동기화 시 자동 조정됩니다.
          </p>
        ) : null}
      </Section>

      {/* 번역 필요 목록 */}
      <Section title={`번역 필요 (${needsTranslationCount}개)`}>
        {needsTranslation.length === 0 ? (
          <p className="text-sm text-muted-foreground">모두 번역 완료</p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {needsTranslation.map((p) => (
              <AdminRow key={p.id} post={p} />
            ))}
          </div>
        )}
      </Section>

      {/* 토픽별 분포 */}
      <Section title="토픽별 분포">
        <DistributionList items={topicCounts} total={total} />
      </Section>

      {/* 출처별 분포 (상위 10) */}
      <Section title="출처별 분포 (상위 10)">
        <DistributionList items={sourceCounts} total={total} />
      </Section>
    </main>
  );
}

// ── 서브 컴포넌트 ──

function StatCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div className="border rounded-lg p-4 bg-card">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? "text-destructive" : ""}`}>
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-base font-semibold mb-3 border-b pb-2">{title}</h2>
      {children}
    </section>
  );
}

function AdminRow({ post }: { post: NotionPost }) {
  return (
    <div className="flex items-start gap-3 py-1.5 text-sm">
      <div className="flex-1 min-w-0">
        <a
          href={post.link ?? `/posts/${post.slug}`}
          target={post.link ? "_blank" : undefined}
          rel={post.link ? "noopener noreferrer" : undefined}
          className="font-medium hover:text-primary transition-colors line-clamp-1"
        >
          {post.title || "제목 없음"}
        </a>
        <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground flex-wrap">
          {post.source && <span>{post.source}</span>}
          {post.topic && post.topic !== "미분류" && <span>· {post.topic}</span>}
          {post.collectedDate && <span>· {formatDate(post.collectedDate)}</span>}
          {post.importance > 0 && (
            <span className="text-yellow-600 dark:text-yellow-400">
              · 중요도 {post.importance}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function DistributionList({ items, total }: { items: [string, number][]; total: number }) {
  if (items.length === 0) return <p className="text-sm text-muted-foreground">데이터 없음</p>;
  return (
    <div className="space-y-2">
      {items.map(([label, count]) => {
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <div key={label} className="flex items-center gap-3 text-sm">
            <span className="w-28 shrink-0 truncate text-muted-foreground">{label}</span>
            <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary/60"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground w-12 text-right shrink-0">
              {count}개 ({pct}%)
            </span>
          </div>
        );
      })}
    </div>
  );
}
