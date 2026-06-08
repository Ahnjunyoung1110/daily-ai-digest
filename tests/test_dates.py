from datetime import datetime

from daily_ai_digest.dates import parse_date, parse_date_from_url, parse_loose_date


def test_deepseek_news_url_date():
    assert parse_date_from_url("https://api-docs.deepseek.com/news/news251201").startswith("2025-12-01")


def test_iso_z_date_parses():
    parsed = parse_date("2026-06-04T00:00:00.000Z")
    assert parsed is not None
    datetime.fromisoformat(parsed)


def test_rfc822_date_parses():
    parsed = parse_date("Thu, 05 Jun 2026 08:45:00 +0000")
    assert parsed is not None
    assert "2026-06-05" in parsed


def test_date_from_url_generic():
    assert parse_date_from_url("https://example.com/2026/01/15/article").startswith("2026-01-15")


def test_parse_loose_date_time_tag():
    html = '<time datetime="2026-05-20">May 20, 2026</time>'
    parsed = parse_loose_date(html)
    assert parsed is not None
    assert "2026-05-20" in parsed


def test_parse_loose_date_month_year():
    parsed = parse_loose_date("Published: June 2026")
    assert parsed is not None
    assert "2026-06" in parsed


def test_parse_date_returns_none_for_garbage():
    assert parse_date("not a date at all") is None


def test_parse_date_from_url_no_match():
    assert parse_date_from_url("https://example.com/about") is None
