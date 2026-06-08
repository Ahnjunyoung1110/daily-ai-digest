/**
 * Notion 블록 렌더러
 * 백엔드 make_page_blocks()가 생성하는 블록 타입 우선 지원:
 *   heading_2, paragraph, bulleted_list_item
 * 추가 지원: heading_1/3, numbered_list_item, code, image, quote, divider, callout
 */
import Image from "next/image";
import { Fragment } from "react";
import type { NotionBlock, RichTextItem } from "@/types/notion";

// rich_text 배열 → JSX (bold/italic/code/link 인라인 스타일 처리)
function renderRichText(richText: RichTextItem[]): React.ReactNode {
  if (!richText?.length) return null;

  return richText.map((item, i) => {
    const text = item.plain_text ?? item.text?.content ?? "";
    const a = item.annotations;

    // 인라인 스타일 적용 (우선순위: code > bold+italic > bold > italic > 기타)
    let content: React.ReactNode = text;
    if (a?.code) {
      content = (
        <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">
          {text}
        </code>
      );
    } else if (a?.bold && a?.italic) {
      content = (
        <strong>
          <em>{text}</em>
        </strong>
      );
    } else if (a?.bold) {
      content = <strong>{text}</strong>;
    } else if (a?.italic) {
      content = <em>{text}</em>;
    } else if (a?.strikethrough) {
      content = <del>{text}</del>;
    } else if (a?.underline) {
      content = <u>{text}</u>;
    }

    // 링크 래핑
    if (item.href) {
      return (
        <a
          key={i}
          href={item.href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary underline underline-offset-4 hover:opacity-70 transition-opacity"
        >
          {content}
        </a>
      );
    }

    return <Fragment key={i}>{content}</Fragment>;
  });
}

// 단일 블록 렌더러
function BlockRenderer({ block }: { block: NotionBlock }) {
  switch (block.type) {
    case "paragraph": {
      const rt = block.paragraph?.rich_text ?? [];
      // 빈 단락 → 수직 여백
      if (!rt.length || rt.every((t) => !(t.plain_text ?? t.text?.content))) {
        return <div className="h-3" />;
      }
      return (
        <p className="text-base leading-relaxed">{renderRichText(rt)}</p>
      );
    }

    case "heading_1": {
      const rt = block.heading_1?.rich_text ?? [];
      return (
        <h2 className="text-2xl font-bold mt-8 mb-3">
          {renderRichText(rt)}
        </h2>
      );
    }

    case "heading_2": {
      const rt = block.heading_2?.rich_text ?? [];
      return (
        <h3 className="text-xl font-semibold mt-6 mb-2 pb-1 border-b border-border">
          {renderRichText(rt)}
        </h3>
      );
    }

    case "heading_3": {
      const rt = block.heading_3?.rich_text ?? [];
      return (
        <h4 className="text-lg font-semibold mt-4 mb-1">
          {renderRichText(rt)}
        </h4>
      );
    }

    case "quote": {
      const rt = block.quote?.rich_text ?? [];
      return (
        <blockquote className="border-l-4 border-primary/40 pl-4 text-muted-foreground italic">
          {renderRichText(rt)}
        </blockquote>
      );
    }

    case "divider": {
      return <hr className="my-6 border-border" />;
    }

    case "callout": {
      const rt = block.callout?.rich_text ?? [];
      const icon = block.callout?.icon;
      return (
        <div className="flex gap-3 p-4 rounded-lg bg-muted">
          {icon?.type === "emoji" && (
            <span className="text-xl flex-shrink-0 leading-relaxed">
              {icon.emoji}
            </span>
          )}
          <div className="text-base leading-relaxed">{renderRichText(rt)}</div>
        </div>
      );
    }

    case "code": {
      const rt = block.code?.rich_text ?? [];
      const lang = block.code?.language ?? "";
      const code = rt.map((t) => t.plain_text ?? t.text?.content ?? "").join("");
      return (
        <div className="rounded-lg overflow-hidden border border-border">
          {lang && (
            <div className="bg-muted/60 px-4 py-1.5 text-xs text-muted-foreground font-mono border-b border-border">
              {lang}
            </div>
          )}
          <pre className="bg-muted/30 p-4 overflow-x-auto text-sm font-mono leading-relaxed">
            <code>{code}</code>
          </pre>
        </div>
      );
    }

    case "image": {
      const img = block.image;
      if (!img) return null;
      const url =
        img.type === "external" ? img.external?.url : img.file?.url;
      if (!url) return null;
      const captionText = (img.caption ?? [])
        .map((t) => t.plain_text ?? "")
        .join("");
      return (
        <figure className="my-4">
          {/* 이미지 원본 비율 유지 — width/height 0 + sizes 패턴 */}
          <Image
            src={url}
            alt={captionText || "이미지"}
            width={0}
            height={0}
            sizes="(max-width: 768px) 100vw, 700px"
            className="rounded-lg w-full h-auto"
            style={{ width: "100%", height: "auto" }}
          />
          {captionText && (
            <figcaption className="text-center text-sm text-muted-foreground mt-2">
              {captionText}
            </figcaption>
          )}
        </figure>
      );
    }

    default: {
      // 지원하지 않는 블록 타입 — 숨기지 않고 안내 표시
      return (
        <div className="border border-dashed border-border rounded-lg p-3 text-xs text-muted-foreground">
          지원하지 않는 블록: {block.type}
        </div>
      );
    }
  }
}

// 연속 list_item 그룹화 타입
type BlockGroup =
  | { kind: "single"; block: NotionBlock }
  | { kind: "bullet_list"; items: NotionBlock[] }
  | { kind: "numbered_list"; items: NotionBlock[] };

// 연속 bulleted_list_item / numbered_list_item → ul/ol로 그룹화
function groupBlocks(blocks: NotionBlock[]): BlockGroup[] {
  const groups: BlockGroup[] = [];
  let i = 0;
  while (i < blocks.length) {
    const block = blocks[i];
    if (block.type === "bulleted_list_item") {
      const items: NotionBlock[] = [];
      while (i < blocks.length && blocks[i].type === "bulleted_list_item") {
        items.push(blocks[i]);
        i++;
      }
      groups.push({ kind: "bullet_list", items });
    } else if (block.type === "numbered_list_item") {
      const items: NotionBlock[] = [];
      while (i < blocks.length && blocks[i].type === "numbered_list_item") {
        items.push(blocks[i]);
        i++;
      }
      groups.push({ kind: "numbered_list", items });
    } else {
      groups.push({ kind: "single", block });
      i++;
    }
  }
  return groups;
}

interface NotionRendererProps {
  blocks: NotionBlock[];
}

// Notion 블록 렌더러 메인 컴포넌트
export function NotionRenderer({ blocks }: NotionRendererProps) {
  if (!blocks.length) {
    return (
      <p className="text-muted-foreground text-sm">본문 내용이 없습니다.</p>
    );
  }

  const groups = groupBlocks(blocks);

  return (
    <div className="space-y-4">
      {groups.map((group, i) => {
        if (group.kind === "bullet_list") {
          return (
            <ul key={i} className="list-disc space-y-1.5 pl-6">
              {group.items.map((item) => (
                <li key={item.id} className="text-base leading-relaxed">
                  {renderRichText(item.bulleted_list_item?.rich_text ?? [])}
                </li>
              ))}
            </ul>
          );
        }

        if (group.kind === "numbered_list") {
          return (
            <ol key={i} className="list-decimal space-y-1.5 pl-6">
              {group.items.map((item) => (
                <li key={item.id} className="text-base leading-relaxed">
                  {renderRichText(item.numbered_list_item?.rich_text ?? [])}
                </li>
              ))}
            </ol>
          );
        }

        return <BlockRenderer key={group.block.id} block={group.block} />;
      })}
    </div>
  );
}
