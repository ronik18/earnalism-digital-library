#!/usr/bin/env python3
"""Repair The Canterville Ghost chapter boundaries and paragraph structure."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repair_lady_stolen_reader_preflights import (
    BACKEND_ROOT,
    CONTENT_ROOT,
    CONTROLLED_ROOT,
    ROOT,
    WORD_RE,
    audio_hidden_public_book,
    checksum_bytes,
    json_bytes,
    normalized,
    read_json,
    semantic_reflow,
    sha256_file,
    sha256_text,
)


SLUG = "the-canterville-ghost"
CHAPTER_FILES = (
    "001-i-when-mr-hiram-b-otis-the-american-minister-bought-canterville-chase.json",
    "002-ii.json",
    "003-iii.json",
    "004-iv.json",
    "005-v.json",
    "006-vi.json",
    "007-vii.json",
)
CHAPTER_TITLES = ("I", "II", "III", "IV", "V", "VI", "VII")
OLD_SHA256 = (
    "333f0968262f7c650a35b60844231edbce145d17bcbba5eda5947b8126751814",
    "bc2f48555407040de184311fda546dde35ee0db73da5963b7b70518bcb586c9f",
    "9bd84a4f122dcefe6c287f60771de6de7bf01ec3fe5dffb1f3c3b12670fed43b",
    "ea9991cde6d92da7c32309ffdc638c1a49dd502af3595e5ebb1258c7d20dae4f",
    "5a5c951ddcd154c15c40d2296b61fcd118863baa9e4d0c51ab2941ef13e74353",
    "b17273d8c7292ebeed92eece608ed06b837292f15752b610362294451749b6c5",
    "58ba0ba31ba3f48e8bfb43403816b30f0e12fab0a32c23ad6a4c07b4444d0b38",
)
NEW_SHA256 = (
    "6f436ff68f8b4d8ece9cbea4df262f295bfdbdfde143071f547face74acc1284",
    "76f8703c8eafaa0fd4f2ee4235fbb3c137bdd56d71b379620cb2bf4e301f5ca3",
    "c624baee2a0f6c4c473ef5e2b7d641a9789fbb9ac700a23f2eba9202bacfa22c",
    "a1a1f60155fc8192a6a21e61a30c00a57061bc472c790f3e687b080f163aad49",
    "edd7b06cd8d89d79d48f2ba266cff19df7114de438b27e87a76797f5c344eb9b",
    "be067cae2299134e9b311aa67c1385d28941fbdf0f83e0ed17416ab853989712",
    "b8989aa96939b115575384ccfb8619999c078dbf34a7562a8a2b3c5b1c1f9718",
)
SEMANTIC_BLOCKS = (19, 5, 10, 6, 34, 11, 16)
WORD_COUNTS = (1492, 1177, 2270, 1696, 1662, 1525, 1471)
FIRST_SENTENCE_PREFIX = "When Mr. Hiram B. Otis, the American Minister, bought Canterville Chase,"
ENDPOINT = "Virginia blushed."


def raw_chapters(raw: str) -> list[str]:
    markers = list(re.finditer(r"(?m)^(I|II|III|IV|V|VI|VII)$", raw))
    if [match.group(1) for match in markers] != list(CHAPTER_TITLES):
        raise ValueError("Canonical Roman chapter markers changed")
    chapters: list[str] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(raw)
        chapters.append(semantic_reflow(raw[marker.end():end].strip()))
    return chapters


def build_replacements(requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_dir = CONTENT_ROOT / SLUG
    controlled_dir = CONTROLLED_ROOT / SLUG
    backend_dir = BACKEND_ROOT / SLUG
    source = read_json(controlled_dir / "source_evidence.json")
    repair = source.get("reader_chapter_boundary_repair")
    repaired_at = (
        str(repair.get("repaired_at"))
        if isinstance(repair, dict) and repair.get("repaired_at")
        else requested_at
    )
    raw = (content_dir / "raw" / "source.txt").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    source_hash = sha256_text(raw)
    chapters = raw_chapters(raw)
    if not chapters[0].startswith(FIRST_SENTENCE_PREFIX) or not chapters[-1].endswith(ENDPOINT):
        raise ValueError("Canonical narrative boundaries changed")

    content_chapters: list[dict[str, Any]] = []
    controlled_chapters: list[dict[str, Any]] = []
    replacements: dict[Path, bytes] = {}
    chapter_evidence: list[dict[str, Any]] = []
    for index, (filename, title, text) in enumerate(zip(CHAPTER_FILES, CHAPTER_TITLES, chapters)):
        content_path = content_dir / "chapters" / filename
        controlled_path = controlled_dir / "chapters" / f"chapter-{index + 1:03d}.json"
        content_chapter = read_json(content_path)
        controlled_chapter = read_json(controlled_path)
        existing = str(content_chapter.get("content") or "")
        if existing != str(controlled_chapter.get("content") or ""):
            raise ValueError(f"Chapter {index + 1}: canonical and controlled content diverged")
        if sha256_text(existing) not in {OLD_SHA256[index], NEW_SHA256[index]}:
            raise ValueError(f"Chapter {index + 1}: unexpected existing checksum")
        if index == 0 and sha256_text(existing) == OLD_SHA256[index]:
            expected_title = f"I. {FIRST_SENTENCE_PREFIX}"
            if content_chapter.get("title") != expected_title:
                raise ValueError("Chapter I title no longer contains the omitted opening sentence")
            comparable_existing = f"{FIRST_SENTENCE_PREFIX}\n\n{existing}"
        else:
            comparable_existing = existing
        if normalized(text) != normalized(comparable_existing):
            raise ValueError(f"Chapter {index + 1}: repair changed words or order")
        if sha256_text(text) != NEW_SHA256[index]:
            raise ValueError(f"Chapter {index + 1}: repaired checksum changed")
        if len(re.split(r"\n\s*\n", text)) != SEMANTIC_BLOCKS[index]:
            raise ValueError(f"Chapter {index + 1}: semantic blocks changed")
        words = len(WORD_RE.findall(text))
        if words != WORD_COUNTS[index]:
            raise ValueError(f"Chapter {index + 1}: word count changed")
        minutes = max(1, math.ceil(words / 240))

        content_chapter = copy.deepcopy(content_chapter)
        content_chapter.update(
            {
                "title": title,
                "content": text,
                "sanitizedSha256": NEW_SHA256[index],
                "wordCountApprox": words,
                "characterCount": len(text),
                "readingTimeMinutesApprox": minutes,
            }
        )
        controlled_chapter = copy.deepcopy(controlled_chapter)
        controlled_chapter.update(
            {
                "title": title,
                "content": text,
                "content_hash": NEW_SHA256[index],
                "sanitizedSha256": NEW_SHA256[index],
                "word_count": words,
                "reading_minutes": minutes,
                "updated_at": repaired_at,
            }
        )
        content_chapters.append(content_chapter)
        controlled_chapters.append(controlled_chapter)
        replacements[content_path] = json_bytes(content_chapter)
        chapter_evidence.append(
            {
                "id": f"chapter-{index + 1:03d}",
                "title": title,
                "semantic_blocks": SEMANTIC_BLOCKS[index],
                "word_count": words,
                "sanitized_sha256": NEW_SHA256[index],
                "normalized_words_order_unchanged": True,
            }
        )

    total_words = sum(WORD_COUNTS)
    total_minutes = max(1, math.ceil(total_words / 240))
    book = read_json(content_dir / "book.json")
    book.update(
        {
            "wordCountApprox": total_words,
            "readingTimeMinutesApprox": total_minutes,
            "updatedAt": repaired_at,
        }
    )
    replacements[content_dir / "book.json"] = json_bytes(book)

    aggregate_content_hash = sha256_text(
        json.dumps(content_chapters, ensure_ascii=False, sort_keys=True)
    )
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
            "reader_chapter_boundary_repair": {
                "status": "PASS",
                "repaired_at": repaired_at,
                "chapter_count": 7,
                "opening_sentence_restored_to_chapter_i": True,
                "chapter_i_title_normalized": "I",
                "narrative_endpoint": ENDPOINT,
                "normalized_words_order_unchanged": True,
                "root_backend_byte_parity": True,
                "legacy_estimated_sync_invalidated": True,
                "audio_enabled": False,
            },
        }
    )

    public = audio_hidden_public_book(read_json(controlled_dir / "public_book.json"))
    public_rows = copy.deepcopy(public.get("chapters") or [])
    reader = read_json(controlled_dir / "reader_manifest.json")
    reader_rows = copy.deepcopy(reader.get("chapters") or [])
    if len(public_rows) != 7 or len(reader_rows) != 7:
        raise ValueError("Expected seven public and reader chapter rows")
    for index, title in enumerate(CHAPTER_TITLES):
        row_update = {
            "title": title,
            "word_count": WORD_COUNTS[index],
            "reading_minutes": max(1, math.ceil(WORD_COUNTS[index] / 240)),
            "updated_at": repaired_at,
        }
        public_rows[index].update(row_update)
        reader_rows[index].update(row_update)
    public.update(
        {
            "chapters": public_rows,
            "estimated_reading_time": f"{total_minutes} min",
            "source_hash": source_hash,
            "content_hash": aggregate_content_hash,
            "provenance_hash": provenance_hash,
            "updated_at": repaired_at,
        }
    )
    reader.update(
        {
            "chapters": reader_rows,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generated_at": repaired_at,
        }
    )
    approval = read_json(controlled_dir / "approval_evidence.json")
    approval.update(
        {"audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED", "audiobook_enabled": False}
    )
    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_CHAPTER_BOUNDARY_PARAGRAPH_REPAIR",
        "generatedAt": repaired_at,
        "source": "reader_chapter_boundary_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": "Legacy deterministic sync did not match the corrected chapter boundaries. Future audio requires measured synchronization.",
    }
    controlled_files = {
        "approval_evidence.json": json_bytes(approval),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "source_evidence.json": json_bytes(source),
    }
    for index, chapter in enumerate(controlled_chapters, start=1):
        controlled_files[f"chapters/chapter-{index:03d}.json"] = json_bytes(chapter)
    checksum = checksum_bytes(controlled_files, repaired_at, SLUG)
    for publication_dir in (controlled_dir, backend_dir):
        for relative, payload in controlled_files.items():
            replacements[publication_dir / relative] = payload
        replacements[publication_dir / "checksum_manifest.json"] = checksum

    evidence = {
        "slug": SLUG,
        "repaired_at": repaired_at,
        "raw_source_immutable": True,
        "source_hash": source_hash,
        "content_hash": aggregate_content_hash,
        "provenance_hash": provenance_hash,
        "chapter_count": 7,
        "opening_sentence_restored_to_chapter_i": True,
        "chapter_i_title_normalized": "I",
        "narrative_endpoint": ENDPOINT,
        "word_count": total_words,
        "reading_minutes": total_minutes,
        "chapters": chapter_evidence,
        "root_backend_byte_parity": True,
        "legacy_estimated_sync_invalidated": True,
        "audio_enabled": False,
        "remote_media_mutated": False,
    }
    return replacements, evidence


def verify_written(replacements: dict[Path, bytes]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    controlled_dir = CONTROLLED_ROOT / SLUG
    backend_dir = BACKEND_ROOT / SLUG
    for publication_dir in (controlled_dir, backend_dir):
        manifest = read_json(publication_dir / "checksum_manifest.json")
        for row in manifest.get("files") or []:
            target = publication_dir / str(row["file"])
            if not target.is_file() or sha256_file(target) != row.get("sha256"):
                raise ValueError(f"Controlled checksum mismatch: {target}")
    for relative in [row["file"] for row in read_json(controlled_dir / "checksum_manifest.json")["files"]] + ["checksum_manifest.json"]:
        if (controlled_dir / relative).read_bytes() != (backend_dir / relative).read_bytes():
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
    report = {
        "schema": "earnalism.canterville_reader_preflight_repair.v1",
        "mode": "write" if args.write else "dry-run",
        "title": evidence,
        "changed_files": [
            str(path.relative_to(ROOT))
            for path, payload in replacements.items()
            if not path.exists() or path.read_bytes() != payload
        ],
    }
    if args.write:
        for path, payload in replacements.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        verify_written(replacements)
    if args.evidence_out:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_bytes(json_bytes(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
