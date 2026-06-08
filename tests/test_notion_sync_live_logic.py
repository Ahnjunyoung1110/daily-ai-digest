from __future__ import annotations

from daily_ai_digest.notion_sync import ensure_database_schema, query_existing_pages, sync


def test_ensure_database_schema_adds_missing_property(monkeypatch):
    import daily_ai_digest.notion_sync as ns
    calls = []

    def fake_request(method, path, token, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"properties": {"제목": {"type": "title"}}}
        return {}

    monkeypatch.setattr(ns, "_notion_request", fake_request)
    result = ensure_database_schema("db", "token")
    assert result["changed"] is True
    assert calls[-1] == ("PATCH", "/databases/db", {"properties": {"Canonical Key": {"rich_text": {}}}})


def test_query_existing_pages_reads_url_and_canonical_key(monkeypatch):
    import daily_ai_digest.notion_sync as ns

    def fake_request(method, path, token, body=None):
        return {
            "results": [
                {
                    "id": "page1",
                    "properties": {
                        "링크": {"url": "https://example.com/a"},
                        "Canonical Key": {"rich_text": [{"plain_text": "url:https://example.com/a"}]},
                    },
                }
            ],
            "has_more": False,
        }

    monkeypatch.setattr(ns, "_notion_request", fake_request)
    url_cache, key_cache = query_existing_pages("db", "token")
    assert url_cache["https://example.com/a"] == "page1"
    assert key_cache["url:https://example.com/a"] == "page1"


def test_sync_updates_by_canonical_key(monkeypatch):
    import daily_ai_digest.notion_sync as ns
    calls = []

    monkeypatch.setattr(ns, "ensure_database_schema", lambda *a, **k: {"changed": False})
    monkeypatch.setattr(ns, "query_existing_pages", lambda *a, **k: ({}, {"url:https://example.com/a": "page1"}))
    monkeypatch.setattr(ns, "update_page", lambda page_id, item, meta, token, update_body=True: calls.append(("update", page_id, item["canonical_key"], update_body)))
    monkeypatch.setattr(ns, "create_page", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not create")))
    monkeypatch.setattr(ns, "mark_notion_page", lambda *a, **k: 1)

    raw = {
        "meta": {"generated_at_kst": "2026-06-08T08:45:00+09:00"},
        "items": [{"title": "A", "url": "https://example.com/a", "canonical_key": "url:https://example.com/a", "source": "OpenAI"}],
    }
    result = sync(raw, token="token", dry_run=False)
    assert result["synced"][0]["action"] == "updated_by_canonical_key"
    assert calls == [("update", "page1", "url:https://example.com/a", True)]
