#!/usr/bin/env python3
"""Generate deterministic demand priority reports without external API calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.demand_scoring import demand_report_csv, demand_report_markdown, rank_demand, seed_books


def load_books(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return seed_books()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        books = payload.get("books", [])
        if isinstance(books, list):
            return [item for item in books if isinstance(item, dict)]
    raise ValueError("Input must be a JSON array of book/topic records or an object with a books array.")


def write_reports(books: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scores = rank_demand(books)
    csv_path = output_dir / "demand_priority_report.csv"
    md_path = output_dir / "demand_priority_report.md"
    csv_path.write_text(demand_report_csv(scores), encoding="utf-8")
    md_path.write_text(demand_report_markdown(scores), encoding="utf-8")
    return csv_path, md_path, len(scores)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional local JSON export of book/topic records.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/demand"))
    args = parser.parse_args()

    books = load_books(args.input)
    csv_path, md_path, count = write_reports(books, args.output_dir)
    print(f"Demand priority dry-run complete: items={count} csv={csv_path} markdown={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
