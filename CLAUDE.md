# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

Hermes 크론 스케줄러용 AI/LLM 콘텐츠 수집기. RSS, API, HTML 파싱으로 다수 출처에서 데이터 수집 → JSON 정규화 → 매일 08:45 KST 한국어 Telegram 다이제스트 발송. SQLite 레저로 중복 추적, Notion DB에 아이템 동기화.

## 명령어

```bash
# 단일 소스 스모크 테스트 (권장 — GitHub Search 전체 실행은 느림)
python scripts/daily_ai_digest_collect.py --source "LangChain" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "Anthropic News" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "HF Papers" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "DeepSeek" --include-stale --no-ledger
python scripts/daily_ai_digest_collect.py --source "Reddit LocalLLaMA" --lookback-days 7 --no-ledger

# 전체 프로덕션 실행 (GitHub Search 레이트 리밋으로 느림)
python scripts/daily_ai_digest_collect.py --max-items 160

# 발송 후 레저 마킹 (Hermes 크론 후처리)
python scripts/mark_digest_sent.py

# Notion 스키마 검증 및 동기화
python scripts/notion_ensure_schema.py
python scripts/notion_digest_sync.py

# 테스트
python -m pytest tests/

# 구문 검사 (모든 모듈)
python -m py_compile src/daily_ai_digest/collector.py src/daily_ai_digest/config.py src/daily_ai_digest/sources.py src/daily_ai_digest/fetch.py src/daily_ai_digest/output.py src/daily_ai_digest/dates.py src/daily_ai_digest/ledger.py src/daily_ai_digest/notion_sync.py src/daily_ai_digest/parsers/rss.py src/daily_ai_digest/parsers/html.py scripts/daily_ai_digest_collect.py
```

### CLI 플래그
- `--source "정확한 소스명"`: 단일 소스만 수집 (디버깅용)
- `--include-stale`: 24시간 최신성 필터 우회 (테스트 전용)
- `--html-only`: HTML 파싱 소스만 수집
- `--max-items N`: 최종 출력 항목 수 제한 (기본값 160)
- `--lookback-days N`: 프로덕션 후보 룩백 윈도우 (기본값 7, 범위 1-7)
- `--no-ledger`: SQLite 레저 업데이트 생략 (테스트 전용)
- `--force-failure`: 드라이런용 합성 실패 추가

## 아키텍처

### 진입점
- **`scripts/daily_ai_digest_collect.py`** — Hermes 크론 래퍼. `src/`를 sys.path에 추가 후 `collector.main()` 호출.
- **`src/daily_ai_digest/collector.py`** — 얇은 오케스트레이션 (`collect_all`, `main`, `__main__`만).

### 모듈 구조

| 모듈 | 주요 내용 |
|---|---|
| `config.py` | `KST`, `LOG_PATH`, `JSON_DIR`, `log()`, `kst_now()` |
| `sources.py` | `RSS_SOURCES`, `HTML_SOURCES`, `AI_TERMS`, `PROMO_TERMS` 등 소스 레지스트리 |
| `fetch.py` | `http_get`, `curl_get`, `fetch_bytes`, `github_request`, `github_token()`, 네트워크 상수 |
| `dates.py` | `parse_date`, `parse_loose_date`, `parse_date_from_url`, `enrich_html_dates` |
| `output.py` | `make_item`, `score_item` (v2), `dedupe`, `filter_items`, `build_result`, 텍스트 유틸 |
| `ledger.py` | SQLite `seen_items` 테이블 — canonical_key 기준 seen/selected/notion 추적 |
| `notion_sync.py` | Notion DB upsert — 한국어 title_ko/summary_ko 필드, 페이지 바디 생성 |
| `parsers/rss.py` | `collect_rss`, `collect_hn`, `collect_github` |
| `parsers/html.py` | `extract_anchor_cards`, `extract_article_cards`, 사이트별 파서 6개, `collect_html` |

의존 방향: `config` ← `sources`/`fetch`/`output` ← `dates` ← `ledger`/`notion_sync` ← `parsers` ← `collector`

### 스크립트

| 스크립트 | 역할 |
|---|---|
| `scripts/daily_ai_digest_collect.py` | Hermes 크론 진입점 (메인 수집기) |
| `scripts/mark_digest_sent.py` | Telegram 발송 후 레저에 `digest_sent_at` 마킹 |
| `scripts/notion_ensure_schema.py` | Notion DB 스키마 검증/보정 |
| `scripts/notion_digest_sync.py` | 원본 JSON → Notion DB 동기화 CLI |

> `digest_collect.py` (프로젝트 루트): 별도 ETL 도구 — Telegram 다이제스트 텍스트 파싱 및 초록 조회용. 메인 수집 파이프라인과 무관.

### 데이터 소스 (총 24개)
- **RSS (14개)**: OpenAI, Google AI, HuggingFace, GitHub Blog, NVIDIA, AWS ML, MS Research, LangChain, Qwen, arXiv cs.AI/CL/LG/stat.ML, Simon Willison
- **커뮤니티/API (3개)**: Reddit LocalLLaMA, Reddit MachineLearning, HN Algolia Search
- **GitHub Search (1개)**: 키워드(llm/rag/agent/mcp/inference) + 토픽 검색
- **HTML 전용 (6개)**: Anthropic, Google DeepMind, Meta AI, Mistral, DeepSeek, HF Papers

### 출력 스키마 (stdout)
```json
{
  "meta": {
    "generated_at_kst": "...",
    "since_kst": "...",
    "recency_cutoff_kst": "...",
    "lookback_days": 7,
    "source_statuses": [],
    "sources_collected_no_latest": [],
    "sources_date_issues": [],
    "unknown_date_candidates": [],
    "ledger_path": "...",
    "ledger_seen_upserts": 0,
    "ledger_selected_marks": 0
  },
  "items": [...],
  "failed_sources": [...]
}
```
- stdout은 Hermes 크론 프롬프트가 직접 파싱 — **스키마 변경 시 다운스트림 업데이트 필수**
- stdout은 `ensure_ascii=True` 유지 (Windows 코드페이지 호환)
- 원본 UTF-8 JSON은 `raw_json_path`에 별도 아카이브

### 로그/아카이브 경로
- 원본 JSON: `C:/Users/gsnp/AppData/Local/hermes/daily_ai_digest/daily_ai_digest_YYYYMMDD_HHMMSS_KST.json`
- 진단 로그: `C:/Users/gsnp/AppData/Local/hermes/logs/daily_ai_digest.log`
- 레저 DB: `C:/Users/gsnp/AppData/Local/hermes/daily_ai_digest/digest_ledger.sqlite`

## 스코어링 v2

`output.py`의 `score_item()` 구성:

| 항목 | 기준 |
|---|---|
| source_authority | official=40, vendor_blog=25, research=18, repo=5, community=0, expert=25 |
| popularity | source_class별 차등 (HN/Reddit/GitHub stars 기준) |
| topic_relevance | AI_TERMS=+15, IMPACT_TERMS=+12, paper=+8, repo=+5 |
| freshness | 24h=+20, 3d=+10, 7d=0, 7d초과=-20 |
| penalty | promo_terms=-12, low_value_terms=-20, 저참여 커뮤니티=-25 |

SOURCE_CLASS_THRESHOLDS: official=40, vendor_blog=45, community=55, repo=50, research=45, expert=40, unknown=50

## 핵심 제약

1. **소스별 소프트 실패**: HTML 파서 예외는 전체 크래시 아닌 `failed_sources`에 추가
2. **최신성 엄격 적용**: 정확히 24시간 이내. 점수 높아도 날짜 미확인 아이템은 제외
3. **미확인 날짜 메타데이터 기록**: `unknown_date_candidates`에 포함 — 숨기지 않음
4. **스모크 테스트 우선**: 전체 실행은 GitHub Search 슬립(7초/요청)으로 느림
5. **레저 테스트 격리**: 테스트 시 `--no-ledger` 사용 — 프로덕션 SQLite 오염 방지
6. **`digest_sent_at` 설정 금지**: collector가 직접 설정하지 않음. `scripts/mark_digest_sent.py`만 설정
7. **Notion 한국어 필드**: `title_ko`, `summary_ko` 등 한국어 우선 필드 사용
8. **Hermes 호환 shim 편집 금지**: `C:/Users/gsnp/AppData/Local/hermes/scripts/` 경로 수정 금지

## 참고 문서

- `docs/architecture.md` — 런타임 플로우, 모듈 의존 다이어그램, 경로 목록
- `docs/sources.md` — 소스 레지스트리, 소스 추가 방법, 소스 클래스 임계값
- `docs/operations.md` — 장애 패턴, Notion 동기화 체크, cron 확인 방법
- `AGENTS.md` — AI 에이전트 검증 시퀀스
