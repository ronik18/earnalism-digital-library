#!/usr/bin/env python3
"""Generate dry-run Earnalism edition scaffolds without external API calls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.edition_generator import (  # noqa: E402
    EditionGenerationInput,
    edition_report_csv,
    edition_report_json,
    edition_report_markdown,
    generate_edition,
)
from backend.source_ingestion import hash_provenance, hash_source  # noqa: E402


SAMPLE_TEXT = """Chapter 1

Alice was beginning to get very tired of sitting by her sister on the bank.
The book her sister read had no pictures or conversations in it, and Alice wondered what use a book was without pictures or conversations.
She considered whether the pleasure of making a daisy-chain would be worth the trouble of getting up and picking the daisies.
Just then a White Rabbit with pink eyes ran close by her.
The Rabbit actually took a watch out of its waistcoat-pocket, looked at it, and hurried on.
Alice started to her feet, burning with curiosity, and ran across the field after it.
"""


SAMPLE_BOOK = {
    "title": "Alice's Adventures in Wonderland",
    "author": "Lewis Carroll",
    "language": "en",
    "source_name": "Project Gutenberg",
    "source_url": "https://www.gutenberg.org/ebooks/11",
    "source_license": "Public domain",
    "rights_tier": "A",
    "verification_status": "approved",
    "blocked_reason": "",
    "action_status": "READY_FOR_GENERATION",
    "ingestion_status": "CLEANED",
}


def load_payload(path: Path | None, *, sample: bool) -> dict[str, Any]:
    if sample:
        content_hash = hash_source(SAMPLE_TEXT)
        return {
            **SAMPLE_BOOK,
            "cleaned_text": SAMPLE_TEXT,
            "source_hash": content_hash,
            "content_hash": content_hash,
            "provenance_hash": hash_provenance(
                source_url=SAMPLE_BOOK["source_url"],
                source_name=SAMPLE_BOOK["source_name"],
                source_license=SAMPLE_BOOK["source_license"],
                content_hash=content_hash,
            ),
        }
    if path is None:
        raise ValueError("--input is required unless --sample is used.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("--input must be a JSON object.")
    return normalize_payload(payload)


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    source_result = payload.get("source_ingestion") or payload.get("source_ingestion_result")
    if isinstance(source_result, dict):
        merged = {**payload, **source_result}
        merged.pop("source_ingestion", None)
        merged.pop("source_ingestion_result", None)
        payload = merged

    if not payload.get("cleaned_text") and payload.get("cleaned_text_preview"):
        raise ValueError("Phase 5 requires cleaned_text; rerun Phase 4 with --include-text for local dry-run generation.")
    return payload


def write_reports(
    result,
    output_dir: Path,
    *,
    include_content: bool = False,
    content_preview_chars: int = 1200,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "edition_generation_report.json"
    csv_path = output_dir / "edition_generation_report.csv"
    md_path = output_dir / "edition_generation_report.md"
    json_path.write_text(
        json.dumps(
            edition_report_json(
                result,
                include_content=include_content,
                content_preview_chars=content_preview_chars,
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    csv_path.write_text(edition_report_csv(result), encoding="utf-8")
    md_path.write_text(
        edition_report_markdown(
            result,
            include_content=include_content,
            content_preview_chars=content_preview_chars,
        ),
        encoding="utf-8",
    )
    return json_path, csv_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Local JSON source ingestion or book/text payload.")
    parser.add_argument("--output-dir", type=Path, default=Path("output/edition_generation"))
    parser.add_argument("--section", action="append", default=[], help="Specific section id to generate. Repeatable.")
    parser.add_argument("--existing-cache-key", action="append", default=[], help="Existing generation cache key.")
    parser.add_argument("--max-sections-per-run", type=int, default=4)
    parser.add_argument("--max-generation-budget", type=int, default=10_000)
    parser.add_argument("--include-content", action="store_true", help="Include full generated section content in JSON.")
    parser.add_argument("--content-preview-chars", type=int, default=1200, help="Generated content preview length.")
    parser.add_argument("--sample", action="store_true", help="Run a deterministic local fixture.")
    parser.add_argument("--commit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--write", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.commit or args.publish or args.write:
        parser.error("Phase 5 edition generation is dry-run only; commit/publish/write options are not supported.")

    payload = load_payload(args.input, sample=args.sample)
    text = str(payload.get("cleaned_text") or payload.get("source_excerpt") or payload.get("text") or "")
    source_hash = str(payload.get("source_hash") or hash_source(text))
    content_hash = str(payload.get("content_hash") or source_hash)
    provenance_hash = str(payload.get("provenance_hash") or "")
    result = generate_edition(
        EditionGenerationInput(
            title=str(payload.get("title") or payload.get("work_title") or "Untitled"),
            author=str(payload.get("author") or payload.get("author_name") or ""),
            language=str(payload.get("language") or "en"),
            cleaned_text=text,
            source_hash=source_hash,
            source_name=str(payload.get("source_name") or ""),
            source_url=str(payload.get("source_url") or ""),
            source_license=str(payload.get("source_license") or ""),
            content_hash=content_hash,
            provenance_hash=provenance_hash,
            rights_tier=str(payload.get("rights_tier") or ""),
            verification_status=str(payload.get("verification_status") or ""),
            blocked_reason=str(payload.get("blocked_reason") or ""),
            action_status=str(payload.get("action_status") or ""),
            ingestion_status=str(payload.get("ingestion_status") or ""),
            requested_sections=args.section,
            existing_cache_keys=set(args.existing_cache_key),
            max_sections_per_run=args.max_sections_per_run,
            max_generation_budget=args.max_generation_budget,
            dry_run=True,
        )
    )
    json_path, csv_path, md_path = write_reports(
        result,
        args.output_dir,
        include_content=args.include_content,
        content_preview_chars=args.content_preview_chars,
    )
    print(
        "Edition generation dry-run complete: "
        f"status={result.generation_status} "
        f"qa={result.state.qa_status} "
        f"json={json_path} csv={csv_path} markdown={md_path}"
    )
    return 0 if result.state.qa_status != "BLOCKED_QA" else 2


if __name__ == "__main__":
    raise SystemExit(main())
