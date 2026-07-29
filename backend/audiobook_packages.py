"""Canonical helpers for immutable Earnalism audiobook packages.

This module is deliberately independent from the runtime server and controlled
publication state.  It validates release packages, derives content-addressed
package versions, and selects an already-approved active release for a sticky
rollout cohort.  It does not upload, publish, or mutate release state.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


PACKAGE_SCHEMA_VERSION = "audiobook_package_manifest.v2"
ACTIVE_RELEASE_SCHEMA_VERSION = "audiobook_active_release.v1"
MAX_SEGMENT_DURATION_MS = 12 * 60 * 1000
ROLLOUT_PERCENTAGES = frozenset({0, 5, 25, 100})

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,119}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_PACKAGE_VERSION_RE = re.compile(r"^sha256-([a-f0-9]{64})$")
_STORAGE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
_BUCKET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")

_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "slug",
        "package_version",
        "release_evidence_version",
        "release_descriptor_sha256",
        "source_sha256",
        "manuscript_sha256",
        "duration_ms",
        "segment_count",
        "word_count",
        "paragraph_count",
        "sync_tier",
        "highlight_sync_enabled",
        "tracks",
    }
)
_TRACK_FIELDS = frozenset(
    {
        "id",
        "chapter_id",
        "order",
        "title",
        "start_word",
        "end_word",
        "start_paragraph",
        "end_paragraph",
        "chunks",
    }
)
_SEGMENT_FIELDS = frozenset(
    {
        "segment_id",
        "order",
        "start_word",
        "end_word",
        "start_paragraph",
        "end_paragraph",
        "cumulative_start_ms",
        "duration_ms",
        "assets",
    }
)
_ASSET_FIELDS = frozenset(
    {"sha256", "size_bytes", "mime_type", "storage", "replicas"}
)
_STORAGE_FIELDS = frozenset({"store", "bucket", "key", "version_id"})
_ASSET_MIME_TYPES = {
    "audio": "audio/mpeg",
    "timestamps": "application/json",
    "vtt": "text/vtt",
    "metadata": "application/json",
}


class AudiobookPackageValidationError(ValueError):
    """Raised when an immutable audiobook package is not internally valid."""


class AudiobookReleaseSelectionError(ValueError):
    """Raised when an active release cannot be selected or requested safely."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AudiobookPackageValidationError(f"{label} must be an object")
    return value


def _strict_fields(
    value: Mapping[str, Any],
    allowed: frozenset[str],
    required: frozenset[str],
    label: str,
) -> None:
    unknown = sorted(set(value) - allowed)
    missing = sorted(required - set(value))
    if unknown:
        raise AudiobookPackageValidationError(
            f"{label} contains unsupported fields: {', '.join(unknown)}"
        )
    if missing:
        raise AudiobookPackageValidationError(
            f"{label} is missing required fields: {', '.join(missing)}"
        )


def _nonempty_string(value: Any, label: str, *, max_length: int = 1000) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AudiobookPackageValidationError(
            f"{label} must be a non-empty canonical string"
        )
    if len(value) > max_length:
        raise AudiobookPackageValidationError(f"{label} is too long")
    return value


def _identifier(value: Any, label: str) -> str:
    candidate = _nonempty_string(value, label, max_length=120)
    if not _IDENTIFIER_RE.fullmatch(candidate):
        raise AudiobookPackageValidationError(f"{label} is not a valid identifier")
    return candidate


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise AudiobookPackageValidationError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _integer(
    value: Any,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise AudiobookPackageValidationError(
            f"{label} must be an integer >= {minimum}"
        )
    if maximum is not None and value > maximum:
        raise AudiobookPackageValidationError(
            f"{label} must be an integer <= {maximum}"
        )
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise AudiobookPackageValidationError(f"{label} must be an array")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable RFC-8259-compatible JSON bytes for content addressing."""

    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise AudiobookPackageValidationError(
            f"package is not canonical-JSON serializable: {exc}"
        ) from exc
    return encoded.encode("utf-8")


def canonical_package_sha256(package: Mapping[str, Any]) -> str:
    """Hash every package field except the self-referential package_version."""

    payload = copy.deepcopy(dict(_mapping(package, "package")))
    payload.pop("package_version", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def expected_package_version(package: Mapping[str, Any]) -> str:
    return f"sha256-{canonical_package_sha256(package)}"


def with_canonical_package_version(package: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deep-copied package carrying its canonical package_version."""

    payload = copy.deepcopy(dict(_mapping(package, "package")))
    payload["package_version"] = expected_package_version(payload)
    return payload


def immutable_release_prefix(slug: str, release_descriptor_sha256: str) -> str:
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise AudiobookPackageValidationError("slug is not canonical")
    descriptor = _sha256(
        release_descriptor_sha256,
        "release_descriptor_sha256",
    )
    return f"v1/prod/sprint1/{slug}/releases/{descriptor}/"


def _validate_storage(
    value: Any,
    *,
    label: str,
    immutable_prefix: str,
) -> dict[str, str]:
    storage = _mapping(value, label)
    _strict_fields(
        storage,
        _STORAGE_FIELDS,
        _STORAGE_FIELDS,
        label,
    )
    store = _nonempty_string(storage.get("store"), f"{label}.store", max_length=80)
    bucket = _nonempty_string(storage.get("bucket"), f"{label}.bucket", max_length=255)
    key = _nonempty_string(storage.get("key"), f"{label}.key", max_length=1024)
    version_id = _nonempty_string(
        storage.get("version_id"),
        f"{label}.version_id",
        max_length=512,
    )
    if not _STORAGE_NAME_RE.fullmatch(store):
        raise AudiobookPackageValidationError(f"{label}.store is not canonical")
    if not _BUCKET_RE.fullmatch(bucket):
        raise AudiobookPackageValidationError(f"{label}.bucket is not canonical")
    if (
        not key.startswith(immutable_prefix)
        or key.startswith("/")
        or "//" in key
        or any(part in {".", ".."} for part in key.split("/"))
    ):
        raise AudiobookPackageValidationError(
            f"{label}.key must use immutable prefix {immutable_prefix}"
        )
    return {
        "store": store,
        "bucket": bucket,
        "key": key,
        "version_id": version_id,
    }


def _validate_asset(
    value: Any,
    *,
    asset_name: str,
    label: str,
    immutable_prefix: str,
) -> dict[str, Any]:
    asset = _mapping(value, label)
    _strict_fields(asset, _ASSET_FIELDS, _ASSET_FIELDS, label)
    mime_type = _nonempty_string(
        asset.get("mime_type"),
        f"{label}.mime_type",
        max_length=120,
    )
    expected_mime = _ASSET_MIME_TYPES[asset_name]
    if mime_type != expected_mime:
        raise AudiobookPackageValidationError(
            f"{label}.mime_type must be {expected_mime}"
        )
    primary_storage = _validate_storage(
        asset.get("storage"),
        label=f"{label}.storage",
        immutable_prefix=immutable_prefix,
    )
    replicas_raw = _sequence(asset.get("replicas"), f"{label}.replicas")
    if not replicas_raw:
        raise AudiobookPackageValidationError(
            f"{label}.replicas must contain at least one disaster-recovery copy"
        )
    replicas: list[dict[str, str]] = []
    seen_replica_destinations: set[tuple[str, str]] = set()
    for replica_index, replica_value in enumerate(replicas_raw):
        replica_label = f"{label}.replicas[{replica_index}]"
        replica = _validate_storage(
            replica_value,
            label=replica_label,
            immutable_prefix=immutable_prefix,
        )
        if replica["store"] == primary_storage["store"]:
            raise AudiobookPackageValidationError(
                f"{replica_label}.store must differ from primary storage"
            )
        if replica["bucket"] == primary_storage["bucket"]:
            raise AudiobookPackageValidationError(
                f"{replica_label}.bucket must differ from primary storage"
            )
        if replica["key"] != primary_storage["key"]:
            raise AudiobookPackageValidationError(
                f"{replica_label}.key must exactly match the primary immutable key"
            )
        destination = (replica["store"], replica["bucket"])
        if destination in seen_replica_destinations:
            raise AudiobookPackageValidationError(
                f"{replica_label} duplicates another replica destination"
            )
        seen_replica_destinations.add(destination)
        replicas.append(replica)

    return {
        "sha256": _sha256(asset.get("sha256"), f"{label}.sha256"),
        "size_bytes": _integer(
            asset.get("size_bytes"),
            f"{label}.size_bytes",
            minimum=1,
        ),
        "mime_type": mime_type,
        "storage": primary_storage,
        "replicas": replicas,
    }


def validate_audiobook_package(
    package: Mapping[str, Any],
    *,
    expected_slug: str,
    expected_source_sha256: str,
    expected_manuscript_sha256: str,
    expected_release_descriptor_sha256: str,
) -> dict[str, Any]:
    """Validate and return a normalized deep copy of an immutable package.

    Structural and semantic validation intentionally happen together.  JSON
    Schema alone cannot prove the canonical package digest, global word and
    paragraph contiguity, cumulative duration, or storage-key prefix.
    """

    raw = _mapping(package, "package")
    required_top = _TOP_LEVEL_FIELDS - {"sync_tier", "highlight_sync_enabled"}
    _strict_fields(raw, _TOP_LEVEL_FIELDS, required_top, "package")

    if raw.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        raise AudiobookPackageValidationError(
            f"schema_version must be {PACKAGE_SCHEMA_VERSION}"
        )
    slug = raw.get("slug")
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise AudiobookPackageValidationError("slug is not canonical")
    if (
        not isinstance(expected_slug, str)
        or not _SLUG_RE.fullmatch(expected_slug)
        or slug != expected_slug
    ):
        raise AudiobookPackageValidationError("slug does not match controlled truth")

    version = raw.get("package_version")
    if not isinstance(version, str) or not _PACKAGE_VERSION_RE.fullmatch(version):
        raise AudiobookPackageValidationError(
            "package_version must be sha256-<lowercase digest>"
        )
    calculated_version = expected_package_version(raw)
    if version != calculated_version:
        raise AudiobookPackageValidationError(
            "package_version does not match canonical package content"
        )

    source_sha256 = _sha256(raw.get("source_sha256"), "source_sha256")
    manuscript_sha256 = _sha256(
        raw.get("manuscript_sha256"),
        "manuscript_sha256",
    )
    if source_sha256 != _sha256(
        expected_source_sha256,
        "expected_source_sha256",
    ):
        raise AudiobookPackageValidationError(
            "source_sha256 does not match controlled truth"
        )
    if manuscript_sha256 != _sha256(
        expected_manuscript_sha256,
        "expected_manuscript_sha256",
    ):
        raise AudiobookPackageValidationError(
            "manuscript_sha256 does not match controlled truth"
        )

    release_descriptor_sha256 = _sha256(
        raw.get("release_descriptor_sha256"),
        "release_descriptor_sha256",
    )
    if release_descriptor_sha256 != _sha256(
        expected_release_descriptor_sha256,
        "expected_release_descriptor_sha256",
    ):
        raise AudiobookPackageValidationError(
            "release_descriptor_sha256 does not match controlled release truth"
        )
    immutable_prefix = immutable_release_prefix(slug, release_descriptor_sha256)
    release_evidence_version = _identifier(
        raw.get("release_evidence_version"),
        "release_evidence_version",
    )
    duration_ms = _integer(raw.get("duration_ms"), "duration_ms", minimum=1)
    segment_count = _integer(raw.get("segment_count"), "segment_count", minimum=1)
    word_count = _integer(raw.get("word_count"), "word_count", minimum=1)
    paragraph_count = _integer(
        raw.get("paragraph_count"),
        "paragraph_count",
        minimum=1,
    )
    if "sync_tier" in raw:
        _nonempty_string(raw.get("sync_tier"), "sync_tier", max_length=80)
    if "highlight_sync_enabled" in raw and not isinstance(
        raw.get("highlight_sync_enabled"),
        bool,
    ):
        raise AudiobookPackageValidationError(
            "highlight_sync_enabled must be a boolean"
        )

    tracks_raw = _sequence(raw.get("tracks"), "tracks")
    if not tracks_raw:
        raise AudiobookPackageValidationError("tracks must not be empty")

    seen_track_ids: set[str] = set()
    seen_chapter_ids: set[str] = set()
    seen_segment_ids: set[str] = set()
    expected_word = 0
    expected_paragraph = 0
    expected_start_ms = 0
    actual_segment_count = 0

    for track_index, track_value in enumerate(tracks_raw):
        label = f"tracks[{track_index}]"
        track = _mapping(track_value, label)
        _strict_fields(
            track,
            _TRACK_FIELDS,
            _TRACK_FIELDS - {"title"},
            label,
        )
        track_id = _identifier(track.get("id"), f"{label}.id")
        chapter_id = _identifier(track.get("chapter_id"), f"{label}.chapter_id")
        if track_id in seen_track_ids:
            raise AudiobookPackageValidationError(f"{label}.id must be unique")
        if chapter_id in seen_chapter_ids:
            raise AudiobookPackageValidationError(
                f"{label}.chapter_id must be unique"
            )
        seen_track_ids.add(track_id)
        seen_chapter_ids.add(chapter_id)
        if _integer(track.get("order"), f"{label}.order") != track_index:
            raise AudiobookPackageValidationError(
                f"{label}.order must equal its global track index"
            )
        if "title" in track and track.get("title") != "":
            _nonempty_string(track.get("title"), f"{label}.title", max_length=160)

        chunks = _sequence(track.get("chunks"), f"{label}.chunks")
        if not chunks:
            raise AudiobookPackageValidationError(f"{label}.chunks must not be empty")

        track_start_word = _integer(
            track.get("start_word"),
            f"{label}.start_word",
        )
        track_end_word = _integer(track.get("end_word"), f"{label}.end_word")
        track_start_paragraph = _integer(
            track.get("start_paragraph"),
            f"{label}.start_paragraph",
        )
        track_end_paragraph = _integer(
            track.get("end_paragraph"),
            f"{label}.end_paragraph",
        )
        if track_start_word != expected_word:
            raise AudiobookPackageValidationError(
                f"{label}.start_word is not globally contiguous"
            )
        if track_start_paragraph != expected_paragraph:
            raise AudiobookPackageValidationError(
                f"{label}.start_paragraph is not globally contiguous"
            )

        first_segment: Mapping[str, Any] | None = None
        last_segment: Mapping[str, Any] | None = None
        for segment_index, segment_value in enumerate(chunks):
            segment_label = f"{label}.chunks[{segment_index}]"
            segment = _mapping(segment_value, segment_label)
            _strict_fields(
                segment,
                _SEGMENT_FIELDS,
                _SEGMENT_FIELDS,
                segment_label,
            )
            segment_id = _identifier(
                segment.get("segment_id"),
                f"{segment_label}.segment_id",
            )
            if segment_id in seen_segment_ids:
                raise AudiobookPackageValidationError(
                    f"{segment_label}.segment_id must be globally unique"
                )
            seen_segment_ids.add(segment_id)
            if _integer(
                segment.get("order"),
                f"{segment_label}.order",
            ) != segment_index:
                raise AudiobookPackageValidationError(
                    f"{segment_label}.order must equal its chapter segment index"
                )

            start_word = _integer(
                segment.get("start_word"),
                f"{segment_label}.start_word",
            )
            end_word = _integer(
                segment.get("end_word"),
                f"{segment_label}.end_word",
            )
            start_paragraph = _integer(
                segment.get("start_paragraph"),
                f"{segment_label}.start_paragraph",
            )
            end_paragraph = _integer(
                segment.get("end_paragraph"),
                f"{segment_label}.end_paragraph",
            )
            if start_word != expected_word or end_word < start_word:
                raise AudiobookPackageValidationError(
                    f"{segment_label} word boundaries are not globally contiguous"
                )
            if (
                start_paragraph != expected_paragraph
                or end_paragraph < start_paragraph
            ):
                raise AudiobookPackageValidationError(
                    f"{segment_label} paragraph boundaries are not globally contiguous"
                )
            cumulative_start_ms = _integer(
                segment.get("cumulative_start_ms"),
                f"{segment_label}.cumulative_start_ms",
            )
            if cumulative_start_ms != expected_start_ms:
                raise AudiobookPackageValidationError(
                    f"{segment_label}.cumulative_start_ms is not globally contiguous"
                )
            segment_duration = _integer(
                segment.get("duration_ms"),
                f"{segment_label}.duration_ms",
                minimum=1,
                maximum=MAX_SEGMENT_DURATION_MS,
            )

            assets = _mapping(segment.get("assets"), f"{segment_label}.assets")
            expected_asset_names = frozenset(_ASSET_MIME_TYPES)
            _strict_fields(
                assets,
                expected_asset_names,
                expected_asset_names,
                f"{segment_label}.assets",
            )
            for asset_name in sorted(expected_asset_names):
                _validate_asset(
                    assets.get(asset_name),
                    asset_name=asset_name,
                    label=f"{segment_label}.assets.{asset_name}",
                    immutable_prefix=immutable_prefix,
                )

            first_segment = first_segment or segment
            last_segment = segment
            expected_word = end_word + 1
            expected_paragraph = end_paragraph + 1
            expected_start_ms += segment_duration
            actual_segment_count += 1

        assert first_segment is not None and last_segment is not None
        if (
            track_start_word != first_segment["start_word"]
            or track_end_word != last_segment["end_word"]
        ):
            raise AudiobookPackageValidationError(
                f"{label} word bounds do not match its segments"
            )
        if (
            track_start_paragraph != first_segment["start_paragraph"]
            or track_end_paragraph != last_segment["end_paragraph"]
        ):
            raise AudiobookPackageValidationError(
                f"{label} paragraph bounds do not match its segments"
            )

    if actual_segment_count != segment_count:
        raise AudiobookPackageValidationError(
            "segment_count does not match the exact segment list"
        )
    if expected_start_ms != duration_ms:
        raise AudiobookPackageValidationError(
            "duration_ms does not match cumulative segment duration"
        )
    if expected_word != word_count:
        raise AudiobookPackageValidationError(
            "word_count does not match global segment boundaries"
        )
    if expected_paragraph != paragraph_count:
        raise AudiobookPackageValidationError(
            "paragraph_count does not match global segment boundaries"
        )

    normalized = copy.deepcopy(dict(raw))
    normalized["release_evidence_version"] = release_evidence_version
    return normalized


def build_active_release_state(
    *,
    slug: str,
    active_release_descriptor_sha256: str,
    retained_release_descriptor_sha256s: Sequence[str] | None = None,
    candidate_release_descriptor_sha256: str = "",
    rollout_percentage: int = 0,
    rollout_salt: str = "",
    status: str = "ACTIVE",
) -> dict[str, Any]:
    retained = list(retained_release_descriptor_sha256s or [])
    if active_release_descriptor_sha256 not in retained:
        retained.insert(0, active_release_descriptor_sha256)
    if (
        candidate_release_descriptor_sha256
        and candidate_release_descriptor_sha256 not in retained
    ):
        retained.append(candidate_release_descriptor_sha256)
    state = {
        "schema_version": ACTIVE_RELEASE_SCHEMA_VERSION,
        "slug": slug,
        "status": status,
        "active_release_descriptor_sha256": active_release_descriptor_sha256,
        "candidate_release_descriptor_sha256": candidate_release_descriptor_sha256,
        "retained_release_descriptor_sha256s": retained,
        "rollout": {
            "percentage": rollout_percentage,
            "salt": rollout_salt,
        },
    }
    validate_active_release_state(state)
    return state


def validate_active_release_state(state: Mapping[str, Any]) -> dict[str, Any]:
    try:
        raw = dict(state)
    except (TypeError, ValueError) as exc:
        raise AudiobookReleaseSelectionError(
            "active release state must be an object"
        ) from exc
    allowed = {
        "schema_version",
        "slug",
        "status",
        "active_release_descriptor_sha256",
        "candidate_release_descriptor_sha256",
        "retained_release_descriptor_sha256s",
        "rollout",
    }
    if set(raw) != allowed:
        missing = sorted(allowed - set(raw))
        unknown = sorted(set(raw) - allowed)
        detail = []
        if missing:
            detail.append(f"missing {', '.join(missing)}")
        if unknown:
            detail.append(f"unsupported {', '.join(unknown)}")
        raise AudiobookReleaseSelectionError(
            f"active release state fields are invalid: {'; '.join(detail)}"
        )
    if raw.get("schema_version") != ACTIVE_RELEASE_SCHEMA_VERSION:
        raise AudiobookReleaseSelectionError(
            f"schema_version must be {ACTIVE_RELEASE_SCHEMA_VERSION}"
        )
    slug = raw.get("slug")
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise AudiobookReleaseSelectionError("active release slug is not canonical")
    status = raw.get("status")
    if status not in {"ACTIVE", "INACTIVE"}:
        raise AudiobookReleaseSelectionError(
            "active release status must be ACTIVE or INACTIVE"
        )

    active = raw.get("active_release_descriptor_sha256")
    candidate = raw.get("candidate_release_descriptor_sha256")
    if not isinstance(active, str) or not _SHA256_RE.fullmatch(active):
        raise AudiobookReleaseSelectionError(
            "active release descriptor must be a lowercase SHA-256"
        )
    if candidate:
        if not isinstance(candidate, str) or not _SHA256_RE.fullmatch(candidate):
            raise AudiobookReleaseSelectionError(
                "candidate release descriptor must be a lowercase SHA-256"
            )
        if candidate == active:
            raise AudiobookReleaseSelectionError(
                "candidate release must differ from active release"
            )
    elif not isinstance(candidate, str):
        raise AudiobookReleaseSelectionError(
            "candidate release descriptor must be a string"
        )

    retained = raw.get("retained_release_descriptor_sha256s")
    if (
        isinstance(retained, (str, bytes, bytearray))
        or not isinstance(retained, Sequence)
        or not 1 <= len(retained) <= 3
    ):
        raise AudiobookReleaseSelectionError(
            "retained releases must contain current plus at most two releases"
        )
    retained_values = list(retained)
    if len(set(retained_values)) != len(retained_values):
        raise AudiobookReleaseSelectionError("retained releases must be unique")
    if any(
        not isinstance(value, str) or not _SHA256_RE.fullmatch(value)
        for value in retained_values
    ):
        raise AudiobookReleaseSelectionError(
            "retained releases must be lowercase SHA-256 digests"
        )
    if active not in retained_values:
        raise AudiobookReleaseSelectionError(
            "active release must be retained"
        )
    if candidate and candidate not in retained_values:
        raise AudiobookReleaseSelectionError(
            "candidate release must be retained during rollout"
        )

    rollout = raw.get("rollout")
    if not isinstance(rollout, Mapping) or set(rollout) != {"percentage", "salt"}:
        raise AudiobookReleaseSelectionError(
            "rollout must contain exactly percentage and salt"
        )
    percentage = rollout.get("percentage")
    if isinstance(percentage, bool) or percentage not in ROLLOUT_PERCENTAGES:
        raise AudiobookReleaseSelectionError(
            "rollout percentage must be one of 0, 5, 25, 100"
        )
    salt = rollout.get("salt")
    if not isinstance(salt, str) or salt != salt.strip() or len(salt) > 200:
        raise AudiobookReleaseSelectionError(
            "rollout salt must be a canonical string"
        )
    if percentage and not candidate:
        raise AudiobookReleaseSelectionError(
            "non-zero rollout requires a candidate release"
        )
    if candidate and not salt:
        raise AudiobookReleaseSelectionError(
            "candidate rollout requires a non-empty sticky salt"
        )
    return copy.deepcopy(raw)


def deterministic_rollout_bucket(
    *,
    slug: str,
    sticky_key: str,
    salt: str,
) -> int:
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise AudiobookReleaseSelectionError("rollout slug is not canonical")
    if (
        not isinstance(sticky_key, str)
        or not sticky_key
        or sticky_key != sticky_key.strip()
        or len(sticky_key) > 512
    ):
        raise AudiobookReleaseSelectionError(
            "sticky rollout key must be a non-empty canonical string"
        )
    if not isinstance(salt, str) or not salt or salt != salt.strip():
        raise AudiobookReleaseSelectionError(
            "rollout salt must be a non-empty canonical string"
        )
    material = f"{salt}\0{slug}\0{sticky_key}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % 100


def select_release_descriptor_sha256(
    state: Mapping[str, Any],
    *,
    sticky_key: str,
) -> str:
    validated = validate_active_release_state(state)
    if validated["status"] != "ACTIVE":
        raise AudiobookReleaseSelectionError("audiobook release state is inactive")
    active = validated["active_release_descriptor_sha256"]
    candidate = validated["candidate_release_descriptor_sha256"]
    percentage = validated["rollout"]["percentage"]
    if percentage == 0:
        return active
    if percentage == 100:
        return candidate
    bucket = deterministic_rollout_bucket(
        slug=validated["slug"],
        sticky_key=sticky_key,
        salt=validated["rollout"]["salt"],
    )
    return candidate if bucket < percentage else active


def require_selected_release(
    state: Mapping[str, Any],
    *,
    requested_release_descriptor_sha256: str,
    sticky_key: str,
) -> str:
    if (
        not isinstance(requested_release_descriptor_sha256, str)
        or not _SHA256_RE.fullmatch(requested_release_descriptor_sha256)
    ):
        raise AudiobookReleaseSelectionError(
            "requested release descriptor must be a lowercase SHA-256"
        )
    selected = select_release_descriptor_sha256(state, sticky_key=sticky_key)
    if requested_release_descriptor_sha256 != selected:
        raise AudiobookReleaseSelectionError(
            "requested audiobook release is inactive or stale for this cohort"
        )
    return selected


# Concise aliases for callers that treat the module as a package contract.
validate_package = validate_audiobook_package
package_sha256 = canonical_package_sha256
