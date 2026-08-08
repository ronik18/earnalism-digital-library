"""Canonical, lane-separated publication manifest for Earnalism books.

The manifest collapses repeated release decisions into one integrity-protected
artifact. Reader and audio publication are deliberately independent: a book
can be ready for reading while audio remains NOT_REQUESTED or in production.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

try:
    from rights_engine import evaluate_rights
except ImportError:  # pragma: no cover
    from backend.rights_engine import evaluate_rights


SCHEMA_NAME = "earnalism-publication-manifest"
SCHEMA_VERSION = 1
READER_READY = "READY_FOR_APPROVAL"
READER_APPROVED = "APPROVED"
AUDIO_NOT_REQUESTED = "NOT_REQUESTED"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
UNSAFE_READER_HTML_RE = re.compile(r"<(?:script|iframe|object|embed)\b", re.IGNORECASE)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("manifest_sha256", None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _rights_book(public_book: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    rights = {
        "work_title": public_book.get("title", ""),
        "work_slug": public_book.get("slug", ""),
        "author_name": public_book.get("author", ""),
        "author_death_year": source.get("author_death_year"),
        "original_publication_year": source.get("original_publication_year"),
        "country_of_origin": source.get("country_of_origin", ""),
        "source_url": source.get("source_url", ""),
        "source_name": source.get("source_name", ""),
        "source_license": source.get("source_license", ""),
        "rights_tier": source.get("rights_tier", public_book.get("rights_tier", "")),
        "verification_status": source.get("verification_status", public_book.get("verification_status", "")),
        "publication_region": source.get("publication_region", "global"),
        "verified_at": source.get("verified_at", ""),
        "blocked_reason": source.get("blocked_reason", ""),
        "source_type": source.get("source_type", ""),
        "copyright_owner": source.get("copyright_owner", ""),
        "commercial_use_allowed": source.get("commercial_use_allowed") is True,
        "owner_attestation": source.get("owner_attestation", ""),
        "rights_basis": source.get("rights_basis", ""),
    }
    return {**public_book, "rights_metadata": rights}


def build_manifest(
    artifact_dir: Path,
    *,
    publish_approved: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    public_path = artifact_dir / "public_book.json"
    reader_path = artifact_dir / "reader_manifest.json"
    source_path = artifact_dir / "source_evidence.json"
    approval_path = artifact_dir / "approval_evidence.json"
    inputs = {
        "public_book": public_path,
        "reader_manifest": reader_path,
        "source_evidence": source_path,
        "approval_evidence": approval_path,
    }
    public_book = _read_json(public_path)
    reader = _read_json(reader_path)
    source = _read_json(source_path)
    approval = _read_json(approval_path)
    slug = str(public_book.get("slug") or source.get("slug") or artifact_dir.name).strip().lower()
    blockers: list[str] = []

    for label, path in inputs.items():
        if not path.exists():
            blockers.append(f"Missing {label} artifact.")

    cover_url = str(public_book.get("cover_image_url") or public_book.get("cover_url") or "").strip()
    if not cover_url:
        blockers.append("Front cover is required.")

    source_hashes = {
        key: str(source.get(key) or public_book.get(key) or "").strip().lower()
        for key in ("source_hash", "content_hash", "provenance_hash")
    }
    for key, value in source_hashes.items():
        if not SHA256_RE.fullmatch(value):
            blockers.append(f"{key} must be a SHA-256 digest.")
    if source.get("reader_facing_boilerplate_removed") is not True:
        blockers.append("Reader-facing source boilerplate removal is not verified.")

    chapters = sorted(public_book.get("chapters") or [], key=lambda item: int(item.get("order") or 0))
    chapter_ids = [str(item.get("id") or "").strip() for item in chapters]
    orders = [int(item.get("order") or 0) for item in chapters]
    if not chapters:
        blockers.append("At least one chapter is required.")
    if len(set(chapter_ids)) != len(chapter_ids) or any(not item for item in chapter_ids):
        blockers.append("Chapter ids must be present and unique.")
    if orders != list(range(1, len(chapters) + 1)):
        blockers.append("Chapter ordering must be contiguous and one-based.")
    if int(reader.get("chapter_count") or 0) != len(chapters):
        blockers.append("Reader manifest chapter count does not match the public book.")

    chapter_index: list[dict[str, Any]] = []
    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "").strip()
        if chapter.get("processing_status") != "ready":
            blockers.append(f"Chapter {chapter_id or 'unknown'} is not ready.")
        chapter_path = artifact_dir / "chapters" / f"{chapter_id}.json"
        payload = _read_json(chapter_path)
        content = str(payload.get("content") or "")
        if not content.strip():
            blockers.append(f"Chapter {chapter_id or 'unknown'} has no reader content.")
        if UNSAFE_READER_HTML_RE.search(content):
            blockers.append(f"Chapter {chapter_id or 'unknown'} contains unsafe embedded markup.")
        chapter_index.append({
            "id": chapter_id,
            "order": int(chapter.get("order") or 0),
            "title": str(chapter.get("title") or "").strip(),
            "word_count": int(chapter.get("word_count") or 0),
            "sha256": file_sha256(chapter_path) if chapter_path.exists() else "",
        })

    rights_decision = evaluate_rights(_rights_book(public_book, source))
    blockers.extend(f"Rights: {issue}" for issue in rights_decision.issues)
    reader_qa = str(public_book.get("qa_status") or approval.get("qa_status") or "").strip().upper()
    if reader_qa not in {"QA_PASSED", "PASS", "PASSED", "APPROVED"}:
        blockers.append("Reader QA must pass.")

    audio_requested = bool(
        public_book.get("audio_enabled")
        or public_book.get("audiobook_enabled")
        or public_book.get("generate_audiobook")
        or public_book.get("audiobook_assets")
    )
    audio_status = "IN_PROGRESS" if audio_requested else AUDIO_NOT_REQUESTED

    approval_present = approval.get("approved_to_publish") is True
    reader_status = "BLOCKED" if blockers else READER_READY
    reader_exposed = False
    if publish_approved and not blockers and approval_present:
        reader_status = READER_APPROVED
        reader_exposed = True
    elif publish_approved and not approval_present:
        blockers.append("Explicit reader publication approval evidence is required.")
        reader_status = "BLOCKED"

    artifact_hashes = {
        label: file_sha256(path)
        for label, path in inputs.items()
        if path.exists()
    }
    index_hash = hashlib.sha256(
        json.dumps(chapter_index, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    manifest: dict[str, Any] = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "title": str(public_book.get("title") or "").strip(),
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "content": {
            **source_hashes,
            "sanitized": source.get("reader_facing_boilerplate_removed") is True,
            "chapter_count": len(chapters),
            "chapter_index_sha256": index_hash,
            "chapters": chapter_index,
        },
        "rights": {
            "status": rights_decision.status.upper(),
            "tier": rights_decision.rights_tier,
            "publication_region": rights_decision.publication_region,
            "evidence_sha256": artifact_hashes.get("source_evidence", ""),
        },
        "reader_release": {
            "status": reader_status,
            "exposed": reader_exposed,
            "qa_status": reader_qa,
            "cover_url": cover_url,
            "blockers": blockers,
        },
        "audio_release": {
            "status": audio_status,
            "exposed": False,
            "required_for_reader_release": False,
        },
        "commerce_release": {
            "status": "NOT_REQUESTED",
            "required_for_reader_release": False,
        },
        "artifacts": artifact_hashes,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def validate_manifest(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return ["publication manifest must be an object"]
    issues: list[str] = []
    if manifest.get("schema_name") != SCHEMA_NAME:
        issues.append("publication manifest schema_name is invalid")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"publication manifest schema_version must be {SCHEMA_VERSION}")
    expected = str(manifest.get("manifest_sha256") or "")
    if not SHA256_RE.fullmatch(expected) or expected != canonical_sha256(manifest):
        issues.append("publication manifest checksum is invalid")
    for section in ("content", "rights", "reader_release", "audio_release", "commerce_release", "artifacts"):
        if not isinstance(manifest.get(section), dict):
            issues.append(f"publication manifest {section} must be an object")
    reader = manifest.get("reader_release") if isinstance(manifest.get("reader_release"), dict) else {}
    audio = manifest.get("audio_release") if isinstance(manifest.get("audio_release"), dict) else {}
    if reader.get("exposed") is True and reader.get("status") != READER_APPROVED:
        issues.append("reader exposure requires an APPROVED reader release")
    if audio.get("status") == AUDIO_NOT_REQUESTED and audio.get("exposed") is True:
        issues.append("audio cannot be exposed when it is NOT_REQUESTED")
    if audio.get("required_for_reader_release") is not False:
        issues.append("audio must remain independent from reader release")
    return issues


def manifest_reader_exposed(manifest: Any) -> bool:
    if validate_manifest(manifest):
        return False
    reader = manifest.get("reader_release") or {}
    return reader.get("status") == READER_APPROVED and reader.get("exposed") is True
