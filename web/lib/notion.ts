/**
 * Notion API 클라이언트 레이어
 * 실제 DB 스키마: src/daily_ai_digest/notion_sync.py make_page_properties() 기준
 * 프로퍼티 이름은 모두 한국어 리터럴 (제목/한줄요약/토픽/태그/출처/링크/수집일/게시일/상태/중요/중요도)
 */
import { Client, isFullPage } from "@notionhq/client";
import { buildStarScale, starsFromScale } from "@/lib/stars";
import type { NotionPost, NotionBlock } from "@/types/notion";

// 백엔드 notion_sync.py DEFAULT_DB_ID 와 동일
const DEFAULT_DB_ID = "376d18a9-aa84-80f6-8a9b-e26f880dd0aa";

// 환경변수 — NOTION_TOKEN은 백엔드 호환 fallback
function getEnv() {
  const apiKey = process.env.NOTION_API_KEY ?? process.env.NOTION_TOKEN;
  const dbId = process.env.NOTION_DATABASE_ID ?? DEFAULT_DB_ID;
  if (!apiKey) {
    throw new Error("NOTION_API_KEY 환경변수가 설정되지 않았습니다.");
  }
  return { apiKey, dbId };
}

// Notion 클라이언트 싱글톤
let _client: Client | null = null;
function getClient(): Client {
  if (!_client) {
    const { apiKey } = getEnv();
    _client = new Client({ auth: apiKey });
  }
  return _client;
}

// slug(대시 없는 ID) → UUID 형식(대시 포함)으로 변환
function withDashes(slug: string): string {
  const s = slug.replace(/-/g, "");
  return `${s.slice(0, 8)}-${s.slice(8, 12)}-${s.slice(12, 16)}-${s.slice(16, 20)}-${s.slice(20)}`;
}

// UUID → slug (대시 제거)
function withoutDashes(id: string): string {
  return id.replace(/-/g, "");
}

// rich_text 배열 → 순수 텍스트 (백엔드 _plain_text 패턴 참고)
function extractRichText(richText: unknown[]): string {
  return (
    richText as Array<{ plain_text?: string; text?: { content?: string } }>
  )
    .map((t) => t.plain_text ?? t.text?.content ?? "")
    .join("");
}

// Notion 페이지 프로퍼티 → NotionPost 매핑
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapPage(page: { id: string; properties: Record<string, any> }): NotionPost {
  const props = page.properties;

  // 제목 (title 타입)
  const title = extractRichText(props["제목"]?.title ?? []);

  // 한줄요약 (rich_text 타입)
  const summary = extractRichText(props["한줄요약"]?.rich_text ?? []);

  // 토픽 (select 타입) — 없으면 "미분류"
  const topic: string = props["토픽"]?.select?.name ?? "미분류";

  // 태그 (multi_select 타입)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tags: string[] = (props["태그"]?.multi_select ?? []).map((t: any) => t.name as string);

  // 출처 (select 타입)
  const source: string = props["출처"]?.select?.name ?? "";

  // 링크 (url 타입)
  const link: string | null = props["링크"]?.url ?? null;

  // 수집일 (date 타입) — YYYY-MM-DD
  const collectedDate: string | null = props["수집일"]?.date?.start ?? null;

  // 게시일 (date 타입) — Notion DB 업로드일. 백엔드 미반영 시 null
  const publishedDate: string | null = props["게시일"]?.date?.start ?? null;

  // Canonical Key (rich_text 타입) — 고유 식별자
  const canonicalKey = extractRichText(props["Canonical Key"]?.rich_text ?? []);

  // 중요 (checkbox 타입) — 상단 강조 섹션 표시용
  const important: boolean = props["중요"]?.checkbox ?? false;

  // 중요도 (number 타입) — 숫자 기준 정렬용 (Notion DB 미반영 시 0으로 안전 처리)
  const importance: number = props["중요도"]?.number ?? 0;

  // 상태 (select 타입) — 관리자 대시보드용
  const status: string = props["상태"]?.select?.name ?? "";

  return {
    id: page.id,
    slug: withoutDashes(page.id),
    title,
    summary,
    topic,
    tags,
    source,
    link,
    collectedDate,
    publishedDate,
    canonicalKey,
    important,
    importance,
    stars: 0, // 개별 매핑 시점 미정 — queryPosts에서 코퍼스 기준으로 주입
    status,
  };
}

/**
 * Notion DB 쿼리 공통 헬퍼 (페이지네이션 포함, 최대 500개)
 * statusFilter가 없으면 전체 조회 (관리자용)
 */
async function queryPosts(statusFilter?: string): Promise<NotionPost[]> {
  const { dbId } = getEnv();
  const client = getClient();
  const posts: NotionPost[] = [];
  let cursor: string | undefined = undefined;

  do {
    const response = await client.databases.query({
      database_id: dbId,
      ...(statusFilter
        ? {
            filter: {
              property: "상태",
              select: { equals: statusFilter },
            },
          }
        : {}),
      sorts: [{ property: "수집일", direction: "descending" }],
      page_size: 100,
      ...(cursor ? { start_cursor: cursor } : {}),
    });

    for (const page of response.results) {
      if (isFullPage(page)) {
        posts.push(mapPage(page));
      }
    }

    cursor = response.has_more ? (response.next_cursor ?? undefined) : undefined;
  } while (cursor && posts.length < 500);

  // 코퍼스 전체 기준 상대 분위수로 별 개수 주입
  const scale = buildStarScale(posts.map((p) => p.importance));
  posts.forEach((p) => {
    p.stars = starsFromScale(p.importance, scale);
  });

  return posts;
}

/**
 * 발행된 글 목록 조회
 * 필터: 상태 = "수집완료"
 * 정렬: 수집일 내림차순 (최신순)
 * 최대 500개 (페이지네이션 포함)
 */
export async function getPosts(): Promise<NotionPost[]> {
  return queryPosts("수집완료");
}

/**
 * 전체 글 목록 조회 (관리자 대시보드용)
 * 필터 없음 — 번역필요 포함 전체
 * 정렬: 수집일 내림차순
 */
export async function getAllPosts(): Promise<NotionPost[]> {
  return queryPosts();
}

/**
 * slug(페이지 ID, 대시 없음)로 단일 글 조회
 * pages.retrieve API 1콜 — 레이트리밋 절약
 */
export async function getPostBySlug(slug: string): Promise<NotionPost | null> {
  const client = getClient();
  try {
    const page = await client.pages.retrieve({ page_id: withDashes(slug) });
    if (isFullPage(page)) {
      const post = mapPage(page);
      // 별점: 수집완료 전체 코퍼스 기준 동일 척도 적용
      // (목록과 상세 페이지 별 개수 일치 보장)
      const allPosts = await getPosts();
      const match = allPosts.find((p) => p.slug === slug);
      if (match) {
        // 코퍼스에서 찾으면 이미 계산된 stars 재사용
        post.stars = match.stars;
      } else {
        // 코퍼스 외 항목(번역필요 등)은 동일 척도로 직접 산출
        const scale = buildStarScale(allPosts.map((p) => p.importance));
        post.stars = starsFromScale(post.importance, scale);
      }
      return post;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * 페이지 블록 조회 (페이지네이션 포함)
 * 반환: NotionBlock[] — 렌더러에서 직접 사용
 */
export async function getPostBlocks(pageId: string): Promise<NotionBlock[]> {
  const client = getClient();
  const blocks: NotionBlock[] = [];
  let cursor: string | undefined = undefined;

  do {
    const response = await client.blocks.children.list({
      block_id: pageId,
      ...(cursor ? { start_cursor: cursor } : {}),
    });

    for (const block of response.results) {
      // 완전한 블록만 (type 프로퍼티가 있는 블록)
      if ("type" in block) {
        blocks.push(block as unknown as NotionBlock);
      }
    }

    cursor = response.has_more ? (response.next_cursor ?? undefined) : undefined;
  } while (cursor);

  return blocks;
}

/**
 * 글 목록에서 고유 토픽 추출 (가나다순 정렬)
 * "전체" 탭은 UI에서 별도 추가
 */
export function getTopics(posts: NotionPost[]): string[] {
  const topicSet = new Set(posts.map((p) => p.topic).filter(Boolean));
  return Array.from(topicSet).sort();
}
