#!/usr/bin/env python3
"""Validate clean ElevenLabs narration text for the Dracula internal workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUDIO_FILE_EXTENSIONS = {".aac", ".m4a", ".mp3", ".ogg", ".wav"}

BANNED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("comment line", re.compile(r"(?m)^\s*#")),
    ("sentence id marker", re.compile(r"\[s\d{3}\]", re.IGNORECASE)),
    ("raw underscore or markdown italic marker", re.compile(r"_|\*[^*\n]+\*")),
    ("asterism separator", re.compile(r"\*\s+\*\s+\*\s+\*\s+\*")),
    ("raw memorandum markup", re.compile(r"\(_Mem\._", re.IGNORECASE)),
    ("raw double-hyphen punctuation", re.compile(r"--")),
    (
        "internal instruction",
        re.compile(
            r"Do not narrate|Internal-only|Internal only|Public audio release|"
            r"NOT FOR ELEVENLABS|sync/highlight|sentence IDs?|frontend/public|frontend/build",
            re.IGNORECASE,
        ),
    ),
)

REQUIRED_CHUNK_FIELDS = {
    "chunk_id",
    "sentence_ids",
    "narration_text",
    "text_hash",
    "estimated_duration_seconds",
    "generation_status",
}


class NarrationValidationError(ValueError):
    """Raised when narration text or chunk metadata is not generation-ready."""

    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__("\n".join(failures))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _line_number_for(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def validate_text(label: str, text: str) -> list[str]:
    failures: list[str] = []
    if not text.strip():
        failures.append(f"{label}: narration text is empty")
        return failures

    for name, pattern in BANNED_PATTERNS:
        match = pattern.search(text)
        if match:
            line_number = _line_number_for(text, match.start())
            snippet = match.group(0).replace("\n", "\\n")
            failures.append(f"{label}: banned {name} on line {line_number}: {snippet}")
    return failures


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def public_audio_files() -> list[str]:
    matches: list[str] = []
    for relative in ("frontend/public", "frontend/build"):
        root = ROOT / relative
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_FILE_EXTENSIONS:
                matches.append(str(path.relative_to(ROOT)))
    return sorted(matches)


def validate_sentence_map(sample_dir: Path) -> tuple[dict[str, Any], list[str]]:
    path = sample_dir / "sentence_map.json"
    failures: list[str] = []
    if not path.exists():
        return {}, [f"{path}: sentence_map.json is missing"]

    sentence_map = load_json(path)
    if not isinstance(sentence_map, dict) or not sentence_map:
        return {}, [f"{path}: sentence_map.json must be a non-empty object"]

    expected_ids = [f"s{index:03d}" for index in range(1, len(sentence_map) + 1)]
    actual_ids = list(sentence_map)
    if actual_ids != expected_ids:
        failures.append(f"{path}: sentence IDs must be contiguous and ordered from {expected_ids[0]}")

    for sentence_id, entry in sentence_map.items():
        if not re.fullmatch(r"s\d{3}", sentence_id):
            failures.append(f"{path}: invalid sentence ID {sentence_id!r}")
            continue
        if not isinstance(entry, dict):
            failures.append(f"{path}: {sentence_id} must map to an object")
            continue
        narration_text = str(entry.get("narration_text") or "")
        sync_action = str(entry.get("sync_action") or "narrate")
        if sync_action == "pause_only":
            if narration_text.strip():
                failures.append(f"{path}: {sentence_id} pause_only entry must not include narration_text")
            if not entry.get("silence_ms"):
                failures.append(f"{path}: {sentence_id} pause_only entry must include silence_ms")
            continue
        failures.extend(validate_text(f"{path}:{sentence_id}.narration_text", narration_text))
    return sentence_map, failures


def validate_chunk_manifest(sample_dir: Path, sentence_map: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    path = sample_dir / "chunk_manifest.json"
    failures: list[str] = []
    if not path.exists():
        return {}, [f"{path}: chunk_manifest.json is missing"]

    manifest = load_json(path)
    chunks = manifest.get("chunks") if isinstance(manifest, dict) else None
    if not isinstance(chunks, list) or not chunks:
        return {}, [f"{path}: chunks must be a non-empty list"]

    for index, chunk in enumerate(chunks, start=1):
        label = f"{path}:chunk[{index}]"
        if not isinstance(chunk, dict):
            failures.append(f"{label}: chunk must be an object")
            continue
        missing = sorted(REQUIRED_CHUNK_FIELDS - set(chunk))
        if missing:
            failures.append(f"{label}: missing required fields: {', '.join(missing)}")
        if chunk.get("generation_status") != "NOT_GENERATED":
            failures.append(f"{label}: generation_status must be NOT_GENERATED")

        sentence_ids = chunk.get("sentence_ids")
        if not isinstance(sentence_ids, list) or not sentence_ids:
            failures.append(f"{label}: sentence_ids must be a non-empty list")
            sentence_ids = []

        narration_text = str(chunk.get("narration_text") or "")
        failures.extend(validate_text(f"{label}.narration_text", narration_text))

        expected_lines: list[str] = []
        for sentence_id in sentence_ids:
            entry = sentence_map.get(str(sentence_id))
            if not isinstance(entry, dict):
                failures.append(f"{label}: unknown sentence_id {sentence_id!r}")
                continue
            mapped_text = str(entry.get("narration_text") or "").strip()
            if mapped_text:
                expected_lines.append(mapped_text)
        expected_text = "\n".join(expected_lines)
        if expected_text and narration_text != expected_text:
            failures.append(f"{label}: narration_text must match sentence_map narration order")
        if narration_text and chunk.get("text_hash") != sha256_text(narration_text):
            failures.append(f"{label}: text_hash does not match narration_text")
        duration = chunk.get("estimated_duration_seconds")
        if not isinstance(duration, (int, float)) or duration <= 0:
            failures.append(f"{label}: estimated_duration_seconds must be positive")

    return manifest, failures


def validate_sample_dir(sample_dir: Path) -> dict[str, Any]:
    sample_dir = sample_dir if sample_dir.is_absolute() else ROOT / sample_dir
    failures: list[str] = []

    narration_path = sample_dir / "full_chapter_narration_text.txt"
    if narration_path.exists():
        narration_text = narration_path.read_text(encoding="utf-8")
        failures.extend(validate_text(str(narration_path), narration_text))
    else:
        failures.append(f"{narration_path}: full_chapter_narration_text.txt is missing")
        narration_text = ""

    sentence_map, map_failures = validate_sentence_map(sample_dir)
    failures.extend(map_failures)
    chunk_manifest, chunk_failures = validate_chunk_manifest(sample_dir, sentence_map)
    failures.extend(chunk_failures)

    public_audio = public_audio_files()
    if public_audio:
        failures.append("public audio files are present: " + ", ".join(public_audio))

    if failures:
        raise NarrationValidationError(failures)

    chunks = chunk_manifest.get("chunks", [])
    pause_count = sum(1 for entry in sentence_map.values() if entry.get("sync_action") == "pause_only")
    return {
        "sample_dir": str(sample_dir.relative_to(ROOT) if sample_dir.is_relative_to(ROOT) else sample_dir),
        "narration_file": str(narration_path.relative_to(ROOT) if narration_path.is_relative_to(ROOT) else narration_path),
        "narration_hash": sha256_text(narration_text),
        "sentence_count": len(sentence_map),
        "pause_only_count": pause_count,
        "chunk_count": len(chunks),
        "public_audio_files": public_audio,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        summary = validate_sample_dir(args.sample_dir)
    except NarrationValidationError as exc:
        print("ElevenLabs narration text validation failed:", file=sys.stderr)
        for failure in exc.failures:
            print(f"- {failure}", file=sys.stderr)
        return 2

    print(
        "ElevenLabs narration text validation passed: "
        f"narration_file={summary['narration_file']} "
        f"sentences={summary['sentence_count']} chunks={summary['chunk_count']} "
        f"pause_only={summary['pause_only_count']} public_audio_files=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
