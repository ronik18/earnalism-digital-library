#!/usr/bin/env python3
"""Remove the publisher colophon from the Horseman reader edition.

The raw source archive is immutable. This repair changes only the reader-facing
chapter boundary, invalidates the obsolete estimated highlight map, and
rebinds every controlled checksum before any audiobook synthesis begins.
"""

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
SLUG = "a-horseman-in-the-sky"
CONTENT_DIR = ROOT / "content" / "books" / SLUG
PUBLICATION_DIR = ROOT / "data" / "controlled_publications" / SLUG
CONTENT_CHAPTER = CONTENT_DIR / "chapters" / "001-a-horseman-in-the-sky.json"
CONTROLLED_CHAPTER = PUBLICATION_DIR / "chapters" / "chapter-001.json"
RAW_SOURCE = CONTENT_DIR / "raw" / "source.txt"
BOUNDARY_MARKER = "\n\nHere ends No. Four of the Western Classics"
EXPECTED_OLD_SANITIZED_SHA256 = (
    "7f2adce9763b42c9502f31ba97d33fc5d5a9aae7864a38db847eaef52958c8b2"
)
EXPECTED_NEW_SANITIZED_SHA256 = (
    "1fa2d6c67f279a3861edbe4a448bc003d23a9546c0d7304e638c902db1a2f552"
)
EXPECTED_ENDPOINT = 'The sergeant rose to his feet and walked away. "Good God!" he said.'
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


def normalized_source_text() -> str:
    return RAW_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()


def repaired_content(existing: str) -> str:
    digest = sha256_text(existing)
    if digest == EXPECTED_NEW_SANITIZED_SHA256:
        repaired = existing
    elif digest == EXPECTED_OLD_SANITIZED_SHA256:
        if existing.count(BOUNDARY_MARKER) != 1:
            raise ValueError("Expected exactly one publisher-colophon boundary marker")
        repaired = existing.split(BOUNDARY_MARKER, 1)[0].rstrip()
    else:
        raise ValueError(f"Unexpected Horseman chapter checksum: {digest}")
    if sha256_text(repaired) != EXPECTED_NEW_SANITIZED_SHA256:
        raise ValueError("Repaired chapter checksum does not match the reviewed endpoint")
    if not repaired.endswith(EXPECTED_ENDPOINT):
        raise ValueError("Repaired chapter does not end at the canonical narrative endpoint")
    if "Here ends No. Four of the Western Classics" in repaired:
        raise ValueError("Publisher colophon remains in reader-facing content")
    return repaired


def build_replacements(repaired_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_chapter = read_json(CONTENT_CHAPTER)
    controlled_chapter = read_json(CONTROLLED_CHAPTER)
    if content_chapter.get("content") != controlled_chapter.get("content"):
        raise ValueError("Content and controlled chapters diverged before repair")

    text = repaired_content(str(content_chapter.get("content") or ""))
    source_hash = sha256_text(normalized_source_text())
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
                "removed_matter": "publisher_colophon",
                "canonical_endpoint": EXPECTED_ENDPOINT,
                "sanitized_sha256": sanitized_hash,
            },
        }
    )

    public = read_json(PUBLICATION_DIR / "public_book.json")
    public_chapters = copy.deepcopy(public.get("chapters") or [])
    if len(public_chapters) != 1:
        raise ValueError("Horseman public metadata must contain exactly one chapter")
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
        raise ValueError("Horseman reader manifest must contain exactly one chapter")
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
        "note": "The legacy estimated map included publisher colophon text and must not be reused. A measured map is required for any future audiobook release.",
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
    checksum = {"slug": SLUG, "generated_at": repaired_at, "files": checksum_rows}
    replacements[PUBLICATION_DIR / "checksum_manifest.json"] = json_bytes(checksum)

    evidence = {
        "schema": "earnalism.reader_boundary_repair.v1",
        "slug": SLUG,
        "repaired_at": repaired_at,
        "raw_source_immutable": True,
        "source_hash": source_hash,
        "source_hash_domain": source["source_hash_domain"],
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
            raise ValueError(f"Written artifact does not match planned bytes: {path}")
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
    repaired_at = args.repaired_at or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if args.write
        else "DRY_RUN"
    )
    replacements, evidence = build_replacements(repaired_at)
    changed = [str(path.relative_to(ROOT)) for path, payload in replacements.items() if path.read_bytes() != payload]
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
