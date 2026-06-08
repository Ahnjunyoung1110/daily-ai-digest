from __future__ import annotations

import json
import time
import urllib.parse
from datetime import datetime

from ..config import KST, log
from ..dates import parse_date
from ..fetch import (
    RSS_ACCEPT,
    GITHUB_PER_PAGE,
    GITHUB_UNAUTH_SLEEP,
    HN_HITS_PER_PAGE,
    HN_MIN_POINTS,
    fetch_bytes,
    github_request,
    github_token,
)
from ..output import clean_text, make_item
from ..sources import GITHUB_KEYWORDS, GITHUB_TOPICS

RSS_ENTRY_LIMIT = 12
REDDIT_LIMIT = 50


def collect_rss(source: str, typ: str, url: str, failures: list[dict], statuses: list[dict]) -> list[dict]:
    try:
        status, body, ctype, method = fetch_bytes(url, RSS_ACCEPT)
        statuses.append({"source": source, "status": status, "content_type": ctype, "method": method})
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        if "text/html" in (ctype or "").lower() and not body.lstrip().startswith(b"<rss") and not body.lstrip().startswith(b"<?xml"):
            raise RuntimeError(f"RSS fetch returned HTML (content-type: {ctype})")
        try:
            import feedparser  # type: ignore
            parsed = feedparser.parse(body)
            if getattr(parsed, "bozo", False) and not parsed.entries:
                raise RuntimeError(str(getattr(parsed, "bozo_exception", "parse failed")))
            out = []
            for e in parsed.entries[:RSS_ENTRY_LIMIT]:
                title = clean_text(getattr(e, "title", ""), 240)
                link = getattr(e, "link", "") or url
                published = parse_date(
                    getattr(e, "published", None) or getattr(e, "updated", None),
                    getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None),
                )
                summary = clean_text(getattr(e, "summary", None) or getattr(e, "description", None) or "")
                out.append(make_item(source, typ, title, link, published, summary))
            return out
        except ImportError:
            return _collect_rss_xml_fallback(source, typ, url, body)
    except Exception as e:
        failures.append({"source": source, "reason": str(e)[:240]})
        log(f"FAIL rss {source}: {e}")
        return []


def _collect_rss_xml_fallback(source: str, typ: str, url: str, body: bytes) -> list[dict]:
    import xml.etree.ElementTree as ET
    root = ET.fromstring(body)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    nodes = root.findall(".//item") or root.findall(".//atom:entry", ns)
    out = []
    for node in nodes[:RSS_ENTRY_LIMIT]:
        def txt(path):
            x = node.find(path, ns)
            return x.text if x is not None else None
        title = clean_text(txt("title") or txt("atom:title"), 240)
        link = txt("link")
        if not link:
            ln = node.find("atom:link", ns)
            link = ln.attrib.get("href") if ln is not None else url
        published = parse_date(
            txt("pubDate") or txt("published") or txt("atom:published") or txt("atom:updated")
        )
        summary = clean_text(txt("description") or txt("summary") or txt("atom:summary") or "")
        out.append(make_item(source, typ, title, link or url, published, summary))
    return out


def collect_reddit(source: str, subreddit: str, failures: list[dict], statuses: list[dict], time_window: str = "week") -> list[dict]:
    """Collect Reddit by JSON API top/week so score and comment signals exist.

    RSS is intentionally avoided for production quality because it does not carry
    points/comments, which made low-signal posts indistinguishable from important
    community discussions.
    """
    url = f"https://www.reddit.com/r/{subreddit}/top.json?" + urllib.parse.urlencode({"t": time_window, "limit": str(REDDIT_LIMIT), "raw_json": "1"})
    try:
        status, body, ctype, method = fetch_bytes(url, "application/json, */*;q=0.1")
        statuses.append({"source": f"{source} JSON", "status": status, "content_type": ctype, "method": method})
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        data = json.loads(body.decode("utf-8", "replace"))
        out = []
        for child in data.get("data", {}).get("children", []):
            r = child.get("data") or {}
            title = r.get("title") or ""
            permalink = r.get("permalink") or ""
            link = urllib.parse.urljoin("https://www.reddit.com", permalink) if permalink else (r.get("url") or f"https://www.reddit.com/r/{subreddit}/")
            created = r.get("created_utc")
            published = None
            if created:
                try:
                    published = datetime.fromtimestamp(float(created), tz=KST).isoformat()
                except Exception:
                    published = None
            signals = {
                "stars": 0,
                "points": r.get("score") or 0,
                "comments": r.get("num_comments") or 0,
                "upvote_ratio": r.get("upvote_ratio"),
                "subreddit": subreddit,
                "flair": r.get("link_flair_text"),
            }
            summary = clean_text(r.get("selftext") or r.get("url") or "", 500)
            out.append(make_item(source, "community", title, link, published, summary, signals))
        return out
    except Exception as e:
        # Reddit JSON is the preferred path because it carries points/comments,
        # but reddit.com may return 403 to unauthenticated JSON clients. Fall
        # back to RSS so the source remains observable; production score v2 will
        # usually drop these low-signal fallback items instead of promoting them.
        log(f"WARN reddit_json_failed source={source}: {e}; falling back to RSS")
        rss_url = f"https://www.reddit.com/r/{subreddit}/.rss"
        fallback = collect_rss(source, "community", rss_url, failures, statuses)
        for item in fallback:
            item.setdefault("signals", {"stars": 0, "points": 0, "comments": 0})
            item["signals"]["reddit_signal_source"] = "rss_fallback_no_points_comments"
        if fallback:
            statuses.append({"source": f"{source} JSON", "status": "fallback_to_rss", "reason": str(e)[:160]})
            return fallback
        failures.append({"source": source, "reason": str(e)[:240]})
        log(f"FAIL reddit {source}: {e}")
        return []


def collect_hn(ts_epoch: int, failures: list[dict], statuses: list[dict]) -> list[dict]:
    q = "(LLM OR RAG OR agent OR MCP OR inference)"
    params = {
        "query": q,
        "tags": "story",
        "numericFilters": f"created_at_i>{ts_epoch},points>{HN_MIN_POINTS}",
        "hitsPerPage": str(HN_HITS_PER_PAGE),
    }
    url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(params)
    try:
        status, body, ctype, method = fetch_bytes(url)
        statuses.append({"source": "HN Algolia", "status": status, "content_type": ctype, "method": method})
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        data = json.loads(body.decode("utf-8", "replace"))
        out = []
        for h in data.get("hits", []):
            objid = h.get("objectID")
            link = h.get("url") or (
                f"https://news.ycombinator.com/item?id={objid}" if objid else "https://news.ycombinator.com/"
            )
            signals = {
                "stars": 0,
                "points": h.get("points") or 0,
                "comments": h.get("num_comments") or 0,
            }
            summary = f"author={h.get('author')}; points={h.get('points')}; comments={h.get('num_comments')}"
            out.append(make_item("HN", "community", h.get("title") or h.get("story_title") or "", link, h.get("created_at"), summary, signals))
        return out
    except Exception as e:
        failures.append({"source": "HN Algolia", "reason": str(e)[:240]})
        log(f"FAIL hn: {e}")
        return []


def collect_github(date_str: str, failures: list[dict], statuses: list[dict]) -> list[dict]:
    token_present = bool(github_token())
    queries = GITHUB_KEYWORDS + (GITHUB_TOPICS if token_present else [])
    out = []
    seen: set[str] = set()
    for i, q in enumerate(queries):
        encoded_q = urllib.parse.quote_plus(f"{q} created:>{date_str}")
        url = f"https://api.github.com/search/repositories?q={encoded_q}&sort=stars&order=desc&per_page={GITHUB_PER_PAGE}"
        try:
            status, data, remain = github_request(url)
            statuses.append({"source": f"GitHub {q}", "status": status, "rate_remaining": remain})
            for r in data.get("items", []):
                name = r.get("full_name")
                if not name or name in seen:
                    continue
                seen.add(name)
                signals = {
                    "stars": r.get("stargazers_count") or 0,
                    "points": 0,
                    "comments": 0,
                    "language": r.get("language"),
                    "updated_at": r.get("updated_at"),
                    "topics": r.get("topics") or [],
                }
                out.append(make_item(
                    "GitHub", "repo", name,
                    r.get("html_url") or "",
                    r.get("created_at"),
                    clean_text(r.get("description") or ""),
                    signals,
                ))
        except Exception as e:
            failures.append({"source": f"GitHub {q}", "reason": str(e)[:240]})
            log(f"FAIL github {q}: {e}")
        if not token_present and i != len(queries) - 1:
            time.sleep(GITHUB_UNAUTH_SLEEP)
    return out
