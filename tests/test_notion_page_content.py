from __future__ import annotations

from daily_ai_digest.notion_sync import make_page_blocks, make_page_properties, replace_page_children


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
    blocks = make_page_blocks(item)
    texts = []
    for b in blocks:
        payload = b[b["type"]]
        texts.extend(rt["text"]["content"] for rt in payload.get("rich_text", []))
    joined = "\n".join(texts)
    assert "핵심 정리" in joined
    assert "첫 번째 핵심" in joined
    assert "왜 중요한가" in joined
    assert "확인/활용 포인트" in joined
    assert "원문 제목: Original English Title" in joined


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
