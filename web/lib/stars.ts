/**
 * 별점 분위수 척도 유틸
 * - buildStarScale: importance 배열 → 분위수 기반 cutoff 계산
 * - starsFromScale: 단일 importance + 척도 → 별 개수(0~5)
 *
 * 분위수 배분 (표시 항목 집합 내 상대 평가):
 *   상위 10% (≥P90) → 5★
 *   ~30%  (≥P70) → 4★
 *   ~55%  (≥P45) → 3★
 *   ~80%  (≥P20) → 2★
 *   나머지          → 1★
 *   importance<=0   → 0★ (미표시 — Notion 미반영 항목 보호)
 */

export interface StarScale {
  /** [P90, P70, P45, P20] — 각각 5/4/3/2★ 하한값 */
  cutoffs: number[];
}

/**
 * importance 배열로부터 별점 척도(분위수 cutoff) 계산
 * importance<=0 값은 제외하고 오름차순 정렬 후 분위수 산출
 */
export function buildStarScale(importances: number[]): StarScale {
  const valid = importances.filter((v) => v > 0).sort((a, b) => a - b);
  if (valid.length === 0) return { cutoffs: [] };

  // q(p): 정렬 배열의 floor(p * len) 인덱스 값
  const q = (p: number) => valid[Math.floor(p * valid.length)];

  return {
    cutoffs: [q(0.9), q(0.7), q(0.45), q(0.2)],
  };
}

/**
 * 미리 계산된 척도로 importance → 별 개수(0~5) 변환
 * importance<=0 또는 척도 미구성 시 0 반환 (미표시)
 */
export function starsFromScale(importance: number, scale: StarScale): number {
  if (importance <= 0 || scale.cutoffs.length === 0) return 0;
  const [c5, c4, c3, c2] = scale.cutoffs;
  if (importance >= c5) return 5;
  if (importance >= c4) return 4;
  if (importance >= c3) return 3;
  if (importance >= c2) return 2;
  return 1;
}
