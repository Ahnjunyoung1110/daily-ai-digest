#!/usr/bin/env python3
"""Ensure the Daily AI Digest Notion DB has required properties."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from daily_ai_digest.notion_sync import DEFAULT_DB_ID, ensure_database_schema


def _get_token() -> str:
    return os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY") or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-id", default=DEFAULT_DB_ID)
    args = ap.parse_args()
    token = _get_token()
    if not token:
        print(json.dumps({"ok": False, "error": "NOTION_TOKEN or NOTION_API_KEY required"}, ensure_ascii=False))
        return 1
    result = ensure_database_schema(args.database_id, token)
    print(json.dumps({"ok": True, "database_id": args.database_id, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
