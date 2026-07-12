#!/usr/bin/env python3
"""Build a source-bound private Google English TTS input from controlled data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
INPUT_SCHEMA = "earnalism.google_english_private_input.v1"
BOILERPLATE_MARKERS = (
    "*** start of this project gutenberg",
    "*** end of this project gutenberg",
    "project gutenberg literary archive foundation",
    "www.gutenberg.org",
    "this ebook is for the use of anyone anywhere",
)


class InputPreparationError(RuntimeError):
    """Fail-closed source preparation error."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputPreparationError(f"Invalid JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise InputPreparationError(f"JSON evidence must be an object: {path}")
    return payload


def normalized_chapter_text(value: Any, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputPreparationError(f"Chapter content is empty: {path}")
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    lowered = text.lower()
    found = [marker for marker in BOILERPLATE_MARKERS if marker in lowered]
    if found:
        raise InputPreparationError(
            f"Chapter contains reader-facing source boilerplate: {path}: {found}"
        )
    return text


def rights_pass(source: dict[str, Any], approval: dict[str, Any]) -> bool:
    basis = str(source.get("rights_basis") or "").strip()
    return bool(
        basis
        and source.get("reader_facing_boilerplate_removed") is True
        and approval.get("approved_to_publish") is True
        and str(approval.get("verification_status") or "").lower() == "approved"
    )


def evidence_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_input(
    *, slug: str, controlled_root: Path, output_root: Path
) -> dict[str, Any]:
    book_dir = controlled_root / slug
    chapter_dir = book_dir / "chapters"
    chapter_paths = sorted(chapter_dir.glob("*.json"))
    if not chapter_paths:
        raise InputPreparationError(f"No controlled chapters found for {slug}")

    source_path = book_dir / "source_evidence.json"
    approval_path = book_dir / "approval_evidence.json"
    public_book_path = book_dir / "public_book.json"
    source = read_json(source_path)
    approval = read_json(approval_path)
    public_book = read_json(public_book_path)
    if not rights_pass(source, approval):
        raise InputPreparationError(f"Rights/source approval is incomplete for {slug}")

    ordered: list[tuple[int, str, Path]] = []
    for path in chapter_paths:
        chapter = read_json(path)
        if chapter.get("bookSlug") != slug:
            raise InputPreparationError(f"Chapter slug mismatch: {path}")
        if chapter.get("processing_status") != "ready":
            raise InputPreparationError(f"Chapter is not ready: {path}")
        warnings = chapter.get("processing_warnings") or []
        if warnings:
            raise InputPreparationError(f"Chapter has processing warnings: {path}")
        order = chapter.get("order")
        if not isinstance(order, int) or order < 1:
            raise InputPreparationError(f"Chapter order is invalid: {path}")
        ordered.append((order, normalized_chapter_text(chapter.get("content"), path), path))

    ordered.sort(key=lambda item: item[0])
    expected_orders = list(range(1, len(ordered) + 1))
    actual_orders = [item[0] for item in ordered]
    if actual_orders != expected_orders:
        raise InputPreparationError(
            f"Chapter order must be contiguous for {slug}: {actual_orders}"
        )

    source_text = "\n\n".join(item[1] for item in ordered).strip() + "\n"
    source_bytes = source_text.encode("utf-8")
    language = str(public_book.get("language") or "en").lower()
    if language not in {"en", "english"}:
        chapter_language = str(read_json(ordered[0][2]).get("language") or "").lower()
        if chapter_language not in {"en", "english"}:
            raise InputPreparationError(f"Title is not an English source: {slug}")

    title = str(public_book.get("title") or "").strip()
    author = str(public_book.get("author") or "").strip()
    if not title or not author:
        raise InputPreparationError(f"Title/author metadata is incomplete for {slug}")

    output_dir = output_root / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    sanitized_path = output_dir / "sanitized_source.txt"
    manifest_path = output_dir / "input_manifest.json"
    sanitized_path.write_bytes(source_bytes)
    manifest = {
        "schema_version": INPUT_SCHEMA,
        "slug": slug,
        "title": title,
        "author": author,
        "language": "en",
        "sanitized_source_sha256": sha256_bytes(source_bytes),
        "sanitized_source_characters": len(source_text),
        "chapter_count": len(ordered),
        "chapter_orders": actual_orders,
        "sanitization_status": "PASS",
        "rights_status": "PASS",
        "commercial_use_allowed": True,
        "source_evidence_path": evidence_path(source_path),
        "approval_evidence_path": evidence_path(approval_path),
        "controlled_publication_path": evidence_path(book_dir),
        "public_audio_release_approved": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "PASS_PRIVATE_INPUT_READY",
        "slug": slug,
        "sanitized_source": str(sanitized_path),
        "input_manifest": str(manifest_path),
        "source_sha256": manifest["sanitized_source_sha256"],
        "characters": manifest["sanitized_source_characters"],
        "chapter_count": manifest["chapter_count"],
        "provider_calls_ran": False,
        "release_mutation_performed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument(
        "--controlled-root", type=Path, default=ROOT / "data/controlled_publications"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "internal/audiobook_lab/private_runs/inputs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_input(
            slug=args.slug,
            controlled_root=args.controlled_root.expanduser().resolve(),
            output_root=args.output_root.expanduser().resolve(),
        )
    except InputPreparationError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
