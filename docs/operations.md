# Operations

## Fast parser smoke tests

Use these instead of full runs when debugging one parser:

```bash
python scripts/daily_ai_digest_collect.py --source "LangChain" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "Anthropic News" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "DeepSeek" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "HF Papers" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "Reddit LocalLLaMA" --lookback-days 7 --no-ledger
```

To summarize JSON quickly on this Windows/Git-Bash host:

```bash
python scripts/daily_ai_digest_collect.py --source "HF Papers" --include-stale > C:/Users/gsnp/AppData/Local/Temp/hf.json
python - <<'PY'
import json
p='C:/Users/gsnp/AppData/Local/Temp/hf.json'
d=json.load(open(p, encoding='utf-8'))
print('items', len(d['items']))
print('failed', d['failed_sources'])
print('date_issues', d['meta']['sources_date_issues'])
print('unknown_total', d['meta']['unknown_date_candidates_total'])
PY
```

## Notion schema/sync checks

```bash
# Requires NOTION_TOKEN or NOTION_API_KEY in the environment.
python scripts/notion_ensure_schema.py
python scripts/notion_digest_sync.py --json-path <raw_json_path> --limit 1
python scripts/notion_digest_sync.py --json-path <enriched_json_path> --no-update-page-body
python scripts/mark_digest_sent.py --json-path <raw_json_path>
```

`notion_digest_sync.py` ensures the `Canonical Key` rich_text property and the `중요` checkbox property by default, then upserts by `canonical_key` before falling back to exact URL. It prefers enriched Korean fields (`title_ko`, `summary_ko`, `key_points_ko`, `why_it_matters_ko`, `action_items_ko`) and renders each DB row as a readable Notion page, not just a one-line summary. `important: true` maps to the Notion `중요` checkbox; the sync normalizes the current set to 3-5 checked items when possible and clears stale checked pages outside the current sync set. Use `--no-ensure-schema` only for tests or schema debugging; use `--no-update-page-body` only when you deliberately want to skip replacing existing page children.

## Cron checks

```bash
hermes --profile cron-it cron list --all
```

The 08:45 collector script should display as an absolute path under this project. The 08:55 `cron-it` Notion follow-up job should use workdir `C:/Users/gsnp/Desktop/Project/daily-ai-digest` and run `scripts/notion_digest_sync.py` from this repo.

## Common failure patterns

- `RSS fetch returned HTML`: the feed URL likely moved or the Accept header is not enough.
- `parsed_items > 0` but `final_items = 0`: parser worked, but recency/date filtering removed all items.
- `unknown_date_candidates_total > 0`: date parser/recovery needs source-specific improvement, or the item should be ignored as a false positive.
- Full collector runs taking too long: GitHub unauthenticated search sleeps between queries by design.
- Notion cron run taking many minutes: check whether the LLM generated a temporary enrichment/translation script such as `tmp_notion_enrich.py` or called Google Translate. The cron prompt should forbid external translation services and fragile shell heredocs; direct LLM enrichment plus checked-in scripts is the intended path.
- More than 5 `중요=true` pages in Notion: run `notion_digest_sync.py` again against the latest enriched JSON. Live sync clears stale checked pages outside the current sync set.
