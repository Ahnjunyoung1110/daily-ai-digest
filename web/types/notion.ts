// Notion 포스트 타입 정의
// 실제 스키마: src/daily_ai_digest/notion_sync.py make_page_properties() 기준
export interface NotionPost {
  id: string;            // 페이지 ID (대시 포함, UUID 형식)
  slug: string;          // URL slug (페이지 ID에서 대시 제거)
  title: string;         // 제목 (한국어 우선)
  summary: string;       // 한줄요약
  topic: string;         // 토픽 select (논문/깃허브/블로그/뉴스/토론/공지/아티클/커뮤니티/미분류)
  tags: string[];        // 태그 multi_select (Daily AI Digest + 출처 + 유형)
  source: string;        // 출처 select
  link: string | null;   // 원문 링크 url
  collectedDate: string | null; // 수집일 date (YYYY-MM-DD)
  canonicalKey: string;  // Canonical Key — 고유 식별자
}

// Notion rich_text 아이템
export interface RichTextItem {
  type?: string;
  text?: { content: string; link: { url: string } | null };
  annotations?: {
    bold: boolean;
    italic: boolean;
    strikethrough: boolean;
    underline: boolean;
    code: boolean;
    color: string;
  };
  plain_text?: string;
  href?: string | null;
}

// Notion 블록 타입 (주요 블록만 정의 — make_page_blocks() 기준 + 추가 지원)
export interface NotionBlock {
  id: string;
  type: string;
  has_children?: boolean;
  paragraph?: { rich_text: RichTextItem[] };
  heading_1?: { rich_text: RichTextItem[]; is_toggleable?: boolean };
  heading_2?: { rich_text: RichTextItem[]; is_toggleable?: boolean };
  heading_3?: { rich_text: RichTextItem[]; is_toggleable?: boolean };
  bulleted_list_item?: { rich_text: RichTextItem[] };
  numbered_list_item?: { rich_text: RichTextItem[] };
  code?: { rich_text: RichTextItem[]; language: string; caption?: RichTextItem[] };
  image?: {
    type: "external" | "file";
    external?: { url: string };
    file?: { url: string; expiry_time: string };
    caption?: RichTextItem[];
  };
  quote?: { rich_text: RichTextItem[] };
  callout?: {
    rich_text: RichTextItem[];
    icon?:
      | { type: "emoji"; emoji: string }
      | { type: "external"; external: { url: string } };
  };
  divider?: Record<string, never>;
}
