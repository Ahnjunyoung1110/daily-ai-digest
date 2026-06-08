from __future__ import annotations

import json
import sqlite3
import urllib.parse
from datetime import datetime
from pathlib import Path

from .config import JSON_DIR

LEDGER_PATH = JSON_DIR / "digest_ledger.sqlite"

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "fbclid", "gclid"}


def normalize_url(url: str) -> str:
    if not url:
        return ""
    p = urllib.parse.urlparse(url.strip())
    scheme = (p.scheme or "https").lower()
    netloc = p.netloc.lower()
    path = p.path.rstrip("/") or "/"
    query = urllib.parse.parse_qsl(p.query, keep_blank_values=False)
    query = [(k, v) for k, v in query if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith("utm_")]
    return urllib.parse.urlunparse((scheme, netloc, path, "", urllib.parse.urlencode(query), ""))


def canonical_key(item: dict) -> str:
    source = item.get("source") or ""
    url = normalize_url(item.get("url") or "")
    if source == "GitHub" and url:
        p = urllib.parse.urlparse(url)
        parts = [x for x in p.path.split("/") if x]
        if len(parts) >= 2:
            return f"github:{parts[0].lower()}/{parts[1].lower()}"
    if source.startswith("Reddit") and url:
        p = urllib.parse.urlparse(url)
        parts = [x for x in p.path.split("/") if x]
        if "comments" in parts:
            i = parts.index("comments")
            if i + 1 < len(parts):
                return f"reddit:{parts[i + 1].lower()}"
    if "arxiv.org" in url:
        p = urllib.parse.urlparse(url)
        parts = [x for x in p.path.split("/") if x]
        if parts:
            return f"arxiv:{parts[-1].lower()}"
    if url:
        return "url:" + url.lower()
    title = " ".join((item.get("title") or "").lower().split())
    published = (item.get("published") or "")[:10]
    return f"title:{source.lower()}:{published}:{title[:160]}"


def enrich_items(items: list[dict]) -> list[dict]:
    for item in items:
        item["canonical_key"] = canonical_key(item)
    return items


def _connect(path: Path = LEDGER_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_items (
            canonical_key TEXT PRIMARY KEY,
            canonical_url TEXT,
            title TEXT,
            source TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            selected_for_digest_at TEXT,
            digest_sent_at TEXT,
            published_at TEXT,
            
            seen_count INTEGER NOT NULL DEFAULT 1,
            last_score INTEGER NOT NULL DEFAULT 0,
            last_signals_json TEXT NOT NULL DEFAULT '{}',
            notion_page_id TEXT,
            raw_item_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(seen_items)").fetchall()}
    if "digest_sent_at" not in existing_cols:
        conn.execute("ALTER TABLE seen_items ADD COLUMN digest_sent_at TEXT")
    if "notion_page_id" not in existing_cols:
        conn.execute("ALTER TABLE seen_items ADD COLUMN notion_page_id TEXT")
    conn.commit()
    return conn


def upsert_seen(items: list[dict], seen_at: datetime, path: Path = LEDGER_PATH) -> int:
    if not items:
        return 0
    conn = _connect(path)
    ts = seen_at.isoformat(timespec="seconds")
    try:
        for item in items:
            key = item.get("canonical_key") or canonical_key(item)
            item["canonical_key"] = key
            conn.execute(
                """
                INSERT INTO seen_items (
                    canonical_key, canonical_url, title, source, first_seen_at, last_seen_at,
                    published_at, seen_count, last_score, last_signals_json, raw_item_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(canonical_key) DO UPDATE SET
                    canonical_url=excluded.canonical_url,
                    title=excluded.title,
                    source=excluded.source,
                    last_seen_at=excluded.last_seen_at,
                    published_at=excluded.published_at,
                    seen_count=seen_count + 1,
                    last_score=excluded.last_score,
                    last_signals_json=excluded.last_signals_json,
                    raw_item_json=excluded.raw_item_json
                """,
                (
                    key,
                    normalize_url(item.get("url") or ""),
                    item.get("title") or "",
                    item.get("source") or "",
                    ts,
                    ts,
                    item.get("published") or "",
                    int(item.get("score") or 0),
                    json.dumps(item.get("signals") or {}, ensure_ascii=False),
                    json.dumps(item, ensure_ascii=False),
                ),
            )
        conn.commit()
        return len(items)
    finally:
        conn.close()


def mark_selected(items: list[dict], selected_at: datetime, path: Path = LEDGER_PATH) -> int:
    if not items:
        return 0
    conn = _connect(path)
    ts = selected_at.isoformat(timespec="seconds")
    try:
        count = 0
        for item in items:
            key = item.get("canonical_key") or canonical_key(item)
            conn.execute(
                "UPDATE seen_items SET selected_for_digest_at=? WHERE canonical_key=?",
                (ts, key),
            )
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def mark_digest_sent(keys_or_items: list, sent_at: datetime, path: Path = LEDGER_PATH) -> int:
    if not keys_or_items:
        return 0
    conn = _connect(path)
    ts = sent_at.isoformat(timespec="seconds")
    try:
        count = 0
        for value in keys_or_items:
            key = canonical_key(value) if isinstance(value, dict) else str(value)
            cur = conn.execute(
                "UPDATE seen_items SET digest_sent_at=? WHERE canonical_key=?",
                (ts, key),
            )
            count += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
        conn.commit()
        return count
    finally:
        conn.close()


def mark_notion_page(key: str, page_id: str, path: Path = LEDGER_PATH) -> int:
    if not key or not page_id:
        return 0
    conn = _connect(path)
    try:
        cur = conn.execute(
            "UPDATE seen_items SET notion_page_id=? WHERE canonical_key=?",
            (page_id, key),
        )
        conn.commit()
        return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    finally:
        conn.close()
