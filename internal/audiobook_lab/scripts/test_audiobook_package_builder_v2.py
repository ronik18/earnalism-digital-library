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


def _legacy_word_normalization_fixture(tmp_path: Path) -> dict[str, Any]:
    repo_root = tmp_path / "repo"
    slug = "measured-legacy-title"
    controlled_dirs = [
        repo_root / "data/controlled_publications" / slug,
        repo_root / "backend/data/controlled_publications" / slug,
    ]
    chapter_relative = "chapters/chapter-001.json"
    source_text = "One two three.\n\nFour five six.\n"
    manuscript_sha256 = builder.hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    chapter = {
        "bookSlug": slug,
        "id": "chapter-001",
        "content": source_text.rstrip("\n"),
    }
    for directory in controlled_dirs:
        _write_json(directory / chapter_relative, chapter)
    chapter_sha256 = builder.sha256_file(controlled_dirs[0] / chapter_relative)
    checksum_manifest = {
        "slug": slug,
        "files": [{"file": chapter_relative, "sha256": chapter_sha256}],
    }

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    timestamps_path = assets_dir / "timestamps.json"
    vtt_path = assets_dir / "highlight.vtt"
    audio_sha256 = "a" * 64
    words = [
        {"word": word, "start": float(index), "end": float(index + 1)}
        for index, word in enumerate(("One", "two", "three", "Four", "five", "six"))
    ]
    timestamps = {
        "slug": slug,
        "alignment_method": "openai_verbose_json_word_timestamps",
        "auto_estimated_sync": False,
        "granularity": "word",
        "audio_hash": audio_sha256,
        "source_text_hash": manuscript_sha256,
        "words": words,
    }
    _write_json(timestamps_path, timestamps)
    vtt_path.write_text(
        "\n".join(
            [
                "WEBVTT",
                "",
                *[
                    line
                    for index, word in enumerate(words, start=1)
                    for line in (
                        str(index),
                        (
                            f"00:00:0{index - 1}.000 --> "
                            f"00:00:0{index}.000"
                        ),
                        word["word"],
                        "",
                    )
                ],
            ]
        ),
        encoding="utf-8",
    )
    timestamp_sha256 = builder.sha256_file(timestamps_path)
    vtt_sha256 = builder.sha256_file(vtt_path)
    upstream = {
        "slug": slug,
        "measured_quality": {
            "sync_score": 9.8,
            "sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "auto_estimated_sync": False,
        },
        "sidecars": {
            "timestamps": {"sha256": timestamp_sha256},
            "vtt": {"sha256": vtt_sha256},
        },
        "release_gates": {
            "source_binding": "PASS",
            "asr_source": "PASS",
            "first_last": "PASS",
            "sidecars": "PASS",
        },
    }
    upstream_path = repo_root / "internal/upstream-release-evidence.json"
    _write_json(upstream_path, upstream)
    evidence = {
        **upstream,
        "schema_version": (
            "audiobook_package_v2_legacy_normalization_evidence.v1"
        ),
        "status": "NORMALIZATION_INPUT_EVIDENCE_READY",
        "narration_regenerated": False,
        "release_gate_mutated": False,
        "measured_quality": {
            "upstream_transcript_vtt_sync_score": 9.8,
            "upstream_sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "post_conversion_boundary_quality_score": 1.0,
            "boundary_method": "equal_opcode_anchored_internal_boundaries",
            "sync_tier": "SECTION_BOUNDARIES_EQUAL_OPCODE_MEASURED",
            "auto_estimated_sync": False,
        },
        "source": {
            "chapter_path": chapter_relative,
            "chapter_sha256": chapter_sha256,
            "manuscript_sha256": manuscript_sha256,
            "section_count": 2,
            "emitted_section_count": 2,
            "anchored_internal_boundary_count": 1,
            "coalesced_boundary_count": 0,
            "boundary_retention_ratio": 1.0,
            "coverage": 1.0,
            "coverage_method": (
                "audio_derived_asr_matching_characters_over_canonical_source_characters"
            ),
        },
        "upstream_release_evidence": {
            "path": "internal/upstream-release-evidence.json",
            "sha256": builder.sha256_file(upstream_path),
        },
    }
    evidence_path = repo_root / "internal/release-evidence.json"
    _write_json(evidence_path, evidence)
    approval = {
        "source_coverage": 1.0,
        "source_coverage_method": (
            "audio_derived_asr_matching_characters_over_canonical_source_characters"
        ),
        "measured_section_boundary_score": 1.0,
        "measured_section_boundary_method": (
            "equal_opcode_anchored_internal_boundaries"
        ),
        "approved_legacy_sidecar_normalization": {
            "schema_version": builder.LEGACY_WORD_NORMALIZATION_SCHEMA,
            "mode": builder.LEGACY_WORD_NORMALIZATION_MODE,
            "output_granularity": "section",
            "source_chapter_files": [chapter_relative],
            "source_section_count": 2,
            "measured_word_count": 6,
            "minimum_monotonic_alignment_ratio": 0.99,
            "minimum_boundary_retention_ratio": 0.99,
            "input_sha256": {
                "timestamps": timestamp_sha256,
                "vtt": vtt_sha256,
            },
            "release_evidence_path": "internal/release-evidence.json",
            "release_evidence_sha256": builder.sha256_file(evidence_path),
        },
    }
    return {
        "repo_root": repo_root,
        "context": {
            "dirs": controlled_dirs,
            "checksum_manifest": checksum_manifest,
        },
        "slug": slug,
        "approval": approval,
        "timestamps": timestamps,
        "timestamps_path": timestamps_path,
        "vtt_path": vtt_path,
        "meta": {
            "slug": slug,
            "audio_hash": audio_sha256,
            "source_text_hash": manuscript_sha256,
            "auto_estimated_sync": False,
            "sync_score": 9.8,
        },
        "asset_facts": {
            "timestamps": {"sha256": timestamp_sha256},
            "vtt": {"sha256": vtt_sha256},
        },
        "manuscript_sha256": manuscript_sha256,
        "audio_sha256": audio_sha256,
        "evidence_path": evidence_path,
    }


def _approved_word_normalized_fixture(tmp_path: Path) -> dict[str, Any]:
    fixture = _approved_legacy_fixture(tmp_path)
    repo_root = fixture["repo_root"]
    slug = fixture["slug"]
    paths = fixture["paths"]
    source_text = "One two three.\n\nFour five six.\n"
    manuscript_sha256 = builder.hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    audio_sha256 = fixture["audio_sha256"]
    words = [
        {"word": word, "start": float(index), "end": float(index + 1)}
        for index, word in enumerate(("One", "two", "three", "Four", "five", "six"))
    ]
    _write_json(
        paths["timestamps"],
        {
            "slug": slug,
            "alignment_method": "openai_verbose_json_word_timestamps",
            "auto_estimated_sync": False,
            "granularity": "word",
            "audio_hash": audio_sha256,
            "source_text_hash": manuscript_sha256,
            "words": words,
        },
    )
    paths["vtt"].write_text(
        "\n".join(
            [
                "WEBVTT",
                "",
                *[
                    line
                    for index, word in enumerate(words, start=1)
                    for line in (
                        str(index),
                        (
                            f"00:00:0{index - 1}.000 --> "
                            f"00:00:0{index}.000"
                        ),
                        word["word"],
                        "",
                    )
                ],
            ]
        ),
        encoding="utf-8",
    )
    _write_json(
        paths["meta"],
        {
            "slug": slug,
            "audio_hash": audio_sha256,
            "source_text_hash": manuscript_sha256,
            "auto_estimated_sync": False,
            "duration_seconds": 600.0,
            "sync_score": 9.8,
        },
    )
    for name in ("timestamps", "vtt", "meta"):
        _rebind_fixture_asset(fixture, name)

    approval = fixture["documents"]["approval_evidence.json"]
    audiobook = fixture["documents"]["public_book.json"]["audiobook"]
    approval["source_sha256"] = manuscript_sha256
    approval["source_coverage"] = 1.0
    approval["source_coverage_method"] = (
        "audio_derived_asr_matching_characters_over_canonical_source_characters"
    )
    approval.pop("measured_paragraph_sync_score")
    approval["measured_section_boundary_score"] = 1.0
    approval["measured_section_boundary_method"] = (
        "equal_opcode_anchored_internal_boundaries"
    )
    audiobook["source_sha256"] = manuscript_sha256

    chapter_relative = "chapters/chapter-001.json"
    chapter = {
        "bookSlug": slug,
        "id": "chapter-001",
        "content": source_text.rstrip("\n"),
    }
    controlled_dirs = [
        repo_root / "data/controlled_publications" / slug,
        repo_root / "backend/data/controlled_publications" / slug,
    ]
    for directory in controlled_dirs:
        _write_json(directory / chapter_relative, chapter)
    chapter_sha256 = builder.sha256_file(controlled_dirs[0] / chapter_relative)
    timestamp_sha256 = builder.sha256_file(paths["timestamps"])
    vtt_sha256 = builder.sha256_file(paths["vtt"])
    upstream = {
        "slug": slug,
        "measured_quality": {
            "sync_score": 9.8,
            "sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "auto_estimated_sync": False,
        },
        "sidecars": {
            "timestamps": {"sha256": timestamp_sha256},
            "vtt": {"sha256": vtt_sha256},
        },
        "release_gates": {
            "source_binding": "PASS",
            "asr_source": "PASS",
            "first_last": "PASS",
            "sidecars": "PASS",
        },
    }
    upstream_path = repo_root / "internal/upstream-release-evidence.json"
    _write_json(upstream_path, upstream)
    evidence = {
        "schema_version": (
            "audiobook_package_v2_legacy_normalization_evidence.v1"
        ),
        "slug": slug,
        "status": "NORMALIZATION_INPUT_EVIDENCE_READY",
        "narration_regenerated": False,
        "release_gate_mutated": False,
        "source": {
            "chapter_path": chapter_relative,
            "chapter_sha256": chapter_sha256,
            "manuscript_sha256": manuscript_sha256,
            "section_count": 2,
            "emitted_section_count": 2,
            "anchored_internal_boundary_count": 1,
            "coalesced_boundary_count": 0,
            "boundary_retention_ratio": 1.0,
            "coverage": 1.0,
            "coverage_method": (
                "audio_derived_asr_matching_characters_over_canonical_source_characters"
            ),
        },
        "measured_quality": {
            "upstream_transcript_vtt_sync_score": 9.8,
            "upstream_sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "post_conversion_boundary_quality_score": 1.0,
            "boundary_method": "equal_opcode_anchored_internal_boundaries",
            "sync_tier": "SECTION_BOUNDARIES_EQUAL_OPCODE_MEASURED",
            "auto_estimated_sync": False,
        },
        "sidecars": upstream["sidecars"],
        "release_gates": upstream["release_gates"],
        "upstream_release_evidence": {
            "path": "internal/upstream-release-evidence.json",
            "sha256": builder.sha256_file(upstream_path),
        },
    }
    evidence_path = repo_root / "internal/normalization-evidence.json"
    _write_json(evidence_path, evidence)
    approval["approved_legacy_sidecar_normalization"] = {
        "schema_version": builder.LEGACY_WORD_NORMALIZATION_SCHEMA,
        "mode": builder.LEGACY_WORD_NORMALIZATION_MODE,
        "output_granularity": "section",
        "source_chapter_files": [chapter_relative],
        "source_section_count": 2,
        "measured_word_count": 6,
        "minimum_monotonic_alignment_ratio": 0.99,
        "minimum_boundary_retention_ratio": 0.99,
        "input_sha256": {
            "timestamps": timestamp_sha256,
            "vtt": vtt_sha256,
        },
        "release_evidence_path": "internal/normalization-evidence.json",
        "release_evidence_sha256": builder.sha256_file(evidence_path),
    }
    _write_controlled_mirrors(repo_root, fixture["documents"])
    for directory in controlled_dirs:
        _write_json(directory / chapter_relative, chapter)
        checksum_path = directory / "checksum_manifest.json"
        checksum = builder.read_json(checksum_path)
        checksum["files"].append(
            {"file": chapter_relative, "sha256": chapter_sha256}
        )
        _write_json(checksum_path, checksum)
    fixture.update(
        {
            "manuscript_sha256": manuscript_sha256,
            "normalization_evidence_path": evidence_path,
        }
    )
    return fixture


def _normalize_word_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    return builder._normalize_legacy_measured_word_sidecars(
        repo_root=fixture["repo_root"],
        context=fixture["context"],
        slug=fixture["slug"],
        approval=fixture["approval"],
        timestamps=fixture["timestamps"],
        vtt_path=fixture["vtt_path"],
        meta=fixture["meta"],
        asset_facts=fixture["asset_facts"],
        manuscript_sha256=fixture["manuscript_sha256"],
        audio_sha256=fixture["audio_sha256"],
        duration_seconds=6.0,
    )


def _add_source_equivalence(
    fixture: dict[str, Any],
    narrated_text: str,
) -> Path:
    narrated_path = fixture["repo_root"] / "internal/narrated-manuscript.txt"
    narrated_path.write_text(narrated_text, encoding="utf-8")
    narrated_sha256 = builder.sha256_file(narrated_path)
    chapter_path = fixture["context"]["dirs"][0] / "chapters/chapter-001.json"
    chapter = builder.read_json(chapter_path)
    canonical_text = str(chapter["content"]).rstrip("\n") + "\n"
    canonical_sha256 = builder.hashlib.sha256(
        canonical_text.encode("utf-8")
    ).hexdigest()
    fixture["manuscript_sha256"] = narrated_sha256
    fixture["timestamps"]["source_text_hash"] = narrated_sha256
    fixture["meta"]["source_text_hash"] = narrated_sha256
    contract = fixture["approval"]["approved_legacy_sidecar_normalization"]
    contract["source_text_equivalence"] = {
        "schema_version": "approved_legacy_source_text_equivalence.v1",
        "mode": "collapse_whitespace_only",
        "alignment_token_mode": "collapse_intraword_ascii_hyphens",
        "canonical_source_sha256": canonical_sha256,
        "narrated_manuscript_path": "internal/narrated-manuscript.txt",
        "narrated_manuscript_sha256": narrated_sha256,
    }
    evidence = builder.read_json(fixture["evidence_path"])
    evidence["source"].update(
        {
            "canonical_source_sha256": canonical_sha256,
            "manuscript_sha256": narrated_sha256,
            "narrated_manuscript_sha256": narrated_sha256,
            "text_equivalence_mode": "collapse_whitespace_only",
            "alignment_token_mode": "collapse_intraword_ascii_hyphens",
        }
    )
    _write_json(fixture["evidence_path"], evidence)
    contract["release_evidence_sha256"] = builder.sha256_file(
        fixture["evidence_path"]
    )
    return narrated_path


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


def test_legacy_measured_words_normalize_to_exact_source_sections(tmp_path):
    fixture = _legacy_word_normalization_fixture(tmp_path)

    result = _normalize_word_fixture(fixture)

    assert result["source_coverage"] == 1.0
    assert result["alignment_ratio"] == 1.0
    assert [
        (cue["start"], cue["end"], cue["text"])
        for cue in result["cues"]
    ] == [
        (0.0, 3.0, "One two three."),
        (3.0, 6.0, "Four five six."),
    ]
    assert all(
        cue["timing_origin"]
        == "measured_equal_opcode_word_anchor_bound_to_canonical_source"
        for cue in result["cues"]
    )


def test_source_equivalence_accepts_whitespace_only_and_preserves_canonical_text(
    tmp_path,
):
    fixture = _legacy_word_normalization_fixture(tmp_path)
    narrated_path = _add_source_equivalence(
        fixture,
        "One two three.\n\n\nFour   five six.\n",
    )

    result = _normalize_word_fixture(fixture)

    assert [cue["text"] for cue in result["cues"]] == [
        "One two three.",
        "Four five six.",
    ]
    assert result["narrated_manuscript_path"] == narrated_path


def test_source_equivalence_rejects_any_non_whitespace_text_change(tmp_path):
    fixture = _legacy_word_normalization_fixture(tmp_path)
    _add_source_equivalence(
        fixture,
        "One two altered.\n\nFour five six.\n",
    )

    with pytest.raises(
        builder.PackageBuildError,
        match="differ beyond whitespace",
    ):
        _normalize_word_fixture(fixture)


def test_alignment_token_mode_only_collapses_intraword_ascii_hyphens():
    assert builder._alignment_tokens("bath-tub") == ["bath", "tub"]
    assert builder._alignment_tokens(
        "bath-tub",
        collapse_intraword_hyphens=True,
    ) == ["bathtub"]
    assert builder._alignment_tokens(
        "stop--start",
        collapse_intraword_hyphens=True,
    ) == ["stop", "start"]


def test_deletion_at_section_boundary_coalesces_without_interpolation():
    sections = ["one missing", "words two", "three"]
    source_tokens = ["one", "missing", "words", "two", "three"]
    asr_tokens = ["one", "two", "three"]
    opcodes = builder.difflib.SequenceMatcher(
        None,
        source_tokens,
        asr_tokens,
        autojunk=False,
    ).get_opcodes()

    result = builder._coalesce_sections_to_equal_opcode_boundaries(
        sections=sections,
        source_boundaries=[0, 2, 4, 5],
        opcodes=opcodes,
        asr_token_word_indexes=[0, 1, 2],
        measured_word_count=3,
        minimum_retention_ratio=0.5,
    )

    assert result["sections"] == ["one missing\n\nwords two", "three"]
    assert result["word_boundaries"] == [0, 2, 3]
    assert result["anchored_internal_boundary_count"] == 1
    assert result["coalesced_boundary_count"] == 1
    assert result["boundary_quality_score"] == 1.0

    with pytest.raises(builder.PackageBuildError, match="coalesced too many"):
        builder._coalesce_sections_to_equal_opcode_boundaries(
            sections=sections,
            source_boundaries=[0, 2, 4, 5],
            opcodes=opcodes,
            asr_token_word_indexes=[0, 1, 2],
            measured_word_count=3,
            minimum_retention_ratio=0.75,
        )


def test_legacy_word_normalization_rejects_release_evidence_hash_drift(tmp_path):
    fixture = _legacy_word_normalization_fixture(tmp_path)
    fixture["evidence_path"].write_text("{}\n", encoding="utf-8")

    with pytest.raises(builder.PackageBuildError, match="evidence hash"):
        _normalize_word_fixture(fixture)


def test_legacy_word_normalization_rejects_unaligned_measured_words(tmp_path):
    fixture = _legacy_word_normalization_fixture(tmp_path)
    fixture["timestamps"]["words"] = [
        {**word, "word": "unrelated"}
        for word in fixture["timestamps"]["words"]
    ]

    with pytest.raises(builder.PackageBuildError, match="do not align safely"):
        _normalize_word_fixture(fixture)


def test_section_granularity_requires_hash_bound_normalization_contract(
    tmp_path,
    monkeypatch,
):
    fixture = _approved_legacy_fixture(tmp_path)
    timestamps = builder.read_json(fixture["paths"]["timestamps"])
    timestamps["sync_granularity"] = "section"
    for cue in timestamps["cues"]:
        cue["granularity"] = "section"
    _write_json(fixture["paths"]["timestamps"], timestamps)
    meta = builder.read_json(fixture["paths"]["meta"])
    meta["sync_granularity"] = "section"
    _write_json(fixture["paths"]["meta"], meta)
    _rebind_fixture_asset(fixture, "timestamps")
    _rebind_fixture_asset(fixture, "meta")
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match="not paragraph/stanza"):
        _validate_fixture(fixture)


def test_build_approved_word_normalization_binds_provenance_and_section_truth(
    tmp_path,
    monkeypatch,
):
    fixture = _approved_word_normalized_fixture(tmp_path)
    output_dir = tmp_path / "normalized-package"
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

    descriptor = builder.read_json(output_dir / "release-descriptor.json")
    assert result["status"] == "RELEASE_CANDIDATE_PACKAGE_BUILT"
    assert descriptor["sync_tier"] == "section"
    assert descriptor["release_candidate_evidence"]["gates"][
        "measured_sync_kind"
    ] == "equal_opcode_anchored_section_boundaries"
    assert descriptor["release_candidate_evidence"]["gates"][
        "measured_sync_score"
    ] == 1.0
    evidence_sha256 = builder.sha256_file(
        fixture["normalization_evidence_path"]
    )
    assert descriptor["release_candidate_evidence"][
        "normalization_release_evidence_sha256"
    ] == evidence_sha256
    plan = builder.read_json(output_dir / "upload-plan.json")
    evidence_asset = next(
        asset
        for asset in plan["assets"]
        if asset["asset_id"]
        == "provenance.controlled.normalization_release_evidence"
    )
    assert evidence_asset["sha256"] == evidence_sha256
    legacy_timestamps = next(
        asset
        for asset in plan["assets"]
        if asset["asset_id"] == "provenance.legacy.timestamps"
    )
    assert legacy_timestamps["sha256"] == builder.sha256_file(
        fixture["paths"]["timestamps"]
    )
    generated = builder.read_json(
        output_dir / "sidecars/chapter-001/segment-001-timestamps.json"
    )
    assert generated["sync_granularity"] == "section"
    assert generated["auto_estimated_sync"] is False
    assert all(cue["granularity"] == "section" for cue in generated["cues"])
    assert all(
        cue["timing_origin"]
        == "measured_equal_opcode_word_anchor_bound_to_canonical_source"
        for cue in generated["cues"]
    )


def test_build_approved_word_normalization_fails_closed_on_evidence_drift(
    tmp_path,
    monkeypatch,
):
    fixture = _approved_word_normalized_fixture(tmp_path)
    fixture["normalization_evidence_path"].write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(builder, "ffprobe_duration_ms", lambda path: 600_000)

    with pytest.raises(builder.PackageBuildError, match="evidence hash"):
        builder.build_approved_legacy(
            repo_root=fixture["repo_root"],
            slug=fixture["slug"],
            audio_path=fixture["paths"]["mp3"],
            timestamps_path=fixture["paths"]["timestamps"],
            vtt_path=fixture["paths"]["vtt"],
            chapters_path=fixture["paths"]["chapters"],
            meta_path=fixture["paths"]["meta"],
            output_dir=tmp_path / "must-remain-empty",
        )
