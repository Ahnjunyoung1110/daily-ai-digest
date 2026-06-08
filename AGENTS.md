# AGENTS.md — Daily AI Digest

Guidance for AI agents working in this project.

## Source of truth

- Main implementation: `src/daily_ai_digest/collector.py`
- Cron entrypoint: `scripts/daily_ai_digest_collect.py`
- Project docs: `README.md`, `docs/architecture.md`, `docs/sources.md`, `docs/operations.md`
- Default-profile cron job file: `C:/Users/gsnp/AppData/Local/hermes/cron/jobs.json`
- cron-it Notion follow-up job file: `C:/Users/gsnp/AppData/Local/hermes/profiles/cron-it/cron/jobs.json`

Do not edit `C:/Users/gsnp/AppData/Local/hermes/scripts/daily_ai_digest_collect.py` except to maintain the compatibility shim.

## Operating rules

1. Keep the stdout JSON schema stable; the Hermes cron prompt depends on it.
2. Keep Windows cron stdout ASCII-safe: use `json.dumps(..., ensure_ascii=True)` for stdout and fatal paths.
3. HTML-only source parsers must fail soft per source and append diagnostics, not abort the whole digest.
4. Production collection uses a bounded rolling lookback, default 7 days. Freshness is score v2 input; stale/unknown dates must not be silently promoted.
5. Unknown dates should be reported in metadata, not silently promoted into production items.
6. Prefer per-source smoke tests. Full collector runs are slower because GitHub Search may sleep to avoid unauthenticated rate limits.
7. When adding or changing metadata fields, update the cron-it Hermes cron prompt if user-facing output should mention them.
8. `digest_sent_at` is not set by the collector. It is marked only by the downstream cron/post-processing hook via `scripts/mark_digest_sent.py`.
9. Notion item pages should use Korean displayed titles (`title_ko`) and detailed page body fields (`summary_ko`, `key_points_ko`, `why_it_matters_ko`, `action_items_ko`) whenever a Hermes cron synthesis step can enrich raw items.
10. The Notion checkbox property `중요` is the current-feature flag for the frontend. Each sync should leave exactly 3-5 current item pages checked when possible, and clear stale checked pages outside the current sync set.
11. The cron-it Notion enrichment prompt must not generate temporary translation/enrichment scripts, call external translation APIs, or embed large JSON in fragile shell heredocs; prefer direct LLM enrichment plus checked-in project scripts.

## Safe verification sequence

```bash
python -m py_compile src/daily_ai_digest/collector.py src/daily_ai_digest/notion_sync.py scripts/daily_ai_digest_collect.py scripts/notion_digest_sync.py scripts/notion_ensure_schema.py
python scripts/daily_ai_digest_collect.py --source "LangChain" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "DeepSeek" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "HF Papers" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "Anthropic News" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "Reddit LocalLLaMA" --lookback-days 7 --no-ledger
python -m pytest tests/test_notion_page_content.py -v
```

Only run `python scripts/daily_ai_digest_collect.py --max-items 160` when a full end-to-end collection is truly needed.
