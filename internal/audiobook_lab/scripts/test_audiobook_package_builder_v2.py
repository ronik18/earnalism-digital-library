import copy
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

import pytest


SCRIPT = Path(__file__).with_name("audiobook_package_builder_v2.py")
SPEC = importlib.util.spec_from_file_location("audiobook_package_builder_v2", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_controlled_mirrors(
    repo_root: Path,
    documents: dict[str, dict[str, Any]],
) -> None:
    for mirror in ("backend/data", "data"):
        directory = (
            repo_root / mirror / "controlled_publications" / "the-open-window"
        )
        for filename, document in documents.items():
            _write_json(directory / filename, document)
        checksums = {
            "slug": "the-open-window",
            "files": [
                {
                    "file": filename,
                    "sha256": builder.sha256_file(directory / filename),
                }
                for filename in (
                    "approval_evidence.json",
                    "public_book.json",
                    "reader_manifest.json",
                    "source_evidence.json",
                )
            ],
        }
        _write_json(directory / "checksum_manifest.json", checksums)


def _approved_legacy_fixture(tmp_path: Path) -> dict[str, Any]:
    repo_root = tmp_path / "repo"
    assets_dir = tmp_path / "approved-assets"
    assets_dir.mkdir()
    slug = "the-open-window"
    source_sha256 = "1" * 64
    manuscript_sha256 = "2" * 64
    paths = {
        "mp3": assets_dir / f"{slug}.mp3",
        "timestamps": assets_dir / f"{slug}-timestamps.json",
        "vtt": assets_dir / f"{slug}.vtt",
        "chapters": assets_dir / f"{slug}-chapters.json",
        "meta": assets_dir / f"{slug}-meta.json",
    }
    paths["mp3"].write_bytes(b"exact-approved-open-window-mp3")
    audio_sha256 = builder.sha256_file(paths["mp3"])
    cues = [
        {
            "id": "paragraph-001",
            "start": 0.0,
            "end": 300.0,
            "text": "My aunt will be down presently.",
            "granularity": "paragraph",
            "timing_origin": "audio_derived_asr_measured_exact_canonical_paragraph",
        },
        {
            "id": "paragraph-002",
            "start": 301.0,
            "end": 600.0,
            "text": "Framton endeavoured to say the correct something.",
            "granularity": "paragraph",
            "timing_origin": "audio_derived_asr_measured_exact_canonical_paragraph",
        },
    ]
    _write_json(
        paths["timestamps"],
        {
            "slug": slug,
            "audio_hash": audio_sha256,
            "source_text_hash": manuscript_sha256,
            "auto_estimated_sync": False,
            "sync_granularity": "paragraph",
            "alignment_method": (
                "audio_derived_asr_word_timestamps_to_exact_canonical_paragraphs"
            ),
            "cues": cues,
        },
    )
    paths["vtt"].write_text(
        "\n".join(
            [
                "WEBVTT",
                "",
                "1",
                "00:00:00.000 --> 00:05:00.000",
                cues[0]["text"],
                "",
                "2",
                "00:05:01.000 --> 00:10:00.000",
                cues[1]["text"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_json(
        paths["chapters"],
        {
            "slug": slug,
            "chapters": [
                {
                    "id": "chapter-001",
                    "title": "The Open Window",
                    "start": 0.0,
                    "end": 600.0,
                }
            ],
        },
    )
    _write_json(
        paths["meta"],
        {
            "slug": slug,
            "audio_hash": audio_sha256,
            "source_text_hash": manuscript_sha256,
            "auto_estimated_sync": False,
            "sync_granularity": "paragraph",
            "duration_seconds": 600.0,
            "asr_transcript_match_score": 10.0,
            "asr_release_status": "PASS",
        },
    )
    asset_hashes = {
        name: builder.sha256_file(path) for name, path in paths.items()
    }
    asset_urls = {
        name: (
            "https://audio.example.test/the-open-window/"
            f"{slug}_{name}_{digest[:12]}"
            f"{'.mp3' if name == 'mp3' else '.vtt' if name == 'vtt' else '.json'}"
        )
        for name, digest in asset_hashes.items()
    }
    documents = {
        "public_book.json": {
            "slug": slug,
            "title": "The Open Window",
            "author": "Saki",
            "source_hash": source_sha256,
            "approved_to_publish": True,
            "isPublic": True,
            "isLive": True,
            "audio_enabled": True,
            "audiobook_enabled": True,
            "audiobook_assets": asset_urls,
            "audiobook": {
                "url": asset_urls["mp3"],
                "provider": "kokoro",
                "voice": "af_bella",
                "model": "Kokoro-82M 0.9.4",
                "size": paths["mp3"].stat().st_size,
                "duration_ms": 600_000,
                "audio_sha256": audio_sha256,
                "source_sha256": manuscript_sha256,
                "asset_sha256": asset_hashes,
                "assets": asset_urls,
            },
        },
        "reader_manifest.json": {
            "slug": slug,
            "audio_enabled": True,
            "audiobook_enabled": True,
        },
        "source_evidence.json": {
            "slug": slug,
            "source_hash": source_sha256,
            "rights_basis": "Public domain text with approved AI narration rights",
        },
        "approval_evidence.json": {
            "slug": slug,
            "approved_to_publish": True,
            "audiobook_enabled": True,
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_APPROVED",
            "qa_status": "QA_PASSED",
            "audio_qa_status": "QA_PASSED",
            "rights_tier": "A",
            "verification_status": "approved",
            "asr_manuscript_score": 10.0,
            "source_coverage": 1.0,
            "first_words_match": True,
            "last_words_match": True,
            "no_missing_duplicated_reordered_content": True,
            "listening_qa_overall_score": 9.4,
            "listening_qa_minimum_confidence": 0.95,
            "listening_qa_fatal_flags": [],
            "auto_estimated_sync": False,
            "sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "measured_paragraph_sync_score": 10.0,
            "upload_status": "UPLOADED_CHECKSUM_VERIFIED_PRIVATE_ORIGIN",
            "endpoint_http_status": 206,
            "browser_gate_status": "PASS",
            "release_blockers": [],
            "audio_sha256": audio_sha256,
            "source_sha256": manuscript_sha256,
            "uploaded_artifact_sha256": asset_hashes,
            "uploaded_artifact_size_bytes": {
                name: path.stat().st_size for name, path in paths.items()
            },
        },
    }
    _write_controlled_mirrors(repo_root, documents)
    return {
        "repo_root": repo_root,
        "slug": slug,
        "paths": paths,
        "documents": documents,
        "audio_sha256": audio_sha256,
        "source_sha256": source_sha256,
        "manuscript_sha256": manuscript_sha256,
    }


def _rewrite_approval(
    fixture: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    approval = fixture["documents"]["approval_evidence.json"]
    mutate(approval)
    _write_controlled_mirrors(fixture["repo_root"], fixture["documents"])


def _rebind_fixture_asset(fixture: dict[str, Any], name: str) -> None:
    path = fixture["paths"][name]
    digest = builder.sha256_file(path)
    approval = fixture["documents"]["approval_evidence.json"]
    public_book = fixture["documents"]["public_book.json"]
    approval["uploaded_artifact_sha256"][name] = digest
    approval["uploaded_artifact_size_bytes"][name] = path.stat().st_size
    public_book["audiobook"]["asset_sha256"][name] = digest
    suffix = ".mp3" if name == "mp3" else ".vtt" if name == "vtt" else ".json"
    replacement_url = (
        "https://audio.example.test/the-open-window/"
        f"the-open-window_{name}_{digest[:12]}{suffix}"
    )
    public_book["audiobook_assets"][name] = replacement_url
    public_book["audiobook"]["assets"][name] = replacement_url
    _write_controlled_mirrors(fixture["repo_root"], fixture["documents"])


def _validate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    paths = fixture["paths"]
    return builder._validate_approved_legacy_inputs(
        repo_root=fixture["repo_root"],
        slug=fixture["slug"],
        audio_path=paths["mp3"],
        timestamps_path=paths["timestamps"],
        vtt_path=paths["vtt"],
        chapters_path=paths["chapters"],
        meta_path=paths["meta"],
    )


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


def test_segment_groups_preserve_silence_between_measured_cues():
    chapter = {
        "id": "chapter-001",
        "title": "Long chapter",
        "start": 0.0,
        "end": 1300.0,
    }
    cues = [
        {
            "id": "p1",
            "start": 0.0,
            "end": 400.0,
            "chapter_id": "chapter-001",
        },
        {
            "id": "p2",
            "start": 401.0,
            "end": 800.0,
            "chapter_id": "chapter-001",
        },
        {
            "id": "p3",
            "start": 802.0,
            "end": 1300.0,
            "chapter_id": "chapter-001",
        },
    ]

    groups = builder._segment_cue_groups([chapter], cues)

    assert groups[0]["start"] == 0.0
    assert groups[-1]["end"] == 1300.0
    assert all(
        left["end"] == right["start"]
        for left, right in zip(groups, groups[1:])
    )
    assert all(
        group["end"] - group["start"] <= builder.MAX_SEGMENT_SECONDS
        for group in groups
    )


@pytest.mark.parametrize(
    "chapter_id",
    ("../escape", "chapter/escape", "/absolute", "."),
)
def test_approved_legacy_rejects_noncanonical_chapter_ids(
    tmp_path,
    monkeypatch,
    chapter_id,
):
    fixture = _approved_legacy_fixture(tmp_path)
    chapters = builder.read_json(fixture["paths"]["chapters"])
    chapters["chapters"][0]["id"] = chapter_id
    _write_json(fixture["paths"]["chapters"], chapters)
    _rebind_fixture_asset(fixture, "chapters")
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match="canonical package identifier"):
        _validate_fixture(fixture)


def test_approved_legacy_rejects_duplicate_chapter_ids(tmp_path, monkeypatch):
    fixture = _approved_legacy_fixture(tmp_path)
    chapters = builder.read_json(fixture["paths"]["chapters"])
    chapters["chapters"] = [
        {
            "id": "chapter-001",
            "title": "Part one",
            "start": 0.0,
            "end": 300.0,
        },
        {
            "id": "chapter-001",
            "title": "Part two",
            "start": 300.0,
            "end": 600.0,
        },
    ]
    _write_json(fixture["paths"]["chapters"], chapters)
    _rebind_fixture_asset(fixture, "chapters")
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match="Duplicate chapter id"):
        _validate_fixture(fixture)


@pytest.mark.parametrize("second_start", (300.02, 299.98))
def test_approved_legacy_rejects_chapter_gap_or_overlap(
    tmp_path,
    monkeypatch,
    second_start,
):
    fixture = _approved_legacy_fixture(tmp_path)
    chapters = builder.read_json(fixture["paths"]["chapters"])
    chapters["chapters"] = [
        {
            "id": "chapter-001",
            "title": "Part one",
            "start": 0.0,
            "end": 300.0,
        },
        {
            "id": "chapter-002",
            "title": "Part two",
            "start": second_start,
            "end": 600.0,
        },
    ]
    _write_json(fixture["paths"]["chapters"], chapters)
    _rebind_fixture_asset(fixture, "chapters")
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match="not contiguous"):
        _validate_fixture(fixture)


@pytest.mark.parametrize(
    "groups",
    (
        [{"start": 0.0, "end": 300.0}, {"start": 300.02, "end": 600.0}],
        [{"start": 0.0, "end": 300.0}, {"start": 299.98, "end": 600.0}],
    ),
)
def test_segment_source_coverage_rejects_gap_or_overlap(groups):
    with pytest.raises(builder.PackageBuildError, match="gap or overlap"):
        builder._validate_segment_source_coverage(
            groups,
            duration_seconds=600.0,
        )


def test_final_encoded_duration_allows_codec_padding_within_global_tolerance():
    builder._validate_final_encoded_duration(
        source_duration_ms=600_000,
        encoded_duration_ms=601_400,
    )


def test_final_encoded_duration_rejects_cumulative_padding_drift():
    with pytest.raises(builder.PackageBuildError, match="duration drifted"):
        builder._validate_final_encoded_duration(
            source_duration_ms=600_000,
            encoded_duration_ms=601_501,
        )


def test_build_approved_legacy_emits_release_candidate_from_open_window_shape(
    tmp_path,
    monkeypatch,
):
    fixture = _approved_legacy_fixture(tmp_path)
    output_dir = tmp_path / "package"

    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)
    monkeypatch.setattr(
        builder,
        "ffprobe_audio_profile",
        lambda path: {
            "codec_name": "mp3",
            "channels": 1,
            "sample_rate": "48000",
            "bit_rate": "96000",
        },
    )

    def fake_run_checked(command):
        destination = Path(command[-1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            b"pcm-master" if destination.suffix == ".wav" else b"encoded-segment"
        )

    monkeypatch.setattr(builder, "run_checked", fake_run_checked)
    result = builder.build_approved_legacy(
        repo_root=fixture["repo_root"],
        slug=fixture["slug"],
        audio_path=fixture["paths"]["mp3"],
        timestamps_path=fixture["paths"]["timestamps"],
        vtt_path=fixture["paths"]["vtt"],
        chapters_path=fixture["paths"]["chapters"],
        meta_path=fixture["paths"]["meta"],
        output_dir=output_dir,
    )

    assert result["status"] == "RELEASE_CANDIDATE_PACKAGE_BUILT"
    assert result["release_status"] == "RELEASE_CANDIDATE"
    assert result["release_blockers"] == []
    assert result["segment_count"] == 1
    descriptor = builder.read_json(output_dir / "release-descriptor.json")
    assert descriptor["approved_source_audio_sha256"] == fixture["audio_sha256"]
    assert descriptor["controlled_source_sha256"] == fixture["source_sha256"]
    assert descriptor["manuscript_sha256"] == fixture["manuscript_sha256"]
    assert descriptor["release_candidate_evidence"]["status"] == "PASS"
    assert descriptor["release_candidate_evidence"]["all_release_gates_passed"]
    assert descriptor["known_release_blockers"] == []
    assert builder.canonical_sha256(descriptor) == result[
        "release_descriptor_sha256"
    ]
    plan = builder.read_json(output_dir / "upload-plan.json")
    assert plan["release_status"] == "RELEASE_CANDIDATE"
    assert plan["immutable_prefix"].endswith(
        f"/{result['release_descriptor_sha256']}/"
    )
    assert {
        "master.original",
        "master.pcm",
        "release.descriptor",
        "provenance.legacy.timestamps",
        "provenance.legacy.vtt",
        "provenance.legacy.chapters",
        "provenance.legacy.meta",
        "provenance.controlled.approval",
        "provenance.controlled.source",
        "provenance.controlled.checksums",
        "c001-s001.audio",
        "c001-s001.timestamps",
        "c001-s001.vtt",
        "c001-s001.metadata",
    } == {asset["asset_id"] for asset in plan["assets"]}
    for asset in plan["assets"]:
        path = Path(asset["local_path"])
        assert path.is_file()
        assert asset["sha256"] == builder.sha256_file(path)
        assert asset["size_bytes"] == path.stat().st_size


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("asr_manuscript_score", 9.69, "ASR/manuscript"),
        ("source_coverage", 0.97, "ASR/source coverage"),
        ("first_words_match", False, "First/last"),
        ("last_words_match", False, "First/last"),
        (
            "no_missing_duplicated_reordered_content",
            False,
            "ordered-content",
        ),
        ("listening_qa_overall_score", 9.19, "Listening score"),
        ("listening_qa_minimum_confidence", 0.89, "Listening confidence"),
        ("listening_qa_fatal_flags", ["robotic texture"], "fatal flags"),
        ("auto_estimated_sync", True, "measured paragraph/stanza sync"),
        ("rights_tier", "B", "rights"),
        ("upload_status", "UPLOAD_FAILED", "checksum verified"),
        ("endpoint_http_status", 200, "HTTP 206"),
        ("browser_gate_status", "FAIL", "browser gate"),
        ("release_blockers", ["missing-proof"], "release blockers"),
    ],
)
def test_approved_legacy_rejects_every_degraded_release_gate(
    tmp_path,
    monkeypatch,
    field,
    value,
    error,
):
    fixture = _approved_legacy_fixture(tmp_path)
    _rewrite_approval(
        fixture,
        lambda approval: approval.__setitem__(field, value),
    )
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match=error):
        _validate_fixture(fixture)


def test_approved_legacy_rejects_local_asset_hash_drift(tmp_path, monkeypatch):
    fixture = _approved_legacy_fixture(tmp_path)
    fixture["paths"]["mp3"].write_bytes(b"not-the-approved-audio")
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match="controlled hash"):
        _validate_fixture(fixture)


def test_approved_legacy_rejects_non_measured_sidecar_sync(
    tmp_path,
    monkeypatch,
):
    fixture = _approved_legacy_fixture(tmp_path)
    timestamps_path = fixture["paths"]["timestamps"]
    timestamps = builder.read_json(timestamps_path)
    timestamps["auto_estimated_sync"] = True
    _write_json(timestamps_path, timestamps)
    replacement_hash = builder.sha256_file(timestamps_path)
    fixture["documents"]["approval_evidence.json"]["uploaded_artifact_sha256"][
        "timestamps"
    ] = replacement_hash
    fixture["documents"]["approval_evidence.json"]["uploaded_artifact_size_bytes"][
        "timestamps"
    ] = timestamps_path.stat().st_size
    fixture["documents"]["public_book.json"]["audiobook"]["asset_sha256"][
        "timestamps"
    ] = replacement_hash
    replacement_url = (
        "https://audio.example.test/the-open-window/"
        f"the-open-window_timestamps_{replacement_hash[:12]}.json"
    )
    fixture["documents"]["public_book.json"]["audiobook_assets"][
        "timestamps"
    ] = replacement_url
    fixture["documents"]["public_book.json"]["audiobook"]["assets"][
        "timestamps"
    ] = replacement_url
    _write_controlled_mirrors(fixture["repo_root"], fixture["documents"])
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match="Estimated sync"):
        _validate_fixture(fixture)
