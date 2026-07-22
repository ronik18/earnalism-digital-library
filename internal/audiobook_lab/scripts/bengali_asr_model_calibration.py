#!/usr/bin/env python3
"""Bounded, hash-bound Bengali ASR model/language calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = ROOT / "internal/audiobook_lab/scripts"
HOOK_DIR = SCRIPTS_DIR / "factory_hooks"
import sys

sys.path[:0] = [str(SCRIPTS_DIR), str(HOOK_DIR)]
from asr_sync_hook import transcript_similarity  # noqa: E402
from bengali_asr_normalization import analyze_bengali_asr, detect_script_mix, script_counts  # noqa: E402
from providers.sarvam_stt_adapter import (  # noqa: E402
    require_paid_campaign_approval,
    transcribe_rest as transcribe_sarvam_rest,
    validate_campaign_budget,
)


HOLDER = "sprint1_bengali_asr_model_calibration"
SARVAM_STT_ENDPOINT = os.environ.get("SARVAM_STT_ENDPOINT", "https://api.sarvam.ai/speech-to-text")
SARVAM_REST_CLIP_SECONDS = 29.0


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, payload: dict | bytes) -> None:
    data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False, indent=2).encode() + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def validate_internal_path(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve()
    internal_root = (ROOT / "internal").resolve()
    if resolved != internal_root and internal_root not in resolved.parents:
        raise RuntimeError(f"{label} must remain under the repository internal directory")
    return resolved


def load_lock(raw: bytes, *, slug: str | None = None) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock is not available")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    allowed_slugs = payload.get("allowed_slugs")
    if slug and (not isinstance(allowed_slugs, list) or slug not in allowed_slugs):
        raise RuntimeError(f"paid_tts.lock does not authorize slug: {slug}")
    return payload


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def selected_chunks(manifest: dict, chunk_ids: list[str], run_dir: Path) -> list[dict]:
    chunks = manifest.get("chunks") if isinstance(manifest.get("chunks"), list) else []
    by_id = {f"group_{int(item.get('index', -1)):04d}": item for item in chunks}
    selected = []
    for chunk_id in chunk_ids:
        if chunk_id not in by_id:
            raise RuntimeError(f"Unknown chunk id: {chunk_id}")
        item = dict(by_id[chunk_id])
        path = Path(str(item.get("path") or ""))
        if not path.is_absolute():
            root_path = ROOT / path
            path = root_path if root_path.exists() else run_dir / path
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"Chunk audio is missing: {chunk_id}")
        item.update({"chunk_id": chunk_id, "audio_path": str(path), "audio_hash": sha256_file(path)})
        selected.append(item)
    return selected


def estimated_cost(chunks: list[dict], arm_count: int, rate_per_minute: float) -> float:
    duration = sum(float(item.get("duration_seconds") or 0) for item in chunks)
    return round(duration / 60.0 * rate_per_minute * arm_count, 4)


def script_ratio(profile: dict) -> float:
    counts = profile.get("counts") or profile
    bengali = int(counts.get("bengali") or 0)
    devanagari = int(counts.get("devanagari") or 0)
    latin = int(counts.get("latin") or 0)
    denominator = bengali + devanagari + latin
    return round(bengali / denominator, 4) if denominator else 0.0


def best_arm(results: list[dict]) -> dict | None:
    passed = [item for item in results if item.get("status") == "PASS"]
    candidates = passed or [item for item in results if item.get("status") != "ERROR"]
    return max(candidates, key=lambda item: (float(item.get("source_score") or 0), float(item.get("bengali_script_ratio") or 0)), default=None)


def summarize_arms(results: list[dict], expected_chunk_ids: list[str]) -> list[dict]:
    grouped: dict[tuple[str, str, str, str], list[dict]] = {}
    for item in results:
        key = (
            str(item.get("provider") or ""),
            str(item.get("model") or ""),
            str(item.get("language") or ""),
            str(item.get("mode") or "default"),
        )
        grouped.setdefault(key, []).append(item)
    summaries: list[dict] = []
    expected = set(expected_chunk_ids)
    for (provider, model, language, mode), items in grouped.items():
        observed = {str(item.get("chunk_id") or "") for item in items}
        complete = observed == expected and len(items) == len(expected_chunk_ids)
        passing = complete and all(item.get("status") == "PASS" for item in items)
        numeric = lambda field: [float(item.get(field) or 0) for item in items]
        summaries.append(
            {
                "provider": provider,
                "model": model,
                "language": language,
                "mode": mode,
                "status": "PASS" if passing else "BELOW_THRESHOLD",
                "chunk_ids": sorted(observed),
                "expected_chunk_ids": list(expected_chunk_ids),
                "all_chunks_present": complete,
                "source_score": min(numeric("source_score"), default=0.0),
                "source_score_min": min(numeric("source_score"), default=0.0),
                "coverage_min": min(numeric("coverage"), default=0.0),
                "token_order_similarity_min": min(numeric("token_order_similarity"), default=0.0),
                "bengali_script_ratio": min(numeric("bengali_script_ratio"), default=0.0),
                "all_boundaries_match": complete
                and all(item.get("first_words_match") and item.get("last_words_match") for item in items),
            }
        )
    return summaries


def same_attempt(prior: dict, current: dict) -> bool:
    """Recognize an exhausted provider attempt across evidence-schema upgrades."""
    keys = ("slug", "provider", "chunks", "models", "languages")
    if not all(prior.get(key) == current.get(key) for key in keys):
        return False
    prior_modes = prior.get("modes") or (["transcribe"] if prior.get("provider") == "sarvam" else ["default"])
    current_modes = current.get("modes") or (["transcribe"] if current.get("provider") == "sarvam" else ["default"])
    prior_timestamps = bool(prior.get("require_timestamps", False))
    current_timestamps = bool(current.get("require_timestamps", False))
    return prior_modes == current_modes and prior_timestamps == current_timestamps


def acquired_lock(lock: dict, *, slug: str, estimate: float) -> dict:
    payload = dict(lock)
    payload.update(
        {
            "current_holder": HOLDER,
            "allowed_next_holders": [],
            "holder_started_at": iso_now(),
            "budget_cap_usd": estimate,
            "approved_scope": f"{slug} bounded Bengali ASR model/language calibration only; no TTS, upload, or publication",
            "allowed_slugs": [slug],
            "updated_at": iso_now(),
        }
    )
    return payload


def transcribe_openai(path: Path, *, model: str, language: str, timeout: float) -> str:
    from openai import OpenAI

    client = OpenAI(timeout=timeout)
    params = {"model": model, "response_format": "json"}
    if language != "auto":
        params["language"] = language
    with path.open("rb") as handle:
        response = client.audio.transcriptions.create(file=handle, **params)
    if hasattr(response, "model_dump"):
        payload = response.model_dump()
    elif isinstance(response, dict):
        payload = response
    else:
        payload = json.loads(response.json())
    return str(payload.get("text") or "").strip()


def transcribe_google(path: Path, *, model: str, language: str, timeout: float) -> str:
    if language == "auto":
        raise RuntimeError("Google Speech calibration requires an explicit BCP-47 language")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required")
    duration_result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        capture_output=True,
        check=True,
    )
    duration = float(duration_result.stdout.strip())
    transcripts: list[str] = []
    with tempfile.TemporaryDirectory(prefix="earnalism-google-asr-") as tmp:
        token_result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if token_result.returncode != 0 or not token_result.stdout.strip():
            raise RuntimeError(token_result.stderr.strip() or "Google ADC access token is unavailable")
        token_path = Path(tmp) / "adc_access_token.txt"
        token_path.write_text(token_result.stdout.strip() + "\n", encoding="utf-8")
        offset = 0.0
        index = 0
        while offset < duration - 0.05:
            clip = Path(tmp) / f"clip_{index:03d}.flac"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{offset:.3f}",
                    "-t",
                    "55",
                    "-i",
                    str(path),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(clip),
                ],
                check=True,
            )
            command = [
                "gcloud",
                "ml",
                "speech",
                "recognize",
                str(clip),
                f"--language-code={language}",
                f"--model={model}",
                "--encoding=flac",
                "--enable-automatic-punctuation",
                "--include-word-time-offsets",
                f"--project={project}",
                f"--billing-project={project}",
                f"--access-token-file={token_path}",
                "--format=json",
                "--quiet",
            ]
            result = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Google Speech command failed")
            payload = json.loads(result.stdout or "{}")
            for recognition in payload.get("results") or []:
                alternatives = recognition.get("alternatives") or []
                if alternatives and str(alternatives[0].get("transcript") or "").strip():
                    transcripts.append(str(alternatives[0]["transcript"]).strip())
            offset += 55.0
            index += 1
    return " ".join(transcripts).strip()


def transcribe_sarvam(path: Path, *, model: str, language: str, timeout: float) -> str:
    """Transcribe a calibration group through Saaras without retaining provider audio."""
    payload = transcribe_sarvam_rest(
        path,
        model=model,
        language="unknown" if language == "auto" else language,
        mode="transcribe",
        with_timestamps=False,
        timeout=timeout,
        request_gap_seconds=float(os.environ.get("EARNALISM_SARVAM_ASR_REQUEST_GAP_SECONDS", "0.25")),
    )
    return str(payload.get("text") or "").strip()


def transcribe_sarvam_payload(
    path: Path, *, model: str, language: str, mode: str, require_timestamps: bool, timeout: float
) -> dict:
    return transcribe_sarvam_rest(
        path,
        model=model,
        language=language,
        mode=mode,
        with_timestamps=require_timestamps,
        timeout=timeout,
        request_gap_seconds=float(os.environ.get("EARNALISM_SARVAM_ASR_REQUEST_GAP_SECONDS", "0.25")),
    )


def transcribe(path: Path, *, provider: str, model: str, language: str, timeout: float) -> str:
    if provider == "openai":
        return transcribe_openai(path, model=model, language=language, timeout=timeout)
    if provider == "google":
        return transcribe_google(path, model=model, language=language, timeout=timeout)
    if provider == "sarvam":
        return transcribe_sarvam(path, model=model, language=language, timeout=timeout)
    raise RuntimeError(f"Unsupported ASR calibration provider: {provider}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--chunk-ids", required=True)
    parser.add_argument("--provider", choices=("openai", "google", "sarvam"), default="openai")
    parser.add_argument("--models", default="gpt-4o-mini-transcribe")
    parser.add_argument("--language-options", default="auto")
    parser.add_argument("--modes", default="transcribe")
    parser.add_argument("--require-timestamps", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--max-estimated-usd", type=float, required=True)
    parser.add_argument("--prior-estimated-usd", type=float, default=0.0)
    parser.add_argument("--cumulative-cap-usd", type=float, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")
    if args.provider == "google" and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        raise SystemExit("GOOGLE_CLOUD_PROJECT is required")
    if args.execute and args.provider == "sarvam" and not os.environ.get("SARVAM_API_KEY"):
        raise SystemExit("SARVAM_API_KEY is required")
    if args.execute and args.provider == "sarvam":
        require_paid_campaign_approval()
    run_dir = validate_internal_path(args.run_dir, label="run-dir")
    manifest = read_json(run_dir / "tts_chunk_manifest.json")
    chunks = selected_chunks(manifest, parse_csv(args.chunk_ids), run_dir)
    models = parse_csv(args.models)
    languages = parse_csv(args.language_options)
    modes = parse_csv(args.modes) if args.provider == "sarvam" else ["default"]
    arms = [(model, language, mode) for model in models for language in languages for mode in modes]
    rate = float(os.environ.get("EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE", "0.008"))
    estimate = estimated_cost(chunks, len(arms), rate)
    if estimate > args.max_estimated_usd:
        raise SystemExit(f"Estimated calibration cost {estimate:.4f} exceeds cap {args.max_estimated_usd:.4f}")
    cumulative_estimate = round(args.prior_estimated_usd + estimate, 4)
    if cumulative_estimate > args.cumulative_cap_usd:
        raise SystemExit(
            f"Estimated cumulative pilot cost {cumulative_estimate:.4f} exceeds cap {args.cumulative_cap_usd:.4f}"
        )
    if args.execute and args.provider == "sarvam":
        validate_campaign_budget(
            title_estimate_usd=estimate,
            campaign_cumulative_usd=cumulative_estimate,
        )
    output = validate_internal_path(args.output if args.output.is_absolute() else ROOT / args.output, label="output")
    fingerprint = {
        "slug": args.slug,
        "provider": args.provider,
        "chunks": [{"chunk_id": item["chunk_id"], "audio_hash": item["audio_hash"]} for item in chunks],
        "models": models,
        "languages": languages,
        "modes": modes,
        "require_timestamps": args.require_timestamps,
        "source_manifest_sha256": sha256_file(run_dir / "tts_chunk_manifest.json"),
        "provider_configuration": {
            "endpoint": SARVAM_STT_ENDPOINT if args.provider == "sarvam" else "provider_default",
            "transport": "rest" if args.provider == "sarvam" else "provider_default",
            "mode": modes if args.provider == "sarvam" else "provider_default",
            "with_timestamps": args.require_timestamps if args.provider == "sarvam" else None,
            "clip_seconds": SARVAM_REST_CLIP_SECONDS if args.provider == "sarvam" else None,
            "clip_codec": "pcm_s16le_16khz_mono" if args.provider == "sarvam" else None,
        },
        "runner_sha256": sha256_file(Path(__file__)),
        "adapter_sha256": sha256_file(SCRIPTS_DIR / "providers/sarvam_stt_adapter.py"),
        "normalizer_sha256": sha256_file(SCRIPTS_DIR / "bengali_asr_normalization.py"),
    }
    if output.exists():
        prior = read_json(output)
        if same_attempt(prior.get("fingerprint") or {}, fingerprint) and prior.get("provider_calls_ran") is True:
            raise SystemExit("Identical calibration already ran; refusing duplicate provider calls")
    preflight = {
        "generated_at": iso_now(),
        "slug": args.slug,
        "status": "DRY_RUN_PASS",
        "fingerprint": fingerprint,
        "estimated_cost_usd": estimate,
        "max_estimated_usd": args.max_estimated_usd,
        "prior_estimated_usd": args.prior_estimated_usd,
        "estimated_cumulative_usd": cumulative_estimate,
        "cumulative_cap_usd": args.cumulative_cap_usd,
        "provider_calls_ran": False,
        "results": [],
    }
    if not args.execute:
        atomic_write(output, preflight)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0

    original_lock = args.lock_path.expanduser().resolve().read_bytes()
    lock = load_lock(original_lock, slug=args.slug)
    results = []
    try:
        atomic_write(args.lock_path, acquired_lock(lock, slug=args.slug, estimate=estimate))
        for model, language, mode in arms:
            for chunk in chunks:
                item = {
                    "model": model,
                    "provider": args.provider,
                    "language": language,
                    "mode": mode,
                    "chunk_id": chunk["chunk_id"],
                    "audio_hash": chunk["audio_hash"],
                    "duration_seconds": chunk.get("duration_seconds"),
                }
                try:
                    timeout = float(os.environ.get("EARNALISM_ASR_REQUEST_TIMEOUT_SECONDS", "180"))
                    timestamp_count = 0
                    if args.provider == "sarvam":
                        response = transcribe_sarvam_payload(
                            Path(chunk["audio_path"]),
                            model=model,
                            language=language,
                            mode=mode,
                            require_timestamps=args.require_timestamps,
                            timeout=timeout,
                        )
                        transcript = str(response.get("text") or "")
                        timestamp_count = len(response.get("words") or [])
                    else:
                        transcript = transcribe(
                            Path(chunk["audio_path"]),
                            provider=args.provider,
                            model=model,
                            language=language,
                            timeout=timeout,
                        )
                    profile = {"detected": detect_script_mix(transcript), "counts": script_counts(transcript)}
                    similarity = transcript_similarity(str(chunk.get("text") or ""), transcript)
                    ratio = script_ratio(profile)
                    with tempfile.TemporaryDirectory(prefix="earnalism-asr-projection-") as projection_dir:
                        projection = analyze_bengali_asr(
                            slug=f"{args.slug}-{chunk['chunk_id']}",
                            title=args.slug,
                            author="",
                            language="ben",
                            manuscript=str(chunk.get("text") or ""),
                            transcript=transcript,
                            run_dir=Path(projection_dir),
                            audio_hash=str(chunk["audio_hash"]),
                            raw_asr_score=float(similarity["score"]),
                            raw_similarity=float(similarity["raw_similarity"]),
                            raw_coverage=float(similarity["coverage"]),
                        )
                    normalized_score = float(projection.get("normalized_asr_score") or 0)
                    phonetic_score = float(projection.get("phonetic_projection_score") or 0)
                    projected_score = min(normalized_score, phonetic_score)
                    strict_pass = (
                        float(similarity["score"]) >= 9.7
                        and normalized_score >= 9.7
                        and phonetic_score >= 9.7
                        and float(projection.get("coverage") or 0) >= 0.98
                        and float(projection.get("projection_confidence") or 0) >= 0.97
                        and bool(projection.get("first_words_match"))
                        and bool(projection.get("last_words_match"))
                        and not projection.get("missing_spans")
                        and not projection.get("extra_spans")
                        and ratio >= 0.9
                        and (not args.require_timestamps or timestamp_count > 0)
                    )
                    item.update(
                        {
                            "status": "PASS" if strict_pass else "BELOW_THRESHOLD",
                            "transcript": transcript,
                            "transcript_hash": hashlib.sha256(transcript.encode()).hexdigest(),
                            "transcript_chars": len(transcript),
                            "source_score": projected_score,
                            "raw_source_score": similarity["score"],
                            "raw_similarity": similarity["raw_similarity"],
                            "char_similarity": similarity["char_similarity"],
                            "token_order_similarity": projection.get("projection_confidence"),
                            "coverage": projection.get("coverage"),
                            "first_words_match": projection.get("first_words_match"),
                            "last_words_match": projection.get("last_words_match"),
                            "first_words_match_score": similarity["first_words_match_score"],
                            "last_words_match_score": similarity["last_words_match_score"],
                            "script_profile": profile,
                            "bengali_script_ratio": ratio,
                            "measured_timestamp_count": timestamp_count,
                            "timestamp_granularity": "word" if timestamp_count else "none",
                            "audio_derived_projection": {
                                key: projection.get(key)
                                for key in (
                                    "normalized_asr_score",
                                    "phonetic_projection_score",
                                    "coverage",
                                    "projection_confidence",
                                    "first_words_match",
                                    "last_words_match",
                                    "missing_spans",
                                    "extra_spans",
                                    "content_match_proven",
                                    "release_pass",
                                )
                            },
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    item.update({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:1000]})
                results.append(item)
    finally:
        atomic_write(args.lock_path, original_lock)
    arm_summaries = summarize_arms(results, [item["chunk_id"] for item in chunks])
    best = best_arm(arm_summaries)
    completed_estimate = round(
        sum(float(item.get("duration_seconds") or 0) for item in results)
        / 60.0
        * rate,
        4,
    )
    payload = {
        **preflight,
        "generated_at": iso_now(),
        "status": "CALIBRATION_PASS" if best and best.get("status") == "PASS" else "CALIBRATION_REPAIR_REQUIRED",
        "provider_calls_ran": True,
        "completed_call_estimated_cost_usd": completed_estimate,
        "results": results,
        "arm_summaries": arm_summaries,
        "best_arm": best,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": args.lock_path.read_bytes() == original_lock,
    }
    atomic_write(output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "CALIBRATION_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
