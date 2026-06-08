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
python scripts/mark_digest_sent.py --json-path <raw_json_path>
```

`notion_digest_sync.py` ensures the `Canonical Key` rich_text property by default and then upserts by `canonical_key` before falling back to exact URL. It prefers enriched Korean fields (`title_ko`, `summary_ko`, `key_points_ko`, `why_it_matters_ko`, `action_items_ko`) and renders each DB row as a readable Notion page, not just a one-line summary. Use `--no-ensure-schema` only for tests or schema debugging; use `--no-update-page-body` only when you deliberately want to skip replacing existing page children.

## Cron checks

```bash
hermes --profile cron-it cron list --all
```

The script should display as an absolute path under this project.

## Common failure patterns

- `RSS fetch returned HTML`: the feed URL likely moved or the Accept header is not enough.
- `parsed_items > 0` but `final_items = 0`: parser worked, but recency/date filtering removed all items.
- `unknown_date_candidates_total > 0`: date parser/recovery needs source-specific improvement, or the item should be ignored as a false positive.
- Full runs taking too long: GitHub unauthenticated search sleeps between queries by design.
