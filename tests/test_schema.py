from __future__ import annotations

from datetime import datetime, timedelta

from daily_ai_digest.config import KST
from daily_ai_digest.output import build_result

REQUIRED_TOP_KEYS = {"meta", "items", "failed_sources"}
REQUIRED_META_KEYS = {
    "generated_at_kst",
    "since_kst",
    "recency_cutoff_kst",
    "recency_cutoff_hours",
    "yesterday_date_kst",
    "hn_since_epoch_yesterday_midnight_kst",
    "user_agent",
    "antigravity_cli",
    "github_token_present",
    "log_path",
    "raw_json_path",
    "source_statuses",
    "sources_collected_no_latest",
    "sources_date_issues",
    "unknown_date_candidates",
    "unknown_date_candidates_total",
}


def _make_result(**overrides):
    now = datetime.now(KST)
    defaults = dict(
        now=now,
        since=now - timedelta(days=1),
        cutoff_24h=now - timedelta(hours=24),
        yesterday_midnight=(now.date() - timedelta(days=1)).isoformat(),
        ts_epoch=int(datetime.combine(now.date() - timedelta(days=1), datetime.min.time(), tzinfo=KST).timestamp()),
        out_items=[],
        failures=[],
        statuses=[],
        unknown_date_candidates=[],
        antigravity_path=None,
    )
    defaults.update(overrides)
    return build_result(**defaults)


def test_top_level_keys():
    result = _make_result()
    assert REQUIRED_TOP_KEYS.issubset(result.keys())


def test_meta_keys():
    result = _make_result()
    assert REQUIRED_META_KEYS.issubset(result["meta"].keys())


def test_items_and_failures_are_lists():
    result = _make_result()
    assert isinstance(result["items"], list)
    assert isinstance(result["failed_sources"], list)


def test_meta_list_fields_are_lists():
    result = _make_result()
    meta = result["meta"]
    for field in ("source_statuses", "sources_collected_no_latest", "sources_date_issues", "unknown_date_candidates"):
        assert isinstance(meta[field], list), f"{field} should be a list"


def test_meta_scalar_types():
    result = _make_result()
    meta = result["meta"]
    assert isinstance(meta["unknown_date_candidates_total"], int)
    assert isinstance(meta["github_token_present"], bool)
    assert isinstance(meta["recency_cutoff_hours"], int)
    assert meta["recency_cutoff_hours"] == 24


def test_items_passed_through():
    from daily_ai_digest.output import make_item
    now = datetime.now(KST)
    item = make_item("OpenAI", "blog", "Test", "https://example.com", now.isoformat())
    result = _make_result(out_items=[item])
    assert len(result["items"]) == 1
    assert result["items"][0]["source"] == "OpenAI"


def test_failures_passed_through():
    result = _make_result(failures=[{"source": "TestSource", "reason": "timeout"}])
    assert len(result["failed_sources"]) == 1
    assert result["failed_sources"][0]["source"] == "TestSource"


def test_unknown_date_candidates_capped():
    from daily_ai_digest.config import UNKNOWN_DATE_CANDIDATE_LIMIT
    candidates = [{"source": "X", "title": f"item {i}"} for i in range(UNKNOWN_DATE_CANDIDATE_LIMIT + 10)]
    result = _make_result(unknown_date_candidates=candidates)
    assert len(result["meta"]["unknown_date_candidates"]) == UNKNOWN_DATE_CANDIDATE_LIMIT
    assert result["meta"]["unknown_date_candidates_total"] == UNKNOWN_DATE_CANDIDATE_LIMIT + 10
