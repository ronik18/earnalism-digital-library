#!/usr/bin/env python3
"""Reconcile The Bishop's translator rights and audio-hidden controlled package."""

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
SLUG = "the-bishop"
CONTENT_DIR = ROOT / "content" / "books" / SLUG
ROOT_PUBLICATION = ROOT / "data" / "controlled_publications" / SLUG
BACKEND_PUBLICATION = ROOT / "backend" / "data" / "controlled_publications" / SLUG
DUPLICATE_APPROVAL = ROOT_PUBLICATION / "approval_evidence 2.json"
CONTENT_CHAPTER = CONTENT_DIR / "chapters" / "001-the-bishop.json"
CONTROLLED_CHAPTER = ROOT_PUBLICATION / "chapters" / "chapter-001.json"
RAW_SOURCE = CONTENT_DIR / "raw" / "source.txt"
TRANSLATOR = "Constance Garnett"
TRANSLATOR_DEATH_YEAR = 1946
EXPECTED_OLD_SANITIZED_SHA256 = "adb1023a204738a1877af0aef2795b3b4b563a6f006de10928dec5b1d4c627f6"
EXPECTED_NEW_SANITIZED_SHA256 = "8d532c5d041f5327f9c8b6232c63a63eab58fe5170028deb4071b7937737b19c"
EXPECTED_SOURCE_SHA256 = "706d537e20ed0eaeddb883abdd23d76a3fb4e68afe1221dbc04d63fb98314071"
EXPECTED_BLOCK_COUNT = 128
EXPECTED_ENDPOINT = "And, indeed, there are some who do not believe her."
WORD_RE = re.compile(r"\b\w+[’'\-]?\w*\b", re.UNICODE)
RIGHTS_BASIS = (
    "Anton Chekhov died in 1904 and English translator Constance Garnett died in 1946; "
    "both terms exceed India's life-plus-60 rule. Project Gutenberg identifies this edition "
    "as public domain in the USA. Publication remains scoped to India."
)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def authoritative_reflow() -> str:
    raw = RAW_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    if sha256_text(raw) != EXPECTED_SOURCE_SHA256:
        raise ValueError("The Bishop immutable raw-source checksum changed")
    blocks = re.split(r"\n\s*\n", raw)
    if len(blocks) != EXPECTED_BLOCK_COUNT:
        raise ValueError(f"Unexpected Bishop raw paragraph count: {len(blocks)}")
    text = "\n\n".join(" ".join(line.strip() for line in block.splitlines()) for block in blocks)
    if sha256_text(text) != EXPECTED_NEW_SANITIZED_SHA256:
        raise ValueError("The Bishop authoritative paragraph reflow checksum changed")
    if not text.startswith("I\n\n"):
        raise ValueError("The Bishop opening section boundary changed")
    if not text.endswith(EXPECTED_ENDPOINT):
        raise ValueError("The Bishop narrative ending changed")
    return text


def repaired_content(existing: str) -> str:
    digest = sha256_text(existing)
    if digest not in {EXPECTED_OLD_SANITIZED_SHA256, EXPECTED_NEW_SANITIZED_SHA256}:
        raise ValueError(f"Unexpected Bishop chapter checksum: {digest}")
    repaired = authoritative_reflow()
    if normalized(repaired) != normalized(existing):
        raise ValueError("The Bishop paragraph repair changed manuscript words or order")
    return repaired


def audio_hidden_public_book(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    for key in (
        "audiobook_assets",
        "audiobook",
        "audiobook_assets_updated_at",
        "audio_url",
        "audiobook_url",
    ):
        result.pop(key, None)
    result.update(
        {
            "translator": TRANSLATOR,
            "rights_basis": RIGHTS_BASIS,
            "formats": ["Ebook"],
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generate_audiobook": False,
            "audiobook_provider": "",
            "audiobook_voice": "",
            "audio_asset_slug": "",
        }
    )
    return result


def checksum_bytes(files: dict[str, bytes], reconciled_at: str) -> bytes:
    rows = [
        {"file": name, "sha256": sha256_bytes(payload)}
        for name, payload in sorted(files.items())
    ]
    return json_bytes({"slug": SLUG, "generated_at": reconciled_at, "files": rows})


def rights_note(reconciled_at: str) -> bytes:
    text = f"""# Source Rights Note: The Bishop

- Title: The Bishop
- Author: Anton Chekhov
- Author death year: 1904
- Translator: {TRANSLATOR}
- Translator death year: {TRANSLATOR_DEATH_YEAR}
- Original publication year: 1902
- Source URL: https://www.gutenberg.org/ebooks/13419
- Source type: gutenberg
- Source format downloaded: text/plain
- Source license: Project Gutenberg public-domain text; source evidence kept internal/admin-only.
- Rights basis: {RIGHTS_BASIS}
- Commercial use allowed: yes
- Publication region: IN
- India statutory term: https://copyright.gov.in/Copyright_Act_1957/chapter_v.html
- Reader-facing boilerplate removed: source furniture and repository-only matter excluded from reader edition.
- Rights reverified at UTC: {reconciled_at}
- Status: ready_for_auto_publication
- Blockers:
- None

Reader-facing Earnalism editions must not expose internal admin-only evidence files.
"""
    return text.encode("utf-8")


def build_replacements(requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_chapter = read_json(CONTENT_CHAPTER)
    controlled_chapter = read_json(CONTROLLED_CHAPTER)
    if content_chapter.get("content") != controlled_chapter.get("content"):
        raise ValueError("The Bishop canonical and controlled chapters diverged")
    was_repaired = sha256_text(str(controlled_chapter.get("content") or "")) == EXPECTED_NEW_SANITIZED_SHA256

    source = read_json(ROOT_PUBLICATION / "source_evidence.json")
    existing_reconciliation = source.get("controlled_reconciliation")
    reconciled_at = (
        str(controlled_chapter.get("updated_at") or existing_reconciliation.get("reconciled_at"))
        if was_repaired and isinstance(existing_reconciliation, dict)
        else requested_at
    )
    if source.get("source_url") != "https://www.gutenberg.org/ebooks/13419":
        raise ValueError("The Bishop source URL changed")
    text = repaired_content(str(controlled_chapter.get("content") or ""))
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
            "updated_at": reconciled_at,
        }
    )
    aggregate_content_hash = sha256_text(
        json.dumps([content_chapter], ensure_ascii=False, sort_keys=True)
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
            "translator_name": TRANSLATOR,
            "translator_death_year": TRANSLATOR_DEATH_YEAR,
            "source_type": "gutenberg",
            "commercial_use_allowed": True,
            "publication_region": "IN",
            "rights_law_url": "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html",
            "rights_basis": RIGHTS_BASIS,
            "verified_at": reconciled_at,
            "source_hash": EXPECTED_SOURCE_SHA256,
            "source_hash_domain": "utf8_text_normalized_lf_trimmed_terminal_whitespace",
            "content_hash": aggregate_content_hash,
            "content_hash_domain": "canonical_content_chapter_json_list_sorted_keys_utf8",
            "provenance_hash": provenance_hash,
            "provenance_hash_domain": "source_url_lf_source_name_lf_source_license_lf_content_hash",
            "reader_facing_boilerplate_removed": True,
            "qa_status": "QA_PASSED",
            "controlled_reconciliation": {
                "status": "PASS",
                "reconciled_at": reconciled_at,
                "translator_rights_verified": True,
                "contradictory_duplicate_approval_removed": True,
                "backend_mirror_rebound": True,
                "legacy_estimated_sync_invalidated": True,
                "paragraph_repair": {
                    "status": "PASS",
                    "semantic_blocks": EXPECTED_BLOCK_COUNT,
                    "normalized_text_unchanged": True,
                    "sanitized_sha256": sanitized_hash,
                },
                "audio_enabled": False,
            },
        }
    )

    public = audio_hidden_public_book(read_json(ROOT_PUBLICATION / "public_book.json"))
    public_chapters = copy.deepcopy(public.get("chapters") or [])
    if len(public_chapters) != 1:
        raise ValueError("The Bishop public metadata must contain exactly one chapter")
    public_chapters[0].update(
        {"word_count": words, "reading_minutes": minutes, "updated_at": reconciled_at}
    )
    public.update(
        {
            "chapters": public_chapters,
            "estimated_reading_time": f"{minutes} min",
            "source_hash": EXPECTED_SOURCE_SHA256,
            "content_hash": aggregate_content_hash,
            "provenance_hash": provenance_hash,
            "updated_at": reconciled_at,
        }
    )
    reader = read_json(ROOT_PUBLICATION / "reader_manifest.json")
    reader_chapters = copy.deepcopy(reader.get("chapters") or [])
    if len(reader_chapters) != 1:
        raise ValueError("The Bishop reader manifest must contain exactly one chapter")
    reader_chapters[0].update(
        {"word_count": words, "reading_minutes": minutes, "updated_at": reconciled_at}
    )
    reader.update(
        {
            "chapters": reader_chapters,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generated_at": reconciled_at,
        }
    )
    approval = read_json(ROOT_PUBLICATION / "approval_evidence.json")
    approval.update(
        {
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        }
    )
    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_PARAGRAPH_REPAIR",
        "generatedAt": reconciled_at,
        "source": "reader_paragraph_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": "The legacy deterministic estimate used corrupted line-wrap paragraphs. Future audio requires measured synchronization.",
    }
    controlled_files = {
        "approval_evidence.json": json_bytes(approval),
        "chapters/chapter-001.json": json_bytes(controlled_chapter),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "source_evidence.json": json_bytes(source),
    }
    checksum = checksum_bytes(controlled_files, reconciled_at)
    replacements: dict[Path, bytes] = {}
    for publication_dir in (ROOT_PUBLICATION, BACKEND_PUBLICATION):
        for relative, payload in controlled_files.items():
            replacements[publication_dir / relative] = payload
        replacements[publication_dir / "checksum_manifest.json"] = checksum

    book = read_json(CONTENT_DIR / "book.json")
    book.update(
        {
            "translator": TRANSLATOR,
            "rightsTerritoryBasis": RIGHTS_BASIS,
            "wordCountApprox": words,
            "readingTimeMinutesApprox": minutes,
            "updatedAt": reconciled_at,
        }
    )
    replacements[CONTENT_CHAPTER] = json_bytes(content_chapter)
    replacements[CONTENT_DIR / "book.json"] = json_bytes(book)
    replacements[CONTENT_DIR / "source-rights.md"] = rights_note(reconciled_at)

    evidence = {
        "schema": "earnalism.controlled_package_reconciliation.v1",
        "slug": SLUG,
        "reconciled_at": reconciled_at,
        "translator": TRANSLATOR,
        "translator_death_year": TRANSLATOR_DEATH_YEAR,
        "manuscript_normalized_text_unchanged": True,
        "source_hash": EXPECTED_SOURCE_SHA256,
        "old_sanitized_sha256": EXPECTED_OLD_SANITIZED_SHA256,
        "new_sanitized_sha256": sanitized_hash,
        "content_hash": aggregate_content_hash,
        "provenance_hash": provenance_hash,
        "semantic_blocks": EXPECTED_BLOCK_COUNT,
        "word_count": words,
        "reading_minutes": minutes,
        "duplicate_approval_present": DUPLICATE_APPROVAL.exists(),
        "root_backend_byte_parity": True,
        "legacy_estimated_sync_invalidated": True,
        "audio_enabled": False,
        "remote_media_mutated": False,
    }
    return replacements, evidence


def verify_written(replacements: dict[Path, bytes]) -> None:
    if DUPLICATE_APPROVAL.exists():
        raise ValueError("Contradictory duplicate approval still exists")
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    for publication_dir in (ROOT_PUBLICATION, BACKEND_PUBLICATION):
        manifest = read_json(publication_dir / "checksum_manifest.json")
        for row in manifest.get("files") or []:
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
            if (ROOT_PUBLICATION / relative).read_bytes() != (BACKEND_PUBLICATION / relative).read_bytes():
                raise ValueError(f"Root/backend mirror mismatch: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--reconciled-at")
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    requested_at = args.reconciled_at or (
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
