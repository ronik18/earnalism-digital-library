"""Fail-closed canonical promotion for private, checksum-bound cover candidates."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from .book_cover import (
    canonical_cover_kind,
    content_addressed_cover_candidate_public_id,
    validate_book_cover,
)


APPROVAL_DECISION = "APPROVE_CANONICAL_COVER"
APPROVAL_EVIDENCE_FILENAME = "cover_approval_evidence.json"
REQUIRED_CONTROLLED_FILES = {
    "public_book.json",
    "reader_manifest.json",
    "approval_evidence.json",
    "source_evidence.json",
    "checksum_manifest.json",
}
HEX_SHA256 = frozenset("0123456789abcdef")

FRONT_COVER_FIELDS = (
    "cover_url",
    "cover_image_url",
    "coverImage",
    "cover_image",
    "thumbnail_url",
    "blur_placeholder",
    "dominant_color",
)
BACK_COVER_FIELDS = (
    "back_cover_url",
    "back_cover_image_url",
    "back_cover_thumbnail_url",
    "back_cover_blur_placeholder",
    "back_cover_dominant_color",
)
AUDIO_TRUTH_FIELDS = (
    "audio_enabled",
    "audiobook_enabled",
    "generate_audiobook",
    "audiobook_assets",
    "audiobook",
    "audiobook_release_gate",
    "audio_qa_status",
    "audio_url",
)


class CoverPromotionError(ValueError):
    """The promotion request or controlled state is not safe to apply."""


def json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return len(normalized) == 64 and set(normalized) <= HEX_SHA256


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverPromotionError(f"Invalid controlled JSON: {path.name}") from exc
    if not isinstance(payload, dict):
        raise CoverPromotionError(f"Controlled JSON must be an object: {path.name}")
    return payload


def controlled_publication_dirs(repo_root: Path, slug: str) -> tuple[Path, Path]:
    normalized = str(slug or "").strip().lower()
    if not normalized or "/" in normalized or normalized in {".", ".."}:
        raise CoverPromotionError("Invalid controlled publication slug.")
    directories = (
        Path(repo_root) / "data" / "controlled_publications" / normalized,
        Path(repo_root) / "backend" / "data" / "controlled_publications" / normalized,
    )
    for directory in directories:
        missing = sorted(
            filename
            for filename in REQUIRED_CONTROLLED_FILES
            if not (directory / filename).is_file()
        )
        if missing:
            raise CoverPromotionError(
                f"Controlled publication mirror is incomplete: {directory} "
                f"(missing {', '.join(missing)})"
            )
    return directories


def _relative_file_map(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and not path.name.startswith(".")
    }


def _verify_mirrors(directories: tuple[Path, Path]) -> None:
    primary, backend = directories
    if _relative_file_map(primary) != _relative_file_map(backend):
        raise CoverPromotionError("Controlled publication mirrors diverge.")


def _verify_checksum_manifest(directory: Path) -> None:
    manifest = _read_json(directory / "checksum_manifest.json")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise CoverPromotionError("checksum_manifest.json files must be an array.")
    for row in rows:
        if not isinstance(row, dict):
            raise CoverPromotionError("checksum_manifest.json contains an invalid row.")
        relative = str(row.get("file") or "").strip()
        expected = str(row.get("sha256") or "").strip().lower()
        if (
            not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or not _is_sha256(expected)
        ):
            raise CoverPromotionError("checksum_manifest.json contains an unsafe row.")
        if relative == "checksum_manifest.json":
            continue
        target = directory / relative
        if not target.is_file():
            raise CoverPromotionError(f"Checksum target is missing: {relative}")
        if sha256_bytes(target.read_bytes()) != expected:
            raise CoverPromotionError(f"Checksum mismatch: {relative}")


def validate_immutable_candidate(candidate: Mapping[str, Any]) -> dict[str, str]:
    url = str(
        candidate.get("immutable_candidate_url") or candidate.get("candidate_url") or ""
    ).strip()
    public_id = str(candidate.get("cloudinary_public_id") or "").strip().strip("/")
    version = str(candidate.get("cloudinary_version") or "").strip()
    version_id = str(candidate.get("cloudinary_version_id") or "").strip()
    image_format = str(candidate.get("cloudinary_format") or "").strip().lower()
    resource_type = str(candidate.get("cloudinary_resource_type") or "").strip().lower()
    slug = str(candidate.get("slug") or "").strip().lower()
    candidate_sha256 = str(candidate.get("sha256") or "").strip().lower()
    try:
        kind = canonical_cover_kind(str(candidate.get("kind") or ""))
    except ValueError as exc:
        raise CoverPromotionError(str(exc)) from exc
    parsed = urlparse(url)
    decoded_path = unquote(parsed.path)

    if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com":
        raise CoverPromotionError("Candidate must use an HTTPS Cloudinary delivery URL.")
    if parsed.query or parsed.fragment:
        raise CoverPromotionError("Candidate URL must not contain query or fragment data.")
    if resource_type != "image":
        raise CoverPromotionError("Candidate Cloudinary resource type must be image.")
    if not version.isdigit() or not version_id or not public_id or not image_format:
        raise CoverPromotionError("Candidate is missing immutable Cloudinary identity.")
    try:
        expected_public_id = content_addressed_cover_candidate_public_id(
            slug,
            kind,
            candidate_sha256,
        )
    except ValueError as exc:
        raise CoverPromotionError(str(exc)) from exc
    if public_id != expected_public_id:
        raise CoverPromotionError(
            "Candidate Cloudinary public ID is not title/side/content scoped."
        )
    marker = f"/image/upload/v{version}/"
    expected_suffix = f"/{public_id}.{image_format}"
    if marker not in decoded_path or not decoded_path.endswith(expected_suffix):
        raise CoverPromotionError(
            "Candidate URL does not match its immutable Cloudinary identity."
        )
    return {
        "url": url,
        "public_id": public_id,
        "version": version,
        "version_id": version_id,
        "resource_type": resource_type,
        "format": image_format,
    }


def verify_remote_candidate_bytes(
    candidate: Mapping[str, Any],
    remote_bytes: bytes,
    *,
    max_bytes: int,
) -> dict[str, Any]:
    identity = validate_immutable_candidate(candidate)
    expected_sha = str(candidate.get("sha256") or "").strip().lower()
    if not _is_sha256(expected_sha):
        raise CoverPromotionError("Candidate input SHA-256 is missing or invalid.")
    remote_sha = sha256_bytes(remote_bytes)
    if remote_sha != expected_sha:
        raise CoverPromotionError("Remote cover bytes do not match candidate input SHA-256.")
    content_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(identity["format"])
    if not content_type:
        raise CoverPromotionError("Candidate image format is not supported.")
    try:
        validation = validate_book_cover(remote_bytes, content_type, max_bytes)
    except ValueError as exc:
        raise CoverPromotionError(f"Remote cover validation failed: {exc}") from exc
    if (
        int(validation["width"]) != int(candidate.get("width") or 0)
        or int(validation["height"]) != int(candidate.get("height") or 0)
    ):
        raise CoverPromotionError("Remote cover dimensions do not match the candidate.")
    return {**validation, "identity": identity}


def _cover_snapshot(public_book: Mapping[str, Any], kind: str) -> dict[str, Any]:
    fields = FRONT_COVER_FIELDS if kind == "front" else BACK_COVER_FIELDS
    snapshot = {field: copy.deepcopy(public_book.get(field)) for field in fields}
    snapshot["cover_status"] = copy.deepcopy(public_book.get("cover_status"))
    snapshot["cover_dimensions"] = copy.deepcopy(public_book.get("cover_dimensions"))
    return snapshot


def _immutable_transformation_url(
    immutable_url: str,
    transformation: str,
) -> str:
    marker = "/image/upload/"
    if marker not in immutable_url:
        raise CoverPromotionError("Immutable Cloudinary URL is malformed.")
    return immutable_url.replace(
        marker,
        f"{marker}{transformation}/",
        1,
    )


def _audio_truth_snapshot(
    public_book: Mapping[str, Any],
    reader_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "public_book": {
            field: copy.deepcopy(public_book.get(field))
            for field in AUDIO_TRUTH_FIELDS
        },
        "reader_manifest": {
            field: copy.deepcopy(reader_manifest.get(field))
            for field in AUDIO_TRUTH_FIELDS
        },
    }


def _apply_cover_fields(
    public_book: dict[str, Any],
    candidate: Mapping[str, Any],
    kind: str,
    approved_at: str,
) -> None:
    canonical_url = str(candidate["immutable_candidate_url"])
    thumbnail = _immutable_transformation_url(
        canonical_url,
        "c_fill,h_450,q_auto:best,w_300",
    )
    blur = _immutable_transformation_url(
        canonical_url,
        "c_fill,e_blur:2000,h_30,q_30,w_20",
    )
    dominant = str(candidate.get("candidate_dominant_color") or "#1A1010")
    if kind == "front":
        public_book.update(
            {
                "cover_url": canonical_url,
                "cover_image_url": canonical_url,
                "coverImage": canonical_url,
                "cover_image": canonical_url,
                "thumbnail_url": thumbnail,
                "blur_placeholder": blur,
                "dominant_color": dominant,
                "cover_status": "CLOUDINARY_ASSIGNED",
            }
        )
    else:
        public_book.update(
            {
                "back_cover_url": canonical_url,
                "back_cover_image_url": canonical_url,
                "back_cover_thumbnail_url": thumbnail,
                "back_cover_blur_placeholder": blur,
                "back_cover_dominant_color": dominant,
            }
        )
    dimensions = copy.deepcopy(public_book.get("cover_dimensions"))
    if not isinstance(dimensions, dict):
        dimensions = {}
    dimensions[kind] = [
        int(candidate.get("width") or 0),
        int(candidate.get("height") or 0),
    ]
    public_book["cover_dimensions"] = dimensions
    public_book["updated_at"] = approved_at


def _approval_document(
    existing: Mapping[str, Any],
    *,
    slug: str,
    kind: str,
    candidate: Mapping[str, Any],
    identity: Mapping[str, str],
    previous_cover: Mapping[str, Any],
    event_id: str,
    approved_at: str,
    approved_by: str,
    approval_note: str,
    rights_basis: str,
) -> dict[str, Any]:
    document = copy.deepcopy(dict(existing))
    history = document.get("history")
    if not isinstance(history, list):
        history = []
    active = document.get("active_approvals")
    if not isinstance(active, dict):
        active = {}
    previous_event_id = str(active.get(kind) or "")
    event = {
        "event_id": event_id,
        "slug": slug,
        "kind": kind,
        "decision": APPROVAL_DECISION,
        "candidate_sha256": str(candidate["sha256"]).lower(),
        "remote_sha256": str(candidate["sha256"]).lower(),
        "cloudinary": dict(identity),
        "width": int(candidate.get("width") or 0),
        "height": int(candidate.get("height") or 0),
        "approved_at": approved_at,
        "approved_by": approved_by,
        "approval_note": approval_note,
        "rights_basis": rights_basis,
        "reader_audio_release_truth_unchanged": True,
    }
    event["event_sha256"] = sha256_bytes(json_bytes(event))
    history.append(event)
    active[kind] = event_id
    rollback_pointers = document.get("rollback_pointers")
    if not isinstance(rollback_pointers, dict):
        rollback_pointers = {}
    rollback_pointers[kind] = {
        "from_event_id": event_id,
        "to_event_id": previous_event_id or None,
        "previous_canonical_cover": copy.deepcopy(dict(previous_cover)),
    }
    return {
        "schema_version": "earnalism.cover_approval_evidence.v1",
        "slug": slug,
        "active_approvals": active,
        "rollback_pointers": rollback_pointers,
        "history": history,
        "updated_at": approved_at,
    }


def _updated_checksum_manifest(
    manifest: Mapping[str, Any],
    managed_files: Mapping[str, bytes],
    approved_at: str,
) -> dict[str, Any]:
    result = copy.deepcopy(dict(manifest))
    rows = result.get("files")
    if not isinstance(rows, list):
        raise CoverPromotionError("checksum_manifest.json files must be an array.")
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise CoverPromotionError("checksum_manifest.json contains an invalid row.")
        filename = str(row.get("file") or "").strip()
        if filename:
            indexed[filename] = {
                "file": filename,
                "sha256": str(row.get("sha256") or "").strip().lower(),
            }
    for filename, payload in managed_files.items():
        indexed[filename] = {"file": filename, "sha256": sha256_bytes(payload)}
    result["files"] = [indexed[name] for name in sorted(indexed)]
    result["generated_at"] = approved_at
    return result


@contextmanager
def _promotion_lock(repo_root: Path, slug: str):
    lock_name = sha256_bytes(f"{Path(repo_root).resolve()}:{slug}".encode())[:20]
    lock_path = Path(tempfile.gettempdir()) / f"earnalism-cover-promotion-{lock_name}.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _atomic_replace_many(changes: Mapping[Path, bytes]) -> None:
    originals: dict[Path, bytes | None] = {
        path: path.read_bytes() if path.exists() else None for path in changes
    }
    staged: dict[Path, Path] = {}
    try:
        for path, payload in changes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, raw_temp = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temp_path = Path(raw_temp)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            staged[path] = temp_path
        for path, temp_path in staged.items():
            os.replace(temp_path, path)
    except Exception as exc:
        _restore_originals(originals)
        raise CoverPromotionError(
            f"Mirrored cover promotion rolled back: {type(exc).__name__}"
        ) from None
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)


def _restore_originals(originals: Mapping[Path, bytes | None]) -> None:
    """Restore a pre-transaction snapshot, including files that did not exist."""
    for path, payload in originals.items():
        if payload is None:
            path.unlink(missing_ok=True)
            continue
        fd, raw_temp = tempfile.mkstemp(
            prefix=f".{path.name}.rollback.", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(raw_temp, path)
        finally:
            Path(raw_temp).unlink(missing_ok=True)


def promote_cover_candidate(
    *,
    repo_root: Path,
    slug: str,
    kind: str,
    candidate: Mapping[str, Any],
    remote_bytes: bytes,
    expected_candidate_sha256: str,
    approval_decision: str,
    editorial_approved: bool,
    rights_cleared: bool,
    approval_note: str,
    rights_basis: str,
    event_id: str,
    approved_at: str,
    approved_by: str,
    max_bytes: int,
) -> dict[str, Any]:
    """Promote one verified side without changing reader or audiobook release truth."""
    normalized_slug = str(slug or "").strip().lower()
    cover_kind = canonical_cover_kind(kind)
    if approval_decision != APPROVAL_DECISION:
        raise CoverPromotionError("Explicit canonical-cover approval is required.")
    if editorial_approved is not True or rights_cleared is not True:
        raise CoverPromotionError("Editorial and cover-rights approval are both required.")
    if len(str(approval_note or "").strip()) < 8:
        raise CoverPromotionError("A meaningful approval note is required.")
    if len(str(rights_basis or "").strip()) < 8:
        raise CoverPromotionError("A meaningful cover-rights basis is required.")
    if not event_id or not approved_at or not approved_by:
        raise CoverPromotionError("Approval audit identity is incomplete.")
    if str(candidate.get("slug") or "").strip().lower() != normalized_slug:
        raise CoverPromotionError("Candidate belongs to a different title.")
    if str(candidate.get("kind") or "").strip().lower() != cover_kind:
        raise CoverPromotionError("Candidate belongs to a different cover side.")
    if candidate.get("audit_status") != "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW":
        raise CoverPromotionError("Candidate is not pending canonical review.")
    stored_sha = str(candidate.get("sha256") or "").strip().lower()
    if (
        not _is_sha256(expected_candidate_sha256)
        or str(expected_candidate_sha256).strip().lower() != stored_sha
    ):
        raise CoverPromotionError("Approval is not bound to the current candidate SHA-256.")

    remote_validation = verify_remote_candidate_bytes(
        candidate, remote_bytes, max_bytes=max_bytes
    )
    identity = remote_validation["identity"]

    with _promotion_lock(repo_root, normalized_slug):
        directories = controlled_publication_dirs(repo_root, normalized_slug)
        _verify_mirrors(directories)
        for directory in directories:
            _verify_checksum_manifest(directory)
        primary = directories[0]
        public_book = _read_json(primary / "public_book.json")
        reader_manifest = _read_json(primary / "reader_manifest.json")
        if str(public_book.get("slug") or "").strip().lower() != normalized_slug:
            raise CoverPromotionError("Controlled public book slug mismatch.")
        if str(reader_manifest.get("slug") or "").strip().lower() != normalized_slug:
            raise CoverPromotionError("Controlled reader manifest slug mismatch.")
        before_audio_truth = _audio_truth_snapshot(public_book, reader_manifest)
        previous_cover = _cover_snapshot(public_book, cover_kind)
        _apply_cover_fields(public_book, candidate, cover_kind, approved_at)
        if before_audio_truth != _audio_truth_snapshot(public_book, reader_manifest):
            raise CoverPromotionError("Cover promotion attempted to change audiobook truth.")

        approval_path = primary / APPROVAL_EVIDENCE_FILENAME
        existing_approval = _read_json(approval_path) if approval_path.exists() else {}
        cover_approval = _approval_document(
            existing_approval,
            slug=normalized_slug,
            kind=cover_kind,
            candidate=candidate,
            identity=identity,
            previous_cover=previous_cover,
            event_id=event_id,
            approved_at=approved_at,
            approved_by=approved_by,
            approval_note=str(approval_note).strip(),
            rights_basis=str(rights_basis).strip(),
        )
        public_bytes = json_bytes(public_book)
        approval_bytes = json_bytes(cover_approval)
        checksum = _updated_checksum_manifest(
            _read_json(primary / "checksum_manifest.json"),
            {
                "public_book.json": public_bytes,
                APPROVAL_EVIDENCE_FILENAME: approval_bytes,
            },
            approved_at,
        )
        checksum_bytes = json_bytes(checksum)
        changes: dict[Path, bytes] = {}
        for directory in directories:
            changes[directory / "public_book.json"] = public_bytes
            changes[directory / APPROVAL_EVIDENCE_FILENAME] = approval_bytes
            changes[directory / "checksum_manifest.json"] = checksum_bytes
        originals = {
            path: path.read_bytes() if path.exists() else None for path in changes
        }
        try:
            _atomic_replace_many(changes)
            _verify_mirrors(directories)
            for directory in directories:
                _verify_checksum_manifest(directory)
            verified_public = _read_json(primary / "public_book.json")
            verified_reader = _read_json(primary / "reader_manifest.json")
            if before_audio_truth != _audio_truth_snapshot(
                verified_public, verified_reader
            ):
                raise CoverPromotionError(
                    "Post-write verification detected audiobook truth mutation."
                )
        except Exception as exc:
            _restore_originals(originals)
            if isinstance(exc, CoverPromotionError):
                raise CoverPromotionError(
                    f"Mirrored cover promotion rolled back: {exc}"
                ) from None
            raise

    return {
        "slug": normalized_slug,
        "kind": cover_kind,
        "canonical_cover_url": identity["url"],
        "candidate_sha256": stored_sha,
        "remote_sha256": remote_validation["sha256"],
        "event_id": event_id,
        "approval_evidence_file": APPROVAL_EVIDENCE_FILENAME,
        "reader_audio_release_truth_unchanged": True,
    }
