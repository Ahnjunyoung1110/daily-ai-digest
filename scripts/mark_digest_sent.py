#!/usr/bin/env python3
"""Mark selected raw JSON items as digest-sent in the local ledger.

This script is intentionally separate from the collector: a Hermes cron prompt
or downstream job can call it only after the digest composition/delivery path is
considered successful.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from daily_ai_digest.config import KST
from daily_ai_digest.ledger import canonical_key, mark_digest_sent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-path", help="collector raw JSON whose items were included in the digest")
    ap.add_argument("--keys", nargs="*", default=None, help="canonical keys to mark")
    ap.add_argument("--keys-stdin", action="store_true", help="read newline/comma separated canonical keys from stdin")
    args = ap.parse_args()

    keys: list[str] = []
    if args.json_path:
        raw = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
        for item in raw.get("items", []):
            keys.append(item.get("canonical_key") or canonical_key(item))
    if args.keys:
        keys.extend(args.keys)
    if args.keys_stdin:
        text = sys.stdin.read()
        for part in text.replace(",", "\n").splitlines():
            part = part.strip()
            if part:
                keys.append(part)

    # de-dupe preserving order
    seen = set()
    keys = [k for k in keys if k and not (k in seen or seen.add(k))]
    count = mark_digest_sent(keys, datetime.now(KST))
    print(json.dumps({"marked_digest_sent": count, "keys": keys}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
