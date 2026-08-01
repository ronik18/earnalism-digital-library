#!/usr/bin/env python3
"""Offline, checkpoint-aware rescue for mixed-script Bengali ASR evidence.

This tool reuses existing transcripts and TTS chunk bindings. It performs no
provider calls, does not modify audio, and cannot approve public release. Its
only purpose is to distinguish a script false-negative from under-transcription
or a real audio/manuscript mismatch before any additional spend is considered.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from bengali_asr_normalization import detect_script_mix, script_counts, tokenize


MIN_SOURCE_SCORE = 9.7
MIN_COVERAGE = 0.97
MIN_PROJECTION_CONFIDENCE = 0.95


class RescueError(RuntimeError):
    """Raised when source-bound checkpoint evidence is malformed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RescueError(f"invalid JSON object: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RescueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_path(path: Path) -> str:
    parts = path.resolve().parts
    if "internal" in parts:
        return Path(*parts[parts.index("internal") :]).as_posix()
    return path.name


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def chunk_id(chunk: Mapping[str, Any]) -> str:
    explicit = str(chunk.get("chunk_id") or "").strip()
    if explicit:
        return explicit
    try:
        return f"group_{int(chunk['index']):04d}"
    except (KeyError, TypeError, ValueError) as exc:
        raise RescueError("TTS chunk has neither chunk_id nor integer index") from exc


def token_values(text: str, attribute: str) -> list[str]:
    values: list[str] = []
    for token in tokenize(text):
        value = str(getattr(token, attribute) or "")
        if value:
            values.append(value)
    return values


def ordered_exact_coverage(actual: Sequence[str], expected: Sequence[str]) -> tuple[float, float, int]:
    if not actual or not expected:
        return 0.0, 0.0, 0
    matcher = SequenceMatcher(None, list(expected), list(actual), autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return matched / len(expected), matched / len(actual), matched


def char_similarity(actual: Sequence[str], expected: Sequence[str]) -> float:
    left = " ".join(actual)
    right = " ".join(expected)
    return SequenceMatcher(None, left, right, autojunk=False).ratio() if left and right else 0.0


def edge_match(actual: Sequence[str], expected: Sequence[str], *, first: bool) -> bool:
    if not actual or not expected:
        return False
    window = 12
    actual_edge = "".join(actual[:window] if first else actual[-window:])
    expected_edge = "".join(expected[:window] if first else expected[-window:])
    return SequenceMatcher(None, actual_edge, expected_edge, autojunk=False).ratio() >= 0.78


def score_checkpoint(expected_text: str, transcript: str, identifier: str) -> dict[str, Any]:
    expected_phonetic = token_values(expected_text, "phonetic")
    actual_phonetic = token_values(transcript, "phonetic")
    expected_normalized = token_values(expected_text, "normalized")
    actual_normalized = token_values(transcript, "normalized")
    coverage, precision, matched = ordered_exact_coverage(actual_phonetic, expected_phonetic)
    phonetic_similarity = char_similarity(actual_phonetic, expected_phonetic)
    normalized_similarity = char_similarity(actual_normalized, expected_normalized)
    length_coverage = min(1.0, len(actual_phonetic) / len(expected_phonetic)) if expected_phonetic else 0.0
    # A high character similarity cannot hide a truncated transcript. The
    # source score therefore remains bounded by transcript length coverage.
    source_score = min(max(phonetic_similarity, normalized_similarity), length_coverage) * 10
    confidence = min(coverage, precision, length_coverage)
    return {
        "chunk_id": identifier,
        "script": detect_script_mix(transcript),
        "script_counts": script_counts(transcript),
        "expected_token_count": len(expected_phonetic),
        "transcript_token_count": len(actual_phonetic),
        "ordered_exact_match_count": matched,
        "ordered_exact_coverage": round(coverage, 4),
        "ordered_exact_precision": round(precision, 4),
        "transcript_length_coverage": round(length_coverage, 4),
        "normalized_similarity": round(normalized_similarity, 4),
        "phonetic_similarity": round(phonetic_similarity, 4),
        "source_score": round(source_score, 4),
        "projection_confidence": round(confidence, 4),
        "first_words_match": edge_match(actual_phonetic, expected_phonetic, first=True),
        "last_words_match": edge_match(actual_phonetic, expected_phonetic, first=False),
    }


def build_report(
    *,
    slug: str,
    title: str,
    author: str,
    manifest_path: Path,
    checkpoint_dir: Path,
) -> dict[str, Any]:
    manifest = load_object(manifest_path)
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise RescueError("TTS manifest has no chunks")
    results: list[dict[str, Any]] = []
    missing_checkpoints: list[str] = []
    invalid_checkpoints: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise RescueError("TTS manifest contains a non-object chunk")
        identifier = chunk_id(chunk)
        expected = str(chunk.get("text") or "")
        checkpoint_path = checkpoint_dir / f"{identifier}.json"
        if not checkpoint_path.is_file():
            missing_checkpoints.append(identifier)
            continue
        checkpoint = load_object(checkpoint_path)
        if checkpoint.get("status") != "PASS" or not str(checkpoint.get("transcript_text") or "").strip():
            invalid_checkpoints.append(identifier)
            continue
        transcript = str(checkpoint["transcript_text"])
        results.append(score_checkpoint(expected, transcript, identifier))

    if not results:
        raise RescueError("no passing ASR checkpoints were available")
    expected_tokens = sum(int(row["expected_token_count"]) for row in results)
    weighted = lambda key: (
        sum(float(row[key]) * int(row["expected_token_count"]) for row in results) / expected_tokens
        if expected_tokens else 0.0
    )
    script_distribution: Counter[str] = Counter(str(row["script"]) for row in results)
    failing = [
        str(row["chunk_id"])
        for row in results
        if float(row["source_score"]) < MIN_SOURCE_SCORE
        or float(row["transcript_length_coverage"]) < MIN_COVERAGE
    ]
    aggregate_score = round(weighted("source_score"), 4)
    aggregate_coverage = round(weighted("transcript_length_coverage"), 4)
    aggregate_confidence = round(weighted("projection_confidence"), 4)
    first_match = bool(results[0]["first_words_match"])
    last_match = bool(results[-1]["last_words_match"])
    content_gate_passed = bool(
        not missing_checkpoints
        and not invalid_checkpoints
        and not failing
        and aggregate_score >= MIN_SOURCE_SCORE
        and aggregate_coverage >= MIN_COVERAGE
        and aggregate_confidence >= MIN_PROJECTION_CONFIDENCE
        and first_match
        and last_match
    )
    if content_gate_passed:
        classification = "SCRIPT_RESCUE_CONTENT_MATCH_PROVEN_SYNC_REBUILD_REQUIRED"
        next_action = "Rebuild measured Bengali paragraph or stanza sync, then run independent full listening QA; do not publish from this diagnostic."
    elif aggregate_coverage < 0.85:
        classification = "CHECKPOINT_ASR_UNDERTRANSCRIPTION_OR_SOURCE_MISMATCH_CONFIRMED"
        next_action = "Do not master or publish this candidate. Preserve the failed fingerprint and use source-bound human narration or licensed audio; retry ASR only if a separately authorized, Bengali-capable model can target the failing checkpoints."
    else:
        classification = "SCRIPT_NORMALIZATION_INSUFFICIENT_SOURCE_MATCH_NOT_PROVEN"
        next_action = "Do not master or publish this candidate. Validate a source-bound replacement through the existing narration intake packet."
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "slug": slug,
        "title": title,
        "author": author,
        "mode": "OFFLINE_EXISTING_CHECKPOINT_REUSE",
        "classification": classification,
        "thresholds": {
            "minimum_source_score": MIN_SOURCE_SCORE,
            "minimum_coverage": MIN_COVERAGE,
            "minimum_projection_confidence": MIN_PROJECTION_CONFIDENCE,
        },
        "source_binding": {
            "tts_manifest": evidence_path(manifest_path),
            "tts_manifest_sha256": sha256_file(manifest_path),
            "checkpoint_dir": evidence_path(checkpoint_dir),
            "manifest_chunk_count": len(chunks),
            "passing_checkpoint_count": len(results),
            "missing_checkpoint_ids": missing_checkpoints,
            "invalid_checkpoint_ids": invalid_checkpoints,
        },
        "aggregate": {
            "source_score": aggregate_score,
            "transcript_length_coverage": aggregate_coverage,
            "projection_confidence": aggregate_confidence,
            "full_transcript_phonetic_similarity": round(weighted("phonetic_similarity"), 4),
            "first_words_match": first_match,
            "last_words_match": last_match,
            "failing_checkpoint_count": len(failing),
            "failing_checkpoint_ids": failing,
            "script_distribution": dict(sorted(script_distribution.items())),
        },
        "checkpoint_results": results,
        "release_gates": {
            "content_gate_passed": content_gate_passed,
            "measured_sync_passed": False,
            "independent_listening_passed": False,
            "public_release_approved": False,
        },
        "safety": {
            "provider_calls_ran": False,
            "audio_modified": False,
            "paid_tts_lock_touched": False,
            "public_metadata_mutated": False,
            "diagnostic_normalization_is_release_transcript": False,
        },
        "next_action": next_action,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    aggregate = report["aggregate"]
    gates = report["release_gates"]
    return "\n".join(
        [
            f"# {report['slug']} Mixed-Script ASR Rescue",
            "",
            f"- Classification: `{report['classification']}`",
            f"- Offline source score: {aggregate['source_score']} / 10 (required {report['thresholds']['minimum_source_score']})",
            f"- Transcript length coverage: {aggregate['transcript_length_coverage']}",
            f"- Projection confidence: {aggregate['projection_confidence']}",
            f"- First words match: {aggregate['first_words_match']}",
            f"- Last words match: {aggregate['last_words_match']}",
            f"- Failing checkpoints: {aggregate['failing_checkpoint_count']}",
            f"- Content gate passed: {gates['content_gate_passed']}",
            "- Provider calls: none",
            "- Audio/public metadata/paid lock mutations: none",
            "",
            "## Decision",
            "",
            str(report["next_action"]),
            "",
        ]
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--author", default="")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--checkpoint-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        slug=args.slug,
        title=args.title,
        author=args.author,
        manifest_path=args.manifest.resolve(),
        checkpoint_dir=args.checkpoint_dir.resolve(),
    )
    output = args.output.resolve()
    atomic_write_json(output, report)
    atomic_write_text(output.with_suffix(".md"), render_markdown(report))
    print(json.dumps({
        "output": str(output),
        "classification": report["classification"],
        "source_score": report["aggregate"]["source_score"],
        "content_gate_passed": report["release_gates"]["content_gate_passed"],
        "provider_calls_ran": False,
        "public_release_approved": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
