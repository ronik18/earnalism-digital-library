#!/usr/bin/env python3
"""Isolate The Happy Prince from its source collection without changing the raw archive."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SLUG = "the-happy-prince"
CONTENT_DIR = ROOT / "content" / "books" / SLUG
PUBLICATION_DIR = ROOT / "data" / "controlled_publications" / SLUG
CONTENT_CHAPTER = CONTENT_DIR / "chapters" / "001-the-happy-prince.json"
CONTROLLED_CHAPTER = PUBLICATION_DIR / "chapters" / "chapter-001.json"
RAW_SOURCE = CONTENT_DIR / "raw" / "source.txt"
OPENING_PICTURE = "[Picture: Woman opening window and seeing bird]\n\n"
NEXT_STORY_BOUNDARY = "\n\n[Picture: Decorative graphic of two birds]"
NEXT_STORY_TITLE = "The Nightingale and the Rose."
EXPECTED_OLD_SANITIZED_SHA256 = "c7c1364caa823124f83970c63f5bb170beb6bd8d792efa57d03aa14667fdfe86"
EXPECTED_NEW_SANITIZED_SHA256 = "2063240573e7485e286de9b50610adb8ee77297dd2ceebd63583cc782f634247"
EXPECTED_ENDPOINT = "Prince shall praise me.”"
WORD_RE = re.compile(r"\b\w+[’'\-]?\w*\b", re.UNICODE)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repaired_content(existing: str) -> str:
    digest = sha256_text(existing)
    if digest == EXPECTED_NEW_SANITIZED_SHA256:
        repaired = existing
    elif digest == EXPECTED_OLD_SANITIZED_SHA256:
        if not existing.startswith(OPENING_PICTURE):
            raise ValueError("Expected the reviewed opening picture placeholder")
        if existing.count(NEXT_STORY_BOUNDARY) != 1:
            raise ValueError("Expected exactly one reviewed next-story boundary")
        repaired = existing[len(OPENING_PICTURE) :].split(NEXT_STORY_BOUNDARY, 1)[0].rstrip()
    else:
        raise ValueError(f"Unexpected Happy Prince chapter checksum: {digest}")
    if sha256_text(repaired) != EXPECTED_NEW_SANITIZED_SHA256:
        raise ValueError("Repaired chapter checksum differs from the reviewed narrative")
    if not repaired.endswith(EXPECTED_ENDPOINT):
        raise ValueError("Repaired chapter does not end at The Happy Prince boundary")
    if "[Picture:" in repaired or NEXT_STORY_TITLE in repaired:
        raise ValueError("Picture furniture or the next story remains in reader content")
    return repaired


def build_replacements(requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_chapter = read_json(CONTENT_CHAPTER)
    controlled_chapter = read_json(CONTROLLED_CHAPTER)
    if content_chapter.get("content") != controlled_chapter.get("content"):
        raise ValueError("Canonical and controlled chapter content diverged")

    was_repaired = sha256_text(str(controlled_chapter.get("content") or "")) == EXPECTED_NEW_SANITIZED_SHA256
    repaired_at = str(controlled_chapter.get("updated_at") or requested_at) if was_repaired else requested_at
    text = repaired_content(str(controlled_chapter.get("content") or ""))
    source_text = RAW_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    source_hash = sha256_text(source_text)
    if source_hash != content_chapter.get("sourceSha256"):
        raise ValueError("Normalized immutable raw-source checksum changed")

    words = len(WORD_RE.findall(text))
    minutes = max(1, math.ceil(words / 240))
    sanitized_hash = sha256_text(text)

    content_chapter = copy.deepcopy(content_chapter)
    content_chapter.update(
        {
            "content": text,
            "sanitizedSha256": sanitized_hash,
            "wordCountApprox": words,
            "characterCount": len(text),
            "readingTimeMinutesApprox": minutes,
        }
    )
    controlled_chapter = copy.deepcopy(controlled_chapter)
    controlled_chapter.update(
        {
            "content": text,
            "content_hash": sanitized_hash,
            "sanitizedSha256": sanitized_hash,
            "word_count": words,
            "reading_minutes": minutes,
            "updated_at": repaired_at,
        }
    )

    book = read_json(CONTENT_DIR / "book.json")
    book.update(
        {
            "wordCountApprox": words,
            "readingTimeMinutesApprox": minutes,
            "updatedAt": repaired_at,
        }
    )

    aggregate_content_hash = sha256_text(
        json.dumps([content_chapter], ensure_ascii=False, sort_keys=True)
    )
    source = read_json(PUBLICATION_DIR / "source_evidence.json")
    provenance_hash = sha256_text(
        "\n".join(
            (
                str(source.get("source_url") or ""),
                str(source.get("source_name") or ""),
                str(source.get("source_license") or ""),
                aggregate_content_hash,
            )
        )
    )
    source.update(
        {
            "source_hash": source_hash,
            "source_hash_domain": "utf8_text_normalized_lf_trimmed_terminal_whitespace",
            "content_hash": aggregate_content_hash,
            "content_hash_domain": "canonical_content_chapter_json_list_sorted_keys_utf8",
            "provenance_hash": provenance_hash,
            "provenance_hash_domain": "source_url_lf_source_name_lf_source_license_lf_content_hash",
            "reader_facing_boilerplate_removed": True,
            "qa_status": "QA_PASSED",
            "verified_at": repaired_at,
            "reader_boundary_repair": {
                "status": "PASS",
                "removed_matter": ["picture_placeholders", "the-nightingale-and-the-rose"],
                "canonical_endpoint": EXPECTED_ENDPOINT,
                "sanitized_sha256": sanitized_hash,
            },
        }
    )

    public = read_json(PUBLICATION_DIR / "public_book.json")
    public_chapters = copy.deepcopy(public.get("chapters") or [])
    if len(public_chapters) != 1:
        raise ValueError("Happy Prince public metadata must contain exactly one chapter")
    public_chapters[0].update(
        {"word_count": words, "reading_minutes": minutes, "updated_at": repaired_at}
    )
    public.update(
        {
            "chapters": public_chapters,
            "estimated_reading_time": f"{minutes} min",
            "source_hash": source_hash,
            "content_hash": aggregate_content_hash,
            "provenance_hash": provenance_hash,
            "updated_at": repaired_at,
        }
    )

    reader = read_json(PUBLICATION_DIR / "reader_manifest.json")
    reader_chapters = copy.deepcopy(reader.get("chapters") or [])
    if len(reader_chapters) != 1:
        raise ValueError("Happy Prince reader manifest must contain exactly one chapter")
    reader_chapters[0].update(
        {"word_count": words, "reading_minutes": minutes, "updated_at": repaired_at}
    )
    reader.update(
        {
            "chapters": reader_chapters,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generated_at": repaired_at,
        }
    )

    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_SOURCE_BOUNDARY_CHANGED",
        "generatedAt": repaired_at,
        "source": "reader_boundary_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": "The legacy estimated map included picture labels and another story. Measured synchronization is required for future audio.",
    }

    replacements = {
        CONTENT_CHAPTER: json_bytes(content_chapter),
        CONTENT_DIR / "book.json": json_bytes(book),
        CONTROLLED_CHAPTER: json_bytes(controlled_chapter),
        PUBLICATION_DIR / "public_book.json": json_bytes(public),
        PUBLICATION_DIR / "reader_manifest.json": json_bytes(reader),
        PUBLICATION_DIR / "source_evidence.json": json_bytes(source),
        PUBLICATION_DIR / "highlight_sync.json": json_bytes(highlight),
    }
    checksum_rows = []
    for path in sorted(PUBLICATION_DIR.rglob("*")):
        if not path.is_file() or path.name in {"checksum_manifest.json", "publication_manifest.json"}:
            continue
        payload = replacements.get(path)
        checksum_rows.append(
            {
                "file": path.relative_to(PUBLICATION_DIR).as_posix(),
                "sha256": sha256_bytes(payload) if payload is not None else sha256_file(path),
            }
        )
    replacements[PUBLICATION_DIR / "checksum_manifest.json"] = json_bytes(
        {"slug": SLUG, "generated_at": repaired_at, "files": checksum_rows}
    )

    evidence = {
        "schema": "earnalism.reader_boundary_repair.v1",
        "slug": SLUG,
        "repaired_at": repaired_at,
        "raw_source_immutable": True,
        "source_hash": source_hash,
        "old_sanitized_sha256": EXPECTED_OLD_SANITIZED_SHA256,
        "new_sanitized_sha256": sanitized_hash,
        "content_hash": aggregate_content_hash,
        "provenance_hash": provenance_hash,
        "canonical_endpoint": EXPECTED_ENDPOINT,
        "word_count": words,
        "reading_minutes": minutes,
        "legacy_highlight_sync_invalidated": True,
        "audio_enabled": False,
    }
    evidence["evidence_sha256"] = sha256_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return replacements, evidence


def verify_written(replacements: dict[Path, bytes]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from planned bytes: {path}")
    checksum = read_json(PUBLICATION_DIR / "checksum_manifest.json")
    for row in checksum.get("files") or []:
        target = PUBLICATION_DIR / str(row["file"])
        if not target.is_file() or sha256_file(target) != row.get("sha256"):
            raise ValueError(f"Controlled checksum mismatch: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repaired-at")
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    requested_at = args.repaired_at or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if args.write
        else "DRY_RUN"
    )
    replacements, evidence = build_replacements(requested_at)
    changed = [
        str(path.relative_to(ROOT))
        for path, payload in replacements.items()
        if path.read_bytes() != payload
    ]
    evidence["mode"] = "write" if args.write else "dry-run"
    evidence["changed_files"] = changed
    if args.write:
        for path, payload in replacements.items():
            path.write_bytes(payload)
        verify_written(replacements)
    if args.evidence_out:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_bytes(json_bytes(evidence))
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
