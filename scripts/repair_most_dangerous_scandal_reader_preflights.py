#!/usr/bin/env python3
"""Repair the Most Dangerous Game and Scandal reader preflights safely."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
from dataclasses import dataclass
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


MOST_DANGEROUS_ATTRIBUTION = (
    "Text transcription adapted from Wikisource contributors, “The Most Dangerous Game,” "
    "https://en.wikisource.org/wiki/O._Henry_Memorial_Award_Prize_Stories_of_1924/"
    "The_Most_Dangerous_Game, under CC BY-SA 4.0, "
    "https://creativecommons.org/licenses/by-sa/4.0/. The underlying 1924 story by "
    "Richard Connell is public domain in India and the United States."
)


@dataclass(frozen=True)
class RepairSpec:
    slug: str
    chapter_name: str
    old_sha256: str
    new_sha256: str
    semantic_blocks: int
    start: str
    endpoint: str
    expected_words: int
    required_attribution: str = ""


SPECS = (
    RepairSpec(
        slug="the-most-dangerous-game",
        chapter_name="001-the-most-dangerous-game.json",
        old_sha256="7427c3362c926e0bb0eb5a74c1d2431fadb8c54be7488f33cc557c3fc6a47b68",
        new_sha256="0fc44f09b5da4dccf181357f25ec32c1b21a9aada4391e51e811bfcd057930d6",
        semantic_blocks=211,
        start="OFF there to the right",
        endpoint="He had never slept in a better bed, Rainsford decided.",
        expected_words=7990,
        required_attribution=MOST_DANGEROUS_ATTRIBUTION,
    ),
    RepairSpec(
        slug="a-scandal-in-bohemia",
        chapter_name="001-a-scandal-in-bohemia.json",
        old_sha256="bce4104846c45ea4e50a2e933a961893c525260bb138bb1ea136e75973f2c92c",
        new_sha256="b916cefa2e3bf0071435341af94c94b7f7ff3466799a79005f8a9ddc60bbf462",
        semantic_blocks=262,
        start="I.\n\nTo Sherlock Holmes",
        endpoint="title of _the_ woman.",
        expected_words=8542,
    ),
)


CONTROLLED_FILES = (
    "approval_evidence.json",
    "chapters/chapter-001.json",
    "highlight_sync.json",
    "public_book.json",
    "reader_manifest.json",
    "source_evidence.json",
    "checksum_manifest.json",
)


def narrative_slice(value: str, spec: RepairSpec) -> str:
    text = value.replace("\r\n", "\n").rstrip()
    start_at = text.find(spec.start)
    end_at = text.find(spec.endpoint, start_at)
    if start_at < 0 or end_at < 0:
        raise ValueError(f"{spec.slug}: exact narrative boundary missing")
    end_at += len(spec.endpoint)
    if text.find(spec.start, start_at + 1) >= 0:
        raise ValueError(f"{spec.slug}: narrative start is not unique")
    if text.find(spec.endpoint, end_at) >= 0:
        raise ValueError(f"{spec.slug}: narrative endpoint is not unique")
    return text[start_at:end_at]


def most_dangerous_rights_note(repaired_at: str) -> bytes:
    return f"""# Source Rights Note: The Most Dangerous Game

- Title: The Most Dangerous Game
- Author: Richard Connell
- Author death year: 1949
- Original publication year: 1924
- Source URL: https://en.wikisource.org/wiki/O._Henry_Memorial_Award_Prize_Stories_of_1924/The_Most_Dangerous_Game
- Source type: wikisource_html
- Source format downloaded: text/plain
- Source license: Underlying 1924 story is public domain in the U.S. and India; Wikisource transcription/source layer is reused under CC BY-SA 4.0.
- Rights basis: Richard Connell died in 1949 and the story was first published in 1924. Public domain in India and the U.S.; canonical title corrected from manifest alias.
- Commercial use allowed: yes
- Requires attribution: yes
- Requires share alike: yes
- Required attribution: {MOST_DANGEROUS_ATTRIBUTION}
- Reader-facing boilerplate removed: Collier's byline and source public-domain notices excluded from the narrative; required license credit retained separately.
- Updated at UTC: {repaired_at}
- Status: ready_for_auto_publication
- Blockers:
- None

Reader-facing Earnalism editions must not expose internal admin-only evidence files except legally required attribution.
""".encode("utf-8")


def build_title(spec: RepairSpec, requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_dir = CONTENT_ROOT / spec.slug
    controlled_dir = CONTROLLED_ROOT / spec.slug
    backend_dir = BACKEND_ROOT / spec.slug
    content_chapter_path = content_dir / "chapters" / spec.chapter_name
    controlled_chapter_path = controlled_dir / "chapters" / "chapter-001.json"
    source = read_json(controlled_dir / "source_evidence.json")
    repair = source.get("reader_boundary_paragraph_repair")
    repaired_at = (
        str(repair.get("repaired_at"))
        if isinstance(repair, dict) and repair.get("repaired_at")
        else requested_at
    )

    raw = (content_dir / "raw" / "source.txt").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    narrative = narrative_slice(raw, spec)
    text = semantic_reflow(narrative)
    blocks = re.split(r"\n\s*\n", text)
    if len(blocks) != spec.semantic_blocks:
        raise ValueError(f"{spec.slug}: semantic block count changed")
    if sha256_text(text) != spec.new_sha256:
        raise ValueError(f"{spec.slug}: repaired manuscript checksum changed")
    if not text.startswith(spec.start) or not text.endswith(spec.endpoint):
        raise ValueError(f"{spec.slug}: narrative boundary changed")

    content_chapter = read_json(content_chapter_path)
    controlled_chapter = read_json(controlled_chapter_path)
    existing = str(content_chapter.get("content") or "")
    if existing != str(controlled_chapter.get("content") or ""):
        raise ValueError(f"{spec.slug}: canonical and controlled chapters diverged")
    if sha256_text(existing) not in {spec.old_sha256, spec.new_sha256}:
        raise ValueError(f"{spec.slug}: unexpected existing chapter checksum")
    if normalized(text) != normalized(narrative_slice(existing, spec)):
        raise ValueError(f"{spec.slug}: repair changed narrative words or order")
    source_hash = sha256_text(raw)
    if source_hash != content_chapter.get("sourceSha256"):
        raise ValueError(f"{spec.slug}: immutable raw-source checksum changed")

    words = len(WORD_RE.findall(text))
    if words != spec.expected_words:
        raise ValueError(f"{spec.slug}: word count changed")
    minutes = max(1, math.ceil(words / 240))
    content_chapter = copy.deepcopy(content_chapter)
    content_chapter.update(
        {
            "content": text,
            "sanitizedSha256": spec.new_sha256,
            "wordCountApprox": words,
            "characterCount": len(text),
            "readingTimeMinutesApprox": minutes,
        }
    )
    controlled_chapter = copy.deepcopy(controlled_chapter)
    controlled_chapter.update(
        {
            "content": text,
            "content_hash": spec.new_sha256,
            "sanitizedSha256": spec.new_sha256,
            "word_count": words,
            "reading_minutes": minutes,
            "updated_at": repaired_at,
        }
    )

    book = read_json(content_dir / "book.json")
    book.update(
        {
            "wordCountApprox": words,
            "readingTimeMinutesApprox": minutes,
            "updatedAt": repaired_at,
        }
    )
    if spec.required_attribution:
        book.update(
            {
                "requires_attribution": True,
                "requires_share_alike": True,
                "required_attribution": spec.required_attribution,
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
            "source_hash": source_hash,
            "source_hash_domain": "utf8_text_normalized_lf_trimmed_terminal_whitespace",
            "content_hash": aggregate_content_hash,
            "content_hash_domain": "canonical_content_chapter_json_list_sorted_keys_utf8",
            "provenance_hash": provenance_hash,
            "provenance_hash_domain": "source_url_lf_source_name_lf_source_license_lf_content_hash",
            "reader_facing_boilerplate_removed": True,
            "qa_status": "QA_PASSED",
            "verified_at": repaired_at,
            "reader_boundary_paragraph_repair": {
                "status": "PASS",
                "repaired_at": repaired_at,
                "narrative_start": spec.start,
                "narrative_endpoint": spec.endpoint,
                "semantic_blocks": spec.semantic_blocks,
                "narrative_words_order_unchanged": True,
                "sanitized_sha256": spec.new_sha256,
                "root_backend_byte_parity": True,
                "legacy_estimated_sync_invalidated": True,
                "audio_enabled": False,
            },
        }
    )
    if spec.required_attribution:
        source.update(
            {
                "requires_attribution": True,
                "requires_share_alike": True,
                "required_attribution": spec.required_attribution,
                "attribution_location": "reader_edition_credits_not_narrative",
            }
        )

    public = audio_hidden_public_book(read_json(controlled_dir / "public_book.json"))
    public_chapters = copy.deepcopy(public.get("chapters") or [])
    if len(public_chapters) != 1:
        raise ValueError(f"{spec.slug}: expected exactly one public chapter")
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
    if spec.required_attribution:
        public.update(
            {
                "requires_attribution": True,
                "requires_share_alike": True,
                "required_attribution": spec.required_attribution,
            }
        )

    reader = read_json(controlled_dir / "reader_manifest.json")
    reader_chapters = copy.deepcopy(reader.get("chapters") or [])
    if len(reader_chapters) != 1:
        raise ValueError(f"{spec.slug}: expected exactly one reader chapter")
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
    if spec.required_attribution:
        reader.update(
            {
                "requires_attribution": True,
                "requires_share_alike": True,
                "required_attribution": spec.required_attribution,
            }
        )

    approval = read_json(controlled_dir / "approval_evidence.json")
    approval.update(
        {"audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED", "audiobook_enabled": False}
    )
    highlight = {
        "slug": spec.slug,
        "status": "INVALIDATED_BOUNDARY_PARAGRAPH_REPAIR",
        "generatedAt": repaired_at,
        "source": "reader_boundary_paragraph_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": "Legacy deterministic sync did not match the repaired canonical narrative. Future audio requires measured synchronization.",
    }
    controlled_files = {
        "approval_evidence.json": json_bytes(approval),
        "chapters/chapter-001.json": json_bytes(controlled_chapter),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "source_evidence.json": json_bytes(source),
    }
    checksum = checksum_bytes(controlled_files, repaired_at, spec.slug)
    replacements: dict[Path, bytes] = {
        content_chapter_path: json_bytes(content_chapter),
        content_dir / "book.json": json_bytes(book),
    }
    if spec.required_attribution:
        replacements[content_dir / "source-rights.md"] = most_dangerous_rights_note(repaired_at)
    for publication_dir in (controlled_dir, backend_dir):
        for relative, payload in controlled_files.items():
            replacements[publication_dir / relative] = payload
        replacements[publication_dir / "checksum_manifest.json"] = checksum

    evidence = {
        "slug": spec.slug,
        "repaired_at": repaired_at,
        "raw_source_immutable": True,
        "old_sanitized_sha256": spec.old_sha256,
        "new_sanitized_sha256": spec.new_sha256,
        "source_hash": source_hash,
        "content_hash": aggregate_content_hash,
        "provenance_hash": provenance_hash,
        "semantic_blocks": spec.semantic_blocks,
        "narrative_words_order_unchanged": True,
        "word_count": words,
        "reading_minutes": minutes,
        "required_attribution_bound": bool(spec.required_attribution),
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
    for spec in SPECS:
        controlled_dir = CONTROLLED_ROOT / spec.slug
        backend_dir = BACKEND_ROOT / spec.slug
        for publication_dir in (controlled_dir, backend_dir):
            manifest = read_json(publication_dir / "checksum_manifest.json")
            for row in manifest.get("files") or []:
                target = publication_dir / str(row["file"])
                if not target.is_file() or sha256_file(target) != row.get("sha256"):
                    raise ValueError(f"Controlled checksum mismatch: {target}")
        for relative in CONTROLLED_FILES:
            if (controlled_dir / relative).read_bytes() != (backend_dir / relative).read_bytes():
                raise ValueError(f"{spec.slug}: root/backend mirror mismatch: {relative}")


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
    replacements: dict[Path, bytes] = {}
    evidence_rows: list[dict[str, Any]] = []
    for spec in SPECS:
        title_replacements, evidence = build_title(spec, requested_at)
        replacements.update(title_replacements)
        evidence_rows.append(evidence)
    report = {
        "schema": "earnalism.shortest_reader_boundary_preflight_repair.v1",
        "mode": "write" if args.write else "dry-run",
        "titles": evidence_rows,
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
