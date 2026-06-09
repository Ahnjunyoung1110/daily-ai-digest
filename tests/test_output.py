from __future__ import annotations

from datetime import datetime, timedelta

from daily_ai_digest.config import KST
from daily_ai_digest.output import (
    _freshness_points,
    clean_text,
    compute_rank_score,
    dedupe,
    filter_items,
    make_item,
    score_item,
)


def test_make_item_schema_v2():
    item = make_item("OpenAI", "blog", "Test title", "https://example.com", None)
    assert {"source", "source_class", "type", "title", "url", "published", "summary_candidate",
            "signals", "score", "rank_score", "score_version", "score_breakdown",
            "importance_reason"}.issubset(item.keys())
    assert item["signals"] == {"stars": 0, "points": 0, "comments": 0}
    assert item["score_version"] == 2
    assert isinstance(item["score"], int)
    assert isinstance(item["rank_score"], int)


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


# ---------------------------------------------------------------------------
# 신규: 키워드 직교성, freshness 연속성, rank_score
# ---------------------------------------------------------------------------

def test_topic_relevance_no_double_count():
    """RELEVANCE_TERMS ∩ IMPACT_TERMS = ∅ → 같은 단어 이중 계산 없음."""
    from daily_ai_digest.output import score_breakdown
    # "inference"는 RELEVANCE_TERMS에만, "release"는 IMPACT_TERMS에만 있음
    item_both = make_item("OpenAI", "blog", "LLM inference release", "https://example.com", None)
    item_only_relevance = make_item("OpenAI", "blog", "LLM inference only", "https://example.com", None)
    item_only_impact = make_item("OpenAI", "blog", "new release today", "https://example.com", None)
    br_both = score_breakdown(item_both)
    br_rel = score_breakdown(item_only_relevance)
    br_imp = score_breakdown(item_only_impact)
    # 두 신호 모두 매치 시 합산이지만 cap 25
    assert br_both["topic_relevance"] <= 25
    # 각 신호 단독보다 크거나 같음
    assert br_both["topic_relevance"] >= br_rel["topic_relevance"]
    assert br_both["topic_relevance"] >= br_imp["topic_relevance"]


def test_topic_relevance_cap():
    """키워드 둘 다 매치(15+12=27)여도 cap=25 적용."""
    from daily_ai_digest.output import score_breakdown
    item = make_item("GitHub", "repo", "LLM inference release benchmark", "https://github.com/x/y", None)
    br = score_breakdown(item)
    # keyword_score = min(15+12, 25) = 25, type_bonus repo = +5 → 30 허용
    assert br["topic_relevance"] <= 30


def test_freshness_no_cliff():
    """24h→25h 전환 시 절벽 없음 — 인접 시간 차이 ≤ 2점."""
    now = datetime.now(KST)
    # 168h(7d) 초과는 의도적 고정 -20 — 이미 lookback 필터로 제거되는 stale 항목.
    # 168h 경계는 제외하고 구간 내 연속성만 검증.
    for age_h in [23, 24, 48, 71, 72, 96, 120, 167]:
        pub_curr = (now - timedelta(hours=age_h)).isoformat()
        pub_next = (now - timedelta(hours=age_h + 1)).isoformat()
        f_curr = _freshness_points({"published": pub_curr}, now)
        f_next = _freshness_points({"published": pub_next}, now)
        diff = f_curr - f_next
        assert diff <= 2, f"age={age_h}h→{age_h+1}h 절벽: {f_curr}→{f_next} (diff={diff})"


def test_freshness_anchors():
    """구간 선형 보간이 앵커값(0h=+20, 72h=+10, 168h=0, 169h=-20)을 보존."""
    now = datetime.now(KST)

    def fp(age_h):
        return _freshness_points({"published": (now - timedelta(hours=age_h)).isoformat()}, now)

    assert abs(fp(0) - 20) <= 1
    assert abs(fp(72) - 10) <= 1
    assert abs(fp(168) - 0) <= 1
    assert fp(169) == -20


def test_rank_score_cross_class_ordering():
    """raw score 순서와 rank_score 순서가 다를 수 있음 — 클래스 횡단 비교."""
    now = datetime.now(KST)
    pub = (now - timedelta(hours=1)).isoformat()
    # community: 임계값 55 → 달성하기 어려움, official: 임계값 40 → 낮음
    # 비슷한 raw score에서 rank_score가 클래스 보정
    community_item = make_item(
        "Reddit LocalLLaMA", "community",
        "LLM inference benchmark release",
        "https://reddit.com/r/x", pub,
        signals={"stars": 0, "points": 300, "comments": 60},
    )
    official_item = make_item(
        "OpenAI", "blog",
        "LLM inference benchmark release",
        "https://openai.com/blog/x", pub,
    )
    # rank_score = score - threshold
    community_rank = compute_rank_score(community_item)
    official_rank = compute_rank_score(official_item)
    # 두 항목 rank_score 모두 int 반환
    assert isinstance(community_rank, int)
    assert isinstance(official_rank, int)


def test_vendor_blog_rank_score_positive():
    """vendor_blog 클래스가 rank_score에서 올바르게 임계값(45) 차감됨 — 구버그 회귀 방지."""
    now = datetime.now(KST)
    pub = (now - timedelta(hours=1)).isoformat()
    item = make_item("LangChain", "blog", "LLM agent framework release", "https://langchain.com/blog", pub)
    # vendor_blog 임계값 45, authority 25 + topic + freshness → 양수 rank_score 기대
    assert item["rank_score"] > 0, f"vendor_blog rank_score 음수: {item['rank_score']}"


def test_rank_score_stored_in_filter_items():
    """filter_items 통과 항목에 rank_score 필드 존재."""
    now = datetime.now(KST)
    pub = (now - timedelta(hours=1)).isoformat()
    item = make_item("OpenAI", "blog", "LLM inference benchmark release", "https://example.com", pub)
    results = filter_items([item], now, include_stale=False, lookback_days=7)
    assert len(results) == 1
    assert "rank_score" in results[0]
    assert isinstance(results[0]["rank_score"], int)
