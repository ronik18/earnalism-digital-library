#!/usr/bin/env python3
"""Generate dry-run public-domain source ingestion reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.source_ingestion import (  # noqa: E402
    SourceIngestionInput,
    ingest_source,
    ingestion_report_csv,
    ingestion_report_markdown,
)


SAMPLE_TEXT = """*** START OF THE PROJECT GUTENBERG EBOOK SAMPLE ***

Chapter 1

This is a cleared sample source for ingestion validation.

Chapter 2

The cleaned text remains separate from the raw source text.

*** END OF THE PROJECT GUTENBERG EBOOK SAMPLE ***
"""


SAMPLE_BOOK = {
    "title": "Sample Public Domain Book",
    "slug": "sample-public-domain-book",
    "author": "Sample Author",
    "rights_metadata": {
        "work_title": "Sample Public Domain Book",
        "work_slug": "sample-public-domain-book",
        "author_name": "Sample Author",
        "author_death_year": 1850,
        "original_publication_year": 1880,
        "country_of_origin": "United Kingdom",
        "source_url": "https://www.gutenberg.org/ebooks/1",
        "source_name": "Project Gutenberg",
        "source_license": "Public domain",
        "rights_tier": "A",
        "verification_status": "approved",
        "publication_region": "global",
        "verified_at": "2026-06-18T00:00:00+00:00",
    },
}


def load_book(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample:
        return dict(SAMPLE_BOOK)
    if path is None:
        raise ValueError("--book is required unless --sample is used.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError("--book must point to a JSON object containing book and rights metadata.")


def load_text(path: Path | None, *, sample: bool) -> str:
    if sample:
        return SAMPLE_TEXT
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def write_reports(record, output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source_ingestion_report.json"
    csv_path = output_dir / "source_ingestion_report.csv"
    md_path = output_dir / "source_ingestion_report.md"
    json_path.write_text(json.dumps(record.as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path.write_text(ingestion_report_csv([record]), encoding="utf-8")
    md_path.write_text(ingestion_report_markdown([record]), encoding="utf-8")
    return json_path, csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=Path, help="Local JSON book record with rights_metadata.")
    parser.add_argument("--text-file", type=Path, help="Local raw source text file.")
    parser.add_argument("--source-url", default="", help="Override rights_metadata.source_url.")
    parser.add_argument("--source-name", default="", help="Override rights_metadata.source_name.")
    parser.add_argument("--source-license", default="", help="Override rights_metadata.source_license.")
    parser.add_argument("--language", default="", help="Optional language override.")
    parser.add_argument("--connector", default="auto")
    parser.add_argument("--existing-hash", action="append", default=[], help="Existing source hash to dedupe.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/source_ingestion"))
    parser.add_argument("--sample", action="store_true", help="Run a deterministic local sample.")
    parser.add_argument("--commit", action="store_true", help="Marks reports as non-dry-run only; no production mutation occurs.")
    args = parser.parse_args()

    book = load_book(args.book, sample=args.sample)
    raw_text = load_text(args.text_file, sample=args.sample)
    record = ingest_source(
        SourceIngestionInput(
            book=book,
            raw_text=raw_text,
            source_url=args.source_url,
            source_name=args.source_name,
            source_license=args.source_license,
            language=args.language,
            connector=args.connector,
            previous_source_hashes=set(args.existing_hash),
            dry_run=not args.commit,
        )
    )
    json_path, csv_path, md_path = write_reports(record, args.output_dir)
    print(
        "Source ingestion dry-run complete: "
        f"status={record.ingestion_status} "
        f"rights={record.rights_status} "
        f"json={json_path} csv={csv_path} markdown={md_path}"
    )
    return 0 if not record.ingestion_status.startswith("BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
