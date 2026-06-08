"""Notion sync core: raw collector JSON → Notion DB pages."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .ledger import canonical_key, mark_notion_page

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_DB_ID = "376d18a9-aa84-80f6-8a9b-e26f880dd0aa"
RATE_LIMIT_DELAY = 0.35
CANONICAL_KEY_PROP = "Canonical Key"

# 소문자 비교용 플레이스홀더 집합
_PLACEHOLDER_TITLES = {"없음", "최신 항목 없음", "no items", "none"}

_TYPE_MAP = {
    "paper": "논문",
    "repo": "깃허브",
    "blog": "블로그",
    "news": "뉴스",
    "discussion": "토론",
    "announcement": "공지",
    "article": "아티클",
    "community": "커뮤니티",
}

# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

def is_placeholder(title: str | None) -> bool:
    if not title or not title.strip():
        return True
    return title.strip().lower() in {p.lower() for p in _PLACEHOLDER_TITLES}


def map_type_to_korean(type_str: str | None) -> str:
    if not type_str:
        return "미분류"
    return _TYPE_MAP.get(type_str.lower(), type_str)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _split_rich_text(text: str, max_len: int = 1800) -> list[dict]:
    """text → Notion rich_text 블록 리스트 (각 청크 ≤ max_len)."""
    if not text:
        return []
    blocks = []
    while text:
        chunk = text[:max_len]
        text = text[max_len:]
        blocks.append({"type": "text", "text": {"content": chunk}})
    return blocks


def _plain_text(prop: dict | None) -> str:
    if not prop:
        return ""
    chunks = prop.get("rich_text") or prop.get("title") or []
    return "".join((c.get("plain_text") or c.get("text", {}).get("content") or "") for c in chunks)


def ensure_item_canonical_key(item: dict) -> str:
    key = item.get("canonical_key") or canonical_key(item)
    item["canonical_key"] = key
    return key

# ---------------------------------------------------------------------------
# Notion 프로퍼티 빌더
# ---------------------------------------------------------------------------

def make_page_properties(item: dict, meta: dict) -> dict:
    title = item.get("title_ko") or item.get("korean_title") or item.get("title") or ""
    summary = (
        item.get("summary_ko")
        or item.get("korean_summary")
        or item.get("key_summary_ko")
        or item.get("summary_candidate")
        or ""
    )
    source = item.get("source") or ""
    url = item.get("url") or ""
    item_type = item.get("type") or item.get("kind") or ""
    published = item.get("published") or meta.get("generated_at_kst", "")
    ckey = ensure_item_canonical_key(item) if url or title else ""

    date_part = published[:10] if published else None

    # 태그: Daily AI Digest + source + type
    tags: list[dict] = [{"name": "Daily AI Digest"}]
    if source:
        tags.append({"name": _truncate(source, 100)})
    if item_type:
        tags.append({"name": item_type})

    # 출처: item.source > URL host > unknown
    source_val = source
    if not source_val and url:
        parsed = urllib.parse.urlparse(url)
        source_val = parsed.netloc or "unknown"
    if not source_val:
        source_val = "unknown"

    props: dict[str, Any] = {
        "제목": {
            "title": [{"type": "text", "text": {"content": _truncate(title, 2000)}}]
        },
        "한줄요약": {
            "rich_text": _split_rich_text(_truncate(summary, 1800))
        },
        "상태": {
            "select": {"name": "수집완료"}
        },
        "태그": {
            "multi_select": tags
        },
        "출처": {
            "select": {"name": _truncate(source_val, 100)}
        },
        "링크": {
            "url": url or None
        },
    }

    if ckey:
        props[CANONICAL_KEY_PROP] = {
            "rich_text": [{"type": "text", "text": {"content": _truncate(ckey, 2000)}}]
        }

    if item_type:
        props["토픽"] = {"select": {"name": map_type_to_korean(item_type)}}

    if date_part:
        props["수집일"] = {"date": {"start": date_part}}

    return props


def _text_block(block_type: str, text: str) -> dict:
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": [{"type": "text", "text": {"content": text[:1900]}}]},
    }


def _bullets(values: list | str | None) -> list[dict]:
    if not values:
        return []
    if isinstance(values, str):
        values = [v.strip(" -•\t") for v in values.splitlines() if v.strip(" -•\t")]
    out = []
    for value in values[:8]:
        out.append(_text_block("bulleted_list_item", str(value)))
    return out


def make_page_blocks(item: dict) -> list[dict]:
    """Create a readable Notion item page, then preserve raw metadata."""
    ensure_item_canonical_key(item)
    original_title = item.get("title") or ""
    title_ko = item.get("title_ko") or item.get("korean_title") or original_title
    summary = (
        item.get("summary_ko")
        or item.get("korean_summary")
        or item.get("key_summary_ko")
        or item.get("summary_candidate")
        or ""
    )
    why = item.get("why_it_matters_ko") or item.get("why_it_matters") or ""
    action_items = item.get("action_items_ko") or item.get("check_points_ko") or []
    key_points = item.get("key_points_ko") or item.get("core_points_ko") or []

    blocks: list[dict] = []
    blocks.append(_text_block("heading_2", "핵심 정리"))
    if summary:
        blocks.append(_text_block("paragraph", str(summary)))
    blocks.extend(_bullets(key_points))

    if why:
        blocks.append(_text_block("heading_2", "왜 중요한가"))
        blocks.append(_text_block("paragraph", str(why)))

    if action_items:
        blocks.append(_text_block("heading_2", "확인/활용 포인트"))
        blocks.extend(_bullets(action_items))

    blocks.append(_text_block("heading_2", "원문 및 메타데이터"))
    meta_lines = []
    meta_pairs = [
        ("원문 제목", original_title),
        ("출처", item.get("source")),
        ("유형", item.get("type")),
        ("발행일", item.get("published")),
        ("점수", item.get("score")),
        ("Canonical Key", item.get("canonical_key")),
        ("링크", item.get("url")),
    ]
    for label, val in meta_pairs:
        if val is not None and val != "":
            meta_lines.append(f"{label}: {val}")
    for key in ("score_breakdown", "signals"):
        val = item.get(key)
        if val is not None:
            meta_lines.append(f"{key}: {json.dumps(val, ensure_ascii=False)}")
    raw_text = "\n".join(meta_lines)
    while raw_text:
        chunk = raw_text[:1800]
        raw_text = raw_text[1800:]
        blocks.append(_text_block("paragraph", chunk))
    return blocks

# ---------------------------------------------------------------------------
# Notion API
# ---------------------------------------------------------------------------

def _notion_request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = f"{NOTION_API_BASE}{path}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        raise RuntimeError(
            f"Notion API {method} {path} -> {e.code}: {body_bytes.decode('utf-8', errors='replace')}"
        ) from e


def ensure_database_schema(db_id: str, token: str) -> dict:
    """Ensure the DB has the Canonical Key rich_text property."""
    db = _notion_request("GET", f"/databases/{db_id}", token)
    props = db.get("properties", {})
    if CANONICAL_KEY_PROP in props:
        return {"changed": False, "property": CANONICAL_KEY_PROP, "type": props[CANONICAL_KEY_PROP].get("type")}
    _notion_request("PATCH", f"/databases/{db_id}", token, {"properties": {CANONICAL_KEY_PROP: {"rich_text": {}}}})
    return {"changed": True, "property": CANONICAL_KEY_PROP, "type": "rich_text"}


def query_existing_pages(db_id: str, token: str) -> tuple[dict[str, str], dict[str, str]]:
    """DB 전체 페이지를 페이지네이션으로 조회 → ({url: page_id}, {canonical_key: page_id})."""
    url_to_page: dict[str, str] = {}
    key_to_page: dict[str, str] = {}
    cursor = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = _notion_request("POST", f"/databases/{db_id}/query", token, body)
        for page in resp.get("results", []):
            page_id = page.get("id")
            properties = page.get("properties", {})
            page_url = properties.get("링크", {}).get("url")
            page_key = _plain_text(properties.get(CANONICAL_KEY_PROP))
            if page_url and page_id:
                url_to_page[page_url] = page_id
            if page_key and page_id:
                key_to_page[page_key] = page_id
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        time.sleep(RATE_LIMIT_DELAY)
    return url_to_page, key_to_page


def query_existing_urls(db_id: str, token: str) -> dict[str, str]:
    """Backward-compatible URL-only cache wrapper."""
    return query_existing_pages(db_id, token)[0]


def _chunk_children(children: list[dict], size: int = 90):
    for i in range(0, len(children), size):
        yield children[i:i + size]


def _list_block_children(block_id: str, token: str) -> list[dict]:
    children: list[dict] = []
    cursor = None
    while True:
        path = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            path += "&start_cursor=" + urllib.parse.quote(cursor)
        resp = _notion_request("GET", path, token)
        children.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        time.sleep(RATE_LIMIT_DELAY)
    return children


def replace_page_children(page_id: str, blocks: list[dict], token: str) -> int:
    """Archive current top-level children and append the rendered page body."""
    existing = _list_block_children(page_id, token)
    for child in existing:
        block_id = child.get("id")
        if block_id:
            _notion_request("PATCH", f"/blocks/{block_id}", token, {"archived": True})
            time.sleep(RATE_LIMIT_DELAY)
    appended = 0
    for chunk in _chunk_children(blocks):
        _notion_request("PATCH", f"/blocks/{page_id}/children", token, {"children": chunk})
        appended += len(chunk)
        time.sleep(RATE_LIMIT_DELAY)
    return appended


def create_page(db_id: str, item: dict, meta: dict, token: str) -> str:
    """Notion 페이지 생성 → page_id 반환."""
    props = make_page_properties(item, meta)
    blocks = make_page_blocks(item)
    body = {
        "parent": {"database_id": db_id},
        "properties": props,
        "children": blocks,
    }
    resp = _notion_request("POST", "/pages", token, body)
    return resp.get("id", "")


def update_page(page_id: str, item: dict, meta: dict, token: str, update_body: bool = True) -> None:
    """기존 Notion 페이지 properties 업데이트 및 page body 갱신."""
    props = make_page_properties(item, meta)
    _notion_request("PATCH", f"/pages/{page_id}", token, {"properties": props})
    if update_body:
        replace_page_children(page_id, make_page_blocks(item), token)

# ---------------------------------------------------------------------------
# 메인 동기화 로직
# ---------------------------------------------------------------------------

def validate_item(item: dict) -> str | None:
    """아이템 유효성 검사. 문제 있으면 reason 문자열, 없으면 None."""
    url = item.get("url")
    title = item.get("title")
    if not url:
        return "url 없음"
    if not title:
        return "title 없음"
    if is_placeholder(title):
        return f"플레이스홀더 제목: {title!r}"
    ensure_item_canonical_key(item)
    return None


def sync(
    raw_json: dict,
    db_id: str = DEFAULT_DB_ID,
    token: str = "",
    dry_run: bool = False,
    limit: int | None = None,
    ensure_schema: bool = True,
    update_page_body: bool = True,
) -> dict:
    """
    raw collector JSON → Notion sync.

    raw_json: {meta: ..., items: [...], failed_sources: [...]}
    반환값: stdout JSON 스키마 호환 dict
    """
    meta = raw_json.get("meta", {})
    items: list[dict] = raw_json.get("items", [])

    if limit is not None:
        items = items[:limit]

    items_total = len(items)
    synced_list: list[dict] = []
    skipped_list: list[dict] = []
    failed_list: list[dict] = []
    source_counts: dict[str, int] = {}
    schema_result = {"changed": False, "property": CANONICAL_KEY_PROP, "dry_run": dry_run}

    # 유효 아이템 필터링
    valid_items = []
    for item in items:
        reason = validate_item(item)
        if reason:
            skipped_list.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "reason": reason,
            })
        else:
            valid_items.append(item)

    items_valid = len(valid_items)

    if dry_run:
        for item in valid_items:
            synced_list.append({
                "title": item.get("title_ko") or item.get("korean_title") or item["title"],
                "url": item["url"],
                "canonical_key": item.get("canonical_key", ""),
                "source": item.get("source", ""),
                "action": "would_create",
                "notion_page_id": None,
            })
            src = item.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
    else:
        if ensure_schema:
            schema_result = ensure_database_schema(db_id, token)
            time.sleep(RATE_LIMIT_DELAY)

        url_cache, key_cache = query_existing_pages(db_id, token)
        time.sleep(RATE_LIMIT_DELAY)

        for item in valid_items:
            url = item["url"]
            ckey = item.get("canonical_key") or ensure_item_canonical_key(item)
            try:
                if ckey in key_cache:
                    page_id = key_cache[ckey]
                    update_page(page_id, item, meta, token, update_body=update_page_body)
                    action = "updated_by_canonical_key"
                elif url in url_cache:
                    page_id = url_cache[url]
                    update_page(page_id, item, meta, token, update_body=update_page_body)
                    key_cache[ckey] = page_id
                    action = "updated_by_url"
                else:
                    page_id = create_page(db_id, item, meta, token)
                    url_cache[url] = page_id
                    key_cache[ckey] = page_id
                    action = "created"

                try:
                    mark_notion_page(ckey, page_id)
                except Exception:
                    pass

                synced_list.append({
                    "title": item.get("title_ko") or item.get("korean_title") or item["title"],
                    "url": url,
                    "canonical_key": ckey,
                    "source": item.get("source", ""),
                    "action": action,
                    "notion_page_id": page_id,
                })
                src = item.get("source", "unknown")
                source_counts[src] = source_counts.get(src, 0) + 1
                time.sleep(RATE_LIMIT_DELAY)
            except Exception as exc:
                failed_list.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "canonical_key": ckey,
                    "reason": str(exc),
                })

    return {
        "meta": {
            "json_path": meta.get("raw_json_path", ""),
            "generated_at_kst": meta.get("generated_at_kst", ""),
            "notion_db_id": db_id,
            "canonical_key_property": CANONICAL_KEY_PROP,
            "schema": schema_result,
            "update_page_body": update_page_body,
            "items_total": items_total,
            "items_valid": items_valid,
            "items_synced": len(synced_list),
            "items_skipped": len(skipped_list),
            "items_failed": len(failed_list),
            "dry_run": dry_run,
        },
        "synced": synced_list,
        "skipped": skipped_list,
        "failed": failed_list,
        "source_counts": source_counts,
    }
