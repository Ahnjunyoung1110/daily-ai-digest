from __future__ import annotations

from daily_ai_digest.notion_sync import (
    IMPORTANT_PROP,
    SCORE_PROP,
    clear_stale_important_pages,
    ensure_database_schema,
    make_page_blocks,
    make_page_properties,
    normalize_important_flags,
    replace_page_children,
)


def _joined_block_text(blocks: list[dict]) -> str:
    texts = []
    for b in blocks:
        payload = b[b["type"]]
        texts.extend(rt["text"]["content"] for rt in payload.get("rich_text", []))
    return "\n".join(texts)


def test_korean_title_property_preferred():
    item = {
        "title": "Introducing GPT-Rosalind",
        "title_ko": "GPT-Rosalind 공개",
        "url": "https://openai.com/example",
        "summary_candidate": "English summary",
        "summary_ko": "한국어 요약",
        "source": "OpenAI",
        "type": "blog",
    }
    props = make_page_properties(item, {"generated_at_kst": "2026-06-08T08:45:00+09:00"})
    assert props["제목"]["title"][0]["text"]["content"] == "GPT-Rosalind 공개"
    assert props["한줄요약"]["rich_text"][0]["text"]["content"] == "한국어 요약"
    assert props[IMPORTANT_PROP]["checkbox"] is False


def test_important_checkbox_property_true():
    item = {
        "title": "Major model launch",
        "url": "https://example.com/important",
        "source": "OpenAI",
        "type": "announcement",
        "important": True,
    }
    props = make_page_properties(item, {"generated_at_kst": "2026-06-08T08:45:00+09:00"})
    assert props[IMPORTANT_PROP] == {"checkbox": True}


def test_page_blocks_are_readable_article_structure():
    item = {
        "title": "Original English Title",
        "title_ko": "한국어 제목",
        "url": "https://example.com/a",
        "source": "OpenAI",
        "type": "blog",
        "summary_ko": "핵심 요약 문장",
        "key_points_ko": ["첫 번째 핵심", "두 번째 핵심"],
        "why_it_matters_ko": "왜 중요한지 설명",
        "action_items_ko": ["확인할 것"],
        "score": 80,
    }
    joined = _joined_block_text(make_page_blocks(item))
    assert "핵심 정리" in joined
    assert "첫 번째 핵심" in joined
    assert "왜 중요한가" in joined
    assert "확인/활용 포인트" in joined
    assert "원문 제목: Original English Title" in joined


def test_page_blocks_filter_generic_enrichment_metadata():
    item = {
        "title": "dots.tts Technical Report",
        "url": "https://huggingface.co/papers/2606.07080",
        "source": "HF Papers",
        "type": "paper",
        "summary_candidate": "We present dots.tts, a 2B-parameter continuous autoregressive text-to-speech foundation model.",
        "summary_ko": "HF Papers의 논문 항목입니다. 원문 제목은 \"dots.tts Technical Report\"이며, 요약 후보는 \"We present dots.tts...\"입니다.",
        "key_points_ko": [
            "출처: HF Papers (research)",
            "원문 제목: dots.tts Technical Report",
            "연속 잠재 공간에서 음성을 모델링하는 2B 파라미터 TTS 모델입니다.",
        ],
    }
    joined = _joined_block_text(make_page_blocks(item))
    readable_section = joined.split("원문 및 메타데이터")[0]
    assert "요약 후보는" not in readable_section
    assert "출처: HF Papers (research)" not in readable_section
    assert "연속 잠재 공간에서 음성을 모델링" in joined


def test_normalize_important_flags_bounds_count_and_preserves_prompt_marks():
    items = [
        {"title": f"item {i}", "url": f"https://example.com/{i}", "score": i, "type": "blog"}
        for i in range(10)
    ]
    items[1]["important"] = True
    count = normalize_important_flags(items)
    assert count == 3
    assert items[1]["important"] is True
    assert sum(1 for item in items if item.get("important")) == 3


def test_normalize_important_flags_trims_too_many_marks():
    items = [
        {"title": f"item {i}", "url": f"https://example.com/{i}", "score": i, "type": "blog", "important": True}
        for i in range(8)
    ]
    assert normalize_important_flags(items) == 5
    assert sum(1 for item in items if item.get("important")) == 5


def test_ensure_database_schema_creates_important_checkbox(monkeypatch):
    import daily_ai_digest.notion_sync as ns

    calls = []

    def fake_request(method, path, token, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"properties": {"Canonical Key": {"type": "rich_text"}}}
        return {}

    monkeypatch.setattr(ns, "_notion_request", fake_request)
    result = ensure_database_schema("db1", "token")
    assert result["changed"] is True
    assert result["properties"][IMPORTANT_PROP]["type"] == "checkbox"
    assert calls[-1] == (
        "PATCH",
        "/databases/db1",
        {"properties": {
            IMPORTANT_PROP: {"checkbox": {}},
            SCORE_PROP: {"number": {"format": "number"}},
        }},
    )


def test_clear_stale_important_pages_unchecks_pages_outside_current_sync(monkeypatch):
    import daily_ai_digest.notion_sync as ns

    calls = []

    def fake_request(method, path, token, body=None):
        calls.append((method, path, body))
        if method == "POST":
            return {
                "results": [
                    {"id": "keep-page"},
                    {"id": "stale-page"},
                ],
                "has_more": False,
            }
        return {}

    monkeypatch.setattr(ns, "_notion_request", fake_request)
    monkeypatch.setattr(ns.time, "sleep", lambda _: None)

    cleared = clear_stale_important_pages("db1", "token", {"keep-page"})
    assert cleared == 1
    assert (
        "PATCH",
        "/pages/stale-page",
        {"properties": {IMPORTANT_PROP: {"checkbox": False}}},
    ) in calls
    assert not any(call[1] == "/pages/keep-page" for call in calls)


def test_page_blocks_meta_section_trimmed():
    """body '원문 및 메타데이터' 섹션에 score_breakdown/signals/Canonical Key/점수 없음."""
    item = {
        "title": "Test Item",
        "url": "https://example.com/test",
        "source": "Test Source",
        "type": "paper",
        "published": "2026-06-08T09:00:00+09:00",
        "score": 80,
        "canonical_key": "url:https://example.com/test",
        "score_breakdown": {"freshness": 20, "popularity": 5},
        "signals": {"stars": 100, "points": 50},
    }
    joined = _joined_block_text(make_page_blocks(item))
    # 유지: heading + 기본 메타
    assert "원문 및 메타데이터" in joined
    assert "원문 제목: Test Item" in joined
    assert "출처: Test Source" in joined
    assert "링크: https://example.com/test" in joined
    # 제거: score_breakdown, signals, Canonical Key, 점수
    assert "score_breakdown" not in joined
    assert "signals" not in joined
    assert "Canonical Key" not in joined
    assert "점수:" not in joined


def test_replace_page_children_archives_then_appends(monkeypatch):
    import daily_ai_digest.notion_sync as ns
    calls = []

    def fake_request(method, path, token, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"results": [{"id": "old1"}], "has_more": False}
        return {}

    monkeypatch.setattr(ns, "_notion_request", fake_request)
    count = replace_page_children("page1", [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}], "token")
    assert count == 1
    assert ("PATCH", "/blocks/old1", {"archived": True}) in calls
    assert calls[-1][0] == "PATCH"
    assert calls[-1][1] == "/blocks/page1/children"
