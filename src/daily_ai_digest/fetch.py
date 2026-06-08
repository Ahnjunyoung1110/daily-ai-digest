from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from .config import log

UA = "ai-digest-bot/1.0"
TIMEOUT = 15
RSS_ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml, */*;q=0.1"
GITHUB_UNAUTH_SLEEP = 7  # unauthenticated Search API limit is 10/min; leave margin
GITHUB_PER_PAGE = 10
HN_HITS_PER_PAGE = 30
HN_MIN_POINTS = 30


def github_token() -> str | None:
    return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or None


def http_get(url: str, accept: str = "*/*") -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return int(getattr(r, "status", 200)), r.read(), r.headers.get("content-type", "")


def curl_get(url: str) -> tuple[int, bytes, str]:
    # Mandatory fallback path: raw fetch via curl, still with UA and timeout.
    p = subprocess.run(
        ["curl", "-L", "--max-time", str(TIMEOUT), "-A", UA, "-sS", "-w", "\n%{http_code}\n%{content_type}", url],
        capture_output=True,
        timeout=TIMEOUT + 5,
    )
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).decode("utf-8", "replace")[:300])
    raw = p.stdout
    parts = raw.rsplit(b"\n", 2)
    if len(parts) != 3:
        raise RuntimeError("curl output parse failed")
    body, code_b, ctype_b = parts
    return int(code_b.decode(errors="replace") or 0), body, ctype_b.decode(errors="replace")


def fetch_bytes(url: str, accept: str = "*/*") -> tuple[int, bytes, str, str]:
    try:
        status, body, ctype = http_get(url, accept)
        return status, body, ctype, "urllib"
    except Exception as e1:
        try:
            status, body, ctype = curl_get(url)
            return status, body, ctype, f"curl_fallback_after:{type(e1).__name__}"
        except Exception as e2:
            raise RuntimeError(f"urllib {type(e1).__name__}: {e1}; curl {type(e2).__name__}: {e2}")


def gh_headers() -> dict:
    h = {"User-Agent": UA, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    tok = github_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def github_request(url: str) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, headers=gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return int(r.status), json.loads(r.read().decode("utf-8", "replace")), r.headers.get("x-ratelimit-remaining", "?")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code}: {body}")
