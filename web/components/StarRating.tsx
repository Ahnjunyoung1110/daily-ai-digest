import { StarIcon } from "lucide-react";
import { scoreToStars } from "@/lib/format";

interface StarRatingProps {
  score: number;
  size?: "sm" | "md";
}

// 중요도 별점 컴포넌트 (0별이면 미표시)
export function StarRating({ score, size = "sm" }: StarRatingProps) {
  const stars = scoreToStars(score);

  // 0별 = 미표시 (Notion 미반영 항목 보호)
  if (stars === 0) return null;

  const iconClass = size === "md" ? "w-4 h-4" : "w-3 h-3";

  return (
    <span
      role="img"
      aria-label={`중요도 ${stars}/5`}
      className="inline-flex items-center gap-0.5"
    >
      {Array.from({ length: 5 }, (_, i) => (
        <StarIcon
          key={i}
          className={[
            iconClass,
            i < stars
              ? "text-yellow-500 dark:text-yellow-400 fill-current"
              : "text-muted-foreground/30",
          ].join(" ")}
        />
      ))}
    </span>
  );
}
