#!/usr/bin/env python3
"""Restore semantic paragraphs for The Pit and the Pendulum without changing its words."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repair_happy_prince_reader_boundary import (
    json_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    sha256_text,
)


ROOT = Path(__file__).resolve().parents[1]
SLUG = "the-pit-and-the-pendulum"
CONTENT_DIR = ROOT / "content" / "books" / SLUG
PUBLICATION_DIR = ROOT / "data" / "controlled_publications" / SLUG
BACKEND_PUBLICATION_DIR = ROOT / "backend" / "data" / "controlled_publications" / SLUG
CONTENT_CHAPTER = CONTENT_DIR / "chapters" / "001-the-pit-and-the-pendulum.json"
CONTROLLED_CHAPTER = PUBLICATION_DIR / "chapters" / "chapter-001.json"
RAW_SOURCE = CONTENT_DIR / "raw" / "source.txt"
EXPECTED_OLD_SANITIZED_SHA256 = "66979b5c7d7e91e721b5cc71eacda01c97a4b63b10393fcc10917a666a794f8a"
EXPECTED_NEW_SANITIZED_SHA256 = "778162c0eb0685fc28e6433b48e5685e3ae86fd69413588c90c21a967d4babb6"
EXPECTED_ENDPOINT = "The Inquisition was in the hands of its enemies."
EXPECTED_BLOCK_COUNT = 40
WORD_RE = re.compile(r"\b\w+[’'\-]?\w*\b", re.UNICODE)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def authoritative_reflow() -> str:
    raw = RAW_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    blocks = re.split(r"\n\s*\n", raw)
    if len(blocks) != EXPECTED_BLOCK_COUNT:
        raise ValueError(f"Unexpected raw paragraph count: {len(blocks)}")
    repaired: list[str] = []
    for index, block in enumerate(blocks):
        lines = [line.strip() for line in block.splitlines()]
        repaired.append("\n".join(lines) if index == 0 else " ".join(lines))
    text = "\n\n".join(repaired)
    if sha256_text(text) != EXPECTED_NEW_SANITIZED_SHA256:
        raise ValueError("Authoritative paragraph reflow checksum changed")
    if len(re.split(r"\n\s*\n", text)) != EXPECTED_BLOCK_COUNT:
        raise ValueError("Reflow did not preserve semantic paragraph count")
    if len(text.splitlines()[:4]) < 4 or not text.startswith("Impia tortorum"):
        raise ValueError("Four-line epigraph boundary changed")
    if not text.endswith(EXPECTED_ENDPOINT):
        raise ValueError("Narrative ending changed")
    return text


def repaired_content(existing: str) -> str:
    digest = sha256_text(existing)
    if digest not in {EXPECTED_OLD_SANITIZED_SHA256, EXPECTED_NEW_SANITIZED_SHA256}:
        raise ValueError(f"Unexpected Pit chapter checksum: {digest}")
    repaired = authoritative_reflow()
    if normalized(repaired) != normalized(existing):
        raise ValueError("Paragraph repair changed manuscript words or order")
    return repaired


def build_replacements(requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_chapter = read_json(CONTENT_CHAPTER)
    controlled_chapter = read_json(CONTROLLED_CHAPTER)
    if content_chapter.get("content") != controlled_chapter.get("content"):
        raise ValueError("Canonical and controlled chapters diverged")
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
        {"wordCountApprox": words, "readingTimeMinutesApprox": minutes, "updatedAt": repaired_at}
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
            "reader_paragraph_repair": {
                "status": "PASS",
                "semantic_blocks": EXPECTED_BLOCK_COUNT,
                "normalized_text_unchanged": True,
                "sanitized_sha256": sanitized_hash,
            },
        }
    )

    public = read_json(PUBLICATION_DIR / "public_book.json")
    public_chapters = copy.deepcopy(public.get("chapters") or [])
    if len(public_chapters) != 1:
        raise ValueError("Pit public metadata must contain exactly one chapter")
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
        raise ValueError("Pit reader manifest must contain exactly one chapter")
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
        "status": "INVALIDATED_PARAGRAPH_REPAIR",
        "generatedAt": repaired_at,
        "source": "reader_paragraph_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": "The legacy deterministic estimate used corrupted line-wrap paragraphs. Future audio requires measured synchronization.",
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
    rows = []
    for path in sorted(PUBLICATION_DIR.rglob("*")):
        if not path.is_file() or path.name in {"checksum_manifest.json", "publication_manifest.json"}:
            continue
        payload = replacements.get(path)
        rows.append(
            {
                "file": path.relative_to(PUBLICATION_DIR).as_posix(),
                "sha256": sha256_bytes(payload) if payload is not None else sha256_file(path),
            }
        )
    replacements[PUBLICATION_DIR / "checksum_manifest.json"] = json_bytes(
        {"slug": SLUG, "generated_at": repaired_at, "files": rows}
    )
    controlled_relatives = (
        "approval_evidence.json",
        "chapters/chapter-001.json",
        "highlight_sync.json",
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
        "checksum_manifest.json",
    )
    for relative in controlled_relatives:
        root_path = PUBLICATION_DIR / relative
        payload = replacements.get(root_path, root_path.read_bytes())
        replacements[root_path] = payload
        replacements[BACKEND_PUBLICATION_DIR / relative] = payload
    evidence = {
        "schema": "earnalism.reader_paragraph_repair.v1",
        "slug": SLUG,
        "repaired_at": repaired_at,
        "raw_source_immutable": True,
        "source_hash": source_hash,
        "old_sanitized_sha256": EXPECTED_OLD_SANITIZED_SHA256,
        "new_sanitized_sha256": sanitized_hash,
        "content_hash": aggregate_content_hash,
        "provenance_hash": provenance_hash,
        "semantic_blocks": EXPECTED_BLOCK_COUNT,
        "normalized_text_unchanged": True,
        "word_count": words,
        "reading_minutes": minutes,
        "legacy_highlight_sync_invalidated": True,
        "root_backend_byte_parity": True,
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
    for publication_dir in (PUBLICATION_DIR, BACKEND_PUBLICATION_DIR):
        for row in read_json(publication_dir / "checksum_manifest.json").get("files") or []:
            target = publication_dir / str(row["file"])
            if not target.is_file() or sha256_file(target) != row.get("sha256"):
                raise ValueError(f"Controlled checksum mismatch: {target}")
    for relative in (
        "approval_evidence.json",
        "chapters/chapter-001.json",
        "highlight_sync.json",
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
        "checksum_manifest.json",
    ):
        if (PUBLICATION_DIR / relative).read_bytes() != (BACKEND_PUBLICATION_DIR / relative).read_bytes():
            raise ValueError(f"Root/backend mirror mismatch: {relative}")


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
    evidence["mode"] = "write" if args.write else "dry-run"
    evidence["changed_files"] = [
        str(path.relative_to(ROOT))
        for path, payload in replacements.items()
        if not path.exists() or path.read_bytes() != payload
    ]
    if args.write:
        for path, payload in replacements.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        verify_written(replacements)
    if args.evidence_out:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_bytes(json_bytes(evidence))
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
