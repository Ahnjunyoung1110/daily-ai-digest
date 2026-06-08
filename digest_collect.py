#!/usr/bin/env python3
"""Deterministic ETL for Telegram IT digest text.

Reads digest text from stdin or --input, parses topic/bullet/link items,
fetches abstracts/content with GET-only network reads, and writes a pure JSON
array to stdout. All diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import date
from typing import Any
from urllib.parse import urlparse

import httpx

try:
    import trafilatura
except ImportError:  # graceful for arxiv-only smoke/use without generic fetches
    trafilatura = None  # type: ignore[assignment]

USER_AGENT = "digest-collect/1.0 (+https://github.com/Ahnjunyoung1110)"
TIMEOUT_SECONDS = 20.0
MAX_GENERIC_CONTENT_CHARS = 4000
URL_RE = re.compile(r"https?://[^\s<>'\"\])}]+")
BULLET = "•"
ASCII_BULLET_RE = re.compile(r"^[-*]\s+")
DASH_RE = re.compile(r"\s+[—–]\s+|\s+-\s+")

META_LINE_PATTERNS = (
    re.compile(r"^Cronjob Response:", re.IGNORECASE),
    re.compile(r"^\(job_id:\s*[^)]+\)$", re.IGNORECASE),
    re.compile(r"^-{3,}$"),
    re.compile(r"^Daily\s+AI\s+Digest\s*[·-]\s*\d{4}-\d{2}-\d{2}\s+KST$", re.IGNORECASE),
)


def log(message: str) -> None:
    print(message, file=sys.stderr)


def read_input(path: str | None) -> str:
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return sys.stdin.read()


def is_meta_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in META_LINE_PATTERNS)


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = html.unescape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"__(.+?)__", r"\1", value)
    value = re.sub(r"\*(.+?)\*", r"\1", value)
    value = re.sub(r"\s+", " ", value).strip(" \t-—–:•")
    return value or None


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in URL_RE.findall(text):
        url = match.rstrip(".,;:!?)]}>")
        if url and url not in urls:
            urls.append(url)
    return urls


def remove_urls(text: str) -> str:
    return clean_text(URL_RE.sub("", text)) or ""


def normalize_source(url: str | None) -> str:
    if not url:
        return "unknown"
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "arxiv.org" or host.endswith(".arxiv.org"):
        return "arXiv"
    if host == "huggingface.co" or host.endswith(".huggingface.co"):
        return "HuggingFace"
    return host or "unknown"


def split_bullet_items(line: str) -> list[str]:
    if BULLET in line:
        return [part.strip() for part in line.split(BULLET) if part.strip()]
    if ASCII_BULLET_RE.match(line):
        return [ASCII_BULLET_RE.sub("", line, count=1).strip()]
    return []


def is_bullet_line(line: str) -> bool:
    return BULLET in line or bool(ASCII_BULLET_RE.match(line))


def make_item(
    run_date: str,
    topic: str | None,
    title: str | None,
    desc: str | None,
    url: str | None,
) -> dict[str, Any]:
    return {
        "date": run_date,
        "topic": topic,
        "title": title,
        "desc": desc,
        "url": url,
        "source": normalize_source(url),
        "content": "",
        "fetch_status": "pending",
    }


def parse_bullet(raw_item: str, topic: str | None, run_date: str) -> list[dict[str, Any]]:
    raw_item = raw_item.strip()
    if not raw_item:
        return []

    urls = extract_urls(raw_item)
    text_without_urls = remove_urls(raw_item)

    title: str | None
    desc: str | None
    split = DASH_RE.search(text_without_urls)
    if split:
        title = clean_text(text_without_urls[: split.start()])
        desc = clean_text(text_without_urls[split.end() :])
    else:
        title = clean_text(text_without_urls)
        desc = None

    if not urls:
        return [make_item(run_date, topic, title, desc, None)]

    return [make_item(run_date, topic, title, desc, url) for url in urls]


def attach_urls_to_pending(
    pending_items: list[dict[str, Any]], urls: list[str]
) -> list[dict[str, Any]]:
    if not pending_items or not urls:
        return pending_items

    attached: list[dict[str, Any]] = []
    for pending in pending_items:
        if len(urls) == 1:
            item = pending
            item["url"] = urls[0]
            item["source"] = normalize_source(urls[0])
            attached.append(item)
        else:
            for url in urls:
                item = deepcopy(pending)
                item["url"] = url
                item["source"] = normalize_source(url)
                attached.append(item)
    return attached


def parse_digest(text: str, run_date: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    current_topic: str | None = None
    pending_items: list[dict[str, Any]] = []

    def flush_pending() -> None:
        nonlocal pending_items
        if pending_items:
            items.extend(pending_items)
            pending_items = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or is_meta_line(line):
            continue

        if is_bullet_line(line):
            flush_pending()
            for bullet_text in split_bullet_items(line):
                parsed = parse_bullet(bullet_text, current_topic, run_date)
                if parsed and all(item["url"] is None for item in parsed):
                    pending_items.extend(parsed)
                else:
                    items.extend(parsed)
            continue

        urls = extract_urls(line)
        if urls and pending_items:
            items.extend(attach_urls_to_pending(pending_items, urls))
            pending_items = []
            continue

        # Non-bullet, non-continuation lines are topic headers.
        flush_pending()
        topic = clean_text(URL_RE.sub("", line))
        if topic:
            current_topic = topic

    flush_pending()
    return items


def arxiv_id_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    match = re.search(r"(?:abs|pdf|e-print)/([^/?#]+)", path, re.IGNORECASE)
    if match:
        return match.group(1).removesuffix(".pdf")
    tail = path.rsplit("/", 1)[-1]
    return tail.removesuffix(".pdf") if tail else None


def fetch_arxiv_abstract(url: str, client: httpx.Client) -> tuple[str, str]:
    arxiv_id = arxiv_id_from_url(url)
    if not arxiv_id:
        return "", "failed:arxiv_id_not_found"

    api_url = "https://export.arxiv.org/api/query"
    response = client.get(api_url, params={"id_list": arxiv_id})
    response.raise_for_status()

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError:
        return "", "failed:xml_parse_error"

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    summary_el = root.find("atom:entry/atom:summary", ns)
    summary = clean_text(summary_el.text if summary_el is not None else None)
    if not summary:
        return "", "failed:summary_not_found"
    return summary, "ok"


def meta_description(html_text: str) -> str | None:
    patterns = (
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(match.group(1))
    return None


def fetch_huggingface_paper_abstract(url: str, client: httpx.Client) -> tuple[str, str]:
    response = client.get(url)
    response.raise_for_status()
    html_text = response.text

    extracted = None
    if trafilatura is not None:
        extracted = trafilatura.extract(
            html_text,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
    if extracted:
        abstract_match = re.search(
            r"(?:^|\n)Abstract\s*\n+(.+?)(?:\n\s*\n|\n(?:Community|BibTeX|Paper|Models)\b|\Z)",
            extracted,
            re.IGNORECASE | re.DOTALL,
        )
        content = clean_text(abstract_match.group(1) if abstract_match else extracted)
        if content:
            return content, "ok"

    description = meta_description(html_text)
    if description:
        return description, "ok"
    return "", "failed:abstract_not_found"


def fetch_generic_content(url: str, client: httpx.Client) -> tuple[str, str]:
    response = client.get(url)
    response.raise_for_status()
    if trafilatura is None:
        return "", "failed:trafilatura_not_installed"

    extracted = trafilatura.extract(
        response.text,
        include_comments=False,
        include_tables=False,
    )
    content = clean_text(extracted)
    if not content:
        return "", "failed:empty_content"
    return content[:MAX_GENERIC_CONTENT_CHARS], "ok"


def fetch_content(url: str, client: httpx.Client) -> tuple[str, str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    try:
        if host == "arxiv.org" or host.endswith(".arxiv.org"):
            return fetch_arxiv_abstract(url, client)
        if (host == "huggingface.co" or host.endswith(".huggingface.co")) and parsed.path.startswith("/papers/"):
            return fetch_huggingface_paper_abstract(url, client)
        return fetch_generic_content(url, client)
    except httpx.TimeoutException:
        return "", "failed:timeout"
    except httpx.HTTPStatusError as exc:
        return "", f"failed:http_{exc.response.status_code}"
    except httpx.RequestError as exc:
        return "", f"failed:request_{type(exc).__name__}"
    except Exception as exc:  # keep one bad URL from aborting the ETL
        return "", f"failed:{type(exc).__name__}"


def enrich_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with httpx.Client(
        timeout=httpx.Timeout(TIMEOUT_SECONDS),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for item in items:
            url = item.get("url")
            if not url:
                item["content"] = ""
                item["fetch_status"] = "skipped:no_url"
                item["source"] = normalize_source(None)
                continue

            log(f"[fetch] {url}")
            content, status = fetch_content(url, client)
            item["content"] = content if status == "ok" else ""
            item["fetch_status"] = status
            item["source"] = normalize_source(url)
    return items


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse Telegram IT digest text and fetch link abstracts/content as JSON."
    )
    parser.add_argument("--input", metavar="PATH", help="input text file; defaults to stdin")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="ISO date; defaults to execution date")
    args = parser.parse_args()

    run_date = args.date or date.today().isoformat()
    try:
        text = read_input(args.input)
        items = parse_digest(text, run_date)
        log(f"[parse] parsed {len(items)} items")
        enriched = enrich_items(items)
        json.dump(enriched, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    except BrokenPipeError:
        return 1
    except Exception as exc:
        log(f"[fatal] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
