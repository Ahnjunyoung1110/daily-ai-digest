/**
 * 공통 포맷 유틸
 * - formatDate: 날짜 문자열 → 한국어 표기
 * - scoreToStars: 중요도 raw score → 별 개수(0~5)
 */

// 날짜 한국어 포맷 (null 또는 빈 값 → "")
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * 중요도 raw score(0~100+) → 별 개수(0~5)
 *
 * 임계값 기준 (스코어링 v2 분포):
 *   90+  → 5별 (최상위)
 *   70~89 → 4별
 *   55~69 → 3별
 *   40~54 → 2별
 *   1~39  → 1별
 *   0     → 0별 (별점 미표시 — Notion 미반영 항목 1별 오인 방지)
 */
export function scoreToStars(score: number): number {
  if (score >= 90) return 5;
  if (score >= 70) return 4;
  if (score >= 55) return 3;
  if (score >= 40) return 2;
  if (score > 0) return 1;
  return 0;
}
