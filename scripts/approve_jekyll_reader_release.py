#!/usr/bin/env python3
"""Promote the owner-approved corrected Jekyll reader while keeping audio disabled."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repair_lady_stolen_reader_preflights import (
    BACKEND_ROOT,
    CONTENT_ROOT,
    CONTROLLED_ROOT,
    ROOT,
    checksum_bytes,
    json_bytes,
    read_json,
    sha256_file,
)


SLUG = "jekyll-and-hyde"
ALIAS_SLUG = "the-strange-case-of-dr-jekyll-and-mr-hyde"
OWNER = "Ronik Basak"
APPROVED_FINGERPRINT = "36a0b3e4a640bc6f8925979358edbb8009dc5de87618337f7d4dbb38b3a41dd3"
PARENT_MANIFEST_SHA256 = "4d23a105ee667d78fb0081a4504ba6118e644c656f5f7e090ec671e6a83ad9d0"
DECISION_KEY = "approve_checksum_bound_corrected_jekyll_reader_only_release"
FINGERPRINT_BINDING = {
    "schema": "earnalism.private_reader_gate_binding.v1",
    "repository_head": "b0bd9b3a5ccb3c0adf929f59a834a482ef0f3a4d",
    "slug": SLUG,
    "voice": "bm_george",
    "controlled_manifest_sha256": PARENT_MANIFEST_SHA256,
    "source_content_hash": "9b1ab2987886368c4dae32d7fd1c12da9bccb91d74425eccda60333ddfbb5acb",
    "chapter_sha256": "6741a99c2a840b45efea63acb2a17363b72daafc7ef8ad44dc469a68a1d662f3",
    "cover_sha256": "eefa51647e7dbe342ab55c7ba1df1f7a596794ed0edfd0d628f793b7f69a7dd8",
    "preview_text_sha256": "69a45f07c86702868852fad15151add246b984c26a9b0ac145b54deb2b165043",
}
PREVIEW_SHA256 = "b3c2eec2285971ff535d8cc354dd41df7e28511256c1ba608a48de154327569a"


def canonical_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def add_once(values: list[str], value: str) -> list[str]:
    return [*dict.fromkeys([*values, value])]


def approval_receipt(approved_at: str) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": "earnalism.reader_release_approval.v1",
        "slug": SLUG,
        "owner": OWNER,
        "role": "owner_and_product_owner",
        "status": "APPROVED",
        "approved_at": approved_at,
        "statement": (
            "I approve checksum-bound reader fingerprint "
            f"{APPROVED_FINGERPRINT}. Replace the malformed live reader through PR #293; "
            "keep audiobook exposure disabled."
        ),
        "scope": "corrected_canonical_reader_only",
        "approved_reader_gate_fingerprint": APPROVED_FINGERPRINT,
        "approved_parent_manifest_sha256": PARENT_MANIFEST_SHA256,
        "binding": copy.deepcopy(FINGERPRINT_BINDING),
        "preview_sha256": PREVIEW_SHA256,
        "public_reader_authorized": True,
        "public_audiobook_authorized": False,
        "stale_alias_authorized": False,
        "audio_release_gate_waived": False,
        "content_regeneration_authorized": False,
    }
    receipt["approval_sha256"] = canonical_sha256(receipt)
    return receipt


def assert_audio_disabled(value: dict[str, Any], label: str) -> None:
    for key in ("audio_enabled", "audiobook_enabled", "generate_audiobook"):
        if value.get(key) not in (False, None):
            raise ValueError(f"{label}: {key} must remain false")
    for key in ("audio_url", "audiobook_url", "audio_asset_slug"):
        if value.get(key) not in (None, ""):
            raise ValueError(f"{label}: {key} must remain empty")


def verify_parent_or_child(controlled_dir: Path) -> str:
    manifest_path = controlled_dir / "checksum_manifest.json"
    current_sha = sha256_file(manifest_path)
    if current_sha == PARENT_MANIFEST_SHA256:
        return "parent"
    receipt_path = controlled_dir / "reader_release_approval.json"
    if not receipt_path.is_file():
        raise ValueError("Jekyll manifest is neither the approved parent nor an approved child")
    receipt = read_json(receipt_path)
    if receipt.get("approved_parent_manifest_sha256") != PARENT_MANIFEST_SHA256:
        raise ValueError("Approved child does not preserve the expected parent manifest")
    if receipt.get("approved_reader_gate_fingerprint") != APPROVED_FINGERPRINT:
        raise ValueError("Approved child fingerprint binding changed")
    return "child"


def build(requested_at: str) -> tuple[dict[Path, bytes], dict[str, Any]]:
    if canonical_sha256(FINGERPRINT_BINDING) != APPROVED_FINGERPRINT:
        raise ValueError("Approved Jekyll reader fingerprint does not recompute")

    controlled_dir = CONTROLLED_ROOT / SLUG
    backend_dir = BACKEND_ROOT / SLUG
    root_state = verify_parent_or_child(controlled_dir)
    backend_state = verify_parent_or_child(backend_dir)
    if root_state != backend_state:
        raise ValueError("Root/backend approval states diverged")
    if (controlled_dir / "checksum_manifest.json").read_bytes() != (
        backend_dir / "checksum_manifest.json"
    ).read_bytes():
        raise ValueError("Root/backend Jekyll manifests diverged")

    existing_receipt_path = controlled_dir / "reader_release_approval.json"
    approved_at = (
        str(read_json(existing_receipt_path).get("approved_at"))
        if existing_receipt_path.is_file()
        else requested_at
    )
    receipt = approval_receipt(approved_at)

    chapter_payloads: dict[str, bytes] = {}
    for index in range(1, 11):
        relative = f"chapters/chapter-{index:03d}.json"
        root_payload = (controlled_dir / relative).read_bytes()
        backend_payload = (backend_dir / relative).read_bytes()
        if root_payload != backend_payload:
            raise ValueError(f"Jekyll mirror differs: {relative}")
        chapter_payloads[relative] = root_payload

    source = copy.deepcopy(read_json(controlled_dir / "source_evidence.json"))
    if source.get("content_hash") != FINGERPRINT_BINDING["source_content_hash"]:
        raise ValueError("Jekyll source content hash changed after owner approval")
    source.update(
        {
            "qa_status": "QA_PASSED",
            "verification_status": "approved",
            "reader_release_status": "READER_ONLY_LIVE_APPROVED",
            "reader_release_approved_at": approved_at,
            "reader_release_approval_sha256": receipt["approval_sha256"],
            "audio_enabled": False,
            "audiobook_enabled": False,
        }
    )

    approval = copy.deepcopy(read_json(controlled_dir / "approval_evidence.json"))
    approval.update(
        {
            "approved_to_publish": True,
            "verification_status": "approved",
            "qa_status": "QA_PASSED",
            "approval_scope": "checksum_bound_corrected_reader_approval",
            "historical_approval_superseded": True,
            "reader_public_release": "READER_ONLY_LIVE_APPROVED",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
            "controlled_reader_release_approval": {
                "status": "APPROVED",
                "approved_by": OWNER,
                "approved_at": approved_at,
                "reader_gate_fingerprint": APPROVED_FINGERPRINT,
                "parent_manifest_sha256": PARENT_MANIFEST_SHA256,
                "approval_sha256": receipt["approval_sha256"],
                "scope": "Corrected canonical reader only; audiobook and stale alias remain disabled.",
            },
        }
    )

    cover = copy.deepcopy(read_json(controlled_dir / "cover_approval_evidence.json"))
    highlight = copy.deepcopy(read_json(controlled_dir / "highlight_sync.json"))
    highlight.update({"audio_enabled": False, "totalDurationMs": 0})

    public = copy.deepcopy(read_json(controlled_dir / "public_book.json"))
    public.update(
        {
            "qa_status": "QA_PASSED",
            "approved_to_publish": True,
            "publication_status": "LIVE_APPROVED",
            "readerStatus": "reader_ready",
            "publicationStatus": "live",
            "isPublic": True,
            "isLive": True,
            "showInPublicLibrary": True,
            "showInHomepage": False,
            "allowPublicReading": True,
            "allowCheckout": False,
            "allowPayment": False,
            "is_published": True,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generate_audiobook": False,
            "audiobook_provider": "",
            "audiobook_voice": "",
            "audio_asset_slug": "",
            "updated_at": approved_at,
        }
    )
    for key in ("audio_url", "audiobook_url", "audiobook", "audiobook_assets"):
        public.pop(key, None)
    assert_audio_disabled(public, "public_book")

    reader = copy.deepcopy(read_json(controlled_dir / "reader_manifest.json"))
    reader.update(
        {
            "reader_release_status": "READER_ONLY_LIVE_APPROVED",
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generated_at": approved_at,
        }
    )

    payloads: dict[str, bytes] = {
        "approval_evidence.json": json_bytes(approval),
        "cover_approval_evidence.json": json_bytes(cover),
        "highlight_sync.json": json_bytes(highlight),
        "public_book.json": json_bytes(public),
        "reader_manifest.json": json_bytes(reader),
        "reader_release_approval.json": json_bytes(receipt),
        "source_evidence.json": json_bytes(source),
        **chapter_payloads,
    }
    checksum = checksum_bytes(payloads, approved_at, SLUG)
    replacements: dict[Path, bytes] = {}
    for package_dir in (controlled_dir, backend_dir):
        for relative, payload in payloads.items():
            replacements[package_dir / relative] = payload
        replacements[package_dir / "checksum_manifest.json"] = checksum

    content_book_path = CONTENT_ROOT / SLUG / "book.json"
    content_book = copy.deepcopy(read_json(content_book_path))
    content_book.update(
        {
            "readerStatus": "reader_ready",
            "publicationStatus": "live",
            "isPublic": True,
            "isLive": True,
            "showInPublicLibrary": True,
            "showInHomepage": False,
            "allowPublicReading": True,
            "allowCheckout": False,
            "allowPayment": False,
            "is_published": True,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generate_audiobook": False,
            "audiobook_provider": "",
            "audiobook_voice": "",
            "audio_asset_slug": "",
            "updatedAt": approved_at,
        }
    )
    for key in ("audio_url", "audiobook_url", "audiobook", "audiobook_assets"):
        content_book.pop(key, None)
    assert_audio_disabled(content_book, "content book")
    replacements[content_book_path] = json_bytes(content_book)

    for launch_path in (
        ROOT / "data/controlled_launch.json",
        ROOT / "backend/data/controlled_launch.json",
    ):
        launch = copy.deepcopy(read_json(launch_path))
        launch["live_approved_slugs"] = add_once(
            [
                slug
                for slug in launch.get("live_approved_slugs", [])
                if slug not in (SLUG, ALIAS_SLUG)
            ],
            SLUG,
        )
        launch["audio_enabled_slugs"] = [
            slug
            for slug in launch.get("audio_enabled_slugs", [])
            if slug not in (SLUG, ALIAS_SLUG)
        ]
        replacements[launch_path] = json_bytes(launch)

    promotion_path = ROOT / "content/books/batch-1-promotion-report.json"
    promotion = copy.deepcopy(read_json(promotion_path))
    promotion["promotedLiveSlugs"] = add_once(
        [slug for slug in promotion.get("promotedLiveSlugs", []) if slug != SLUG], SLUG
    )
    promotion["heldSlugs"] = [
        slug for slug in promotion.get("heldSlugs", []) if slug != SLUG
    ]
    promotion["approvedReleaseAllowlist"] = add_once(
        [slug for slug in promotion.get("approvedReleaseAllowlist", []) if slug != SLUG],
        SLUG,
    )
    for row in promotion.get("books", []):
        if row.get("slug") == SLUG:
            row.update(
                {
                    "chapterCount": 10,
                    "wordCountApprox": 25609,
                    "routeStatus": "READY",
                    "blockers": [],
                    "decision": "PROMOTED_LIVE_READER_ONLY",
                }
            )
            break
    else:
        raise ValueError("Jekyll promotion row is missing")
    replacements[promotion_path] = json_bytes(promotion)

    history_path = ROOT / "internal/earnalism_intelligence/title_decision_history.json"
    history = copy.deepcopy(read_json(history_path))
    row = history.setdefault("titles", {}).setdefault(SLUG, {})
    row.update(
        {
            "latest_decision": "READER_ONLY_LIVE_APPROVED_PENDING_MERGE_DEPLOY",
            "decision_reason": (
                "Owner approved the checksum-bound corrected ten-chapter reader; audio and the "
                "stale alias remain disabled."
            ),
            "updated_at": approved_at,
            "reader_chapter_count": 10,
            "reader_gate_fingerprint": APPROVED_FINGERPRINT,
            "reader_release_approval_sha256": receipt["approval_sha256"],
            "public_reader_status": "READER_ONLY_LIVE_APPROVED_PENDING_MERGE_DEPLOY",
            "public_audio_status": "HIDDEN_NOT_APPROVED",
            "duplicate_slug_status": "INERT_ALIAS",
            "remote_media_mutated": False,
            "next_action": "Merge PR #293, deploy merged main, and verify the production reader while audio stays disabled.",
        }
    )
    replacements[history_path] = json_bytes(history)

    ledger_path = ROOT / "internal/earnalism_intelligence/decision_ledger.jsonl"
    ledger_lines = [
        line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    ledger = [json.loads(line) for line in ledger_lines]
    if not any(
        row.get("slug_or_area") == SLUG and row.get("decision") == DECISION_KEY
        for row in ledger
    ):
        ledger_lines.append(
            json.dumps(
                {
                    "timestamp": approved_at,
                    "workstream": "english_25_title_controlled_release",
                    "slug_or_area": SLUG,
                    "decision": DECISION_KEY,
                    "evidence": {
                        "reader_gate_fingerprint": APPROVED_FINGERPRINT,
                        "approved_parent_manifest_sha256": PARENT_MANIFEST_SHA256,
                        "preview_sha256": PREVIEW_SHA256,
                        "chapter_count": 10,
                        "audio_enabled": False,
                        "stale_alias_inert": True,
                    },
                    "selected_option": "Promote only the corrected canonical reader through PR #293.",
                    "customer_experience_reason": "Readers receive the source-correct ten-chapter edition.",
                    "release_gate_reason": "Fresh owner approval is bound to the repaired parent manifest.",
                    "result": "READER_ONLY_LIVE_APPROVED_PENDING_MERGE_DEPLOY",
                    "next_action": "Merge PR #293 and verify reader-only production truth.",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    replacements[ledger_path] = ("\n".join(ledger_lines) + "\n").encode("utf-8")

    evidence = {
        "slug": SLUG,
        "approved_at": approved_at,
        "reader_gate_fingerprint": APPROVED_FINGERPRINT,
        "approved_parent_manifest_sha256": PARENT_MANIFEST_SHA256,
        "reader_release_approval_sha256": receipt["approval_sha256"],
        "chapter_count": 10,
        "reader_release_status": "READER_ONLY_LIVE_APPROVED",
        "audio_enabled": False,
        "stale_alias_inert": True,
        "source_state": root_state,
    }
    return replacements, evidence


def verify_written(replacements: dict[Path, bytes]) -> None:
    for path, expected in replacements.items():
        if path.read_bytes() != expected:
            raise ValueError(f"Written artifact differs from plan: {path}")
    for package_dir in (CONTROLLED_ROOT / SLUG, BACKEND_ROOT / SLUG):
        manifest = read_json(package_dir / "checksum_manifest.json")
        if len(manifest.get("files") or []) != 17:
            raise ValueError("Approved Jekyll package must contain 17 controlled checksums")
        for row in manifest["files"]:
            target = package_dir / str(row["file"])
            if not target.is_file() or sha256_file(target) != row.get("sha256"):
                raise ValueError(f"Controlled checksum mismatch: {target}")
    root = CONTROLLED_ROOT / SLUG
    backend = BACKEND_ROOT / SLUG
    if (root / "checksum_manifest.json").read_bytes() != (
        backend / "checksum_manifest.json"
    ).read_bytes():
        raise ValueError("Approved Jekyll checksum mirrors diverged")
    for row in read_json(root / "checksum_manifest.json")["files"]:
        relative = str(row["file"])
        if (root / relative).read_bytes() != (backend / relative).read_bytes():
            raise ValueError(f"Approved Jekyll mirror mismatch: {relative}")
    alias = read_json(CONTROLLED_ROOT / ALIAS_SLUG / "public_book.json")
    if alias.get("isPublic") or alias.get("isLive") or alias.get("chapters"):
        raise ValueError("Stale Jekyll alias is no longer inert")
    assert_audio_disabled(read_json(root / "public_book.json"), "written public book")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--approved-at")
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    approved_at = args.approved_at or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if args.write
        else "DRY_RUN"
    )
    replacements, evidence = build(approved_at)
    report = {
        "schema": "earnalism.jekyll_reader_release_approval.v1",
        "mode": "write" if args.write else "dry-run",
        "title": evidence,
        "changed_files": sorted(
            str(path.relative_to(ROOT))
            for path, payload in replacements.items()
            if not path.exists() or path.read_bytes() != payload
        ),
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
