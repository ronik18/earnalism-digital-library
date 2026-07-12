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
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
import sys

sys.path.insert(0, str(HOOK_DIR))
from asr_sync_hook import transcript_similarity  # noqa: E402
from bengali_asr_normalization import detect_script_mix, script_counts  # noqa: E402


HOLDER = "sprint1_bengali_asr_model_calibration"


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


def load_lock(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("status") != "active" or payload.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock is not available")
    if payload.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
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


def transcribe(path: Path, *, provider: str, model: str, language: str, timeout: float) -> str:
    if provider == "openai":
        return transcribe_openai(path, model=model, language=language, timeout=timeout)
    if provider == "google":
        return transcribe_google(path, model=model, language=language, timeout=timeout)
    raise RuntimeError(f"Unsupported ASR calibration provider: {provider}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--chunk-ids", required=True)
    parser.add_argument("--provider", choices=("openai", "google"), default="openai")
    parser.add_argument("--models", default="gpt-4o-mini-transcribe")
    parser.add_argument("--language-options", default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--max-estimated-usd", type=float, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")
    if args.provider == "google" and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        raise SystemExit("GOOGLE_CLOUD_PROJECT is required")
    run_dir = args.run_dir.expanduser().resolve()
    manifest = read_json(run_dir / "tts_chunk_manifest.json")
    chunks = selected_chunks(manifest, parse_csv(args.chunk_ids), run_dir)
    models = parse_csv(args.models)
    languages = parse_csv(args.language_options)
    arms = [(model, language) for model in models for language in languages]
    rate = float(os.environ.get("EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE", "0.008"))
    estimate = estimated_cost(chunks, len(arms), rate)
    if estimate > args.max_estimated_usd:
        raise SystemExit(f"Estimated calibration cost {estimate:.4f} exceeds cap {args.max_estimated_usd:.4f}")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    fingerprint = {
        "slug": args.slug,
        "provider": args.provider,
        "chunks": [{"chunk_id": item["chunk_id"], "audio_hash": item["audio_hash"]} for item in chunks],
        "models": models,
        "languages": languages,
    }
    if output.exists():
        prior = read_json(output)
        if prior.get("fingerprint") == fingerprint and prior.get("provider_calls_ran") is True:
            raise SystemExit("Identical calibration already ran; refusing duplicate provider calls")
    preflight = {
        "generated_at": iso_now(),
        "slug": args.slug,
        "status": "DRY_RUN_PASS",
        "fingerprint": fingerprint,
        "estimated_cost_usd": estimate,
        "max_estimated_usd": args.max_estimated_usd,
        "provider_calls_ran": False,
        "results": [],
    }
    if not args.execute:
        atomic_write(output, preflight)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0

    original_lock = args.lock_path.expanduser().resolve().read_bytes()
    lock = load_lock(original_lock)
    results = []
    try:
        atomic_write(args.lock_path, acquired_lock(lock, slug=args.slug, estimate=estimate))
        for model, language in arms:
            for chunk in chunks:
                item = {
                    "model": model,
                    "provider": args.provider,
                    "language": language,
                    "chunk_id": chunk["chunk_id"],
                    "audio_hash": chunk["audio_hash"],
                    "duration_seconds": chunk.get("duration_seconds"),
                }
                try:
                    transcript = transcribe(
                        Path(chunk["audio_path"]),
                        provider=args.provider,
                        model=model,
                        language=language,
                        timeout=float(os.environ.get("EARNALISM_ASR_REQUEST_TIMEOUT_SECONDS", "180")),
                    )
                    profile = {"detected": detect_script_mix(transcript), "counts": script_counts(transcript)}
                    similarity = transcript_similarity(str(chunk.get("text") or ""), transcript)
                    ratio = script_ratio(profile)
                    item.update(
                        {
                            "status": "PASS" if similarity["score"] >= 9.7 and ratio >= 0.9 else "BELOW_THRESHOLD",
                            "transcript": transcript,
                            "transcript_hash": hashlib.sha256(transcript.encode()).hexdigest(),
                            "transcript_chars": len(transcript),
                            "source_score": similarity["score"],
                            "first_words_match": similarity["first_words_match"],
                            "last_words_match": similarity["last_words_match"],
                            "script_profile": profile,
                            "bengali_script_ratio": ratio,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    item.update({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:1000]})
                results.append(item)
    finally:
        atomic_write(args.lock_path, original_lock)
    best = best_arm(results)
    payload = {
        **preflight,
        "generated_at": iso_now(),
        "status": "CALIBRATION_PASS" if best and best.get("status") == "PASS" else "CALIBRATION_REPAIR_REQUIRED",
        "provider_calls_ran": True,
        "results": results,
        "best_arm": best,
        "actual_provider_billing": "NOT_REPORTED",
        "lock_restored": args.lock_path.read_bytes() == original_lock,
    }
    atomic_write(output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "CALIBRATION_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
