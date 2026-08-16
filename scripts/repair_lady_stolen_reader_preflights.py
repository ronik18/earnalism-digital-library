#!/usr/bin/env python3
"""Repair the next two shortest English reader preflights without changing words."""

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

from repair_happy_prince_reader_boundary import json_bytes, read_json, sha256_bytes, sha256_file, sha256_text


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_ROOT = ROOT / "data" / "controlled_publications"
BACKEND_ROOT = ROOT / "backend" / "data" / "controlled_publications"
CONTENT_ROOT = ROOT / "content" / "books"
WORD_RE = re.compile(r"\b\w+[’'\-]?\w*\b", re.UNICODE)
INDIA_TERM_URL = "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html"
LADY_RIGHTS_BASIS = (
    "Anton Chekhov died in 1904 and English translator Constance Garnett died in 1946; "
    "both terms exceed India's life-plus-60 rule. Project Gutenberg identifies this edition "
    "as public domain in the USA. Publication remains scoped to India."
)


@dataclass(frozen=True)
class RepairSpec:
    slug: str
    chapter_name: str
    old_sha256: str
    new_sha256: str
    semantic_blocks: int
    endpoint: str
    translator_name: str = ""
    translator_death_year: int | None = None
    rights_basis: str = ""
    legacy_sha256s: tuple[str, ...] = ()
    source_old_sha256: str = ""
    source_new_sha256: str = ""
    source_old_fragment: str = ""
    source_new_fragment: str = ""


SPECS = (
    RepairSpec(
        slug="the-lady-with-the-dog",
        chapter_name="001-the-lady-with-the-dog.json",
        old_sha256="67e5caa912f45efb7ca8d99c9e401116e8f3e2a6a9a71c4ccb7ccd81ab62ad62",
        new_sha256="ec3ceb6ecdd81da8b89878a491fa42517849f70cf623b23bf7f0b10ecb76f391",
        semantic_blocks=129,
        endpoint="the most complicated and difficult part of it was only just beginning.",
        translator_name="Constance Garnett",
        translator_death_year=1946,
        rights_basis=LADY_RIGHTS_BASIS,
    ),
    RepairSpec(
        slug="the-stolen-white-elephant",
        chapter_name="001-the-stolen-white-elephant.json",
        old_sha256="5ef929068e406918ade3f4f9316ea248eb70e3d0eb26ae2abe54fe1aad57a693",
        new_sha256="1f73408bab8612720c3463f1a48f16b58a3403a29749e3544789e743323558f9",
        semantic_blocks=201,
        endpoint="will so remain unto the end.",
    ),
)


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def semantic_reflow(raw: str) -> str:
    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n").rstrip())
    repaired: list[str] = []
    for block in blocks:
        raw_lines = block.splitlines()
        lines = [line.strip() for line in raw_lines]
        preserve_lines = len(lines) == 1 or any(line.startswith((" ", "\t")) for line in raw_lines)
        repaired.append("\n".join(lines) if preserve_lines else " ".join(lines))
    return "\n\n".join(repaired)


def rights_note(spec: RepairSpec, repaired_at: str) -> bytes:
    if not spec.translator_name:
        return (CONTENT_ROOT / spec.slug / "source-rights.md").read_bytes()
    text = f"""# Source Rights Note: The Lady with the Dog

- Title: The Lady with the Dog
- Author: Anton Chekhov
- Author death year: 1904
- Translator: {spec.translator_name}
- Translator death year: {spec.translator_death_year}
- Original publication year: 1899
- Source URL: https://www.gutenberg.org/ebooks/13415
- Source type: gutenberg
- Source format downloaded: text/plain
- Source license: Project Gutenberg public-domain text; source evidence kept internal/admin-only.
- Rights basis: {spec.rights_basis}
- Commercial use allowed: yes
- Publication region: IN
- India statutory term: {INDIA_TERM_URL}
- Reader-facing boilerplate removed: source furniture and repository-only matter excluded from reader edition.
- Rights reverified at UTC: {repaired_at}
- Status: ready_for_auto_publication
- Blockers:
- None

Reader-facing Earnalism editions must not expose internal admin-only evidence files.
"""
    return text.encode("utf-8")


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


def checksum_bytes(files: dict[str, bytes], repaired_at: str, slug: str) -> bytes:
    rows = [
        {"file": relative, "sha256": sha256_bytes(payload)}
        for relative, payload in sorted(files.items())
    ]
    return json_bytes({"slug": slug, "generated_at": repaired_at, "files": rows})


def build_title(spec: RepairSpec, requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_dir = CONTENT_ROOT / spec.slug
    controlled_dir = CONTROLLED_ROOT / spec.slug
    backend_dir = BACKEND_ROOT / spec.slug
    raw_path = content_dir / "raw" / "source.txt"
    content_chapter_path = content_dir / "chapters" / spec.chapter_name
    controlled_chapter_path = controlled_dir / "chapters" / "chapter-001.json"
    source = read_json(controlled_dir / "source_evidence.json")
    repair = source.get("reader_paragraph_repair")
    repaired_at = (
        str(repair.get("repaired_at"))
        if isinstance(repair, dict) and repair.get("repaired_at")
        else requested_at
    )

    raw = raw_path.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip()
    original_raw = raw
    raw_corrected = False
    if spec.source_new_sha256:
        raw_digest = sha256_text(raw)
        if raw_digest == spec.source_old_sha256:
            if not spec.source_old_fragment or raw.count(spec.source_old_fragment) != 1:
                raise ValueError(f"{spec.slug}: canonical source repair anchor changed")
            raw = raw.replace(spec.source_old_fragment, spec.source_new_fragment, 1)
            raw_corrected = True
        elif raw_digest != spec.source_new_sha256:
            raise ValueError(f"{spec.slug}: unexpected raw-source checksum")
        if sha256_text(raw) != spec.source_new_sha256:
            raise ValueError(f"{spec.slug}: repaired raw-source checksum changed")
        correction = source.get("source_correction")
        if raw_corrected:
            repaired_at = requested_at
        elif isinstance(correction, dict) and correction.get("repaired_at"):
            repaired_at = str(correction["repaired_at"])
    text = semantic_reflow(raw)
    blocks = re.split(r"\n\s*\n", text)
    if len(blocks) != spec.semantic_blocks:
        raise ValueError(f"{spec.slug}: semantic block count changed")
    if sha256_text(text) != spec.new_sha256:
        raise ValueError(f"{spec.slug}: repaired manuscript checksum changed")
    if not text.endswith(spec.endpoint):
        raise ValueError(f"{spec.slug}: narrative endpoint changed")

    content_chapter = read_json(content_chapter_path)
    controlled_chapter = read_json(controlled_chapter_path)
    existing = str(content_chapter.get("content") or "")
    if existing != str(controlled_chapter.get("content") or ""):
        raise ValueError(f"{spec.slug}: canonical and controlled chapters diverged")
    if sha256_text(existing) not in {spec.old_sha256, spec.new_sha256, *spec.legacy_sha256s}:
        raise ValueError(f"{spec.slug}: unexpected existing chapter checksum")
    accepted_normalized = {normalized(text)}
    if spec.source_new_sha256:
        accepted_normalized.add(normalized(semantic_reflow(original_raw)))
    if normalized(existing) not in accepted_normalized:
        raise ValueError(f"{spec.slug}: repair changed words beyond the checksum-bound source correction")
    source_hash = sha256_text(raw)
    accepted_source_hashes = {source_hash}
    if spec.source_old_sha256:
        accepted_source_hashes.add(spec.source_old_sha256)
    if content_chapter.get("sourceSha256") not in accepted_source_hashes:
        raise ValueError(f"{spec.slug}: immutable raw-source checksum changed")

    words = len(WORD_RE.findall(text))
    minutes = max(1, math.ceil(words / 240))
    content_chapter = copy.deepcopy(content_chapter)
    content_chapter.update(
        {
            "content": text,
            "sanitizedSha256": spec.new_sha256,
            "sourceSha256": source_hash,
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
            "sourceSha256": source_hash,
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
    if spec.translator_name:
        book.update(
            {
                "translator": spec.translator_name,
                "rightsTerritoryBasis": spec.rights_basis,
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
            "reader_paragraph_repair": {
                "status": "PASS",
                "repaired_at": repaired_at,
                "semantic_blocks": spec.semantic_blocks,
                "normalized_text_unchanged": not bool(spec.source_new_sha256),
                "normalized_words_order_match_canonical_source": True,
                "sanitized_sha256": spec.new_sha256,
                "root_backend_byte_parity": True,
                "legacy_estimated_sync_invalidated": True,
                "audio_enabled": False,
            },
        }
    )
    if spec.source_new_sha256:
        source["source_correction"] = {
            "status": "PASS",
            "repaired_at": repaired_at,
            "old_source_hash": spec.source_old_sha256,
            "new_source_hash": source_hash,
            "old_sanitized_sha256": spec.old_sha256,
            "new_sanitized_sha256": spec.new_sha256,
            "checksum_bound_fragment_replacement": True,
            "words_added": len(WORD_RE.findall(spec.source_new_fragment))
            - len(WORD_RE.findall(spec.source_old_fragment)),
        }
    if spec.translator_name:
        source.update(
            {
                "translator_name": spec.translator_name,
                "translator_death_year": spec.translator_death_year,
                "source_type": "gutenberg",
                "commercial_use_allowed": True,
                "publication_region": "IN",
                "rights_law_url": INDIA_TERM_URL,
                "rights_basis": spec.rights_basis,
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
    if spec.translator_name:
        public.update({"translator": spec.translator_name, "rights_basis": spec.rights_basis})

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
    approval = read_json(controlled_dir / "approval_evidence.json")
    approval.update(
        {
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        }
    )
    highlight = {
        "slug": spec.slug,
        "status": "INVALIDATED_PARAGRAPH_REPAIR",
        "generatedAt": repaired_at,
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
    checksum = checksum_bytes(controlled_files, repaired_at, spec.slug)
    replacements: dict[Path, bytes] = {
        content_chapter_path: json_bytes(content_chapter),
        content_dir / "book.json": json_bytes(book),
        content_dir / "source-rights.md": rights_note(spec, repaired_at),
    }
    if spec.source_new_sha256:
        replacements[raw_path] = raw.encode("utf-8")
    for publication_dir in (controlled_dir, backend_dir):
        for relative, payload in controlled_files.items():
            replacements[publication_dir / relative] = payload
        replacements[publication_dir / "checksum_manifest.json"] = checksum

    evidence = {
        "slug": spec.slug,
        "repaired_at": repaired_at,
        "raw_source_immutable": not bool(spec.source_new_sha256),
        "raw_source_corrected": bool(spec.source_new_sha256),
        "raw_source_mutated_this_run": raw_corrected,
        "old_source_hash": spec.source_old_sha256 or source_hash,
        "new_source_hash": source_hash,
        "old_sanitized_sha256": spec.old_sha256,
        "new_sanitized_sha256": spec.new_sha256,
        "source_hash": source_hash,
        "content_hash": aggregate_content_hash,
        "provenance_hash": provenance_hash,
        "semantic_blocks": spec.semantic_blocks,
        "normalized_text_unchanged": not bool(spec.source_new_sha256),
        "normalized_words_order_match_canonical_source": True,
        "word_count": words,
        "reading_minutes": minutes,
        "translator_rights_bound": bool(spec.translator_name),
        "duplicate_approval_removed": not any(controlled_dir.glob("approval_evidence 2.json")),
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
        if any(controlled_dir.glob("approval_evidence 2.json")):
            raise ValueError(f"{spec.slug}: duplicate approval evidence remains")
        for publication_dir in (controlled_dir, backend_dir):
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
        "schema": "earnalism.shortest_reader_preflight_repair.v1",
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
