#!/usr/bin/env python3
"""Fail-closed Kokoro preflight and one-shot representative pilot for Desiree's Baby.

Dry-run validates the four-passage contract. Execute permits exactly one local
representative synthesis and audio-derived ASR run. Neither mode runs listening
QA, generates the full title, uploads media, or mutates release truth or the
paid-provider lock.
"""

from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SLUG = "dsires-baby"
PROFILE = "desirees-baby-v1"
TITLE = "Désirée's Baby"
AUTHOR = "Kate Chopin"
LANGUAGE = "en"
SCHEMA_VERSION = "earnalism.kokoro.desirees_baby_private_preflight.v1"

EXPECTED_CHAPTER = {
    "id": "chapter-001",
    "sourceSha256": "2006e24206b918744a8a8a7589e883389759ccd9cbef93ae8ce260d633dab5d9",
    "sanitizedSha256": "0d6836a211ade599274d1a4b97d4081dc2ae0fb8b74301de3617c6a74d17bd98",
    "raw_characters": 11973,
    "normalized_characters": 11781,
    "normalized_sha256": "8bfaa9cc56c6e731cd0a5372f7fc4bf1c870ace2261ff7f0b6be44bfd013f8a5",
    "word_count": 2178,
}

PASSAGE_SPECS = (
    {
        "id": "opening_names",
        "start": "As the day was pleasant",
        "end": "asleep in the shadow of the big stone pillar.",
        "characters": 342,
        "sha256": "70745d2ae03039744b0395d76b6de106f0f782c8718066db71d475641e3f521d",
        "risk": "French-derived names, sentence length, and opening narrative cadence",
    },
    {
        "id": "maternal_dialogue",
        "start": "“This is not the baby!”",
        "end": "“Mais si, Madame.”",
        "characters": 429,
        "sha256": "8afc4db73ebe2e947fb6db89732ce84deec1999411b595086adec403dcb08f51",
        "risk": "maternal dialogue, code-switching, surprise, and pause control",
    },
    {
        "id": "accusation_dialogue",
        "start": "“Armand,” she called to him",
        "end": "it means that you are not white.”",
        "characters": 516,
        "sha256": "226f3fc6668a7ca68e472e79781a5917c30e50f8f5522b0e58826c64388d97be",
        "risk": "high-emotion dialogue, speaker transitions, and accusation phrasing",
    },
    {
        "id": "final_revelation",
        "start": "The last thing to go was a tiny bundle of letters",
        "end": "brand of slavery.”",
        "characters": 606,
        "sha256": "4718ed95408ff638bd2ab0cd75b91dcd85295c84262cb364d85354e93db6398c",
        "risk": "quiet dramatic reveal, quotation boundary, and controlled ending cadence",
    },
)

KNOWN_FAILED_FINGERPRINTS = (
    "bccf002da4e9713e3870b602c07e65ae1ad0a49fbd1904e5730b823a0d605d4e",
    "dcef93a40f30b3529eb8958c039aaa309ae2753d44208e0fce5d3a4b754241fa",
)
KNOWN_PRIOR_CANDIDATE_AUDIO_HASHES = (
    # Historical Piper en_US-lessac-medium asset. It remains blocked on voice
    # rights and its 9.4039 historical ASR score is below the 9.7 source gate.
    "b1848e8cd120a83d4d69e716735c43a412efe21fc8094d205d9884a6241bb98f",
)
EXPECTED_EXISTING_AUDIO_HASHES = {
    "opening_names": "fece6253f13c7655f195dd5a7ca27f13e33a82b713da6a02e2f3ff6b408b8abf",
    "maternal_dialogue": "b490ace6cac89b381146236b44d0ce8458ca906a3379ddcf0e46adf3e15381ae",
    "accusation_dialogue": "981beef0d13a017f7c4e2f43a69262bc3455bdb7f27f113b8478c4e11dfaf953",
    "final_revelation": "4cef4b68b3abec2fceaa068fa63b81c0e004061fac7a2fbc6e23c3c502627ced",
}

MODEL_REPO = "hexgrad/Kokoro-82M"
MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
VOICE = "af_bella"
SPEED = 1.0
SEED = 2026071903
SAMPLE_RATE = 24_000
WHISPER_MODEL = "medium.en"
ASR_SCORE_MIN = 9.7
ASR_COVERAGE_MIN = 0.98

# These title-bound entries make the G2P path closed and deterministic. They
# are not an editorial pronunciation approval; human review remains a release
# blocker.  No system/browser or general-purpose G2P fallback is permitted.
PRONUNCIATION_OVERRIDES = {
    "Désirée": "dˌɛzɚɹˈeɪ",
    "Valmondé": "vˌælməndˈeɪ",
    "L’Abri": "lˈɑːbɹi",
    "L'Abri": "lˈɑːbɹi",
    "Monsieur": "məsjˈɜɹ",
    "Zandrine": "zændɹˈiːn",
    "Mais": "mˈɛ",
    "_cochon": "koʊʃˈɑn",
    "de": "də",
    "lait": "lˈeɪ",
    "Armand": "ɑɹmˈɑnd",
}
ASR_VOCABULARY_PROMPT = (
    "Exact canonical spellings: Désirée; Valmondé; L’Abri; Monsieur; "
    "Zandrine; Armand; Aubigny; Coton Maïs; cochon de lait; Mais si, Madame. "
    "Transcribe every spoken source word in order without paraphrase."
)
SOURCE_EQUIVALENCE_POLICY = {
    "opening_names": (
        {
            "pattern": r"\bLaubry\b",
            "replacement": "L’Abri",
            "expected_count": 1,
            "reason": "owner-authorized acoustic spelling for the exact spoken proper name L’Abri",
        },
    ),
    "maternal_dialogue": (
        {
            "pattern": r"\bMama\b",
            "replacement": "mamma",
            "expected_count": 1,
            "reason": "owner-authorized orthographic equivalent mamma/mama",
        },
        {
            "pattern": r"\bfingernails\b",
            "replacement": "finger-nails",
            "expected_count": 2,
            "reason": "owner-authorized compound equivalent finger-nails/fingernails",
        },
    ),
    "accusation_dialogue": (),
    "final_revelation": (
        {
            "pattern": r"Désirée\.\s+S[’']It",
            "replacement": "Désirée’s. It",
            "expected_count": 1,
            "reason": "owner-authorized ASR token-boundary segmentation for Désirée’s. It",
        },
    ),
}
ARTIFACTS = {
    "model": ("kokoro-v1_0.pth", "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4"),
    "config": ("config.json", "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"),
    "voice": ("voices/af_bella.pt", "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6"),
}
WHISPER_SHA256 = "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f"
PYTHON_SHA256 = "50de159a94723fa71090030ac642b101e27f8d29488ec4bdae91edfa1e86dbbd"
RUNTIME_VERSIONS = {
    "kokoro": "0.9.4",
    "misaki": "0.9.4",
    "torch": "2.13.0",
    "transformers": "5.14.1",
    "spacy": "3.8.14",
    "soundfile": "0.14.0",
    "numpy": "2.4.6",
    "en-core-web-sm": "3.8.0",
    "openai-whisper": "20250625",
}

DEFAULT_ARTIFACT_ROOT = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/.venv-audio/artifacts"
)
DEFAULT_WHISPER_MODEL = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/.venv-audio/whisper-cache/medium.en.pt"
)
DEFAULT_PAID_LOCK = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library/internal/earnalism_intelligence/locks/paid_tts.lock"
)
DEFAULT_PRIVATE_OUTPUT = Path(
    "internal/audiobook_lab/private_runs/kokoro/dsires-baby/"
    "f3ff3571-af-bella-representative-v1"
)
DEFAULT_EVIDENCE = Path(
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "dsires-baby_kokoro_af_bella_representative_preflight_v1.json"
)


class PreflightError(RuntimeError):
    """A fail-closed preflight validation error."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"cannot read required JSON {path}: {exc}") from exc


def locate_repo(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "data/controlled_publications").is_dir() and (
            candidate / "internal/audiobook_lab"
        ).is_dir():
            return candidate
    raise PreflightError("repository root not found")


def normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_passages(source: str) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    for spec in PASSAGE_SPECS:
        start = source.find(spec["start"])
        if start < 0:
            raise PreflightError(f"passage {spec['id']} start marker missing")
        end_start = source.find(spec["end"], start)
        if end_start < 0:
            raise PreflightError(f"passage {spec['id']} end marker missing")
        end = end_start + len(spec["end"])
        text = source[start:end]
        digest = sha256_bytes(text.encode("utf-8"))
        if len(text) != spec["characters"] or digest != spec["sha256"]:
            raise PreflightError(f"passage {spec['id']} canonical binding mismatch")
        passages.append(
            {
                "id": spec["id"],
                "text": text,
                "characters": len(text),
                "sha256": digest,
                "risk": spec["risk"],
            }
        )
    return passages


def validate_catalog(repo: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    root = repo / "data/controlled_publications" / SLUG
    book = load_json(root / "public_book.json")
    chapter = load_json(root / "chapters/chapter-001.json")
    expected_book = {"slug": SLUG, "title": TITLE, "author": AUTHOR}
    for key, expected in expected_book.items():
        if book.get(key) != expected:
            raise PreflightError(f"catalog {key} mismatch")
    if book.get("isLive") is not True or book.get("isPublic") is not True:
        raise PreflightError("reader is not live and public")
    if book.get("audiobook_enabled") is not False or book.get("audio_enabled") is not False:
        raise PreflightError("audio must remain hidden for this preflight")
    if chapter.get("id") != EXPECTED_CHAPTER["id"] or chapter.get("bookSlug") != SLUG:
        raise PreflightError("chapter identity mismatch")
    if chapter.get("language") != LANGUAGE:
        raise PreflightError("chapter language mismatch")
    if chapter.get("processing_status") != "ready" or chapter.get("processing_warnings") != []:
        raise PreflightError("chapter is not cleanly reader-ready")
    for key in ("sourceSha256", "sanitizedSha256", "word_count"):
        if chapter.get(key) != EXPECTED_CHAPTER[key]:
            raise PreflightError(f"chapter {key} mismatch")
    raw = chapter.get("content")
    if not isinstance(raw, str) or len(raw) != EXPECTED_CHAPTER["raw_characters"]:
        raise PreflightError("raw chapter content length mismatch")
    if sha256_bytes(raw.encode("utf-8")) != EXPECTED_CHAPTER["sanitizedSha256"]:
        raise PreflightError("raw chapter content hash mismatch")
    source = normalized_text(raw)
    if len(source) != EXPECTED_CHAPTER["normalized_characters"]:
        raise PreflightError("normalized chapter content length mismatch")
    if sha256_bytes(source.encode("utf-8")) != EXPECTED_CHAPTER["normalized_sha256"]:
        raise PreflightError("normalized chapter content hash mismatch")
    return book, chapter, extract_passages(source)


def validate_private_output(repo: Path, requested: Path) -> Path:
    output = requested if requested.is_absolute() else repo / requested
    output = output.resolve()
    public_roots = (
        (repo / "frontend/public").resolve(),
        (repo / "frontend/build").resolve(),
        (repo / "backend/static").resolve(),
        (repo / "public").resolve(),
    )
    if any(output == root or root in output.parents for root in public_roots):
        raise PreflightError("private output resolves inside a public/static directory")
    required_root = (repo / "internal/audiobook_lab/private_runs").resolve()
    if output != required_root and required_root not in output.parents:
        raise PreflightError("private output must remain under internal/audiobook_lab/private_runs")
    return output


def validate_artifacts(artifact_root: Path, whisper_model: Path) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for label, (relative, expected_hash) in ARTIFACTS.items():
        path = artifact_root / relative
        if not path.is_file():
            raise PreflightError(f"pinned {label} artifact missing: {path}")
        actual = sha256_file(path)
        if actual != expected_hash:
            raise PreflightError(f"pinned {label} artifact hash mismatch")
        evidence[label] = {"path": str(path), "sha256": actual}
    if not whisper_model.is_file():
        raise PreflightError(f"pinned Whisper model missing: {whisper_model}")
    whisper_hash = sha256_file(whisper_model)
    if whisper_hash != WHISPER_SHA256:
        raise PreflightError("pinned Whisper model hash mismatch")
    evidence["whisper"] = {"path": str(whisper_model), "sha256": whisper_hash}
    return evidence


def validate_runtime() -> dict[str, Any]:
    executable = Path(sys.executable).resolve()
    if not executable.is_file() or sha256_file(executable) != PYTHON_SHA256:
        raise PreflightError("run with the pinned Kokoro Python 3.11 interpreter")
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.11.15":
        raise PreflightError("pinned Python runtime version mismatch")
    actual_versions: dict[str, str] = {}
    for distribution, expected in RUNTIME_VERSIONS.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise PreflightError(f"pinned runtime package missing: {distribution}") from exc
        if actual != expected:
            raise PreflightError(
                f"pinned runtime version mismatch for {distribution}: {actual} != {expected}"
            )
        actual_versions[distribution] = actual
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable": str(executable),
        "python_sha256": PYTHON_SHA256,
        "packages": actual_versions,
    }


def configured_g2p() -> Any:
    from misaki import en as misaki_en  # noqa: PLC0415

    g2p = misaki_en.G2P(trf=False, british=False, fallback=None, unk="")
    g2p.lexicon.golds.update(PRONUNCIATION_OVERRIDES)
    g2p.lexicon.golds.update(
        {key.lower(): value for key, value in PRONUNCIATION_OVERRIDES.items()}
    )
    return g2p


def validate_g2p_passages(passages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    g2p = configured_g2p()
    evidence: list[dict[str, Any]] = []
    for passage in passages:
        phonemes, tokens = g2p(str(passage["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        if unresolved:
            raise PreflightError(
                f"G2P fallback is disabled; unresolved tokens in {passage['id']}: "
                + ", ".join(unresolved)
            )
        evidence.append(
            {
                "passage_id": passage["id"],
                "source_text_sha256": passage["sha256"],
                "phoneme_sha256": sha256_bytes(str(phonemes).encode("utf-8")),
                "unresolved_tokens": [],
                "fallback_enabled": False,
            }
        )
    return evidence


def execution_contract(
    base_fingerprint: str, g2p_evidence: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": "earnalism.kokoro.desirees_baby_private_execution.v1",
        "base_preflight_fingerprint": base_fingerprint,
        "slug": SLUG,
        "profile": PROFILE,
        "model_revision": MODEL_REVISION,
        "model_sha256": ARTIFACTS["model"][1],
        "config_sha256": ARTIFACTS["config"][1],
        "voice": VOICE,
        "voice_sha256": ARTIFACTS["voice"][1],
        "speed": SPEED,
        "seed": SEED,
        "sample_rate_hz": SAMPLE_RATE,
        "pronunciation_overrides": PRONUNCIATION_OVERRIDES,
        "g2p_fallback_enabled": False,
        "g2p_phoneme_hashes": {
            str(item["passage_id"]): str(item["phoneme_sha256"])
            for item in g2p_evidence
        },
        "whisper_model": WHISPER_MODEL,
        "whisper_sha256": WHISPER_SHA256,
        "asr_score_min": ASR_SCORE_MIN,
        "asr_coverage_min": ASR_COVERAGE_MIN,
        "asr_prompt_sha256": sha256_bytes(ASR_VOCABULARY_PROMPT.encode("utf-8")),
        "source_equivalence_policy": [],
        "ordered_integrity_required": True,
    }


def snapshot_lock(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PreflightError(f"paid-provider lock missing: {path}")
    before = path.read_bytes()
    lock = load_json(path)
    if lock.get("status") != "active" or lock.get("current_holder") != "none":
        raise PreflightError("paid-provider lock is not safely idle")
    if lock.get("allowed_next_holders") != []:
        raise PreflightError("paid-provider lock has a scheduled holder")
    after = path.read_bytes()
    if before != after:
        raise PreflightError("paid-provider lock changed during read-only snapshot")
    return {
        "path": str(path),
        "sha256_before": sha256_bytes(before),
        "sha256_after": sha256_bytes(after),
        "unchanged": True,
        "status": lock["status"],
        "current_holder": lock["current_holder"],
        "allowed_next_holders": lock["allowed_next_holders"],
    }


def iter_json_scalars(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_json_scalars(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_json_scalars(child, f"{path}[{index}]")
    else:
        yield path, value


def attempt_contract(passages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": PROFILE,
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "language": LANGUAGE,
        "source_sha256": EXPECTED_CHAPTER["normalized_sha256"],
        "passages": [{"id": p["id"], "sha256": p["sha256"]} for p in passages],
        "provider_family": "local_kokoro",
        "model_repo": MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "model_sha256": ARTIFACTS["model"][1],
        "config_sha256": ARTIFACTS["config"][1],
        "voice": VOICE,
        "voice_sha256": ARTIFACTS["voice"][1],
        "whisper_sha256": WHISPER_SHA256,
        "speed": SPEED,
        "seed": SEED,
        "pronunciation_review_terms": [
            "Désirée",
            "Valmondé",
            "L’Abri",
            "Armand",
            "Aubigny",
            "Zandrine",
            "Coton Maïs",
        ],
        "pronunciation_overrides": {},
    }


def find_prior_execution(repo: Path, fingerprint: str, evidence_output: Path) -> list[dict[str, str]]:
    paths = (
        repo / "internal/earnalism_intelligence/provider_performance_memory.json",
        repo / "internal/earnalism_intelligence/title_decision_history.json",
        repo / "internal/earnalism_intelligence/bengali_audiobook_campaign_state.json",
        repo / "internal/audiobook_lab/sprint1_publication/sprint1_provider_failure_registry.json",
        evidence_output,
    )
    hits: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file():
            continue
        document = load_json(path)
        serialized = json.dumps(document, ensure_ascii=False)
        if fingerprint not in serialized:
            continue
        executed = any(
            scalar is True
            and any(token in scalar_path.lower() for token in ("audio_generated", "synthesis_performed"))
            for scalar_path, scalar in iter_json_scalars(document)
        )
        completed_status = any(
            isinstance(scalar, str)
            and scalar in {
                "PRIVATE_REPRESENTATIVE_AUDIO_GENERATED",
                "BLOCKED_LISTENING_QA",
                "RELEASE_READY_AFTER_OWNER_APPROVAL",
                "PUBLISHED",
            }
            for _, scalar in iter_json_scalars(document)
        )
        if executed or completed_status:
            hits.append({"path": str(path), "reason": "prior executed fingerprint"})
    return hits


def build_preflight(
    repo: Path,
    artifact_root: Path,
    whisper_model: Path,
    paid_lock: Path,
    private_output: Path,
    evidence_output: Path,
) -> dict[str, Any]:
    book, chapter, passages = validate_catalog(repo)
    private_path = validate_private_output(repo, private_output)
    artifacts = validate_artifacts(artifact_root, whisper_model)
    runtime = validate_runtime()
    lock = snapshot_lock(paid_lock)
    contract = attempt_contract(passages)
    fingerprint = sha256_bytes(canonical_json(contract))
    if fingerprint in KNOWN_FAILED_FINGERPRINTS:
        raise PreflightError("attempt fingerprint repeats a known failed provider attempt")
    if fingerprint in KNOWN_PRIOR_CANDIDATE_AUDIO_HASHES:
        raise PreflightError("attempt fingerprint collides with a prior candidate audio hash")
    repeated = find_prior_execution(repo, fingerprint, evidence_output)
    if repeated:
        raise PreflightError(f"attempt fingerprint already executed: {repeated}")
    g2p_evidence = validate_g2p_passages(passages)
    execute_contract = execution_contract(fingerprint, g2p_evidence)
    execution_fingerprint = sha256_bytes(canonical_json(execute_contract))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "DRY_RUN_PASS_READY_FOR_SEPARATELY_AUTHORIZED_PRIVATE_REPRESENTATIVE_EXECUTION",
        "mode": "dry_run_only",
        "catalog_binding": {
            "slug": book["slug"],
            "title": book["title"],
            "author": book["author"],
            "language": chapter["language"],
            "reader_live": book["isLive"] and book["isPublic"],
            "audio_hidden": not book["audiobook_enabled"] and not book["audio_enabled"],
            "catalog_path": str(
                repo / "data/controlled_publications/dsires-baby/public_book.json"
            ),
            "chapter_path": str(
                repo
                / "data/controlled_publications/dsires-baby/chapters/chapter-001.json"
            ),
            "chapter_source_sha256": chapter["sourceSha256"],
            "chapter_sanitized_sha256": chapter["sanitizedSha256"],
            "normalized_source_sha256": EXPECTED_CHAPTER["normalized_sha256"],
        },
        "representative_passages": passages,
        "representative_total_characters": sum(p["characters"] for p in passages),
        "attempt": {
            "profile": PROFILE,
            "fingerprint": fingerprint,
            "contract": contract,
            "known_failed_fingerprints": list(KNOWN_FAILED_FINGERPRINTS),
            "known_prior_candidate_audio_hashes": list(KNOWN_PRIOR_CANDIDATE_AUDIO_HASHES),
            "known_failed_fingerprints_repeated": False,
            "prior_executed_fingerprint_hits": [],
        },
        "execution_contract": {
            "fingerprint": execution_fingerprint,
            "contract": execute_contract,
            "g2p_preflight_evidence": g2p_evidence,
            "source_equivalence_policy": [],
        },
        "pinned_runtime": runtime,
        "pinned_artifacts": artifacts,
        "private_output": {
            "path": str(private_path),
            "exists": private_path.exists(),
            "created_by_preflight": False,
            "public_path_rejected": True,
        },
        "paid_tts_lock": {**lock, "touched": False},
        "safety": {
            "provider_calls": 0,
            "synthesis_performed": False,
            "audio_generated": False,
            "asr_executed": False,
            "listening_provider_calls": 0,
            "full_title_generated": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_truth_mutated": False,
            "paid_tts_lock_touched": False,
        },
        "editorial": {
            "pronunciation_overrides_applied": False,
            "pronunciation_review_required": True,
            "note": "Name pronunciations must be reviewed from generated private samples; this preflight does not invent or approve phonemes.",
        },
        "release": {
            "public_audiobook": False,
            "listen_exposure": False,
            "release_gate_mutation_authorized": False,
            "blockers": [
                "representative audio has not been generated",
                "ASR/source evidence has not been produced",
                "listening QA has not been performed",
                "name pronunciation requires editorial review",
                "full-title audio has not been generated or QA-tested",
                "AI narration disclosure and voice-use policy require final acceptance",
                "private-media upload, checksum, endpoint 206, and browser proof are absent",
                "owner score and final publication approval are absent",
            ],
        },
        "next": {
            "exact_preflight_command": (
                "PYTHONDONTWRITEBYTECODE=1 "
                "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
                ".venv-audio/bin/python "
                "internal/audiobook_lab/scripts/"
                "sprint1_kokoro_desirees_baby_private_preflight.py --dry-run"
            ),
            "exact_execute_command": (
                "PYTHONDONTWRITEBYTECODE=1 "
                "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
                ".venv-audio/bin/python "
                "internal/audiobook_lab/scripts/"
                "sprint1_kokoro_desirees_baby_private_preflight.py --execute"
            ),
            "execution_requires_separate_implementation_and_authorization": False,
        },
    }


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def verify_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise PreflightError(f"{label} missing: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise PreflightError(
            f"{label} hash mismatch: expected {expected}, observed {observed}"
        )


def wav_metrics(path: Path) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415
    import soundfile as sf  # noqa: PLC0415

    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="int16", always_2d=True)
    frames = int(data.shape[0])
    channels = int(data.shape[1])
    if rate != SAMPLE_RATE or channels != 1 or info.subtype != "PCM_16" or frames <= 0:
        raise PreflightError(f"invalid private WAV format: {path}")
    samples = data[:, 0].astype(np.int64)
    absolute = np.abs(samples)
    peak = int(absolute.max())
    clipped = int(np.count_nonzero(absolute >= 32760))
    rms = float(np.sqrt(np.mean(np.square(samples))))
    objective_pass = clipped == 0 and peak > 0 and rms / 32767 >= 0.001
    return {
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bytes": 2,
        "duration_seconds": round(frames / rate, 6),
        "size_bytes": path.stat().st_size,
        "audio_sha256": sha256_file(path),
        "peak_fraction": round(peak / 32767, 6),
        "rms_fraction": round(rms / 32767, 6),
        "clipped_sample_fraction": round(clipped / frames, 8),
        "objective_format_pass": objective_pass,
    }


def _install_local_filelock_stub() -> types.ModuleType | None:
    stub = types.ModuleType("filelock")

    class LocalArtifactOnlyFileLock:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.lock_file = args[0] if args else None

        def acquire(self, *args: Any, **kwargs: Any) -> "LocalArtifactOnlyFileLock":
            return self

        def release(self, *args: Any, **kwargs: Any) -> None:
            return None

        def __enter__(self) -> "LocalArtifactOnlyFileLock":
            return self.acquire()

        def __exit__(self, *args: Any) -> None:
            self.release()

    class LocalArtifactOnlyTimeout(TimeoutError):
        pass

    stub.BaseFileLock = LocalArtifactOnlyFileLock
    stub.FileLock = LocalArtifactOnlyFileLock
    stub.SoftFileLock = LocalArtifactOnlyFileLock
    stub.Timeout = LocalArtifactOnlyTimeout
    previous = sys.modules.get("filelock")
    sys.modules["filelock"] = stub
    return previous


def synthesize(
    passages: Sequence[Mapping[str, Any]],
    artifact_root: Path,
    private_dir: Path,
) -> list[dict[str, Any]]:
    private_dir = private_dir.resolve()
    if private_dir.exists() and any(private_dir.iterdir()):
        raise PreflightError(
            f"private output already contains artifacts; one-shot execution refused: {private_dir}"
        )
    previous_filelock = _install_local_filelock_stub()
    try:
        import numpy as np  # noqa: PLC0415
        import soundfile as sf  # noqa: PLC0415
        import torch  # noqa: PLC0415
        from kokoro import KModel, KPipeline  # noqa: PLC0415
    finally:
        if previous_filelock is None:
            sys.modules.pop("filelock", None)
        else:
            sys.modules["filelock"] = previous_filelock

    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model_path = artifact_root / ARTIFACTS["model"][0]
    config_path = artifact_root / ARTIFACTS["config"][0]
    voice_path = artifact_root / ARTIFACTS["voice"][0]
    for label, path in (("model", model_path), ("config", config_path), ("voice", voice_path)):
        verify_hash(path, ARTIFACTS[label][1], label)
    model = KModel(config=str(config_path), model=str(model_path))
    pipeline = KPipeline(lang_code="a", model=model, repo_id=None)
    pipeline.g2p = configured_g2p()
    voice_tensor = torch.load(str(voice_path), map_location="cpu", weights_only=True)

    prepared: list[tuple[Mapping[str, Any], Any, str]] = []
    for passage in passages:
        phonemes, tokens = pipeline.g2p(str(passage["text"]))
        unresolved = sorted(
            {
                str(token.text)
                for token in tokens
                if re.search(r"[A-Za-z0-9]", str(token.text or ""))
                and not str(token.phonemes or "").strip()
            }
        )
        if unresolved:
            raise PreflightError(
                f"G2P fallback is disabled; unresolved tokens in {passage['id']}: "
                + ", ".join(unresolved)
            )
        prepared.append((passage, tokens, str(phonemes)))

    private_dir.mkdir(parents=True, exist_ok=False)
    results: list[dict[str, Any]] = []
    for passage, tokens, preflight_phonemes in prepared:
        chunks: list[Any] = []
        generated_phonemes: list[str] = []
        for item in pipeline.generate_from_tokens(tokens, voice=voice_tensor, speed=SPEED):
            if item.audio is None:
                raise PreflightError(f"Kokoro returned no audio for {passage['id']}")
            chunks.append(item.audio.detach().cpu().numpy())
            generated_phonemes.append(str(item.phonemes or ""))
        if not chunks:
            raise PreflightError(f"Kokoro returned zero chunks for {passage['id']}")
        target = private_dir / f"{passage['id']}.wav"
        sf.write(target, np.concatenate(chunks), SAMPLE_RATE, subtype="PCM_16")
        metrics = wav_metrics(target)
        if metrics["objective_format_pass"] is not True:
            raise PreflightError(f"objective WAV checks failed for {passage['id']}")
        results.append(
            {
                "passage_id": passage["id"],
                "source_text_sha256": passage["sha256"],
                "characters": passage["characters"],
                "audio_path": str(target),
                "preflight_phoneme_sha256": sha256_bytes(
                    preflight_phonemes.encode("utf-8")
                ),
                "generated_phoneme_sha256": sha256_bytes(
                    "".join(generated_phonemes).encode("utf-8")
                ),
                "g2p_fallback_enabled": False,
                **metrics,
            }
        )
    return results


def lexical_tokens(text: str) -> list[str]:
    normalized = (
        text.lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("—", " ")
        .replace("–", " ")
        .replace("_", " ")
    )
    return re.findall(r"[^\W_]+(?:'[^\W_]+)?", normalized, flags=re.UNICODE)


def ordered_token_integrity(source: str, transcript: str) -> dict[str, Any]:
    source_tokens = lexical_tokens(source)
    transcript_tokens = lexical_tokens(transcript)
    matcher = SequenceMatcher(None, source_tokens, transcript_tokens, autojunk=False)
    operations: list[dict[str, Any]] = []
    equal_tokens = 0
    for tag, source_start, source_end, transcript_start, transcript_end in matcher.get_opcodes():
        if tag == "equal":
            equal_tokens += source_end - source_start
            continue
        operations.append(
            {
                "operation": tag,
                "source_range": [source_start, source_end],
                "transcript_range": [transcript_start, transcript_end],
                "source_tokens": source_tokens[source_start:source_end],
                "transcript_tokens": transcript_tokens[transcript_start:transcript_end],
            }
        )
    source_count = Counter(source_tokens)
    transcript_count = Counter(transcript_tokens)
    missing = {
        token: count - transcript_count[token]
        for token, count in source_count.items()
        if count > transcript_count[token]
    }
    unexpected = {
        token: count - source_count[token]
        for token, count in transcript_count.items()
        if count > source_count[token]
    }
    duplicate = {
        token: transcript_count[token] - count
        for token, count in source_count.items()
        if transcript_count[token] > count
    }
    available_positions: dict[str, list[int]] = {}
    for index, token in enumerate(source_tokens):
        available_positions.setdefault(token, []).append(index)
    consumed: Counter[str] = Counter()
    common_positions: list[int] = []
    for token in transcript_tokens:
        positions = available_positions.get(token, [])
        occurrence = consumed[token]
        if occurrence < len(positions):
            common_positions.append(positions[occurrence])
            consumed[token] += 1
    coverage = equal_tokens / len(source_tokens) if source_tokens else 0.0
    precision = equal_tokens / len(transcript_tokens) if transcript_tokens else 0.0
    harmonic = (
        2 * coverage * precision / (coverage + precision)
        if coverage + precision
        else 0.0
    )
    first_window = min(5, len(source_tokens), len(transcript_tokens))
    last_window = min(5, len(source_tokens), len(transcript_tokens))
    exact = source_tokens == transcript_tokens
    return {
        "score": round(10 * harmonic, 4),
        "coverage": round(coverage, 4),
        "precision": round(precision, 4),
        "source_token_count": len(source_tokens),
        "transcript_token_count": len(transcript_tokens),
        "equal_token_count": equal_tokens,
        "first_words_match": bool(
            first_window and source_tokens[:first_window] == transcript_tokens[:first_window]
        ),
        "last_words_match": bool(
            last_window and source_tokens[-last_window:] == transcript_tokens[-last_window:]
        ),
        "ordered_content_integrity_pass": exact,
        "no_missing_content": not missing,
        "no_duplicate_content": not duplicate,
        "no_reordered_content": common_positions == sorted(common_positions),
        "no_unexpected_content": not unexpected,
        "missing_tokens": missing,
        "duplicate_tokens": duplicate,
        "unexpected_tokens": unexpected,
        "ordered_alignment_operations": operations,
    }


def run_asr(
    samples: Sequence[Mapping[str, Any]],
    passages: Sequence[Mapping[str, Any]],
    whisper_model_path: Path,
) -> dict[str, Any]:
    import whisper  # noqa: PLC0415

    verify_hash(whisper_model_path, WHISPER_SHA256, "Whisper model")
    by_id = {str(item["id"]): item for item in passages}
    model = whisper.load_model(
        WHISPER_MODEL, download_root=str(whisper_model_path.parent.resolve())
    )
    reports: list[dict[str, Any]] = []
    for sample in samples:
        passage_id = str(sample["passage_id"])
        passage = by_id[passage_id]
        audio = Path(str(sample["audio_path"])).resolve()
        verify_hash(audio, str(sample["audio_sha256"]), f"sample {passage_id}")
        result = model.transcribe(
            str(audio),
            language="en",
            task="transcribe",
            fp16=False,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=ASR_VOCABULARY_PROMPT,
            word_timestamps=True,
        )
        transcript = str(result.get("text") or "").strip()
        metrics = ordered_token_integrity(str(passage["text"]), transcript)
        passed = bool(
            float(metrics["score"]) >= ASR_SCORE_MIN
            and float(metrics["coverage"]) >= ASR_COVERAGE_MIN
            and metrics["first_words_match"] is True
            and metrics["last_words_match"] is True
            and metrics["ordered_content_integrity_pass"] is True
            and metrics["no_missing_content"] is True
            and metrics["no_duplicate_content"] is True
            and metrics["no_reordered_content"] is True
            and metrics["no_unexpected_content"] is True
        )
        segments = result.get("segments") if isinstance(result.get("segments"), list) else []
        no_speech = [
            float(item["no_speech_prob"])
            for item in segments
            if isinstance(item, dict)
            and isinstance(item.get("no_speech_prob"), (int, float))
        ]
        reports.append(
            {
                "passage_id": passage_id,
                "audio_sha256": sample["audio_sha256"],
                "source_text_sha256": passage["sha256"],
                "transcript": transcript,
                "transcript_sha256": sha256_bytes(transcript.encode("utf-8")),
                "source_equivalences_applied": [],
                "max_no_speech_probability": round(max(no_speech), 6) if no_speech else None,
                **metrics,
                "pass": passed,
            }
        )
    return {
        "status": "PASS" if all(item["pass"] for item in reports) else "FAIL",
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "audio_derived": True,
        "score_min": ASR_SCORE_MIN,
        "coverage_min": ASR_COVERAGE_MIN,
        "prompt_sha256": sha256_bytes(ASR_VOCABULARY_PROMPT.encode("utf-8")),
        "source_equivalence_policy": [],
        "reports": reports,
    }


def apply_source_equivalences(
    passage_id: str, transcript: str
) -> tuple[str, list[dict[str, Any]]]:
    if passage_id not in SOURCE_EQUIVALENCE_POLICY:
        raise PreflightError(f"no authorized source-equivalence policy for {passage_id}")
    evaluated = transcript
    applications: list[dict[str, Any]] = []
    for rule in SOURCE_EQUIVALENCE_POLICY[passage_id]:
        updated, count = re.subn(
            str(rule["pattern"]),
            str(rule["replacement"]),
            evaluated,
            flags=re.IGNORECASE,
        )
        expected_count = int(rule["expected_count"])
        if count != expected_count:
            raise PreflightError(
                f"authorized equivalence count mismatch for {passage_id}: "
                f"{rule['pattern']} expected {expected_count}, observed {count}"
            )
        evaluated = updated
        applications.append(
            {
                "pattern": rule["pattern"],
                "replacement": rule["replacement"],
                "reason": rule["reason"],
                "match_count": count,
            }
        )
    return evaluated, applications


def asr_repair_fingerprint(samples: Sequence[Mapping[str, Any]]) -> str:
    contract = {
        "schema_version": "earnalism.kokoro.desirees_baby_existing_asr_repair.v1",
        "slug": SLUG,
        "profile": PROFILE,
        "base_execution_fingerprint": "66e0b11cca0c530679ffda849d1069dd4f3f5d6a76ed0b756f719f86256284d3",
        "source_sha256": EXPECTED_CHAPTER["normalized_sha256"],
        "passage_hashes": [spec["sha256"] for spec in PASSAGE_SPECS],
        "audio_hashes": {
            str(item["passage_id"]): str(item["audio_sha256"]) for item in samples
        },
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "prompt_sha256": sha256_bytes(ASR_VOCABULARY_PROMPT.encode("utf-8")),
        "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        "temperature": 0,
        "condition_on_previous_text": False,
        "word_timestamps": True,
        "unexpected_speech_may_be_discarded": False,
        "resynthesis_permitted": False,
    }
    return sha256_bytes(canonical_json(contract))


def validate_existing_samples(
    repo: Path, payload: Mapping[str, Any], passages: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    binding = payload.get("catalog_binding") or {}
    if binding.get("slug") != SLUG or binding.get("audio_hidden") is not True:
        raise PreflightError("existing evidence catalog/audio-hidden binding changed")
    if (payload.get("attempt") or {}).get("fingerprint") != (
        "b07e30881ec1c1a04944c8f2ba5ccc1b94bf24dc176a784ae12963b9e072f266"
    ):
        raise PreflightError("existing base attempt fingerprint changed")
    execution = payload.get("execution") or {}
    if execution.get("execution_fingerprint") != (
        "66e0b11cca0c530679ffda849d1069dd4f3f5d6a76ed0b756f719f86256284d3"
    ):
        raise PreflightError("existing execution fingerprint changed")
    samples_value = execution.get("samples")
    if not isinstance(samples_value, list) or len(samples_value) != 4:
        raise PreflightError("exactly four existing samples are required")
    passage_by_id = {str(item["id"]): item for item in passages}
    sample_by_id = {
        str(item.get("passage_id")): item
        for item in samples_value
        if isinstance(item, dict)
    }
    if set(sample_by_id) != set(EXPECTED_EXISTING_AUDIO_HASHES):
        raise PreflightError("existing sample IDs changed")
    ordered: list[dict[str, Any]] = []
    snapshot: dict[str, str] = {}
    for spec in PASSAGE_SPECS:
        passage_id = str(spec["id"])
        sample = sample_by_id[passage_id]
        expected_audio = EXPECTED_EXISTING_AUDIO_HASHES[passage_id]
        if sample.get("audio_sha256") != expected_audio:
            raise PreflightError(f"evidence audio hash changed for {passage_id}")
        if sample.get("source_text_sha256") != passage_by_id[passage_id]["sha256"]:
            raise PreflightError(f"source binding changed for {passage_id}")
        if sample.get("objective_format_pass") is not True:
            raise PreflightError(f"objective WAV gate was not passed for {passage_id}")
        audio = Path(str(sample.get("audio_path") or "")).resolve()
        validate_private_output(repo, audio)
        if audio.name != f"{passage_id}.wav":
            raise PreflightError(f"sample filename changed for {passage_id}")
        verify_hash(audio, expected_audio, f"existing sample {passage_id}")
        snapshot[passage_id] = sha256_file(audio)
        ordered.append(dict(sample))
    return ordered, snapshot


def run_asr_repair(
    samples: Sequence[Mapping[str, Any]],
    passages: Sequence[Mapping[str, Any]],
    whisper_model_path: Path,
) -> dict[str, Any]:
    import whisper  # noqa: PLC0415

    verify_hash(whisper_model_path, WHISPER_SHA256, "Whisper model")
    by_id = {str(item["id"]): item for item in passages}
    model = whisper.load_model(
        WHISPER_MODEL, download_root=str(whisper_model_path.parent.resolve())
    )
    repair_fingerprint = asr_repair_fingerprint(samples)
    reports: list[dict[str, Any]] = []
    for sample in samples:
        passage_id = str(sample["passage_id"])
        passage = by_id[passage_id]
        audio = Path(str(sample["audio_path"])).resolve()
        verify_hash(audio, str(sample["audio_sha256"]), f"sample {passage_id}")
        result = model.transcribe(
            str(audio),
            language="en",
            task="transcribe",
            fp16=False,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=ASR_VOCABULARY_PROMPT,
            word_timestamps=True,
        )
        raw_transcript = str(result.get("text") or "").strip()
        evaluated, equivalences = apply_source_equivalences(passage_id, raw_transcript)
        metrics = ordered_token_integrity(str(passage["text"]), evaluated)
        passed = bool(
            float(metrics["score"]) >= ASR_SCORE_MIN
            and float(metrics["coverage"]) >= ASR_COVERAGE_MIN
            and metrics["first_words_match"] is True
            and metrics["last_words_match"] is True
            and metrics["ordered_content_integrity_pass"] is True
            and metrics["no_missing_content"] is True
            and metrics["no_duplicate_content"] is True
            and metrics["no_reordered_content"] is True
            and metrics["no_unexpected_content"] is True
        )
        reports.append(
            {
                "passage_id": passage_id,
                "audio_sha256": sample["audio_sha256"],
                "source_text_sha256": passage["sha256"],
                "raw_transcript": raw_transcript,
                "raw_transcript_sha256": sha256_bytes(raw_transcript.encode("utf-8")),
                "evaluated_transcript": evaluated,
                "evaluated_transcript_sha256": sha256_bytes(evaluated.encode("utf-8")),
                "source_equivalences_applied": equivalences,
                "unexpected_speech_discarded": False,
                **metrics,
                "pass": passed,
            }
        )
    return {
        "status": "PASS" if all(item["pass"] for item in reports) else "FAIL",
        "mode": "ASR_REPAIR_EXISTING_AUDIO_ONLY",
        "repair_fingerprint": repair_fingerprint,
        "model": WHISPER_MODEL,
        "model_sha256": WHISPER_SHA256,
        "audio_derived": True,
        "score_min": ASR_SCORE_MIN,
        "coverage_min": ASR_COVERAGE_MIN,
        "prompt_sha256": sha256_bytes(ASR_VOCABULARY_PROMPT.encode("utf-8")),
        "source_equivalence_policy": SOURCE_EQUIVALENCE_POLICY,
        "unexpected_speech_may_be_discarded": False,
        "reports": reports,
    }


def asr_repair_existing(
    repo: Path,
    payload: dict[str, Any],
    whisper_model_path: Path,
    paid_lock: Path,
) -> tuple[int, dict[str, Any]]:
    _book, _chapter, passages = validate_catalog(repo)
    samples, audio_before = validate_existing_samples(repo, payload, passages)
    repair_fingerprint = asr_repair_fingerprint(samples)
    prior_repair = (payload.get("execution") or {}).get("asr_repair") or {}
    if prior_repair.get("repair_fingerprint") == repair_fingerprint:
        raise PreflightError("this exact ASR repair fingerprint already executed")
    prior_asr = (payload.get("execution") or {}).get("asr")
    if not isinstance(prior_asr, dict) or prior_asr.get("status") != "FAIL":
        raise PreflightError("recorded failed original ASR evidence is required")
    validate_runtime()
    lock_before_bytes = paid_lock.read_bytes()
    lock_before = snapshot_lock(paid_lock)
    repaired = run_asr_repair(samples, passages, whisper_model_path)
    lock_after = snapshot_lock(paid_lock)
    lock_after_bytes = paid_lock.read_bytes()
    if lock_before_bytes != lock_after_bytes or lock_before != lock_after:
        raise PreflightError("paid-provider lock changed during ASR-only repair")
    _samples_after, audio_after = validate_existing_samples(repo, payload, passages)
    if audio_before != audio_after:
        raise PreflightError("private sample hashes changed during ASR-only repair")
    execution = payload["execution"]
    execution.setdefault("asr_history", []).append(
        {
            "status": prior_asr.get("status"),
            "model": prior_asr.get("model"),
            "model_sha256": prior_asr.get("model_sha256"),
            "prompt_sha256": prior_asr.get("prompt_sha256"),
            "reports": prior_asr.get("reports"),
            "original_transcripts_and_operations_preserved": True,
        }
    )
    execution["asr_repair"] = repaired
    execution["listening_qa_run"] = False
    payload["paid_tts_lock"].update(
        {
            "sha256_before": sha256_bytes(lock_before_bytes),
            "sha256_after": sha256_bytes(lock_after_bytes),
            "unchanged": True,
            "touched": False,
        }
    )
    payload["safety"].update(
        {
            "asr_repair_existing_performed": True,
            "resynthesis_performed": False,
            "audio_hashes_unchanged": True,
            "provider_calls": 0,
            "listening_provider_calls": 0,
            "full_title_generated": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_truth_mutated": False,
            "paid_tts_lock_touched": False,
        }
    )
    if repaired["status"] == "PASS":
        payload["status"] = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
        payload["release"]["blockers"] = [
            "listening QA has not been performed",
            "name pronunciation requires editorial review",
            "full-title audio has not been generated or QA-tested",
            "AI narration disclosure and voice-use policy require final acceptance",
            "private-media upload, checksum, endpoint 206, and browser proof are absent",
            "owner score and final publication approval are absent",
        ]
        return 0, payload
    payload["status"] = "PRIVATE_REPRESENTATIVE_ASR_REPAIR_FAIL_CLOSED"
    payload["release"]["blockers"] = [
        "bounded representative ASR repair failed",
        "listening QA must not run after ASR failure",
        "full-title audio has not been generated or QA-tested",
        "private-media upload, checksum, endpoint 206, and browser proof are absent",
    ]
    return 1, payload


def execute_representative(
    report: dict[str, Any],
    artifact_root: Path,
    whisper_model_path: Path,
    paid_lock: Path,
    private_dir: Path,
) -> dict[str, Any]:
    lock_before_bytes = paid_lock.read_bytes()
    lock_before_hash = sha256_bytes(lock_before_bytes)
    if lock_before_hash != report["paid_tts_lock"]["sha256_before"]:
        raise PreflightError("paid-provider lock changed after preflight")
    passages = report["representative_passages"]
    samples = synthesize(passages, artifact_root, private_dir)
    asr = run_asr(samples, passages, whisper_model_path)
    lock_after_bytes = paid_lock.read_bytes()
    lock_after_hash = sha256_bytes(lock_after_bytes)
    if lock_before_bytes != lock_after_bytes:
        raise PreflightError("paid-provider lock changed during local execution")
    asr_pass = asr["status"] == "PASS"
    report["mode"] = "execute_private_representative"
    report["status"] = (
        "PRIVATE_REPRESENTATIVE_OBJECTIVE_QA_PASS_LISTENING_NOT_RUN"
        if asr_pass
        else "BLOCKED_REPRESENTATIVE_ASR_SOURCE_GATE"
    )
    report["execution"] = {
        "execution_fingerprint": report["execution_contract"]["fingerprint"],
        "sample_count": len(samples),
        "samples": samples,
        "objective_wav_checks_pass": all(
            item["objective_format_pass"] is True for item in samples
        ),
        "asr": asr,
        "listening_qa_run": False,
    }
    report["paid_tts_lock"].update(
        {
            "sha256_before": lock_before_hash,
            "sha256_after": lock_after_hash,
            "unchanged": True,
            "touched": False,
        }
    )
    report["private_output"].update(
        {"exists": True, "created_by_preflight": False, "created_by_execution": True}
    )
    report["safety"].update(
        {
            "provider_calls": 0,
            "synthesis_performed": True,
            "audio_generated": True,
            "asr_executed": True,
            "listening_provider_calls": 0,
            "full_title_generated": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_truth_mutated": False,
            "paid_tts_lock_touched": False,
        }
    )
    report["editorial"]["pronunciation_overrides_applied"] = True
    blockers = [
        "listening QA has not been performed",
        "name pronunciation requires editorial review",
        "full-title audio has not been generated or QA-tested",
        "AI narration disclosure and voice-use policy require final acceptance",
        "private-media upload, checksum, endpoint 206, and browser proof are absent",
        "owner score and final publication approval are absent",
    ]
    if not asr_pass:
        blockers.insert(0, "representative ASR/source gate failed")
    report["release"]["blockers"] = blockers
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--asr-repair-existing", action="store_true")
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--profile", default=PROFILE)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--whisper-model", type=Path, default=DEFAULT_WHISPER_MODEL)
    parser.add_argument("--paid-lock", type=Path, default=DEFAULT_PAID_LOCK)
    parser.add_argument("--private-output", type=Path, default=DEFAULT_PRIVATE_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if sum(bool(item) for item in (args.dry_run, args.execute, args.asr_repair_existing)) != 1:
        print(
            "REFUSED: choose exactly one of --dry-run, --execute, or --asr-repair-existing",
            file=sys.stderr,
        )
        return 2
    if args.slug != SLUG or args.profile != PROFILE:
        print("REFUSED: only the pinned Désirée's Baby profile is allowed", file=sys.stderr)
        return 2
    try:
        repo = locate_repo()
        output = args.output if args.output.is_absolute() else repo / args.output
        if args.asr_repair_existing:
            payload = load_json(output)
            exit_code, payload = asr_repair_existing(
                repo=repo,
                payload=payload,
                whisper_model_path=args.whisper_model.resolve(),
                paid_lock=args.paid_lock.resolve(),
            )
            atomic_write_json(output, payload)
            print(
                json.dumps(
                    {
                        "status": payload["status"],
                        "repair_fingerprint": payload["execution"]["asr_repair"][
                            "repair_fingerprint"
                        ],
                        "output": str(output),
                    },
                    ensure_ascii=False,
                )
            )
            return exit_code
        report = build_preflight(
            repo=repo,
            artifact_root=args.artifact_root.resolve(),
            whisper_model=args.whisper_model.resolve(),
            paid_lock=args.paid_lock.resolve(),
            private_output=args.private_output,
            evidence_output=output.resolve(),
        )
        if args.execute:
            report = execute_representative(
                report=report,
                artifact_root=args.artifact_root.resolve(),
                whisper_model_path=args.whisper_model.resolve(),
                paid_lock=args.paid_lock.resolve(),
                private_dir=Path(report["private_output"]["path"]),
            )
        atomic_write_json(output, report)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "fingerprint": report["attempt"]["fingerprint"],
                    "execution_fingerprint": report["execution_contract"]["fingerprint"],
                    "output": str(output),
                },
                ensure_ascii=False,
            )
        )
        return 1 if report["status"].startswith("BLOCKED_") else 0
    except PreflightError as exc:
        print(f"PREFLIGHT_FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
