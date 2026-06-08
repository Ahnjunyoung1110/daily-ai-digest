import Link from "next/link";
import { CalendarIcon } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { NotionPost } from "@/types/notion";

// 수집일 한국어 포맷
function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

interface PostCardProps {
  post: NotionPost;
}

// 글 목록 카드 컴포넌트
export function PostCard({ post }: PostCardProps) {
  // "Daily AI Digest" 태그는 카드에서 제외 (모든 글에 공통으로 있어 의미 없음)
  const displayTags = post.tags.filter((t) => t !== "Daily AI Digest").slice(0, 3);

  return (
    <Link href={`/posts/${post.slug}`} className="block group h-full">
      <Card className="h-full flex flex-col transition-shadow hover:shadow-md">
        <CardHeader className="pb-2">
          {/* 토픽 배지 + 출처 */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
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
          {/* 수집일 */}
          {post.collectedDate && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <CalendarIcon className="w-3 h-3 flex-shrink-0" />
              <span>{formatDate(post.collectedDate)}</span>
            </div>
          )}

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
