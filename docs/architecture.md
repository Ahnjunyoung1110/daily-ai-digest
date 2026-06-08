# Architecture

## Runtime flow

`Hermes cron job 7de550b0ea5f`
→ runs `scripts/daily_ai_digest_collect.py`
→ imports `daily_ai_digest.collector.main()` from `src/`
→ prints normalized JSON to stdout
→ Hermes injects that JSON into the cron prompt
→ the agent writes a concise Korean Telegram digest.

`cron-it` follow-up job `c32e07833ba2`
→ reads the archived raw JSON path from the 08:45 cron output
→ enriches items into Korean fields without external translation scripts
→ runs `scripts/notion_digest_sync.py`
→ upserts Notion item pages, marks the current 3-5 featured items via the `중요` checkbox, writes a daily summary row, then calls `scripts/mark_digest_sent.py` when upstream delivery succeeded.

## Collector modules

```text
src/daily_ai_digest/
  config.py           # KST, 경로, log(), kst_now(), 공용 상수
  sources.py          # RSS_SOURCES, HTML_SOURCES, AI_TERMS, PROMO_TERMS 등 소스 레지스트리
  fetch.py            # http_get, curl_get, fetch_bytes, gh_headers, github_request, 상수
  dates.py            # parse_date, parse_loose_date, parse_date_from_url, 날짜 복구 헬퍼
  output.py           # make_item, score_item v2, score_breakdown, dedupe, filter_items, build_result, 텍스트 유틸
  ledger.py           # canonical_key, SQLite seen/selected/digest_sent/notion_page ledger
  notion_sync.py      # enriched/raw JSON → Notion rows/pages, Korean title/body, Canonical Key + 중요 체크박스 + 중요도(score) number schema/upsert
  parsers/rss.py      # collect_rss, collect_reddit, collect_hn, collect_github
  parsers/html.py     # extract_anchor_cards, extract_article_cards, 사이트별 파서, collect_html
  collector.py        # collect_all(), main(), __main__ — 얇은 오케스트레이션만
```

의존 방향 (낮은 레벨 → 높은 레벨): `config` ← `sources`/`fetch`/`output` ← `dates` ← `parsers` ← `collector`

주요 함수 위치:
- `make_item()` — `output.py`. RSS/Reddit/HN/GitHub/HTML 모든 아이템이 이 단일 빌더 사용
- `score_item()` / `score_breakdown()` — `output.py`. source taxonomy 기반 score v2 사용
- `filter_items()` — `output.py`. 기본 7일 lookback + freshness weighting + source-class threshold 필터
- `build_result()` — `output.py`. stdout 스키마 조립 (제약: 스키마 변경 시 Hermes 크론 프롬프트도 업데이트 필요)
- `collect_all()` — `collector.py`. 소스 루프 오케스트레이션

## Data and logs

- Raw JSON archive: `C:/Users/gsnp/AppData/Local/hermes/daily_ai_digest/`
- Local ledger: `C:/Users/gsnp/AppData/Local/hermes/daily_ai_digest/digest_ledger.sqlite`
- Log file: `C:/Users/gsnp/AppData/Local/hermes/logs/daily_ai_digest.log`
- Default-profile cron output archive: `C:/Users/gsnp/AppData/Local/hermes/cron/output/7de550b0ea5f/`
- cron-it output archives: `C:/Users/gsnp/AppData/Local/hermes/profiles/cron-it/cron/output/b6271d30c1f5/` and `.../c32e07833ba2/`

## Why HTML parsers are separate

RSS/API sources are stable enough to parse generically. HTML-only sources have site-specific structure, date formats, and failure modes, so they are registered separately and must fail soft source-by-source.


## Notion important-item semantics

The Notion property `중요` is a checkbox used by the frontend to feature current high-impact AI/IT items. The LLM enrichment step may set `important: true` and `importance_reason_ko`, but `notion_sync.py` is the enforcement layer: it normalizes the current sync set to 3-5 important items when possible, maps the flag to the Notion checkbox, and clears stale checked pages that are no longer part of the current sync set.

The Notion property `중요도` is a number field storing the raw `score` value computed by `output.py`'s `score_item()` (sum of source_authority + popularity + topic_relevance + freshness + penalty, range ~0–100+). It is written on every create/update and reflects how the collector ranked each item independently of the LLM-selected `중요` checkbox.
