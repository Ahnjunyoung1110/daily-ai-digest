from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
HOME = Path.home()
LOG_PATH = HOME / "AppData" / "Local" / "hermes" / "logs" / "daily_ai_digest.log"
JSON_DIR = HOME / "AppData" / "Local" / "hermes" / "daily_ai_digest"

DATE_RETRY_LIMIT_PER_SOURCE = 6
UNKNOWN_DATE_CANDIDATE_LIMIT = 40


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(KST).isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def kst_now() -> datetime:
    return datetime.now(KST)
