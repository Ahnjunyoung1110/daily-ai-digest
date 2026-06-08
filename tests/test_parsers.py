from __future__ import annotations

from daily_ai_digest.parsers.html import extract_anchor_cards, extract_article_cards

ANCHOR_HTML = """
<html><body>
  <a href="/news/article-llm-update">
    <h2>LLM Update</h2>
    <p>New language model released</p>
    <time datetime="2026-06-01">June 1, 2026</time>
  </a>
  <a href="/news/agent-benchmark">
    <h2>Agent Benchmark Results</h2>
    <p>New eval for AI agents</p>
    <time datetime="2026-06-02">June 2, 2026</time>
  </a>
  <a href="/about">Unrelated link</a>
</body></html>
"""

ARTICLE_HTML = """
<html><body>
  <article>
    <h2>Transformer Research</h2>
    <a href="/blog/transformer-research">Read more</a>
    <p>Latest findings on transformers</p>
    <time datetime="2026-05-30">May 30</time>
  </article>
  <article>
    <h2>RAG Improvements</h2>
    <a href="/blog/rag-improvements">Read more</a>
    <p>Better retrieval augmented generation</p>
  </article>
  <article>
    <h2>Unrelated Post</h2>
    <a href="/unrelated/post">Read</a>
  </article>
</body></html>
"""


def test_extract_anchor_cards_count():
    items = extract_anchor_cards(ANCHOR_HTML, "https://example.com", r"/news/[^/?#]+", "TestSource", "blog")
    assert len(items) == 2


def test_extract_anchor_cards_title():
    items = extract_anchor_cards(ANCHOR_HTML, "https://example.com", r"/news/[^/?#]+", "TestSource", "blog")
    assert items[0]["title"] == "LLM Update"


def test_extract_anchor_cards_url():
    items = extract_anchor_cards(ANCHOR_HTML, "https://example.com", r"/news/[^/?#]+", "TestSource", "blog")
    assert items[0]["url"] == "https://example.com/news/article-llm-update"


def test_extract_anchor_cards_date():
    items = extract_anchor_cards(ANCHOR_HTML, "https://example.com", r"/news/[^/?#]+", "TestSource", "blog")
    assert items[0]["published"] is not None
    assert "2026-06-01" in items[0]["published"]


def test_extract_anchor_cards_source_and_type():
    items = extract_anchor_cards(ANCHOR_HTML, "https://example.com", r"/news/[^/?#]+", "MySource", "paper")
    assert items[0]["source"] == "MySource"
    assert items[0]["type"] == "paper"


def test_extract_article_cards_count():
    items = extract_article_cards(ARTICLE_HTML, "https://example.com", r"/blog/[^/?#]+", "TestSource", "blog")
    assert len(items) == 2


def test_extract_article_cards_title():
    items = extract_article_cards(ARTICLE_HTML, "https://example.com", r"/blog/[^/?#]+", "TestSource", "blog")
    titles = {it["title"] for it in items}
    assert "Transformer Research" in titles
    assert "RAG Improvements" in titles


def test_extract_article_cards_date():
    items = extract_article_cards(ARTICLE_HTML, "https://example.com", r"/blog/[^/?#]+", "TestSource", "blog")
    dated = [it for it in items if it["published"]]
    assert len(dated) >= 1
    assert "2026-05-30" in dated[0]["published"]
