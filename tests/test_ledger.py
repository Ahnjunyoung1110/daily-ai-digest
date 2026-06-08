from __future__ import annotations

from datetime import datetime

from daily_ai_digest.config import KST
from daily_ai_digest.ledger import canonical_key, mark_digest_sent, mark_notion_page, mark_selected, normalize_url, upsert_seen
from daily_ai_digest.output import make_item


def test_normalize_url_strips_tracking_params():
    assert normalize_url("https://Example.com/a/?utm_source=x&b=1#frag") == "https://example.com/a?b=1"


def test_canonical_key_github_repo():
    item = make_item("GitHub", "repo", "A/B", "https://github.com/A/B?utm_source=x", None)
    assert canonical_key(item) == "github:a/b"


def test_canonical_key_reddit_comment_id():
    item = make_item("Reddit LocalLLaMA", "community", "Post", "https://www.reddit.com/r/LocalLLaMA/comments/abc123/title/", None)
    assert canonical_key(item) == "reddit:abc123"


def test_upsert_seen_and_mark_selected(tmp_path):
    db = tmp_path / "ledger.sqlite"
    now = datetime.now(KST)
    item = make_item("OpenAI", "blog", "LLM inference benchmark release", "https://openai.com/a", now.isoformat())
    item["canonical_key"] = canonical_key(item)
    assert upsert_seen([item], now, db) == 1
    assert mark_selected([item], now, db) == 1
    assert mark_digest_sent([item["canonical_key"]], now, db) == 1
    assert mark_notion_page(item["canonical_key"], "page1", db) == 1
