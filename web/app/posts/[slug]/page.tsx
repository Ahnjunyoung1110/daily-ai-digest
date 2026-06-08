import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeftIcon, ExternalLinkIcon, CalendarIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { NotionRenderer } from "@/components/NotionRenderer";
import { getPosts, getPostBySlug, getPostBlocks } from "@/lib/notion";
import type { Metadata } from "next";

// ISR: 1시간마다 재생성
export const revalidate = 3600;

interface PageProps {
  params: Promise<{ slug: string }>;
}

// 빌드 시 정적 경로 생성 — 최신 50개 제한 (빌드시간/레이트리밋 고려)
export async function generateStaticParams() {
  const posts = await getPosts();
  return posts.slice(0, 50).map((p) => ({ slug: p.slug }));
}

// OG 메타데이터 생성
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPostBySlug(slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.summary || undefined,
    openGraph: {
      title: post.title,
      description: post.summary || undefined,
      type: "article",
    },
  };
}

// 수집일 한국어 포맷
function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default async function PostPage({ params }: PageProps) {
  const { slug } = await params;

  // 글 정보와 전체 목록을 병렬 조회 (이전/다음 글 네비게이션용)
  const [post, posts] = await Promise.all([getPostBySlug(slug), getPosts()]);

  if (!post) notFound();

  // 블록 조회
  const blocks = await getPostBlocks(post.id);

  // 이전/다음 글 (수집일 내림차순 — 인접 글)
  // posts[0] = 최신, posts[n-1] = 오래된
  const idx = posts.findIndex((p) => p.slug === slug);
  const newerPost = idx > 0 ? posts[idx - 1] : null;     // 더 최신 (목록에서 위)
  const olderPost = idx < posts.length - 1 ? posts[idx + 1] : null; // 더 오래된

  // "Daily AI Digest" 태그 제외
  const displayTags = post.tags.filter((t) => t !== "Daily AI Digest");

  return (
    <main className="container mx-auto max-w-3xl px-4 py-8">
      {/* 뒤로가기 */}
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeftIcon className="w-4 h-4" />
          목록으로
        </Link>
      </div>

      {/* 글 헤더 */}
      <header className="mb-8">
        {/* 토픽 + 태그 배지 */}
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {post.topic && post.topic !== "미분류" && (
            <Badge variant="secondary">{post.topic}</Badge>
          )}
          {displayTags.slice(0, 5).map((tag) => (
            <Badge key={tag} variant="outline">
              {tag}
            </Badge>
          ))}
        </div>

        {/* 제목 */}
        <h1 className="text-2xl font-bold leading-snug mb-4">{post.title}</h1>

        {/* 메타 정보 */}
        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          {post.collectedDate && (
            <div className="flex items-center gap-1">
              <CalendarIcon className="w-4 h-4" />
              <span>{formatDate(post.collectedDate)}</span>
            </div>
          )}
          {post.source && <span>{post.source}</span>}
        </div>

        {/* 원문 바로가기 버튼 */}
        {post.link && (
          <div className="mt-4">
            <a
              href={post.link}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" size="sm" className="gap-2">
                <ExternalLinkIcon className="w-4 h-4" />
                원문 보기
              </Button>
            </a>
          </div>
        )}
      </header>

      {/* 본문 — Notion 블록 렌더러 */}
      <article>
        <NotionRenderer blocks={blocks} />
      </article>

      {/* 이전/다음 글 네비게이션 */}
      <nav className="mt-12 pt-8 border-t border-border">
        <div className="grid grid-cols-2 gap-6">
          {/* 왼쪽: 더 오래된 글 (이전) */}
          {olderPost ? (
            <div className="col-start-1">
              <p className="text-xs text-muted-foreground mb-1.5">← 이전 글</p>
              <Link
                href={`/posts/${olderPost.slug}`}
                className="text-sm font-medium hover:text-primary transition-colors line-clamp-2 leading-snug"
              >
                {olderPost.title}
              </Link>
            </div>
          ) : (
            <div />
          )}

          {/* 오른쪽: 더 최신 글 (다음) */}
          {newerPost ? (
            <div className="col-start-2 text-right">
              <p className="text-xs text-muted-foreground mb-1.5">다음 글 →</p>
              <Link
                href={`/posts/${newerPost.slug}`}
                className="text-sm font-medium hover:text-primary transition-colors line-clamp-2 leading-snug"
              >
                {newerPost.title}
              </Link>
            </div>
          ) : (
            <div />
          )}
        </div>
      </nav>
    </main>
  );
}
