from __future__ import annotations

import html
import re
import urllib.parse
from datetime import datetime, timedelta

from .config import KST, LOG_PATH, UNKNOWN_DATE_CANDIDATE_LIMIT, log
from .fetch import UA, github_token
from .sources import (
    AI_TERMS,
    IMPACT_TERMS,
    LOW_VALUE_TERMS,
    PROMO_TERMS,
    SOURCE_CLASS_THRESHOLDS,
    source_class,
)


def clean_text(s: str | None, n: int = 500) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def strip_tags(s: str, n: int = 500) -> str:
    return clean_text(s, n=n)


def attr_value(tag: str, name: str) -> str | None:
    m = re.search(rf"\b{name}\s*=\s*(['\"])(.*?)\1", tag, re.I | re.S)
    if not m:
        m = re.search(rf"\b{name}\s*=\s*([^\s>]+)", tag, re.I | re.S)
    return html.unescape((m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)).strip()) if m else None


def normalize_url(href: str, base_url: str) -> str:
    href = html.unescape((href or "").strip())
    return urllib.parse.urljoin(base_url, href).split("#", 1)[0]


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _freshness_points(item: dict, now: datetime | None) -> int:
    if not now or not item.get("published"):
        return 0
    try:
        pub = datetime.fromisoformat(str(item["published"]).replace("Z", "+00:00")).astimezone(KST)
    except Exception:
        return 0
    age_hours = max(0.0, (now - pub).total_seconds() / 3600)
    if age_hours <= 24:
        return 20
    if age_hours <= 72:
        return 10
    if age_hours <= 168:
        return 0
    return -20


def score_breakdown(item: dict, now: datetime | None = None) -> dict[str, int]:
    """Score v2: source-class aware 0~100-ish importance scoring.

    This intentionally replaces the old tiny +3/+2/+1 scale. The final
    production filter applies source-class thresholds from sources.py.
    """
    text = f"{item.get('title','')} {item.get('summary_candidate','')}"
    source = item.get("source", "")
    typ = item.get("type", "")
    cls = source_class(source, typ)
    sig = item.get("signals") or {}
    points = _safe_int(sig.get("points"))
    comments = _safe_int(sig.get("comments"))
    stars = _safe_int(sig.get("stars"))

    source_authority = {
        "official": 40,
        "vendor_blog": 25,
        "research": 18,
        "repo": 5,
        "community": 0,
        "expert": 25,
        "unknown": 0,
    }.get(cls, 0)

    popularity = 0
    if cls == "community":
        if points >= 500:
            popularity += 35
        elif points >= 200:
            popularity += 25
        elif points >= 100:
            popularity += 15
        elif points >= 50:
            popularity += 8
        if comments >= 100:
            popularity += 30
        elif comments >= 50:
            popularity += 20
        elif comments >= 20:
            popularity += 10
        elif comments >= 10:
            popularity += 5
    elif cls == "repo":
        if stars >= 1000:
            popularity += 40
        elif stars >= 300:
            popularity += 30
        elif stars >= 100:
            popularity += 20
        elif stars >= 30:
            popularity += 10
    else:
        if points >= 100 or comments >= 50:
            popularity += 15
        elif points >= 30 or comments >= 10:
            popularity += 8

    topic_relevance = 0
    if AI_TERMS.search(text):
        topic_relevance += 15
    if IMPACT_TERMS.search(text):
        topic_relevance += 12
    if typ == "paper":
        topic_relevance += 8
    if typ == "repo":
        topic_relevance += 5

    freshness = _freshness_points(item, now)

    penalty = 0
    if PROMO_TERMS.search(text):
        penalty -= 12
    if LOW_VALUE_TERMS.search(text):
        penalty -= 20
    if cls == "community" and points < 50 and comments < 10:
        penalty -= 25

    return {
        "source_authority": source_authority,
        "popularity": popularity,
        "topic_relevance": topic_relevance,
        "freshness": freshness,
        "penalty": penalty,
    }


def score_item(item: dict, now: datetime | None = None) -> int:
    return sum(score_breakdown(item, now).values())


def importance_reason(item: dict) -> str:
    parts = []
    cls = source_class(item.get("source", ""), item.get("type"))
    parts.append(f"source_class={cls}")
    sig = item.get("signals") or {}
    if sig.get("points") or sig.get("comments"):
        parts.append(f"points={sig.get('points', 0)}, comments={sig.get('comments', 0)}")
    if sig.get("stars"):
        parts.append(f"stars={sig.get('stars')}")
    br = item.get("score_breakdown") or {}
    if br:
        top = sorted(br.items(), key=lambda kv: kv[1], reverse=True)[:2]
        parts.append("top_score=" + ",".join(f"{k}:{v}" for k, v in top))
    return "; ".join(parts)


def make_item(
    source: str,
    typ: str,
    title: str,
    url: str,
    published: str | None,
    summary: str = "",
    signals: dict | None = None,
) -> dict:
    item = {
        "source": source,
        "source_class": source_class(source, typ),
        "type": typ,
        "title": clean_text(title, 240),
        "url": url,
        "published": published,
        "summary_candidate": clean_text(summary, 500),
        "signals": signals or {"stars": 0, "points": 0, "comments": 0},
        "score": 0,
        "score_version": 2,
        "score_breakdown": {},
        "importance_reason": "",
    }
    item["score_breakdown"] = score_breakdown(item)
    item["score"] = score_item(item)
    item["importance_reason"] = importance_reason(item)
    return item


def dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for it in sorted(items, key=lambda x: (x.get("score") or 0), reverse=True):
        key = (it.get("canonical_key") or it.get("url") or it.get("title") or "").lower().rstrip("/")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _is_recent_enough(item: dict, now: datetime, lookback_days: int) -> bool:
    pub = item.get("published")
    if not pub:
        return False
    try:
        pub_dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00")).astimezone(KST)
    except Exception:
        return False
    return pub_dt >= now - timedelta(days=lookback_days)


def passes_quality_threshold(item: dict) -> bool:
    cls = item.get("source_class") or source_class(item.get("source", ""), item.get("type"))
    threshold = SOURCE_CLASS_THRESHOLDS.get(cls, SOURCE_CLASS_THRESHOLDS["unknown"])
    return int(item.get("score") or 0) >= threshold


def filter_items(items: list[dict], now: datetime, include_stale: bool, lookback_days: int = 1) -> list[dict]:
    out = []
    for it in items:
        # Re-score here so freshness is evaluated against the actual run time.
        it["source_class"] = source_class(it.get("source", ""), it.get("type"))
        it["score_breakdown"] = score_breakdown(it, now)
        it["score"] = score_item(it, now)
        it["importance_reason"] = importance_reason(it)

        if not include_stale and not _is_recent_enough(it, now, lookback_days):
            it["drop_reason"] = f"outside_lookback_{lookback_days}d_or_unknown_date"
            continue
        text = f"{it.get('title', '')} {it.get('summary_candidate', '')}"
        if not (AI_TERMS.search(text) or it.get("type") in {"paper", "repo"} or it.get("source") == "HN"):
            it["drop_reason"] = "no_ai_relevance"
            continue
        if not include_stale and not passes_quality_threshold(it):
            it["drop_reason"] = "below_source_class_threshold"
            continue
        out.append(it)
    return out


def build_result(
    now: datetime,
    since: datetime,
    cutoff_24h: datetime,
    yesterday_midnight: str,
    ts_epoch: int,
    out_items: list[dict],
    failures: list[dict],
    statuses: list[dict],
    unknown_date_candidates: list[dict],
    antigravity_path: str | None,
    lookback_days: int = 1,
    ledger_path: str | None = None,
    ledger_seen_upserts: int = 0,
    ledger_selected_marks: int = 0,
) -> dict:
    final_counts: dict[str, int] = {}
    for it in out_items:
        src = it.get("source") or ""
        final_counts[src] = final_counts.get(src, 0) + 1

    sources_collected_no_latest = []
    for st in statuses:
        src = st.get("source")
        parsed = int(st.get("parsed_items") or 0)
        if src and parsed > 0 and final_counts.get(src, 0) == 0:
            unknown_count = int(st.get("unknown_date_items") or 0)
            entry: dict = {
                "source": src,
                "parsed_items": parsed,
                "final_items": 0,
                "reason": (
                    "parsed_but_no_recent_or_high_quality_final_items"
                    if unknown_count == 0
                    else "parsed_but_no_recent_final_items_with_unresolved_date_parse_failures"
                ),
            }
            if unknown_count:
                entry["date_parse_failed_items"] = st.get("date_parse_failed_items")
                entry["unknown_date_items"] = unknown_count
            sources_collected_no_latest.append(entry)
            log(
                f"WARN source_collected_no_latest source={src}: "
                f"parsed_items={parsed} final_items=0 "
                f"date_parse_failed={st.get('date_parse_failed_items', 0)} "
                f"unknown_date={st.get('unknown_date_items', 0)}"
            )

    sources_date_issues = [
        {
            "source": st.get("source"),
            "date_parse_failed_items": st.get("date_parse_failed_items", 0),
            "date_retry_attempts": st.get("date_retry_attempts", 0),
            "date_retry_recovered": st.get("date_retry_recovered", 0),
            "unknown_date_items": st.get("unknown_date_items", 0),
        }
        for st in statuses
        if st.get("unknown_date_items")
    ]

    return {
        "meta": {
            "generated_at_kst": now.isoformat(timespec="seconds"),
            "since_kst": since.isoformat(timespec="seconds"),
            "recency_cutoff_kst": cutoff_24h.isoformat(timespec="seconds"),
            "recency_cutoff_hours": 24,
            "lookback_days": lookback_days,
            "yesterday_date_kst": yesterday_midnight,
            "hn_since_epoch_yesterday_midnight_kst": ts_epoch,
            "user_agent": UA,
            "antigravity_cli": {
                "available": bool(antigravity_path),
                "path": antigravity_path,
                "fetch_path_used": "urllib_or_curl_feedparser_fallback",
            },
            "github_token_present": bool(github_token()),
            "log_path": str(LOG_PATH),
            "raw_json_path": "",
            "ledger_path": ledger_path or "",
            "ledger_seen_upserts": ledger_seen_upserts,
            "ledger_selected_marks": ledger_selected_marks,
            "source_statuses": statuses,
            "sources_collected_no_latest": sources_collected_no_latest,
            "sources_date_issues": sources_date_issues,
            "unknown_date_candidates": unknown_date_candidates[:UNKNOWN_DATE_CANDIDATE_LIMIT],
            "unknown_date_candidates_total": len(unknown_date_candidates),
        },
        "items": out_items,
        "failed_sources": failures,
    }
