"""notion_sync 단위 테스트 — 오프라인, Notion API 미호출."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# src/ 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from daily_ai_digest.notion_sync import (
    DEFAULT_DB_ID,
    is_placeholder,
    make_page_properties,
    map_type_to_korean,
    sync,
    validate_item,
)


# ---------------------------------------------------------------------------
# 플레이스홀더 감지
# ---------------------------------------------------------------------------

class TestIsPlaceholder:
    def test_empty_string(self):
        assert is_placeholder("") is True

    def test_none(self):
        assert is_placeholder(None) is True

    def test_whitespace_only(self):
        assert is_placeholder("   ") is True

    def test_korean_placeholder(self):
        assert is_placeholder("없음") is True
        assert is_placeholder("최신 항목 없음") is True

    def test_english_placeholder(self):
        assert is_placeholder("no items") is True
        assert is_placeholder("none") is True

    def test_case_insensitive(self):
        assert is_placeholder("No Items") is True
        assert is_placeholder("NONE") is True

    def test_real_title(self):
        assert is_placeholder("GPT-5 발표") is False
        assert is_placeholder("LangChain 0.3 released") is False


# ---------------------------------------------------------------------------
# 타입 → 한국어 매핑
# ---------------------------------------------------------------------------

class TestMapTypeToKorean:
    @pytest.mark.parametrize("input_type,expected", [
        ("paper", "논문"),
        ("repo", "깃허브"),
        ("blog", "블로그"),
        ("news", "뉴스"),
        ("discussion", "토론"),
        ("announcement", "공지"),
        ("article", "아티클"),
        ("community", "커뮤니티"),
        ("unknown_type", "unknown_type"),
        ("", "미분류"),
        (None, "미분류"),
    ])
    def test_mapping(self, input_type, expected):
        assert map_type_to_korean(input_type) == expected


# ---------------------------------------------------------------------------
# 아이템 유효성 검사
# ---------------------------------------------------------------------------

class TestValidateItem:
    def test_valid_item(self):
        item = {"title": "GPT-5 출시", "url": "https://example.com/gpt5"}
        assert validate_item(item) is None

    def test_missing_url(self):
        item = {"title": "GPT-5 출시"}
        assert validate_item(item) is not None

    def test_empty_url(self):
        item = {"title": "GPT-5 출시", "url": ""}
        assert validate_item(item) is not None

    def test_missing_title(self):
        item = {"url": "https://example.com"}
        assert validate_item(item) is not None

    def test_placeholder_title(self):
        item = {"title": "없음", "url": "https://example.com"}
        assert validate_item(item) is not None


# ---------------------------------------------------------------------------
# Notion 프로퍼티 매핑
# ---------------------------------------------------------------------------

class TestMakePageProperties:
    def _base_item(self, **kwargs):
        base = {
            "source": "Anthropic News",
            "type": "news",
            "title": "Claude 4 출시",
            "url": "https://anthropic.com/claude4",
            "published": "2026-06-08T09:00:00+09:00",
            "summary_candidate": "Claude 4 공식 발표",
        }
        base.update(kwargs)
        return base

    def _base_meta(self):
        return {"generated_at_kst": "2026-06-08T08:45:00+09:00"}

    def test_title_preserved(self):
        props = make_page_properties(self._base_item(), self._base_meta())
        title_content = props["제목"]["title"][0]["text"]["content"]
        assert title_content == "Claude 4 출시"

    def test_source_preserved_as_source(self):
        """item.source가 출처 select로 정확히 들어가야 함 (URL 도메인 아님)."""
        props = make_page_properties(self._base_item(), self._base_meta())
        assert props["출처"]["select"]["name"] == "Anthropic News"

    def test_source_in_tags(self):
        """item.source가 태그에도 포함돼야 함."""
        props = make_page_properties(self._base_item(), self._base_meta())
        tag_names = [t["name"] for t in props["태그"]["multi_select"]]
        assert "Anthropic News" in tag_names
        assert "Daily AI Digest" in tag_names

    def test_type_mapped_to_korean(self):
        props = make_page_properties(self._base_item(type="news"), self._base_meta())
        assert props["토픽"]["select"]["name"] == "뉴스"

    def test_status_always_collected(self):
        props = make_page_properties(self._base_item(), self._base_meta())
        assert props["상태"]["select"]["name"] == "수집완료"

    def test_date_from_published(self):
        props = make_page_properties(self._base_item(), self._base_meta())
        assert props["수집일"]["date"]["start"] == "2026-06-08"

    def test_date_fallback_to_meta(self):
        item = self._base_item()
        item.pop("published", None)
        props = make_page_properties(item, self._base_meta())
        assert props["수집일"]["date"]["start"] == "2026-06-08"

    def test_url_set(self):
        props = make_page_properties(self._base_item(), self._base_meta())
        assert props["링크"]["url"] == "https://anthropic.com/claude4"

    def test_canonical_key_property_set(self):
        item = self._base_item(url="https://anthropic.com/news/claude4?utm_source=x")
        props = make_page_properties(item, self._base_meta())
        assert "Canonical Key" in props
        assert props["Canonical Key"]["rich_text"][0]["text"]["content"].startswith("url:https://anthropic.com/news/claude4")

    def test_no_topic_when_type_missing(self):
        item = self._base_item()
        item.pop("type", None)
        props = make_page_properties(item, self._base_meta())
        assert "토픽" not in props

    def test_source_fallback_to_url_host(self):
        item = self._base_item()
        item["source"] = ""
        props = make_page_properties(item, self._base_meta())
        assert props["출처"]["select"]["name"] == "anthropic.com"

    def test_title_truncated_at_2000(self):
        long_title = "A" * 3000
        props = make_page_properties(self._base_item(title=long_title), self._base_meta())
        content = props["제목"]["title"][0]["text"]["content"]
        assert len(content) <= 2000


# ---------------------------------------------------------------------------
# dry-run 동작
# ---------------------------------------------------------------------------

SAMPLE_RAW_JSON = {
    "meta": {
        "generated_at_kst": "2026-06-08T08:45:21+09:00",
        "raw_json_path": "/tmp/test.json",
    },
    "items": [
        {
            "source": "Anthropic News",
            "type": "news",
            "title": "Claude 4 출시",
            "url": "https://anthropic.com/news/claude4",
            "canonical_key": "url:https://anthropic.com/news/claude4",
            "published": "2026-06-08T01:00:00+09:00",
            "summary_candidate": "최신 Claude 모델 공개",
            "signals": {},
            "score": 5,
        },
        {
            "source": "HuggingFace",
            "type": "paper",
            "title": "Attention Is All You Need v2",
            "url": "https://huggingface.co/papers/attn-v2",
            "published": "2026-06-08T02:00:00+09:00",
            "summary_candidate": "",
            "signals": {},
            "score": 3,
        },
        {
            "source": "Reddit",
            "type": "community",
            "title": "없음",
            "url": "https://reddit.com/r/placeholder",
            "published": "2026-06-08T03:00:00+09:00",
            "summary_candidate": "",
            "signals": {},
            "score": 0,
        },
    ],
    "failed_sources": [],
}


class TestDryRun:
    def test_dry_run_no_notion_calls(self, monkeypatch):
        """dry-run에서 Notion API 절대 미호출."""
        import daily_ai_digest.notion_sync as ns
        calls = []
        monkeypatch.setattr(ns, "_notion_request", lambda *a, **kw: calls.append(a) or {})
        sync(SAMPLE_RAW_JSON, db_id=DEFAULT_DB_ID, token="fake", dry_run=True)
        assert calls == [], "dry_run=True인데 Notion API 호출됨"

    def test_dry_run_would_create_for_valid(self):
        result = sync(SAMPLE_RAW_JSON, dry_run=True)
        actions = [r["action"] for r in result["synced"]]
        assert all(a == "would_create" for a in actions)

    def test_dry_run_placeholder_skipped(self):
        result = sync(SAMPLE_RAW_JSON, dry_run=True)
        # "없음" 제목 아이템은 synced 아닌 skipped
        synced_urls = [r["url"] for r in result["synced"]]
        assert "https://reddit.com/r/placeholder" not in synced_urls
        skipped_urls = [r["url"] for r in result["skipped"]]
        assert "https://reddit.com/r/placeholder" in skipped_urls

    def test_dry_run_counts(self):
        result = sync(SAMPLE_RAW_JSON, dry_run=True)
        m = result["meta"]
        assert m["items_total"] == 3
        assert m["items_valid"] == 2
        assert m["items_synced"] == 2
        assert m["items_skipped"] == 1
        assert m["items_failed"] == 0
        assert m["dry_run"] is True

    def test_dry_run_limit(self):
        result = sync(SAMPLE_RAW_JSON, dry_run=True, limit=1)
        assert result["meta"]["items_total"] == 1

    def test_dry_run_output_schema(self):
        result = sync(SAMPLE_RAW_JSON, dry_run=True)
        assert set(result.keys()) == {"meta", "synced", "skipped", "failed", "source_counts"}
        assert set(result["meta"].keys()) >= {
            "json_path", "generated_at_kst", "notion_db_id",
            "items_total", "items_valid", "items_synced",
            "items_skipped", "items_failed", "dry_run",
        }

    def test_dry_run_source_counts(self):
        result = sync(SAMPLE_RAW_JSON, dry_run=True)
        counts = result["source_counts"]
        assert counts.get("Anthropic News") == 1
        assert counts.get("HuggingFace") == 1

    def test_dry_run_notion_page_id_null(self):
        result = sync(SAMPLE_RAW_JSON, dry_run=True)
        for item in result["synced"]:
            assert item["notion_page_id"] is None
            assert "canonical_key" in item

    def test_dry_run_source_field_preserved(self):
        """synced 항목의 source는 item.source 그대로여야 함."""
        result = sync(SAMPLE_RAW_JSON, dry_run=True)
        sources = {r["source"] for r in result["synced"]}
        assert "Anthropic News" in sources
        assert "HuggingFace" in sources

    def test_failed_sources_not_synced(self):
        """failed_sources는 절대 sync 대상이 아님."""
        raw = {
            **SAMPLE_RAW_JSON,
            "failed_sources": [
                {"source": "FakeSource", "error": "timeout"}
            ],
        }
        result = sync(raw, dry_run=True)
        synced_sources = [r["source"] for r in result["synced"]]
        assert "FakeSource" not in synced_sources

    def test_item_missing_url_skipped(self):
        raw = {
            "meta": SAMPLE_RAW_JSON["meta"],
            "items": [{"title": "Valid title", "source": "Test"}],
            "failed_sources": [],
        }
        result = sync(raw, dry_run=True)
        assert result["meta"]["items_skipped"] == 1
        assert result["meta"]["items_synced"] == 0
