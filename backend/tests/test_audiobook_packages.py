import json
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audiobook_packages import (  # noqa: E402
    ACTIVE_RELEASE_SCHEMA_VERSION,
    PACKAGE_SCHEMA_VERSION,
    AudiobookPackageValidationError,
    AudiobookReleaseSelectionError,
    build_active_release_state,
    canonical_package_sha256,
    deterministic_rollout_bucket,
    expected_package_version,
    immutable_release_prefix,
    require_selected_release,
    select_release_descriptor_sha256,
    validate_active_release_state,
    validate_audiobook_package,
    with_canonical_package_version,
)


SLUG = "muchiram-gurer-jibanchorit"
SOURCE_SHA256 = "1" * 64
MANUSCRIPT_SHA256 = "2" * 64
RELEASE_DESCRIPTOR_SHA256 = "3" * 64
ACTIVE_RELEASE_SHA256 = "a" * 64
CANDIDATE_RELEASE_SHA256 = "b" * 64
PREVIOUS_RELEASE_SHA256 = "c" * 64


def _asset(asset_name, segment_id):
    suffixes = {
        "audio": ("mp3", "audio/mpeg"),
        "timestamps": ("timestamps.json", "application/json"),
        "vtt": ("vtt", "text/vtt"),
        "metadata": ("metadata.json", "application/json"),
    }
    suffix, mime_type = suffixes[asset_name]
    directory = "audio" if asset_name == "audio" else "sidecars"
    immutable_key = (
        f"{immutable_release_prefix(SLUG, RELEASE_DESCRIPTOR_SHA256)}"
        f"{directory}/{segment_id}.{suffix}"
    )
    return {
        "sha256": {
            "audio": "4",
            "timestamps": "5",
            "vtt": "6",
            "metadata": "7",
        }[asset_name]
        * 64,
        "size_bytes": {
            "audio": 100_000,
            "timestamps": 4_000,
            "vtt": 3_000,
            "metadata": 2_000,
        }[asset_name],
        "mime_type": mime_type,
        "storage": {
            "store": "production_primary",
            "bucket": "earnalism-prod-audio",
            "key": immutable_key,
            "version_id": f"version-{segment_id}-{asset_name}",
        },
        "replicas": [
            {
                "store": "production_dr",
                "bucket": "earnalism-prod-audio-dr",
                "key": immutable_key,
                "version_id": f"dr-version-{segment_id}-{asset_name}",
            }
        ],
    }


def _segment(
    *,
    segment_id,
    order,
    start_word,
    end_word,
    start_paragraph,
    end_paragraph,
    cumulative_start_ms,
    duration_ms,
):
    return {
        "segment_id": segment_id,
        "order": order,
        "start_word": start_word,
        "end_word": end_word,
        "start_paragraph": start_paragraph,
        "end_paragraph": end_paragraph,
        "cumulative_start_ms": cumulative_start_ms,
        "duration_ms": duration_ms,
        "assets": {
            asset_name: _asset(asset_name, segment_id)
            for asset_name in ("audio", "timestamps", "vtt", "metadata")
        },
    }


def _package_without_version():
    return {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "slug": SLUG,
        "release_descriptor_sha256": RELEASE_DESCRIPTOR_SHA256,
        "source_sha256": SOURCE_SHA256,
        "manuscript_sha256": MANUSCRIPT_SHA256,
        "release_evidence_version": "release-evidence-v1",
        "duration_ms": 360_000,
        "segment_count": 3,
        "word_count": 10,
        "paragraph_count": 4,
        "sync_tier": "measured_paragraph",
        "highlight_sync_enabled": True,
        "tracks": [
            {
                "id": "track-001",
                "chapter_id": "chapter-001",
                "title": "Chapter 1",
                "order": 0,
                "start_word": 0,
                "end_word": 4,
                "start_paragraph": 0,
                "end_paragraph": 1,
                "chunks": [
                    _segment(
                        segment_id="segment-0001",
                        order=0,
                        start_word=0,
                        end_word=4,
                        start_paragraph=0,
                        end_paragraph=1,
                        cumulative_start_ms=0,
                        duration_ms=120_000,
                    )
                ],
            },
            {
                "id": "track-002",
                "chapter_id": "chapter-002",
                "title": "Chapter 2",
                "order": 1,
                "start_word": 5,
                "end_word": 9,
                "start_paragraph": 2,
                "end_paragraph": 3,
                "chunks": [
                    _segment(
                        segment_id="segment-0002",
                        order=0,
                        start_word=5,
                        end_word=7,
                        start_paragraph=2,
                        end_paragraph=2,
                        cumulative_start_ms=120_000,
                        duration_ms=180_000,
                    ),
                    _segment(
                        segment_id="segment-0003",
                        order=1,
                        start_word=8,
                        end_word=9,
                        start_paragraph=3,
                        end_paragraph=3,
                        cumulative_start_ms=300_000,
                        duration_ms=60_000,
                    ),
                ],
            },
        ],
    }


def _package():
    return with_canonical_package_version(_package_without_version())


def _rehash(package):
    return with_canonical_package_version(package)


def _validate(package, **overrides):
    expected = {
        "expected_slug": SLUG,
        "expected_source_sha256": SOURCE_SHA256,
        "expected_manuscript_sha256": MANUSCRIPT_SHA256,
        "expected_release_descriptor_sha256": RELEASE_DESCRIPTOR_SHA256,
    }
    expected.update(overrides)
    return validate_audiobook_package(package, **expected)


def test_package_version_is_canonical_and_package_validates():
    package = _package()
    reversed_package = dict(reversed(list(package.items())))

    assert package["package_version"] == f"sha256-{canonical_package_sha256(package)}"
    assert expected_package_version(reversed_package) == package["package_version"]
    assert _validate(package) == package


def test_package_version_detects_tampering_and_truth_hash_mismatch():
    tampered = _package()
    tampered["tracks"][0]["chunks"][0]["duration_ms"] += 1

    with pytest.raises(AudiobookPackageValidationError, match="package_version"):
        _validate(tampered)

    package = _package()
    with pytest.raises(AudiobookPackageValidationError, match="source_sha256"):
        _validate(package, expected_source_sha256="8" * 64)
    with pytest.raises(AudiobookPackageValidationError, match="manuscript_sha256"):
        _validate(package, expected_manuscript_sha256="9" * 64)
    with pytest.raises(
        AudiobookPackageValidationError, match="release_descriptor_sha256"
    ):
        _validate(package, expected_release_descriptor_sha256="0" * 64)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("start_word", 6, "globally contiguous"),
        ("start_paragraph", 3, "globally contiguous"),
    ],
)
def test_package_rejects_noncontiguous_global_boundaries(field, value, message):
    package = _package()
    package["tracks"][1]["chunks"][0][field] = value
    package["tracks"][1][field] = value
    package = _rehash(package)

    with pytest.raises(AudiobookPackageValidationError, match=message):
        _validate(package)


def test_package_requires_all_four_assets():
    package = _package()
    del package["tracks"][0]["chunks"][0]["assets"]["vtt"]
    package = _rehash(package)

    with pytest.raises(AudiobookPackageValidationError, match="missing required fields"):
        _validate(package)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda asset: asset.__setitem__("mime_type", "application/octet-stream"),
            "mime_type must be",
        ),
        (
            lambda asset: asset["storage"].__setitem__(
                "key", "v1/prod/sprint1/another-book/releases/" + "3" * 64 + "/a.mp3"
            ),
            "immutable prefix",
        ),
        (
            lambda asset: asset["storage"].__setitem__("version_id", ""),
            "version_id",
        ),
    ],
)
def test_package_rejects_invalid_asset_records(mutation, message):
    package = _package()
    asset = package["tracks"][0]["chunks"][0]["assets"]["audio"]
    mutation(asset)
    package = _rehash(package)

    with pytest.raises(AudiobookPackageValidationError, match=message):
        _validate(package)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda asset: asset.__setitem__("replicas", []),
            "at least one disaster-recovery copy",
        ),
        (
            lambda asset: asset["replicas"][0].__setitem__(
                "store", asset["storage"]["store"]
            ),
            "store must differ from primary",
        ),
        (
            lambda asset: asset["replicas"][0].__setitem__(
                "bucket", asset["storage"]["bucket"]
            ),
            "bucket must differ from primary",
        ),
        (
            lambda asset: asset["replicas"][0].__setitem__(
                "key", asset["storage"]["key"] + ".copy"
            ),
            "key must exactly match the primary immutable key",
        ),
        (
            lambda asset: asset["replicas"][0].__setitem__("version_id", ""),
            "version_id",
        ),
    ],
)
def test_final_package_requires_versioned_dr_replica_with_key_parity(
    mutation, message
):
    package = _package()
    asset = package["tracks"][0]["chunks"][0]["assets"]["audio"]
    mutation(asset)
    package = _rehash(package)

    with pytest.raises(AudiobookPackageValidationError, match=message):
        _validate(package)


def test_v2_schema_declares_hash_bound_assets_and_storage():
    schema_path = (
        BACKEND_DIR.parent
        / "internal"
        / "audiobook_lab"
        / "schemas"
        / "audiobook_package_manifest.v2.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["package_version"]["pattern"] == (
        "^sha256-[a-f0-9]{64}$"
    )
    segment = schema["$defs"]["segment"]
    assert {"start_paragraph", "end_paragraph", "assets"} <= set(
        segment["required"]
    )
    assert set(segment["properties"]["assets"]["required"]) == {
        "audio",
        "timestamps",
        "vtt",
        "metadata",
    }
    assert set(schema["$defs"]["asset"]["required"]) == {
        "sha256",
        "size_bytes",
        "mime_type",
        "storage",
        "replicas",
    }
    assert schema["$defs"]["asset"]["properties"]["replicas"]["minItems"] == 1
    assert set(schema["$defs"]["storage"]["required"]) == {
        "store",
        "bucket",
        "key",
        "version_id",
    }


def _active_state(percentage):
    return build_active_release_state(
        slug=SLUG,
        active_release_descriptor_sha256=ACTIVE_RELEASE_SHA256,
        candidate_release_descriptor_sha256=CANDIDATE_RELEASE_SHA256,
        retained_release_descriptor_sha256s=[
            ACTIVE_RELEASE_SHA256,
            CANDIDATE_RELEASE_SHA256,
            PREVIOUS_RELEASE_SHA256,
        ],
        rollout_percentage=percentage,
        rollout_salt="muchiram-rollout-v1",
    )


def test_active_release_state_and_zero_or_full_rollout_are_deterministic():
    zero = _active_state(0)
    full = _active_state(100)

    assert zero["schema_version"] == ACTIVE_RELEASE_SCHEMA_VERSION
    assert validate_active_release_state(zero) == zero
    assert select_release_descriptor_sha256(zero, sticky_key="reader-1") == (
        ACTIVE_RELEASE_SHA256
    )
    assert select_release_descriptor_sha256(full, sticky_key="reader-1") == (
        CANDIDATE_RELEASE_SHA256
    )


@pytest.mark.parametrize("percentage", [5, 25])
def test_sticky_rollout_uses_a_stable_bucket(percentage):
    state = _active_state(percentage)
    sticky_key = "reader-sticky-key"
    bucket = deterministic_rollout_bucket(
        slug=SLUG,
        sticky_key=sticky_key,
        salt=state["rollout"]["salt"],
    )
    expected = (
        CANDIDATE_RELEASE_SHA256
        if bucket < percentage
        else ACTIVE_RELEASE_SHA256
    )

    assert select_release_descriptor_sha256(state, sticky_key=sticky_key) == expected
    assert select_release_descriptor_sha256(state, sticky_key=sticky_key) == expected
    assert (
        require_selected_release(
            state,
            requested_release_descriptor_sha256=expected,
            sticky_key=sticky_key,
        )
        == expected
    )


def test_inactive_and_stale_release_requests_fail_closed():
    inactive = _active_state(25)
    inactive["status"] = "INACTIVE"

    with pytest.raises(AudiobookReleaseSelectionError, match="inactive"):
        select_release_descriptor_sha256(inactive, sticky_key="reader-1")

    state = _active_state(25)
    selected = select_release_descriptor_sha256(state, sticky_key="reader-1")
    wrong_cohort = (
        CANDIDATE_RELEASE_SHA256
        if selected == ACTIVE_RELEASE_SHA256
        else ACTIVE_RELEASE_SHA256
    )
    with pytest.raises(AudiobookReleaseSelectionError, match="inactive or stale"):
        require_selected_release(
            state,
            requested_release_descriptor_sha256=wrong_cohort,
            sticky_key="reader-1",
        )
    with pytest.raises(AudiobookReleaseSelectionError, match="inactive or stale"):
        require_selected_release(
            state,
            requested_release_descriptor_sha256="d" * 64,
            sticky_key="reader-1",
        )


def test_active_release_state_rejects_unsupported_rollout_and_retention():
    state = _active_state(25)
    state["rollout"]["percentage"] = 10
    with pytest.raises(AudiobookReleaseSelectionError, match="0, 5, 25, 100"):
        validate_active_release_state(state)

    state = _active_state(25)
    state["retained_release_descriptor_sha256s"].append("d" * 64)
    with pytest.raises(AudiobookReleaseSelectionError, match="at most two"):
        validate_active_release_state(state)
