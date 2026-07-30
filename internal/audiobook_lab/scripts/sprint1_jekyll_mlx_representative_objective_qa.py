#!/usr/bin/env python3
"""Run a bounded MLX Whisper diagnostic on the exact Jekyll candidate.

This adapter is deliberately narrower than full-title objective QA.  It
compares two known medium.en failure chunks with three exact-pass controls
using a materially different cached model.  It never synthesizes audio,
contacts a provider, reads the paid-provider lock, uploads media, or changes
release state.  A full 92-unit MLX run is only recommended when every bound
diagnostic unit passes the existing strict objective policy.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import sprint1_google_english_full_audio_derived_qa as full_qa  # noqa: E402
import sprint1_google_english_full_candidate_qa as candidate_qa  # noqa: E402
import sprint1_google_english_private_pipeline as google_pipeline  # noqa: E402
import sprint1_gift_kokoro_full_title_private_qa as asr_common  # noqa: E402


SCHEMA = "earnalism.jekyll_mlx_representative_objective_qa.v1"
EXPECTED_SLUG = "jekyll-and-hyde"
EXPECTED_PRIOR_SCHEMA = "earnalism.google_english_full_audio_derived_qa.v1"
EXPECTED_PRIOR_MODEL = "medium.en"
EXPECTED_TARGET_UNIT_IDS = ("chunk_0009", "chunk_0045")
EXPECTED_CONTROL_UNIT_IDS = ("chunk_0008", "chunk_0064", "chunk_0071")
EXPECTED_UNIT_IDS = EXPECTED_TARGET_UNIT_IDS + EXPECTED_CONTROL_UNIT_IDS
DEFAULT_MODEL_PROFILE = "large-v3-turbo"
MODEL_PROFILES = {
    "large-v3-turbo": {
        "repository": "mlx-community/whisper-large-v3-turbo",
        "revision": "a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb",
        "license": "UPSTREAM_OPENAI_WHISPER_MIT",
        "weights_filename": "weights.safetensors",
        "weights_sha256": (
            "951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6"
        ),
        "config_sha256": (
            "b34fc29e4e11e0a25e812775dd67f4dd16fc2c8eb43d28ae25ff7d660ecb6379"
        ),
        "diagnostic_directory": "mlx_large_v3_turbo_diagnostic",
    },
    "large-v3": {
        "repository": "mlx-community/whisper-large-v3-mlx",
        "revision": "49e6aa286ad60c14352c404340ded53710378a11",
        "license": "MIT",
        "weights_filename": "weights.npz",
        "weights_sha256": (
            "05ff791ce3630fae47e7c51004e9666204d786246ec07cac6110af768099b40d"
        ),
        "config_sha256": (
            "34982ce6ae286095000f82ae9583b3431639e8b092bf60c961f203745e6500e3"
        ),
        "diagnostic_directory": "mlx_large_v3_diagnostic",
    },
}
ASR_SETTINGS = {
    "language": "en",
    "task": "transcribe",
    "temperature": 0.0,
    "condition_on_previous_text": False,
    "initial_prompt": None,
    "word_timestamps": True,
    "compression_ratio_threshold": 2.4,
    "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6,
}


class JekyllMLXDiagnosticError(RuntimeError):
    """Raised when bounded diagnostic evidence is not exact."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise JekyllMLXDiagnosticError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JekyllMLXDiagnosticError(f"cannot read {label}: {path}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def validate_output_path(
    output: Path,
    run_dir: Path,
    diagnostic_directory: str = "mlx_large_v3_turbo_diagnostic",
) -> Path:
    resolved = output.expanduser().resolve()
    diagnostic_root = (
        run_dir / diagnostic_directory
    ).expanduser().resolve()
    require(
        candidate_qa.is_within(resolved, diagnostic_root),
        "output must remain under the candidate's private MLX diagnostic directory",
    )
    require(resolved.suffix == ".json", "diagnostic output must be JSON")
    require(not resolved.exists(), "diagnostic output already exists")
    return resolved


def validate_model(model_path: Path, profile_name: str) -> dict[str, Any]:
    require(profile_name in MODEL_PROFILES, "unsupported MLX model profile")
    profile = MODEL_PROFILES[profile_name]
    resolved = model_path.expanduser().resolve()
    weights = resolved / str(profile["weights_filename"])
    config = resolved / "config.json"
    require(weights.is_file(), "cached MLX Whisper weights are missing")
    require(config.is_file(), "cached MLX Whisper config is missing")
    require(
        sha256_file(weights) == profile["weights_sha256"],
        "cached MLX Whisper weights hash changed",
    )
    require(
        sha256_file(config) == profile["config_sha256"],
        "cached MLX Whisper config hash changed",
    )
    return {
        "profile": profile_name,
        "repository": profile["repository"],
        "revision": profile["revision"],
        "license": profile["license"],
        "path": str(resolved),
        "weights_filename": profile["weights_filename"],
        "weights_sha256": profile["weights_sha256"],
        "config_sha256": profile["config_sha256"],
        "diagnostic_directory": profile["diagnostic_directory"],
    }


def validate_prior_report(
    path: Path,
    expected_sha256: str,
    evidence: candidate_qa.CandidateEvidence,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    resolved = path.expanduser().resolve()
    require(resolved.is_file(), "prior medium.en report is missing")
    require(
        len(expected_sha256) == 64
        and all(character in "0123456789abcdef" for character in expected_sha256),
        "prior report SHA-256 must be explicit",
    )
    require(
        sha256_file(resolved) == expected_sha256,
        "prior medium.en report hash changed",
    )
    report = read_json_object(resolved, "prior medium.en report")
    require(
        report.get("schema_version") == EXPECTED_PRIOR_SCHEMA,
        "prior report schema changed",
    )
    require(report.get("slug") == EXPECTED_SLUG, "prior report title changed")
    require(
        report.get("source_sha256") == evidence.source_sha256
        and report.get("input_manifest_sha256")
        == evidence.input_manifest_sha256
        and report.get("full_manifest_sha256")
        == evidence.manifest_sha256,
        "prior report candidate binding changed",
    )
    asr = report.get("audio_derived_asr")
    require(isinstance(asr, dict), "prior report lacks audio-derived ASR")
    require(asr.get("model") == EXPECTED_PRIOR_MODEL, "prior ASR model changed")
    require(
        asr.get("chunk_count") == len(evidence.records)
        and asr.get("local_asr_run_count") == len(evidence.records),
        "prior medium.en report is not a complete title run",
    )
    reports = asr.get("reports")
    require(
        isinstance(reports, list) and len(reports) == len(evidence.records),
        "prior report unit count changed",
    )
    by_id = {
        str(item.get("unit_id")): item
        for item in reports
        if isinstance(item, dict)
    }
    require(len(by_id) == len(evidence.records), "prior report has duplicate units")
    for record in evidence.records:
        prior = by_id.get(str(record["unit_id"]))
        require(prior is not None, f"prior report lacks {record['unit_id']}")
        require(
            prior.get("audio_sha256") == record["audio_sha256"]
            and prior.get("source_text_sha256") == record["text_sha256"],
            f"prior report binding changed for {record['unit_id']}",
        )
    for field in (
        "upload_performed",
        "publication_performed",
        "release_mutation_performed",
        "paid_lock_read_or_written",
    ):
        require(report.get(field) is False, f"prior report {field} must be false")
    return report, by_id


def selected_records(
    evidence: candidate_qa.CandidateEvidence,
) -> list[dict[str, Any]]:
    by_id = {
        str(record["unit_id"]): record
        for record in evidence.records
    }
    require(
        set(EXPECTED_UNIT_IDS).issubset(by_id),
        "candidate lacks one or more bound diagnostic units",
    )
    return [by_id[unit_id] for unit_id in EXPECTED_UNIT_IDS]


def compact_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: metrics.get(key)
        for key in (
            "score",
            "coverage",
            "precision",
            "source_token_count",
            "transcript_token_count",
            "equal_token_count",
            "first_words_match",
            "last_words_match",
            "ordered_content_integrity_pass",
            "no_missing_content",
            "no_duplicate_content",
            "no_reordered_content",
            "no_unexpected_content",
            "pass",
        )
    }


def classify(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {str(item["unit_id"]): item for item in reports}
    controls_pass = all(
        by_id[unit_id].get("strict_objective_pass") is True
        for unit_id in EXPECTED_CONTROL_UNIT_IDS
    )
    targets_pass = all(
        by_id[unit_id].get("strict_objective_pass") is True
        for unit_id in EXPECTED_TARGET_UNIT_IDS
    )
    timestamps_pass = all(
        item.get("word_timestamp_evidence_valid") is True
        for item in reports
    )
    if controls_pass and targets_pass and timestamps_pass:
        status = "MEDIUM_EN_LIMITATION_CONFIRMED_MLX_FULL_DIAGNOSTIC_ELIGIBLE"
        reason = (
            "The materially different MLX model strictly passes both prior "
            "failure chunks and all exact-pass controls with measured word "
            "timestamps. The evidence supports a separate full MLX QA run; it "
            "does not itself authorize release."
        )
        full_run_eligible = True
    elif not controls_pass:
        status = "MLX_MODEL_NOT_VALIDATED_ON_STRONG_CONTROLS"
        reason = (
            "One or more exact-pass controls regressed, so this model/settings "
            "fingerprint cannot distinguish recognition limits from narration."
        )
        full_run_eligible = False
    else:
        boundary_failures = [
            unit_id
            for unit_id in EXPECTED_TARGET_UNIT_IDS
            if by_id[unit_id]["metrics"].get("last_words_match") is not True
        ]
        if boundary_failures:
            status = "NARRATION_OR_BOUNDARY_MISMATCH_REMAINS_POSSIBLE"
            reason = (
                "Strong controls pass, but a materially different recognizer "
                "still misses one or more target endings. Inspect the bound "
                "audio before any broader inference."
            )
        else:
            status = "MLX_RECOGNITION_IMPROVED_BUT_OBJECTIVE_GATE_STILL_FAILS"
            reason = (
                "The alternate recognizer improves evidence but one or more "
                "strict content gates still fail."
            )
        full_run_eligible = False
    return {
        "status": status,
        "reason": reason,
        "controls_pass": controls_pass,
        "targets_pass": targets_pass,
        "timestamps_pass": timestamps_pass,
        "full_92_unit_mlx_run_eligible": full_run_eligible,
        "release_authorized": False,
    }


def run_diagnostic(
    *,
    full_manifest: Path,
    prior_report: Path,
    prior_report_sha256: str,
    model_path: Path,
    model_profile: str = DEFAULT_MODEL_PROFILE,
    output: Path,
    transcriber: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    manifest = full_manifest.expanduser().resolve()
    try:
        evidence = full_qa.validate_contract(manifest)
    except (
        candidate_qa.CandidateQAError,
        full_qa.FullAudioDerivedQAError,
    ) as exc:
        raise JekyllMLXDiagnosticError(str(exc)) from exc
    require(evidence.manifest.get("slug") == EXPECTED_SLUG, "wrong title")
    require(model_profile in MODEL_PROFILES, "unsupported MLX model profile")
    destination = validate_output_path(
        output,
        evidence.manifest_path.parent,
        str(MODEL_PROFILES[model_profile]["diagnostic_directory"]),
    )
    model = validate_model(model_path, model_profile)
    prior, prior_by_id = validate_prior_report(
        prior_report,
        prior_report_sha256,
        evidence,
    )
    records = selected_records(evidence)
    fingerprint = canonical_sha256(
        {
            "schema_version": SCHEMA,
            "source_sha256": evidence.source_sha256,
            "input_manifest_sha256": evidence.input_manifest_sha256,
            "full_manifest_sha256": evidence.manifest_sha256,
            "prior_report_sha256": prior_report_sha256,
            "model": model,
            "settings": ASR_SETTINGS,
            "units": [
                {
                    "unit_id": record["unit_id"],
                    "source_text_sha256": record["text_sha256"],
                    "audio_sha256": record["audio_sha256"],
                }
                for record in records
            ],
        }
    )

    if transcriber is None:
        try:
            import mlx_whisper  # noqa: PLC0415
        except ImportError as exc:
            raise JekyllMLXDiagnosticError(
                "mlx-whisper is required in the selected interpreter"
            ) from exc
        transcriber = mlx_whisper.transcribe

    raw_root = destination.parent / "raw_results"
    reports: list[dict[str, Any]] = []
    started = time.monotonic()
    for record in records:
        audio_path = Path(str(record["audio_path"])).resolve()
        require(
            sha256_file(audio_path) == record["audio_sha256"],
            f"audio hash changed for {record['unit_id']}",
        )
        result = transcriber(
            str(audio_path),
            path_or_hf_repo=model["path"],
            verbose=False,
            **ASR_SETTINGS,
        )
        require(
            isinstance(result, Mapping),
            f"MLX returned a non-object for {record['unit_id']}",
        )
        raw_path = raw_root / f"{record['unit_id']}.json"
        atomic_write_json(raw_path, result)
        transcript = str(result.get("text") or "").strip()
        metrics = full_qa._evaluated_metrics(
            str(record["source_text"]),
            transcript,
            slug=EXPECTED_SLUG,
        )
        words, anomalies = asr_common.verified_words(
            result,
            float(record["measured_duration_seconds"]),
        )
        strict_pass = bool(metrics["pass"] and words and not anomalies)
        prior_unit = prior_by_id[str(record["unit_id"])]
        reports.append(
            {
                "unit_id": record["unit_id"],
                "role": (
                    "prior_medium_en_failure"
                    if record["unit_id"] in EXPECTED_TARGET_UNIT_IDS
                    else "exact_pass_control"
                ),
                "source_text_sha256": record["text_sha256"],
                "audio_sha256": record["audio_sha256"],
                "duration_seconds": record["measured_duration_seconds"],
                "transcript": transcript,
                "transcript_sha256": google_pipeline.sha256_text(transcript),
                "raw_result_path": str(raw_path),
                "raw_result_sha256": sha256_file(raw_path),
                "audio_derived_word_timestamp_count": len(words),
                "audio_derived_word_timestamps_sha256": canonical_sha256(words),
                "word_timestamp_anomalies": anomalies,
                "word_timestamp_evidence_valid": bool(words) and not anomalies,
                "metrics": compact_metrics(metrics),
                "strict_objective_pass": strict_pass,
                "prior_medium_en": {
                    "transcript_sha256": prior_unit.get("transcript_sha256"),
                    "score": prior_unit.get("score"),
                    "coverage": prior_unit.get("coverage"),
                    "first_words_match": prior_unit.get("first_words_match"),
                    "last_words_match": prior_unit.get("last_words_match"),
                    "pass": prior_unit.get("pass"),
                },
                "score_delta_vs_medium_en": round(
                    float(metrics.get("score") or 0.0)
                    - float(prior_unit.get("score") or 0.0),
                    4,
                ),
                "coverage_delta_vs_medium_en": round(
                    float(metrics.get("coverage") or 0.0)
                    - float(prior_unit.get("coverage") or 0.0),
                    4,
                ),
            }
        )

    decision = classify(reports)
    result = {
        "schema_version": SCHEMA,
        "slug": EXPECTED_SLUG,
        "status": decision["status"],
        "diagnostic_fingerprint": fingerprint,
        "source_sha256": evidence.source_sha256,
        "input_manifest_sha256": evidence.input_manifest_sha256,
        "full_manifest_sha256": evidence.manifest_sha256,
        "prior_medium_en_report_path": str(prior_report.expanduser().resolve()),
        "prior_medium_en_report_sha256": prior_report_sha256,
        "prior_medium_en_status": prior.get("status"),
        "model": model,
        "runtime": {
            "name": "mlx-whisper",
            "version": importlib.metadata.version("mlx-whisper"),
            "settings": ASR_SETTINGS,
            "offline_environment": {
                "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
                "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE"),
            },
            "wall_seconds": round(time.monotonic() - started, 3),
        },
        "target_unit_ids": list(EXPECTED_TARGET_UNIT_IDS),
        "control_unit_ids": list(EXPECTED_CONTROL_UNIT_IDS),
        "reports": reports,
        "decision": decision,
        "network_or_provider_calls_made": False,
        "audio_generated": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_mutation_performed": False,
        "paid_lock_read_or_written": False,
        "next_exact_command": (
            "Do not run full MLX QA unless decision.full_92_unit_mlx_run_eligible "
            "is true and a separate exact-provenance full-run adapter is reviewed."
        ),
    }
    atomic_write_json(destination, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bounded Jekyll MLX Whisper objective diagnostic"
    )
    parser.add_argument("--full-manifest", type=Path, required=True)
    parser.add_argument("--prior-report", type=Path, required=True)
    parser.add_argument("--prior-report-sha256", required=True)
    parser.add_argument(
        "--model-profile",
        choices=sorted(MODEL_PROFILES),
        default=DEFAULT_MODEL_PROFILE,
    )
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        result = run_diagnostic(
            full_manifest=args.full_manifest,
            prior_report=args.prior_report,
            prior_report_sha256=args.prior_report_sha256,
            model_profile=args.model_profile,
            model_path=args.model_path,
            output=args.output,
        )
    except JekyllMLXDiagnosticError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return (
        0
        if result["decision"]["full_92_unit_mlx_run_eligible"] is True
        else 3
    )


if __name__ == "__main__":
    raise SystemExit(main())
