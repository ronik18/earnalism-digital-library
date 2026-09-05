#!/usr/bin/env python3
"""Dry-run the deterministic Reading Pass page plan for controlled titles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.catalog_truth import CONTROLLED_LIVE_BOOK_SLUGS, controlled_artifact_dir, load_controlled_artifact_book
from backend.domain.reading_pass import _content_blocks, canonical_page_records


CANDIDATE_TARGETS = (3200, 2800, 2400, 2000, 1600, 1200, 1000, 800)
MATRIX_SCHEMA = "earnalism.reading-pass-segment-matrix.v1"


def matrix_row(slug: str) -> dict:
    book = load_controlled_artifact_book(slug, include_content=True, artifact_dir=controlled_artifact_dir(slug))
    if not book:
        raise ValueError(f"controlled title is unavailable: {slug}")
    chapters = list(book.get("chapters") or [])
    content = "\n".join(str(chapter.get("content") or "") for chapter in chapters)
    page_counts = {
        str(target): len(canonical_page_records(book_slug=slug, chapters=chapters, target_characters=target))
        for target in CANDIDATE_TARGETS
    }
    selected = next((target for target in CANDIDATE_TARGETS if page_counts[str(target)] >= 4), None)
    if not selected:
        classification = "SOURCE_INCOMPLETE_OR_CORRUPT" if not content.strip() else "RELEASE_TRUTH_CONFLICT"
        reason = "no approved canonical target produces a protected page"
    elif selected == CANDIDATE_TARGETS[0]:
        classification = "READY_PROTECTED_STANDARD"
        reason = "standard canonical target produces page 4"
    else:
        classification = "READY_PROTECTED_ADAPTIVE"
        reason = "largest approved canonical target that produces page 4"
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", content)).strip()
    return {
        "slug": slug,
        "book_id": str(book.get("id") or ""),
        "title": str(book.get("title") or ""),
        "language": str(book.get("language") or ""),
        "publication_state": str(book.get("publication_status") or book.get("publicationStatus") or ""),
        "reader_approval": bool(book.get("readerStatus") == "reader_ready" and book.get("allowPublicReading") is True),
        "source_hash": str(book.get("source_hash") or ""),
        "content_hash": str(book.get("content_hash") or ""),
        "computed_content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "unicode_character_count": len(content),
        "plain_text_character_count": len(plain),
        "word_count": len(re.findall(r"\S+", plain)),
        "semantic_block_count": len(_content_blocks(content)),
        "page_counts": page_counts,
        "selected_target_characters": selected,
        "selected_segmentation_version": f"uat-canonical-html-blocks-v1-target-{selected}" if selected else None,
        "public_existing_page_count": min(3, page_counts[str(selected)]) if selected else 0,
        "protected_page_start": 4 if selected else None,
        "classification": classification,
        "reason": reason,
        "blocking": classification not in {"READY_PROTECTED_STANDARD", "READY_PROTECTED_ADAPTIVE"},
    }


def build_matrix(slugs: Iterable[str]) -> dict:
    rows = [matrix_row(slug) for slug in sorted(set(slugs))]
    return {
        "schema_version": MATRIX_SCHEMA,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "candidate_targets": list(CANDIDATE_TARGETS),
        "rows": rows,
        "result": "PASS" if rows and not any(row["blocking"] for row in rows) else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", action="append")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.all == bool(args.slug):
        parser.error("provide exactly one of --all or --slug")
    report = build_matrix(CONTROLLED_LIVE_BOOK_SLUGS if args.all else args.slug)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "titles": len(report["rows"])}, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
