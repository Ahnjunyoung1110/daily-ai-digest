"""Notion digest sync CLI wrapper.

사용법:
  python scripts/notion_digest_sync.py --json-path PATH [--dry-run] [--limit N] [--database-id ID]
  python scripts/notion_digest_sync.py --json-path-stdin [--dry-run] [--limit N] [--database-id ID]

stdout: 순수 JSON
stderr: 진단 로그
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# src/ 경로 추가 (스크립트를 scripts/ 디렉터리에서 실행할 때)
_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from daily_ai_digest.notion_sync import DEFAULT_DB_ID, sync  # noqa: E402


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _get_token() -> str:
    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY") or ""
    return token


def main() -> None:
    parser = argparse.ArgumentParser(
        description="collector raw JSON → Notion DB sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--json-path", metavar="PATH", help="collector raw JSON 파일 경로")
    src_group.add_argument(
        "--json-path-stdin",
        action="store_true",
        help="stdin에서 raw JSON 파일 경로 한 줄을 읽기",
    )

    parser.add_argument("--dry-run", action="store_true", help="Notion API 미호출, would_create로 표시")
    parser.add_argument("--no-ensure-schema", action="store_true", help="Canonical Key DB 속성 자동 생성/확인을 건너뜀")
    parser.add_argument("--no-update-page-body", action="store_true", help="기존 Notion page children 갱신을 건너뜀")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="동기화할 최대 아이템 수")
    parser.add_argument("--top-n", type=int, default=30, metavar="N",
                        help="중요도 상위 N개만 동기화 (기본값: 30, None으로 비활성화 불가 — 0 입력 시 제한 없음)")
    parser.add_argument(
        "--database-id",
        default=DEFAULT_DB_ID,
        metavar="ID",
        help=f"Notion 데이터베이스 ID (기본값: {DEFAULT_DB_ID})",
    )

    args = parser.parse_args()

    # raw JSON 로드
    if args.json_path_stdin:
        json_label = sys.stdin.read().strip().strip('"')
        _log(f"[notion_sync] stdin에서 JSON 경로 읽음: {json_label}")
        if not json_label:
            _log("[notion_sync] stdin JSON 경로가 비어 있음")
            sys.exit(1)
        json_path = Path(json_label)
        if not json_path.exists():
            _log(f"[notion_sync] 파일 없음: {json_path}")
            sys.exit(1)
        try:
            raw_json = json.loads(json_path.read_bytes().decode("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _log(f"[notion_sync] JSON 로드 실패: {e}")
            sys.exit(1)
    else:
        json_path = Path(args.json_path)
        _log(f"[notion_sync] 파일 읽는 중: {json_path}")
        if not json_path.exists():
            _log(f"[notion_sync] 파일 없음: {json_path}")
            sys.exit(1)
        try:
            raw_json = json.loads(json_path.read_bytes().decode("utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _log(f"[notion_sync] JSON 로드 실패: {e}")
            sys.exit(1)
        json_label = str(json_path)

    # items / meta 검증
    if not isinstance(raw_json, dict) or "items" not in raw_json:
        _log("[notion_sync] 유효하지 않은 collector JSON (items 키 없음)")
        sys.exit(1)

    # 토큰 확인 (dry-run 아닌 경우 필수)
    token = _get_token()
    if not args.dry_run and not token:
        _log("[notion_sync] NOTION_TOKEN 또는 NOTION_API_KEY 환경변수 필요 (라이브 모드)")
        sys.exit(1)

    items_total = len(raw_json.get("items", []))
    _log(
        f"[notion_sync] 시작: items={items_total}, db={args.database_id}, "
        f"dry_run={args.dry_run}, limit={args.limit}"
    )

    top_n_value: int | None = args.top_n if args.top_n and args.top_n > 0 else None
    try:
        result = sync(
            raw_json=raw_json,
            db_id=args.database_id,
            token=token,
            dry_run=args.dry_run,
            limit=args.limit,
            top_n=top_n_value,
            ensure_schema=not args.no_ensure_schema,
            update_page_body=not args.no_update_page_body,
        )
    except Exception as exc:
        _log(f"[notion_sync] 치명적 오류: {exc}")
        sys.exit(1)

    # json_path 덮어쓰기 (meta에 없을 수 있음)
    result["meta"]["json_path"] = json_label

    _log(
        f"[notion_sync] 완료: synced={result['meta']['items_synced']}, "
        f"skipped={result['meta']['items_skipped']}, "
        f"failed={result['meta']['items_failed']}"
    )

    # stdout: 순수 JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
