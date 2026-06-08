# Daily AI Digest

Hermes cron collector project for the daily Korean AI/LLM digest delivered to Telegram.

This project exists because the collector is no longer a one-off file under the default Hermes profile's `scripts/` directory. Future AI agents should treat this directory as the source of truth.

## What it does

1. Collects recent AI-related candidates from RSS/API sources, Reddit JSON/RSS fallback, GitHub Search, HN Algolia, and selected HTML-only vendor pages.
2. Scores candidates with source-class-aware score v2, normally using a 7-day lookback plus freshness weighting instead of a hard 24-hour-only window.
3. Normalizes every selected item into a JSON shape consumed by a Hermes cron prompt.
3. Emits ASCII-safe JSON to stdout for the cron scheduler.
4. Writes the full UTF-8 raw JSON to `C:/Users/gsnp/AppData/Local/hermes/daily_ai_digest/`.
5. Syncs item rows/pages to Notion with Korean titles, detailed page bodies, and `Canonical Key` based upsert when `scripts/notion_digest_sync.py` is run.
6. Tracks seen/selected/digest-sent state in the local SQLite ledger.
7. Logs parser diagnostics to `C:/Users/gsnp/AppData/Local/hermes/logs/daily_ai_digest.log`.

## Cron integration

Default Hermes profile job:

- Job ID: `7de550b0ea5f`
- Name: `Daily AI Digest — 08:45 KST`
- Schedule: `45 8 * * *`
- Script path should be:
  `C:/Users/gsnp/Desktop/Project/daily-ai-digest/scripts/daily_ai_digest_collect.py`

The old default-profile script path remains only as a compatibility shim:
`C:/Users/gsnp/AppData/Local/hermes/scripts/daily_ai_digest_collect.py`.
Do not make source edits there.

## Quick commands

From this project root:

```bash
python -m py_compile src/daily_ai_digest/collector.py scripts/daily_ai_digest_collect.py
python scripts/daily_ai_digest_collect.py --source "LangChain" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "HF Papers" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "Reddit LocalLLaMA" --lookback-days 7 --no-ledger
python scripts/daily_ai_digest_collect.py --html-only --include-stale --max-items 80 --no-ledger
```

Use `--source "Exact Source Name"` for fast parser debugging. Avoid full runs unless needed because GitHub unauthenticated search intentionally sleeps between queries to avoid rate limits.

## Important output contract

Cron expects stdout to be one JSON object:

```json
{
  "meta": {
    "generated_at_kst": "...",
    "source_statuses": [],
    "sources_collected_no_latest": [],
    "sources_date_issues": [],
    "unknown_date_candidates": []
  },
  "items": [],
  "failed_sources": []
}
```

Do not change this schema without also updating the Hermes cron prompt in the cron-it profile. The Notion follow-up cron also calls `scripts/mark_digest_sent.py` as a post-processing hook when upstream delivery status is OK.
