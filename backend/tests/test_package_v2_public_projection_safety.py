from __future__ import annotations

import json
from copy import deepcopy

from backend import catalog_truth, home_curation_v4


SLUG = "book-2b9853ec52"
RELEASE_DESCRIPTOR_SHA256 = "e00ec647012b90a2f2d5324ac59eec8f755e6353c3a736497495e53d9a21f26a"
PACKAGE_VERSION = "sha256-" + ("7" * 64)
PRIVATE_BUCKET = "earnalism-private-package-v2-test"
PRIVATE_KEY = (
    f"v1/prod/sprint1/{SLUG}/releases/{RELEASE_DESCRIPTOR_SHA256}/"
    "delivery/chapter-001/segment-001.mp3"
)
PRIVATE_VERSION_ID = "4_z-private-package-v2-version"

FORBIDDEN_PUBLIC_KEYS = {
    "asset_id",
    "audiobook_active_release",
    "audiobook_legacy_release_descriptor_sha256",
    "audiobook_hidden_release_descriptor_sha256",
    "audiobook_package_canary",
    "audiobook_manuscript_sha256",
    "audiobook_package",
    "audiobook_package_release_evidence",
    "audiobook_packages",
    "audiobook_release_descriptor_sha256",
    "audiobook_rollout_state",
    "bucket",
    "immutable_prefix",
    "key",
    "manuscript_sha256",
    "package_version",
    "release_descriptor_sha256",
    "replicas",
    "source_sha256",
    "storage",
    "store",
    "version_id",
}
FORBIDDEN_PUBLIC_VALUES = {
    RELEASE_DESCRIPTOR_SHA256,
    PACKAGE_VERSION,
    PRIVATE_BUCKET,
    PRIVATE_KEY,
    PRIVATE_VERSION_ID,
    "v1/prod/sprint1/",
}


def _package_v2() -> dict:
    storage = {
        "store": "audiobook_prod",
        "bucket": PRIVATE_BUCKET,
        "key": PRIVATE_KEY,
        "version_id": PRIVATE_VERSION_ID,
    }
    return {
        "schema_version": "audiobook_package_manifest.v2",
        "slug": SLUG,
        "package_version": PACKAGE_VERSION,
        "release_evidence_version": "goliveevidence-private-test",
        "release_descriptor_sha256": RELEASE_DESCRIPTOR_SHA256,
        "source_sha256": "1" * 64,
        "manuscript_sha256": "2" * 64,
        "duration_ms": 1000,
        "segment_count": 1,
        "word_count": 2,
        "paragraph_count": 1,
        "tracks": [
            {
                "id": "chapter-001",
                "chapter_id": "chapter-001",
                "order": 0,
                "start_word": 0,
                "end_word": 1,
                "start_paragraph": 0,
                "end_paragraph": 0,
                "chunks": [
                    {
                        "segment_id": "c001-s001",
                        "order": 0,
                        "start_word": 0,
                        "end_word": 1,
                        "start_paragraph": 0,
                        "end_paragraph": 0,
                        "cumulative_start_ms": 0,
                        "duration_ms": 1000,
                        "assets": {
                            "audio": {
                                "asset_id": "c001-s001.audio",
                                "sha256": "3" * 64,
                                "size_bytes": 1234,
                                "mime_type": "audio/mpeg",
                                "storage": storage,
                                "replicas": [
                                    {
                                        **storage,
                                        "store": "audiobook_dr",
                                        "bucket": "earnalism-private-package-v2-dr-test",
                                        "version_id": "4_z-private-package-v2-dr-version",
                                    }
                                ],
                            }
                        },
                    }
                ],
            }
        ],
    }


def _artifact_with_internal_package() -> dict:
    artifact = catalog_truth.load_controlled_artifact_book(SLUG, include_content=False)
    assert artifact is not None
    artifact = deepcopy(artifact)
    package = _package_v2()
    artifact["audiobook_package"] = package
    artifact["audiobook_packages"] = {RELEASE_DESCRIPTOR_SHA256: package}
    artifact["audiobook_release_descriptor_sha256"] = RELEASE_DESCRIPTOR_SHA256
    artifact["audiobook_manuscript_sha256"] = "2" * 64
    artifact["audiobook_legacy_release_descriptor_sha256"] = "9" * 64
    artifact["audiobook_package_release_evidence"] = {
        RELEASE_DESCRIPTOR_SHA256: {
            "schema_version": "audiobook_package_release_evidence.v1",
            "release_eligible": True,
            "primary_receipt_sha256": "5" * 64,
            "replica_receipt_sha256": "6" * 64,
        }
    }
    artifact["audiobook_active_release"] = {
        "schema_version": "audiobook_active_release.v1",
        "slug": SLUG,
        "status": "ACTIVE",
        "active_release_descriptor_sha256": RELEASE_DESCRIPTOR_SHA256,
        "candidate_release_descriptor_sha256": "",
        "retained_release_descriptor_sha256s": [RELEASE_DESCRIPTOR_SHA256],
        "rollout": {"percentage": 0, "salt": ""},
    }
    artifact["audiobook_rollout_state"] = {
        "active_release_descriptor_sha256": RELEASE_DESCRIPTOR_SHA256,
        "retained_release_descriptor_sha256s": [RELEASE_DESCRIPTOR_SHA256],
    }
    artifact.setdefault("audiobook", {})["package"] = package
    return artifact


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _assert_no_private_package_identity(payload) -> None:
    leaked_keys = FORBIDDEN_PUBLIC_KEYS.intersection(_walk_keys(payload))
    assert leaked_keys == set()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    leaked_values = {value for value in FORBIDDEN_PUBLIC_VALUES if value in encoded}
    assert leaked_values == set()


def test_public_catalog_projection_omits_package_v2_storage_identity() -> None:
    projected = catalog_truth.public_book_projection(_artifact_with_internal_package())

    assert projected is not None
    assert projected["slug"] == SLUG
    assert projected["audio_enabled"] is True
    assert projected["audio_url"] == f"/api/reader/book/{SLUG}/audiobook"
    _assert_no_private_package_identity(projected)


def test_transport_canary_remains_reader_only_and_redacts_hidden_identity(
    monkeypatch,
) -> None:
    artifact = _artifact_with_internal_package()
    artifact["audio_enabled"] = False
    artifact["audiobook_enabled"] = False
    artifact["audiobook_hidden_release_descriptor_sha256"] = "8" * 64
    artifact["audiobook_package_canary"] = {
        "schema_version": "audiobook_new_title_package_canary.v1",
        "status": "PUBLIC_AUDIO_PACKAGE_CANARY_APPROVED",
        "candidate_release_descriptor_sha256": RELEASE_DESCRIPTOR_SHA256,
        "hidden_release_descriptor_sha256": "8" * 64,
    }
    monkeypatch.setattr(catalog_truth, "AUDIO_ENABLED_SLUGS", set())

    projected = catalog_truth.public_book_projection(artifact)

    assert projected is not None
    assert projected["reader_enabled"] is True
    assert projected["audio_enabled"] is False
    assert projected["audiobook_enabled"] is False
    assert projected["audio_url"] == ""
    _assert_no_private_package_identity(projected)


def test_home_v4_projection_omits_package_v2_storage_identity() -> None:
    artifact = _artifact_with_internal_package()
    payload = home_curation_v4.build_home_curated_payload_v4(
        [artifact],
        config={
            "sprint1_active_slugs": [SLUG],
            "hero_featured_slugs": [SLUG],
        },
        audio_contracts={
            SLUG: {
                "enabled": True,
                "url": f"/api/reader/book/{SLUG}/audiobook",
                "release_gate": "APPROVED",
                "qa_status": "QA_PASSED",
                "duration_ms": 327069,
                "package_valid": True,
                "endpoint_valid": True,
                # Even if an internal caller accidentally adds these fields,
                # the Home contract must project only reader-facing status.
                "package_version": PACKAGE_VERSION,
                "release_descriptor_sha256": RELEASE_DESCRIPTOR_SHA256,
                "storage_key": PRIVATE_KEY,
                "version_id": PRIVATE_VERSION_ID,
            }
        },
        generated_at="2026-07-29T10:02:21Z",
    )

    assert payload["source"]["approved_audiobook_count"] == 1
    assert payload["shelves"]["approved_audiobooks"][0]["slug"] == SLUG
    assert (
        payload["shelves"]["approved_audiobooks"][0]["audiobook_url"]
        == f"/api/reader/book/{SLUG}/audiobook"
    )
    _assert_no_private_package_identity(payload)


def test_home_book_contract_is_an_explicit_public_allowlist() -> None:
    artifact = _artifact_with_internal_package()
    contract = home_curation_v4._book_contract(
        artifact,
        {},
        {
            "enabled": True,
            "url": f"/api/reader/book/{SLUG}/audiobook",
            "release_gate": "APPROVED",
            "qa_status": "QA_PASSED",
            "package_valid": True,
            "endpoint_valid": True,
            "package_version": PACKAGE_VERSION,
            "version_id": PRIVATE_VERSION_ID,
        },
    )

    assert contract is not None
    assert contract["audiobook_enabled"] is True
    _assert_no_private_package_identity(contract)
