#!/usr/bin/env python3
"""Collect fixed-source Daily AI Digest inputs as normalized JSON.

Stdout: JSON object with items[], failed_sources[], meta{}.
Logs: AppData/Local/hermes/logs/daily_ai_digest.log
"""
from __future__ import annotations

import argparse
import json
import subprocess
import traceback
from datetime import datetime, timedelta

from .config import JSON_DIR, KST, log, kst_now
from .ledger import LEDGER_PATH, enrich_items, mark_selected, upsert_seen
from .output import build_result, dedupe, filter_items
from .parsers.html import collect_html
from .parsers.rss import collect_github, collect_hn, collect_reddit, collect_rss
from .sources import HTML_SOURCES, REDDIT_SOURCES, RSS_SOURCES


def collect_all(
    html_only: bool,
    source_filter: str | None,
    ts_epoch: int,
    github_since_date: str,
    failures: list[dict],
    statuses: list[dict],
    unknown_date_candidates: list[dict],
) -> list[dict]:
    items: list[dict] = []
    if not html_only:
        for source, typ, url in RSS_SOURCES:
            if source_filter and source_filter != source:
                continue
            items.extend(collect_rss(source, typ, url, failures, statuses))
        for source, _typ, subreddit in REDDIT_SOURCES:
            if source_filter and source_filter != source:
                continue
            items.extend(collect_reddit(source, subreddit, failures, statuses))
        if not source_filter:
            items.extend(collect_hn(ts_epoch, failures, statuses))
            items.extend(collect_github(github_since_date, failures, statuses))
    for source, typ, url in HTML_SOURCES:
        if source_filter and source_filter != source:
            continue
        items.extend(collect_html(source, typ, url, failures, statuses, unknown_date_candidates))
    return items


def _source_status_counts(statuses: list[dict], items: list[dict]) -> None:
    counts: dict[str, int] = {}
    for item in items:
        src = item.get("source") or ""
        counts[src] = counts.get(src, 0) + 1
    for st in statuses:
        src = st.get("source") or ""
        if "parsed_items" not in st and src in counts:
            st["parsed_items"] = counts[src]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-failure", action="store_true", help="append one synthetic failure for dry-run resilience testing")
    ap.add_argument("--max-items", type=int, default=160)
    ap.add_argument("--html-only", action="store_true", help="collect only HTML-scraped sources; useful for parser smoke tests")
    ap.add_argument("--source", help="collect only one exact source name, e.g. 'Anthropic News' or 'HF Papers'")
    ap.add_argument("--include-stale", action="store_true", help="skip production recency/quality filtering; useful for parser smoke tests")
    ap.add_argument("--lookback-days", type=int, default=7, help="production candidate lookback window; freshness is scored separately")
    ap.add_argument("--no-ledger", action="store_true", help="do not update the local SQLite seen/selected ledger")
    args = ap.parse_args()

    now = kst_now()
    lookback_days = max(1, min(args.lookback_days, 7))
    since = now - timedelta(days=lookback_days)
    github_since_date = since.date().isoformat()
    # Kept for output compatibility with the existing cron prompt.
    yesterday_midnight = (now.date() - timedelta(days=1)).isoformat()
    ts_epoch = int(datetime.combine(since.date(), datetime.min.time(), tzinfo=KST).timestamp())
    cutoff_24h = now - timedelta(hours=24)

    failures: list[dict] = []
    statuses: list[dict] = []
    unknown_date_candidates: list[dict] = []
    log(f"START daily_ai_digest_collect lookback_days={lookback_days}")

    # Antigravity discovery: collection falls back automatically if unavailable.
    antigravity_path = None
    try:
        p = subprocess.run(["bash", "-lc", "command -v antigravity || true"], capture_output=True, text=True, timeout=5)
        antigravity_path = p.stdout.strip() or None
    except Exception:
        antigravity_path = None

    items = collect_all(
        html_only=args.html_only,
        source_filter=args.source,
        ts_epoch=ts_epoch,
        github_since_date=github_since_date,
        failures=failures,
        statuses=statuses,
        unknown_date_candidates=unknown_date_candidates,
    )
    enrich_items(items)
    _source_status_counts(statuses, items)

    ledger_seen_upserts = 0
    ledger_selected_marks = 0
    if not args.no_ledger:
        try:
            ledger_seen_upserts = upsert_seen(items, now)
        except Exception as e:
            failures.append({"source": "ledger", "reason": str(e)[:240]})
            log(f"FAIL ledger upsert_seen: {e}")

    if args.force_failure:
        failures.append({"source": "Synthetic failure check", "reason": "forced dry-run failure"})

    filtered = filter_items(items, now, args.include_stale, lookback_days=lookback_days)
    out_items = dedupe(filtered)[: args.max_items]

    if not args.no_ledger:
        try:
            ledger_selected_marks = mark_selected(out_items, now)
        except Exception as e:
            failures.append({"source": "ledger", "reason": str(e)[:240]})
            log(f"FAIL ledger mark_selected: {e}")

    result = build_result(
        now=now,
        since=since,
        cutoff_24h=cutoff_24h,
        yesterday_midnight=yesterday_midnight,
        ts_epoch=ts_epoch,
        out_items=out_items,
        failures=failures,
        statuses=statuses,
        unknown_date_candidates=unknown_date_candidates,
        antigravity_path=antigravity_path,
        lookback_days=lookback_days,
        ledger_path="" if args.no_ledger else str(LEDGER_PATH),
        ledger_seen_upserts=ledger_seen_upserts,
        ledger_selected_marks=ledger_selected_marks,
    )

    JSON_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = JSON_DIR / f"daily_ai_digest_{now.strftime('%Y%m%d_%H%M%S')}_KST.json"
    result["meta"]["raw_json_path"] = str(raw_path)
    raw_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = result["meta"]
    log(
        f"DONE items={len(out_items)} failures={len(failures)} "
        f"lookback_days={lookback_days} ledger_seen={ledger_seen_upserts} ledger_selected={ledger_selected_marks} "
        f"no_latest={len(meta['sources_collected_no_latest'])} "
        f"date_issue_sources={len(meta['sources_date_issues'])} "
        f"unknown_date_candidates={len(unknown_date_candidates)} raw={raw_path}"
    )
    # Cron의 Windows 부모 프로세스가 활성 ANSI 코드페이지로 stdout을 디코딩할 수 있음.
    # 스케줄러가 JSON을 안정적으로 수신하도록 stdout은 ASCII-only 유지.
    # UTF-8 원본 JSON은 raw_path에 별도 보관.
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        log(f"FATAL {type(e).__name__}: {e}\n{traceback.format_exc()}")
        print(json.dumps({
            "meta": {"generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"), "fatal": True},
            "items": [],
            "failed_sources": [{"source": "collector", "reason": str(e)[:500]}],
        }, ensure_ascii=True))
        raise SystemExit(0)
