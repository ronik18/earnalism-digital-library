#!/usr/bin/env python3
"""Remove publisher furniture and restore semantic paragraphs for Owl Creek Bridge."""

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
SLUG = "an-occurrence-at-owl-creek-bridge"
CONTENT_DIR = ROOT / "content" / "books" / SLUG
PUBLICATION_DIR = ROOT / "data" / "controlled_publications" / SLUG
BACKEND_PUBLICATION_DIR = ROOT / "backend" / "data" / "controlled_publications" / SLUG
CONTENT_CHAPTER = CONTENT_DIR / "chapters" / "001-an-occurrence-at-owl-creek-bridge.json"
CONTROLLED_CHAPTER = PUBLICATION_DIR / "chapters" / "chapter-001.json"
RAW_SOURCE = CONTENT_DIR / "raw" / "source.txt"
PUBLISHER_BANNER = "THE MILLENNIUM FULCRUM EDITION, 1988"
EXPECTED_OLD_SANITIZED_SHA256 = "f3a5405dc122810740007c283e07c295fdb1f246d9528ca7b48d9ae7ddcdcb15"
EXPECTED_NEW_SANITIZED_SHA256 = "516dd1e31637b06e0bbe6d17cda767fa753c35cb12a0e3ec9213af3a72abbf68"
EXPECTED_ENDPOINT = "beneath the timbers of the Owl Creek bridge."
EXPECTED_BLOCK_COUNT = 40
WORD_RE = re.compile(r"\b\w+[’'\-]?\w*\b", re.UNICODE)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def remove_publisher_banner(value: str) -> str:
    if not value.startswith(PUBLISHER_BANNER):
        raise ValueError("Reviewed Owl Creek publisher banner is missing")
    return value[len(PUBLISHER_BANNER) :].lstrip()


def authoritative_reflow() -> str:
    raw = RAW_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    blocks = re.split(r"\n\s*\n", raw)
    if blocks[0].strip() != PUBLISHER_BANNER:
        raise ValueError("Reviewed Owl Creek publisher boundary changed")
    narrative_blocks = blocks[1:]
    if len(narrative_blocks) != EXPECTED_BLOCK_COUNT:
        raise ValueError(f"Unexpected Owl Creek paragraph count: {len(narrative_blocks)}")
    repaired = "\n\n".join(
        " ".join(line.strip() for line in block.splitlines())
        for block in narrative_blocks
    )
    if sha256_text(repaired) != EXPECTED_NEW_SANITIZED_SHA256:
        raise ValueError("Authoritative Owl Creek paragraph checksum changed")
    if repaired.split("\n\n", 1)[0] != "I":
        raise ValueError("Owl Creek section-I opening changed")
    if not repaired.endswith(EXPECTED_ENDPOINT):
        raise ValueError("Owl Creek narrative ending changed")
    if PUBLISHER_BANNER in repaired:
        raise ValueError("Publisher furniture remains in Owl Creek reader text")
    return repaired


def repaired_content(existing: str) -> str:
    digest = sha256_text(existing)
    if digest == EXPECTED_OLD_SANITIZED_SHA256:
        narrative = remove_publisher_banner(existing)
    elif digest == EXPECTED_NEW_SANITIZED_SHA256:
        narrative = existing
    else:
        raise ValueError(f"Unexpected Owl Creek chapter checksum: {digest}")
    repaired = authoritative_reflow()
    if normalized(repaired) != normalized(narrative):
        raise ValueError("Owl Creek repair changed narrative words or order")
    return repaired


def build_replacements(requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_chapter = read_json(CONTENT_CHAPTER)
    controlled_chapter = read_json(CONTROLLED_CHAPTER)
    if content_chapter.get("content") != controlled_chapter.get("content"):
        raise ValueError("Canonical and controlled Owl Creek chapters diverged")
    was_repaired = sha256_text(str(controlled_chapter.get("content") or "")) == EXPECTED_NEW_SANITIZED_SHA256
    repaired_at = str(controlled_chapter.get("updated_at") or requested_at) if was_repaired else requested_at
    text = repaired_content(str(controlled_chapter.get("content") or ""))
    source_text = RAW_SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    source_hash = sha256_text(source_text)
    if source_hash != content_chapter.get("sourceSha256"):
        raise ValueError("Normalized immutable Owl Creek source checksum changed")

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
            "qa_status": "READY_FOR_APPROVAL",
            "verified_at": repaired_at,
            "reader_preflight_repair": {
                "status": "PASS",
                "removed_matter": ["millennium_fulcrum_edition_banner"],
                "semantic_blocks": EXPECTED_BLOCK_COUNT,
                "normalized_narrative_text_unchanged": True,
                "canonical_endpoint": EXPECTED_ENDPOINT,
                "sanitized_sha256": sanitized_hash,
            },
        }
    )

    public = read_json(PUBLICATION_DIR / "public_book.json")
    public_chapters = copy.deepcopy(public.get("chapters") or [])
    if len(public_chapters) != 1:
        raise ValueError("Owl Creek public metadata must contain exactly one chapter")
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
            "qa_status": "READY_FOR_APPROVAL",
            "approved_to_publish": False,
            "publication_status": "READY_FOR_APPROVAL",
            "isPublic": False,
            "isLive": False,
            "showInPublicLibrary": False,
            "showInHomepage": False,
            "allowPublicReading": False,
            "is_published": False,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generate_audiobook": False,
        }
    )
    reader = read_json(PUBLICATION_DIR / "reader_manifest.json")
    reader_chapters = copy.deepcopy(reader.get("chapters") or [])
    if len(reader_chapters) != 1:
        raise ValueError("Owl Creek reader manifest must contain exactly one chapter")
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
    approval = read_json(PUBLICATION_DIR / "approval_evidence.json")
    approval.update(
        {
            "approved_to_publish": False,
            "qa_status": "READY_FOR_APPROVAL",
            "approval_scope": "historical_admin_import_reconstruction_superseded",
            "historical_approval_superseded": True,
            "reader_public_release": "READER_APPROVAL_REQUIRED",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        }
    )
    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_READER_PREFLIGHT_REPAIR",
        "generatedAt": repaired_at,
        "source": "reader_preflight_repair",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": "Publisher furniture and artificial line-wrap paragraphs were removed. Future audio requires measured synchronization.",
    }

    replacements = {
        CONTENT_CHAPTER: json_bytes(content_chapter),
        CONTENT_DIR / "book.json": json_bytes(book),
        CONTROLLED_CHAPTER: json_bytes(controlled_chapter),
        PUBLICATION_DIR / "public_book.json": json_bytes(public),
        PUBLICATION_DIR / "reader_manifest.json": json_bytes(reader),
        PUBLICATION_DIR / "source_evidence.json": json_bytes(source),
        PUBLICATION_DIR / "approval_evidence.json": json_bytes(approval),
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
        "schema": "earnalism.reader_preflight_repair.v1",
        "slug": SLUG,
        "repaired_at": repaired_at,
        "raw_source_immutable": True,
        "source_hash": source_hash,
        "old_sanitized_sha256": EXPECTED_OLD_SANITIZED_SHA256,
        "new_sanitized_sha256": sanitized_hash,
        "content_hash": aggregate_content_hash,
        "provenance_hash": provenance_hash,
        "removed_matter": ["millennium_fulcrum_edition_banner"],
        "semantic_blocks": EXPECTED_BLOCK_COUNT,
        "normalized_narrative_text_unchanged": True,
        "canonical_endpoint": EXPECTED_ENDPOINT,
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
