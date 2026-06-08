from __future__ import annotations

import email.utils
import html
import re
import urllib.parse
from datetime import datetime

from .config import DATE_RETRY_LIMIT_PER_SOURCE, KST, log
from .fetch import fetch_bytes
from .output import attr_value, clean_text, strip_tags

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7,
    "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def parse_date(value, parsed_struct=None) -> str | None:
    if parsed_struct:
        try:
            from datetime import timezone
            return datetime(*parsed_struct[:6], tzinfo=timezone.utc).astimezone(KST).isoformat()
        except Exception:
            pass
    if not value:
        return None
    value = str(value).strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).isoformat()
    except Exception:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).isoformat()
    except Exception:
        return None


def parse_loose_date(segment: str) -> str | None:
    if not segment:
        return None
    m = re.search(r"<time\b[^>]*\bdatetime\s*=\s*(['\"])(.*?)\1", segment, re.I | re.S)
    if not m:
        m = re.search(r"<time\b[^>]*\bdatetime\s*=\s*([^\s>]+)", segment, re.I | re.S)
    candidates = []
    if m:
        candidates.append(html.unescape(m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)))
    for tm in re.findall(r"<time\b[^>]*>(.*?)</time>", segment, re.I | re.S):
        candidates.append(strip_tags(tm, 80))
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?)?\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
        r"\bDate:\s*\d{4}-\d{2}-\d{2}\b",
    ]
    for pat in patterns:
        candidates.extend(re.findall(pat, strip_tags(segment, 2000), re.I))
    for cand in candidates:
        cand = re.sub(r"^Date:\s*", "", cand.strip(), flags=re.I).rstrip(".")
        parsed = parse_date(cand)
        if parsed:
            return parsed
        m = re.match(r"(?i)^([a-z]+)\.?\s+(\d{4})$", cand)
        if m and m.group(1).lower() in _MONTHS:
            return datetime(int(m.group(2)), _MONTHS[m.group(1).lower()], 1, tzinfo=KST).isoformat()
        m = re.match(r"(?i)^([a-z]+)\.?\s+(\d{1,2}),\s+(\d{4})$", cand)
        if m and m.group(1).lower() in _MONTHS:
            return datetime(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)), tzinfo=KST).isoformat()
        m = re.match(r"(?i)^(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})$", cand)
        if m and m.group(2).lower() in _MONTHS:
            return datetime(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)), tzinfo=KST).isoformat()
    return None


def _iter_meta_contents(page_text: str) -> list[tuple[str, str]]:
    pairs = []
    for m in re.finditer(r"<meta\b[^>]*>", page_text, re.I | re.S):
        tag = m.group(0)
        key = attr_value(tag, "property") or attr_value(tag, "name") or attr_value(tag, "itemprop") or ""
        content = attr_value(tag, "content") or ""
        if key and content:
            pairs.append((key.strip().lower(), html.unescape(content.strip())))
    return pairs


def _unescape_jsonish(s: str) -> str:
    text = html.unescape(s)
    return text.replace('\\\\"', '"').replace('\\"', '"').replace('\\/', '/')


def parse_date_from_meta(page_text: str) -> str | None:
    wanted = {
        "article:published_time",
        "article:modified_time",
        "og:published_time",
        "date",
        "pubdate",
        "publishdate",
        "publish_date",
        "publication_date",
        "dc.date",
        "dc.date.issued",
        "dcterms.date",
        "datepublished",
        "datemodified",
    }
    for key, content in _iter_meta_contents(page_text):
        key_norm = key.replace("-", "").replace("_", "")
        if key in wanted or key_norm in {"datepublished", "datemodified", "publishdate", "publicationdate"}:
            parsed = parse_date(content)
            if parsed:
                return parsed
            parsed = parse_loose_date(content)
            if parsed:
                return parsed
    # JSON-LD and embedded structured data often carry datePublished/dateModified.
    # Some sites (Anthropic/Sanity) use publishedOn in escaped Next.js data.
    jsonish = _unescape_jsonish(page_text) if "\\\"" in page_text or "&quot;" in page_text else page_text
    for m in re.finditer(r'"(?:date(?:Published|Modified|Created)|publishedOn)"\s*:\s*"([^"]+)"', jsonish, re.I):
        parsed = parse_date(html.unescape(m.group(1))) or parse_loose_date(m.group(1))
        if parsed:
            return parsed
    return None


def parse_date_from_url(url: str) -> str | None:
    path = urllib.parse.urlparse(url).path
    # DeepSeek docs news pages encode dates as /news/newsYYMMDD.
    m = re.search(r"/news/news(\d{2})(\d{2})(\d{2})(?:/|$)", path, re.I)
    if m:
        try:
            return datetime(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=KST).isoformat()
        except Exception:
            pass
    patterns = [
        r"/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)",
        r"/(20\d{2})-(\d{1,2})-(\d{1,2})(?:/|$)",
        r"/(20\d{2})(\d{2})(\d{2})(?:/|$)",
        r"/date/(20\d{2})-(\d{1,2})-(\d{1,2})(?:/|$)",
    ]
    for pat in patterns:
        m = re.search(pat, path)
        if not m:
            continue
        try:
            if len(m.group(1)) == 4 and len(m.groups()) == 3:
                y, mo, d = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            else:
                continue
            return datetime(y, mo, d, tzinfo=KST).isoformat()
        except Exception:
            continue
    return None


def retry_item_date_from_url_or_page(item: dict, source: str) -> str | None:
    url = item.get("url") or ""
    parsed = parse_date_from_url(url)
    if parsed:
        item["date_recovery"] = "url"
        log(f"DEBUG date_retry_ok source={source} method=url url={url} date={parsed}")
        return parsed
    try:
        status, body, _ctype, method = fetch_bytes(url)
        if status >= 400:
            log(f"DEBUG date_retry_fail source={source} method=page_fetch status={status} url={url}")
            return None
        page_text = body.decode("utf-8", "replace")
        parsed = parse_date_from_meta(page_text) or parse_loose_date(page_text[:12000])
        if parsed:
            item["date_recovery"] = f"page_meta_or_time:{method}"
            log(f"DEBUG date_retry_ok source={source} method=page_meta_or_time fetch={method} url={url} date={parsed}")
            return parsed
        log(f"DEBUG date_retry_fail source={source} method=page_meta_or_time url={url}")
    except Exception as e:
        log(f"DEBUG date_retry_fail source={source} error={type(e).__name__}:{str(e)[:160]} url={url}")
    return None


def enrich_html_dates(source: str, items: list[dict], status_entry: dict) -> list[dict]:
    date_parse_failed = 0
    date_retry_attempts = 0
    date_retry_recovered = 0
    unknown = []
    for item in items:
        if item.get("published"):
            continue
        date_parse_failed += 1
        if date_retry_attempts < DATE_RETRY_LIMIT_PER_SOURCE:
            date_retry_attempts += 1
            recovered = retry_item_date_from_url_or_page(item, source)
            if recovered:
                item["published"] = recovered
                date_retry_recovered += 1
                continue
        item["date_unknown"] = True
        unknown.append({
            "source": source,
            "type": item.get("type"),
            "title": item.get("title"),
            "url": item.get("url"),
            "published": None,
            "reason": "date_parse_failed_after_url_or_page_meta_retry",
        })
    if date_parse_failed:
        status_entry["date_parse_failed_items"] = date_parse_failed
        status_entry["date_retry_attempts"] = date_retry_attempts
        status_entry["date_retry_recovered"] = date_retry_recovered
        status_entry["unknown_date_items"] = len(unknown)
        log(
            f"WARN date_parse source={source}: failed={date_parse_failed} "
            f"retry_attempts={date_retry_attempts} recovered={date_retry_recovered} "
            f"unknown={len(unknown)}"
        )
    return unknown
