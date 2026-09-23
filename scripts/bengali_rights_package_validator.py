#!/usr/bin/env python3
"""Fail-closed audit for title-level Bengali rights packages.

This reports evidence completeness separately from release authority. It never
publishes, edits, or expands the controlled launch allowlist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = Path("data/title_rights_evidence/bengali-bankim-cohort-1.json")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def canonical_hash(package: Path) -> tuple[str, int]:
    public_book = read_json(package / "public_book.json")
    chapters = public_book.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return "", 0
    content: list[str] = []
    seen: set[str] = set()
    ordered = sorted(
        chapters, key=lambda row: row.get("order", 0) if isinstance(row, dict) else 0
    )
    for row in ordered:
        if not isinstance(row, dict):
            return "", 0
        chapter_id = str(row.get("id") or "")
        if not chapter_id or chapter_id in seen:
            return "", 0
        seen.add(chapter_id)
        chapter = read_json(package / "chapters" / f"{chapter_id}.json")
        text = chapter.get("content")
        if not isinstance(text, str) or not text:
            return "", 0
        if chapter.get("order") != row.get("order"):
            return "", 0
        if "\ufffd" in text or "\x00" in text:
            return "", 0
        content.append(text)
    return hashlib.sha256("\n".join(content).encode("utf-8")).hexdigest(), len(content)


def package_is_held(package: Path) -> bool:
    book = read_json(package / "public_book.json")
    approval = read_json(package / "approval_evidence.json")
    flags = (
        book.get("is_published"),
        book.get("isPublic"),
        book.get("isLive"),
        book.get("allowPublicReading"),
        book.get("showInPublicLibrary"),
        book.get("approved_to_publish"),
    )
    return (
        not any(value is True for value in flags)
        and approval.get("approved_to_publish") is False
        and str(book.get("publication_status", "")).upper()
        not in {
            "LIVE_APPROVED",
            "PUBLISHED",
        }
    )


def checksum_manifest_matches(package: Path) -> bool:
    manifest = read_json(package / "checksum_manifest.json")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            return False
        relative = entry.get("file")
        expected = entry.get("sha256")
        if (
            not isinstance(relative, str)
            or not relative
            or not isinstance(expected, str)
        ):
            return False
        target = package / relative
        if relative == "checksum_manifest.json":
            continue
        if (
            not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != expected
        ):
            return False
    return True


def evaluate_title(
    root: Path, title: dict[str, Any], launch: dict[str, Any], territory: str
) -> dict[str, Any]:
    slug = str(title.get("slug") or "")
    package = root / "data/controlled_publications" / slug
    actual_hash, chapter_count = canonical_hash(package)
    source_evidence = read_json(package / "source_evidence.json")
    approval = read_json(package / "approval_evidence.json")
    backend_package = root / "backend/data/controlled_publications" / slug
    backend_package_exists = backend_package.is_dir()
    expected_hash = str(title.get("canonical_text_sha256") or "")
    source_revision = str(title.get("source_page_revision") or "")
    source_url = str(title.get("source_page_revision_url") or "")
    license_name = str(title.get("source_layer_status") or "")
    attribution = title.get("attribution_implemented") is True
    package_book = read_json(package / "public_book.json")
    cover_asset = str(title.get("cover_asset") or "")
    package_cover = str(package_book.get("cover_image_url") or "")
    cover_confirmed = bool(
        title.get("external_protected_cover_elements") is False
        and cover_asset
        and cover_asset == package_cover
    )
    text_verified = title.get("text_integrity_status") == "TEXT_VERIFIED"
    rights_allowed = bool(
        title.get("rights_status") in {"CLEAR", "LICENSED_WITH_CONDITIONS"}
        and title.get("underlying_work_status") == "INDIA_COPYRIGHT_EVIDENCE_COMPLETE"
    )
    launch_slugs = set(launch.get("live_approved_slugs") or [])

    rights_decision = read_json(package / "rights_decision.json")
    decision_hash = str(
        rights_decision.get("canonical_text_hash")
        or rights_decision.get("content_hash")
        or ""
    )
    decision_accepted = (
        str(rights_decision.get("status") or "").upper() == "ACCEPTED"
        and decision_hash == expected_hash
        and str(rights_decision.get("slug") or "") == slug
        and str(rights_decision.get("territory") or "").upper() == "IN"
    )
    checks = {
        "rights_packet_present": bool(
            slug and title.get("author") and title.get("underlying_work_status")
        ),
        "rights_status_allowed": rights_allowed,
        "canonical_hash_matches": bool(
            HEX_SHA256.fullmatch(expected_hash) and actual_hash == expected_hash
        ),
        "canonical_chapter_count_matches": chapter_count == title.get("chapter_count"),
        "source_provenance_present": bool(
            source_revision
            and source_url
            and title.get("source_edition")
            and title.get("source_provider")
            and license_name
            and source_evidence.get("source_url")
            and source_evidence.get("source_name")
            and source_evidence.get("source_license")
        ),
        "license_obligations_satisfied": (
            attribution
            if "CC_BY_SA" in license_name
            else title.get("license_obligations_not_applicable") is True
        ),
        "text_verified": text_verified,
        "cover_ready": cover_confirmed,
        "publication_manifest_present": (
            package / "publication_manifest.json"
        ).is_file(),
        "package_checksums_match": checksum_manifest_matches(package),
        "backend_mirror_held": not backend_package_exists
        or package_is_held(backend_package),
        "backend_mirror_checksums_match": not backend_package_exists
        or checksum_manifest_matches(backend_package),
        "territory_allowed": territory == "IN"
        and launch.get("launch_compliance_jurisdiction") == "IN",
        "package_held": package_is_held(package),
        "release_allowlisted": slug in launch_slugs,
        "hash_bound_release_decision_accepted": decision_accepted,
        "release_package_unheld": not package_is_held(package),
        "backend_package_present": backend_package_exists,
        "backend_package_unheld": backend_package_exists
        and not package_is_held(backend_package),
        "approval_evidence_authorizes_release": (
            approval.get("approved_to_publish") is True
            and str(approval.get("verification_status") or "").upper()
            in {"VERIFIED", "ACCEPTED"}
        ),
        "approval_evidence_not_authorizing": approval.get("approved_to_publish")
        is False,
    }
    readiness_names = {
        "rights_packet_present",
        "rights_status_allowed",
        "canonical_hash_matches",
        "canonical_chapter_count_matches",
        "source_provenance_present",
        "license_obligations_satisfied",
        "text_verified",
        "cover_ready",
        "publication_manifest_present",
        "package_checksums_match",
        "backend_mirror_held",
        "backend_mirror_checksums_match",
        "territory_allowed",
    }
    readiness_complete = all(checks[name] for name in readiness_names)
    release_allowed = bool(
        readiness_complete
        and checks["release_allowlisted"]
        and checks["hash_bound_release_decision_accepted"]
        and checks["release_package_unheld"]
        and checks["backend_package_present"]
        and checks["backend_package_unheld"]
        and checks["approval_evidence_authorizes_release"]
    )
    checks["evidence_complete_for_commercial_release"] = readiness_complete
    checks["reader_release_allowed"] = release_allowed
    readiness_blockers = [name.upper() for name in readiness_names if not checks[name]]
    release_blockers = [
        name.upper()
        for name in (
            "release_allowlisted",
            "hash_bound_release_decision_accepted",
            "release_package_unheld",
            "backend_package_present",
            "backend_package_unheld",
            "approval_evidence_authorizes_release",
        )
        if not checks[name]
    ]
    # Evidence readiness is distinct from the deliberate release decision.
    # An allowlist entry or manifest alone cannot make an incomplete title
    # ready, and a ready package remains unpublished without release authority.
    return {
        "slug": slug,
        "title_bn": title.get("title_bn"),
        "status": "READY_FOR_COMMERCIAL_RELEASE" if readiness_complete else "HOLD",
        "checks": checks,
        "blockers": readiness_blockers,
        "release_blockers": release_blockers,
        "canonical_hash": actual_hash,
        "chapter_count": chapter_count,
    }


def audit(root: Path = ROOT, packet_path: Path | None = None) -> dict[str, Any]:
    packet = read_json(root / PACKET if packet_path is None else packet_path)
    titles = packet.get("titles")
    launch = read_json(root / "backend/data/controlled_launch.json")
    if not isinstance(titles, list) or not titles:
        return {
            "status": "INVALID",
            "issues": ["Missing title-level rights packet rows."],
            "titles": [],
        }
    territory = str(packet.get("territory") or "")
    rows = [
        evaluate_title(root, row, launch, territory)
        for row in titles
        if isinstance(row, dict)
    ]
    issues: list[str] = []
    if len(rows) != len(titles):
        issues.append("Rights packet contains a malformed title row.")
    slugs = [row["slug"] for row in rows]
    if not all(slugs) or len(set(slugs)) != len(slugs):
        issues.append("Rights packet title slugs are missing or duplicated.")
    if launch.get("live_approved_slugs") != [
        "a-ghost-story",
        "the-tell-tale-heart",
        "radharani",
    ]:
        issues.append("The existing three-title India pilot allowlist changed.")
    if (
        launch.get("public_audio_exposure_enabled") is not False
        or launch.get("public_paid_commerce_enabled") is not False
    ):
        issues.append(
            "Audio or paid commerce is enabled in the current launch configuration."
        )
    if any(not row["checks"]["package_held"] for row in rows):
        issues.append(
            "A held cohort package still has public/live/approval flags enabled."
        )
    if any(row["slug"] in set(launch.get("live_approved_slugs") or []) for row in rows):
        issues.append("A cohort title entered the current pilot Reader allowlist.")
    return {
        "status": "PASS" if not issues else "FAIL",
        "meaning": "PASS means the evidence was evaluated and held titles fail closed; it does not mean a title is cleared or released.",
        "issues": issues,
        "titles": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--packet", type=Path)
    args = parser.parse_args()
    report = audit(args.root, args.packet)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
