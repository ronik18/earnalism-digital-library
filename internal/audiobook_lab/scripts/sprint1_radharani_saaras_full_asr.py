#!/usr/bin/env python3
"""Checkpointed full-title Saaras ASR proof for the private Radharani canary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bengali_asr_normalization import analyze_bengali_asr  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent / "factory_hooks"))
from asr_sync_hook import transcript_similarity  # noqa: E402
from providers.sarvam_stt_adapter import (  # noqa: E402
    CLIP_SECONDS,
    DEFAULT_ENDPOINT,
    require_paid_campaign_approval,
    sha256_file,
    transcribe_rest,
    validate_campaign_budget,
)


HOLDER = "sprint1_radharani_saaras_full_asr"
REQUIRED_SCORE = 9.7
REQUIRED_COVERAGE = 0.98
REQUIRED_CONFIDENCE = 0.97


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def validate_internal_path(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve()
    internal_root = (ROOT / "internal").resolve()
    if resolved != internal_root and internal_root not in resolved.parents:
        raise RuntimeError(f"{label} must remain under the repository internal directory")
    return resolved


def validate_lock(raw: bytes, slug: str) -> dict[str, Any]:
    lock = json.loads(raw)
    if lock.get("status") != "active" or lock.get("current_holder") != "none":
        raise RuntimeError("paid_tts.lock is unavailable")
    if lock.get("allowed_next_holders") != []:
        raise RuntimeError("paid_tts.lock allowed_next_holders must be empty")
    if slug not in (lock.get("allowed_slugs") or []):
        raise RuntimeError(f"paid_tts.lock does not authorize slug: {slug}")
    return lock


def acquired_lock(lock: dict[str, Any], *, slug: str, estimate: float) -> dict[str, Any]:
    updated = dict(lock)
    updated.update(
        {
            "current_holder": HOLDER,
            "holder_started_at": iso_now(),
            "allowed_next_holders": [],
            "allowed_slugs": [slug],
            "budget_cap_usd": estimate,
            "approved_scope": f"{slug} Saaras v3 full-title ASR only; no TTS, listening, upload, metadata, or publication",
            "updated_at": iso_now(),
        }
    )
    return updated


def cost_estimate(chunks: list[dict[str, Any]], rate_per_minute: float) -> float:
    return round(sum(float(item.get("duration_seconds") or 0) for item in chunks) / 60.0 * rate_per_minute, 4)


def projection_summary(*, slug: str, source: str, transcript: str, audio_hash: str) -> dict[str, Any]:
    raw_similarity_result = transcript_similarity(source, transcript)
    with tempfile.TemporaryDirectory(prefix="earnalism-radharani-projection-") as temporary_directory:
        report = analyze_bengali_asr(
            slug=slug,
            title="রাধারাণী",
            author="বঙ্কিমচন্দ্র চট্টোপাধ্যায়",
            language="ben",
            manuscript=source,
            transcript=transcript,
            run_dir=Path(temporary_directory),
            audio_hash=audio_hash,
            raw_asr_score=float(raw_similarity_result["score"]),
            raw_similarity=float(raw_similarity_result["raw_similarity"]),
            raw_coverage=float(raw_similarity_result["coverage"]),
        )
    fields = (
        "raw_asr_script_detected",
        "raw_asr_score",
        "raw_similarity",
        "raw_coverage",
        "normalized_asr_score",
        "phonetic_projection_score",
        "coverage",
        "projection_confidence",
        "first_words_match",
        "last_words_match",
        "missing_spans",
        "extra_spans",
        "frontmatter_absent",
        "content_match_proven",
        "release_pass",
        "ordered_normalized_alignment",
        "ordered_phonetic_alignment",
    )
    return {field: report.get(field) for field in fields}


def group_pass(projection: dict[str, Any], word_count: int) -> bool:
    return bool(
        float(projection.get("raw_asr_score") or 0) >= REQUIRED_SCORE
        and float(projection.get("normalized_asr_score") or 0) >= REQUIRED_SCORE
        and float(projection.get("phonetic_projection_score") or 0) >= REQUIRED_SCORE
        and float(projection.get("coverage") or 0) >= REQUIRED_COVERAGE
        and float(projection.get("projection_confidence") or 0) >= REQUIRED_CONFIDENCE
        and projection.get("first_words_match") is True
        and projection.get("last_words_match") is True
        and not projection.get("missing_spans")
        and not projection.get("extra_spans")
        and projection.get("frontmatter_absent") is True
        and int(word_count) > 0
    )


def fingerprint(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "slug": manifest.get("slug"),
        "source_hash": manifest.get("source_hash"),
        "tts_prepared_text_hash": manifest.get("tts_prepared_text_hash"),
        "manifest_sha256": sha256_file(manifest_path),
        "final_audio_hash": manifest.get("final_audio_hash"),
        "provider": "sarvam",
        "endpoint": DEFAULT_ENDPOINT,
        "model": "saaras:v3",
        "language": "bn-IN",
        "mode": "transcribe",
        "transport": "rest",
        "with_timestamps": True,
        "timestamp_granularity": "word",
        "clip_seconds": CLIP_SECONDS,
        "runner_sha256": sha256_file(Path(__file__)),
        "adapter_sha256": sha256_file(Path(__file__).resolve().parent / "providers/sarvam_stt_adapter.py"),
        "normalizer_sha256": sha256_file(Path(__file__).resolve().parent / "bengali_asr_normalization.py"),
        "chunks": [
            {
                "index": int(item["index"]),
                "text_hash": item.get("text_hash"),
                "audio_sha256": item.get("sha256"),
                "duration_seconds": item.get("duration_seconds"),
            }
            for item in manifest.get("chunks") or []
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--prior-estimated-usd", type=float, required=True)
    parser.add_argument("--max-estimated-usd", type=float, required=True)
    parser.add_argument("--cumulative-cap-usd", type=float, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute and not os.environ.get("SARVAM_API_KEY"):
        raise SystemExit("SARVAM_API_KEY is required")
    if args.execute:
        require_paid_campaign_approval()
    run_dir = validate_internal_path(args.run_dir, label="run-dir")
    manifest_path = run_dir / "tts_chunk_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("slug") != "radharani":
        raise SystemExit("This bounded runner authorizes only radharani")
    chunks = list(manifest.get("chunks") or [])
    if len(chunks) != 28 or [int(item.get("index", -1)) for item in chunks] != list(range(28)):
        raise SystemExit("Radharani requires the exact 28-group TTS manifest")
    for item in chunks:
        path = ROOT / str(item.get("path") or "")
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise SystemExit(f"Audio hash mismatch for group_{int(item['index']):04d}")
    rate = float(os.environ.get("EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE", "0.008"))
    estimate = cost_estimate(chunks, rate)
    cumulative = round(args.prior_estimated_usd + estimate, 4)
    if estimate > args.max_estimated_usd:
        raise SystemExit(f"Estimated ASR cost {estimate:.4f} exceeds cap {args.max_estimated_usd:.4f}")
    if cumulative > args.cumulative_cap_usd:
        raise SystemExit(f"Estimated cumulative cost {cumulative:.4f} exceeds cap {args.cumulative_cap_usd:.4f}")
    if args.execute:
        validate_campaign_budget(title_estimate_usd=estimate, campaign_cumulative_usd=cumulative)
    output = validate_internal_path(args.output if args.output.is_absolute() else ROOT / args.output, label="output")
    attempt = fingerprint(manifest_path, manifest)
    prior = read_json(output) if output.exists() else {}
    if prior and prior.get("fingerprint") != attempt:
        raise SystemExit("Existing full-ASR evidence has a different fingerprint; refusing overwrite")
    if prior.get("provider_calls_ran") and prior.get("status") != "IN_PROGRESS":
        raise SystemExit("This full-ASR fingerprint is already closed; refusing duplicate provider calls")
    completed = list(prior.get("results") or []) if prior.get("status") == "IN_PROGRESS" else []
    completed_indices = {int(item["index"]) for item in completed if item.get("status") == "PASS"}
    preflight = {
        "generated_at": iso_now(),
        "slug": "radharani",
        "status": "DRY_RUN_PASS",
        "fingerprint": attempt,
        "estimated_cost_usd": estimate,
        "prior_estimated_usd": args.prior_estimated_usd,
        "estimated_cumulative_usd": cumulative,
        "max_estimated_usd": args.max_estimated_usd,
        "cumulative_cap_usd": args.cumulative_cap_usd,
        "required_score": REQUIRED_SCORE,
        "required_coverage": REQUIRED_COVERAGE,
        "required_confidence": REQUIRED_CONFIDENCE,
        "provider_calls_ran": bool(completed),
        "actual_provider_billing": "NOT_REPORTED",
        "results": completed,
    }
    if not args.execute:
        atomic_json(output, preflight)
        print(json.dumps({key: value for key, value in preflight.items() if key != "fingerprint"}, indent=2))
        return 0

    lock_path = args.lock_path.expanduser().resolve()
    original_lock = lock_path.read_bytes()
    lock = validate_lock(original_lock, "radharani")
    provider_calls_ran = bool(completed)
    failure = ""
    try:
        atomic_json(lock_path, acquired_lock(lock, slug="radharani", estimate=estimate))
        for chunk in chunks:
            index = int(chunk["index"])
            if index in completed_indices:
                continue
            current = {
                **preflight,
                "generated_at": iso_now(),
                "status": "IN_PROGRESS",
                "provider_calls_ran": provider_calls_ran,
                "results": completed,
                "next_group_index": index,
            }
            atomic_json(output, current)
            try:
                audio_path = ROOT / str(chunk["path"])
                response = transcribe_rest(
                    audio_path,
                    model="saaras:v3",
                    language="bn-IN",
                    mode="transcribe",
                    with_timestamps=True,
                    timeout=float(os.environ.get("EARNALISM_ASR_REQUEST_TIMEOUT_SECONDS", "180")),
                    request_gap_seconds=float(os.environ.get("EARNALISM_SARVAM_ASR_REQUEST_GAP_SECONDS", "0.25")),
                )
                provider_calls_ran = True
                transcript = str(response["text"])
                projection = projection_summary(
                    slug=f"radharani-group-{index:04d}",
                    source=str(chunk["text"]),
                    transcript=transcript,
                    audio_hash=str(chunk["sha256"]),
                )
                passed = group_pass(projection, len(response["words"]))
                result = {
                    "index": index,
                    "status": "PASS" if passed else "BELOW_THRESHOLD",
                    "text_hash": chunk["text_hash"],
                    "audio_sha256": chunk["sha256"],
                    "duration_seconds": chunk["duration_seconds"],
                    "transcript": transcript,
                    "transcript_sha256": sha256_text(transcript),
                    "words": response["words"],
                    "word_timestamp_count": len(response["words"]),
                    "request_count": response["request_count"],
                    "request_id_hashes": response["request_id_hashes"],
                    "clips": response["clips"],
                    "projection": projection,
                }
                completed.append(result)
                completed.sort(key=lambda item: int(item["index"]))
                atomic_json(
                    output,
                    {
                        **preflight,
                        "generated_at": iso_now(),
                        "status": "IN_PROGRESS" if passed else "FULL_ASR_CONTENT_GATE_FAILED",
                        "provider_calls_ran": True,
                        "results": completed,
                        "next_group_index": index + 1 if passed else None,
                    },
                )
                if not passed:
                    failure = f"group_{index:04d} failed the source gate"
                    break
            except Exception as exc:  # noqa: BLE001
                provider_calls_ran = True
                failure = f"{type(exc).__name__}: {exc}"[:1000]
                completed.append(
                    {
                        "index": index,
                        "status": "ERROR",
                        "error": failure,
                        "text_hash": chunk.get("text_hash"),
                        "audio_sha256": chunk.get("sha256"),
                        "duration_seconds": chunk.get("duration_seconds"),
                    }
                )
                atomic_json(
                    output,
                    {
                        **preflight,
                        "generated_at": iso_now(),
                        "status": "FULL_ASR_PROVIDER_ERROR",
                        "provider_calls_ran": True,
                        "results": completed,
                    },
                )
                break
    finally:
        lock_path.write_bytes(original_lock)

    all_pass = len(completed) == 28 and all(item.get("status") == "PASS" for item in completed)
    aggregate: dict[str, Any] = {}
    if all_pass:
        full_source = "\n\n".join(str(item["text"]) for item in chunks)
        full_transcript = "\n\n".join(str(item["transcript"]) for item in completed)
        aggregate_projection = projection_summary(
            slug="radharani-full-title",
            source=full_source,
            transcript=full_transcript,
            audio_hash=str(manifest["final_audio_hash"]),
        )
        offset = 0.0
        full_words: list[dict[str, Any]] = []
        for chunk, result in zip(chunks, completed):
            for word in result["words"]:
                full_words.append(
                    {
                        "word": word["word"],
                        "start": round(float(word["start"]) + offset, 3),
                        "end": round(float(word["end"]) + offset, 3),
                    }
                )
            offset += float(chunk["duration_seconds"])
        all_pass = group_pass(aggregate_projection, len(full_words))
        aggregate = {
            "status": "PASS" if all_pass else "BELOW_THRESHOLD",
            "source_text_sha256": sha256_text(full_source),
            "transcript_sha256": sha256_text(full_transcript),
            "transcript": full_transcript,
            "words": full_words,
            "word_timestamp_count": len(full_words),
            "timestamp_granularity": "word",
            "auto_estimated_sync": False,
            "projection": aggregate_projection,
            "normalized_asr_score_min": min(
                float(item["projection"]["normalized_asr_score"]) for item in completed
            ),
            "phonetic_projection_score_min": min(
                float(item["projection"]["phonetic_projection_score"]) for item in completed
            ),
            "coverage_min": min(float(item["projection"]["coverage"]) for item in completed),
            "projection_confidence_min": min(
                float(item["projection"]["projection_confidence"]) for item in completed
            ),
            "all_boundaries_match": all(
                item["projection"]["first_words_match"] and item["projection"]["last_words_match"]
                for item in completed
            ),
            "material_missing_or_extra_spans": sum(
                len(item["projection"].get("missing_spans") or [])
                + len(item["projection"].get("extra_spans") or [])
                for item in completed
            ),
        }
    status = "FULL_ASR_PASS" if all_pass else ("FULL_ASR_CONTENT_GATE_FAILED" if not failure else "FULL_ASR_BLOCKED")
    completed_cost = cost_estimate([chunks[int(item["index"])] for item in completed], rate)
    payload = {
        **preflight,
        "generated_at": iso_now(),
        "status": status,
        "provider_calls_ran": provider_calls_ran,
        "completed_call_estimated_cost_usd": completed_cost,
        "estimated_cumulative_completed_usd": round(args.prior_estimated_usd + completed_cost, 4),
        "actual_provider_billing": "NOT_REPORTED",
        "results": completed,
        "aggregate": aggregate,
        "failure": failure,
        "lock_restored": lock_path.read_bytes() == original_lock,
        "downstream_status": "NOT_RUN" if not all_pass else "READY_FOR_LISTENING_AND_SYNC_QA",
        "upload_performed": False,
        "publication_performed": False,
    }
    atomic_json(output, payload)
    print(
        json.dumps(
            {
                "status": status,
                "groups_completed": len(completed),
                "groups_passed": sum(item.get("status") == "PASS" for item in completed),
                "completed_call_estimated_cost_usd": completed_cost,
                "aggregate": {key: value for key, value in aggregate.items() if key not in {"transcript", "words"}},
                "lock_restored": payload["lock_restored"],
                "failure": failure,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if all_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
