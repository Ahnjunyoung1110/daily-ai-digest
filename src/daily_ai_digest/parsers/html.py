from __future__ import annotations

import html
import json
import re

from ..config import log
from ..dates import enrich_html_dates, parse_date, parse_date_from_url, parse_loose_date, _unescape_jsonish
from ..fetch import fetch_bytes
from ..output import attr_value, make_item, normalize_url, strip_tags
from ..sources import DEBUG_HTML_SOURCES

ANCHOR_WINDOW = 900
DEEPSEEK_LINKS_LIMIT = 4
HTML_ENTRY_LIMIT = 12


def first_match_text(patterns: list[str], segment: str, n: int = 240) -> str:
    for pat in patterns:
        m = re.search(pat, segment, re.I | re.S)
        if m:
            txt = strip_tags(m.group(1), n)
            if txt:
                return txt
    return ""


def log_debug_html_item(source: str, item: dict, stage: str = "parsed") -> None:
    if source not in DEBUG_HTML_SOURCES:
        return
    log(
        "DEBUG html_item "
        f"stage={stage} source={source} "
        f"title={json.dumps(item.get('title') or '', ensure_ascii=False)} "
        f"url={item.get('url') or ''} "
        f"date={item.get('published') or ''}"
    )


def make_html_item(source: str, typ: str, title: str, url: str, published: str | None, summary: str = "") -> dict:
    return make_item(source, typ, title, url, published, summary)


def extract_anchor_cards(
    html_text: str, base_url: str, href_re: str, source: str, typ: str, limit: int = HTML_ENTRY_LIMIT
) -> list[dict]:
    out = []
    seen: set[str] = set()
    for m in re.finditer(
        r"<a\b(?P<tag>[^>]*\bhref\s*=\s*(?:['\"][^'\"]+['\"]|[^\s>]+)[^>]*)>(?P<body>.*?)</a>",
        html_text, re.I | re.S,
    ):
        tag = m.group("tag")
        href = attr_value(tag, "href") or ""
        url = normalize_url(href, base_url)
        if not re.search(href_re, url, re.I) or url in seen:
            continue
        start = max(0, m.start() - ANCHOR_WINDOW)
        end = min(len(html_text), m.end() + ANCHOR_WINDOW)
        segment = html_text[start:end]
        title = first_match_text(
            [r"<h[1-4][^>]*>(.*?)</h[1-4]>", r"<span[^>]*title[^>]*>(.*?)</span>"],
            m.group("body"),
        )
        if not title:
            title = attr_value(tag, "aria-label") or attr_value(tag, "title") or ""
            title = re.sub(r"^(Read|View|Learn more:?|View paper)\s+", "", title, flags=re.I).strip()
        if not title:
            title = first_match_text(
                [r"<h[1-4][^>]*>(.*?)</h[1-4]>", r"<span[^>]*title[^>]*>(.*?)</span>"],
                segment,
            )
        if not title:
            text = strip_tags(m.group("body"), 240)
            if text and not re.fullmatch(r"(?i)(learn more|view paper|featured|read more)", text):
                title = text
        if not title or re.fullmatch(r"(?i)(learn more|view paper|trending papers|weekly|monthly|english|中文.*)", title):
            continue
        summary = first_match_text(
            [r"<p[^>]*>(.*?)</p>", r"<meta[^>]+name=['\"]description['\"][^>]+content=['\"](.*?)['\"]"],
            segment, 500,
        )
        out.append(make_html_item(source, typ, title, url, parse_loose_date(segment), summary))
        seen.add(url)
        if len(out) >= limit:
            break
    return out


def extract_article_cards(
    html_text: str, base_url: str, href_re: str, source: str, typ: str, limit: int = HTML_ENTRY_LIMIT
) -> list[dict]:
    out = []
    seen: set[str] = set()
    for am in re.finditer(r"<article\b.*?</article>", html_text, re.I | re.S):
        segment = am.group(0)
        href = ""
        for hm in re.finditer(r"<a\b[^>]*\bhref\s*=\s*(['\"]?)([^'\" >]+)\1", segment, re.I | re.S):
            candidate = normalize_url(hm.group(2), base_url)
            if re.search(href_re, candidate, re.I):
                href = candidate
                break
        if not href or href in seen:
            continue
        title = first_match_text([r"<h[1-4][^>]*>(.*?)</h[1-4]>", r"<a\b[^>]*\btitle=['\"]([^'\"]+)['\"]"], segment)
        if not title:
            title = first_match_text([r"<a\b[^>]*>(.*?)</a>"], segment)
        if not title:
            continue
        summary = first_match_text([r"<p[^>]*>(.*?)</p>"], segment, 500)
        out.append(make_html_item(source, typ, title, href, parse_loose_date(segment), summary))
        seen.add(href)
        if len(out) >= limit:
            break
    return out


def _anthropic_date_map(html_text: str) -> dict[str, str]:
    """Anthropic 임베디드 Sanity/Next 데이터에서 slug → 발행일 추출."""
    text = _unescape_jsonish(html_text)
    dates: dict[str, str] = {}
    for m in re.finditer(r'"publishedOn"\s*:\s*"([^"T]+(?:T[^"]+)?)"', text, re.I):
        date_raw = m.group(1)
        window_start = max(0, m.start() - 1800)
        window = text[window_start: min(len(text), m.end() + 1800)]
        rel_match_end = m.end() - window_start
        slug = None
        # Current Anthropic data stores slugs as {"slug":{"current":"..."}}.
        before = list(re.finditer(r'"current"\s*:\s*"([^"/]+)"', window[:rel_match_end], re.I))
        if before:
            slug = before[-1].group(1)
        after = re.search(r'"current"\s*:\s*"([^"/]+)"', window[rel_match_end:], re.I)
        if after:
            slug = slug or after.group(1)
        if slug:
            parsed = parse_date(date_raw) or parse_loose_date(date_raw)
            if parsed:
                dates[slug] = parsed
    return dates


def parse_anthropic(html_text: str, base_url: str) -> list[dict]:
    items = extract_anchor_cards(html_text, base_url, r"/news/[^/?#]+/?$", "Anthropic News", "blog")
    date_map = _anthropic_date_map(html_text)
    for item in items:
        if item.get("published"):
            continue
        slug = (item.get("url") or "").rstrip("/").rsplit("/", 1)[-1]
        if slug in date_map:
            item["published"] = date_map[slug]
            item["date_recovery"] = "anthropic_embedded_publishedOn"
    return items


def parse_deepmind(html_text: str, base_url: str) -> list[dict]:
    items = extract_article_cards(html_text, base_url, r"(?:deepmind\.google/blog/|blog\.google/.+ai)", "Google DeepMind", "blog")
    return items or extract_anchor_cards(html_text, base_url, r"(?:deepmind\.google/blog/|blog\.google/.+ai)", "Google DeepMind", "blog")


def parse_meta_ai(html_text: str, base_url: str) -> list[dict]:
    return extract_anchor_cards(html_text, base_url, r"ai\.meta\.com/blog/[^/?#]+/?$", "Meta AI", "blog")


def parse_mistral(html_text: str, base_url: str) -> list[dict]:
    items = extract_article_cards(html_text, base_url, r"mistral\.ai/news/[^/?#]+/?$", "Mistral", "blog")
    return items or extract_anchor_cards(html_text, base_url, r"mistral\.ai/news/[^/?#]+/?$", "Mistral", "blog")


def parse_deepseek(html_text: str, base_url: str) -> list[dict]:
    # Docusaurus renders the news pages in sidebar links. Follow the linked
    # official news pages so titles/dates come from page content instead of the
    # sidebar label text.
    links = []
    for m in re.finditer(r"<a\b[^>]*\bhref\s*=\s*(['\"]?)(/news/news\d+)\1", html_text, re.I | re.S):
        url = normalize_url(m.group(2), base_url)
        if url not in links:
            links.append(url)
    out = []
    for url in links[:DEEPSEEK_LINKS_LIMIT]:
        page_text = ""
        try:
            status, body, _ctype, _method = fetch_bytes(url)
            if status < 400:
                page_text = body.decode("utf-8", "replace")
        except Exception:
            page_text = ""
        if not page_text:
            continue
        title = first_match_text([
            r"<h1[^>]*>(.*?)</h1>",
            r"<meta[^>]+property=['\"]og:title['\"][^>]+content=['\"](.*?)['\"]",
            r"<title[^>]*>(.*?)</title>",
        ], page_text)
        title = re.sub(r"\s*\|\s*DeepSeek API Docs\s*$", "", title).strip()
        if not title or title.lower() == "news":
            title = f"DeepSeek news {url.rsplit('/', 1)[-1].replace('news', '')}"
        summary = first_match_text([
            r"<meta[^>]+name=['\"]description['\"][^>]+content=['\"](.*?)['\"]",
            r"<meta[^>]+property=['\"]og:description['\"][^>]+content=['\"](.*?)['\"]",
            r"<p[^>]*>(.*?)</p>",
        ], page_text, 500)
        published = parse_loose_date(page_text) or parse_date_from_url(url)
        out.append(make_html_item("DeepSeek", "blog", title, url, published, summary))
    if out:
        return out
    title = (
        first_match_text([r"<h1[^>]*>(.*?)</h1>", r"<title[^>]*>(.*?)</title>"], html_text)
        or "DeepSeek API updates"
    )
    return [make_html_item(
        "DeepSeek", "blog", title, base_url, parse_loose_date(html_text),
        first_match_text([r"<meta[^>]+name=['\"]description['\"][^>]+content=['\"](.*?)['\"]"], html_text),
    )]


def _parse_hf_daily_papers_props(html_text: str, base_url: str) -> list[dict]:
    """Hugging Face DailyPapers Svelte data-props JSON 파싱."""
    out = []
    for m in re.finditer(
        r'<div\b[^>]*\bdata-target=["\']DailyPapers["\'][^>]*\bdata-props=(["\'])(.*?)\1',
        html_text, re.I | re.S,
    ):
        props_raw = m.group(2)
        try:
            props = json.loads(html.unescape(props_raw))
        except Exception as e:
            log(f"DEBUG hf_papers data_props_parse_failed {type(e).__name__}:{str(e)[:120]}")
            continue
        for row in (props.get("dailyPapers") or [])[:HTML_ENTRY_LIMIT]:
            paper = row.get("paper") if isinstance(row, dict) else None
            if not isinstance(paper, dict):
                continue
            from ..output import clean_text
            paper_id = clean_text(paper.get("id") or "", 80)
            title = paper.get("title") or ""
            if not paper_id or not title:
                continue
            published_raw = (
                paper.get("submittedOnDailyAt") or row.get("submittedOnDailyAt")
                or paper.get("publishedAt") or row.get("publishedAt")
            )
            published = parse_date(published_raw) or parse_loose_date(str(published_raw or ""))
            summary = paper.get("summary") or paper.get("abstract") or ""
            url = normalize_url(f"/papers/{paper_id}", base_url)
            out.append(make_html_item("HF Papers", "paper", title, url, published, summary))
        if out:
            return out
    return out


def parse_hf_papers(html_text: str, base_url: str) -> list[dict]:
    items = _parse_hf_daily_papers_props(html_text, base_url)
    if items:
        return items
    items = extract_article_cards(
        html_text, base_url,
        r"huggingface\.co/papers/(?!date/|trending$)\d{4}\.\d+",
        "HF Papers", "paper",
    )
    return items or extract_anchor_cards(
        html_text, base_url,
        r"huggingface\.co/papers/(?!date/|trending$)\d{4}\.\d+",
        "HF Papers", "paper",
    )


HTML_PARSERS = {
    "Anthropic News": parse_anthropic,
    "Google DeepMind": parse_deepmind,
    "Meta AI": parse_meta_ai,
    "Mistral": parse_mistral,
    "DeepSeek": parse_deepseek,
    "HF Papers": parse_hf_papers,
}


def collect_html(
    source: str, typ: str, url: str,
    failures: list[dict], statuses: list[dict], unknown_date_candidates: list[dict],
) -> list[dict]:
    try:
        status, body, ctype, method = fetch_bytes(url)
        status_entry = {"source": source, "status": status, "content_type": ctype, "method": method, "parser": "html"}
        statuses.append(status_entry)
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        parser = HTML_PARSERS[source]
        items = parser(body.decode("utf-8", "replace"), url)[:HTML_ENTRY_LIMIT]
        status_entry["parsed_items"] = len(items)
        if items:
            unknown_date_candidates.extend(enrich_html_dates(source, items, status_entry))
        if not items:
            raise RuntimeError("no HTML items parsed")
        return items
    except Exception as e:
        failures.append({"source": source, "reason": str(e)[:240]})
        log(f"FAIL html {source}: {e}")
        return []
