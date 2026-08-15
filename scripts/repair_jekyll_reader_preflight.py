#!/usr/bin/env python3
"""Repair Jekyll's false signature chapter and retire the stale duplicate slug."""

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
    read_json,
    sha256_file,
    sha256_text,
)


SLUG = "jekyll-and-hyde"
ALIAS_SLUG = "the-strange-case-of-dr-jekyll-and-mr-hyde"
SOURCE_SHA256 = "7e19df634b5db327f75392f934268bc232179bd17c44e52fc399b640a0375958"
SOURCE_URL = "https://www.gutenberg.org/cache/epub/43/pg43.txt"
CATALOG_URL = "https://www.gutenberg.org/ebooks/43"
INDIA_TERM_URL = "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html"
RIGHTS_BASIS = (
    "Robert Louis Stevenson died in 1894. Under section 22 of India's Copyright "
    "Act, the literary-work term expired after 31 December 1954. This original "
    "1886 English work is public domain for the India-scoped release."
)
CHAPTER_TITLES = (
    "STORY OF THE DOOR",
    "SEARCH FOR MR. HYDE",
    "DR. JEKYLL WAS QUITE AT EASE",
    "THE CAREW MURDER CASE",
    "INCIDENT OF THE LETTER",
    "INCIDENT OF DR. LANYON",
    "INCIDENT AT THE WINDOW",
    "THE LAST NIGHT",
    "DR. LANYON’S NARRATIVE",
    "HENRY JEKYLL’S FULL STATEMENT OF THE CASE",
)
CONTENT_NAMES = (
    "001-story-of-the-door.json",
    "002-search-for-mr-hyde.json",
    "003-dr-jekyll-was-quite-at-ease.json",
    "004-the-carew-murder-case.json",
    "005-incident-of-the-letter.json",
    "006-incident-of-dr-lanyon.json",
    "007-incident-at-the-window.json",
    "008-the-last-night.json",
    "009-dr-lanyon-s-narrative.json",
    "010-henry-jekyll-s-full-statement-of-the-case.json",
)
OLD_FALSE_CONTENT = "009-henry-jekyll.json"
OLD_SHIFTED_CONTENT = (
    "010-dr-lanyon-s-narrative.json",
    "011-henry-jekyll-s-full-statement-of-the-case.json",
)
SIGNATURE = "“HENRY JEKYLL.”"
NARRATIVE_START = "Mr. Utterson the lawyer"
NARRATIVE_ENDPOINT = "I bring the life of that unhappy Henry Jekyll to an end."
DECISION_KEY = "repair_false_jekyll_signature_chapter_and_retire_duplicate_slug"


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_official_chapters(raw: str) -> list[str]:
    positions: list[int] = []
    for title in CHAPTER_TITLES:
        match = re.search(rf"(?m)^{re.escape(title)}$", raw)
        if not match:
            raise ValueError(f"Official source heading not found: {title}")
        positions.append(match.start())
    footer = raw.index(
        "*** END OF THE PROJECT GUTENBERG EBOOK THE STRANGE CASE OF DR. JEKYLL AND MR. HYDE ***"
    )
    chapters: list[str] = []
    for index, position in enumerate(positions):
        body_start = raw.index("\n", position) + 1
        body_end = positions[index + 1] if index + 1 < len(positions) else footer
        chapters.append(raw[body_start:body_end].strip())
    return chapters


def source_content_chapters(content_dir: Path) -> list[dict[str, Any]]:
    repaired_paths = [content_dir / "chapters" / name for name in CONTENT_NAMES]
    if all(path.is_file() for path in repaired_paths):
        return [copy.deepcopy(read_json(path)) for path in repaired_paths]

    old_paths = sorted((content_dir / "chapters").glob("*.json"))
    if len(old_paths) != 11:
        raise ValueError("Expected either repaired ten-chapter or historical eleven-unit package")
    old = [copy.deepcopy(read_json(path)) for path in old_paths]
    repaired = old[:8]
    repaired[7]["content"] = (
        str(repaired[7].get("content") or "").rstrip()
        + "\n\n"
        + SIGNATURE
        + "\n\n"
        + str(old[8].get("content") or "").lstrip()
    )
    repaired.extend(old[9:11])
    return repaired


def source_controlled_chapters(controlled_dir: Path) -> list[dict[str, Any]]:
    paths = sorted((controlled_dir / "chapters").glob("chapter-*.json"))
    if len(paths) == 10:
        return [copy.deepcopy(read_json(path)) for path in paths]
    if len(paths) != 11:
        raise ValueError("Unexpected controlled chapter count")
    old = [copy.deepcopy(read_json(path)) for path in paths]
    repaired = old[:8]
    repaired[7]["content"] = (
        str(repaired[7].get("content") or "").rstrip()
        + "\n\n"
        + SIGNATURE
        + "\n\n"
        + str(old[8].get("content") or "").lstrip()
    )
    repaired.extend(old[9:11])
    return repaired


def rights_note(repaired_at: str) -> bytes:
    return f"""# Source Rights Note: The Strange Case of Dr. Jekyll and Mr. Hyde

- Title: The Strange Case of Dr. Jekyll and Mr. Hyde
- Author: Robert Louis Stevenson
- Author death year: 1894
- Original publication year: 1886
- Source URL: {CATALOG_URL}
- Source snapshot URL: {SOURCE_URL}
- Source snapshot SHA-256: {SOURCE_SHA256}
- Source type: gutenberg
- Source format downloaded: text/plain
- Source license: Public-domain source edition; repository furniture excluded from the reader edition.
- Rights basis: {RIGHTS_BASIS}
- Commercial use allowed: yes
- Publication region: IN
- India statutory term: {INDIA_TERM_URL}
- Reader-facing boilerplate removed: yes
- Rights reverified at UTC: {repaired_at}
- Status: ready_for_reader_approval
- Blockers:
  - Fresh checksum-bound reader-preview approval is required before the corrected reader is published.

Reader-facing Earnalism editions must not expose internal admin-only evidence files.
""".encode("utf-8")


def build_alias_tombstone(repaired_at: str) -> tuple[dict[Path, bytes], set[Path]]:
    root_dir = CONTROLLED_ROOT / ALIAS_SLUG
    backend_dir = BACKEND_ROOT / ALIAS_SLUG
    source = copy.deepcopy(read_json(root_dir / "source_evidence.json"))
    source.update(
        {
            "slug": ALIAS_SLUG,
            "verification_status": "superseded_alias",
            "qa_status": "CANONICAL_ALIAS_ONLY",
            "canonical_slug": SLUG,
            "reader_facing_boilerplate_removed": True,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "superseded_at": repaired_at,
            "note": "This stale duplicate is inert. Use the checksum-bound jekyll-and-hyde edition.",
        }
    )
    approval = copy.deepcopy(read_json(root_dir / "approval_evidence.json"))
    approval.update(
        {
            "approved_to_publish": False,
            "verification_status": "superseded_alias",
            "qa_status": "CANONICAL_ALIAS_ONLY",
            "approval_scope": "superseded_duplicate_slug",
            "reader_public_release": "SUPERSEDED_ALIAS_NOT_PUBLIC",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
            "canonical_slug": SLUG,
        }
    )
    public = audio_hidden_public_book(read_json(root_dir / "public_book.json"))
    public.update(
        {
            "chapters": [],
            "approved_to_publish": False,
            "verification_status": "superseded_alias",
            "qa_status": "CANONICAL_ALIAS_ONLY",
            "publication_status": "SUPERSEDED_ALIAS",
            "publicationStatus": "draft",
            "readerStatus": "superseded_alias",
            "isPublic": False,
            "isLive": False,
            "showInPublicLibrary": False,
            "showInHomepage": False,
            "allowPublicReading": False,
            "is_published": False,
            "canonical_slug": SLUG,
            "updated_at": repaired_at,
        }
    )
    reader = copy.deepcopy(read_json(root_dir / "reader_manifest.json"))
    reader.update(
        {
            "chapter_count": 0,
            "chapters": [],
            "preview_chapter_ids": [],
            "reader_release_status": "SUPERSEDED_ALIAS_NOT_PUBLIC",
            "audio_enabled": False,
            "audiobook_enabled": False,
            "canonical_slug": SLUG,
            "generated_at": repaired_at,
        }
    )
    highlight = {
        "slug": ALIAS_SLUG,
        "status": "INVALIDATED_SUPERSEDED_ALIAS_AND_SYNTHETIC_SYNC",
        "generatedAt": repaired_at,
        "source": "jekyll_reader_boundary_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "canonical_slug": SLUG,
    }
    payloads = {
        "approval_evidence.json": json_bytes(approval),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "source_evidence.json": json_bytes(source),
    }
    checksum = checksum_bytes(payloads, repaired_at, ALIAS_SLUG)
    replacements: dict[Path, bytes] = {}
    for package_dir in (root_dir, backend_dir):
        for relative, payload in payloads.items():
            replacements[package_dir / relative] = payload
        replacements[package_dir / "checksum_manifest.json"] = checksum
    content_book_path = CONTENT_ROOT / ALIAS_SLUG / "book.json"
    if content_book_path.is_file():
        content_book = copy.deepcopy(read_json(content_book_path))
        content_book.update(
            {
                "publicationStatus": "draft",
                "readerStatus": "superseded_alias",
                "isPublic": False,
                "isLive": False,
                "showInPublicLibrary": False,
                "showInHomepage": False,
                "allowPublicReading": False,
                "is_published": False,
                "canonicalSlug": SLUG,
                "updatedAt": repaired_at,
            }
        )
        replacements[content_book_path] = json_bytes(content_book)
    stale = set(root_dir.glob("chapters/chapter-*.json")) | set(
        backend_dir.glob("chapters/chapter-*.json")
    )
    return replacements, stale


def build(requested_at: str) -> tuple[dict[Path, bytes], set[Path], dict[str, Any]]:
    content_dir = CONTENT_ROOT / SLUG
    controlled_dir = CONTROLLED_ROOT / SLUG
    backend_dir = BACKEND_ROOT / SLUG
    raw_path = content_dir / "raw/source.txt"
    if sha256_file(raw_path) != SOURCE_SHA256:
        raise ValueError("Checked-in official source snapshot checksum changed")
    raw = raw_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    official = parse_official_chapters(raw)
    source = copy.deepcopy(read_json(controlled_dir / "source_evidence.json"))
    prior = source.get("false_signature_chapter_repair")
    repaired_at = (
        str(prior.get("repaired_at"))
        if isinstance(prior, dict) and prior.get("repaired_at")
        else requested_at
    )

    content_chapters = source_content_chapters(content_dir)
    controlled_chapters = source_controlled_chapters(controlled_dir)
    if len(content_chapters) != 10 or len(controlled_chapters) != 10:
        raise ValueError("Jekyll must contain exactly ten repaired chapters")

    replacements: dict[Path, bytes] = {}
    repaired_content: list[dict[str, Any]] = []
    repaired_controlled: list[dict[str, Any]] = []
    total_words = 0
    for index, (content, controlled, source_body) in enumerate(
        zip(content_chapters, controlled_chapters, official), start=1
    ):
        text = str(content.get("content") or "")
        if normalized(text) != normalized(source_body):
            raise ValueError(f"Chapter {index}: repaired content differs from official source")
        title = CHAPTER_TITLES[index - 1]
        digest = sha256_text(text)
        words = len(WORD_RE.findall(text))
        minutes = max(1, math.ceil(words / 240))
        total_words += words
        content.update(
            {
                "bookSlug": SLUG,
                "chapterNumber": index,
                "id": f"chapter-{index:03d}",
                "title": title,
                "sourceTitle": title,
                "content": text,
                "sourceSha256": SOURCE_SHA256,
                "sanitizedSha256": digest,
                "wordCountApprox": words,
                "characterCount": len(text),
                "readingTimeMinutesApprox": minutes,
            }
        )
        controlled.update(
            {
                "id": f"chapter-{index:03d}",
                "bookSlug": SLUG,
                "order": index,
                "title": title,
                "content": text,
                "content_hash": digest,
                "sourceSha256": SOURCE_SHA256,
                "sanitizedSha256": digest,
                "word_count": words,
                "reading_minutes": minutes,
                "updated_at": repaired_at,
            }
        )
        repaired_content.append(content)
        repaired_controlled.append(controlled)
        replacements[content_dir / "chapters" / CONTENT_NAMES[index - 1]] = json_bytes(content)

    total_minutes = max(1, math.ceil(total_words / 240))
    aggregate_content_hash = sha256_text(
        json.dumps(repaired_content, ensure_ascii=False, sort_keys=True)
    )
    provenance_hash = sha256_text(
        "\n".join(
            (
                CATALOG_URL,
                str(source.get("source_name") or ""),
                str(source.get("source_license") or ""),
                aggregate_content_hash,
            )
        )
    )
    source.update(
        {
            "source_url": CATALOG_URL,
            "source_snapshot_url": SOURCE_URL,
            "source_snapshot_path": "raw/source.txt",
            "source_hash": SOURCE_SHA256,
            "source_hash_domain": "official_plaintext_download_exact_bytes",
            "content_hash": aggregate_content_hash,
            "content_hash_domain": "canonical_content_chapter_json_list_sorted_keys_utf8",
            "provenance_hash": provenance_hash,
            "provenance_hash_domain": "source_url_lf_source_name_lf_source_license_lf_content_hash",
            "rights_basis": RIGHTS_BASIS,
            "rights_verification_sources": [CATALOG_URL, INDIA_TERM_URL],
            "commercial_use_allowed": True,
            "publication_region": "IN",
            "reader_facing_boilerplate_removed": True,
            "verification_status": "approved",
            "qa_status": "READY_FOR_APPROVAL",
            "verified_at": repaired_at,
            "false_signature_chapter_repair": {
                "status": "PASS",
                "repaired_at": repaired_at,
                "chapter_count_before": 11,
                "chapter_count_after": 10,
                "false_heading": SIGNATURE,
                "false_heading_role": "letter_signature_inside_the_last_night",
                "narrative_start": NARRATIVE_START,
                "narrative_endpoint": NARRATIVE_ENDPOINT,
                "root_backend_byte_parity": True,
                "stale_duplicate_slug_retired": True,
                "legacy_synthetic_audio_rejected": True,
                "audio_enabled": False,
            },
        }
    )
    approval = copy.deepcopy(read_json(controlled_dir / "approval_evidence.json"))
    approval.update(
        {
            "approved_to_publish": False,
            "verification_status": "approved",
            "qa_status": "READY_FOR_APPROVAL",
            "approval_scope": "historical_eleven_unit_reader_approval_superseded",
            "historical_approval_superseded": True,
            "reader_public_release": "READER_APPROVAL_REQUIRED",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        }
    )
    cover = copy.deepcopy(read_json(controlled_dir / "cover_approval_evidence.json"))

    book = copy.deepcopy(read_json(content_dir / "book.json"))
    book.update(
        {
            "rightsTerritoryBasis": RIGHTS_BASIS,
            "readerStatus": "ready_for_approval",
            "publicationStatus": "draft",
            "isPublic": False,
            "isLive": False,
            "showInPublicLibrary": False,
            "showInHomepage": False,
            "allowPublicReading": False,
            "is_published": False,
            "chapterCount": 10,
            "wordCountApprox": total_words,
            "readingTimeMinutesApprox": total_minutes,
            "updatedAt": repaired_at,
        }
    )
    replacements[content_dir / "book.json"] = json_bytes(book)
    replacements[content_dir / "source-rights.md"] = rights_note(repaired_at)

    public = audio_hidden_public_book(read_json(controlled_dir / "public_book.json"))
    public_rows = copy.deepcopy(public.get("chapters") or [])[:10]
    reader = copy.deepcopy(read_json(controlled_dir / "reader_manifest.json"))
    reader_rows = copy.deepcopy(reader.get("chapters") or [])[:10]
    for index, (public_row, reader_row, chapter) in enumerate(
        zip(public_rows, reader_rows, repaired_controlled), start=1
    ):
        row = {
            "id": f"chapter-{index:03d}",
            "order": index,
            "title": CHAPTER_TITLES[index - 1],
            "word_count": chapter["word_count"],
            "reading_minutes": chapter["reading_minutes"],
            "updated_at": repaired_at,
        }
        public_row.update(row)
        reader_row.update(row)
    public.update(
        {
            "chapters": public_rows,
            "estimated_reading_time": f"{total_minutes} min",
            "source_hash": SOURCE_SHA256,
            "content_hash": aggregate_content_hash,
            "provenance_hash": provenance_hash,
            "rights_basis": RIGHTS_BASIS,
            "qa_status": "READY_FOR_APPROVAL",
            "approved_to_publish": False,
            "publication_status": "READY_FOR_APPROVAL",
            "readerStatus": "ready_for_approval",
            "publicationStatus": "draft",
            "isPublic": False,
            "isLive": False,
            "showInPublicLibrary": False,
            "showInHomepage": False,
            "allowPublicReading": False,
            "is_published": False,
            "updated_at": repaired_at,
        }
    )
    reader.update(
        {
            "chapter_count": 10,
            "chapters": reader_rows,
            "preview_chapter_ids": [f"chapter-{index:03d}" for index in range(1, 11)],
            "reader_release_status": "READY_FOR_APPROVAL",
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generated_at": repaired_at,
        }
    )
    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_FALSE_CHAPTER_AND_UNMEASURED_AUDIO",
        "generatedAt": repaired_at,
        "source": "jekyll_reader_boundary_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
    }
    payloads: dict[str, bytes] = {
        "approval_evidence.json": json_bytes(approval),
        "cover_approval_evidence.json": json_bytes(cover),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "source_evidence.json": json_bytes(source),
    }
    for index, chapter in enumerate(repaired_controlled, start=1):
        payloads[f"chapters/chapter-{index:03d}.json"] = json_bytes(chapter)
    checksum = checksum_bytes(payloads, repaired_at, SLUG)
    for package_dir in (controlled_dir, backend_dir):
        for relative, payload in payloads.items():
            replacements[package_dir / relative] = payload
        replacements[package_dir / "checksum_manifest.json"] = checksum

    alias_replacements, alias_stale = build_alias_tombstone(repaired_at)
    replacements.update(alias_replacements)

    history_path = ROOT / "internal/earnalism_intelligence/title_decision_history.json"
    history = copy.deepcopy(read_json(history_path))
    titles = history.setdefault("titles", {})
    canonical_history = copy.deepcopy(titles.get(SLUG) or {})
    canonical_history.update({
        "latest_decision": "READY_FOR_CHECKSUM_BOUND_READER_APPROVAL",
        "decision_reason": (
            "The letter signature HENRY JEKYLL is restored inside The Last Night; the reader now "
            "matches the source's exact ten-chapter structure and the stale duplicate slug is inert."
        ),
        "updated_at": repaired_at,
        "language": "en",
        "territory": "IN",
        "reader_chapter_count": 10,
        "false_signature_chapter_removed": True,
        "public_reader_status": "HIDDEN_PENDING_FRESH_APPROVAL",
        "public_audio_status": "HIDDEN_NOT_APPROVED",
        "duplicate_slug_status": "INERT_ALIAS",
        "remote_media_mutated": False,
        "next_action": "Render and obtain fresh checksum-bound reader-preview approval.",
    })
    titles[SLUG] = canonical_history

    alias_history = copy.deepcopy(titles.get(ALIAS_SLUG) or {})
    alias_history.update({
        "latest_decision": "SUPERSEDED_DUPLICATE_SLUG_INERT",
        "canonical_slug": SLUG,
        "updated_at": repaired_at,
        "public_reader_status": "HIDDEN",
        "public_audio_status": "HIDDEN",
        "remote_media_mutated": False,
        "next_action": "Retain only as an inert compatibility tombstone; do not publish or synthesize.",
    })
    titles[ALIAS_SLUG] = alias_history
    replacements[history_path] = json_bytes(history)

    ledger_path = ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl"
    ledger_lines = [
        line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    parsed = [json.loads(line) for line in ledger_lines]
    if not any(
        row.get("slug_or_area") == SLUG and row.get("decision") == DECISION_KEY
        for row in parsed
    ):
        ledger_lines.append(
            json.dumps(
                {
                    "timestamp": repaired_at,
                    "workstream": "english_25_title_controlled_release",
                    "slug_or_area": SLUG,
                    "decision": DECISION_KEY,
                    "evidence": {
                        "chapter_count_before": 11,
                        "chapter_count_after": 10,
                        "false_signature": SIGNATURE,
                        "source_snapshot_sha256": SOURCE_SHA256,
                        "root_backend_byte_parity": True,
                        "duplicate_slug_inert": True,
                        "legacy_synthetic_audio_rejected": True,
                        "audio_enabled": False,
                    },
                    "selected_option": (
                        "Restore the signature inside The Last Night, shift the two real final chapters, "
                        "retire the duplicate slug, and stop at fresh reader approval."
                    ),
                    "customer_experience_reason": "Readers receive the source-correct ten-chapter index.",
                    "release_gate_reason": "Historical reader and audio evidence was bound to malformed structure.",
                    "result": "READY_FOR_CHECKSUM_BOUND_READER_APPROVAL",
                    "next_action": "Render and obtain fresh checksum-bound reader-preview approval.",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    replacements[ledger_path] = ("\n".join(ledger_lines) + "\n").encode("utf-8")

    stale_paths = {
        content_dir / "chapters" / OLD_FALSE_CONTENT,
        *(content_dir / "chapters" / name for name in OLD_SHIFTED_CONTENT),
        controlled_dir / "chapters/chapter-011.json",
        backend_dir / "chapters/chapter-011.json",
        *alias_stale,
    }
    evidence = {
        "slug": SLUG,
        "repaired_at": repaired_at,
        "source_snapshot_sha256": SOURCE_SHA256,
        "chapter_count": 10,
        "word_count": total_words,
        "narrative_start": NARRATIVE_START,
        "narrative_endpoint": NARRATIVE_ENDPOINT,
        "false_signature_chapter_removed": True,
        "root_backend_byte_parity": True,
        "duplicate_slug_inert": True,
        "legacy_synthetic_audio_rejected": True,
        "audio_enabled": False,
        "reader_release_status": "READY_FOR_APPROVAL",
        "remote_media_mutated": False,
    }
    return replacements, stale_paths, evidence


def verify_written(replacements: dict[Path, bytes], stale_paths: set[Path]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    for path in stale_paths:
        if path.exists():
            raise ValueError(f"Stale Jekyll artifact remains: {path}")
    for slug, expected_files in ((SLUG, 16), (ALIAS_SLUG, 5)):
        root_dir = CONTROLLED_ROOT / slug
        backend_dir = BACKEND_ROOT / slug
        for package_dir in (root_dir, backend_dir):
            manifest = read_json(package_dir / "checksum_manifest.json")
            if len(manifest.get("files") or []) != expected_files:
                raise ValueError(f"{slug}: unexpected controlled checksum count")
            for row in manifest["files"]:
                target = package_dir / str(row["file"])
                if not target.is_file() or sha256_file(target) != row.get("sha256"):
                    raise ValueError(f"Controlled checksum mismatch: {target}")
        if (root_dir / "checksum_manifest.json").read_bytes() != (
            backend_dir / "checksum_manifest.json"
        ).read_bytes():
            raise ValueError(f"{slug}: root/backend checksum manifest mismatch")
        for row in read_json(root_dir / "checksum_manifest.json")["files"]:
            relative = str(row["file"])
            if (root_dir / relative).read_bytes() != (backend_dir / relative).read_bytes():
                raise ValueError(f"{slug}: root/backend mirror mismatch: {relative}")


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
    replacements, stale_paths, evidence = build(repaired_at)
    report = {
        "schema": "earnalism.jekyll_reader_boundary_repair.v1",
        "mode": "write" if args.write else "dry-run",
        "title": evidence,
        "changed_files": sorted(
            [
                str(path.relative_to(ROOT))
                for path, payload in replacements.items()
                if not path.exists() or path.read_bytes() != payload
            ]
            + [str(path.relative_to(ROOT)) for path in stale_paths if path.exists()]
        ),
    }
    if args.write:
        for path, payload in replacements.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        for path in stale_paths:
            if path.is_file():
                path.unlink()
        verify_written(replacements, stale_paths)
    if args.evidence_out:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_bytes(json_bytes(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
