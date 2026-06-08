"use client";

/**
 * 클라이언트 컴포넌트
 * - 상단 중요 항목 섹션 (important=true, 정렬/검색/필터 미적용 고정)
 * - 검색 입력 (제목+요약+출처+태그 부분일치, 200ms 디바운스)
 * - 정렬 드롭다운 (7종: recent/oldest/importance/relevance/title/source/topic)
 * - 토픽 필터 탭
 * - URL 동기화: ?q= / ?sort= / ?topic=
 */

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { SearchIcon, StarIcon } from "lucide-react";

import { PostCard } from "./PostCard";
import { Input } from "@/components/ui/input";
import { sortPosts, SORT_OPTIONS, type SortKey } from "@/lib/sort";
import type { NotionPost } from "@/types/notion";

interface PostsSectionProps {
  posts: NotionPost[];
  topics: string[];
}

// 부분일치 검색 (대소문자/공백 무시)
function matchesQuery(post: NotionPost, q: string): boolean {
  if (!q.trim()) return true;
  const lower = q.toLowerCase();
  return (
    post.title.toLowerCase().includes(lower) ||
    post.summary.toLowerCase().includes(lower) ||
    post.source.toLowerCase().includes(lower) ||
    post.tags.some((t) => t.toLowerCase().includes(lower))
  );
}

export function PostsSection({ posts, topics }: PostsSectionProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // URL에서 초기값 읽기
  const initialQuery = searchParams.get("q") ?? "";
  const initialSort = (searchParams.get("sort") as SortKey) ?? "recent";
  const initialTopic = searchParams.get("topic") ?? "";

  const [inputValue, setInputValue] = useState(initialQuery);
  const [query, setQuery] = useState(initialQuery);
  const [sortKey, setSortKey] = useState<SortKey>(initialSort);
  const [selectedTopic, setSelectedTopic] = useState(initialTopic);

  // 디바운스: 200ms 후 query 적용 + URL 동기화
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleQueryChange(value: string) {
    setInputValue(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setQuery(value);
      updateUrl({ q: value, sort: sortKey, topic: selectedTopic });
    }, 200);
  }

  function handleSortChange(key: SortKey) {
    setSortKey(key);
    updateUrl({ q: query, sort: key, topic: selectedTopic });
  }

  function handleTopicSelect(topic: string) {
    setSelectedTopic(topic);
    updateUrl({ q: query, sort: sortKey, topic });
  }

  function updateUrl({ q, sort, topic }: { q: string; sort: SortKey; topic: string }) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (sort && sort !== "recent") params.set("sort", sort);
    if (topic) params.set("topic", topic);
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // 중요 항목 분리 (정렬/검색/필터 영향 없음, 항상 상단 고정)
  const importantPosts = posts.filter((p) => p.important);

  // 일반 목록: 중요 항목 제외 → 토픽 필터 → 검색 → 정렬
  const normalPosts = posts.filter((p) => !p.important);
  const topicFiltered = selectedTopic
    ? normalPosts.filter((p) => p.topic === selectedTopic)
    : normalPosts;
  const searchFiltered = topicFiltered.filter((p) => matchesQuery(p, query));
  const sortedPosts = sortPosts(searchFiltered, sortKey, query);

  // 검색어/정렬 활성 여부
  const hasSearch = query.trim().length > 0;
  const hasSortActive = sortKey !== "recent";

  return (
    <div>
      {/* ─── 중요 항목 섹션 ─── */}
      {importantPosts.length > 0 && (
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <StarIcon className="w-5 h-5 text-yellow-500" />
            <h2 className="text-base font-bold">오늘의 중요 항목</h2>
            <span className="text-xs text-muted-foreground">
              ({importantPosts.length}개)
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {importantPosts.map((post) => (
              <PostCard key={post.id} post={post} highlighted />
            ))}
          </div>
          {/* 구분선 */}
          <div className="mt-10 border-t" />
        </section>
      )}

      {/* ─── 검색 + 정렬 컨트롤 ─── */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        {/* 검색 입력 */}
        <div className="relative flex-1 min-w-0">
          <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <Input
            type="search"
            placeholder="제목, 요약, 출처, 태그 검색..."
            aria-label="포스트 검색"
            value={inputValue}
            onChange={(e) => handleQueryChange(e.target.value)}
            className="pl-8"
          />
        </div>

        {/* 정렬 드롭다운 */}
        <select
          value={sortKey}
          onChange={(e) => handleSortChange(e.target.value as SortKey)}
          aria-label="정렬 기준"
          className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring transition-colors text-foreground"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* ─── 토픽 필터 탭 ─── */}
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

      {/* ─── 일반 글 목록 ─── */}
      {sortedPosts.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          {hasSearch ? (
            <>
              <p className="text-lg">
                &ldquo;{query}&rdquo; 검색 결과가 없습니다.
              </p>
              <button
                onClick={() => handleQueryChange("")}
                className="mt-3 text-sm underline hover:text-foreground"
              >
                검색 초기화
              </button>
            </>
          ) : (
            <>
              <p className="text-lg">해당 토픽의 글이 없습니다.</p>
              <button
                onClick={() => handleTopicSelect("")}
                className="mt-3 text-sm underline hover:text-foreground"
              >
                전체 보기
              </button>
            </>
          )}
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground mb-4">
            {selectedTopic ? `${selectedTopic} · ` : ""}
            {hasSearch ? `"${query}" 검색 · ` : ""}
            {hasSortActive
              ? `${SORT_OPTIONS.find((o) => o.value === sortKey)?.label} · `
              : ""}
            총 {sortedPosts.length}개
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {sortedPosts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
