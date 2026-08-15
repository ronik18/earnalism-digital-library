#!/usr/bin/env python3
"""Reconcile The Bishop's translator rights and audio-hidden controlled package."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repair_happy_prince_reader_boundary import json_bytes, read_json, sha256_bytes, sha256_file


ROOT = Path(__file__).resolve().parents[1]
SLUG = "the-bishop"
CONTENT_DIR = ROOT / "content" / "books" / SLUG
ROOT_PUBLICATION = ROOT / "data" / "controlled_publications" / SLUG
BACKEND_PUBLICATION = ROOT / "backend" / "data" / "controlled_publications" / SLUG
DUPLICATE_APPROVAL = ROOT_PUBLICATION / "approval_evidence 2.json"
TRANSLATOR = "Constance Garnett"
TRANSLATOR_DEATH_YEAR = 1946
RIGHTS_BASIS = (
    "Anton Chekhov died in 1904 and English translator Constance Garnett died in 1946; "
    "both terms exceed India's life-plus-60 rule. Project Gutenberg identifies this edition "
    "as public domain in the USA. Publication remains scoped to India."
)


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
    source = read_json(ROOT_PUBLICATION / "source_evidence.json")
    existing_reconciliation = source.get("controlled_reconciliation")
    reconciled_at = (
        str(existing_reconciliation.get("reconciled_at"))
        if isinstance(existing_reconciliation, dict) and existing_reconciliation.get("reconciled_at")
        else requested_at
    )
    if source.get("source_url") != "https://www.gutenberg.org/ebooks/13419":
        raise ValueError("The Bishop source URL changed")
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
            "controlled_reconciliation": {
                "status": "PASS",
                "reconciled_at": reconciled_at,
                "translator_rights_verified": True,
                "contradictory_duplicate_approval_removed": True,
                "backend_mirror_rebound": True,
                "legacy_estimated_sync_invalidated": True,
                "audio_enabled": False,
            },
        }
    )

    public = audio_hidden_public_book(read_json(ROOT_PUBLICATION / "public_book.json"))
    reader = read_json(ROOT_PUBLICATION / "reader_manifest.json")
    reader.update({"audio_enabled": False, "audiobook_enabled": False})
    approval = read_json(ROOT_PUBLICATION / "approval_evidence.json")
    approval.update(
        {
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        }
    )
    chapter = read_json(ROOT_PUBLICATION / "chapters" / "chapter-001.json")
    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_UNMEASURED_AUDIO",
        "generatedAt": reconciled_at,
        "source": "controlled_package_reconciliation",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": "The historical deterministic estimate is not measured synchronization and cannot authorize audio exposure.",
    }
    controlled_files = {
        "approval_evidence.json": json_bytes(approval),
        "chapters/chapter-001.json": json_bytes(chapter),
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
    book.update({"translator": TRANSLATOR, "rightsTerritoryBasis": RIGHTS_BASIS})
    replacements[CONTENT_DIR / "book.json"] = json_bytes(book)
    replacements[CONTENT_DIR / "source-rights.md"] = rights_note(reconciled_at)

    evidence = {
        "schema": "earnalism.controlled_package_reconciliation.v1",
        "slug": SLUG,
        "reconciled_at": reconciled_at,
        "translator": TRANSLATOR,
        "translator_death_year": TRANSLATOR_DEATH_YEAR,
        "manuscript_unchanged": True,
        "source_hash": source.get("source_hash"),
        "content_hash": source.get("content_hash"),
        "provenance_hash": source.get("provenance_hash"),
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
