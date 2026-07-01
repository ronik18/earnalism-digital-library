#!/usr/bin/env python3
"""Validate Dracula full audiobook internal-only preflight or generated state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BOOK_SLUG = "dracula"
EXPECTED_CHAPTER_COUNT = 27
PUBLIC_AUDIO_RELEASE_BLOCKED = "PUBLIC_AUDIO_RELEASE_BLOCKED"
OUTPUT_ROOT = ROOT / "internal" / "audiobook_lab" / BOOK_SLUG / "en" / "full-book"
PUBLIC_PATHS = (ROOT / "frontend" / "public", ROOT / "frontend" / "build")
AUDIO_VIDEO_ARCHIVE_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".aac",
    ".mp4",
    ".webm",
    ".zip",
}
REQUIRED_PREFLIGHT_FILES = (
    "FAST_DRACULA_AUDIOBOOK_PRODUCTION_PLAN.md",
    "chapter_manifest.json",
    "chunk_manifest.json",
    "character_count_report.json",
    "cost_preflight_report.json",
    "generation_preflight_report.json",
    "sync_manifest.json",
    "AUDIOBOOK_QA_REPORT.md",
    "HUMAN_REVIEW_FORM.md",
    "REGENERATION_QUEUE.json",
    "RELEASE_BLOCKERS.md",
    "sample_pack/SAMPLE_COMPARISON_REPORT.md",
    "sample_pack/sample_manifest.json",
)
REQUIRED_GENERATED_FILES = (
    "full_chapter_audio_manifest.json",
    "full_audiobook_manifest.json",
    "audio_checksums.json",
)
PAYMENT_OR_PRICING_PATTERNS = (
    "payment",
    "payments",
    "pricing",
    "checkout",
    "razorpay",
    "stripe",
    "invoice",
    "receipt",
)
LIVE_READER_ONLY_ALLOWLIST = (
    "dracula",
    "frankenstein",
    "jekyll-and-hyde",
    "carmilla",
    "hound-of-the-baskervilles",
    "picture-of-dorian-gray",
    "woman-in-white",
    "hungry-stones",
    "devdas",
    "pather-panchali",
    "eyesore-chokher-bali",
)
NON_DRACULA_AUDIO_FLAG_FIELDS = {
    "audio_enabled",
    "audioEnabled",
    "audiobook_enabled",
    "audiobookEnabled",
    "allowPublicAudio",
    "publicAudioAllowed",
    "listenNowAllowed",
}
NON_DRACULA_AUDIO_REFERENCE_KEYS = {
    "audioUrl",
    "audio_url",
    "audiobookUrl",
    "audiobook_url",
    "publicAudioUrl",
    "public_audio_url",
    "audioManifest",
    "audio_manifest",
    "publicAudioManifest",
    "public_audio_manifest",
    "waveformUrl",
    "waveform_url",
}


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def load_json(path: Path, issues: list[str]) -> Any:
    if not path.exists():
        issues.append(f"Missing required JSON file: {relative(path)}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"Invalid JSON in {relative(path)}: {exc}")
        return {}


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def scan_public_binaries() -> list[str]:
    found: list[str] = []
    for root in PUBLIC_PATHS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_VIDEO_ARCHIVE_EXTENSIONS:
                found.append(relative(path))
    return sorted(found)


def tracked_public_binaries() -> list[str]:
    patterns = [
        "frontend/public/**/*.mp3",
        "frontend/public/**/*.wav",
        "frontend/public/**/*.m4a",
        "frontend/public/**/*.ogg",
        "frontend/public/**/*.aac",
        "frontend/public/**/*.mp4",
        "frontend/public/**/*.webm",
        "frontend/public/**/*.zip",
        "output/**/*.mp4",
        "output/**/*.webm",
        "output/**/*.zip",
    ]
    completed = run_command(["git", "ls-files", *patterns])
    return [line for line in completed.stdout.splitlines() if line.strip()]


def file_contains(pattern: str, roots: tuple[Path, ...]) -> list[str]:
    matches: list[str] = []
    regex = re.compile(pattern, flags=re.IGNORECASE)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx", ".html", ".json", ".md"}:
                continue
            if "node_modules" in path.parts or "build" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if regex.search(text):
                matches.append(relative(path))
    return sorted(set(matches))


def walk_payload(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    entries: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            entries.append((path, value))
            entries.extend(walk_payload(value, path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            path = f"{prefix}[{index}]"
            entries.append((path, value))
            entries.extend(walk_payload(value, path))
    return entries


def truthy_audio_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return bool(stripped) and stripped.lower() not in {"false", "none", "null", "internal_only"}
    if isinstance(value, (list, dict)):
        return bool(value)
    return False


def validate_non_dracula_audio_payload(slug: str, payload: Any, source: str, issues: list[str]) -> None:
    if slug == BOOK_SLUG:
        return
    for key_path, value in walk_payload(payload):
        key_name = key_path.split(".")[-1]
        if key_name in NON_DRACULA_AUDIO_FLAG_FIELDS and value is True:
            issues.append(f"Non-Dracula reader has public audio flag {source}:{key_path}=true: {slug}")
        if key_name in NON_DRACULA_AUDIO_REFERENCE_KEYS and truthy_audio_value(value):
            issues.append(f"Non-Dracula reader has audio reference {source}:{key_path}: {slug}")


def manifest_public_urls() -> list[str]:
    matches: list[str] = []
    if not OUTPUT_ROOT.exists():
        return matches
    url_pattern = re.compile(r"https?://|(?<!internal)/audio/|audiobook_url|audio_url", flags=re.IGNORECASE)
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if url_pattern.search(text):
            matches.append(relative(path))
    return sorted(matches)


def changed_paths() -> list[str]:
    completed = run_command(["git", "diff", "--name-only", "origin/main...HEAD"])
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def validate_payment_unchanged(issues: list[str]) -> None:
    changed = changed_paths()
    suspicious = [
        path
        for path in changed
        if any(token in path.lower() for token in PAYMENT_OR_PRICING_PATTERNS)
        and not path.startswith("internal/audiobook_lab/dracula/en/full-book/")
    ]
    if suspicious:
        issues.append("Payment/pricing-related files changed: " + ", ".join(suspicious))


def validate_release_gate(issues: list[str]) -> None:
    completed = run_command(["python3", "scripts/audiobook_accessibility_release_gate.py"])
    output = completed.stdout
    if completed.returncode != 0:
        issues.append("Audiobook release gate command failed")
        return
    if PUBLIC_AUDIO_RELEASE_BLOCKED not in output or "PASS_EXPECTED_BLOCKED" not in output:
        issues.append("Audiobook release gate is not blocked/expected-blocked")


def validate_reader_library_audio_safety(issues: list[str]) -> None:
    controlled_root = ROOT / "data" / "controlled_publications"
    live_slugs: list[str] = []
    for path in controlled_root.glob("*/public_book.json"):
        payload = load_json(path, issues)
        status = str(payload.get("publicationStatus") or payload.get("publication_status") or "").lower()
        if payload.get("is_published") is True or status in {"live", "published", "public", "published_core_reading_only"}:
            slug = path.parent.name
            live_slugs.append(slug)
            if slug not in LIVE_READER_ONLY_ALLOWLIST:
                issues.append(f"Unexpected live reader slug outside audiobook safety allowlist: {slug}")
            validate_non_dracula_audio_payload(slug, payload, relative(path), issues)
    if "dracula" not in live_slugs:
        issues.append("Dracula live controlled publication was not detected")
    for path in sorted((ROOT / "content" / "books").glob("*/book.json")):
        payload = load_json(path, issues)
        slug = str(payload.get("slug") or path.parent.name)
        if slug in LIVE_READER_ONLY_ALLOWLIST:
            validate_non_dracula_audio_payload(slug, payload, relative(path), issues)


def validate_preflight_files(issues: list[str]) -> dict[str, Any]:
    for relative_path in REQUIRED_PREFLIGHT_FILES:
        path = OUTPUT_ROOT / relative_path
        if not path.exists():
            issues.append(f"Missing required preflight file: {relative(path)}")

    chapter_manifest = load_json(OUTPUT_ROOT / "chapter_manifest.json", issues)
    chunk_manifest = load_json(OUTPUT_ROOT / "chunk_manifest.json", issues)
    character_report = load_json(OUTPUT_ROOT / "character_count_report.json", issues)
    cost_report = load_json(OUTPUT_ROOT / "cost_preflight_report.json", issues)
    generation_report = load_json(OUTPUT_ROOT / "generation_preflight_report.json", issues)
    sync_manifest = load_json(OUTPUT_ROOT / "sync_manifest.json", issues)
    sample_manifest = load_json(OUTPUT_ROOT / "sample_pack" / "sample_manifest.json", issues)

    chapters = chapter_manifest.get("chapters", []) if isinstance(chapter_manifest, dict) else []
    if chapter_manifest.get("chapterCount") != EXPECTED_CHAPTER_COUNT or len(chapters) != EXPECTED_CHAPTER_COUNT:
        issues.append("Chapter manifest must contain exactly 27 chapters")
    expected_chapter_numbers = list(range(1, EXPECTED_CHAPTER_COUNT + 1))
    actual_chapter_numbers = [item.get("chapterNumber") for item in chapters if isinstance(item, dict)]
    if actual_chapter_numbers != expected_chapter_numbers:
        issues.append("Chapter numbers are not exactly 1..27")

    chunks = chunk_manifest.get("chunks", []) if isinstance(chunk_manifest, dict) else []
    if chunk_manifest.get("chunkCount") != len(chunks) or not chunks:
        issues.append("Chunk manifest chunkCount does not match chunks list")
    seen_by_chapter: dict[int, int] = {}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            issues.append("Chunk manifest contains a non-object chunk")
            continue
        chapter_number = int(chunk.get("chapterNumber") or 0)
        expected_index = seen_by_chapter.get(chapter_number, 0) + 1
        expected_chunk_id = f"dracula-chapter-{chapter_number:02d}-chunk-{expected_index:03d}"
        if chunk.get("chunkId") != expected_chunk_id:
            issues.append(f"Unexpected deterministic chunk id: {chunk.get('chunkId')} expected {expected_chunk_id}")
        seen_by_chapter[chapter_number] = expected_index
        if not chunk.get("sourceSha256") or not chunk.get("normalizedSha256"):
            issues.append(f"Missing source or normalized checksum for {chunk.get('chunkId')}")
        if chunk.get("publicAudioAllowed") is not False:
            issues.append(f"Chunk {chunk.get('chunkId')} must keep publicAudioAllowed=false")

    if character_report.get("totalCharacters") != sum(item.get("sourceCharacterCount", 0) for item in chapters):
        issues.append("Character report totalCharacters does not match chapter source counts")
    if character_report.get("totalNormalizedCharacters") != sum(item.get("normalizedCharacterCount", 0) for item in chapters):
        issues.append("Character report totalNormalizedCharacters does not match chapter normalized counts")

    total_characters = int(character_report.get("totalCharacters") or 0)
    expected_flash = round(total_characters / 1000 * 0.05 + 1e-9, 2)
    expected_premium = round(total_characters / 1000 * 0.10 + 1e-9, 2)
    try:
        actual_flash = float(cost_report.get("flash", {}).get("estimatedCostUsd"))
        actual_premium = float(cost_report.get("premium", {}).get("estimatedCostUsd"))
    except (TypeError, ValueError):
        actual_flash = actual_premium = -1.0
    if actual_flash != expected_flash:
        issues.append(f"Flash cost estimate mismatch: {actual_flash} != {expected_flash}")
    if actual_premium != expected_premium:
        issues.append(f"Premium cost estimate mismatch: {actual_premium} != {expected_premium}")

    if generation_report.get("paidApiCalled") is not False:
        issues.append("Preflight generation report must show paidApiCalled=false")
    if generation_report.get("publicAudioRelease") != PUBLIC_AUDIO_RELEASE_BLOCKED:
        issues.append("Generation preflight report must keep public audio blocked")
    if not generation_report.get("approval", {}).get("blockers") and generation_report.get("status") == "BLOCKED_PENDING_OWNER_APPROVAL":
        issues.append("Blocked preflight status must list approval blockers")

    if sync_manifest.get("syncPrecision") != "chunk":
        issues.append("Top-level sync manifest must use syncPrecision=chunk")
    chapter_sync = sync_manifest.get("chapters", [])
    if len(chapter_sync) != EXPECTED_CHAPTER_COUNT:
        issues.append("Top-level sync manifest must include 27 chapter sync files")
    for index in expected_chapter_numbers:
        path = OUTPUT_ROOT / "chapter_sync" / f"chapter-{index:02d}.sync.json"
        payload = load_json(path, issues)
        if payload and payload.get("syncPrecision") != "chunk":
            issues.append(f"{relative(path)} must use syncPrecision=chunk")

    if len(sample_manifest.get("samples", [])) != 3:
        issues.append("Sample manifest must contain exactly three Dracula samples")
    if sample_manifest.get("publicAudioAllowed") is not False:
        issues.append("Sample manifest must keep publicAudioAllowed=false")

    return {
        "chapter_count": len(chapters),
        "chunk_count": len(chunks),
        "total_characters": total_characters,
        "flash_estimate_usd": cost_report.get("flash", {}).get("estimatedCostUsd"),
    }


def validate_public_exposure(issues: list[str]) -> None:
    public_binaries = scan_public_binaries()
    if public_binaries:
        issues.append("Public audio/video/archive files found: " + ", ".join(public_binaries))
    tracked_binaries = tracked_public_binaries()
    if tracked_binaries:
        issues.append("Tracked public binary files found: " + ", ".join(tracked_binaries))
    urls = manifest_public_urls()
    if urls:
        issues.append("Public URL-like values found in internal audiobook manifests: " + ", ".join(urls))
    listen_now = file_contains(r"\bListen Now\b", (ROOT / "frontend" / "src", ROOT / "frontend" / "public"))
    if listen_now:
        issues.append("Listen Now appears in public UI files: " + ", ".join(listen_now))
    audio_object = file_contains(r"AudioObject", (ROOT / "frontend" / "src", ROOT / "frontend" / "public"))
    if audio_object:
        issues.append("AudioObject metadata appears: " + ", ".join(audio_object))


def validate_generated(issues: list[str]) -> dict[str, Any]:
    for relative_path in REQUIRED_GENERATED_FILES:
        path = OUTPUT_ROOT / relative_path
        if not path.exists():
            issues.append(f"Missing required generated-mode file: {relative(path)}")
    chapter_audio_manifest = load_json(OUTPUT_ROOT / "full_chapter_audio_manifest.json", issues)
    full_manifest = load_json(OUTPUT_ROOT / "full_audiobook_manifest.json", issues)
    checksums = load_json(OUTPUT_ROOT / "audio_checksums.json", issues)

    chapter_files = []
    for index in range(1, EXPECTED_CHAPTER_COUNT + 1):
        path = OUTPUT_ROOT / "chapters" / f"chapter-{index:02d}.mp3"
        chapter_files.append(path)
        if not path.exists():
            issues.append(f"Missing generated chapter audio: {relative(path)}")
        elif path.stat().st_size <= 0:
            issues.append(f"Generated chapter audio is zero-byte: {relative(path)}")
        else:
            try:
                path.resolve().relative_to(OUTPUT_ROOT.resolve())
            except ValueError:
                issues.append(f"Generated chapter audio is not internal: {relative(path)}")

    if chapter_audio_manifest.get("chapterCount") != EXPECTED_CHAPTER_COUNT:
        issues.append("Full chapter audio manifest must contain 27 chapters")
    if full_manifest.get("chapterCount") != EXPECTED_CHAPTER_COUNT:
        issues.append("Full audiobook manifest must contain 27 chapters")
    if full_manifest.get("publicUrls") not in ([], None):
        issues.append("Full audiobook manifest must not contain public URLs")
    if full_manifest.get("publicAudioAllowed") is not False:
        issues.append("Full audiobook manifest must keep publicAudioAllowed=false")
    if full_manifest.get("internalOnlyStatus") != "INTERNAL_REVIEW_ONLY":
        issues.append("Full audiobook manifest must be internal review only")
    for item in checksums.get("chunks", []):
        if not item.get("audioSha256"):
            issues.append(f"Missing audio checksum for generated chunk {item.get('chunkId')}")
        if item.get("public") is not False:
            issues.append(f"Generated chunk checksum entry must be public=false: {item.get('chunkId')}")
    return {
        "generated_chapter_files": sum(1 for path in chapter_files if path.exists() and path.stat().st_size > 0),
        "total_duration_seconds": full_manifest.get("totalDurationSeconds"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "generated"), default="preflight")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    issues: list[str] = []
    summary = validate_preflight_files(issues)
    validate_public_exposure(issues)
    validate_release_gate(issues)
    validate_reader_library_audio_safety(issues)
    validate_payment_unchanged(issues)
    if args.mode == "generated":
        summary.update(validate_generated(issues))
    payload = {
        "status": "PASS" if not issues else "FAIL",
        "mode": args.mode,
        "summary": summary,
        "issues": issues,
        "publicAudioRelease": PUBLIC_AUDIO_RELEASE_BLOCKED,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
