#!/usr/bin/env python3
"""Judge the exact four-sample Call of the Wild ``am_michael`` candidate.

This wrapper binds three immutable targeted WAVs plus the retained exact Spitz
passage. It reuses the strict schema-3 listening judge, exact-10 owner gate,
budget guard, no-repeat fingerprint, and byte-for-byte paid-lock restoration.
A pass authorizes only a private full-title decision; it is not release
evidence and cannot generate, upload, or publish.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load(
    "earnalism_call_wild_strict_private_listening_qa",
    SCRIPT_DIR / "sprint1_gift_kokoro_private_listening_qa.py",
)
PROFILE = _load(
    "call_wild_am_michael_listening_profile",
    SCRIPT_DIR / "sprint1_call_wild_am_michael_private_audition.py",
)

SLUG = "the-call-of-the-wild"
TITLE = "The Call of the Wild"
AUTHOR = "Jack London"
LANGUAGE = "eng"
SCOPE = "call_wild_am_michael_representative_listening_qa_v1"
HOLDER = "sprint1_call_wild_am_michael_private_listening_qa"
EXPECTED_SCHEMA = (
    "earnalism.kokoro.call_wild_am_michael_targeted_asr_projection.v1"
)
EXPECTED_STATUS = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
EXPECTED_EVIDENCE_SHA256 = (
    "166a3c412d8e71f12e922237e4510d462a041ea7c8d6049c984dcecb3ab24700"
)
EXPECTED_SOURCE_SHA256 = PROFILE.EXPECTED_RECONCILIATION_SHA256
EXPECTED_ATTEMPT_FINGERPRINT = (
    "86481d57a50301fa01372213d3291fe1edd42fac6eb85a032f860a017797bc71"
)
EXPECTED_ASR_CONFIG_FINGERPRINT = (
    "202233ae6913aefb18da02d8cce108edfd4bf3038955c146ec5d20aba0c60a46"
)
EXPECTED_MODEL_REVISION = PROFILE.BASE.MODEL_REVISION
EXPECTED_VOICE_SHA256 = PROFILE.VOICE_SHA256
PRIOR_REPAIR_SHA256 = (
    "62e3f5b882bf247e701f6df36af462abe0a3d8b510f2cd9de951b91d600eb898"
)
PRIOR_REPAIR_FINGERPRINT = (
    "0b990e5c8efbc8fd8eebbe347a95d36922bc00c16f814911136e4a047888b36c"
)
EXPECTED_SAMPLE_BINDINGS: dict[str, dict[str, Any]] = {
    "opening_exposition": {
        "source_text_sha256": "1791560e493d4ea492e40cca2a7ebb9722b70c1bd282a9853cb12877c5172216",
        "audio_sha256": "ce95652d03943d8f2613bdf988ecd3f3309a62e972513ee919b154dfc3288b51",
        "size_bytes": 1_860_044,
        "duration_seconds": 38.75,
    },
    "spitz_final_conflict": {
        "source_text_sha256": "11ea4acd69bd769dcbb1ac522aa27f90f47bd900a94fffaab4890279a3af5d6f",
        "audio_sha256": "ff10825d490813fd40bc2595df610216e5dd773c36196be2041c02f046d54506",
        "size_bytes": 4_891_244,
        "duration_seconds": 101.9,
    },
    "thornton_bond": {
        "source_text_sha256": "a0f70373151c13d69f99afbec80f83fb548e4b473eb19ad2ab05497c43927567",
        "audio_sha256": "96118bd3ef8fa4d87215efbdce5578738867aea9ed18e06a1bfd6fd4f367fbe5",
        "size_bytes": 3_619_244,
        "duration_seconds": 75.4,
    },
    "closing_call": {
        "source_text_sha256": "01835614d16f85410731e48e6a4b11b6fb8f2c75a8cdaa68ba34ab849d09134b",
        "audio_sha256": "4738e9a658420b101bb011678826041909fa743f8b580330fbba12a16d05765a",
        "size_bytes": 3_661_244,
        "duration_seconds": 76.275,
    },
}

EXPECTED_ENV = {
    "EARNALISM_APPROVE_CALL_WILD_AM_MICHAEL_LISTENING_QA": "true",
    "EARNALISM_APPROVED_AUDIOBOOK_SLUG": SLUG,
    "EARNALISM_APPROVED_AUDIOBOOK_SCOPE": SCOPE,
    "EARNALISM_ENABLE_OPENAI_LISTENING_QA": "true",
    "EARNALISM_OPENAI_LISTENING_QA_MODEL": "gpt-audio",
    "EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD": "0.05",
    "EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD": "0.20",
    "MAX_TTS_BUDGET_USD": "0.20",
    "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
}

DEFAULT_EVIDENCE = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_targeted_asr_projection_v1.json"
)
DEFAULT_PRIOR_REPAIR = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_asr_repair_v1.json"
)
DEFAULT_OUTPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-call-of-the-wild_kokoro_am_michael_listening_qa_v1.json"
)
DEFAULT_PAID_LOCK = BASE.DEFAULT_PAID_LOCK


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise BASE.GiftKokoroListeningQAError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def load_evidence(path: Path):
    """Return four hash-verified private samples and their no-repeat binding."""

    _require(BASE.sha256_file(path), EXPECTED_EVIDENCE_SHA256, "evidence SHA-256")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    _require(evidence.get("schema"), EXPECTED_SCHEMA, "evidence schema")
    _require(evidence.get("status"), EXPECTED_STATUS, "evidence status")
    _require(
        evidence.get("attempt_fingerprint"),
        EXPECTED_ATTEMPT_FINGERPRINT,
        "attempt fingerprint",
    )
    _require(
        evidence.get("projection_fingerprint"),
        EXPECTED_ASR_CONFIG_FINGERPRINT,
        "projection fingerprint",
    )
    scope = evidence.get("scope") or {}
    _require(scope.get("slug"), SLUG, "scope.slug")
    _require(scope.get("title"), TITLE, "scope.title")
    _require(scope.get("author"), AUTHOR, "scope.author")
    _require(scope.get("full_title_generated"), False, "scope.full_title_generated")
    engine = evidence.get("engine") or {}
    _require(engine.get("model_revision"), EXPECTED_MODEL_REVISION, "model revision")
    _require(engine.get("voice"), "am_michael", "voice")
    _require(engine.get("voice_sha256"), EXPECTED_VOICE_SHA256, "voice SHA-256")

    _require(
        BASE.sha256_file(DEFAULT_PRIOR_REPAIR),
        PRIOR_REPAIR_SHA256,
        "prior repair SHA-256",
    )
    prior = json.loads(DEFAULT_PRIOR_REPAIR.read_text(encoding="utf-8"))
    _require(
        (prior.get("asr_repair") or {}).get("repair_fingerprint"),
        PRIOR_REPAIR_FINGERPRINT,
        "prior repair fingerprint",
    )
    prior_samples = {
        str(item.get("passage_id")): item for item in prior.get("samples", [])
    }
    targeted_samples = {
        str(item.get("passage_id")): item
        for item in evidence.get("targeted_samples", [])
    }
    sample_records = {
        passage_id: (
            prior_samples.get(passage_id, {})
            if passage_id == "spitz_final_conflict"
            else targeted_samples.get(passage_id, {})
        )
        for passage_id in EXPECTED_SAMPLE_BINDINGS
    }
    reports = {
        str(item.get("passage_id")): item
        for item in evidence.get("combined_representative_reports", [])
    }
    _require(set(reports), set(EXPECTED_SAMPLE_BINDINGS), "combined report IDs")

    verified: list[dict[str, Any]] = []
    for passage_id, expected in EXPECTED_SAMPLE_BINDINGS.items():
        sample = sample_records[passage_id]
        report = reports[passage_id]
        for key in ("audio_sha256", "size_bytes", "duration_seconds"):
            _require(sample.get(key), expected[key], f"{passage_id} sample {key}")
        measured_source = sample.get("canonical_source_text_sha256") or sample.get(
            "source_text_sha256"
        )
        _require(
            measured_source,
            expected["source_text_sha256"],
            f"{passage_id} canonical source hash",
        )
        audio = BASE.assert_private_audio(Path(str(sample.get("audio_path") or "")))
        if not audio.is_file():
            raise BASE.GiftKokoroListeningQAError(
                f"private audio is missing: {passage_id}"
            )
        _require(
            BASE.sha256_file(audio),
            expected["audio_sha256"],
            f"{passage_id} measured SHA-256",
        )
        _require(
            audio.stat().st_size,
            expected["size_bytes"],
            f"{passage_id} measured size",
        )
        measured_duration = BASE.ffprobe_duration(audio) or 0.0
        if abs(measured_duration - float(expected["duration_seconds"])) > 0.005:
            raise BASE.GiftKokoroListeningQAError(
                f"{passage_id} measured duration changed: {measured_duration}"
            )
        for key, required in {
            "audio_sha256": expected["audio_sha256"],
            "score": 10.0,
            "coverage": 1.0,
            "precision": 1.0,
            "pass": True,
            "first_words_match": True,
            "last_words_match": True,
            "ordered_content_integrity_pass": True,
            "no_missing_content": True,
            "no_duplicate_content": True,
            "no_reordered_content": True,
            "no_unexpected_content": True,
        }.items():
            _require(report.get(key), required, f"{passage_id} report {key}")
        verified.append(
            {
                "sample_label": passage_id,
                "sample_audio_path": str(audio),
                "sample_audio_hash": expected["audio_sha256"],
                "sample_audio_size_bytes": expected["size_bytes"],
                "sample_audio_duration_seconds": expected["duration_seconds"],
                "source_text_sha256": expected["source_text_sha256"],
                "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
                "asr_config_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
            }
        )

    sample_fingerprint = BASE.canonical_hash(
        {
            "slug": SLUG,
            "scope": SCOPE,
            "evidence_sha256": EXPECTED_EVIDENCE_SHA256,
            "source_sha256": EXPECTED_SOURCE_SHA256,
            "attempt_fingerprint": EXPECTED_ATTEMPT_FINGERPRINT,
            "asr_config_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
            "sample_bindings": EXPECTED_SAMPLE_BINDINGS,
            "judge_model": EXPECTED_ENV["EARNALISM_OPENAI_LISTENING_QA_MODEL"],
            "rubric_version": BASE.LISTENING_QA_RUBRIC_VERSION,
            "hook_version": BASE.LISTENING_QA_HOOK_VERSION,
            "platform_thresholds": BASE.PLATFORM_THRESHOLDS,
            "owner_quality_target": 10.0,
        }
    )
    return evidence, verified, sample_fingerprint


_BASE_EXECUTE = BASE.execute


def execute(*args: Any, **kwargs: Any):
    code, result = _BASE_EXECUTE(*args, **kwargs)
    status = str(result.get("status") or "")
    if status.startswith("PRIVATE_GIFT_"):
        result["status"] = status.replace(
            "PRIVATE_GIFT_", "PRIVATE_CALL_WILD_AM_MICHAEL_", 1
        )
    if "scope" in result:
        result["scope"] = (
            "PRIVATE_CALL_WILD_AM_MICHAEL_REPRESENTATIVE_SCREEN_ONLY_"
            "NOT_RELEASE_EVIDENCE"
        )
    blockers = result.get("release_blockers_preserved")
    if isinstance(blockers, list):
        result["release_blockers_preserved"] = [
            str(item).replace(
                "GIFT_TITLE_SCOPED", "CALL_WILD_TITLE_SCOPED"
            )
            for item in blockers
        ]
    output_path = Path(args[1] if len(args) > 1 else kwargs["output_path"])
    BASE.write_json(output_path, result)
    return code, result


def configure_base() -> None:
    BASE.SLUG = SLUG
    BASE.TITLE = TITLE
    BASE.AUTHOR = AUTHOR
    BASE.LANGUAGE = LANGUAGE
    BASE.SCOPE = SCOPE
    BASE.HOLDER = HOLDER
    BASE.EXPECTED_SAMPLE_COUNT = 4
    BASE.EXPECTED_SCHEMA = EXPECTED_SCHEMA
    BASE.EXPECTED_STATUS = EXPECTED_STATUS
    BASE.EXPECTED_EVIDENCE_SHA256 = EXPECTED_EVIDENCE_SHA256
    BASE.EXPECTED_SOURCE_SHA256 = EXPECTED_SOURCE_SHA256
    BASE.EXPECTED_ATTEMPT_FINGERPRINT = EXPECTED_ATTEMPT_FINGERPRINT
    BASE.EXPECTED_ASR_CONFIG_FINGERPRINT = EXPECTED_ASR_CONFIG_FINGERPRINT
    BASE.EXPECTED_MODEL_REVISION = EXPECTED_MODEL_REVISION
    BASE.EXPECTED_VOICE_SHA256 = EXPECTED_VOICE_SHA256
    BASE.EXPECTED_SAMPLE_BINDINGS = EXPECTED_SAMPLE_BINDINGS
    BASE.EXPECTED_ENV = EXPECTED_ENV
    BASE.DEFAULT_EVIDENCE = DEFAULT_EVIDENCE
    BASE.DEFAULT_OUTPUT = DEFAULT_OUTPUT
    BASE.DEFAULT_PAID_LOCK = DEFAULT_PAID_LOCK
    BASE.load_evidence = load_evidence
    BASE.execute = execute


def expand_defaults(argv: Sequence[str] | None) -> list[str]:
    args = list(argv or [])
    options = {item for item in args if item.startswith("--")}
    for option, value in (
        ("--evidence", DEFAULT_EVIDENCE),
        ("--output", DEFAULT_OUTPUT),
        ("--paid-lock", DEFAULT_PAID_LOCK),
    ):
        if option not in options:
            args.extend((option, str(value)))
    return args


def main(argv: Sequence[str] | None = None) -> int:
    configure_base()
    return int(BASE.main(expand_defaults(argv)))


configure_base()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
