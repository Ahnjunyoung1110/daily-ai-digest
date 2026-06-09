/**
 * 공통 포맷 유틸
 * - formatDate: 날짜 문자열 → 한국어 표기
 *
 * 별점 변환은 web/lib/stars.ts 참고 (상대 분위수 기반)
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
