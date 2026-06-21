#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "output/audiobook_bakeoff/kshudhita-pashan"
REPORT_MD = ROOT / "AUDIOBOOK_MODEL_BAKEOFF_AUDIO_QA_REPORT.md"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe_duration(path: Path) -> float | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return round(float(result.stdout.strip()), 3)
    except ValueError:
        return None


def evaluate_audio_file(path: Path) -> dict[str, Any]:
    duration = ffprobe_duration(path)
    size = path.stat().st_size
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": True,
        "file_size_bytes": size,
        "sha256": sha256_file(path),
        "duration_seconds": duration,
        "obviously_empty_audio": size < 2048 or duration == 0,
        "public_path_leakage": "/public/" in str(path) or "/frontend/public/" in str(path),
        "asr_back_transcription": "OPERATOR_REQUIRED",
        "mos_predictor": "OPERATOR_REQUIRED",
        "forced_alignment": "OPERATOR_REQUIRED",
    }


def evaluate_samples(book_slug: str) -> dict[str, Any]:
    if book_slug != "kshudhita-pashan":
        raise ValueError("Audio sample evaluation is scoped only to kshudhita-pashan.")
    audio_files = sorted(
        [
            *OUTPUT_ROOT.glob("**/*.wav"),
            *OUTPUT_ROOT.glob("**/*.mp3"),
            *OUTPUT_ROOT.glob("**/*.ogg"),
            *OUTPUT_ROOT.glob("**/*.aac"),
        ]
    )
    records = [evaluate_audio_file(path) for path in audio_files]
    repeated_hashes = {
        record["sha256"]
        for record in records
        if record.get("sha256") and sum(other.get("sha256") == record["sha256"] for other in records) > 1
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "book_slug": book_slug,
        "scope": "INTERNAL_REVIEW_ONLY",
        "audio_file_count": len(records),
        "missing_output": len(records) == 0,
        "repeated_audio_hashes": sorted(repeated_hashes),
        "public_path_leakage": any(record["public_path_leakage"] for record in records),
        "asr_metrics_status": "OPERATOR_REQUIRED",
        "mos_metrics_status": "OPERATOR_REQUIRED",
        "records": records,
    }
    write_json(OUTPUT_ROOT / "evaluation.json", payload)
    return payload


def write_report(payload: dict[str, Any]) -> None:
    lines = [
        "# Audiobook Model Bake-Off Audio QA Report",
        "",
        "Scope: `INTERNAL_REVIEW_ONLY`.",
        "",
        "No ASR, MOS, cloud STT, paid API, or public upload was run. Missing optional metrics are marked `OPERATOR_REQUIRED` rather than faked.",
        "",
        f"- Audio files found: `{payload['audio_file_count']}`",
        f"- Missing output: `{payload['missing_output']}`",
        f"- Public path leakage: `{payload['public_path_leakage']}`",
        f"- ASR metrics: `{payload['asr_metrics_status']}`",
        f"- MOS metrics: `{payload['mos_metrics_status']}`",
        "",
        "## Files",
        "",
    ]
    if not payload["records"]:
        lines.append("- No local audio files found. This is expected for dry-run-only PR validation.")
    for record in payload["records"]:
        lines.append(
            f"- `{record['path']}` size={record['file_size_bytes']} duration={record['duration_seconds']} "
            f"empty={record['obviously_empty_audio']}"
        )
    REPORT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate internal Bengali audiobook bake-off sample files.")
    parser.add_argument("--book-slug", default="kshudhita-pashan")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = evaluate_samples(args.book_slug)
    write_report(payload)
    print(f"Audio QA report written: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
