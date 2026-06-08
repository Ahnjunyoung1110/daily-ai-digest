/**
 * 포스트 정렬 유틸
 * sortPosts(posts, sortKey, query) — 순수 함수, 사이드이펙트 없음
 *
 * 지원 정렬 키:
 *   recent     최신순 (수집일 desc) — 기본값
 *   oldest     오래된순 (수집일 asc)
 *   importance 중요도순 (중요도 number desc → 수집일 desc tiebreak)
 *   relevance  관련도순 (검색어 매치 가중치 desc → 수집일 desc tiebreak, 검색어 없으면 recent 폴백)
 *   title      제목순 (가나다 localeCompare ko)
 *   source     출처순 (localeCompare ko)
 *   topic      토픽순 (localeCompare ko → 수집일 desc tiebreak)
 *
 * 참고: 점수/인기순은 Notion DB에 숫자 필드 없어 미지원
 */

import type { NotionPost } from "@/types/notion";

export type SortKey =
  | "recent"
  | "oldest"
  | "importance"
  | "relevance"
  | "title"
  | "source"
  | "topic";

export const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "recent", label: "최신순" },
  { value: "oldest", label: "오래된순" },
  { value: "importance", label: "중요도순" },
  { value: "relevance", label: "관련도순" },
  { value: "title", label: "제목순" },
  { value: "source", label: "출처순" },
  { value: "topic", label: "토픽순" },
];

// 날짜 문자열 → 숫자 (없으면 0)
function dateNum(d: string | null): number {
  if (!d) return 0;
  return new Date(d).getTime() || 0;
}

// 관련도 점수: 제목 3점, 요약 2점, 출처 1점, 태그(개별) 1점
function relevanceScore(post: NotionPost, query: string): number {
  if (!query.trim()) return 0;
  const q = query.toLowerCase();
  let score = 0;
  if (post.title.toLowerCase().includes(q)) score += 3;
  if (post.summary.toLowerCase().includes(q)) score += 2;
  if (post.source.toLowerCase().includes(q)) score += 1;
  for (const tag of post.tags) {
    if (tag.toLowerCase().includes(q)) {
      score += 1;
      break; // 태그 다중 매치 방지
    }
  }
  return score;
}

export function sortPosts(
  posts: NotionPost[],
  sortKey: SortKey,
  query: string = ""
): NotionPost[] {
  const arr = [...posts];

  switch (sortKey) {
    case "recent":
      return arr.sort((a, b) => dateNum(b.collectedDate) - dateNum(a.collectedDate));

    case "oldest":
      return arr.sort((a, b) => dateNum(a.collectedDate) - dateNum(b.collectedDate));

    case "importance":
      return arr.sort((a, b) => {
        const diff = b.importance - a.importance;
        if (diff !== 0) return diff;
        return dateNum(b.collectedDate) - dateNum(a.collectedDate);
      });

    case "relevance": {
      // 검색어 없으면 최신순 폴백
      if (!query.trim()) {
        return arr.sort((a, b) => dateNum(b.collectedDate) - dateNum(a.collectedDate));
      }
      return arr.sort((a, b) => {
        const diff = relevanceScore(b, query) - relevanceScore(a, query);
        if (diff !== 0) return diff;
        return dateNum(b.collectedDate) - dateNum(a.collectedDate);
      });
    }

    case "title":
      return arr.sort((a, b) =>
        a.title.localeCompare(b.title, "ko", { sensitivity: "base" })
      );

    case "source":
      return arr.sort((a, b) =>
        a.source.localeCompare(b.source, "ko", { sensitivity: "base" })
      );

    case "topic":
      return arr.sort((a, b) => {
        const cmp = a.topic.localeCompare(b.topic, "ko", { sensitivity: "base" });
        if (cmp !== 0) return cmp;
        return dateNum(b.collectedDate) - dateNum(a.collectedDate);
      });

    default:
      return arr;
  }
}
