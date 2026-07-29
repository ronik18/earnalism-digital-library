import copy
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("audiobook_package_builder_v2.py")
SPEC = importlib.util.spec_from_file_location("audiobook_package_builder_v2", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _semantics():
    return {
        "schema_version": "audiobook_package_semantics.v2",
        "package_schema_version": "audiobook_package_manifest.v2",
        "slug": "test-title",
        "release_evidence_version": "evidence-v1",
        "release_descriptor_sha256": "d" * 64,
        "source_sha256": "a" * 64,
        "manuscript_sha256": "b" * 64,
        "duration_ms": 2000,
        "segment_count": 2,
        "word_count": 4,
        "paragraph_count": 2,
        "sync_tier": "paragraph_or_stanza",
        "highlight_sync_enabled": False,
        "tracks": [
            {
                "id": "chapter-001",
                "chapter_id": "chapter-001",
                "order": 0,
                "title": "Test",
                "start_word": 0,
                "end_word": 3,
                "start_paragraph": 0,
                "end_paragraph": 1,
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
                        "asset_ids": {
                            name: f"c001-s001.{name}"
                            for name in ("audio", "timestamps", "vtt", "metadata")
                        },
                    },
                    {
                        "segment_id": "c001-s002",
                        "order": 1,
                        "start_word": 2,
                        "end_word": 3,
                        "start_paragraph": 1,
                        "end_paragraph": 1,
                        "cumulative_start_ms": 1000,
                        "duration_ms": 1000,
                        "asset_ids": {
                            name: f"c001-s002.{name}"
                            for name in ("audio", "timestamps", "vtt", "metadata")
                        },
                    },
                ],
            }
        ],
    }


def _plan_and_receipts():
    prefix = f"v1/prod/sprint1/test-title/releases/{'d' * 64}/"
    mime = {
        "audio": "audio/mpeg",
        "timestamps": "application/json",
        "vtt": "text/vtt",
        "metadata": "application/json",
    }
    assets = []
    primary = []
    replica = []
    for segment in ("c001-s001", "c001-s002"):
        for name in mime:
            asset_id = f"{segment}.{name}"
            row = {
                "asset_id": asset_id,
                "local_path": f"/tmp/{asset_id}",
                "key": f"{prefix}{asset_id}",
                "sha256": (str(len(assets) % 10) * 64),
                "size_bytes": 100 + len(assets),
                "mime_type": mime[name],
            }
            assets.append(row)
            primary.append(
                {
                    **row,
                    "store": "audiobook_prod",
                    "bucket": "primary-bucket",
                    "version_id": f"primary-{asset_id}",
                }
            )
            replica.append(
                {
                    **row,
                    "store": "audiobook_dr",
                    "bucket": "replica-bucket",
                    "version_id": f"replica-{asset_id}",
                }
            )
    plan = {"assets": assets}
    return (
        plan,
        {
            "receipt_role": "primary",
            "release_eligible": True,
            "passed": True,
            "objects": primary,
        },
        {
            "receipt_role": "replica",
            "passed": True,
            "store": {"release_eligible": True},
            "objects": replica,
        },
    )


def test_finalize_binds_primary_and_replica_and_derives_package_version():
    plan, primary, replica = _plan_and_receipts()
    package = builder.finalize_package(
        semantics=_semantics(),
        upload_plan=plan,
        primary_receipt=primary,
        replica_receipt=replica,
    )

    assert package["package_version"].startswith("sha256-")
    assert len(package["package_version"]) == 71
    first_audio = package["tracks"][0]["chunks"][0]["assets"]["audio"]
    assert first_audio["storage"]["version_id"].startswith("primary-")
    assert first_audio["replicas"][0]["version_id"].startswith("replica-")


def test_finalize_rejects_receipt_hash_drift():
    plan, primary, replica = _plan_and_receipts()
    primary["objects"][0]["sha256"] = "f" * 64

    with pytest.raises(builder.PackageBuildError, match="sha256"):
        builder.finalize_package(
            semantics=_semantics(),
            upload_plan=plan,
            primary_receipt=primary,
            replica_receipt=replica,
        )


def test_finalize_rejects_private_qa_staging_receipt():
    plan, primary, replica = _plan_and_receipts()
    primary["receipt_role"] = "private_qa_staging"
    primary["release_eligible"] = False

    with pytest.raises(builder.PackageBuildError, match="release-eligible"):
        builder.finalize_package(
            semantics=_semantics(),
            upload_plan=plan,
            primary_receipt=primary,
            replica_receipt=replica,
        )


def test_rebased_cues_preserve_measured_boundaries():
    cues = [
        {"id": "group-2", "start": 10.0, "end": 12.5, "text": "One two"},
        {"id": "group-3", "start": 12.5, "end": 15.0, "text": "Three four"},
    ]
    rebased = builder.rebased_cues(cues, segment_start_seconds=10.0)

    assert rebased[0]["start"] == 0.0
    assert rebased[-1]["end"] == 5.0
    assert sum(builder.cue_word_count(cue) for cue in cues) == 4


def test_descriptor_hash_is_canonical_across_key_order():
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}
    assert builder.canonical_sha256(left) == builder.canonical_sha256(right)
