import Link from "next/link";
import { CalendarIcon, StarIcon } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StarRating } from "@/components/StarRating";
import { formatDate } from "@/lib/format";
import type { NotionPost } from "@/types/notion";

interface PostCardProps {
  post: NotionPost;
  highlighted?: boolean; // 중요 섹션 카드 강조 스타일
}

// 글 목록 카드 컴포넌트
export function PostCard({ post, highlighted = false }: PostCardProps) {
  // "Daily AI Digest" 태그는 카드에서 제외 (모든 글에 공통으로 있어 의미 없음)
  const displayTags = post.tags.filter((t) => t !== "Daily AI Digest").slice(0, 3);

  return (
    <Link href={`/posts/${post.slug}`} className="block group h-full">
      <Card
        className={[
          "h-full flex flex-col transition-shadow hover:shadow-md",
          highlighted
            ? "border-yellow-400 dark:border-yellow-500 ring-1 ring-yellow-400/40 dark:ring-yellow-500/30"
            : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        <CardHeader className="pb-2">
          {/* 중요 배지 (강조 카드만) + 토픽 배지 + 출처 + 별점 */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {highlighted && (
              <Badge className="text-xs bg-yellow-400 text-yellow-900 dark:bg-yellow-500 dark:text-yellow-950 gap-1 border-0">
                <StarIcon className="w-3 h-3" />
                중요
              </Badge>
            )}
            {post.topic && post.topic !== "미분류" && (
              <Badge variant="secondary" className="text-xs">
                {post.topic}
              </Badge>
            )}
            {post.source && (
              <span className="text-xs text-muted-foreground truncate max-w-[140px]">
                {post.source}
              </span>
            )}
            <StarRating score={post.importance} size="sm" />
          </div>

          {/* 제목 */}
          <CardTitle className="text-sm leading-snug font-semibold group-hover:text-primary transition-colors line-clamp-3">
            {post.title || "제목 없음"}
          </CardTitle>
        </CardHeader>

        <CardContent className="pb-2 flex-1">
          {/* 한줄요약 */}
          {post.summary && (
            <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
              {post.summary}
            </p>
          )}
        </CardContent>

        <CardFooter className="flex items-center justify-between gap-2 pt-2 flex-wrap">
          {/* 날짜 (게시일 우선, 수집일 보조) */}
          <div className="flex flex-col gap-0.5">
            {post.publishedDate ? (
              <>
                {/* 게시일 — 주 날짜 */}
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <CalendarIcon className="w-3 h-3 flex-shrink-0" />
                  <span>게시 {formatDate(post.publishedDate)}</span>
                </div>
                {/* 수집일 — 보조 (들여쓰기) */}
                {post.collectedDate && (
                  <div className="pl-4 text-[11px] text-muted-foreground/60">
                    수집 {formatDate(post.collectedDate)}
                  </div>
                )}
              </>
            ) : (
              /* 게시일 없으면 수집일만 (기존 스타일) */
              post.collectedDate && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <CalendarIcon className="w-3 h-3 flex-shrink-0" />
                  <span>수집 {formatDate(post.collectedDate)}</span>
                </div>
              )
            )}
          </div>

          {/* 태그 */}
          {displayTags.length > 0 && (
            <div className="flex flex-wrap gap-1 ml-auto">
              {displayTags.map((tag) => (
                <Badge
                  key={tag}
                  variant="outline"
                  className="text-xs px-1.5 py-0 h-5"
                >
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </CardFooter>
      </Card>
    </Link>
  );
}
