#!/usr/bin/env python3
"""Build Ginni's provider-free Indic Parler/Aditi audition packet.

This module deliberately has no synthesis, ASR, listening, upload, publication,
release-gate, or paid-lock code path. It binds one future private
representative audition to canonical catalog truth, exact Bengali passages, a
pinned open-source model snapshot, and a previously unused model/voice
fingerprint.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[3]
SLUG = "book-d19e96859f"
TITLE = "গিন্নি"
AUTHOR = "রবীন্দ্রনাথ ঠাকুর"
LANGUAGE = "ben"
PROFILE = "d19-indic-parler-aditi-literary-v1"

RAW_SOURCE_SHA256 = "3c184ef8918fee4686c3ac93e17c12d7108617099c70425948cdd7cbf36b68d5"
NORMALIZED_SOURCE_SHA256 = (
    "e40d3c2cfbc303213bd4a7827dcfdc35fb75fa7e7d5078487cbecba3f1ec9646"
)
RAW_SOURCE_CHARACTERS = 6_459
NORMALIZED_SOURCE_CHARACTERS = 6_432
WORD_COUNT = 1_000

MODEL_REPO = "ai4bharat/indic-parler-tts"
MODEL_REVISION = "7b527af5ee8ed1f9a28d80b19703ed9bb8ba10ca"
MODEL_LICENSE = "Apache-2.0"
MODEL_CARD_URL = f"https://huggingface.co/{MODEL_REPO}"
MODEL_LICENSE_EVIDENCE = (
    "The official model card identifies the repository license as apache-2.0 "
    "and states that the model is permissively licensed under Apache 2.0."
)
REPOSITORY_ACCESS_EVIDENCE = (
    "Hugging Face lists the repository publicly but requires a signed-in user "
    "to share contact information and accept repository access conditions "
    "before downloading files."
)
VOICE = "Aditi"
RANDOM_SEED = 2026073001
VOICE_DESCRIPTION = (
    "Aditi speaks in Bengali with clear diction, a warm restrained literary "
    "narration style, a natural conversational cadence, subtle emotional "
    "depth, a balanced pitch, and a calm moderate pace. The recording is very "
    "clear, close-sounding, and free of background noise."
)
GENERATION_SETTINGS = {
    "do_sample": True,
    "temperature": 1.0,
    "top_k": 50,
    "top_p": 1.0,
}

MODEL_ARTIFACTS = {
    "config.json": {
        "size_bytes": 7_338,
        "sha256": "14b8b2352e854758fc2c6ad8bf72fb8330a8361cdcf79d7eb52a3f665e904cd2",
    },
    "generation_config.json": {
        "size_bytes": 223,
        "sha256": "86d035c0fd9589d60fb763aad1feafeee2040fb9cf51515a0144816cec4d029d",
    },
    "model.safetensors": {
        "size_bytes": 3_751_321_772,
        "sha256": "c68daecb60f80c8f1faf0a6d2e6ddd6de8e224fb19750f3e9a33bca43c552c90",
    },
    "special_tokens_map.json": {
        "size_bytes": 552,
        "sha256": "4859e5dbde90e059988a0a2136d8df3f2773d4d2fc4c4543690028f0b2166e7f",
    },
    "tokenizer.json": {
        "size_bytes": 10_272_460,
        "sha256": "8b5f3a5080f95e5333930b57181cd2a9bf387632bd7b277af5d4fea59acb58de",
    },
    "tokenizer.model": {
        "size_bytes": 1_795_391,
        "sha256": "bc8fa773221597d09cfadb23a2b1bd717488a0481505469ea56d42cb044de9b5",
    },
    "tokenizer_config.json": {
        "size_bytes": 990,
        "sha256": "47baa70cba964a32daa581a4af50b4f2c77edaa18bec2257660133ab204ca36f",
    },
}

RUNTIME_PACKAGES = (
    "torch",
    "transformers",
    "parler-tts",
    "soundfile",
    "sentencepiece",
    "accelerate",
    "scipy",
    "huggingface-hub",
)

PASSAGE_SPECS = (
    {
        "passage_id": "opening_character_control",
        "paragraph_start": 0,
        "paragraph_end": 1,
        "start_offset": 0,
        "end_offset": 397,
        "characters": 397,
        "sha256": "b825c5484e8f9adc1799fd22c836dff9ae8df6c4eba26089d9a3c5f143ace74a",
        "risk": "opening exposition, archaic Bengali diction, and controlled comic menace",
    },
    {
        "passage_id": "satirical_punctuation",
        "paragraph_start": 2,
        "paragraph_end": 2,
        "start_offset": 399,
        "end_offset": 813,
        "characters": 414,
        "sha256": "077f56ee06d735775daa9ed19459e92cc51d0f5b7bc0653f9503a722dea7a354",
        "risk": "long clauses, semicolons, rhetorical contrast, and non-mechanical pauses",
    },
    {
        "passage_id": "play_scene_dialogue",
        "paragraph_start": 20,
        "paragraph_end": 22,
        "start_offset": 4_944,
        "end_offset": 5_443,
        "characters": 499,
        "sha256": "a02fe5e8b1e6d282dbada2411d9110f8397ccdde41d07338b0c5b085f35b0b99",
        "risk": "child dialogue, embedded quotation, domestic warmth, and sudden recognition",
    },
    {
        "passage_id": "ending_emotional_release",
        "paragraph_start": 25,
        "paragraph_end": 26,
        "start_offset": 5_981,
        "end_offset": 6_452,
        "characters": 471,
        "sha256": "ddaaa9b4c370f999dcd0fd1ddce67c8b23965c5cecca13c680618474e684c9d3",
        "risk": "rising shame, tears, cruel chanting, and a restrained final cadence",
    },
)
PASSAGE_CHARACTERS = 1_781

NO_REPEAT_FILES = (
    ROOT / "internal/earnalism_intelligence/provider_performance_memory.json",
    ROOT / "internal/earnalism_intelligence/title_decision_history.json",
    ROOT / "internal/earnalism_intelligence/bengali_audiobook_campaign_state.json",
    ROOT / "internal/earnalism_intelligence/bengali_audiobook_campaign_queue.json",
    ROOT / "internal/earnalism_intelligence/bengali_audiobook_campaign_ledger.jsonl",
)

DEFAULT_PRIVATE_OUTPUT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    "internal/audiobook_lab/private_runs/indic_parler/book-d19e96859f/"
    "7b527af5-aditi-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "book-d19e96859f_indic_parler_aditi_private_preflight_v1.json"
)


class D19IndicParlerPreflightError(RuntimeError):
    """Raised when any fail-closed packet binding is violated."""


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D19IndicParlerPreflightError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise D19IndicParlerPreflightError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temp, path)


def _expect(
    mapping: Mapping[str, Any], expected: Mapping[str, Any], label: str
) -> None:
    for key, value in expected.items():
        observed = mapping.get(key)
        if observed != value:
            raise D19IndicParlerPreflightError(
                f"{label} changed for {key}: expected {value!r}, observed {observed!r}"
            )


def assert_private_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    rendered = f"{resolved.as_posix().lower()}/"
    forbidden = (
        "/frontend/public/",
        "/frontend/build/",
        "/public/audio/",
        "/static/audio/",
    )
    if any(item in rendered for item in forbidden):
        raise D19IndicParlerPreflightError(
            f"public audio path is forbidden: {resolved}"
        )
    private_marker = "/internal/audiobook_lab/private_runs/"
    temp_root = Path(tempfile.gettempdir()).resolve()
    if private_marker not in rendered and not (
        resolved == temp_root or temp_root in resolved.parents
    ):
        raise D19IndicParlerPreflightError(
            "future output must stay under the private run root or OS temp root"
        )
    return resolved


def _publication_root(asset_root: Path, prefix: str) -> Path:
    return asset_root / prefix / "controlled_publications" / SLUG


def _assert_mirrors(asset_root: Path) -> None:
    root = _publication_root(asset_root, "data")
    backend = _publication_root(asset_root, "backend/data")
    for relative in (
        "public_book.json",
        "approval_evidence.json",
        "source_evidence.json",
        "chapters/chapter-001.json",
    ):
        root_path = root / relative
        backend_path = backend / relative
        if not root_path.is_file() or not backend_path.is_file():
            raise D19IndicParlerPreflightError(
                f"controlled-publication mirror file missing: {relative}"
            )
        if root_path.read_bytes() != backend_path.read_bytes():
            raise D19IndicParlerPreflightError(
                f"controlled-publication mirror drift: {relative}"
            )


def controlled_source(
    asset_root: Path, slug: str
) -> tuple[Path, str, list[dict[str, Any]], dict[str, str]]:
    if slug != SLUG:
        raise D19IndicParlerPreflightError(f"only {SLUG} is permitted; observed {slug}")
    _assert_mirrors(asset_root)
    publication = _publication_root(asset_root, "data")
    book = read_json(publication / "public_book.json")
    _expect(
        book,
        {
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "isLive": True,
            "isPublic": True,
            "readerStatus": "reader_ready",
            "publicationStatus": "live",
            "audiobook_enabled": False,
            "audio_enabled": False,
            "generate_audiobook": False,
            "audiobook_assets": {},
            "audiobook": {},
            "source_hash": RAW_SOURCE_SHA256,
            "rights_tier": "A",
            "verification_status": "approved",
        },
        "controlled catalog truth",
    )
    covers = {
        "front_cover_url": str(book.get("cover_url") or ""),
        "back_cover_url": str(book.get("back_cover_url") or ""),
    }
    if not all(
        value.startswith("https://res.cloudinary.com/") for value in covers.values()
    ):
        raise D19IndicParlerPreflightError(
            "canonical front/back cover pair is incomplete"
        )

    source = read_json(publication / "source_evidence.json")
    _expect(
        source,
        {
            "slug": SLUG,
            "source_hash": RAW_SOURCE_SHA256,
            "reader_facing_boilerplate_removed": True,
        },
        "source rights evidence",
    )
    if "public domain" not in str(source.get("rights_basis", "")).lower():
        raise D19IndicParlerPreflightError("literary rights basis is not public-domain")

    approval = read_json(publication / "approval_evidence.json")
    _expect(
        approval,
        {
            "slug": SLUG,
            "approved_to_publish": True,
            "rights_tier": "A",
            "verification_status": "approved",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
            "audiobook_enabled": False,
        },
        "approval evidence",
    )

    chapter_path = publication / "chapters/chapter-001.json"
    chapter = read_json(chapter_path)
    _expect(
        chapter,
        {
            "id": "chapter-001",
            "bookSlug": SLUG,
            "language": LANGUAGE,
            "content_hash": RAW_SOURCE_SHA256,
            "sourceSha256": RAW_SOURCE_SHA256,
            "sanitizedSha256": RAW_SOURCE_SHA256,
            "word_count": WORD_COUNT,
            "processing_status": "ready",
            "processing_warnings": [],
        },
        "controlled chapter truth",
    )
    manuscript = chapter.get("content")
    if not isinstance(manuscript, str):
        raise D19IndicParlerPreflightError("controlled manuscript is missing")
    if len(manuscript) != RAW_SOURCE_CHARACTERS:
        raise D19IndicParlerPreflightError("controlled manuscript length changed")
    if sha256_text(manuscript) != RAW_SOURCE_SHA256:
        raise D19IndicParlerPreflightError("controlled manuscript SHA-256 changed")
    normalized = re.sub(r"\s+", " ", manuscript).strip()
    if (
        len(normalized) != NORMALIZED_SOURCE_CHARACTERS
        or sha256_text(normalized) != NORMALIZED_SOURCE_SHA256
    ):
        raise D19IndicParlerPreflightError("normalized manuscript binding changed")

    paragraphs = manuscript.split("\n\n")
    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        text = "\n\n".join(
            paragraphs[int(spec["paragraph_start"]) : int(spec["paragraph_end"]) + 1]
        )
        start = manuscript.find(text)
        end = start + len(text)
        if (
            start != spec["start_offset"]
            or end != spec["end_offset"]
            or len(text) != spec["characters"]
            or sha256_text(text) != spec["sha256"]
        ):
            raise D19IndicParlerPreflightError(
                f"canonical passage binding changed: {spec['passage_id']}"
            )
        passages.append(
            {
                "passage_id": spec["passage_id"],
                "start_offset": start,
                "end_offset": end,
                "characters": len(text),
                "text": text,
                "text_sha256": spec["sha256"],
                "risk": spec["risk"],
            }
        )
    if sum(int(item["characters"]) for item in passages) != PASSAGE_CHARACTERS:
        raise D19IndicParlerPreflightError("representative passage total changed")
    return chapter_path, manuscript, passages, covers


def attempt_fingerprint(passages: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "contract": "earnalism.indic_parler.d19_private_preflight.v1",
        "slug": SLUG,
        "profile": PROFILE,
        "source_sha256": RAW_SOURCE_SHA256,
        "passage_hashes": [item["text_sha256"] for item in passages],
        "model_repo": MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "voice": VOICE,
        "voice_description": VOICE_DESCRIPTION,
        "generation_settings": GENERATION_SETTINGS,
        "random_seed": RANDOM_SEED,
        "scope": "four_passage_private_representative_preflight_only",
    }
    return sha256_text(json.dumps(contract, sort_keys=True, separators=(",", ":")))


def _attempt_records(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, dict):
        if any("fingerprint" in str(key).lower() for key in value):
            yield value
        for child in value.values():
            yield from _attempt_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from _attempt_records(child)


def _consumed_fingerprint(record: Mapping[str, Any], fingerprint: str) -> bool:
    fingerprints = {
        str(value)
        for key, value in record.items()
        if "fingerprint" in str(key).lower() and isinstance(value, str)
    }
    if fingerprint not in fingerprints:
        return False
    if any(
        bool(record.get(key))
        for key in (
            "audio_generated",
            "provider_calls_ran",
            "attempt_consumed",
            "execution_result_recorded",
        )
    ):
        return True
    status = " ".join(
        str(record.get(key) or "") for key in ("status", "result", "decision")
    ).upper()
    return any(token in status for token in ("CLOSED", "PASS", "FAIL", "REJECT"))


def ensure_not_repeated(fingerprint: str, output: Path) -> None:
    for evidence in NO_REPEAT_FILES:
        if not evidence.is_file():
            continue
        try:
            value: Any = json.loads(evidence.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            value = [
                json.loads(line)
                for line in evidence.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if any(
            _consumed_fingerprint(record, fingerprint)
            for record in _attempt_records(value)
        ):
            raise D19IndicParlerPreflightError(
                f"attempt fingerprint was already consumed in {evidence}"
            )
    if output.is_file() and output.stat().st_size:
        prior = read_json(output)
        prior_fingerprint = str(
            (prior.get("engine") or {}).get("attempt_fingerprint") or ""
        )
        audio_generated = bool((prior.get("safety") or {}).get("audio_generated"))
        if prior_fingerprint == fingerprint and audio_generated:
            raise D19IndicParlerPreflightError(
                "this exact fingerprint already generated audio"
            )


def runtime_evidence(snapshot_dir: Path | None, verify: bool) -> dict[str, Any]:
    packages: dict[str, str | None] = {}
    missing_packages: list[str] = []
    for package in RUNTIME_PACKAGES:
        try:
            observed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            observed = None
            missing_packages.append(package)
        packages[package] = observed

    artifact_checks: dict[str, Any] = {}
    snapshot_verified = False
    if snapshot_dir is not None:
        snapshot = snapshot_dir.expanduser().resolve()
        if snapshot.name != MODEL_REVISION:
            raise D19IndicParlerPreflightError(
                f"model snapshot revision mismatch: {snapshot.name}"
            )
        for relative, expected in MODEL_ARTIFACTS.items():
            path = snapshot / relative
            if not path.is_file():
                raise D19IndicParlerPreflightError(
                    f"pinned model artifact is missing: {relative}"
                )
            size = path.stat().st_size
            digest = sha256_file(path)
            if size != expected["size_bytes"] or digest != expected["sha256"]:
                raise D19IndicParlerPreflightError(
                    f"pinned model artifact binding changed: {relative}"
                )
            artifact_checks[relative] = {
                "size_bytes": size,
                "sha256": digest,
            }
        snapshot_verified = True
    if verify and snapshot_dir is None:
        raise D19IndicParlerPreflightError(
            "--verify-runtime requires --model-snapshot-dir"
        )
    runtime_ready = snapshot_verified and not missing_packages
    if verify and not runtime_ready:
        raise D19IndicParlerPreflightError(
            "runtime dependencies missing: " + ", ".join(missing_packages)
        )
    return {
        "status": (
            "PINNED_PRIVATE_RUNTIME_VERIFIED"
            if runtime_ready
            else "PRIVATE_RUNTIME_PREFLIGHT_REQUIRED"
        ),
        "runtime_ready": runtime_ready,
        "model_snapshot_verified": snapshot_verified,
        "model_snapshot_revision": MODEL_REVISION,
        "artifact_checks": artifact_checks,
        "package_versions": packages,
        "missing_packages": missing_packages,
    }


def build_preflight(
    *,
    asset_root: Path,
    slug: str,
    profile: str,
    private_output_dir: Path,
    output: Path,
    model_snapshot_dir: Path | None = None,
    verify_runtime: bool = False,
) -> dict[str, Any]:
    if profile != PROFILE:
        raise D19IndicParlerPreflightError(f"unsupported profile: {profile}")
    private_dir = assert_private_path(private_output_dir)
    chapter_path, manuscript, passages, covers = controlled_source(asset_root, slug)
    fingerprint = attempt_fingerprint(passages)
    ensure_not_repeated(fingerprint, output)
    runtime = runtime_evidence(model_snapshot_dir, verify_runtime)
    execution_blockers: list[str] = []
    if not runtime["runtime_ready"]:
        execution_blockers.append("PINNED_PRIVATE_RUNTIME_NOT_VERIFIED")
    release_blockers = [
        "REPRESENTATIVE_AUDIO_NOT_GENERATED",
        "REPRESENTATIVE_ASR_NOT_RUN",
        "INDEPENDENT_LISTENING_QA_NOT_RUN",
        "FULL_TITLE_NOT_GENERATED",
        "MEASURED_FULL_TITLE_SYNC_NOT_RUN",
        "PRIVATE_UPLOAD_CHECKSUM_NOT_RUN",
        "PRODUCTION_ENDPOINT_NOT_RUN",
        "BROWSER_PLAYBACK_GATE_NOT_RUN",
    ]
    non_blocking_provenance_notes = [
        "HF_REPOSITORY_ACCESS_ACKNOWLEDGEMENT_RECEIPT_NOT_RECORDED"
    ]
    return {
        "schema": "earnalism.indic_parler.d19_private_preflight.v1",
        "generated_at": utc_now(),
        "status": "PACKET_READY_EXECUTION_BLOCKED",
        "go_no_go": "NO_GO_AUDIO_EXECUTION",
        "scope": {
            "slug": SLUG,
            "title": TITLE,
            "author": AUTHOR,
            "language": LANGUAGE,
            "profile": PROFILE,
            "passage_count": len(passages),
            "characters": PASSAGE_CHARACTERS,
            "representative_only": True,
            "full_title_generated": False,
        },
        "selection": {
            "reason": (
                "Shortest source-bound, rights-clear, front/back-cover-ready hidden "
                "Sprint 1 Bengali title after excluding Muchiram's exhausted lane."
            ),
            "current_title_state_preserved": "HUMAN_NARRATION_REQUIRED",
            "prior_closed_provider_families": ["google", "sarvam"],
            "new_model_voice_has_no_recorded_execution_result": True,
        },
        "source": {
            "chapter_path": str(chapter_path),
            "raw_source_characters": len(manuscript),
            "raw_source_sha256": RAW_SOURCE_SHA256,
            "normalized_source_sha256": NORMALIZED_SOURCE_SHA256,
            "word_count": WORD_COUNT,
            "rights_basis": (
                "Rabindranath Tagore died in 1941; the original literary work is "
                "public domain in India and the U.S."
            ),
            "front_cover_url": covers["front_cover_url"],
            "back_cover_url": covers["back_cover_url"],
            "excluded_source_tail": {
                "text": "১২৯৮?",
                "reason": "source publication-year marker excluded from this audition packet",
                "full_title_editorial_decision_required": True,
            },
            "passages": passages,
        },
        "engine": {
            "family": "open_source_local_tts",
            "provider": "indic-parler-tts",
            "model_repo": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "voice": VOICE,
            "voice_language": "Bengali",
            "voice_description": VOICE_DESCRIPTION,
            "generation_settings": GENERATION_SETTINGS,
            "random_seed": RANDOM_SEED,
            "attempt_fingerprint": fingerprint,
            "browser_or_system_speech_fallback": False,
        },
        "runtime_evidence": runtime,
        "artifact_contract": MODEL_ARTIFACTS,
        "rights": {
            "model_license": MODEL_LICENSE,
            "official_model_card_url": MODEL_CARD_URL,
            "model_license_evidence": MODEL_LICENSE_EVIDENCE,
            "model_license_status": "VERIFIED_OFFICIAL_MODEL_CARD_APACHE_2_0",
            "commercial_use_allowed_under_recorded_license": True,
            "commercial_rights_decision": "ALLOWED_BY_APACHE_2_0_MODEL_LICENSE",
            "repository_access_mode_evidence": REPOSITORY_ACCESS_EVIDENCE,
            "repository_access_acknowledgement_receipt_recorded": False,
            "repository_access_acknowledgement_is_commercial_rights_gate": False,
            "repository_access_acknowledgement_effect": (
                "NON_BLOCKING_PROVENANCE_NOTE_FOR_EXISTING_LOCAL_SNAPSHOT"
            ),
            "private_audition_rights_status": (
                "PERMITTED_BY_RECORDED_APACHE_2_0_MODEL_LICENSE"
            ),
            "public_audio_release_approved": False,
        },
        "future_objective_qa_contract": {
            "asr_source_score_min": 9.7,
            "coverage_min": 0.98,
            "first_words_required": True,
            "last_words_required": True,
            "ordered_content_integrity_required": True,
            "measured_sync_required": True,
            "estimated_sync_allowed": False,
            "listening_score_min": 9.2,
            "listening_confidence_min": 0.9,
            "fatal_flags_allowed": [],
        },
        "next_stage_contract": {
            "scope": "these four exact source-bound passages only",
            "full_title_generation_allowed": False,
            "upload_allowed": False,
            "publication_allowed": False,
            "release_gate_mutation_allowed": False,
            "requirements": [
                (
                    "preserve the official Apache-2.0 model-license evidence "
                    "separately from the Hugging Face access acknowledgement"
                ),
                "verify the pinned snapshot and local runtime without loading the model",
                "preserve this exact fingerprint, passages, voice description, and seed",
                "write any later audition only beneath the recorded private output path",
                "run local objective QA before any listening evaluation",
            ],
        },
        "safety": {
            "private_output_dir": str(private_dir),
            "provider_calls": 0,
            "estimated_provider_cost_usd": 0.0,
            "paid_tts_lock_inspected": False,
            "paid_tts_lock_touched": False,
            "audio_generated": False,
            "asr_run": False,
            "listening_qa_run": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_gate_mutated": False,
            "public_audio_status": "AUDIO_HIDDEN_NOT_PUBLIC",
        },
        "private_audition_execution_blockers": execution_blockers,
        "release_blockers": release_blockers,
        "non_blocking_provenance_notes": non_blocking_provenance_notes,
        "blockers_to_execution_and_release": execution_blockers + release_blockers,
        "next_exact_command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            "/Users/ronikbasak/Documents/GitHub/"
            "earnalism-digital-library-audio-v2/.venv-audio/bin/python "
            "internal/audiobook_lab/scripts/"
            "sprint1_d19_indic_parler_private_preflight.py --preflight "
            "--verify-runtime --model-snapshot-dir "
            "/Users/ronikbasak/.cache/huggingface/hub/"
            "models--ai4bharat--indic-parler-tts/snapshots/"
            f"{MODEL_REVISION} --output /private/tmp/"
            "book-d19e96859f_indic_parler_aditi_runtime_preflight.json"
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="required safety mode")
    parser.add_argument("--verify-runtime", action="store_true")
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--profile", default=PROFILE)
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    parser.add_argument("--model-snapshot-dir", type=Path)
    parser.add_argument(
        "--private-output-dir", type=Path, default=DEFAULT_PRIVATE_OUTPUT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.preflight:
        raise D19IndicParlerPreflightError(
            "--preflight is required; this script cannot execute audio"
        )
    payload = build_preflight(
        asset_root=args.asset_root.resolve(),
        slug=args.slug,
        profile=args.profile,
        private_output_dir=args.private_output_dir,
        output=args.output,
        model_snapshot_dir=args.model_snapshot_dir,
        verify_runtime=args.verify_runtime,
    )
    atomic_write_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
