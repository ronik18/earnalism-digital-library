#!/usr/bin/env python3
"""Repair The Science of Getting Rich reader package and stop at approval."""

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

from repair_lady_stolen_reader_preflights import (
    BACKEND_ROOT,
    CONTENT_ROOT,
    CONTROLLED_ROOT,
    ROOT,
    audio_hidden_public_book,
    checksum_bytes,
    json_bytes,
    read_json,
    sha256_file,
    sha256_text,
)


SLUG = "the-science-of-getting-rich"
UPSTREAM_SOURCE_SHA256 = "adc3fb17f24801597561e992d858e124c8d9b4c6e3bf7593d713e7a71d252744"
SOURCE_SHA256 = "4de04867ec7814f6e7053582eaf50ad3c6817256d06141a5cee93c64f499557b"
SOURCE_URL = "https://www.gutenberg.org/cache/epub/59844/pg59844.txt"
CATALOG_URL = "https://www.gutenberg.org/ebooks/59844"
INDIA_TERM_URL = (
    "https://www.indiacode.nic.in/show-data?actid=AC_CEN_9_30_00006_195714_"
    "1517807321712&orderno=23&sectionId=14525&sectionno=22"
)
RIGHTS_BASIS = (
    "Wallace D. Wattles died in 1911. Under section 22 of India's Copyright "
    "Act, the literary-work term ran for 60 years from the beginning of the "
    "calendar year following his death and expired on 31 December 1971. The "
    "work is public domain for the India-scoped release."
)
NARRATIVE_START = "This book is pragmatical, not philosophical; a practical manual"
NARRATIVE_ENDPOINT = "the steadiness of their faith, and the depth of their\n\ngratitude."
DECISION_KEY = "remove_publisher_advertising_and_rebind_science_reader_candidate"
CHAPTER_COUNT = 18
EXPECTED_METADATA_WORDS = 22649
RAW_RELATIVE = Path("raw/source.txt")
OLD_CONTENT_AD = Path("chapters/019-further-aids-toward-getting-rich-right.json")
OLD_CONTROLLED_AD = Path("chapters/chapter-019.json")
CHAPTER_TITLES = (
    "PREFACE",
    "CHAPTER I. THE RIGHT TO BE RICH",
    "CHAPTER II. THERE IS A SCIENCE OF GETTING RICH",
    "CHAPTER III. IS OPPORTUNITY MONOPOLIZED?",
    "CHAPTER IV. THE FIRST PRINCIPLE IN THE SCIENCE OF GETTING RICH",
    "CHAPTER V. INCREASING LIFE",
    "CHAPTER VI. HOW RICHES COME TO YOU",
    "CHAPTER VII. GRATITUDE",
    "CHAPTER VIII. THINKING IN THE CERTAIN WAY",
    "CHAPTER IX. HOW TO USE THE WILL",
    "CHAPTER X. FURTHER USE OF THE WILL",
    "CHAPTER XI. ACTING IN THE CERTAIN WAY",
    "CHAPTER XII. EFFICIENT ACTION",
    "CHAPTER XIII. GETTING INTO THE RIGHT BUSINESS",
    "CHAPTER XIV. THE IMPRESSION OF INCREASE",
    "CHAPTER XV. THE ADVANCING MAN",
    "CHAPTER XVI. SOME CAUTIONS, AND CONCLUDING OBSERVATIONS",
    "CHAPTER XVII. SUMMARY OF THE SCIENCE OF GETTING RICH",
)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def canonical_source_bytes(value: bytes) -> bytes:
    """Normalize source transport formatting without changing reader text."""
    text = value.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    normalized_text = "\n".join(line.rstrip(" \t") for line in text.split("\n"))
    return (normalized_text.rstrip("\n") + "\n").encode("utf-8")


def source_headings() -> tuple[str, ...]:
    return ("PREFACE.",) + tuple(
        title if title.endswith(("?", "!", ".")) else f"{title}."
        for title in CHAPTER_TITLES[1:]
    )


def parse_source_chapters(raw: str) -> list[str]:
    start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK THE SCIENCE OF GETTING RICH ***"
    start = raw.index(start_marker)
    positions: list[int] = []
    for heading in source_headings():
        match = re.search(rf"(?m)^{re.escape(heading)}$", raw[start:])
        if not match:
            raise ValueError(f"Official source heading not found: {heading}")
        positions.append(start + match.start())
    ad_start = raw.index("\nFURTHER AIDS TOWARD GETTING RICH RIGHT", positions[-1])
    chapters: list[str] = []
    for index, position in enumerate(positions):
        body_start = raw.index("\n", position) + 1
        body_end = positions[index + 1] if index + 1 < len(positions) else ad_start
        body = raw[body_start:body_end]
        if index == CHAPTER_COUNT - 1:
            body = re.sub(r"\n\s*\*\s+\*\s+\*\s+\*\s+\*\s*$", "", body)
        chapters.append(body.strip())
    return chapters


def clean_terminal_ornament(value: str) -> str:
    return re.sub(r"\n\s*\* \* \* \* \*\s*$", "", value).rstrip()


def rights_note(repaired_at: str) -> bytes:
    return f"""# Source Rights Note: The Science of Getting Rich

- Title: The Science of Getting Rich
- Author: W. D. Wattles
- Author death year: 1911
- Original publication year: 1910
- Source URL: {CATALOG_URL}
- Source snapshot URL: {SOURCE_URL}
- Upstream source download SHA-256: {UPSTREAM_SOURCE_SHA256}
- Canonical source snapshot SHA-256: {SOURCE_SHA256}
- Source type: gutenberg
- Source format downloaded: text/plain
- Source license: Public-domain source edition; repository and publisher furniture excluded from the reader edition.
- Rights basis: {RIGHTS_BASIS}
- Commercial use allowed: yes
- Publication region: IN
- India statutory term: {INDIA_TERM_URL}
- Reader-facing boilerplate removed: yes; source furniture, publisher advertisements, prices, addresses, and repository-only matter excluded.
- Rights reverified at UTC: {repaired_at}
- Status: ready_for_reader_approval
- Blockers:
  - Fresh checksum-bound reader-preview approval is required before publication or pilot synthesis.

Reader-facing Earnalism editions must not expose internal admin-only evidence files.
""".encode("utf-8")


def build(repaired_at: str, source_snapshot: Path | None = None) -> tuple[dict[Path, bytes], set[Path], dict[str, Any]]:
    content_dir = CONTENT_ROOT / SLUG
    controlled_dir = CONTROLLED_ROOT / SLUG
    backend_dir = BACKEND_ROOT / SLUG
    raw_path = content_dir / RAW_RELATIVE
    if raw_path.is_file():
        raw_bytes = raw_path.read_bytes()
    elif source_snapshot and source_snapshot.is_file():
        raw_bytes = source_snapshot.read_bytes()
    else:
        raise ValueError("Exact official source snapshot is required for the first repair run")
    raw_digest = hashlib.sha256(raw_bytes).hexdigest()
    if raw_digest not in {UPSTREAM_SOURCE_SHA256, SOURCE_SHA256}:
        raise ValueError("Official source snapshot checksum changed")
    canonical_bytes = canonical_source_bytes(raw_bytes)
    if hashlib.sha256(canonical_bytes).hexdigest() != SOURCE_SHA256:
        raise ValueError("Canonical source snapshot checksum changed")
    raw = canonical_bytes.decode("utf-8").rstrip()
    official_chapters = parse_source_chapters(raw)

    content_paths = sorted((content_dir / "chapters").glob("*.json"))
    controlled_paths = sorted((controlled_dir / "chapters").glob("*.json"))
    if len(content_paths) not in {CHAPTER_COUNT, CHAPTER_COUNT + 1}:
        raise ValueError("Unexpected canonical chapter count")
    if len(controlled_paths) not in {CHAPTER_COUNT, CHAPTER_COUNT + 1}:
        raise ValueError("Unexpected controlled chapter count")
    content_paths = [path for path in content_paths if path.name != OLD_CONTENT_AD.name]
    controlled_paths = [path for path in controlled_paths if path.name != OLD_CONTROLLED_AD.name]
    if len(content_paths) != CHAPTER_COUNT or len(controlled_paths) != CHAPTER_COUNT:
        raise ValueError("Expected Preface plus Chapters I-XVII")

    source = copy.deepcopy(read_json(controlled_dir / "source_evidence.json"))
    prior_repair = source.get("reader_advertising_boundary_repair")
    effective_at = (
        str(prior_repair.get("repaired_at"))
        if isinstance(prior_repair, dict) and prior_repair.get("repaired_at")
        else repaired_at
    )
    replacements: dict[Path, bytes] = {raw_path: canonical_bytes}
    content_chapters: list[dict[str, Any]] = []
    controlled_chapters: list[dict[str, Any]] = []
    metadata_words: list[int] = []
    for index, (content_path, controlled_path, official) in enumerate(
        zip(content_paths, controlled_paths, official_chapters), start=1
    ):
        content_chapter = copy.deepcopy(read_json(content_path))
        controlled_chapter = copy.deepcopy(read_json(controlled_path))
        text = str(content_chapter.get("content") or "")
        if index == CHAPTER_COUNT:
            text = clean_terminal_ornament(text)
        if normalized(text) != normalized(official):
            raise ValueError(f"Chapter {index}: canonical content differs from official source")
        if index < CHAPTER_COUNT and text != str(controlled_chapter.get("content") or ""):
            raise ValueError(f"Chapter {index}: canonical and controlled content diverged")
        title = CHAPTER_TITLES[index - 1]
        digest = sha256_text(text)
        words = int(content_chapter.get("wordCountApprox") or controlled_chapter.get("word_count") or 0)
        if words <= 0:
            raise ValueError(f"Chapter {index}: missing historical word-count estimate")
        minutes = max(1, math.ceil(words / 240))
        metadata_words.append(words)
        content_chapter.update(
            {
                "title": title,
                "content": text,
                "sourceSha256": SOURCE_SHA256,
                "sanitizedSha256": digest,
                "wordCountApprox": words,
                "characterCount": len(text),
                "readingTimeMinutesApprox": minutes,
            }
        )
        controlled_chapter.update(
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
                "updated_at": effective_at,
            }
        )
        content_chapters.append(content_chapter)
        controlled_chapters.append(controlled_chapter)
        replacements[content_path] = json_bytes(content_chapter)

    if sum(metadata_words) != EXPECTED_METADATA_WORDS:
        raise ValueError(f"Narrative word-count estimate changed: {sum(metadata_words)}")
    total_minutes = max(1, math.ceil(EXPECTED_METADATA_WORDS / 240))
    aggregate_content_hash = sha256_text(
        json.dumps(content_chapters, ensure_ascii=False, sort_keys=True)
    )
    provenance_hash = sha256_text(
        "\n".join(
            (
                str(source.get("source_url") or CATALOG_URL),
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
            "source_hash": SOURCE_SHA256,
            "source_hash_domain": "official_plaintext_utf8_normalized_lf_no_trailing_space_exact_bytes",
            "upstream_source_sha256": UPSTREAM_SOURCE_SHA256,
            "upstream_source_hash_domain": "official_plaintext_download_exact_bytes",
            "source_snapshot_path": str(RAW_RELATIVE),
            "upstream_snapshot_drift_from_historical_hash": True,
            "superseded_source_hash": "0295b8681506d1e44c06127b1b543198d38ef33ba08364fcbaee2d2b40489796",
            "content_hash": aggregate_content_hash,
            "content_hash_domain": "canonical_content_chapter_json_list_sorted_keys_utf8",
            "provenance_hash": provenance_hash,
            "provenance_hash_domain": "source_url_lf_source_name_lf_source_license_lf_content_hash",
            "rights_basis": RIGHTS_BASIS,
            "rights_verification_sources": [CATALOG_URL, INDIA_TERM_URL],
            "commercial_use_allowed": True,
            "publication_region": "IN",
            "reader_facing_boilerplate_removed": True,
            "publisher_advertising_removed": True,
            "verification_status": "approved",
            "qa_status": "READY_FOR_APPROVAL",
            "verified_at": effective_at,
            "reader_advertising_boundary_repair": {
                "status": "PASS",
                "repaired_at": effective_at,
                "chapter_count": CHAPTER_COUNT,
                "narrative_start": NARRATIVE_START,
                "narrative_endpoint": NARRATIVE_ENDPOINT,
                "publisher_advertising_removed": True,
                "publisher_advertising_unit_removed": "chapter-019",
                "terminal_ornament_removed": True,
                "official_source_snapshot_sha256": SOURCE_SHA256,
                "official_upstream_download_sha256": UPSTREAM_SOURCE_SHA256,
                "root_backend_byte_parity": True,
                "legacy_estimated_sync_invalidated": True,
                "fresh_reader_approval_required": True,
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
            "approval_scope": "historical_admin_import_reconstruction_superseded",
            "historical_approval_superseded": True,
            "reader_public_release": "READER_APPROVAL_REQUIRED",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        }
    )

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
            "chapterCount": CHAPTER_COUNT,
            "wordCountApprox": EXPECTED_METADATA_WORDS,
            "readingTimeMinutesApprox": total_minutes,
            "updatedAt": effective_at,
        }
    )
    replacements[content_dir / "book.json"] = json_bytes(book)
    replacements[content_dir / "source-rights.md"] = rights_note(effective_at)

    public = audio_hidden_public_book(read_json(controlled_dir / "public_book.json"))
    public_rows = copy.deepcopy(public.get("chapters") or [])[:CHAPTER_COUNT]
    reader = copy.deepcopy(read_json(controlled_dir / "reader_manifest.json"))
    reader_rows = copy.deepcopy(reader.get("chapters") or [])[:CHAPTER_COUNT]
    if len(public_rows) != CHAPTER_COUNT or len(reader_rows) != CHAPTER_COUNT:
        raise ValueError("Expected eighteen public and reader chapter rows")
    for index, (public_row, reader_row, controlled_chapter) in enumerate(
        zip(public_rows, reader_rows, controlled_chapters), start=1
    ):
        row_update = {
            "id": f"chapter-{index:03d}",
            "order": index,
            "title": CHAPTER_TITLES[index - 1],
            "word_count": controlled_chapter["word_count"],
            "reading_minutes": controlled_chapter["reading_minutes"],
            "updated_at": effective_at,
        }
        public_row.update(row_update)
        reader_row.update(row_update)
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
            "updated_at": effective_at,
        }
    )
    reader.update(
        {
            "chapter_count": CHAPTER_COUNT,
            "chapters": reader_rows,
            "preview_chapter_ids": [f"chapter-{index:03d}" for index in range(1, CHAPTER_COUNT + 1)],
            "reader_release_status": "READY_FOR_APPROVAL",
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generated_at": effective_at,
        }
    )
    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_ADVERTISING_BOUNDARY_AND_UNMEASURED_SYNC",
        "generatedAt": effective_at,
        "source": "reader_advertising_boundary_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": (
            "Publisher advertising was removed and the legacy timing data was synthetic. "
            "Any future audiobook requires fresh audio and measured synchronization."
        ),
    }

    controlled_payloads: dict[str, bytes] = {
        "approval_evidence.json": json_bytes(approval),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "source_evidence.json": json_bytes(source),
    }
    for index, chapter in enumerate(controlled_chapters, start=1):
        controlled_payloads[f"chapters/chapter-{index:03d}.json"] = json_bytes(chapter)
    checksum = checksum_bytes(controlled_payloads, effective_at, SLUG)
    if len(read_json_bytes(checksum).get("files") or []) != 23:
        raise ValueError("Expected exactly 23 checksum-bound controlled artifacts")
    for publication_dir in (controlled_dir, backend_dir):
        for relative, payload in controlled_payloads.items():
            replacements[publication_dir / relative] = payload
        replacements[publication_dir / "checksum_manifest.json"] = checksum

    history = copy.deepcopy(read_json(ROOT / "internal/earnalism_intelligence/title_decision_history.json"))
    titles = history.setdefault("titles", {})
    titles[SLUG] = {
        "latest_decision": "READY_FOR_CHECKSUM_BOUND_READER_APPROVAL",
        "decision_reason": (
            "The narrative now ends at Chapter XVII; publisher advertisements and the "
            "terminal ornament are excluded, source provenance is reproducible, and stale "
            "synthetic synchronization is invalidated."
        ),
        "updated_at": effective_at,
        "language": "en",
        "territory": "IN",
        "reader_chapter_count": CHAPTER_COUNT,
        "publisher_advertising_removed": True,
        "public_reader_status": "HIDDEN_PENDING_FRESH_APPROVAL",
        "public_audio_status": "HIDDEN_NOT_APPROVED",
        "legacy_estimated_sync_invalidated": True,
        "remote_media_mutated": False,
        "next_action": "Render and obtain fresh checksum-bound reader-preview approval.",
    }
    replacements[ROOT / "internal/earnalism_intelligence/title_decision_history.json"] = json_bytes(history)

    ledger_path = ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl"
    ledger_lines = [
        line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    parsed_ledger_rows = [json.loads(line) for line in ledger_lines]
    if not any(
        row.get("slug_or_area") == SLUG and row.get("decision") == DECISION_KEY
        for row in parsed_ledger_rows
    ):
        ledger_lines.append(
            json.dumps(
                {
                "timestamp": effective_at,
                "workstream": "english_25_title_controlled_release",
                "slug_or_area": SLUG,
                "decision": DECISION_KEY,
                "evidence": {
                    "chapter_count_before": 19,
                    "chapter_count_after": CHAPTER_COUNT,
                    "publisher_advertising_removed": True,
                    "official_source_snapshot_sha256": SOURCE_SHA256,
                    "official_upstream_download_sha256": UPSTREAM_SOURCE_SHA256,
                    "root_backend_byte_parity": True,
                    "legacy_estimated_sync_invalidated": True,
                    "audio_enabled": False,
                },
                "selected_option": (
                    "Preserve Preface and Chapters I-XVII, remove publisher advertising, "
                    "rebind the controlled package, and stop at fresh reader approval."
                ),
                "customer_experience_reason": "Readers receive only the canonical work, without publisher sales copy.",
                "release_gate_reason": "The previous approval and timing evidence were not bound to the corrected narrative.",
                "result": "READY_FOR_CHECKSUM_BOUND_READER_APPROVAL",
                "next_action": titles[SLUG]["next_action"],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    replacements[ledger_path] = ("\n".join(ledger_lines) + "\n").encode("utf-8")

    stale_paths = {
        content_dir / OLD_CONTENT_AD,
        controlled_dir / OLD_CONTROLLED_AD,
        backend_dir / OLD_CONTROLLED_AD,
    }
    evidence = {
        "slug": SLUG,
        "repaired_at": effective_at,
        "source_snapshot_sha256": SOURCE_SHA256,
        "upstream_source_sha256": UPSTREAM_SOURCE_SHA256,
        "source_snapshot_reproducible": True,
        "chapter_count": CHAPTER_COUNT,
        "metadata_word_count": EXPECTED_METADATA_WORDS,
        "narrative_start": NARRATIVE_START,
        "narrative_endpoint": NARRATIVE_ENDPOINT,
        "publisher_advertising_removed": True,
        "terminal_ornament_removed": True,
        "checksum_artifact_count": 23,
        "root_backend_byte_parity": True,
        "legacy_estimated_sync_invalidated": True,
        "audio_enabled": False,
        "reader_release_status": "READY_FOR_APPROVAL",
        "remote_media_mutated": False,
    }
    return replacements, stale_paths, evidence


def read_json_bytes(value: bytes) -> dict[str, Any]:
    return json.loads(value.decode("utf-8"))


def verify_written(replacements: dict[Path, bytes], stale_paths: set[Path]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    for path in stale_paths:
        if path.exists():
            raise ValueError(f"Stale publisher-advertising artifact remains: {path}")
    controlled_dir = CONTROLLED_ROOT / SLUG
    backend_dir = BACKEND_ROOT / SLUG
    for publication_dir in (controlled_dir, backend_dir):
        manifest = read_json(publication_dir / "checksum_manifest.json")
        if len(manifest.get("files") or []) != 23:
            raise ValueError("Controlled checksum manifest must contain 23 entries")
        for row in manifest["files"]:
            target = publication_dir / str(row["file"])
            if not target.is_file() or sha256_file(target) != row.get("sha256"):
                raise ValueError(f"Controlled checksum mismatch: {target}")
    for row in read_json(controlled_dir / "checksum_manifest.json")["files"]:
        relative = str(row["file"])
        if (controlled_dir / relative).read_bytes() != (backend_dir / relative).read_bytes():
            raise ValueError(f"Root/backend mirror mismatch: {relative}")
    if (controlled_dir / "checksum_manifest.json").read_bytes() != (backend_dir / "checksum_manifest.json").read_bytes():
        raise ValueError("Root/backend checksum manifest mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repaired-at")
    parser.add_argument("--source-snapshot", type=Path)
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    repaired_at = args.repaired_at or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if args.write
        else "DRY_RUN"
    )
    replacements, stale_paths, evidence = build(repaired_at, args.source_snapshot)
    report = {
        "schema": "earnalism.science_getting_rich_reader_preflight_repair.v1",
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
