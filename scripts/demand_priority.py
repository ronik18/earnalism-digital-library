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

from backend.demand_scoring import demand_report_csv, demand_report_json, demand_report_markdown, rank_demand, seed_books


def load_books(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return seed_books()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [_normalize_input_item(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        books = payload.get("books")
        if isinstance(books, list):
            return [_normalize_input_item(item) for item in books if isinstance(item, dict)]
        rows = payload.get("rows")
        if isinstance(rows, list):
            return [_normalize_input_item(item) for item in rows if isinstance(item, dict)]
    raise ValueError(
        "Input must be a JSON array, an object with a books array, or a catalog-audit object with a rows array."
    )


def write_reports(books: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path, Path, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scores = rank_demand(books)
    csv_path = output_dir / "demand_priority_report.csv"
    md_path = output_dir / "demand_priority_report.md"
    json_path = output_dir / "demand_priority_report.json"
    csv_path.write_text(demand_report_csv(scores), encoding="utf-8")
    md_path.write_text(demand_report_markdown(scores), encoding="utf-8")
    json_path.write_text(json.dumps(demand_report_json(scores), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return csv_path, md_path, json_path, len(scores)


def _normalize_input_item(item: dict[str, Any]) -> dict[str, Any]:
    if "content_type" in item or "recommended_action" in item:
        return _catalog_row_to_book(item)
    if "decision_status" in item or "decision_issues" in item:
        return _rights_row_to_book(item)
    return dict(item)


def _catalog_row_to_book(row: dict[str, Any]) -> dict[str, Any]:
    title = str(row.get("title") or row.get("url") or row.get("path") or "Untitled").strip()
    slug = str(row.get("related_slug") or row.get("slug") or row.get("path") or title).strip().strip("/")
    rights_present = str(row.get("rights_metadata_present") or "").lower()
    rights_metadata: dict[str, Any] = {}
    if rights_present in {"yes", "true", "present"}:
        rights_metadata = {"rights_tier": "A", "verification_status": "approved", "publication_region": "global"}
    elif rights_present in {"unknown", "no", "false", "missing"}:
        rights_metadata = {"verification_status": "needs_review"}
    return {
        "title": title,
        "slug": slug.replace("/", "-") or "catalog-item",
        "category_slug": row.get("category_slug") or row.get("content_type") or "",
        "language": row.get("language") or "",
        "rights_metadata": rights_metadata,
    }


def _rights_row_to_book(row: dict[str, Any]) -> dict[str, Any]:
    decision_status = str(row.get("decision_status") or "").lower()
    rights_tier = str(row.get("rights_tier") or "").upper().replace("TIER ", "")
    rights_metadata = {
        "rights_tier": rights_tier,
        "verification_status": "approved" if decision_status == "approved" else decision_status or "needs_review",
        "publication_region": row.get("publication_region") or "global",
        "source_url": row.get("source_url") or "",
        "blocked_reason": row.get("blocked_reason") or row.get("decision_issues") or "",
    }
    return {
        "title": row.get("book_title") or row.get("work_title") or row.get("title") or "Untitled",
        "slug": row.get("book_slug") or row.get("work_slug") or row.get("slug") or "",
        "category_slug": row.get("category_slug") or "",
        "language": row.get("language") or "",
        "rights_metadata": rights_metadata,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional local JSON export of book/topic records.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/demand"))
    args = parser.parse_args()

    books = load_books(args.input)
    csv_path, md_path, json_path, count = write_reports(books, args.output_dir)
    print(f"Demand priority dry-run complete: items={count} csv={csv_path} markdown={md_path} json={json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
