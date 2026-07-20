#!/usr/bin/env python3
"""Judge the exact four-sample Cop ``af_sarah`` private candidate.

The adapter binds immutable private WAVs to exact objective evidence and reuses
the strict schema-3 audio judge, $0.20 budget cap, no-repeat fingerprint, and
byte-for-byte paid-lock restoration. A perfect result authorizes only private
full-title evaluation; this script cannot generate, upload, or publish audio.
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
    "earnalism_strict_cop_af_sarah_listening_qa",
    SCRIPT_DIR / "sprint1_gift_kokoro_private_listening_qa.py",
)
PROFILE = _load(
    "cop_af_sarah_listening_profile",
    SCRIPT_DIR / "sprint1_cop_af_sarah_private_audition.py",
)

SLUG = "the-cop-and-the-anthem"
TITLE = "The Cop and the Anthem"
AUTHOR = "O. Henry"
LANGUAGE = "eng"
SCOPE = "cop_af_sarah_representative_listening_qa_v1"
HOLDER = "sprint1_cop_af_sarah_private_listening_qa"
EXPECTED_SCHEMA = "earnalism.cop_kokoro_af_sarah_representative.v1"
EXPECTED_STATUS = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
EXPECTED_EVIDENCE_SHA256 = (
    "6b8744f0e14c1dedc5500dd4e42697faef0630883ce52483a9e0957dfa10281f"
)
EXPECTED_SOURCE_SHA256 = PROFILE.BASE.EXPECTED_SOURCE_SHA256
EXPECTED_ATTEMPT_FINGERPRINT = PROFILE.EXPECTED_ATTEMPT_FINGERPRINT
EXPECTED_ASR_CONFIG_FINGERPRINT = (
    "5a6efff8ae1067e31d3cfe6ad7338a4b1cb7d42de24252eb0cabb23111d7c6a3"
)
EXPECTED_MODEL_REVISION = PROFILE.BASE.MODEL_REVISION
EXPECTED_VOICE_SHA256 = PROFILE.VOICE_SHA256
EXPECTED_SAMPLE_BINDINGS: dict[str, dict[str, Any]] = {
    "opening_winter": {
        "source_text_sha256": "99ec90941755c7e7b70c98f2a122f1aeefdf7c996bd3e66bade805b8149f4a4c",
        "audio_sha256": "bb297bbd8faf6645a1a7a47600c7f160f7638a3551c2c5c3c10df24d7c17f236",
        "size_bytes": 782_444,
        "duration_seconds": 16.3,
    },
    "waiter_dialogue": {
        "source_text_sha256": "9b7aa5abbd52519cc2fd4c155ceb43711cd287f068792c319b8e1cf4554e50b8",
        "audio_sha256": "93e51660309ee71eb4ed6aa2755e2cdd585da6c06a519355b577de455f8fcd37",
        "size_bytes": 1_262_444,
        "duration_seconds": 26.3,
    },
    "church_reckoning": {
        "source_text_sha256": "8af80b2d0f436da3933b2a50bed8dc98d299367d982d520110c0b07da8b364ae",
        "audio_sha256": "80a05603579ec39aabdf6f42740ba2b818783b75d3a192621b148f3ae5bb3d46",
        "size_bytes": 934_844,
        "duration_seconds": 19.475,
    },
    "ironic_ending": {
        "source_text_sha256": "cb03b2bf6553545bc323f4417dafced01e0042aca8d5f31f32245311357f3c3d",
        "audio_sha256": "b73b0891dcc2d6a5360e0ebb267e4fc345cae1b8e395bb67a694d308c472c825",
        "size_bytes": 2_749_244,
        "duration_seconds": 57.275,
    },
}

EXPECTED_ENV = {
    "EARNALISM_APPROVE_COP_AF_SARAH_LISTENING_QA": "true",
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
    "the-cop-and-the-anthem_kokoro_af_sarah_asr_projection_v1.json"
)
DEFAULT_OUTPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-cop-and-the-anthem_kokoro_af_sarah_listening_qa_v1.json"
)
DEFAULT_PAID_LOCK = BASE.DEFAULT_PAID_LOCK


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise BASE.GiftKokoroListeningQAError(
            f"{label} changed: expected {expected!r}, observed {observed!r}"
        )


def load_evidence(path: Path):
    """Return four immutable, objective-exact private samples."""

    _require(BASE.sha256_file(path), EXPECTED_EVIDENCE_SHA256, "evidence SHA-256")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    _require(evidence.get("schema"), EXPECTED_SCHEMA, "evidence schema")
    _require(evidence.get("status"), EXPECTED_STATUS, "evidence status")
    scope = evidence.get("scope") or {}
    for key, expected in {
        "slug": SLUG,
        "title": TITLE,
        "author": AUTHOR,
        "language": LANGUAGE,
        "passage_count": 4,
        "representative_only": True,
        "full_title_generated": False,
        "public_audio_hidden": True,
    }.items():
        _require(scope.get(key), expected, f"scope.{key}")
    _require((evidence.get("source") or {}).get("source_sha256"), EXPECTED_SOURCE_SHA256, "source SHA-256")
    engine = evidence.get("engine") or {}
    _require(engine.get("package"), "kokoro", "engine package")
    _require(engine.get("model_revision"), EXPECTED_MODEL_REVISION, "model revision")
    _require(engine.get("voice"), "af_sarah", "voice")
    _require(engine.get("voice_sha256"), EXPECTED_VOICE_SHA256, "voice SHA-256")
    _require(engine.get("attempt_fingerprint"), EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")

    asr = evidence.get("asr") or {}
    _require(asr.get("status"), "PASS", "ASR status")
    _require(asr.get("mode"), "OFFLINE_BOUND_TRANSCRIPT_PROJECTION_NO_NEW_DECODER", "ASR mode")
    _require(asr.get("projection_fingerprint"), EXPECTED_ASR_CONFIG_FINGERPRINT, "projection fingerprint")
    _require(asr.get("audio_derived_raw_transcripts"), True, "audio-derived transcript flag")
    _require(asr.get("new_asr_decoder_calls"), 0, "new ASR decoder calls")
    _require(asr.get("resynthesis_performed"), False, "resynthesis flag")
    _require(asr.get("unexpected_speech_may_be_deleted"), False, "unexpected-speech deletion policy")
    reports = {str(item.get("passage_id")): item for item in asr.get("reports", [])}
    _require(set(reports), set(EXPECTED_SAMPLE_BINDINGS), "ASR passage IDs")
    samples = {str(item.get("passage_id")): item for item in evidence.get("samples", [])}
    _require(set(samples), set(EXPECTED_SAMPLE_BINDINGS), "sample passage IDs")

    verified: list[dict[str, Any]] = []
    for passage_id, expected in EXPECTED_SAMPLE_BINDINGS.items():
        sample = samples[passage_id]
        report = reports[passage_id]
        for key in ("source_text_sha256", "audio_sha256", "size_bytes", "duration_seconds"):
            _require(sample.get(key), expected[key], f"{passage_id} sample {key}")
        audio = BASE.assert_private_audio(Path(str(sample.get("audio_path") or "")))
        if not audio.is_file():
            raise BASE.GiftKokoroListeningQAError(f"private audio is missing: {passage_id}")
        _require(BASE.sha256_file(audio), expected["audio_sha256"], f"{passage_id} measured SHA-256")
        _require(audio.stat().st_size, expected["size_bytes"], f"{passage_id} measured size")
        measured_duration = BASE.ffprobe_duration(audio) or 0.0
        if abs(measured_duration - float(expected["duration_seconds"])) > 0.005:
            raise BASE.GiftKokoroListeningQAError(
                f"{passage_id} measured duration changed: {measured_duration}"
            )
        for key, required in {
            "audio_sha256": expected["audio_sha256"],
            "source_text_sha256": expected["source_text_sha256"],
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
            "unexpected_speech_deleted": False,
            "pass": True,
        }.items():
            _require(report.get(key), required, f"{passage_id} objective {key}")
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
            "asr_projection_fingerprint": EXPECTED_ASR_CONFIG_FINGERPRINT,
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
        result["status"] = status.replace("PRIVATE_GIFT_", "PRIVATE_COP_AF_SARAH_", 1)
    if "scope" in result:
        result["scope"] = "PRIVATE_COP_AF_SARAH_REPRESENTATIVE_SCREEN_ONLY_NOT_RELEASE_EVIDENCE"
    blockers = result.get("release_blockers_preserved")
    if isinstance(blockers, list):
        result["release_blockers_preserved"] = [
            str(item).replace("GIFT_TITLE_SCOPED", "COP_TITLE_SCOPED")
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
