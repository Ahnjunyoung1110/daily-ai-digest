import { Suspense } from "react";
import { getPosts, getTopics } from "@/lib/notion";
import { PostsSection } from "@/components/PostsSection";

// ISR: 1분마다 재생성
export const revalidate = 60;

export default async function HomePage() {
  const posts = await getPosts();
  const topics = getTopics(posts);

  return (
    <main className="container mx-auto max-w-6xl px-4 py-8">
      {/* 히어로 섹션 */}
      <section className="text-center mb-10">
        <h1 className="text-3xl font-bold tracking-tight mb-3">
          하루하루의 IT 이슈
        </h1>
        <p className="text-muted-foreground text-base max-w-2xl mx-auto leading-relaxed">
          매일 AI · IT 관련 최신 이슈를 자동 수집하여 한국어로 요약한
          뉴스레터입니다.
        </p>
      </section>

      {/* 포스트 섹션 — useSearchParams 사용으로 Suspense 필요 */}
      <Suspense
        fallback={
          <div className="text-center py-16 text-muted-foreground">
            로딩 중...
          </div>
        }
      >
        <PostsSection posts={posts} topics={topics} />
      </Suspense>
    </main>
  );
}
