from __future__ import annotations

from datetime import datetime, timedelta

from daily_ai_digest.config import KST
from daily_ai_digest.output import clean_text, dedupe, filter_items, make_item, score_item


def test_make_item_schema_v2():
    item = make_item("OpenAI", "blog", "Test title", "https://example.com", None)
    assert {"source", "source_class", "type", "title", "url", "published", "summary_candidate", "signals", "score", "score_version", "score_breakdown", "importance_reason"}.issubset(item.keys())
    assert item["signals"] == {"stars": 0, "points": 0, "comments": 0}
    assert item["score_version"] == 2
    assert isinstance(item["score"], int)


def test_make_item_custom_signals():
    signals = {"stars": 100, "points": 0, "comments": 0}
    item = make_item("GitHub", "repo", "cool-repo", "https://github.com/x/y", None, signals=signals)
    assert item["signals"]["stars"] == 100


def test_make_item_truncates_title():
    long_title = "A" * 300
    item = make_item("OpenAI", "blog", long_title, "https://example.com", None)
    assert len(item["title"]) <= 240


def test_score_v2_high_authority_scale():
    item = make_item("OpenAI", "blog", "LLM inference benchmark release", "https://openai.com/test", None)
    assert item["score"] >= 60
    assert item["score_breakdown"]["source_authority"] == 40


def test_score_promo_terms_reduce_score():
    item_promo = make_item("OpenAI", "blog", "Join our webinar today", "https://openai.com/webinar", None)
    item_normal = make_item("OpenAI", "blog", "LLM inference update", "https://openai.com/update", None)
    assert item_promo["score"] < item_normal["score"]


def test_score_reddit_requires_popularity():
    low = make_item("Reddit LocalLLaMA", "community", "What’s your most unusual AI you use daily?", "https://reddit.com/r/LocalLLaMA/comments/x", None, signals={"stars": 0, "points": 3, "comments": 0})
    high = make_item("Reddit LocalLLaMA", "community", "New open weights LLM inference benchmark release", "https://reddit.com/r/LocalLLaMA/comments/y", None, signals={"stars": 0, "points": 250, "comments": 80})
    assert high["score"] > low["score"]
    assert high["score"] >= 55
    assert low["score"] < 55


def test_score_paper_bonus():
    item = make_item("arXiv cs.AI", "paper", "Transformer benchmark", "https://arxiv.org/abs/2406.0001", None)
    item_blog = make_item("arXiv cs.AI", "blog", "Transformer benchmark", "https://arxiv.org/abs/2406.0001", None)
    assert item["score"] > item_blog["score"]


def test_dedupe_by_url():
    items = [
        make_item("OpenAI", "blog", "Title A", "https://example.com/a", None),
        make_item("OpenAI", "blog", "Title A duplicate", "https://example.com/a", None),
        make_item("OpenAI", "blog", "Title B", "https://example.com/b", None),
    ]
    assert len(dedupe(items)) == 2


def test_dedupe_trailing_slash():
    items = [
        make_item("OpenAI", "blog", "Title A", "https://example.com/a/", None),
        make_item("OpenAI", "blog", "Title A", "https://example.com/a", None),
    ]
    assert len(dedupe(items)) == 1


def test_dedupe_sorted_by_score():
    low = make_item("unknown", "blog", "random post", "https://example.com/low", None)
    high = make_item("OpenAI", "blog", "LLM inference agent MCP", "https://example.com/high", None)
    result = dedupe([low, high])
    assert result[0]["url"] == "https://example.com/high"


def test_filter_items_outside_lookback_drops():
    now = datetime.now(KST)
    old_pub = (now - timedelta(days=8)).isoformat()
    item = make_item("OpenAI", "blog", "LLM inference update", "https://example.com", old_pub)
    assert filter_items([item], now, include_stale=False, lookback_days=7) == []


def test_filter_items_recent_high_quality_passes():
    now = datetime.now(KST)
    recent_pub = (now - timedelta(hours=1)).isoformat()
    item = make_item("OpenAI", "blog", "LLM inference benchmark release", "https://example.com", recent_pub)
    assert len(filter_items([item], now, include_stale=False, lookback_days=7)) == 1


def test_filter_items_include_stale_bypasses_production_quality():
    now = datetime.now(KST)
    old_pub = (now - timedelta(days=10)).isoformat()
    item = make_item("OpenAI", "blog", "LLM news from long ago", "https://example.com", old_pub)
    assert len(filter_items([item], now, include_stale=True, lookback_days=7)) == 1


def test_filter_items_no_ai_terms_dropped():
    now = datetime.now(KST)
    recent_pub = (now - timedelta(hours=1)).isoformat()
    item = make_item("Cooking", "blog", "Best pasta recipes ever", "https://cooking.com/pasta", recent_pub)
    assert filter_items([item], now, include_stale=False, lookback_days=7) == []


def test_filter_items_low_signal_reddit_dropped():
    now = datetime.now(KST)
    recent_pub = (now - timedelta(hours=1)).isoformat()
    item = make_item("Reddit LocalLLaMA", "community", "What’s your most unusual non-LLM AI you use daily?", "https://reddit.com/r/LocalLLaMA/comments/x", recent_pub, signals={"stars": 0, "points": 3, "comments": 0})
    assert filter_items([item], now, include_stale=False, lookback_days=7) == []


def test_filter_items_high_signal_reddit_passes():
    now = datetime.now(KST)
    recent_pub = (now - timedelta(days=2)).isoformat()
    item = make_item("Reddit LocalLLaMA", "community", "Open weights LLM inference benchmark release", "https://reddit.com/r/LocalLLaMA/comments/y", recent_pub, signals={"stars": 0, "points": 250, "comments": 80})
    assert len(filter_items([item], now, include_stale=False, lookback_days=7)) == 1


def test_clean_text_strips_html():
    assert clean_text("<b>Hello</b> &amp; world") == "Hello & world"


def test_clean_text_truncates():
    assert len(clean_text("x" * 1000, n=100)) == 100
