#!/usr/bin/env python3
"""Validate that imported books remain draft/editorial-review only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from publication_safety_mode import validate_manifest_file


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "book_import_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Manifest or metadata JSON files to validate.")
    parser.add_argument(
        "--allow-missing-default",
        action="store_true",
        help="Pass when no explicit path is supplied and book_import_manifest.json is absent.",
    )
    parser.add_argument(
        "--require-draft-fields",
        action="store_true",
        help="Require every owner-approved draft/editorial-review field. Use for generated import metadata.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = args.paths
    if not paths and DEFAULT_MANIFEST.exists():
        paths = [DEFAULT_MANIFEST]
    if not paths:
        if args.allow_missing_default:
            print(json.dumps({"status": "PASS", "message": "No import manifest supplied."}, indent=2))
            return 0
        print("No manifest path supplied and book_import_manifest.json was not found.", file=sys.stderr)
        return 2

    reports = [
        validate_manifest_file(path, require_draft_fields=args.require_draft_fields)
        for path in paths
    ]
    blocked = [report for report in reports if report["status"] != "PASS"]
    output = {
        "status": "PASS" if not blocked else "BLOCKED",
        "reports": reports,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
