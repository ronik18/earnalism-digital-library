#!/usr/bin/env python3
"""Fail-closed manager for package-v2 audiobook release pointers.

The tool binds an eligible first package, stages already-finalized immutable
packages, moves only the approved 0/5/25/100 rollout states, deactivates or
reactivates explicitly, and rolls back by pointer. It never uploads audio,
changes audiobook approval flags, or accepts private-QA-only storage receipts.
All controlled-publication mutations are mirrored and checksum-bound.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audiobook_packages import (  # noqa: E402
    ROLLOUT_PERCENTAGES,
    AudiobookPackageValidationError,
    AudiobookReleaseSelectionError,
    build_active_release_state,
    canonical_json_bytes,
    validate_active_release_state,
    validate_audiobook_package,
)


SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
RECEIPT_SCHEMA = "audiobook_package_storage_receipt.v1"
EVIDENCE_SCHEMA = "audiobook_package_release_evidence.v1"
LEGACY_IDENTITY_SCHEMA = "audiobook_legacy_release_identity.v1"
HIDDEN_IDENTITY_SCHEMA = "audiobook_hidden_release_identity.v1"
HIDDEN_BEFORE_PROOF_SCHEMA = "audiobook_hidden_before_proof.v1"
NEW_TITLE_CANARY_SCHEMA = "audiobook_new_title_package_canary.v1"
NEW_TITLE_CANARY_APPROVAL_ENV = (
    "EARNALISM_APPROVE_NEW_TITLE_AUDIOBOOK_PACKAGE_CANARY"
)
QA_CANDIDATE_DOWNSTREAM_GATES = [
    "PRIVATE_B2_PRIMARY_UPLOAD_REQUIRED",
    "PRIVATE_B2_DR_REPLICA_REQUIRED",
    "CONTROLLED_RELEASE_ACTIVATION_REQUIRED",
    "PRODUCTION_ENDPOINT_AND_BROWSER_PROOF_REQUIRED",
]
QA_CANDIDATE_ENGLISH_LISTENING_POLICY = (
    "platform_audiobook_acceptance_v4_89"
)
QA_CANDIDATE_BENGALI_LISTENING_POLICY = (
    "bengali_audiobook_acceptance_v2_92"
)
QA_CANDIDATE_ENGLISH_LISTENING_MINIMUMS = {
    "naturalness_score": 8.9,
    "pronunciation_score": 8.9,
    "emotional_expression_score": 8.9,
    "punctuation_pause_score": 8.9,
    "pacing_score": 8.9,
    "continuity_score": 8.9,
    "anti_robotic_texture_score": 8.9,
    "anti_choppy_join_score": 8.9,
    "listener_enjoyment_score": 8.9,
    "overall_listening_score": 8.9,
    "confidence_score": 0.9,
}
QA_CANDIDATE_BENGALI_LISTENING_MINIMUMS = {
    "naturalness_score": 9.2,
    "pronunciation_score": 9.2,
    "emotional_expression_score": 9.2,
    "punctuation_pause_score": 9.2,
    "pacing_score": 9.2,
    "continuity_score": 9.2,
    "anti_robotic_texture_score": 9.2,
    "anti_choppy_join_score": 9.2,
    "listener_enjoyment_score": 9.2,
    "overall_listening_score": 9.2,
    "confidence_score": 0.9,
}
QA_CANDIDATE_LANGUAGE_ALIASES = {
    "en": "english",
    "eng": "english",
    "english": "english",
    "bn": "bengali",
    "ben": "bengali",
    "bengali": "bengali",
    "bangla": "bengali",
}
RELEASE_STORE_ROLES = {"primary": "prod", "replica": "dr"}
CHECKSUM_VERIFIED_UPLOAD_STATUSES = frozenset(
    {
        "UPLOADED_CHECKSUM_VERIFIED",
        "UPLOADED_CHECKSUM_VERIFIED_PRIVATE_ORIGIN",
    }
)
CANONICAL_AUDIO_PROXY_HOSTS = frozenset({"api.theearnalism.com"})
MIRROR_RELATIVE_ROOTS = (
    Path("backend/data/controlled_publications"),
    Path("data/controlled_publications"),
)
MANAGED_FIELDS = (
    "audiobook_packages",
    "audiobook_package_release_evidence",
    "audiobook_active_release",
    "audiobook_manuscript_sha256",
    "audiobook_release_descriptor_sha256",
    "audiobook_legacy_release_descriptor_sha256",
    "audiobook_hidden_release_descriptor_sha256",
    "audiobook_package_canary",
)


class ReleasePointerError(RuntimeError):
    """A safe, expected release-control failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleasePointerError(f"Cannot read valid JSON from {path}: {type(exc).__name__}") from None
    if not isinstance(value, dict):
        raise ReleasePointerError(f"Expected a JSON object: {path}")
    return value


def json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_sha256(value: Any, label: str) -> str:
    candidate = str(value or "").strip().lower()
    if not SHA256_RE.fullmatch(candidate):
        raise ReleasePointerError(f"{label} must be a lowercase SHA-256")
    return candidate


def publication_dirs(repo_root: Path, slug: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", slug):
        raise ReleasePointerError("slug is not canonical")
    roots = tuple((repo_root / relative / slug).resolve() for relative in MIRROR_RELATIVE_ROOTS)
    if any(not path.is_dir() for path in roots):
        raise ReleasePointerError("Both controlled-publication mirrors must exist")
    return roots  # type: ignore[return-value]


def _mirrored_json(publications: Sequence[Path], filename: str) -> dict[str, Any]:
    paths = [publication / filename for publication in publications]
    if any(not path.is_file() for path in paths):
        raise ReleasePointerError(f"Mirrored file is missing: {filename}")
    payloads = [path.read_bytes() for path in paths]
    if payloads[0] != payloads[1]:
        raise ReleasePointerError(f"Controlled-publication mirrors diverge: {filename}")
    return read_json(paths[0])


def load_mirrored_publication(repo_root: Path, slug: str) -> dict[str, Any]:
    publications = publication_dirs(repo_root, slug)
    return {
        "dirs": publications,
        "public_book": _mirrored_json(publications, "public_book.json"),
        "reader_manifest": _mirrored_json(publications, "reader_manifest.json"),
        "source_evidence": _mirrored_json(publications, "source_evidence.json"),
        "approval_evidence": _mirrored_json(publications, "approval_evidence.json"),
        "checksum_manifest": _mirrored_json(publications, "checksum_manifest.json"),
    }


def publication_fingerprint(context: Mapping[str, Any]) -> str:
    """Hash the exact semantic state used while planning a mutation."""

    payload = {
        key: context[key]
        for key in (
            "public_book",
            "reader_manifest",
            "source_evidence",
            "approval_evidence",
            "checksum_manifest",
        )
    }
    return sha256_bytes(json_bytes(payload))


def _verify_controlled_checksums(context: Mapping[str, Any]) -> None:
    rows = context["checksum_manifest"].get("files")
    if not isinstance(rows, list):
        raise ReleasePointerError("checksum_manifest.json files must be an array")
    indexed = {
        str(row.get("file") or ""): row
        for row in rows
        if isinstance(row, Mapping)
    }
    first_publication = context["dirs"][0]
    for filename in (
        "public_book.json",
        "reader_manifest.json",
        "source_evidence.json",
        "approval_evidence.json",
    ):
        row = indexed.get(filename)
        if not row or row.get("sha256") != sha256_file(first_publication / filename):
            raise ReleasePointerError(
                f"Controlled publication checksum is stale or missing: {filename}"
            )


def _legacy_audio_sha256(
    public_book: Mapping[str, Any],
    approval_evidence: Mapping[str, Any],
) -> str:
    audiobook = (
        public_book.get("audiobook")
        if isinstance(public_book.get("audiobook"), Mapping)
        else {}
    )
    audiobook_hashes = (
        audiobook.get("asset_sha256")
        if isinstance(audiobook.get("asset_sha256"), Mapping)
        else {}
    )
    approval_hashes = (
        approval_evidence.get("uploaded_artifact_sha256")
        if isinstance(approval_evidence.get("uploaded_artifact_sha256"), Mapping)
        else {}
    )
    candidates = [
        approval_evidence.get("audio_sha256"),
        approval_hashes.get("mp3"),
        audiobook.get("audio_sha256"),
        audiobook_hashes.get("mp3"),
    ]
    normalized = {
        str(value or "").strip().lower()
        for value in candidates
        if str(value or "").strip()
    }
    if not normalized or any(not SHA256_RE.fullmatch(value) for value in normalized):
        raise ReleasePointerError("Approved legacy audio lacks an exact controlled MP3 SHA-256")
    if len(normalized) != 1:
        raise ReleasePointerError("Approved legacy audio SHA-256 evidence conflicts")
    return next(iter(normalized))


def _is_canonical_reader_audio_proxy(endpoint_url: str, slug: str) -> bool:
    parsed = urlsplit(endpoint_url)
    return bool(
        parsed.scheme == "https"
        and parsed.hostname in CANONICAL_AUDIO_PROXY_HOSTS
        and parsed.port is None
        and not parsed.username
        and not parsed.password
        and parsed.path == f"/api/reader/book/{slug}/audiobook"
        and not parsed.query
        and not parsed.fragment
    )


def derive_legacy_release_identity(context: Mapping[str, Any], slug: str) -> dict[str, Any]:
    public_book = context["public_book"]
    approval = context["approval_evidence"]
    if public_book.get("slug") != slug or approval.get("slug") != slug:
        raise ReleasePointerError("Controlled legacy identity slug mismatch")
    if (
        public_book.get("audio_enabled") is not True
        or public_book.get("audiobook_enabled") is not True
        or public_book.get("approved_to_publish") is not True
        or str(public_book.get("verification_status") or "").lower() != "approved"
        or public_book.get("qa_status") != "QA_PASSED"
        or public_book.get("isPublic") is not True
        or public_book.get("isLive") is not True
        or approval.get("audiobook_enabled") is not True
        or approval.get("approved_to_publish") is not True
        or str(approval.get("verification_status") or "").lower() != "approved"
        or approval.get("qa_status") != "QA_PASSED"
        or approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_APPROVED"
    ):
        raise ReleasePointerError(
            "Legacy audio is not already approved, QA-passed, and public-release approved"
        )
    if approval.get("audio_qa_status") not in {None, "", "QA_PASSED"}:
        raise ReleasePointerError("Legacy audio QA evidence conflicts")
    if approval.get("upload_status") not in CHECKSUM_VERIFIED_UPLOAD_STATUSES:
        raise ReleasePointerError("Legacy audio lacks checksum-verified upload evidence")

    source_sha256 = require_sha256(
        approval.get("source_sha256"),
        "approved legacy source SHA-256",
    )
    audio_sha256 = _legacy_audio_sha256(public_book, approval)
    assets = public_book.get("audiobook_assets")
    audiobook = public_book.get("audiobook")
    if not isinstance(assets, Mapping) or not isinstance(audiobook, Mapping):
        raise ReleasePointerError("Approved legacy audio asset identity is incomplete")
    required_assets = ("mp3", "timestamps", "vtt", "chapters", "meta")
    normalized_assets: dict[str, str] = {}
    for asset_name in required_assets:
        asset_url = str(assets.get(asset_name) or "").strip()
        if not asset_url.startswith("https://"):
            raise ReleasePointerError(
                f"Approved legacy {asset_name} asset URL is missing or non-HTTPS"
            )
        normalized_assets[asset_name] = asset_url
    if audiobook.get("url") != normalized_assets["mp3"]:
        raise ReleasePointerError("Approved legacy MP3 identities conflict")
    nested_assets = audiobook.get("assets")
    if not isinstance(nested_assets, Mapping) or any(
        nested_assets.get(name) != normalized_assets[name] for name in required_assets
    ):
        raise ReleasePointerError("Approved legacy sidecar identities conflict")
    endpoint_url = str(approval.get("endpoint_url") or "").strip()
    if (
        endpoint_url
        and endpoint_url != normalized_assets["mp3"]
        and not _is_canonical_reader_audio_proxy(endpoint_url, slug)
    ):
        raise ReleasePointerError("Approved endpoint and legacy MP3 identities conflict")
    try:
        size_bytes = int(audiobook.get("size"))
        duration_ms = int(audiobook.get("duration_ms"))
    except (TypeError, ValueError):
        raise ReleasePointerError("Approved legacy audio size or duration is invalid") from None
    if size_bytes <= 0 or duration_ms <= 0:
        raise ReleasePointerError("Approved legacy audio size or duration is invalid")
    approval_scope = str(approval.get("approval_scope") or "").strip()
    if not approval_scope:
        raise ReleasePointerError("Approved legacy audio lacks an approval scope")

    identity = {
        "schema_version": LEGACY_IDENTITY_SCHEMA,
        "slug": slug,
        "audio_sha256": audio_sha256,
        "source_sha256": source_sha256,
        "assets": normalized_assets,
        "size_bytes": size_bytes,
        "duration_ms": duration_ms,
        "provider": str(
            audiobook.get("provider")
            or public_book.get("audiobook_provider")
            or ""
        ),
        "model": str(
            audiobook.get("model")
            or public_book.get("audiobook_model")
            or ""
        ),
        "voice": str(
            audiobook.get("voice")
            or public_book.get("audiobook_voice")
            or ""
        ),
        "style": str(
            audiobook.get("style")
            or public_book.get("audiobook_style_profile")
            or public_book.get("audiobook_style")
            or ""
        ),
        "approval_scope": approval_scope,
        "approval_evidence_sha256": sha256_bytes(canonical_json_bytes(approval)),
    }
    return identity


def _receipt_is_private_qa(receipt: Mapping[str, Any]) -> bool:
    role = str(receipt.get("receipt_role") or "").lower()
    store = receipt.get("store") if isinstance(receipt.get("store"), Mapping) else {}
    store_role = str(store.get("role") or "").lower()
    return (
        "private_qa" in role
        or "private_qa" in store_role
        or receipt.get("release_eligible") is False
        or store.get("release_eligible") is False
    )


def _receipt_objects(receipt: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    rows = receipt.get("objects")
    if not isinstance(rows, list) or not rows:
        raise ReleasePointerError(f"{label} receipt has no verified objects")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("full_download_verified") is not True:
            raise ReleasePointerError(f"{label} receipt object {index} is not fully verified")
        normalized.append(row)
    return normalized


def _validate_release_eligible_receipt(receipt: Mapping[str, Any], role: str) -> None:
    store = receipt.get("store") if isinstance(receipt.get("store"), Mapping) else {}
    if receipt.get("receipt_schema") != RECEIPT_SCHEMA:
        raise ReleasePointerError(f"{role} receipt schema is invalid")
    if receipt.get("receipt_role") != role:
        raise ReleasePointerError(f"{role} receipt role is invalid")
    if store.get("role") != RELEASE_STORE_ROLES[role]:
        raise ReleasePointerError(
            f"{role} receipt does not use the canonical {RELEASE_STORE_ROLES[role]} store"
        )
    if (
        receipt.get("passed") is not True
        or store.get("release_eligible") is not True
        or (role == "primary" and receipt.get("release_eligible") is not True)
        or _receipt_is_private_qa(receipt)
    ):
        raise ReleasePointerError(f"{role} receipt is not production-release eligible")


def _asset_receipt_match(asset: Mapping[str, Any], row: Mapping[str, Any], storage: Mapping[str, Any]) -> bool:
    try:
        size_matches = int(row.get("size_bytes")) == int(asset.get("size_bytes"))
    except (TypeError, ValueError):
        return False
    return bool(
        row.get("key") == storage.get("key")
        and row.get("sha256") == asset.get("sha256")
        and size_matches
        and row.get("mime_type") == asset.get("mime_type")
        and row.get("version_id") == storage.get("version_id")
        and row.get("store") == storage.get("store")
        and row.get("bucket") == storage.get("bucket")
    )


def validate_release_receipts(
    package: Mapping[str, Any],
    primary_receipt: Mapping[str, Any],
    replica_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    slug = str(package.get("slug") or "")
    descriptor = require_sha256(package.get("release_descriptor_sha256"), "package release descriptor")
    for receipt, role in ((primary_receipt, "primary"), (replica_receipt, "replica")):
        _validate_release_eligible_receipt(receipt, role)
        if receipt.get("slug") != slug or receipt.get("release_descriptor_sha256") != descriptor:
            raise ReleasePointerError(f"{role} receipt is bound to another release")

    primary_rows = _receipt_objects(primary_receipt, "primary")
    replica_rows = _receipt_objects(replica_receipt, "replica")
    for track in package.get("tracks") or []:
        for chunk in track.get("chunks") or []:
            for asset_name, asset in (chunk.get("assets") or {}).items():
                storage = asset.get("storage") if isinstance(asset, Mapping) else {}
                replicas = asset.get("replicas") if isinstance(asset, Mapping) else []
                if not isinstance(storage, Mapping) or not isinstance(replicas, list) or not replicas:
                    raise ReleasePointerError(f"{asset_name} lacks primary/DR storage")
                if not any(_asset_receipt_match(asset, row, storage) for row in primary_rows):
                    raise ReleasePointerError(f"{asset_name} primary storage is not receipt-bound")
                for replica in replicas:
                    if not isinstance(replica, Mapping) or not any(
                        _asset_receipt_match(asset, row, replica) for row in replica_rows
                    ):
                        raise ReleasePointerError(f"{asset_name} DR storage is not receipt-bound")

    return {
        "schema_version": EVIDENCE_SCHEMA,
        "slug": slug,
        "release_descriptor_sha256": descriptor,
        "package_version": str(package.get("package_version") or ""),
        "primary_receipt_sha256": "",
        "replica_receipt_sha256": "",
        "receipt_roles": ["primary", "replica"],
        "release_eligible": True,
    }


def validate_release_manifest_receipts(
    package: Mapping[str, Any],
    primary_receipt: Mapping[str, Any],
    replica_receipt: Mapping[str, Any],
    *,
    release_manifest_sha256: str,
    release_manifest_size_bytes: int,
) -> dict[str, Any]:
    slug = str(package.get("slug") or "")
    descriptor = require_sha256(package.get("release_descriptor_sha256"), "package release descriptor")
    manifest_sha256 = require_sha256(release_manifest_sha256, "release manifest SHA-256")
    if not isinstance(release_manifest_size_bytes, int) or release_manifest_size_bytes <= 0:
        raise ReleasePointerError("release manifest size must be a positive integer")
    expected_key = (
        f"v1/prod/sprint1/{slug}/releases/{descriptor}/release-manifest.json"
    )
    selected_rows: dict[str, dict[str, Any]] = {}
    for receipt, role in ((primary_receipt, "primary"), (replica_receipt, "replica")):
        _validate_release_eligible_receipt(receipt, role)
        if receipt.get("slug") != slug or receipt.get("release_descriptor_sha256") != descriptor:
            raise ReleasePointerError(f"{role} release-manifest receipt is bound to another release")
        rows = _receipt_objects(receipt, f"{role} release-manifest")
        if len(rows) != 1:
            raise ReleasePointerError(
                f"{role} release-manifest receipt must contain only release.manifest"
            )
        matches = [row for row in rows if row.get("asset_id") == "release.manifest"]
        if len(matches) != 1:
            raise ReleasePointerError(
                f"{role} receipt must contain exactly one release.manifest object"
            )
        row = matches[0]
        try:
            size_matches = int(row.get("size_bytes")) == release_manifest_size_bytes
        except (TypeError, ValueError):
            size_matches = False
        if (
            row.get("key") != expected_key
            or row.get("sha256") != manifest_sha256
            or not size_matches
            or row.get("mime_type") != "application/json"
            or not row.get("version_id")
            or not row.get("store")
            or not row.get("bucket")
        ):
            raise ReleasePointerError(
                f"{role} release.manifest object does not match the finalized manifest"
            )
        selected_rows[role] = row

    primary_row = selected_rows["primary"]
    replica_row = selected_rows["replica"]
    if (
        primary_row["store"] != RELEASE_STORE_ROLES["primary"]
        or replica_row["store"] != RELEASE_STORE_ROLES["replica"]
        or primary_row["bucket"] == replica_row["bucket"]
    ):
        raise ReleasePointerError("Release-manifest production and DR objects are not independent")
    primary_store = primary_receipt["store"]
    replica_store = replica_receipt["store"]
    for field in ("role", "endpoint_host", "region", "bucket", "account_fingerprint"):
        primary_value = str(primary_store.get(field) or "")
        replica_value = str(replica_store.get(field) or "")
        if not primary_value or not replica_value or primary_value == replica_value:
            raise ReleasePointerError(
                f"Release-manifest production and DR {field} identities are not independent"
            )
    return {
        "release_manifest_sha256": manifest_sha256,
        "release_manifest_size_bytes": release_manifest_size_bytes,
        "release_manifest_key": expected_key,
        "primary_release_manifest_version_id": str(primary_row["version_id"]),
        "replica_release_manifest_version_id": str(replica_row["version_id"]),
        "primary_release_manifest_store": str(primary_row["store"]),
        "replica_release_manifest_store": str(replica_row["store"]),
    }


def _controlled_hashes(context: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for document_name in ("public_book", "source_evidence"):
        document = context[document_name]
        for key in ("source_hash", "content_hash"):
            value = str(document.get(key) or "").strip().lower().removeprefix("sha256:")
            if SHA256_RE.fullmatch(value):
                values.add(value)
    return values


def _expected_manuscript_sha256(
    context: Mapping[str, Any],
    explicit: str,
    package: Mapping[str, Any],
) -> str:
    candidates = [
        explicit,
        context["public_book"].get("audiobook_manuscript_sha256"),
        context["source_evidence"].get("manuscript_sha256"),
    ]
    canonical = [str(value or "").strip().lower().removeprefix("sha256:") for value in candidates if value]
    if not canonical:
        raise ReleasePointerError(
            "No controlled manuscript hash exists; pass --expected-manuscript-sha256"
        )
    if len(set(canonical)) != 1:
        raise ReleasePointerError("Controlled manuscript hashes disagree")
    expected = require_sha256(canonical[0], "expected manuscript SHA-256")
    if package.get("manuscript_sha256") != expected:
        raise ReleasePointerError("Package manuscript does not match controlled truth")
    return expected


def validate_package_against_publication(
    package: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    slug: str,
    expected_manuscript_sha256: str = "",
) -> dict[str, Any]:
    source_sha256 = str(package.get("source_sha256") or "").strip().lower()
    if source_sha256 not in _controlled_hashes(context):
        raise ReleasePointerError("Package source does not match controlled publication truth")
    manuscript_sha256 = _expected_manuscript_sha256(
        context,
        expected_manuscript_sha256,
        package,
    )
    descriptor = require_sha256(package.get("release_descriptor_sha256"), "release descriptor")
    try:
        return validate_audiobook_package(
            package,
            expected_slug=slug,
            expected_source_sha256=source_sha256,
            expected_manuscript_sha256=manuscript_sha256,
            expected_release_descriptor_sha256=descriptor,
        )
    except AudiobookPackageValidationError as exc:
        raise ReleasePointerError(f"Canonical package validation failed: {exc}") from None


def validate_release_descriptor(
    release_descriptor: Mapping[str, Any],
    package: Mapping[str, Any],
) -> dict[str, Any]:
    descriptor = copy.deepcopy(dict(release_descriptor))
    if descriptor.get("schema_version") != "audiobook_release_descriptor.v1":
        raise ReleasePointerError("Release descriptor schema is invalid")
    expected_sha256 = sha256_bytes(canonical_json_bytes(descriptor))
    if expected_sha256 != package.get("release_descriptor_sha256"):
        raise ReleasePointerError("Release descriptor SHA-256 does not match the package")
    for descriptor_field, package_field in (
        ("slug", "slug"),
        ("controlled_source_sha256", "source_sha256"),
        ("manuscript_sha256", "manuscript_sha256"),
    ):
        if descriptor.get(descriptor_field) != package.get(package_field):
            raise ReleasePointerError(
                f"Release descriptor {descriptor_field} does not match the package"
            )
    blockers = descriptor.get("known_release_blockers")
    if blockers != []:
        raise ReleasePointerError("Release descriptor has known release blockers")
    if descriptor.get("release_candidate_status") != "RELEASE_CANDIDATE":
        raise ReleasePointerError("Release descriptor is not an explicit release candidate")
    candidate_evidence = descriptor.get("release_candidate_evidence")
    if (
        not isinstance(candidate_evidence, Mapping)
        or candidate_evidence.get("status") != "PASS"
        or candidate_evidence.get("all_release_gates_passed") is not True
    ):
        raise ReleasePointerError("Release descriptor lacks passing release-candidate evidence")
    evidence_sha256 = descriptor.get("evidence_sha256")
    if (
        not isinstance(evidence_sha256, Mapping)
        or not evidence_sha256
        or any(
            not isinstance(name, str)
            or not name
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
            for name, digest in evidence_sha256.items()
        )
    ):
        raise ReleasePointerError("Release descriptor evidence hashes are incomplete")
    return descriptor


def validate_qa_candidate_release_descriptor(
    release_descriptor: Mapping[str, Any],
    package: Mapping[str, Any],
    *,
    controlled_language: Any,
) -> dict[str, Any]:
    """Validate the exact post-QA/pre-storage descriptor emitted by builder v2."""

    descriptor = copy.deepcopy(dict(release_descriptor))
    if descriptor.get("schema_version") != "audiobook_release_descriptor.v1":
        raise ReleasePointerError("QA-candidate release descriptor schema is invalid")
    if (
        sha256_bytes(canonical_json_bytes(descriptor))
        != package.get("release_descriptor_sha256")
    ):
        raise ReleasePointerError(
            "QA-candidate release descriptor SHA-256 does not match the package"
        )
    for descriptor_field, package_field in (
        ("slug", "slug"),
        ("controlled_source_sha256", "source_sha256"),
        ("manuscript_sha256", "manuscript_sha256"),
    ):
        if descriptor.get(descriptor_field) != package.get(package_field):
            raise ReleasePointerError(
                f"QA-candidate {descriptor_field} does not match the package"
            )
    if (
        descriptor.get("release_candidate_status")
        != "QA_PASSED_STORAGE_PENDING"
        or descriptor.get("known_release_blockers")
        != QA_CANDIDATE_DOWNSTREAM_GATES
    ):
        raise ReleasePointerError(
            "Release descriptor is not the exact post-QA/pre-storage candidate"
        )
    candidate = descriptor.get("release_candidate_evidence")
    gates = candidate.get("gates") if isinstance(candidate, Mapping) else None
    minimums = (
        gates.get("listening_minimum_scores")
        if isinstance(gates, Mapping)
        else None
    )
    if (
        not isinstance(candidate, Mapping)
        or candidate.get("status") != "PASS"
        or candidate.get("all_pre_storage_release_gates_passed") is not True
        or not isinstance(gates, Mapping)
        or gates.get("reader_truth") != "PASS"
        or gates.get("source_content_toc") != "PASS"
        or gates.get("rights_tier") != "A"
        or gates.get("first_words_match") is not True
        or gates.get("last_words_match") is not True
        or gates.get("ordered_content_integrity") is not True
        or gates.get("listening_sample_count") != 6
        or gates.get("fatal_flags") != []
        or gates.get("sync_tier")
        != "PARAGRAPH_OR_SECTION_SYNC_PREMIUM"
        or gates.get("auto_estimated_sync") is not False
        or not isinstance(gates.get("covers"), Mapping)
        or not gates["covers"].get("front")
        or not gates["covers"].get("back")
        or not isinstance(minimums, Mapping)
    ):
        raise ReleasePointerError(
            "QA-candidate release evidence does not pass every non-storage gate"
        )
    declared_language = str(gates.get("language") or "").strip().lower()
    controlled_language_value = str(controlled_language or "").strip().lower()
    declared_family = QA_CANDIDATE_LANGUAGE_ALIASES.get(declared_language)
    controlled_family = QA_CANDIDATE_LANGUAGE_ALIASES.get(
        controlled_language_value
    )
    if not declared_family or not controlled_family:
        raise ReleasePointerError(
            "QA-candidate controlled or declared language is unsupported"
        )
    if declared_family != controlled_family:
        raise ReleasePointerError(
            "QA-candidate listening language does not match controlled truth"
        )
    if controlled_family == "english":
        required_policy = QA_CANDIDATE_ENGLISH_LISTENING_POLICY
        listening_minimums = QA_CANDIDATE_ENGLISH_LISTENING_MINIMUMS
    else:
        required_policy = QA_CANDIDATE_BENGALI_LISTENING_POLICY
        listening_minimums = QA_CANDIDATE_BENGALI_LISTENING_MINIMUMS
    if gates.get("listening_policy") != required_policy:
        raise ReleasePointerError(
            "QA-candidate listening policy does not match the active "
            f"{controlled_family} policy"
        )
    try:
        asr_score = float(gates["asr_score"])
        coverage = float(gates["source_coverage"])
        listening_values = {
            name: float(minimums[name])
            for name in listening_minimums
        }
    except (KeyError, TypeError, ValueError):
        raise ReleasePointerError(
            "QA-candidate objective/listening scores are incomplete"
        ) from None
    if (
        not math.isfinite(asr_score)
        or not 0.0 <= asr_score <= 10.0
        or not math.isfinite(coverage)
        or not 0.0 <= coverage <= 1.0
        or asr_score < 9.7
        or coverage < 0.98
    ):
        raise ReleasePointerError(
            "QA-candidate objective ASR/source coverage does not pass"
        )
    failed_scores = [
        name
        for name, minimum in listening_minimums.items()
        if (
            not math.isfinite(listening_values[name])
            or listening_values[name] < minimum
            or listening_values[name]
            > (1.0 if name == "confidence_score" else 10.0)
        )
    ]
    if failed_scores:
        raise ReleasePointerError(
            "QA-candidate listening scores do not pass: "
            + ", ".join(sorted(failed_scores))
        )
    evidence_sha256 = descriptor.get("evidence_sha256")
    if (
        not isinstance(evidence_sha256, Mapping)
        or not evidence_sha256
        or any(
            not isinstance(name, str)
            or not name
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
            for name, digest in evidence_sha256.items()
        )
    ):
        raise ReleasePointerError(
            "QA-candidate release descriptor evidence hashes are incomplete"
        )
    return descriptor


def validate_hidden_before_proof(
    proof: Mapping[str, Any],
    *,
    slug: str,
    reference_time: str,
) -> dict[str, Any]:
    value = copy.deepcopy(dict(proof))
    expected_urls = {
        "reader_url": f"https://www.theearnalism.com/reader/{slug}",
        "legacy_audio_url": (
            f"https://api.theearnalism.com/api/reader/book/{slug}/audiobook"
        ),
        "package_manifest_url": (
            f"https://api.theearnalism.com/api/reader/book/{slug}/audiobook/manifest"
        ),
    }
    try:
        checked_at = datetime.fromisoformat(
            str(value.get("checked_at") or "").replace("Z", "+00:00")
        )
        reference = datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
        proof_age_seconds = (reference - checked_at).total_seconds()
    except (TypeError, ValueError):
        proof_age_seconds = -1
    if (
        value.get("schema_version") != HIDDEN_BEFORE_PROOF_SCHEMA
        or value.get("slug") != slug
        or value.get("status") != "PUBLIC_AUDIO_HIDDEN_VERIFIED"
        or value.get("reader_http_status") != 200
        or value.get("legacy_audio_http_status") != 404
        or value.get("package_manifest_http_status") != 404
        or value.get("public_audio_enabled") is not False
        or value.get("public_audiobook_enabled") is not False
        or value.get("approved_audiobooks_contains_slug") is not False
        or value.get("browser_listen_control_count") != 0
        or value.get("browser_audio_request_count") != 0
        or any(value.get(field) != url for field, url in expected_urls.items())
        or proof_age_seconds < 0
        or proof_age_seconds > 24 * 60 * 60
    ):
        raise ReleasePointerError(
            "Hidden-before proof is incomplete, stale-shaped, or non-canonical"
        )
    return value


def validate_hidden_rollback_descriptor(
    descriptor: Mapping[str, Any],
    *,
    slug: str,
    source_sha256: str,
    manuscript_sha256: str,
) -> tuple[dict[str, Any], str]:
    value = copy.deepcopy(dict(descriptor))
    expected = {
        "schema_version": HIDDEN_IDENTITY_SCHEMA,
        "slug": slug,
        "state": "NO_PUBLIC_AUDIO",
        "source_sha256": source_sha256,
        "manuscript_sha256": manuscript_sha256,
    }
    if any(value.get(field) != expected_value for field, expected_value in expected.items()):
        raise ReleasePointerError(
            "Hidden rollback descriptor is not bound to controlled hidden truth"
        )
    if set(value) != set(expected):
        raise ReleasePointerError("Hidden rollback descriptor has unexpected fields")
    return value, sha256_bytes(canonical_json_bytes(value))


def _validate_reader_publication_truth(
    context: Mapping[str, Any],
    slug: str,
) -> None:
    public_book = context["public_book"]
    reader_manifest = context["reader_manifest"]
    source_evidence = context["source_evidence"]
    approval_evidence = context["approval_evidence"]
    if any(
        document.get("slug") != slug
        for document in (
            public_book,
            reader_manifest,
            source_evidence,
            approval_evidence,
        )
    ):
        raise ReleasePointerError("Controlled reader/publication slug truth diverges")
    if (
        public_book.get("approved_to_publish") is not True
        or str(public_book.get("verification_status") or "").lower() != "approved"
        or public_book.get("qa_status") != "QA_PASSED"
        or public_book.get("isPublic") is not True
        or public_book.get("isLive") is not True
        or public_book.get("is_published") is not True
        or public_book.get("allowPublicReading") is not True
    ):
        raise ReleasePointerError(
            "Initial package activation requires approved live reader/publication truth"
        )
    if (
        approval_evidence.get("approved_to_publish") is not True
        or str(approval_evidence.get("verification_status") or "").lower()
        != "approved"
        or approval_evidence.get("qa_status") != "QA_PASSED"
    ):
        raise ReleasePointerError(
            "Initial package activation requires approved publication evidence"
        )
    public_chapters = public_book.get("chapters")
    reader_chapters = reader_manifest.get("chapters")
    try:
        reader_chapter_count = int(reader_manifest.get("chapter_count"))
    except (TypeError, ValueError):
        reader_chapter_count = 0
    if (
        not isinstance(public_chapters, list)
        or not public_chapters
        or any(
            not isinstance(chapter, Mapping)
            or chapter.get("processing_status") != "ready"
            for chapter in public_chapters
        )
        or not isinstance(reader_chapters, list)
        or not reader_chapters
        or reader_chapter_count != len(reader_chapters)
    ):
        raise ReleasePointerError(
            "Initial package activation requires a ready controlled reader manifest"
        )


def _validate_initial_release_slot(
    context: Mapping[str, Any],
) -> None:
    public_book = context["public_book"]
    reader_manifest = context["reader_manifest"]
    approval_evidence = context["approval_evidence"]
    for field in MANAGED_FIELDS:
        if public_book.get(field) != reader_manifest.get(field):
            raise ReleasePointerError(
                f"Controlled public and reader release metadata diverge: {field}"
            )
    if _state_from_publication(context, str(public_book.get("slug") or "")) is not None:
        raise ReleasePointerError("An audiobook active release state already exists")
    for field in (
        "audiobook_legacy_release_descriptor_sha256",
        "audiobook_release_descriptor_sha256",
    ):
        if public_book.get(field) or reader_manifest.get(field):
            raise ReleasePointerError(
                "Initial package activation requires an empty release pointer slot"
            )
    for field in (
        "audiobook_package",
        "audiobook_packages",
        "audiobook_package_release_evidence",
    ):
        if public_book.get(field) or reader_manifest.get(field):
            raise ReleasePointerError(
                "Initial package activation refuses existing package metadata"
            )
    audiobook = public_book.get("audiobook")
    assets = public_book.get("audiobook_assets")
    if (
        public_book.get("audio_enabled") is not False
        or public_book.get("audiobook_enabled") is not False
        or reader_manifest.get("audio_enabled") is not False
        or reader_manifest.get("audiobook_enabled") is not False
        or approval_evidence.get("audiobook_enabled") is not False
        or approval_evidence.get("audio_public_release")
        == "PUBLIC_AUDIO_RELEASE_APPROVED"
        or (isinstance(audiobook, Mapping) and bool(audiobook.get("url")))
        or (isinstance(assets, Mapping) and bool(assets))
    ):
        raise ReleasePointerError(
            "Initial package activation requires audio-hidden, legacy-free controlled truth"
        )


def _validate_current_audio_release_approval(
    context: Mapping[str, Any],
) -> None:
    public_book = context["public_book"]
    reader_manifest = context["reader_manifest"]
    approval = context["approval_evidence"]
    if (
        public_book.get("audio_enabled") is not True
        or public_book.get("audiobook_enabled") is not True
        or reader_manifest.get("audio_enabled") is not True
        or reader_manifest.get("audiobook_enabled") is not True
        or approval.get("audiobook_enabled") is not True
        or approval.get("audio_public_release")
        != "PUBLIC_AUDIO_RELEASE_APPROVED"
        or approval.get("qa_status") != "QA_PASSED"
        or approval.get("audio_qa_status") not in {None, "", "QA_PASSED"}
        or approval.get("upload_status") not in CHECKSUM_VERIFIED_UPLOAD_STATUSES
        or not str(approval.get("approval_scope") or "").strip()
        or approval.get("release_blockers") not in (None, [])
    ):
        raise ReleasePointerError(
            "Reactivation requires current approved, checksum-verified public audio truth"
        )


def _validated_release_bundle(
    context: Mapping[str, Any],
    slug: str,
    package: Mapping[str, Any],
    release_descriptor: Mapping[str, Any],
    primary_receipt: Mapping[str, Any],
    replica_receipt: Mapping[str, Any],
    primary_release_manifest_receipt: Mapping[str, Any],
    replica_release_manifest_receipt: Mapping[str, Any],
    *,
    expected_manuscript_sha256: str,
    release_manifest_sha256: str,
    release_manifest_size_bytes: int,
    generated_at: str,
    primary_receipt_sha256: str,
    replica_receipt_sha256: str,
    primary_release_manifest_receipt_sha256: str,
    replica_release_manifest_receipt_sha256: str,
    descriptor_validator: Callable[
        [Mapping[str, Any], Mapping[str, Any]], dict[str, Any]
    ] = validate_release_descriptor,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validated = validate_package_against_publication(
        package,
        context,
        slug=slug,
        expected_manuscript_sha256=expected_manuscript_sha256,
    )
    descriptor_validator(release_descriptor, validated)
    receipt_evidence = validate_release_receipts(
        validated,
        primary_receipt,
        replica_receipt,
    )
    receipt_evidence.update(
        validate_release_manifest_receipts(
            validated,
            primary_release_manifest_receipt,
            replica_release_manifest_receipt,
            release_manifest_sha256=release_manifest_sha256,
            release_manifest_size_bytes=release_manifest_size_bytes,
        )
    )
    receipt_evidence["primary_receipt_sha256"] = require_sha256(
        primary_receipt_sha256,
        "primary receipt SHA-256",
    )
    receipt_evidence["replica_receipt_sha256"] = require_sha256(
        replica_receipt_sha256,
        "replica receipt SHA-256",
    )
    receipt_evidence["primary_release_manifest_receipt_sha256"] = require_sha256(
        primary_release_manifest_receipt_sha256,
        "primary release-manifest receipt SHA-256",
    )
    receipt_evidence["replica_release_manifest_receipt_sha256"] = require_sha256(
        replica_release_manifest_receipt_sha256,
        "replica release-manifest receipt SHA-256",
    )
    receipt_evidence["staged_at"] = generated_at
    return validated, receipt_evidence


def _validate_retained_packages(
    packages: Mapping[str, Any],
    evidence: Mapping[str, Any],
    context: Mapping[str, Any],
    retained: Sequence[str],
    *,
    slug: str,
    manuscript_sha256: str,
    hidden_descriptor: str = "",
) -> None:
    legacy = str(
        context["public_book"].get("audiobook_legacy_release_descriptor_sha256") or ""
    )
    hidden = str(
        hidden_descriptor
        or context["public_book"].get("audiobook_hidden_release_descriptor_sha256")
        or ""
    )
    if hidden:
        expected_hidden_descriptors = {
            sha256_bytes(
                canonical_json_bytes(
                    {
                        "schema_version": HIDDEN_IDENTITY_SCHEMA,
                        "slug": slug,
                        "state": "NO_PUBLIC_AUDIO",
                        "source_sha256": package.get("source_sha256"),
                        "manuscript_sha256": package.get("manuscript_sha256"),
                    }
                )
            )
            for package in packages.values()
            if isinstance(package, Mapping)
        }
        if hidden not in expected_hidden_descriptors:
            raise ReleasePointerError(
                "Controlled hidden release descriptor is not deterministic"
            )
    for descriptor in retained:
        package = packages.get(descriptor)
        if package is None:
            if descriptor not in {legacy, hidden}:
                raise ReleasePointerError(
                    "Retained release lacks a package manifest and is neither "
                    f"the legacy nor hidden fallback: {descriptor}"
                )
            continue  # Legacy monolith/hidden fallback intentionally lack package v2.
        validate_package_against_publication(
            package,
            context,
            slug=slug,
            expected_manuscript_sha256=manuscript_sha256,
        )
        _eligible_evidence(evidence, descriptor)


def _state_from_publication(context: Mapping[str, Any], slug: str) -> dict[str, Any] | None:
    state = context["public_book"].get("audiobook_active_release")
    if not state:
        return None
    try:
        validated = validate_active_release_state(state)
    except AudiobookReleaseSelectionError as exc:
        raise ReleasePointerError(f"Active release state is invalid: {exc}") from None
    if validated["slug"] != slug:
        raise ReleasePointerError("Active release state slug mismatch")
    return validated


def _retained_for_stage(state: Mapping[str, Any], candidate: str) -> list[str]:
    active = str(state["active_release_descriptor_sha256"])
    prior = [
        value
        for value in state.get("retained_release_descriptor_sha256s") or []
        if value not in {active, state.get("candidate_release_descriptor_sha256"), candidate}
    ][:1]
    return [active, *prior, candidate]


def _unique_limited(values: Sequence[str], limit: int = 3) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
        if len(result) == limit:
            break
    return result


def _eligible_evidence(evidence: Mapping[str, Any], descriptor: str) -> None:
    item = evidence.get(descriptor)
    if (
        not isinstance(item, Mapping)
        or item.get("schema_version") != EVIDENCE_SCHEMA
        or item.get("release_descriptor_sha256") != descriptor
        or item.get("release_eligible") is not True
        or item.get("receipt_roles") != ["primary", "replica"]
    ):
        raise ReleasePointerError("Candidate is not bound to release-eligible production/DR receipts")
    for field in (
        "primary_receipt_sha256",
        "replica_receipt_sha256",
        "release_manifest_sha256",
        "primary_release_manifest_receipt_sha256",
        "replica_release_manifest_receipt_sha256",
    ):
        require_sha256(item.get(field), field.replace("_", " "))
    expected_key = (
        f"v1/prod/sprint1/{item.get('slug')}/releases/{descriptor}/release-manifest.json"
    )
    if item.get("release_manifest_key") != expected_key:
        raise ReleasePointerError("Release evidence has an unexpected release-manifest key")
    try:
        manifest_size = int(item.get("release_manifest_size_bytes"))
    except (TypeError, ValueError):
        manifest_size = 0
    if manifest_size <= 0:
        raise ReleasePointerError("Release evidence has an invalid release-manifest size")
    if (
        not item.get("primary_release_manifest_version_id")
        or not item.get("replica_release_manifest_version_id")
        or item.get("primary_release_manifest_store")
        != RELEASE_STORE_ROLES["primary"]
        or item.get("replica_release_manifest_store")
        != RELEASE_STORE_ROLES["replica"]
    ):
        raise ReleasePointerError(
            "Release evidence lacks independent production/DR release-manifest identities"
        )


def _managed_values(
    *,
    packages: Mapping[str, Any],
    evidence: Mapping[str, Any],
    state: Mapping[str, Any],
    manuscript_sha256: str,
    legacy_descriptor: str,
    hidden_descriptor: str = "",
    package_canary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "audiobook_packages": copy.deepcopy(dict(packages)),
        "audiobook_package_release_evidence": copy.deepcopy(dict(evidence)),
        "audiobook_active_release": copy.deepcopy(dict(state)),
        "audiobook_manuscript_sha256": manuscript_sha256,
        "audiobook_release_descriptor_sha256": state["active_release_descriptor_sha256"],
        "audiobook_legacy_release_descriptor_sha256": legacy_descriptor,
        "audiobook_hidden_release_descriptor_sha256": hidden_descriptor,
        "audiobook_package_canary": copy.deepcopy(dict(package_canary or {})),
    }


def _managed_values_from_context(
    context: Mapping[str, Any],
    *,
    state: Mapping[str, Any],
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in MANAGED_FIELDS:
        if context["public_book"].get(field) != context["reader_manifest"].get(field):
            raise ReleasePointerError(
                f"Controlled public and reader release metadata diverge: {field}"
            )
        values[field] = copy.deepcopy(context["public_book"].get(field))
    values["audiobook_active_release"] = copy.deepcopy(dict(state))
    return values


def _checksum_document(
    checksum_manifest: Mapping[str, Any],
    file_bytes: Mapping[str, bytes],
    generated_at: str,
) -> dict[str, Any]:
    result = copy.deepcopy(dict(checksum_manifest))
    rows = result.get("files")
    if not isinstance(rows, list):
        raise ReleasePointerError("checksum_manifest.json files must be an array")
    found: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ReleasePointerError("checksum_manifest.json contains an invalid row")
        filename = str(row.get("file") or "")
        if filename in file_bytes:
            row["sha256"] = sha256_bytes(file_bytes[filename])
            found.add(filename)
    if found != set(file_bytes):
        raise ReleasePointerError("checksum_manifest.json does not cover every managed file")
    result["generated_at"] = generated_at
    return result


@contextmanager
def _release_lock(repo_root: Path, slug: str):
    lock_path = Path(tempfile.gettempdir()) / f"earnalism-audiobook-release-{sha256_bytes(f'{repo_root}:{slug}'.encode())[:20]}.lock"
    with lock_path.open("a+b") as lock:
        try:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass


def _atomic_replace_many(changes: Mapping[Path, bytes]) -> None:
    originals = {path: path.read_bytes() for path in changes}
    staged: dict[Path, Path] = {}
    try:
        for path, payload in changes.items():
            fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            temp_path = Path(raw_temp)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            staged[path] = temp_path
        for path, temp_path in staged.items():
            os.replace(temp_path, path)
    except Exception as exc:
        for path, payload in originals.items():
            fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.rollback.", suffix=".tmp", dir=path.parent)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(raw_temp, path)
        raise ReleasePointerError(f"Mirrored catalog mutation rolled back: {type(exc).__name__}") from None
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)


def mutate_mirrors(
    repo_root: Path,
    slug: str,
    managed: Mapping[str, Any],
    *,
    generated_at: str,
    apply: bool,
    expected_fingerprint: str,
    approval_evidence_updates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    with _release_lock(repo_root, slug):
        context = load_mirrored_publication(repo_root, slug)
        _verify_controlled_checksums(context)
        if publication_fingerprint(context) != expected_fingerprint:
            raise ReleasePointerError("Controlled publication changed during release planning")
        public_book = copy.deepcopy(context["public_book"])
        reader_manifest = copy.deepcopy(context["reader_manifest"])
        approval_evidence = copy.deepcopy(context["approval_evidence"])
        for key in MANAGED_FIELDS:
            public_book[key] = copy.deepcopy(managed[key])
            reader_manifest[key] = copy.deepcopy(managed[key])
        if approval_evidence_updates:
            approval_evidence.update(copy.deepcopy(dict(approval_evidence_updates)))
        public_bytes = json_bytes(public_book)
        reader_bytes = json_bytes(reader_manifest)
        approval_bytes = json_bytes(approval_evidence)
        checksum_inputs = {
            "public_book.json": public_bytes,
            "reader_manifest.json": reader_bytes,
        }
        if approval_evidence_updates:
            checksum_inputs["approval_evidence.json"] = approval_bytes
        checksum = _checksum_document(
            context["checksum_manifest"],
            checksum_inputs,
            generated_at,
        )
        checksum_bytes = json_bytes(checksum)
        changes: dict[Path, bytes] = {}
        for publication in context["dirs"]:
            changes[publication / "public_book.json"] = public_bytes
            changes[publication / "reader_manifest.json"] = reader_bytes
            if approval_evidence_updates:
                changes[publication / "approval_evidence.json"] = approval_bytes
            changes[publication / "checksum_manifest.json"] = checksum_bytes
        if apply:
            originals = {path: path.read_bytes() for path in changes}
            try:
                _atomic_replace_many(changes)
                verified = load_mirrored_publication(repo_root, slug)
                verified_payloads = {
                    "public_book.json": public_bytes,
                    "reader_manifest.json": reader_bytes,
                }
                if approval_evidence_updates:
                    verified_payloads["approval_evidence.json"] = approval_bytes
                    if verified["approval_evidence"] != approval_evidence:
                        raise ReleasePointerError(
                            "Post-write approval evidence verification failed"
                        )
                for filename, payload in verified_payloads.items():
                    entry = next(
                        (
                            row
                            for row in verified["checksum_manifest"]["files"]
                            if row.get("file") == filename
                        ),
                        {},
                    )
                    if entry.get("sha256") != sha256_bytes(payload):
                        raise ReleasePointerError(
                            f"Post-write checksum verification failed: {filename}"
                        )
            except Exception as exc:
                try:
                    _atomic_replace_many(originals)
                except ReleasePointerError as rollback_exc:
                    raise ReleasePointerError(
                        f"Post-write verification and rollback failed: {rollback_exc}"
                    ) from None
                if isinstance(exc, ReleasePointerError):
                    raise ReleasePointerError(
                        f"Mirrored catalog mutation rolled back: {exc}"
                    ) from None
                raise ReleasePointerError(
                    f"Mirrored catalog mutation rolled back: {type(exc).__name__}"
                ) from None
        return {
            "applied": apply,
            "slug": slug,
            "managed": copy.deepcopy(dict(managed)),
            "files": [str(path) for path in changes],
        }


def bind_legacy_release(
    repo_root: Path,
    slug: str,
    *,
    generated_at: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Bind an already-public legacy audiobook to a deterministic descriptor."""

    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    identity = derive_legacy_release_identity(context, slug)
    descriptor = sha256_bytes(canonical_json_bytes(identity))
    existing_values = {
        str(context[document].get("audiobook_legacy_release_descriptor_sha256") or "")
        for document in ("public_book", "reader_manifest")
    }
    existing_values.discard("")
    if existing_values and existing_values != {descriptor}:
        raise ReleasePointerError(
            "Existing legacy release descriptor conflicts with controlled audio identity"
        )
    result = {
        "applied": False,
        "slug": slug,
        "status": (
            "LEGACY_ALREADY_BOUND"
            if existing_values == {descriptor}
            and all(
                context[document].get("audiobook_legacy_release_descriptor_sha256")
                == descriptor
                for document in ("public_book", "reader_manifest")
            )
            else "LEGACY_BINDING_VALIDATED"
        ),
        "audiobook_legacy_release_descriptor_sha256": descriptor,
        "legacy_identity": identity,
        "files": [],
    }
    if not apply or result["status"] == "LEGACY_ALREADY_BOUND":
        return result

    expected_fingerprint = publication_fingerprint(context)
    with _release_lock(repo_root, slug):
        current = load_mirrored_publication(repo_root, slug)
        if publication_fingerprint(current) != expected_fingerprint:
            raise ReleasePointerError("Controlled publication changed during legacy binding")
        _verify_controlled_checksums(current)
        current_identity = derive_legacy_release_identity(current, slug)
        if sha256_bytes(canonical_json_bytes(current_identity)) != descriptor:
            raise ReleasePointerError("Controlled legacy audio identity changed during binding")
        current_existing = {
            str(
                current[document].get(
                    "audiobook_legacy_release_descriptor_sha256"
                )
                or ""
            )
            for document in ("public_book", "reader_manifest")
        }
        current_existing.discard("")
        if current_existing and current_existing != {descriptor}:
            raise ReleasePointerError(
                "Existing legacy release descriptor conflicts with controlled audio identity"
            )

        public_book = copy.deepcopy(current["public_book"])
        reader_manifest = copy.deepcopy(current["reader_manifest"])
        public_book["audiobook_legacy_release_descriptor_sha256"] = descriptor
        reader_manifest["audiobook_legacy_release_descriptor_sha256"] = descriptor
        public_bytes = json_bytes(public_book)
        reader_bytes = json_bytes(reader_manifest)
        checksum = _checksum_document(
            current["checksum_manifest"],
            {
                "public_book.json": public_bytes,
                "reader_manifest.json": reader_bytes,
            },
            generated_at or utc_now(),
        )
        changes: dict[Path, bytes] = {}
        for publication in current["dirs"]:
            changes[publication / "public_book.json"] = public_bytes
            changes[publication / "reader_manifest.json"] = reader_bytes
            changes[publication / "checksum_manifest.json"] = json_bytes(checksum)
        originals = {path: path.read_bytes() for path in changes}
        try:
            _atomic_replace_many(changes)
            verified = load_mirrored_publication(repo_root, slug)
            if verified["approval_evidence"] != current["approval_evidence"]:
                raise ReleasePointerError("Legacy binding changed approval evidence")
            for document in ("public_book", "reader_manifest"):
                if (
                    verified[document].get(
                        "audiobook_legacy_release_descriptor_sha256"
                    )
                    != descriptor
                ):
                    raise ReleasePointerError(
                        f"Legacy binding verification failed: {document}"
                    )
            _verify_controlled_checksums(verified)
        except Exception as exc:
            try:
                _atomic_replace_many(originals)
            except ReleasePointerError as rollback_exc:
                raise ReleasePointerError(
                    f"Legacy binding verification and rollback failed: {rollback_exc}"
                ) from None
            if isinstance(exc, ReleasePointerError):
                raise ReleasePointerError(
                    f"Legacy binding rolled back: {exc}"
                ) from None
            raise ReleasePointerError(
                f"Legacy binding rolled back: {type(exc).__name__}"
            ) from None

    result["applied"] = True
    result["status"] = "LEGACY_BOUND"
    result["files"] = [str(path) for path in changes]
    return result


def stage_candidate(
    repo_root: Path,
    slug: str,
    package: Mapping[str, Any],
    release_descriptor: Mapping[str, Any],
    primary_receipt: Mapping[str, Any],
    replica_receipt: Mapping[str, Any],
    primary_release_manifest_receipt: Mapping[str, Any],
    replica_release_manifest_receipt: Mapping[str, Any],
    *,
    rollout_salt: str,
    legacy_descriptor: str = "",
    expected_manuscript_sha256: str = "",
    release_manifest_sha256: str,
    release_manifest_size_bytes: int,
    generated_at: str | None = None,
    apply: bool = False,
    primary_receipt_sha256: str = "",
    replica_receipt_sha256: str = "",
    primary_release_manifest_receipt_sha256: str = "",
    replica_release_manifest_receipt_sha256: str = "",
) -> dict[str, Any]:
    if not rollout_salt or rollout_salt != rollout_salt.strip():
        raise ReleasePointerError("A canonical non-empty sticky rollout salt is required")
    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    operation_time = generated_at or utc_now()
    validated, receipt_evidence = _validated_release_bundle(
        context,
        slug,
        package,
        release_descriptor,
        primary_receipt,
        replica_receipt,
        primary_release_manifest_receipt,
        replica_release_manifest_receipt,
        expected_manuscript_sha256=expected_manuscript_sha256,
        release_manifest_sha256=release_manifest_sha256,
        release_manifest_size_bytes=release_manifest_size_bytes,
        generated_at=operation_time,
        primary_receipt_sha256=primary_receipt_sha256,
        replica_receipt_sha256=replica_receipt_sha256,
        primary_release_manifest_receipt_sha256=(
            primary_release_manifest_receipt_sha256
        ),
        replica_release_manifest_receipt_sha256=(
            replica_release_manifest_receipt_sha256
        ),
    )

    descriptor = validated["release_descriptor_sha256"]
    manuscript_sha256 = validated["manuscript_sha256"]
    packages = copy.deepcopy(context["public_book"].get("audiobook_packages") or {})
    evidence = copy.deepcopy(
        context["public_book"].get("audiobook_package_release_evidence") or {}
    )
    if not isinstance(packages, dict) or not isinstance(evidence, dict):
        raise ReleasePointerError("Existing package metadata is not canonical")

    state = _state_from_publication(context, slug)
    existing_legacy = str(
        context["public_book"].get("audiobook_legacy_release_descriptor_sha256") or ""
    ).strip().lower()
    if existing_legacy:
        existing_legacy = require_sha256(
            existing_legacy,
            "controlled legacy release descriptor",
        )
    elif state is None:
        raise ReleasePointerError(
            "A pre-existing controlled legacy release descriptor is required"
        )
    if legacy_descriptor:
        if (
            not existing_legacy
            or require_sha256(
                legacy_descriptor,
                "requested legacy release descriptor",
            )
            != existing_legacy
        ):
            raise ReleasePointerError(
                "Requested legacy release descriptor is not bound to controlled truth"
            )
    if state is None:
        active = existing_legacy
        state = build_active_release_state(
            slug=slug,
            active_release_descriptor_sha256=active,
            retained_release_descriptor_sha256s=[active],
        )
    elif state["status"] != "ACTIVE":
        raise ReleasePointerError(
            "Inactive release state must be explicitly reactivated before staging"
        )
    elif int(state["rollout"]["percentage"]) != 0:
        raise ReleasePointerError("Set rollout to 0 before replacing a staged candidate")
    if descriptor == state["active_release_descriptor_sha256"]:
        raise ReleasePointerError("Candidate must differ from the active release")

    retained = _retained_for_stage(state, descriptor)
    packages[descriptor] = validated
    evidence[descriptor] = receipt_evidence
    packages = {key: value for key, value in packages.items() if key in retained}
    evidence = {key: value for key, value in evidence.items() if key in retained}
    _validate_retained_packages(
        packages,
        evidence,
        context,
        retained,
        slug=slug,
        manuscript_sha256=manuscript_sha256,
    )
    state = build_active_release_state(
        slug=slug,
        active_release_descriptor_sha256=state["active_release_descriptor_sha256"],
        retained_release_descriptor_sha256s=retained,
        candidate_release_descriptor_sha256=descriptor,
        rollout_percentage=0,
        rollout_salt=rollout_salt,
    )
    managed = _managed_values(
        packages=packages,
        evidence=evidence,
        state=state,
        manuscript_sha256=manuscript_sha256,
        legacy_descriptor=existing_legacy,
        hidden_descriptor=str(
            context["public_book"].get(
                "audiobook_hidden_release_descriptor_sha256"
            )
            or ""
        ),
        package_canary=context["public_book"].get("audiobook_package_canary"),
    )
    result = mutate_mirrors(
        repo_root,
        slug,
        managed,
        generated_at=operation_time,
        apply=apply,
        expected_fingerprint=publication_fingerprint(context),
    )
    result["status"] = "CANDIDATE_STAGED" if apply else "CANDIDATE_STAGE_VALIDATED"
    return result


def activate_initial_release(
    repo_root: Path,
    slug: str,
    package: Mapping[str, Any],
    release_descriptor: Mapping[str, Any],
    primary_receipt: Mapping[str, Any],
    replica_receipt: Mapping[str, Any],
    primary_release_manifest_receipt: Mapping[str, Any],
    replica_release_manifest_receipt: Mapping[str, Any],
    *,
    expected_manuscript_sha256: str = "",
    release_manifest_sha256: str,
    release_manifest_size_bytes: int,
    generated_at: str | None = None,
    apply: bool = False,
    primary_receipt_sha256: str = "",
    replica_receipt_sha256: str = "",
    primary_release_manifest_receipt_sha256: str = "",
    replica_release_manifest_receipt_sha256: str = "",
) -> dict[str, Any]:
    """Bind the first immutable package without approving public audio flags."""

    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    _validate_reader_publication_truth(context, slug)
    _validate_initial_release_slot(context)
    operation_time = generated_at or utc_now()
    validated, receipt_evidence = _validated_release_bundle(
        context,
        slug,
        package,
        release_descriptor,
        primary_receipt,
        replica_receipt,
        primary_release_manifest_receipt,
        replica_release_manifest_receipt,
        expected_manuscript_sha256=expected_manuscript_sha256,
        release_manifest_sha256=release_manifest_sha256,
        release_manifest_size_bytes=release_manifest_size_bytes,
        generated_at=operation_time,
        primary_receipt_sha256=primary_receipt_sha256,
        replica_receipt_sha256=replica_receipt_sha256,
        primary_release_manifest_receipt_sha256=(
            primary_release_manifest_receipt_sha256
        ),
        replica_release_manifest_receipt_sha256=(
            replica_release_manifest_receipt_sha256
        ),
    )
    descriptor = validated["release_descriptor_sha256"]
    manuscript_sha256 = validated["manuscript_sha256"]
    packages = {descriptor: validated}
    evidence = {descriptor: receipt_evidence}
    state = build_active_release_state(
        slug=slug,
        active_release_descriptor_sha256=descriptor,
        retained_release_descriptor_sha256s=[descriptor],
    )
    _validate_retained_packages(
        packages,
        evidence,
        context,
        [descriptor],
        slug=slug,
        manuscript_sha256=manuscript_sha256,
    )
    managed = _managed_values(
        packages=packages,
        evidence=evidence,
        state=state,
        manuscript_sha256=manuscript_sha256,
        legacy_descriptor="",
    )
    result = mutate_mirrors(
        repo_root,
        slug,
        managed,
        generated_at=operation_time,
        apply=apply,
        expected_fingerprint=publication_fingerprint(context),
    )
    result["status"] = (
        "INITIAL_RELEASE_ACTIVATED"
        if apply
        else "INITIAL_RELEASE_ACTIVATION_VALIDATED"
    )
    result["selected_release_descriptor_sha256"] = descriptor
    result["audio_approval_flags_changed"] = False
    return result


def activate_new_title_package_canary(
    repo_root: Path,
    slug: str,
    package: Mapping[str, Any],
    release_descriptor: Mapping[str, Any],
    primary_receipt: Mapping[str, Any],
    replica_receipt: Mapping[str, Any],
    primary_release_manifest_receipt: Mapping[str, Any],
    replica_release_manifest_receipt: Mapping[str, Any],
    hidden_before_proof: Mapping[str, Any],
    hidden_rollback_descriptor: Mapping[str, Any],
    *,
    rollout_salt: str,
    expected_manuscript_sha256: str,
    release_manifest_sha256: str,
    release_manifest_size_bytes: int,
    expected_package_sha256: str,
    expected_release_descriptor_sha256: str,
    expected_primary_receipt_sha256: str,
    expected_replica_receipt_sha256: str,
    expected_primary_release_manifest_receipt_sha256: str,
    expected_replica_release_manifest_receipt_sha256: str,
    expected_hidden_before_proof_sha256: str,
    expected_rollback_descriptor_sha256: str,
    generated_at: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Stage a first package at 5% against an explicit no-audio fallback.

    This is a transport canary. It deliberately keeps ordinary catalog and
    reader audio flags false until endpoint, Range, timestamps, and browser
    evidence are collected and a separate promotion is authorized.
    """

    if os.environ.get(NEW_TITLE_CANARY_APPROVAL_ENV) != "true":
        raise ReleasePointerError(
            f"{NEW_TITLE_CANARY_APPROVAL_ENV}=true is required"
        )
    if not rollout_salt or rollout_salt != rollout_salt.strip():
        raise ReleasePointerError("A canonical non-empty sticky rollout salt is required")

    expected_documents = (
        ("package", package, expected_package_sha256),
        (
            "release descriptor",
            release_descriptor,
            expected_release_descriptor_sha256,
        ),
        ("primary receipt", primary_receipt, expected_primary_receipt_sha256),
        ("replica receipt", replica_receipt, expected_replica_receipt_sha256),
        (
            "primary release-manifest receipt",
            primary_release_manifest_receipt,
            expected_primary_release_manifest_receipt_sha256,
        ),
        (
            "replica release-manifest receipt",
            replica_release_manifest_receipt,
            expected_replica_release_manifest_receipt_sha256,
        ),
        (
            "hidden-before proof",
            hidden_before_proof,
            expected_hidden_before_proof_sha256,
        ),
    )
    for label, document, expected_sha256 in expected_documents:
        expected = require_sha256(expected_sha256, f"expected {label}")
        if sha256_bytes(json_bytes(document)) != expected:
            raise ReleasePointerError(f"Expected {label} SHA-256 does not match")

    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    _validate_reader_publication_truth(context, slug)
    _validate_initial_release_slot(context)
    if (
        release_descriptor.get("title")
        != context["public_book"].get("title")
        or release_descriptor.get("author")
        != context["public_book"].get("author")
    ):
        raise ReleasePointerError(
            "QA-candidate title/author do not match controlled publication truth"
        )
    operation_time = generated_at or utc_now()
    proof = validate_hidden_before_proof(
        hidden_before_proof,
        slug=slug,
        reference_time=operation_time,
    )
    fingerprint = publication_fingerprint(context)
    _rollback, hidden_descriptor = validate_hidden_rollback_descriptor(
        hidden_rollback_descriptor,
        slug=slug,
        source_sha256=str(package.get("source_sha256") or ""),
        manuscript_sha256=str(package.get("manuscript_sha256") or ""),
    )
    if hidden_descriptor != expected_rollback_descriptor_sha256:
        raise ReleasePointerError(
            "Expected rollback descriptor SHA-256 is not its canonical identity"
        )
    validated, receipt_evidence = _validated_release_bundle(
        context,
        slug,
        package,
        release_descriptor,
        primary_receipt,
        replica_receipt,
        primary_release_manifest_receipt,
        replica_release_manifest_receipt,
        expected_manuscript_sha256=expected_manuscript_sha256,
        release_manifest_sha256=release_manifest_sha256,
        release_manifest_size_bytes=release_manifest_size_bytes,
        generated_at=operation_time,
        primary_receipt_sha256=expected_primary_receipt_sha256,
        replica_receipt_sha256=expected_replica_receipt_sha256,
        primary_release_manifest_receipt_sha256=(
            expected_primary_release_manifest_receipt_sha256
        ),
        replica_release_manifest_receipt_sha256=(
            expected_replica_release_manifest_receipt_sha256
        ),
        descriptor_validator=(
            lambda descriptor, validated_package:
            validate_qa_candidate_release_descriptor(
                descriptor,
                validated_package,
                controlled_language=context["reader_manifest"].get(
                    "language"
                ),
            )
        ),
    )
    candidate_descriptor = validated["release_descriptor_sha256"]
    if candidate_descriptor == hidden_descriptor:
        raise ReleasePointerError("Candidate and hidden descriptors must differ")
    packages = {candidate_descriptor: validated}
    evidence = {candidate_descriptor: receipt_evidence}
    state = build_active_release_state(
        slug=slug,
        active_release_descriptor_sha256=hidden_descriptor,
        retained_release_descriptor_sha256s=[
            hidden_descriptor,
            candidate_descriptor,
        ],
        candidate_release_descriptor_sha256=candidate_descriptor,
        rollout_percentage=5,
        rollout_salt=rollout_salt,
    )
    _validate_retained_packages(
        packages,
        evidence,
        context,
        state["retained_release_descriptor_sha256s"],
        slug=slug,
        manuscript_sha256=validated["manuscript_sha256"],
        hidden_descriptor=hidden_descriptor,
    )
    canary = {
        "schema_version": NEW_TITLE_CANARY_SCHEMA,
        "status": "PUBLIC_AUDIO_PACKAGE_CANARY_APPROVED",
        "slug": slug,
        "candidate_release_descriptor_sha256": candidate_descriptor,
        "candidate_package_version": validated["package_version"],
        "hidden_release_descriptor_sha256": hidden_descriptor,
        "rollout_percentage": 5,
        "rollout_salt": rollout_salt,
        "qa_candidate_release_descriptor_file_sha256": (
            expected_release_descriptor_sha256
        ),
        "package_release_evidence_sha256": sha256_bytes(
            canonical_json_bytes(receipt_evidence)
        ),
        "primary_receipt_sha256": expected_primary_receipt_sha256,
        "replica_receipt_sha256": expected_replica_receipt_sha256,
        "primary_release_manifest_receipt_sha256": (
            expected_primary_release_manifest_receipt_sha256
        ),
        "replica_release_manifest_receipt_sha256": (
            expected_replica_release_manifest_receipt_sha256
        ),
        "hidden_before_proof_sha256": expected_hidden_before_proof_sha256,
        "rollback_descriptor_sha256": expected_rollback_descriptor_sha256,
        "catalog_audio_enabled": False,
        "package_endpoint_enabled": True,
        "approval_scope": "transport_canary_only_no_customer_discovery",
        "blockers": [],
        "post_deploy_proof_required": [
            "PACKAGE_MANIFEST_200_COHORT_AND_404_NON_COHORT",
            "SEGMENT_RANGE_206",
            "TIMESTAMPS_200",
            "BROWSER_PLAYBACK_PASS",
        ],
        "generated_at": operation_time,
    }
    managed = _managed_values(
        packages=packages,
        evidence=evidence,
        state=state,
        manuscript_sha256=validated["manuscript_sha256"],
        legacy_descriptor="",
        hidden_descriptor=hidden_descriptor,
        package_canary=canary,
    )
    approval_updates = {
        "audiobook_package_canary": copy.deepcopy(canary),
        "audiobook_enabled": False,
        "audio_public_release": "PUBLIC_AUDIO_PACKAGE_CANARY_ONLY",
        "audio_qa_status": "QA_PASSED",
        "upload_status": "UPLOADED_CHECKSUM_VERIFIED_PRIMARY_AND_DR",
        "release_blockers": ["PRODUCTION_ENDPOINT_AND_BROWSER_PROOF_REQUIRED"],
    }
    result = mutate_mirrors(
        repo_root,
        slug,
        managed,
        generated_at=operation_time,
        apply=apply,
        expected_fingerprint=fingerprint,
        approval_evidence_updates=approval_updates,
    )
    result.update(
        {
            "status": (
                "NEW_TITLE_PACKAGE_CANARY_STAGED"
                if apply
                else "NEW_TITLE_PACKAGE_CANARY_VALIDATED"
            ),
            "rollout_percentage": 5,
            "candidate_release_descriptor_sha256": candidate_descriptor,
            "hidden_release_descriptor_sha256": hidden_descriptor,
            "hidden_before_proof": proof,
            "audio_approval_flags_changed": False,
            "ordinary_public_audio_remains_hidden": True,
        }
    )
    return result


def set_rollout(
    repo_root: Path,
    slug: str,
    percentage: int,
    *,
    generated_at: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    if isinstance(percentage, bool) or percentage not in ROLLOUT_PERCENTAGES:
        raise ReleasePointerError("rollout percentage must be one of 0, 5, 25, 100")
    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    state = _state_from_publication(context, slug)
    if state is None:
        raise ReleasePointerError("No active release state exists")
    if state["status"] != "ACTIVE":
        raise ReleasePointerError(
            "Inactive release state must be explicitly reactivated before rollout"
        )
    canary = context["public_book"].get("audiobook_package_canary")
    if (
        isinstance(canary, Mapping)
        and canary.get("schema_version") == NEW_TITLE_CANARY_SCHEMA
        and percentage != 0
    ):
        raise ReleasePointerError(
            "New-title canary may only roll back to 0; advancing requires "
            "dedicated production endpoint, Range, timestamps, and browser proof"
        )
    packages = copy.deepcopy(context["public_book"].get("audiobook_packages") or {})
    evidence = copy.deepcopy(context["public_book"].get("audiobook_package_release_evidence") or {})
    candidate = str(state.get("candidate_release_descriptor_sha256") or "")
    manuscript_sha256 = require_sha256(
        context["public_book"].get("audiobook_manuscript_sha256"),
        "controlled audiobook manuscript",
    )
    if percentage in {5, 25, 100}:
        if not candidate or candidate not in packages:
            raise ReleasePointerError("No package-v2 candidate is staged")
        _eligible_evidence(evidence, candidate)
        validate_package_against_publication(
            packages[candidate],
            context,
            slug=slug,
            expected_manuscript_sha256=manuscript_sha256,
        )

    if percentage == 100:
        previous_active = state["active_release_descriptor_sha256"]
        retained = _unique_limited(
            [
                candidate,
                previous_active,
                *[
                    value
                    for value in state["retained_release_descriptor_sha256s"]
                    if value not in {candidate, previous_active}
                ],
            ]
        )
        state = build_active_release_state(
            slug=slug,
            active_release_descriptor_sha256=candidate,
            retained_release_descriptor_sha256s=retained,
        )
    else:
        retained = list(state["retained_release_descriptor_sha256s"])
        state = build_active_release_state(
            slug=slug,
            active_release_descriptor_sha256=state["active_release_descriptor_sha256"],
            retained_release_descriptor_sha256s=retained,
            candidate_release_descriptor_sha256=candidate,
            rollout_percentage=percentage,
            rollout_salt=state["rollout"]["salt"],
        )
    packages = {key: value for key, value in packages.items() if key in state["retained_release_descriptor_sha256s"]}
    evidence = {key: value for key, value in evidence.items() if key in state["retained_release_descriptor_sha256s"]}
    _validate_retained_packages(
        packages,
        evidence,
        context,
        state["retained_release_descriptor_sha256s"],
        slug=slug,
        manuscript_sha256=manuscript_sha256,
    )
    legacy = str(
        context["public_book"].get("audiobook_legacy_release_descriptor_sha256")
        or ""
    ).strip().lower()
    if legacy:
        legacy = require_sha256(legacy, "legacy release descriptor")
    package_canary = context["public_book"].get("audiobook_package_canary")
    if (
        percentage == 0
        and isinstance(package_canary, Mapping)
        and package_canary.get("schema_version") == NEW_TITLE_CANARY_SCHEMA
    ):
        package_canary = copy.deepcopy(dict(package_canary))
        package_canary.update(
            {
                "status": "ROLLED_BACK_TO_HIDDEN",
                "rollout_percentage": 0,
                "package_endpoint_enabled": False,
                "rolled_back_at": generated_at or utc_now(),
            }
        )
    managed = _managed_values(
        packages=packages,
        evidence=evidence,
        state=state,
        manuscript_sha256=manuscript_sha256,
        legacy_descriptor=legacy,
        hidden_descriptor=str(
            context["public_book"].get(
                "audiobook_hidden_release_descriptor_sha256"
            )
            or ""
        ),
        package_canary=package_canary,
    )
    result = mutate_mirrors(
        repo_root,
        slug,
        managed,
        generated_at=generated_at or utc_now(),
        apply=apply,
        expected_fingerprint=publication_fingerprint(context),
        approval_evidence_updates=(
            {
                "audiobook_package_canary": copy.deepcopy(dict(package_canary)),
                "audiobook_enabled": False,
                "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
                "release_blockers": ["PACKAGE_CANARY_ROLLED_BACK_TO_HIDDEN"],
            }
            if (
                percentage == 0
                and isinstance(package_canary, Mapping)
                and package_canary.get("schema_version")
                == NEW_TITLE_CANARY_SCHEMA
            )
            else None
        ),
    )
    result["status"] = (
        "CANDIDATE_PROMOTED" if percentage == 100 and apply
        else "ROLLOUT_UPDATED" if apply
        else "ROLLOUT_VALIDATED"
    )
    result["requested_percentage"] = percentage
    return result


def rollback_release(
    repo_root: Path,
    slug: str,
    target: str,
    *,
    generated_at: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    if target not in {"legacy", "previous"}:
        raise ReleasePointerError("rollback target must be legacy or previous")
    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    state = _state_from_publication(context, slug)
    if state is None:
        raise ReleasePointerError("No active release state exists")
    if state["status"] != "ACTIVE":
        raise ReleasePointerError(
            "Inactive release state must be explicitly reactivated before rollback"
        )
    active = state["active_release_descriptor_sha256"]
    legacy = str(
        context["public_book"].get("audiobook_legacy_release_descriptor_sha256")
        or ""
    ).strip().lower()
    if legacy:
        legacy = require_sha256(legacy, "legacy release descriptor")
    if target == "legacy":
        if not legacy:
            raise ReleasePointerError("No approved legacy release is retained")
        selected = legacy
    elif state.get("candidate_release_descriptor_sha256"):
        selected = active
    else:
        previous = [value for value in state["retained_release_descriptor_sha256s"] if value != active]
        if not previous:
            raise ReleasePointerError("No previous approved release is retained")
        selected = previous[0]

    packages = copy.deepcopy(context["public_book"].get("audiobook_packages") or {})
    evidence = copy.deepcopy(context["public_book"].get("audiobook_package_release_evidence") or {})
    manuscript_sha256 = require_sha256(
        context["public_book"].get("audiobook_manuscript_sha256"),
        "controlled audiobook manuscript",
    )
    if selected in packages:
        _eligible_evidence(evidence, selected)
        validate_package_against_publication(
            packages[selected],
            context,
            slug=slug,
            expected_manuscript_sha256=manuscript_sha256,
        )
    elif selected != legacy:
        raise ReleasePointerError("Rollback target has no retained approved package")
    retained = _unique_limited(
        [
            selected,
            active,
            *[
                value
                for value in state["retained_release_descriptor_sha256s"]
                if value
                not in {
                    selected,
                    active,
                    state.get("candidate_release_descriptor_sha256"),
                }
            ],
        ]
    )
    state = build_active_release_state(
        slug=slug,
        active_release_descriptor_sha256=selected,
        retained_release_descriptor_sha256s=retained,
    )
    packages = {key: value for key, value in packages.items() if key in retained}
    evidence = {key: value for key, value in evidence.items() if key in retained}
    _validate_retained_packages(
        packages,
        evidence,
        context,
        retained,
        slug=slug,
        manuscript_sha256=manuscript_sha256,
    )
    managed = _managed_values(
        packages=packages,
        evidence=evidence,
        state=state,
        manuscript_sha256=manuscript_sha256,
        legacy_descriptor=legacy,
        hidden_descriptor=str(
            context["public_book"].get(
                "audiobook_hidden_release_descriptor_sha256"
            )
            or ""
        ),
        package_canary=context["public_book"].get("audiobook_package_canary"),
    )
    result = mutate_mirrors(
        repo_root,
        slug,
        managed,
        generated_at=generated_at or utc_now(),
        apply=apply,
        expected_fingerprint=publication_fingerprint(context),
    )
    result["status"] = "ROLLBACK_APPLIED" if apply else "ROLLBACK_VALIDATED"
    result["rollback_target"] = target
    result["selected_release_descriptor_sha256"] = selected
    return result


def deactivate_release(
    repo_root: Path,
    slug: str,
    *,
    generated_at: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Disable package-v2 selection without changing audiobook approval flags."""

    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    state = _state_from_publication(context, slug)
    if state is None:
        raise ReleasePointerError("No active release state exists")
    managed = _managed_values_from_context(context, state=state)
    if state["status"] == "INACTIVE":
        return {
            "applied": False,
            "slug": slug,
            "status": "RELEASE_ALREADY_INACTIVE",
            "active_release_descriptor_sha256": state[
                "active_release_descriptor_sha256"
            ],
            "audio_approval_flags_changed": False,
            "files": [],
        }
    inactive_state = build_active_release_state(
        slug=slug,
        active_release_descriptor_sha256=state[
            "active_release_descriptor_sha256"
        ],
        retained_release_descriptor_sha256s=state[
            "retained_release_descriptor_sha256s"
        ],
        candidate_release_descriptor_sha256=state[
            "candidate_release_descriptor_sha256"
        ],
        rollout_percentage=state["rollout"]["percentage"],
        rollout_salt=state["rollout"]["salt"],
        status="INACTIVE",
    )
    operation_time = generated_at or utc_now()
    canary = context["public_book"].get("audiobook_package_canary")
    approval_updates = None
    if (
        isinstance(canary, Mapping)
        and canary.get("schema_version") == NEW_TITLE_CANARY_SCHEMA
    ):
        canary = copy.deepcopy(dict(canary))
        canary.update(
            {
                "status": "REVOKED",
                "package_endpoint_enabled": False,
                "revoked_at": operation_time,
            }
        )
        managed["audiobook_package_canary"] = canary
        approval_updates = {
            "audiobook_package_canary": copy.deepcopy(canary),
            "audiobook_enabled": False,
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
            "release_blockers": ["PACKAGE_CANARY_REVOKED"],
        }
    result = mutate_mirrors(
        repo_root,
        slug,
        {**managed, "audiobook_active_release": inactive_state},
        generated_at=operation_time,
        apply=apply,
        expected_fingerprint=publication_fingerprint(context),
        approval_evidence_updates=approval_updates,
    )
    result["status"] = (
        "RELEASE_DEACTIVATED" if apply else "RELEASE_DEACTIVATION_VALIDATED"
    )
    result["active_release_descriptor_sha256"] = inactive_state[
        "active_release_descriptor_sha256"
    ]
    result["audio_approval_flags_changed"] = False
    return result


def reactivate_release(
    repo_root: Path,
    slug: str,
    *,
    generated_at: str | None = None,
    apply: bool = False,
) -> dict[str, Any]:
    """Reactivate only a still-approved, fully receipt-bound package pointer."""

    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    state = _state_from_publication(context, slug)
    if state is None:
        raise ReleasePointerError("No active release state exists")
    if state["status"] != "INACTIVE":
        raise ReleasePointerError("Release state is already active")
    _validate_current_audio_release_approval(context)
    _validate_reader_publication_truth(context, slug)
    packages = context["public_book"].get("audiobook_packages") or {}
    evidence = context["public_book"].get("audiobook_package_release_evidence") or {}
    if not isinstance(packages, Mapping) or not isinstance(evidence, Mapping):
        raise ReleasePointerError("Existing package metadata is not canonical")
    manuscript_sha256 = require_sha256(
        context["public_book"].get("audiobook_manuscript_sha256"),
        "controlled audiobook manuscript",
    )
    retained = list(state["retained_release_descriptor_sha256s"])
    _validate_retained_packages(
        packages,
        evidence,
        context,
        retained,
        slug=slug,
        manuscript_sha256=manuscript_sha256,
    )
    active = state["active_release_descriptor_sha256"]
    legacy = str(
        context["public_book"].get("audiobook_legacy_release_descriptor_sha256")
        or ""
    ).strip().lower()
    if active not in packages:
        if not legacy or active != require_sha256(
            legacy,
            "legacy release descriptor",
        ):
            raise ReleasePointerError(
                "Inactive active pointer is not a retained approved package"
            )
        identity = derive_legacy_release_identity(context, slug)
        if sha256_bytes(canonical_json_bytes(identity)) != active:
            raise ReleasePointerError(
                "Inactive legacy pointer no longer matches controlled audio truth"
            )
    active_state = build_active_release_state(
        slug=slug,
        active_release_descriptor_sha256=active,
        retained_release_descriptor_sha256s=retained,
        candidate_release_descriptor_sha256=state[
            "candidate_release_descriptor_sha256"
        ],
        rollout_percentage=state["rollout"]["percentage"],
        rollout_salt=state["rollout"]["salt"],
        status="ACTIVE",
    )
    result = mutate_mirrors(
        repo_root,
        slug,
        _managed_values_from_context(context, state=active_state),
        generated_at=generated_at or utc_now(),
        apply=apply,
        expected_fingerprint=publication_fingerprint(context),
    )
    result["status"] = (
        "RELEASE_REACTIVATED" if apply else "RELEASE_REACTIVATION_VALIDATED"
    )
    result["active_release_descriptor_sha256"] = active
    result["audio_approval_flags_changed"] = False
    return result


def release_status(repo_root: Path, slug: str) -> dict[str, Any]:
    """Validate and report release-pointer state without mutating the catalog."""

    context = load_mirrored_publication(repo_root, slug)
    _verify_controlled_checksums(context)
    state = _state_from_publication(context, slug)
    if state is None:
        return {
            "status": "NO_ACTIVE_RELEASE_STATE",
            "slug": slug,
            "active_release_descriptor_sha256": "",
            "candidate_release_descriptor_sha256": "",
            "retained_release_descriptor_sha256s": [],
            "rollout": {"percentage": 0, "salt": ""},
            "package_presence": {},
            "evidence_presence": {},
            "blockers": ["ACTIVE_RELEASE_STATE_MISSING"],
        }
    for field in MANAGED_FIELDS:
        if context["public_book"].get(field) != context["reader_manifest"].get(field):
            raise ReleasePointerError(
                f"Controlled public and reader release metadata diverge: {field}"
            )
    packages = context["public_book"].get("audiobook_packages") or {}
    evidence = context["public_book"].get("audiobook_package_release_evidence") or {}
    if not isinstance(packages, Mapping) or not isinstance(evidence, Mapping):
        raise ReleasePointerError("Existing package metadata is not canonical")
    manuscript_sha256 = require_sha256(
        context["public_book"].get("audiobook_manuscript_sha256"),
        "controlled audiobook manuscript",
    )
    retained = list(state["retained_release_descriptor_sha256s"])
    _validate_retained_packages(
        packages,
        evidence,
        context,
        retained,
        slug=slug,
        manuscript_sha256=manuscript_sha256,
    )
    inactive = state["status"] == "INACTIVE"
    canary = context["public_book"].get("audiobook_package_canary")
    is_new_title_canary = bool(
        isinstance(canary, Mapping)
        and canary.get("schema_version") == NEW_TITLE_CANARY_SCHEMA
    )
    if is_new_title_canary:
        canary_status = str(canary.get("status") or "")
        if inactive or canary_status == "REVOKED":
            status = "NEW_TITLE_TRANSPORT_CANARY_REVOKED"
            blockers = ["PACKAGE_CANARY_REVOKED"]
        elif canary_status == "ROLLED_BACK_TO_HIDDEN":
            status = "NEW_TITLE_TRANSPORT_CANARY_ROLLED_BACK"
            blockers = ["PACKAGE_CANARY_ROLLED_BACK_TO_HIDDEN"]
        else:
            status = "NEW_TITLE_TRANSPORT_CANARY_ACTIVE"
            blockers = list(canary.get("post_deploy_proof_required") or [])
    else:
        status = (
            "RELEASE_POINTER_INACTIVE" if inactive else "RELEASE_POINTER_VALID"
        )
        blockers = ["ACTIVE_RELEASE_STATE_INACTIVE"] if inactive else []
    return {
        "status": status,
        "release_state_status": state["status"],
        "slug": slug,
        "active_release_descriptor_sha256": state[
            "active_release_descriptor_sha256"
        ],
        "candidate_release_descriptor_sha256": state[
            "candidate_release_descriptor_sha256"
        ],
        "retained_release_descriptor_sha256s": retained,
        "rollout": copy.deepcopy(state["rollout"]),
        "package_presence": {
            descriptor: descriptor in packages for descriptor in retained
        },
        "evidence_presence": {
            descriptor: descriptor in evidence for descriptor in retained
        },
        "transport_canary": is_new_title_canary,
        "ordinary_public_audio_hidden": bool(is_new_title_canary),
        "canary_status": (
            str(canary.get("status") or "")
            if isinstance(canary, Mapping)
            else ""
        ),
        "post_deploy_proof_required": (
            list(canary.get("post_deploy_proof_required") or [])
            if isinstance(canary, Mapping)
            else []
        ),
        "blockers": blockers,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage = subparsers.add_parser("stage", help="Validate and stage one package-v2 candidate.")
    stage.add_argument("--slug", required=True)
    stage.add_argument("--package", type=Path, required=True)
    stage.add_argument("--release-descriptor", type=Path, required=True)
    stage.add_argument("--primary-receipt", type=Path, required=True)
    stage.add_argument("--replica-receipt", type=Path, required=True)
    stage.add_argument("--primary-release-manifest-receipt", type=Path, required=True)
    stage.add_argument("--replica-release-manifest-receipt", type=Path, required=True)
    stage.add_argument("--expected-manuscript-sha256", default="")
    stage.add_argument("--legacy-descriptor", default="")
    stage.add_argument("--rollout-salt", required=True)
    stage.add_argument("--apply", action="store_true")

    activate_initial = subparsers.add_parser(
        "activate-initial",
        help=(
            "Atomically bind the first fully approved package pointer without "
            "changing public audio approval flags."
        ),
    )
    activate_initial.add_argument("--slug", required=True)
    activate_initial.add_argument("--package", type=Path, required=True)
    activate_initial.add_argument("--release-descriptor", type=Path, required=True)
    activate_initial.add_argument("--primary-receipt", type=Path, required=True)
    activate_initial.add_argument("--replica-receipt", type=Path, required=True)
    activate_initial.add_argument(
        "--primary-release-manifest-receipt",
        type=Path,
        required=True,
    )
    activate_initial.add_argument(
        "--replica-release-manifest-receipt",
        type=Path,
        required=True,
    )
    activate_initial.add_argument("--expected-manuscript-sha256", default="")
    activate_initial.add_argument("--apply", action="store_true")

    new_title_canary = subparsers.add_parser(
        "activate-new-title-canary",
        help=(
            "Atomically stage a first package at 5%% against a deterministic "
            "no-audio fallback; ordinary catalog audio remains hidden."
        ),
    )
    new_title_canary.add_argument("--slug", required=True)
    new_title_canary.add_argument("--package", type=Path, required=True)
    new_title_canary.add_argument(
        "--release-descriptor", type=Path, required=True
    )
    new_title_canary.add_argument("--primary-receipt", type=Path, required=True)
    new_title_canary.add_argument("--replica-receipt", type=Path, required=True)
    new_title_canary.add_argument(
        "--primary-release-manifest-receipt", type=Path, required=True
    )
    new_title_canary.add_argument(
        "--replica-release-manifest-receipt", type=Path, required=True
    )
    new_title_canary.add_argument(
        "--hidden-before-proof", type=Path, required=True
    )
    new_title_canary.add_argument(
        "--hidden-rollback-descriptor", type=Path, required=True
    )
    new_title_canary.add_argument("--rollout-salt", required=True)
    new_title_canary.add_argument(
        "--expected-manuscript-sha256", required=True
    )
    for argument in (
        "package",
        "release-descriptor",
        "primary-receipt",
        "replica-receipt",
        "primary-release-manifest-receipt",
        "replica-release-manifest-receipt",
        "hidden-before-proof",
        "rollback-descriptor",
    ):
        new_title_canary.add_argument(
            f"--expected-{argument}-sha256",
            required=True,
        )
    new_title_canary.add_argument("--apply", action="store_true")

    rollout = subparsers.add_parser("rollout", help="Set 0/5/25 or promote at 100.")
    rollout.add_argument("--slug", required=True)
    rollout.add_argument("--percentage", type=int, choices=sorted(ROLLOUT_PERCENTAGES), required=True)
    rollout.add_argument("--apply", action="store_true")

    rollback = subparsers.add_parser("rollback", help="Rollback to the legacy or previous approved release.")
    rollback.add_argument("--slug", required=True)
    rollback.add_argument("--to", choices=("legacy", "previous"), required=True)
    rollback.add_argument("--apply", action="store_true")

    deactivate = subparsers.add_parser(
        "deactivate",
        aliases=["revoke"],
        help="Fail closed package-v2 selection without changing audio approval flags.",
    )
    deactivate.add_argument("--slug", required=True)
    deactivate.add_argument("--apply", action="store_true")

    reactivate = subparsers.add_parser(
        "reactivate",
        help="Reactivate a still-approved, fully receipt-bound package pointer.",
    )
    reactivate.add_argument("--slug", required=True)
    reactivate.add_argument("--apply", action="store_true")

    status = subparsers.add_parser("status", help="Validate release pointers without mutation.")
    status.add_argument("--slug", required=True)

    bind_legacy = subparsers.add_parser(
        "bind-legacy",
        help="Derive and bind an already-approved legacy audio identity.",
    )
    bind_legacy.add_argument("--slug", required=True)
    bind_legacy.add_argument("--apply", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in {
            "stage",
            "activate-initial",
            "activate-new-title-canary",
        }:
            package_path = args.package.resolve()
            primary_path = args.primary_receipt.resolve()
            replica_path = args.replica_receipt.resolve()
            primary_manifest_path = args.primary_release_manifest_receipt.resolve()
            replica_manifest_path = args.replica_release_manifest_receipt.resolve()
            common = {
                "expected_manuscript_sha256": args.expected_manuscript_sha256,
                "release_manifest_sha256": sha256_file(package_path),
                "release_manifest_size_bytes": package_path.stat().st_size,
                "apply": args.apply,
                "primary_receipt_sha256": sha256_file(primary_path),
                "replica_receipt_sha256": sha256_file(replica_path),
                "primary_release_manifest_receipt_sha256": sha256_file(
                    primary_manifest_path
                ),
                "replica_release_manifest_receipt_sha256": sha256_file(
                    replica_manifest_path
                ),
            }
            positional = (
                args.repo_root.resolve(),
                args.slug,
                read_json(package_path),
                read_json(args.release_descriptor.resolve()),
                read_json(primary_path),
                read_json(replica_path),
                read_json(primary_manifest_path),
                read_json(replica_manifest_path),
            )
            if args.command == "stage":
                result = stage_candidate(
                    *positional,
                    rollout_salt=args.rollout_salt,
                    legacy_descriptor=args.legacy_descriptor,
                    **common,
                )
            elif args.command == "activate-initial":
                result = activate_initial_release(*positional, **common)
            else:
                package_document = positional[2]
                release_descriptor_document = positional[3]
                hidden_before_path = args.hidden_before_proof.resolve()
                rollback_path = args.hidden_rollback_descriptor.resolve()
                exact_paths = {
                    "package": package_path,
                    "release_descriptor": args.release_descriptor.resolve(),
                    "primary_receipt": primary_path,
                    "replica_receipt": replica_path,
                    "primary_release_manifest_receipt": primary_manifest_path,
                    "replica_release_manifest_receipt": replica_manifest_path,
                    "hidden_before_proof": hidden_before_path,
                }
                for label, path in exact_paths.items():
                    expected = require_sha256(
                        getattr(args, f"expected_{label}_sha256"),
                        f"expected {label.replace('_', ' ')} SHA-256",
                    )
                    if sha256_file(path) != expected:
                        raise ReleasePointerError(
                            f"Expected {label.replace('_', ' ')} SHA-256 "
                            "does not match the exact file"
                        )
                result = activate_new_title_package_canary(
                    args.repo_root.resolve(),
                    args.slug,
                    package_document,
                    release_descriptor_document,
                    positional[4],
                    positional[5],
                    positional[6],
                    positional[7],
                    read_json(hidden_before_path),
                    read_json(rollback_path),
                    rollout_salt=args.rollout_salt,
                    expected_manuscript_sha256=args.expected_manuscript_sha256,
                    release_manifest_sha256=common[
                        "release_manifest_sha256"
                    ],
                    release_manifest_size_bytes=common[
                        "release_manifest_size_bytes"
                    ],
                    expected_package_sha256=args.expected_package_sha256,
                    expected_release_descriptor_sha256=(
                        args.expected_release_descriptor_sha256
                    ),
                    expected_primary_receipt_sha256=(
                        args.expected_primary_receipt_sha256
                    ),
                    expected_replica_receipt_sha256=(
                        args.expected_replica_receipt_sha256
                    ),
                    expected_primary_release_manifest_receipt_sha256=(
                        args.expected_primary_release_manifest_receipt_sha256
                    ),
                    expected_replica_release_manifest_receipt_sha256=(
                        args.expected_replica_release_manifest_receipt_sha256
                    ),
                    expected_hidden_before_proof_sha256=(
                        args.expected_hidden_before_proof_sha256
                    ),
                    expected_rollback_descriptor_sha256=(
                        args.expected_rollback_descriptor_sha256
                    ),
                    apply=args.apply,
                )
        elif args.command == "rollout":
            result = set_rollout(
                args.repo_root.resolve(),
                args.slug,
                args.percentage,
                apply=args.apply,
            )
        elif args.command == "rollback":
            result = rollback_release(
                args.repo_root.resolve(),
                args.slug,
                args.to,
                apply=args.apply,
            )
        elif args.command in {"deactivate", "revoke"}:
            result = deactivate_release(
                args.repo_root.resolve(),
                args.slug,
                apply=args.apply,
            )
        elif args.command == "reactivate":
            result = reactivate_release(
                args.repo_root.resolve(),
                args.slug,
                apply=args.apply,
            )
        elif args.command == "bind-legacy":
            result = bind_legacy_release(
                args.repo_root.resolve(),
                args.slug,
                apply=args.apply,
            )
        else:
            result = release_status(args.repo_root.resolve(), args.slug)
    except ReleasePointerError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
