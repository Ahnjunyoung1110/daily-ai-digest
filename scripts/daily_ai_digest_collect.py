#!/usr/bin/env python3
"""Cron/script entrypoint for the Daily AI Digest collector.

This wrapper keeps the executable path stable while the implementation lives in
src/daily_ai_digest/collector.py for easier AI/developer navigation.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from daily_ai_digest.collector import main

if __name__ == "__main__":
    raise SystemExit(main())
