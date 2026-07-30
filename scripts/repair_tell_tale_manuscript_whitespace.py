#!/usr/bin/env python3
"""Repair The Tell-Tale Heart's source-wrap whitespace without changing prose.

The historical controlled chapter accidentally promoted every indented
source-wrap continuation into a paragraph break. The live/admin manuscript and
the retained source blob preserve the real paragraph structure. This script
removes only the extra newline in ``"\\n\\n "`` continuations, proves prose
identity before writing, updates both controlled-publication mirrors and their
checksums, and emits the exact narration manuscript used for reconciliation.

It never changes reader or audiobook release flags.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SLUG = "the-tell-tale-heart"
TITLE = "The Tell-Tale Heart"
EXPECTED_SOURCE_SHA256 = (
    "f5d856baf4abec894c1fdc82f8676a416dc96efd3708162c04bcde0ff0a4579b"
)
EXPECTED_OLD_CONTENT_SHA256 = (
    "be8259855845762a7a1c6e5e1bd45d43bbd04c7d769427b25132e2bf514af1f8"
)
EXPECTED_NEW_CONTENT_SHA256 = (
    "0d754cdbbbcdc662091824f2078312d78eb3d80262e6301b0465ab4c3db54e4e"
)
EXPECTED_OLD_MANUSCRIPT_SHA256 = (
    "60c275266b007015732fdb9cca5165c9efc0cffae988bed66c5d6ca9fcbeb748"
)
EXPECTED_CANONICAL_MANUSCRIPT_SHA256 = (
    "316ed82d8ae04a1af3f82ec692e88bc630c4865c06192854a612f29cb017f2bb"
)
EXPECTED_COLLAPSED_MANUSCRIPT_SHA256 = (
    "acbb67e1d96287a80021202229211ffc8072e80a67cf3274b1f3a00376c22fef"
)
EXPECTED_NON_WHITESPACE_SHA256 = (
    "6780433344237e210b8a27954c8790ac4e564a6f46f646e1101201f26ba7b51e"
)
EXPECTED_SOURCE_WRAP_REPAIRS = 167
MANAGED_CHECKSUM_PATHS = {
    "chapters/chapter-001.json",
    "public_book.json",
    "source_evidence.json",
}
AUDIO_TRUTH_FIELDS = (
    "audio_enabled",
    "audiobook_enabled",
    "generate_audiobook",
    "audio_public_release",
)


class ReconciliationError(RuntimeError):
    """Raised when the repair cannot prove a whitespace-only transformation."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconciliationError(f"invalid JSON: {path}: {type(exc).__name__}") from None
    if not isinstance(value, dict):
        raise ReconciliationError(f"JSON root must be an object: {path}")
    return value


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def remove_whitespace(value: str) -> str:
    return re.sub(r"\s+", "", value)


def manuscript_text(chapter: dict[str, Any]) -> str:
    title = str(chapter.get("title") or "").strip()
    content = str(chapter.get("content") or "")
    content = re.sub(r"\n[ \t]+", "\n", content)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    return f"{title}\n\n{content}\n" if title and content else ""


def aggregate_content_hash(chapter: dict[str, Any]) -> str:
    historical_row = {
        "bookSlug": chapter["bookSlug"],
        "chapterNumber": chapter["order"],
        "id": chapter["id"],
        "title": chapter["title"],
        "language": chapter["language"],
        "content": chapter["content"],
        "sourceSha256": chapter["sourceSha256"],
        "sanitizedSha256": chapter["sanitizedSha256"],
        "wordCountApprox": chapter["word_count"],
        "characterCount": len(chapter["content"]),
        "readingTimeMinutesApprox": chapter["reading_minutes"],
        "sourceTitle": chapter["title"],
    }
    canonical = json.dumps(
        [historical_row],
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256_text(canonical)


def audio_truth_snapshot(publication: Path) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for filename in (
        "approval_evidence.json",
        "public_book.json",
        "reader_manifest.json",
    ):
        document = read_json(publication / filename)
        snapshot[filename] = {
            field: document.get(field)
            for field in AUDIO_TRUTH_FIELDS
            if field in document
        }
    return snapshot


def validate_mirrors(primary: Path, backend: Path) -> None:
    primary_files = sorted(
        path.relative_to(primary)
        for path in primary.rglob("*")
        if path.is_file()
    )
    backend_files = sorted(
        path.relative_to(backend)
        for path in backend.rglob("*")
        if path.is_file()
    )
    if primary_files != backend_files:
        raise ReconciliationError("controlled-publication mirror file lists differ")
    for relative in primary_files:
        if (primary / relative).read_bytes() != (backend / relative).read_bytes():
            raise ReconciliationError(
                f"controlled-publication mirrors differ: {relative}"
            )


def repaired_documents(publication: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    chapter_path = publication / "chapters/chapter-001.json"
    chapter = read_json(chapter_path)
    if (
        chapter.get("bookSlug") != SLUG
        or chapter.get("title") != TITLE
        or chapter.get("sourceSha256") != EXPECTED_SOURCE_SHA256
    ):
        raise ReconciliationError("controlled chapter identity is not exact")

    old_content = str(chapter.get("content") or "")
    old_content_sha256 = sha256_text(old_content)
    if old_content_sha256 not in {
        EXPECTED_OLD_CONTENT_SHA256,
        EXPECTED_NEW_CONTENT_SHA256,
    }:
        raise ReconciliationError(
            f"unexpected controlled chapter content SHA-256: {old_content_sha256}"
        )

    old_manuscript = manuscript_text(chapter)
    old_manuscript_sha256 = sha256_text(old_manuscript)
    if old_manuscript_sha256 not in {
        EXPECTED_OLD_MANUSCRIPT_SHA256,
        EXPECTED_CANONICAL_MANUSCRIPT_SHA256,
    }:
        raise ReconciliationError(
            f"unexpected controlled manuscript SHA-256: {old_manuscript_sha256}"
        )

    repair_count = old_content.count("\n\n ")
    if old_content_sha256 == EXPECTED_OLD_CONTENT_SHA256:
        if repair_count != EXPECTED_SOURCE_WRAP_REPAIRS:
            raise ReconciliationError(
                f"expected {EXPECTED_SOURCE_WRAP_REPAIRS} source-wrap artifacts, "
                f"found {repair_count}"
            )
        new_content = old_content.replace("\n\n ", "\n ")
    else:
        if repair_count:
            raise ReconciliationError("repaired content still has source-wrap artifacts")
        new_content = old_content

    if collapse_whitespace(old_content) != collapse_whitespace(new_content):
        raise ReconciliationError("repair changed prose after whitespace collapse")
    if remove_whitespace(old_content) != remove_whitespace(new_content):
        raise ReconciliationError("repair changed non-whitespace characters")
    if sha256_text(new_content) != EXPECTED_NEW_CONTENT_SHA256:
        raise ReconciliationError("repaired chapter content hash is not canonical")

    chapter["content"] = new_content
    chapter["content_hash"] = EXPECTED_NEW_CONTENT_SHA256
    chapter["sanitizedSha256"] = EXPECTED_NEW_CONTENT_SHA256
    canonical_manuscript = manuscript_text(chapter)
    if sha256_text(canonical_manuscript) != EXPECTED_CANONICAL_MANUSCRIPT_SHA256:
        raise ReconciliationError("canonical manuscript hash is not exact")
    if (
        sha256_text(collapse_whitespace(canonical_manuscript))
        != EXPECTED_COLLAPSED_MANUSCRIPT_SHA256
    ):
        raise ReconciliationError("canonical collapsed manuscript hash is not exact")
    if (
        sha256_text(remove_whitespace(canonical_manuscript))
        != EXPECTED_NON_WHITESPACE_SHA256
    ):
        raise ReconciliationError("canonical non-whitespace hash is not exact")

    content_hash = aggregate_content_hash(chapter)
    public_book = read_json(publication / "public_book.json")
    source_evidence = read_json(publication / "source_evidence.json")
    public_book["content_hash"] = content_hash
    source_evidence["content_hash"] = content_hash

    documents = {
        "chapters/chapter-001.json": json_bytes(chapter),
        "public_book.json": json_bytes(public_book),
        "source_evidence.json": json_bytes(source_evidence),
    }
    checksum = read_json(publication / "checksum_manifest.json")
    rows = checksum.get("files")
    if not isinstance(rows, list):
        raise ReconciliationError("checksum manifest files must be an array")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ReconciliationError("checksum manifest row must be an object")
        relative = str(row.get("file") or "")
        if relative in MANAGED_CHECKSUM_PATHS:
            row["sha256"] = sha256_bytes(documents[relative])
            seen.add(relative)
    if seen != MANAGED_CHECKSUM_PATHS:
        raise ReconciliationError("checksum manifest does not cover repaired files")
    documents["checksum_manifest.json"] = json_bytes(checksum)

    return documents, {
        "old_content_sha256": old_content_sha256,
        "old_manuscript_sha256": old_manuscript_sha256,
        "canonical_manuscript": canonical_manuscript,
        "canonical_manuscript_sha256": sha256_text(canonical_manuscript),
        "content_sha256": EXPECTED_NEW_CONTENT_SHA256,
        "aggregate_content_hash": content_hash,
        "source_wrap_repair_count": (
            EXPECTED_SOURCE_WRAP_REPAIRS
            if old_content_sha256 == EXPECTED_OLD_CONTENT_SHA256
            else 0
        ),
        "already_repaired": old_content_sha256 == EXPECTED_NEW_CONTENT_SHA256,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    primary = args.primary_root / SLUG
    backend = args.backend_root / SLUG
    validate_mirrors(primary, backend)
    before_audio_truth = audio_truth_snapshot(primary)
    documents, result = repaired_documents(primary)

    if not args.check:
        for publication in (primary, backend):
            for relative, payload in documents.items():
                path = publication / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
        args.canonical_manuscript.parent.mkdir(parents=True, exist_ok=True)
        args.canonical_manuscript.write_text(
            result["canonical_manuscript"],
            encoding="utf-8",
        )

    validate_mirrors(primary, backend)
    after_audio_truth = audio_truth_snapshot(primary)
    if before_audio_truth != after_audio_truth:
        raise ReconciliationError("reader/audio release truth changed")

    verified_documents, verified = repaired_documents(primary)
    if any(
        (primary / relative).read_bytes() != payload
        for relative, payload in verified_documents.items()
    ):
        raise ReconciliationError("controlled repair output is not byte-stable")
    if args.canonical_manuscript.is_file():
        if (
            sha256_bytes(args.canonical_manuscript.read_bytes())
            != EXPECTED_CANONICAL_MANUSCRIPT_SHA256
        ):
            raise ReconciliationError("canonical manuscript file hash is not exact")
    elif args.check:
        raise ReconciliationError("canonical manuscript file is missing")

    report = {
        "schema_version": "tell_tale_manuscript_reconciliation.v1",
        "generated_at": args.generated_at,
        "slug": SLUG,
        "status": "CANONICAL_MANUSCRIPT_RECONCILED",
        "repair_kind": "SOURCE_WRAP_WHITESPACE_ONLY",
        "controlled_roots": [display_path(primary), display_path(backend)],
        "canonical_manuscript_path": display_path(args.canonical_manuscript),
        "source_provenance": {
            "source_url": "https://www.gutenberg.org/ebooks/2148",
            "historical_raw_source_git_blob": (
                "481bf484a8fa3065e4f140196d136bbc666225f9"
            ),
            "historical_raw_source_file_sha256": (
                "20780b096474c0c584f780e2f515a528a3cf4a1e265425f9b2c20a6842e39526"
            ),
            "historical_raw_source_stripped_sha256": EXPECTED_SOURCE_SHA256,
            "historical_chapter_git_blob": (
                "6aabad76dfb89651574338d011c1fbca06b65a58"
            ),
            "historical_chapter_file_sha256": (
                "7ffb8676227cab07f79fb2f811f13b53616f3869637fc3fa6283f1bee5a4d3ba"
            ),
        },
        "before": {
            "admin_live_manuscript_sha256": EXPECTED_CANONICAL_MANUSCRIPT_SHA256,
            "controlled_manuscript_sha256": EXPECTED_OLD_MANUSCRIPT_SHA256,
            "controlled_content_sha256": EXPECTED_OLD_CONTENT_SHA256,
            "admin_live_chars": 11174,
            "admin_live_bytes": 11350,
            "admin_live_line_count": 204,
            "admin_live_paragraph_count": 19,
            "controlled_chars": 11341,
            "controlled_bytes": 11517,
            "controlled_line_count": 371,
            "controlled_false_paragraph_count": 186,
        },
        "after": {
            "canonical_manuscript_sha256": EXPECTED_CANONICAL_MANUSCRIPT_SHA256,
            "controlled_content_sha256": EXPECTED_NEW_CONTENT_SHA256,
            "aggregate_content_hash": verified["aggregate_content_hash"],
            "collapsed_manuscript_sha256": EXPECTED_COLLAPSED_MANUSCRIPT_SHA256,
            "non_whitespace_sha256": EXPECTED_NON_WHITESPACE_SHA256,
        },
        "source_wrap_artifacts_removed": EXPECTED_SOURCE_WRAP_REPAIRS,
        "canonical_source_decision": (
            "Use the controlled chapter after removing only duplicated newlines "
            "before indented source-wrap continuations; its extracted manuscript "
            "is byte-identical to the recovered admin/live manuscript."
        ),
        "prose_changed": False,
        "reader_release_truth_changed": False,
        "audio_release_truth_changed": False,
        "audio_generated": False,
        "provider_or_cloud_operation": False,
        "public_mutation": False,
        "paid_tts_lock_touched": False,
        "audio_truth": after_audio_truth,
        "check_mode": bool(args.check),
    }
    if not args.check and args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_bytes(json_bytes(report))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--primary-root",
        type=Path,
        default=ROOT / "data/controlled_publications",
    )
    parser.add_argument(
        "--backend-root",
        type=Path,
        default=ROOT / "backend/data/controlled_publications",
    )
    parser.add_argument(
        "--canonical-manuscript",
        type=Path,
        default=(
            ROOT
            / "internal/audiobook_lab/sprint1_publication/source_manuscripts"
            / SLUG
            / "clean_manuscript.txt"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=(
            ROOT
            / "internal/earnalism_intelligence"
            / "the_tell_tale_heart_manuscript_reconciliation_20260730.json"
        ),
    )
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for field in (
        "primary_root",
        "backend_root",
        "canonical_manuscript",
        "report",
    ):
        value = getattr(args, field)
        setattr(args, field, value.expanduser().resolve())
    try:
        report = run(args)
    except ReconciliationError as exc:
        print(json.dumps({"status": "BLOCKED", "detail": str(exc)}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
