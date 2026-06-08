"use client";

/**
 * 클라이언트 컴포넌트 — 토픽 필터 탭 + 글 카드 그리드
 * useSearchParams 사용으로 Suspense 경계 필요 (app/page.tsx 참고)
 */
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { PostCard } from "./PostCard";
import type { NotionPost } from "@/types/notion";

interface PostsSectionProps {
  posts: NotionPost[];
  topics: string[];
}

export function PostsSection({ posts, topics }: PostsSectionProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const selectedTopic = searchParams.get("topic") ?? "";

  // 토픽 선택 → URL ?topic=xxx 동기화
  function handleTopicSelect(topic: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (topic) {
      params.set("topic", topic);
    } else {
      params.delete("topic");
    }
    const query = params.toString();
    router.push(query ? `${pathname}?${query}` : pathname);
  }

  // 클라이언트 사이드 필터링
  const filteredPosts = selectedTopic
    ? posts.filter((p) => p.topic === selectedTopic)
    : posts;

  return (
    <div>
      {/* 토픽 필터 탭 */}
      <div className="flex flex-wrap gap-2 mb-8">
        <button
          onClick={() => handleTopicSelect("")}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            !selectedTopic
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/70"
          }`}
        >
          전체
        </button>
        {topics.map((topic) => (
          <button
            key={topic}
            onClick={() => handleTopicSelect(topic)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              selectedTopic === topic
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {topic}
          </button>
        ))}
      </div>

      {/* 글 목록 */}
      {filteredPosts.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <p className="text-lg">해당 토픽의 글이 없습니다.</p>
          <button
            onClick={() => handleTopicSelect("")}
            className="mt-3 text-sm underline hover:text-foreground"
          >
            전체 보기
          </button>
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground mb-4">
            {selectedTopic ? `${selectedTopic} ` : ""}총 {filteredPosts.length}개
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPosts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
