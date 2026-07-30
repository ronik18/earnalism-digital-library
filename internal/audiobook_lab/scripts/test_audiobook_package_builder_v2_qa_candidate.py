import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


SCRIPT = Path(__file__).with_name("audiobook_package_builder_v2.py")
SPEC = importlib.util.spec_from_file_location("audiobook_package_builder_v2_qa", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _controlled_documents(slug: str) -> dict[str, dict[str, Any]]:
    front_hash = "a" * 64
    back_hash = "b" * 64
    front_url = f"https://covers.example.test/{slug}/front-{front_hash}.jpg"
    back_url = f"https://covers.example.test/{slug}/back-{back_hash}.jpg"
    chapters = [
        {
            "id": "chapter-001",
            "order": 1,
            "title": "Chapter One",
            "content": "Alpha one.\n\nBeta two.\n\nGamma three.",
        },
        {
            "id": "chapter-002",
            "order": 2,
            "title": "Chapter Two",
            "content": "Delta four.\n\nEpsilon five.\n\nZeta six.",
        },
    ]
    chapter_metadata = [
        {
            "id": row["id"],
            "order": row["order"],
            "title": row["title"],
            "processing_status": "ready",
            "processing_warnings": [],
        }
        for row in chapters
    ]
    return {
        "public_book.json": {
            "slug": slug,
            "title": "Exact Candidate",
            "author": "Exact Author",
            "chapters": chapter_metadata,
            "source_hash": "1" * 64,
            "approved_to_publish": True,
            "isPublic": True,
            "isLive": True,
            "allowPublicReading": True,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "cover_status": "CLOUDINARY_ASSIGNED",
            "cover_url": front_url,
            "back_cover_url": back_url,
            "cover_dimensions": {
                "front": [1600, 2400],
                "back": [1600, 2400],
            },
        },
        "reader_manifest.json": {
            "slug": slug,
            "title": "Exact Candidate",
            "author": "Exact Author",
            "language": "en",
            "chapter_count": 2,
            "chapters": chapter_metadata,
            "audio_enabled": False,
            "audiobook_enabled": False,
        },
        "source_evidence.json": {
            "slug": slug,
            "source_hash": "1" * 64,
            "rights_basis": "Public domain source verified for commercial reuse.",
            "reader_facing_boilerplate_removed": True,
        },
        "approval_evidence.json": {
            "slug": slug,
            "approved_to_publish": True,
            "rights_tier": "A",
            "verification_status": "approved",
            "audiobook_use_approved": True,
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
        },
        "cover_approval_evidence.json": {
            "schema_version": "earnalism.cover_approval_evidence.v1",
            "slug": slug,
            "active_approvals": {
                "front": "front-event",
                "back": "back-event",
            },
            "history": [
                {
                    "event_id": "front-event",
                    "slug": slug,
                    "kind": "front",
                    "decision": "APPROVE_CANONICAL_COVER",
                    "candidate_sha256": front_hash,
                    "remote_sha256": front_hash,
                    "cloudinary": {"url": front_url},
                    "width": 1600,
                    "height": 2400,
                    "rights_basis": "Earnalism-owned graphical composition.",
                    "reader_audio_release_truth_unchanged": True,
                },
                {
                    "event_id": "back-event",
                    "slug": slug,
                    "kind": "back",
                    "decision": "APPROVE_CANONICAL_COVER",
                    "candidate_sha256": back_hash,
                    "remote_sha256": back_hash,
                    "cloudinary": {"url": back_url},
                    "width": 1600,
                    "height": 2400,
                    "rights_basis": "Earnalism-owned graphical composition.",
                    "reader_audio_release_truth_unchanged": True,
                },
            ],
        },
        "chapters": {
            row["id"]: {
                "bookSlug": slug,
                "id": row["id"],
                "order": row["order"],
                "title": row["title"],
                "content": row["content"],
                "processing_status": "ready",
                "processing_warnings": [],
            }
            for row in chapters
        },
    }


def _write_controlled(repo_root: Path, documents: dict[str, Any]) -> None:
    slug = documents["public_book.json"]["slug"]
    for mirror in ("backend/data", "data"):
        directory = repo_root / mirror / "controlled_publications" / slug
        for filename in (
            "public_book.json",
            "reader_manifest.json",
            "source_evidence.json",
            "approval_evidence.json",
            "cover_approval_evidence.json",
        ):
            _write_json(directory / filename, documents[filename])
        for chapter_id, chapter in documents["chapters"].items():
            _write_json(directory / "chapters" / f"{chapter_id}.json", chapter)
        checksum_files = [
            "approval_evidence.json",
            "cover_approval_evidence.json",
            "public_book.json",
            "reader_manifest.json",
            "source_evidence.json",
            *[
                f"chapters/{chapter_id}.json"
                for chapter_id in documents["chapters"]
            ],
        ]
        _write_json(
            directory / "checksum_manifest.json",
            {
                "slug": slug,
                "files": [
                    {
                        "file": filename,
                        "sha256": builder.sha256_file(directory / filename),
                    }
                    for filename in checksum_files
                ],
            },
        )


def _fixture(tmp_path: Path) -> dict[str, Any]:
    slug = "qa-candidate"
    repo_root = tmp_path / "repo"
    documents = _controlled_documents(slug)
    _write_controlled(repo_root, documents)
    run_dir = tmp_path / "private" / slug / "full" / "fingerprint"
    run_dir.mkdir(parents=True)
    source = "\n\n".join(
        row["content"] for row in documents["chapters"].values()
    ).strip() + "\n"
    source_path = run_dir / "sanitized_source.txt"
    source_path.write_text(source, encoding="utf-8")
    source_sha256 = builder.sha256_file(source_path)
    input_manifest_path = run_dir / "input_manifest.json"
    input_manifest = {
        "schema_version": builder.GOOGLE_PRIVATE_INPUT_SCHEMA,
        "slug": slug,
        "title": "Exact Candidate",
        "author": "Exact Author",
        "language": "en",
        "sanitized_source_sha256": source_sha256,
        "sanitized_source_characters": len(source),
        "chapter_count": 2,
        "chapter_orders": [1, 2],
        "sanitization_status": "PASS",
        "rights_status": "PASS",
        "commercial_use_allowed": True,
        "controlled_publication_path": f"data/controlled_publications/{slug}",
        "source_evidence_path": (
            f"data/controlled_publications/{slug}/source_evidence.json"
        ),
        "approval_evidence_path": (
            f"data/controlled_publications/{slug}/approval_evidence.json"
        ),
        "public_audio_release_approved": False,
    }
    _write_json(input_manifest_path, input_manifest)
    chunks = [
        paragraph
        for chapter in documents["chapters"].values()
        for paragraph in chapter["content"].split("\n\n")
    ]
    generated = []
    audio_dir = run_dir / "audio"
    audio_dir.mkdir()
    for index, text in enumerate(chunks):
        audio = audio_dir / f"chunk_{index:04d}.mp3"
        audio.write_bytes(b"ID3" + f"provider-{index}".encode("ascii"))
        generated.append(
            {
                "unit_id": f"chunk_{index:04d}",
                "text_sha256": hashlib_sha256(text),
                "characters": len(text),
                "audio_path": str(audio),
                "audio_sha256": builder.sha256_file(audio),
                "audio_size_bytes": audio.stat().st_size,
            }
        )
    manifest_path = run_dir / "full_generation_manifest.json"
    attempt_fingerprint = builder.canonical_sha256(
        {
            "schema": builder.GOOGLE_PRIVATE_PIPELINE_SCHEMA,
            "mode": "full",
            "provider": "google",
            "source_sha256": source_sha256,
            "manifest_sha256": builder.sha256_file(input_manifest_path),
            "voice": "en-GB-Chirp3-HD-Charon",
            "language_code": "en-GB",
            "speaking_rate": 0.94,
            "pitch": 0.0,
            "unit_hashes": [row["text_sha256"] for row in generated],
        }
    )
    manifest = {
        "schema_version": builder.GOOGLE_PRIVATE_PIPELINE_SCHEMA,
        "status": "FULL_GENERATION_PRIVATE_QA_PENDING",
        "mode": "full",
        "slug": slug,
        "title": "Exact Candidate",
        "author": "Exact Author",
        "provider": "google",
        "voice": "en-GB-Chirp3-HD-Charon",
        "language_code": "en-GB",
        "speaking_rate": 0.94,
        "pitch": 0.0,
        "source_sha256": source_sha256,
        "input_manifest_sha256": builder.sha256_file(input_manifest_path),
        "input_schema": builder.GOOGLE_PRIVATE_INPUT_SCHEMA,
        "attempt_fingerprint": attempt_fingerprint,
        "audition_evidence_sha256": "3" * 64,
        "unit_count": len(generated),
        "unit_hashes": [row["text_sha256"] for row in generated],
        "provider_calls_ran": True,
        "synthesis_calls": len(generated),
        "result_manifest_path": str(manifest_path),
        "sanitized_source_copy": str(source_path),
        "input_manifest_copy": str(input_manifest_path),
        "generated_audio": generated,
        "private_output_only": True,
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_restored_byte_for_byte": True,
        "errors": [],
    }
    _write_json(manifest_path, manifest)
    manifest_sha256 = builder.sha256_file(manifest_path)
    sequence_sha256 = builder.canonical_sha256(
        [row["audio_sha256"] for row in generated]
    )
    binding_sha256 = builder.canonical_sha256(
        {
            "manifest_sha256": manifest_sha256,
            "source_sha256": source_sha256,
            "input_manifest_sha256": builder.sha256_file(input_manifest_path),
            "ordered_text_hashes": [row["text_sha256"] for row in generated],
            "ordered_audio_hashes": [row["audio_sha256"] for row in generated],
        }
    )
    reports = []
    sections = []
    all_absolute_words = []
    for index, (text, record) in enumerate(zip(chunks, generated)):
        start = index * 100.0
        words = builder._lexical_tokens(text)
        measured_words = [
            {
                "word": text,
                "start_seconds": 5.0,
                "end_seconds": 35.0,
                "probability": 0.99,
            }
        ]
        absolute_words = [
            {
                **row,
                "start_seconds": round(start + float(row["start_seconds"]), 6),
                "end_seconds": round(start + float(row["end_seconds"]), 6),
            }
            for row in measured_words
        ]
        all_absolute_words.extend(absolute_words)
        reports.append(
            {
                "index": index,
                "unit_id": record["unit_id"],
                "source_text_sha256": record["text_sha256"],
                "audio_sha256": record["audio_sha256"],
                "duration_seconds": 100.0,
                "transcript": text,
                "transcript_sha256": hashlib_sha256(text),
                "pass": True,
                "score": 10.0,
                "coverage": 1.0,
                "precision": 1.0,
                "first_words_match": True,
                "last_words_match": True,
                "ordered_content_integrity_pass": True,
                "no_missing_content": True,
                "no_duplicate_content": True,
                "no_reordered_content": True,
                "no_unexpected_content": True,
                "equal_token_count": len(words),
                "missing_tokens": {},
                "duplicate_tokens": {},
                "unexpected_tokens": {},
                "ordered_alignment_operations": [],
                "word_timestamp_evidence_valid": True,
                "word_timestamp_anomalies": [],
                "frontmatter_absent": True,
                "audio_derived_asr_gate_pass": True,
                "audio_derived_asr_gate_blockers": [],
                "source_token_count": len(words),
                "transcript_token_count": len(words),
                "audio_derived_word_timestamps": measured_words,
                "absolute_audio_derived_word_timestamps": absolute_words,
                "word_timestamp_sha256": builder.canonical_sha256(
                    measured_words
                ),
            }
        )
        sections.append(
            {
                "unit_id": record["unit_id"],
                "source_text_sha256": record["text_sha256"],
                "audio_sha256": record["audio_sha256"],
                "start_seconds": start,
                "end_seconds": start + 100.0,
                "duration_seconds": 100.0,
                "audio_derived_word_timestamp_sha256": (
                    builder.canonical_sha256(measured_words)
                ),
                "binding_pass": True,
                "contiguous_measured_interval": True,
                "duration_binding_pass": True,
            }
        )
    aggregate = {
        "pass": True,
        "score": 10.0,
        "coverage": 1.0,
        "precision": 1.0,
        "first_words_match": True,
        "last_words_match": True,
        "ordered_content_integrity_pass": True,
        "no_missing_content": True,
        "no_duplicate_content": True,
        "no_reordered_content": True,
        "no_unexpected_content": True,
        "source_token_count": sum(
            len(builder._lexical_tokens(text)) for text in chunks
        ),
        "transcript_token_count": sum(
            len(builder._lexical_tokens(text)) for text in chunks
        ),
        "equal_token_count": sum(
            len(builder._lexical_tokens(text)) for text in chunks
        ),
        "missing_tokens": {},
        "duplicate_tokens": {},
        "unexpected_tokens": {},
        "ordered_alignment_operations": [],
        "frontmatter_absent": True,
        "audio_derived_asr_gate_pass": True,
        "audio_derived_asr_gate_blockers": [],
        "audio_derived_word_timestamp_count": len(all_absolute_words),
        "audio_derived_word_timestamps_sha256": builder.canonical_sha256(
            all_absolute_words
        ),
    }
    objective_path = run_dir / "full_audio_derived_qa.json"
    objective = {
        "schema_version": builder.GOOGLE_FULL_OBJECTIVE_SCHEMA,
        "status": "FULL_AUDIO_DERIVED_ASR_SYNC_PASS_PRIVATE_ONLY",
        "slug": slug,
        "title": "Exact Candidate",
        "author": "Exact Author",
        "provider": "google",
        "voice": manifest["voice"],
        "language_code": "en-GB",
        "full_manifest_path": str(manifest_path),
        "full_manifest_sha256": manifest_sha256,
        "source_sha256": source_sha256,
        "input_manifest_sha256": builder.sha256_file(input_manifest_path),
        "attempt_fingerprint": manifest["attempt_fingerprint"],
        "candidate_audio_sequence_sha256": sequence_sha256,
        "candidate_binding_sha256": binding_sha256,
        "audio_derived_asr": {
            "status": "PASS",
            "model": "medium.en",
            "model_sha256": "4" * 64,
            "settings": {
                "initial_prompt": None,
                "word_timestamps": True,
            },
            "source_blind": True,
            "audio_derived": True,
            "provider": "local_openai_whisper",
            "provider_calls_made": False,
            "local_asr_run_count": 6,
            "required_score": builder.QA_CANDIDATE_ASR_SCORE_MIN,
            "required_coverage": builder.QA_CANDIDATE_COVERAGE_MIN,
            "chunk_count": 6,
            "reports": reports,
            "full_title_aggregate": aggregate,
        },
        "measured_sync": {
            "status": "PASS",
            "sync_pass": True,
            "sync_tier": "PARAGRAPH_OR_SECTION_SYNC_PREMIUM",
            "granularity": "measured_source_bound_section",
            "audio_derived_or_measured": True,
            "auto_estimated_sync": False,
            "public_word_level_sync_claim_allowed": False,
            "sync_score": 10.0,
            "coverage": 1.0,
            "section_count": 6,
            "total_measured_duration_seconds": 600.0,
            "sections": sections,
        },
        "objective_pass": True,
        "blockers": [],
        "next_stage": "FULL_TITLE_LISTENING_QA_PRIVATE_ONLY",
        "private_output_only": True,
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_read_or_written": False,
    }
    _write_json(objective_path, objective)
    score_fields = {
        field: minimum + (0.05 if field == "confidence_score" else 0.5)
        for field, minimum in builder.QA_CANDIDATE_LISTENING_THRESHOLDS.items()
    }
    flag_fields = {field: False for field in builder.QA_CANDIDATE_FATAL_FLAGS}
    samples = [
        {
            "sample_label": f"sample-{index}",
            "unit_id": record["unit_id"],
            "sample_audio_hash": record["audio_sha256"],
            "source_text_sha256": record["text_sha256"],
            "scores": score_fields,
            "judge_flags": flag_fields,
            "frontmatter_present": False,
            "blocker_reason": "",
        }
        for index, record in enumerate(generated)
    ]
    listening_path = run_dir / "full_listening_qa.json"
    listening = {
        "qa_schema_version": builder.GOOGLE_FULL_LISTENING_QA_SCHEMA_VERSION,
        "status": "FULL_CANDIDATE_QA_PASS_PRIVATE_ONLY",
        "slug": slug,
        "title": "Exact Candidate",
        "author": "Exact Author",
        "provider": "google",
        "voice": manifest["voice"],
        "full_manifest_sha256": manifest_sha256,
        "source_sha256": source_sha256,
        "input_manifest_sha256": builder.sha256_file(input_manifest_path),
        "candidate_audio_sequence_sha256": sequence_sha256,
        "candidate_binding_sha256": binding_sha256,
        "blockers": [],
        "private_output_only": True,
        "public_release_approved": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "provider_calls_ran": True,
        "provider_call_count": 6,
        "paid_lock_read_or_written": True,
        "paid_lock_touched": True,
        "paid_lock_restored_byte_for_byte": True,
        "paid_lock_sha256_before": "5" * 64,
        "paid_lock_sha256_after": "5" * 64,
        "listening_quality_report": {
            "qa_schema_version": 3,
            "slug": slug,
            "title": "Exact Candidate",
            "author": "Exact Author",
            "audio_hash": sequence_sha256,
            "candidate_binding_sha256": binding_sha256,
            "release_policy": "tiered_audiobook_acceptance_v1",
            "listening_quality": {
                "status": "PASS",
                "audio_hash": sequence_sha256,
                "release_policy": "tiered_audiobook_acceptance_v1",
                "samples": samples,
                "aggregate": score_fields,
                **flag_fields,
                "dialogue_emotional_sections_judged": True,
                "blockers": [],
            },
        },
    }
    _write_json(listening_path, listening)
    release_path = run_dir / "qa_candidate_release_evidence.json"
    controlled_dir = repo_root / "backend/data/controlled_publications" / slug
    release_evidence = {
        "schema_version": builder.QA_CANDIDATE_RELEASE_EVIDENCE_SCHEMA,
        "status": "QA_CANDIDATE_PACKAGE_BUILD_AUTHORIZED",
        "slug": slug,
        "title": "Exact Candidate",
        "author": "Exact Author",
        "controlled_source_sha256": "1" * 64,
        "manuscript_sha256": source_sha256,
        "full_generation_manifest_sha256": manifest_sha256,
        "objective_qa_sha256": builder.sha256_file(objective_path),
        "listening_qa_sha256": builder.sha256_file(listening_path),
        "candidate_audio_sequence_sha256": sequence_sha256,
        "candidate_binding_sha256": binding_sha256,
        "controlled_evidence_sha256": {
            filename: builder.sha256_file(controlled_dir / filename)
            for filename in (
                "public_book.json",
                "reader_manifest.json",
                "source_evidence.json",
                "approval_evidence.json",
                "checksum_manifest.json",
                "cover_approval_evidence.json",
            )
        },
        "controlled_chapter_sha256": {
            chapter_id: builder.sha256_file(
                controlled_dir / "chapters" / f"{chapter_id}.json"
            )
            for chapter_id in documents["chapters"]
        },
        "package_build_authorized": True,
        "public_release_authorized": False,
        "upload_authorized": False,
        "catalog_mutation_authorized": False,
        "downstream_release_gates_required": list(
            builder.QA_CANDIDATE_DOWNSTREAM_GATES
        ),
        "release_evidence_version": "qa-candidate-test-v1",
        "prepared_by": "test-governor",
        "generated_at": "2026-07-30T00:00:00Z",
    }
    _write_json(release_path, release_evidence)
    return {
        "repo_root": repo_root,
        "slug": slug,
        "documents": documents,
        "run_dir": run_dir,
        "full_manifest": manifest_path,
        "objective": objective_path,
        "listening": listening_path,
        "release": release_path,
        "output": tmp_path / "package",
    }


def hashlib_sha256(value: str) -> str:
    return builder.hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mock_media(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_duration(path: Path) -> int:
        if path.name.startswith("chunk_"):
            return 100_000
        if path.suffix == ".wav":
            return 600_000
        if "chapter-001" in path.parts:
            return 305_000
        if "chapter-002" in path.parts:
            return 295_000
        raise AssertionError(path)

    def fake_run(command: list[str]) -> None:
        target = Path(command[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            b"RIFFcandidate-master"
            if target.suffix == ".wav"
            else b"ID3delivery"
        )
        target.write_bytes(payload)

    monkeypatch.setattr(builder, "ffprobe_duration_ms", fake_duration)
    monkeypatch.setattr(builder, "run_checked", fake_run)
    monkeypatch.setattr(builder, "_validate_delivery_audio_profile", lambda _path: None)


def _build(fixture: dict[str, Any]) -> dict[str, Any]:
    return builder.build_qa_candidate(
        repo_root=fixture["repo_root"],
        slug=fixture["slug"],
        full_manifest_path=fixture["full_manifest"],
        objective_qa_path=fixture["objective"],
        listening_qa_path=fixture["listening"],
        release_evidence_path=fixture["release"],
        output_dir=fixture["output"],
    )


def test_builds_private_new_title_without_existing_public_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    _mock_media(monkeypatch)
    result = _build(fixture)
    assert result["status"] == "QA_CANDIDATE_PACKAGE_BUILT"
    assert result["chapter_count"] == 2
    assert result["segment_count"] == 2
    assert result["public_release_approved"] is False
    assert result["upload_performed"] is False
    assert result["catalog_mutation_performed"] is False
    assert result["release_blockers"] == list(builder.QA_CANDIDATE_DOWNSTREAM_GATES)
    assert not (fixture["output"] / ".private-provider-concat.txt").exists()
    semantics = json.loads(
        (fixture["output"] / "package-semantics.json").read_text(encoding="utf-8")
    )
    assert [track["chapter_id"] for track in semantics["tracks"]] == [
        "chapter-001",
        "chapter-002",
    ]
    assert semantics["sync_tier"] == "paragraph"
    assert semantics["segment_count"] == 2
    plan = json.loads(
        (fixture["output"] / "upload-plan.json").read_text(encoding="utf-8")
    )
    assert plan["release_status"] == "RELEASE_CANDIDATE"
    provider_assets = [
        row
        for row in plan["assets"]
        if row["asset_id"].startswith("provenance.provider.")
    ]
    assert len(provider_assets) == 6
    for asset in provider_assets:
        assert builder.sha256_file(Path(asset["local_path"])) == asset["sha256"]
    descriptor = json.loads(
        (fixture["output"] / "release-descriptor.json").read_text(
            encoding="utf-8"
        )
    )
    assert descriptor["known_release_blockers"] == list(
        builder.QA_CANDIDATE_DOWNSTREAM_GATES
    )
    assert descriptor["provider_source_files_unchanged"] is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("objective_score", "ASR/source score"),
        ("estimated_sync", "Measured sync"),
        ("five_samples", "six passes"),
        ("paid_lock_not_restored", "listening QA"),
        ("release_hash", "release evidence"),
        ("release_extra_field", "release evidence"),
        ("title", "title identity"),
    ],
)
def test_rejects_stale_or_nonpassing_candidate_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    message: str,
) -> None:
    fixture = _fixture(tmp_path)
    _mock_media(monkeypatch)
    if mutation == "objective_score":
        payload = json.loads(fixture["objective"].read_text(encoding="utf-8"))
        payload["audio_derived_asr"]["full_title_aggregate"]["score"] = 9.69
        _write_json(fixture["objective"], payload)
    elif mutation == "estimated_sync":
        payload = json.loads(fixture["objective"].read_text(encoding="utf-8"))
        payload["measured_sync"]["auto_estimated_sync"] = True
        _write_json(fixture["objective"], payload)
    elif mutation == "five_samples":
        payload = json.loads(fixture["listening"].read_text(encoding="utf-8"))
        payload["listening_quality_report"]["listening_quality"]["samples"].pop()
        _write_json(fixture["listening"], payload)
    elif mutation == "paid_lock_not_restored":
        payload = json.loads(fixture["listening"].read_text(encoding="utf-8"))
        payload["paid_lock_sha256_after"] = "6" * 64
        _write_json(fixture["listening"], payload)
    elif mutation == "release_hash":
        payload = json.loads(fixture["release"].read_text(encoding="utf-8"))
        payload["objective_qa_sha256"] = "f" * 64
        _write_json(fixture["release"], payload)
    elif mutation == "release_extra_field":
        payload = json.loads(fixture["release"].read_text(encoding="utf-8"))
        payload["publish_now"] = True
        _write_json(fixture["release"], payload)
    elif mutation == "title":
        payload = json.loads(fixture["full_manifest"].read_text(encoding="utf-8"))
        payload["title"] = "Wrong Candidate"
        _write_json(fixture["full_manifest"], payload)
    with pytest.raises(builder.PackageBuildError, match=message):
        _build(fixture)
    assert not fixture["output"].exists()


def test_rejects_missing_canonical_back_cover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    _mock_media(monkeypatch)
    fixture["documents"]["public_book.json"]["back_cover_url"] = ""
    _write_controlled(fixture["repo_root"], fixture["documents"])
    with pytest.raises(builder.PackageBuildError, match="back cover"):
        _build(fixture)
    assert not fixture["output"].exists()


def test_rejects_candidate_if_public_audio_was_already_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    _mock_media(monkeypatch)
    fixture["documents"]["public_book.json"]["audio_enabled"] = True
    _write_controlled(fixture["repo_root"], fixture["documents"])
    with pytest.raises(builder.PackageBuildError, match="public audio still blocked"):
        _build(fixture)
    assert not fixture["output"].exists()


def test_rejects_paragraph_cut_inside_one_measured_timestamp_group() -> None:
    context = {
        "chapter_material": {
            "chapters": [
                {
                    "id": "chapter-001",
                    "order": 1,
                    "title": "Chapter One",
                    "paragraphs": ["Alpha.", "one."],
                }
            ]
        }
    }
    objective = {
        "duration_ms": 2_000,
        "word_timestamps": [
            {
                "source_token": "alpha",
                "transcript_token": "alpha",
                "timestamp_group_id": "chunk_0000:timestamp-00000",
                "start_seconds": 0.0,
                "end_seconds": 1.0,
            },
            {
                "source_token": "one",
                "transcript_token": "one",
                "timestamp_group_id": "chunk_0000:timestamp-00000",
                "start_seconds": 0.0,
                "end_seconds": 1.0,
            },
        ],
    }
    with pytest.raises(
        builder.PackageBuildError,
        match="paragraph boundary falls inside one measured timestamp group",
    ):
        builder._measured_candidate_paragraphs(
            context=context,
            objective=objective,
        )
