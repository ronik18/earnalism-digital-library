#!/usr/bin/env python3
"""Judge the exact four-sample Monkey's Paw ``bf_emma`` candidate.

This wrapper binds three immutable WAVs from the British representative run
plus the one exact targeted replacement.  It reuses the strict schema-3 Gift
listening judge, exact-10 owner gate, budget guard, no-repeat fingerprint, and
byte-for-byte paid-lock restoration.  A pass authorizes only a private
full-title decision; it is not release evidence and cannot upload or publish.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise RuntimeError(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load(
    "earnalism_strict_private_listening_qa",
    SCRIPT_DIR / "sprint1_gift_kokoro_private_listening_qa.py",
)
PROFILE = _load(
    "monkeys_paw_bf_listening_profile",
    SCRIPT_DIR / "sprint1_monkeys_paw_bf_emma_private_audition.py",
)

SLUG = "the-monkeys-paw"
TITLE = "The Monkey's Paw"
AUTHOR = "W. W. Jacobs"
LANGUAGE = "eng"
SCOPE = "monkeys_paw_bf_emma_representative_listening_qa_v1"
HOLDER = "sprint1_monkeys_paw_bf_emma_private_listening_qa"
EXPECTED_SCHEMA = (
    "earnalism.kokoro.monkeys_paw_bf_emma_targeted_resynthesis.v1"
)
EXPECTED_STATUS = "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA"
EXPECTED_EVIDENCE_SHA256 = (
    "4876c21d3e2c2edf6271e9d2feff647de5acb1e421b127257f97c62d4c8b8333"
)
EXPECTED_SOURCE_SHA256 = PROFILE.PROFILE_BASE.NORMALIZED_SOURCE_SHA256
EXPECTED_ATTEMPT_FINGERPRINT = (
    "29da95f0687756670f1a3c21bee7e17e2fe4fdf2cbfeed8d06a32ce558306b81"
)
EXPECTED_ASR_CONFIG_FINGERPRINT = (
    "e2591f24954380337aa47cf5971c839df4aa59b43d81e8d538697f54959167e9"
)
EXPECTED_MODEL_REVISION = PROFILE.PROFILE_BASE.MODEL_REVISION
EXPECTED_VOICE_SHA256 = PROFILE.VOICE_SHA256
PRIOR_REPAIR_SHA256 = (
    "8dd1a4c381522e34daee914d1b2971e94b173311f2b1089dc251dc8cf66efcba"
)
PRIOR_REPAIR_FINGERPRINT = (
    "12a5b40c13022312a66b96adbc6e7fb6743da1efad9c20b6c5bed2f03935986e"
)

EXPECTED_SAMPLE_BINDINGS: dict[str, dict[str, Any]] = {
    "opening_domestic_tension": {
        "source_text_sha256": "1505ffdc29416106677ad7c3ef7ea0a3db602c1069e1d72b81327721c1fe5765",
        "audio_sha256": "2e55b15d360985800588be280ebcc2194a366f93e3b745cd96c787a0259f9559",
        "size_bytes": 990_044,
        "duration_seconds": 20.625,
    },
    "paw_warning_and_fate": {
        "source_text_sha256": "a3ec2e40908f432cca118c418e743329bccc9f411908bc16da2f725e8e43007d",
        "audio_sha256": "b2b02e381e4e4d095bad79a9e6ecfb9b41718fead258b88b09a7212c5de2db94",
        "size_bytes": 2_661_644,
        "duration_seconds": 55.45,
    },
    "factory_news_and_grief": {
        "source_text_sha256": "6877bbcbea4fdfd7729b41ff27dc422b18dd6d44b7b0e4893555ba5e109cf0aa",
        "audio_sha256": "1e63bf51b01bb6a1606d80563ca0d447ef7f5e98a317304b61be84fdcf3c3cae",
        "size_bytes": 2_568_044,
        "duration_seconds": 53.5,
    },
    "final_knocking_and_third_wish": {
        "source_text_sha256": "9198f815c21620148cfab038af5bdaadedd7397567c9a9010c1d1bc340148fb4",
        "audio_sha256": "38d725efe65b6654bff62cee8ac79c8c40d5ed5c3e87012ab6fb1ac84d0e1921",
        "size_bytes": 3_223_244,
        "duration_seconds": 67.15,
    },
}

EXPECTED_ENV = {
    "EARNALISM_APPROVE_MONKEYS_PAW_BF_EMMA_LISTENING_QA": "true",
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
    "the-monkeys-paw_kokoro_bf_emma_targeted_resynthesis_v2.json"
)
DEFAULT_PRIOR_REPAIR = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_bf_emma_asr_repair_v1.json"
)
DEFAULT_OUTPUT = BASE.ROOT / (
    "internal/audiobook_lab/sprint1_publication/title_runs/"
    "the-monkeys-paw_kokoro_bf_emma_listening_qa_v1.json"
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
    _require(evidence.get("attempt_fingerprint"), EXPECTED_ATTEMPT_FINGERPRINT, "attempt fingerprint")
    scope = evidence.get("scope") or {}
    _require(scope.get("slug"), SLUG, "scope.slug")
    _require(scope.get("title"), TITLE, "scope.title")
    _require(scope.get("full_title_generated"), False, "scope.full_title_generated")
    engine = evidence.get("engine") or {}
    _require(engine.get("model_revision"), EXPECTED_MODEL_REVISION, "model revision")
    _require(engine.get("voice"), "bf_emma", "voice")
    _require(engine.get("voice_sha256"), EXPECTED_VOICE_SHA256, "voice SHA-256")

    _require(BASE.sha256_file(DEFAULT_PRIOR_REPAIR), PRIOR_REPAIR_SHA256, "prior repair SHA-256")
    prior = json.loads(DEFAULT_PRIOR_REPAIR.read_text(encoding="utf-8"))
    _require(
        (prior.get("asr_repair") or {}).get("repair_fingerprint"),
        PRIOR_REPAIR_FINGERPRINT,
        "prior repair fingerprint",
    )
    prior_samples = {
        str(item.get("passage_id")): item for item in prior.get("samples", [])
    }
    targeted = evidence.get("targeted_sample") or {}
    sample_records = {
        passage_id: (
            targeted if passage_id == "factory_news_and_grief" else prior_samples.get(passage_id, {})
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
        _require(BASE.sha256_file(audio), expected["audio_sha256"], f"{passage_id} measured SHA-256")
        _require(audio.stat().st_size, expected["size_bytes"], f"{passage_id} measured size")
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
        }
    )
    return evidence, verified, sample_fingerprint


_BASE_EXECUTE = BASE.execute


def execute(*args: Any, **kwargs: Any):
    code, result = _BASE_EXECUTE(*args, **kwargs)
    status = str(result.get("status") or "")
    if status.startswith("PRIVATE_GIFT_"):
        result["status"] = status.replace(
            "PRIVATE_GIFT_", "PRIVATE_MONKEYS_PAW_BF_EMMA_", 1
        )
    if "scope" in result:
        result["scope"] = "PRIVATE_MONKEYS_PAW_BF_EMMA_REPRESENTATIVE_SCREEN_ONLY_NOT_RELEASE_EVIDENCE"
    blockers = result.get("release_blockers_preserved")
    if isinstance(blockers, list):
        result["release_blockers_preserved"] = [
            str(item).replace("GIFT_TITLE_SCOPED", "MONKEYS_PAW_TITLE_SCOPED")
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
