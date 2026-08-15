#!/usr/bin/env python3
"""Fail the current Metamorphosis reader package closed on translation rights."""

from __future__ import annotations

import argparse
import copy
import json
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
)


SLUG = "the-metamorphosis"
TRANSLATOR = "David Wyllie"
SOURCE_URL = "https://www.gutenberg.org/ebooks/5200"
RIGHTS_DECISION = "BLOCKED_COPYRIGHTED_TRANSLATION_PERMISSION_REQUIRED"
DECISION_KEY = "block_copyrighted_wyllie_translation_and_preserve_private_candidate"
CONTROLLED_FILES = (
    "approval_evidence.json",
    "chapters/chapter-001.json",
    "chapters/chapter-002.json",
    "chapters/chapter-003.json",
    "highlight_sync.json",
    "public_book.json",
    "reader_manifest.json",
    "source_evidence.json",
    "checksum_manifest.json",
)


def rights_note(reassessed_at: str) -> bytes:
    return f"""# Source Rights Note: The Metamorphosis

- Title: The Metamorphosis
- Author: Franz Kafka
- Author death year: 1924
- Original publication year: 1915
- Translator: {TRANSLATOR}
- Source URL: {SOURCE_URL}
- Source type: gutenberg_text
- Source format downloaded: text/plain
- Source status: Project Gutenberg labels ebook 5200 as a copyrighted ebook and identifies David Wyllie as translator.
- Rights basis: The original German work is public domain, but the imported English translation is a separate copyrighted work. Earnalism has no checksum-bound commercial redistribution permission for this translation.
- Commercial use allowed: not established
- Publication region: IN
- Reader-facing boilerplate removed: yes, but sanitization does not remove translation copyright.
- Rights reassessed at UTC: {reassessed_at}
- Status: blocked_copyrighted_translation_permission_required
- Blockers:
  - Replace the manuscript with a commercially reusable English translation whose license and attribution are verified, or obtain written commercial permission from the translation copyright holder.
  - Re-run source, reader, audiobook, checksum, and both human gates after any manuscript replacement.

The current manuscript may remain in private audit storage only. It must not be published, synthesized, uploaded, or exposed by Earnalism.
""".encode("utf-8")


def build(reassessed_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    content_dir = CONTENT_ROOT / SLUG
    controlled_dir = CONTROLLED_ROOT / SLUG
    backend_dir = BACKEND_ROOT / SLUG
    source = copy.deepcopy(read_json(controlled_dir / "source_evidence.json"))
    existing_reassessment = source.get("rights_reassessment")
    effective_at = (
        str(existing_reassessment.get("reassessed_at"))
        if isinstance(existing_reassessment, dict)
        and existing_reassessment.get("reassessed_at")
        else reassessed_at
    )

    content_chapter_paths = sorted((content_dir / "chapters").glob("*.json"))
    controlled_chapter_paths = sorted((controlled_dir / "chapters").glob("*.json"))
    if len(content_chapter_paths) != 3 or len(controlled_chapter_paths) != 3:
        raise ValueError("Metamorphosis must retain exactly three private chapters")
    for content_path, controlled_path in zip(content_chapter_paths, controlled_chapter_paths):
        if str(read_json(content_path).get("content") or "") != str(
            read_json(controlled_path).get("content") or ""
        ):
            raise ValueError(f"Canonical and controlled chapter diverged: {content_path.name}")

    source.update(
        {
            "translator_name": TRANSLATOR,
            "source_url": SOURCE_URL,
            "source_license": "COPYRIGHTED_TRANSLATION_PERMISSION_REQUIRED",
            "rights_basis": (
                "Franz Kafka's 1915 German original is public domain, but Project Gutenberg "
                "ebook 5200 labels the imported David Wyllie English translation copyrighted. "
                "Commercial redistribution permission for Earnalism is not established."
            ),
            "commercial_use_allowed": False,
            "rights_tier": "C",
            "verification_status": "blocked",
            "qa_status": "RIGHTS_REVIEW_REQUIRED",
            "verified_at": "",
            "rights_reassessment": {
                "status": RIGHTS_DECISION,
                "reassessed_at": effective_at,
                "author_original_public_domain": True,
                "translation_is_separate_right": True,
                "translator": TRANSLATOR,
                "official_source_marks_copyrighted": True,
                "commercial_permission_verified": False,
                "evidence_urls": [
                    SOURCE_URL,
                    "https://www.gutenberg.org/files/5200/5200-h/5200-h.htm",
                ],
                "reader_exposure_allowed": False,
                "audio_generation_allowed": False,
                "legacy_estimated_sync_invalidated": True,
            },
        }
    )

    approval = copy.deepcopy(read_json(controlled_dir / "approval_evidence.json"))
    approval.update(
        {
            "approved_to_publish": False,
            "rights_tier": "C",
            "verification_status": "blocked",
            "qa_status": "RIGHTS_REVIEW_REQUIRED",
            "approval_scope": "historical_admin_import_reconstruction_invalidated",
            "reader_public_release": "READER_RELEASE_BLOCKED_RIGHTS",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "allowCheckout": False,
            "allowPayment": False,
            "audiobook_enabled": False,
            "rights_blocker": RIGHTS_DECISION,
        }
    )

    public = audio_hidden_public_book(read_json(controlled_dir / "public_book.json"))
    public.update(
        {
            "translator": TRANSLATOR,
            "rights_basis": source["rights_basis"],
            "rights_tier": "C",
            "verification_status": "blocked",
            "qa_status": "RIGHTS_REVIEW_REQUIRED",
            "approved_to_publish": False,
            "publication_status": "RIGHTS_REVIEW_REQUIRED",
            "readerStatus": "rights_review_required",
            "publicationStatus": "draft",
            "isPublic": False,
            "isLive": False,
            "showInPublicLibrary": False,
            "showInHomepage": False,
            "allowPublicReading": False,
            "allowCheckout": False,
            "allowPayment": False,
            "is_published": False,
            "updated_at": effective_at,
        }
    )

    reader = copy.deepcopy(read_json(controlled_dir / "reader_manifest.json"))
    reader.update(
        {
            "translator": TRANSLATOR,
            "reader_release_status": "BLOCKED_RIGHTS",
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generated_at": effective_at,
        }
    )
    highlight = {
        "slug": SLUG,
        "status": "INVALIDATED_RIGHTS_AND_UNMEASURED_SYNC",
        "generatedAt": effective_at,
        "source": "copyrighted_translation_rights_reassessment",
        "chapters": [],
        "totalDurationMs": 0,
        "audio_enabled": False,
        "note": (
            "The current translation is rights-blocked and the legacy timing data was "
            "deterministically estimated. Any future replacement manuscript requires fresh "
            "audio and measured synchronization."
        ),
    }

    controlled_payloads: dict[str, bytes] = {
        "approval_evidence.json": json_bytes(approval),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "source_evidence.json": json_bytes(source),
    }
    for path in controlled_chapter_paths:
        controlled_payloads[f"chapters/{path.name}"] = path.read_bytes()
    checksum = checksum_bytes(controlled_payloads, effective_at, SLUG)

    book = copy.deepcopy(read_json(content_dir / "book.json"))
    book.update(
        {
            "translator": TRANSLATOR,
            "rightsStatus": "copyrighted_translation_permission_required",
            "rightsTerritoryBasis": source["rights_basis"],
            "readerStatus": "blocked_rights",
            "publicationStatus": "draft",
            "isPublic": False,
            "isLive": False,
            "showInPublicLibrary": False,
            "showInHomepage": False,
            "allowPublicReading": False,
            "allowCheckout": False,
            "allowPayment": False,
            "is_published": False,
            "updatedAt": effective_at,
        }
    )

    history = copy.deepcopy(read_json(ROOT / "internal/earnalism_intelligence/title_decision_history.json"))
    titles = history.setdefault("titles", {})
    titles[SLUG] = {
        "latest_decision": RIGHTS_DECISION,
        "decision_reason": (
            "The imported David Wyllie English translation is explicitly marked copyrighted "
            "by its authoritative source. The original Kafka text being public domain does "
            "not establish commercial rights in this translation."
        ),
        "updated_at": effective_at,
        "language": "en",
        "territory": "IN",
        "translator": TRANSLATOR,
        "public_reader_status": "HIDDEN_RIGHTS_BLOCKED",
        "public_audio_status": "HIDDEN_NOT_APPROVED",
        "manuscript_preserved_private": True,
        "legacy_estimated_sync_invalidated": True,
        "public_release_mutated": False,
        "next_action": (
            "Bind a verified commercially reusable English translation or written permission, "
            "then rebuild the checksum-bound reader candidate and repeat both human gates."
        ),
    }

    ledger_path = ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl"
    ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()
    already_recorded = any(
        json.loads(line).get("decision") == DECISION_KEY
        and json.loads(line).get("slug_or_area") == SLUG
        for line in ledger_lines
        if line.strip()
    )
    if not already_recorded:
        ledger_lines.append(
            json.dumps(
                {
                    "timestamp": effective_at,
                    "workstream": "english_25_title_controlled_release",
                    "slug_or_area": SLUG,
                    "decision": DECISION_KEY,
                    "evidence": {
                        "translator": TRANSLATOR,
                        "official_source_marks_copyrighted": True,
                        "commercial_permission_verified": False,
                        "manuscript_content_changed": False,
                        "legacy_estimated_sync_invalidated": True,
                        "audio_enabled": False,
                    },
                    "selected_option": (
                        "Preserve the manuscript only as a private audit candidate and block "
                        "reader, synthesis, upload, and release until translation rights are proven."
                    ),
                    "customer_experience_reason": (
                        "No reader or listener should receive an edition whose translation rights "
                        "cannot be truthfully established."
                    ),
                    "release_gate_reason": (
                        "The authoritative source labels this translation copyrighted; the "
                        "repository's historical public-domain inference was invalid."
                    ),
                    "result": RIGHTS_DECISION,
                    "next_action": titles[SLUG]["next_action"],
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

    replacements: dict[Path, bytes] = {
        content_dir / "book.json": json_bytes(book),
        content_dir / "source-rights.md": rights_note(effective_at),
        ROOT / "internal/earnalism_intelligence/title_decision_history.json": json_bytes(history),
        ledger_path: ("\n".join(ledger_lines) + "\n").encode("utf-8"),
    }
    for publication_dir in (controlled_dir, backend_dir):
        for relative, payload in controlled_payloads.items():
            replacements[publication_dir / relative] = payload
        replacements[publication_dir / "checksum_manifest.json"] = checksum

    evidence = {
        "slug": SLUG,
        "reassessed_at": effective_at,
        "decision": RIGHTS_DECISION,
        "translator": TRANSLATOR,
        "official_source_marks_copyrighted": True,
        "commercial_permission_verified": False,
        "chapter_count": 3,
        "manuscript_content_changed": False,
        "root_backend_byte_parity": True,
        "legacy_estimated_sync_invalidated": True,
        "reader_exposed": False,
        "audio_enabled": False,
        "remote_media_mutated": False,
    }
    return replacements, evidence


def verify_written(replacements: dict[Path, bytes]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    for publication_dir in (CONTROLLED_ROOT / SLUG, BACKEND_ROOT / SLUG):
        manifest = read_json(publication_dir / "checksum_manifest.json")
        for row in manifest.get("files") or []:
            target = publication_dir / str(row["file"])
            if not target.is_file() or sha256_file(target) != row.get("sha256"):
                raise ValueError(f"Controlled checksum mismatch: {target}")
    for relative in CONTROLLED_FILES:
        root_path = CONTROLLED_ROOT / SLUG / relative
        backend_path = BACKEND_ROOT / SLUG / relative
        if root_path.read_bytes() != backend_path.read_bytes():
            raise ValueError(f"Root/backend mirror mismatch: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--reassessed-at")
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    reassessed_at = args.reassessed_at or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if args.write
        else "DRY_RUN"
    )
    replacements, evidence = build(reassessed_at)
    report = {
        "schema": "earnalism.copyrighted_translation_fail_closed.v1",
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
