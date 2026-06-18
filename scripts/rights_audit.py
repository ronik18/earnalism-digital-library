#!/usr/bin/env python3
"""Dry-run rights audit report generator.

This script reads a local JSON export of book documents and writes the same
three report files exposed by the admin API. It never connects to production
and never mutates books.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.rights_engine import RIGHTS_REPORT_FILENAMES, rights_report_csv, rights_report_rows


def load_books(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        books = payload.get("books", [])
        if isinstance(books, list):
            return [item for item in books if isinstance(item, dict)]
    raise ValueError("Input must be a JSON array of books or an object with a books array.")


def write_reports(books: list[dict[str, Any]], output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for report_kind, filename in RIGHTS_REPORT_FILENAMES.items():
        rows = rights_report_rows(books, report_kind)
        (output_dir / filename).write_text(rights_report_csv(rows), encoding="utf-8")
        counts[report_kind] = len(rows)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate dry-run rights audit CSV reports from a local book export.")
    parser.add_argument("--input", required=True, type=Path, help="Path to a JSON array/object containing book documents.")
    parser.add_argument("--output-dir", default=Path("output/rights_audit"), type=Path)
    args = parser.parse_args()

    books = load_books(args.input)
    counts = write_reports(books, args.output_dir)
    print(
        "Rights audit dry-run complete: "
        f"approved={counts.get('approved', 0)} "
        f"quarantine={counts.get('quarantine', 0)} "
        f"blocked={counts.get('blocked', 0)} "
        f"output_dir={args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
