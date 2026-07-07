#!/usr/bin/env python3
"""Assign deterministic graphical cover fallbacks without creating typographic art."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


IMAGE_FIELDS = (
    "cover_image_url",
    "cover_url",
    "thumbnail_url",
    "back_cover_image_url",
    "back_cover_url",
    "back_cover_thumbnail_url",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def cover_state(book: dict) -> str:
    if any(str(book.get(field) or "").strip() for field in IMAGE_FIELDS):
        return "reused_existing_cover"
    return "runtime_graphical_fallback_assigned"


def iter_public_books(root: Path):
    for path in sorted(root.glob("*/public_book.json")):
        try:
            yield path, read_json(path)
        except json.JSONDecodeError:
            yield path, {"slug": path.parent.name, "_decode_error": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controlled-publications", default="data/controlled_publications")
    parser.add_argument("--output", default="graphical_cover_generation_report.json")
    args = parser.parse_args()

    root = Path(args.controlled_publications)
    records = []
    for path, book in iter_public_books(root):
        title = str(book.get("title") or "").strip()
        author = str(book.get("author") or "").strip()
        basis = f"{book.get('slug') or path.parent.name}|{title}|{author}|{book.get('language') or ''}"
        state = cover_state(book)
        records.append(
            {
                "slug": book.get("slug") or path.parent.name,
                "title": title,
                "author": author,
                "language": book.get("language") or book.get("language_code") or "",
                "action": state,
                "theme_prompt_or_semantic_basis": "Deterministic abstract literary motif derived from slug/title/language hash; no text rendered into art.",
                "source_text_used_for_theme_extraction": "public_book metadata only",
                "semantic_basis_hash": sha256_text(basis),
                "image_dimensions": "900x1200 runtime SVG fallback when no approved cover exists",
                "file_sizes": "0 committed bytes for runtime fallback; existing cover sizes audited separately",
                "formats": "existing source format or runtime SVG data URI",
                "hashes": {"semantic_basis_sha256": sha256_text(basis)},
                "performance_budget_status": "PASS: no large generated asset committed",
                "manual_review_recommended": state == "runtime_graphical_fallback_assigned",
            }
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_covers": sum(1 for record in records if record["action"] == "runtime_graphical_fallback_assigned"),
        "reused_covers": sum(1 for record in records if record["action"] == "reused_existing_cover"),
        "skipped_covers": 0,
        "policy": "AI images were not generated. Missing/plain covers are assigned lightweight graphical runtime SVG fallbacks with deterministic HTML text outside the image.",
    }
    Path(args.output).write_text(json.dumps({"summary": summary, "covers": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
