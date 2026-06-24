from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.ingest_bengali_audiobook_store_candidates import (
    RELEASE_HOLD,
    ingest_bengali_store_candidates,
    scan_bundles,
)


ROOT = Path.cwd()
OUTPUT_DIR = ROOT / "internal" / "audiobook_lab" / "pytest_bengali_store_candidates"


@pytest.fixture(autouse=True)
def cleanup_output_dir():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    yield
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)


def write_bundle(
    input_root: Path,
    relative_dir: str,
    *,
    missing_sidecars: bool = False,
    malformed_vtt: bool = False,
    timestamp_order_error: bool = False,
    public_url: bool = False,
) -> Path:
    bundle_dir = input_root / relative_dir
    bundle_dir.mkdir(parents=True, exist_ok=True)
    slug = bundle_dir.name
    (bundle_dir / f"{slug}.mp3").write_bytes(b"fake mp3 bytes for inventory only")
    (bundle_dir / f"{slug}_meta.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "title": "\u09af\u09c1\u0997\u09b2\u09be\u0999\u09cd\u0997\u09c1\u09b0\u09c0\u09af\u09bc",
                "author": "\u09ac\u0999\u09cd\u0995\u09bf\u09ae\u099a\u09a8\u09cd\u09a6\u09cd\u09b0",
                "language": "ben",
                "voice": "bn-IN-TanishaaNeural",
                "duration_ms": 2500,
                "chapters": 1,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    if not missing_sidecars:
        (bundle_dir / f"{slug}_chapters.json").write_text(
            json.dumps([{"title": "Chapter 1", "start_ms": 0}]) + "\n",
            encoding="utf-8",
        )
        timestamps = [
            {"word": "\u0985\u09a7\u09cd\u09af\u09be\u09af\u09bc", "start_ms": 0, "end_ms": 500},
            {"word": "\u09aa\u09cd\u09b0\u09a5\u09ae", "start_ms": 400 if timestamp_order_error else 500, "end_ms": 300 if timestamp_order_error else 1000},
        ]
        (bundle_dir / f"{slug}_timestamps.json").write_text(
            json.dumps(timestamps, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        cue_text = "https://example.com/audio" if public_url else "\u0985\u09a7\u09cd\u09af\u09be\u09af\u09bc"
        header = "" if malformed_vtt else "WEBVTT\n\n"
        (bundle_dir / f"{slug}_highlight.vtt").write_text(
            f"{header}1\n00:00:00.000 --> 00:00:00.500\n{cue_text}\n",
            encoding="utf-8",
        )
    return bundle_dir


def test_scanner_detects_nested_bengali_bundle_folders(tmp_path: Path):
    source = tmp_path / "bundles" / "ben"
    write_bundle(source, "collection/nested-book")
    write_bundle(source, "plain-book")

    bundles = scan_bundles(source)

    assert [bundle.candidate_slug for bundle in bundles] == ["collection-nested-book", "plain-book"]


def test_review_ingest_inventories_audio_sidecars_and_missing_files(tmp_path: Path):
    source = tmp_path / "bundles" / "ben"
    original = write_bundle(source, "collection/nested-book", timestamp_order_error=True)
    missing = write_bundle(source, "missing-sidecars", missing_sidecars=True)
    original_hash = (original / "nested-book.mp3").read_bytes()
    missing_hash = (missing / "missing-sidecars.mp3").read_bytes()

    summary = ingest_bengali_store_candidates(input_dir=source, output_dir=OUTPUT_DIR, mode="review")

    assert summary["candidate_count"] == 2
    assert summary["release_status"] == RELEASE_HOLD
    assert summary["frontend_public_audio_files"] == []
    assert summary["frontend_build_audio_files"] == []

    candidate_dir = OUTPUT_DIR / "collection-nested-book"
    assert (candidate_dir / "source_inventory.json").exists()
    assert (candidate_dir / "audio_file_manifest.json").exists()
    assert (candidate_dir / "sidecar_integrity_report.json").exists()
    assert (candidate_dir / "bengali_listening_qa_scorecard.md").exists()
    assert (candidate_dir / "accessibility_listening_qa_scorecard.md").exists()
    assert (candidate_dir / "store_listing_draft.md").exists()
    assert not (candidate_dir / "audio_internal").exists()

    inventory = json.loads((candidate_dir / "source_inventory.json").read_text(encoding="utf-8"))
    assert inventory["audio_files"]
    assert inventory["sidecar_files"]
    assert inventory["storage_status"] == "LOCAL_SOURCE_ONLY"
    assert inventory["public_serving_status"] == "BLOCKED"
    assert inventory["upload_status"] == "NOT_UPLOADED"

    missing_inventory = json.loads((OUTPUT_DIR / "missing-sidecars" / "source_inventory.json").read_text())
    assert "highlight_vtt" in missing_inventory["missing_required_files"]
    assert "timestamps_json" in missing_inventory["missing_required_files"]
    assert "chapters_json" in missing_inventory["missing_required_files"]

    sidecars = json.loads((candidate_dir / "sidecar_integrity_report.json").read_text(encoding="utf-8"))
    assert sidecars["sidecar_integrity_status"] == "REVIEW_REQUIRED"
    assert any("timestamp order error" in issue for report in sidecars["files"] for issue in report["issues"])

    release_gate = json.loads((candidate_dir / "release_gate_report.json").read_text(encoding="utf-8"))
    assert release_gate["release_status"] == RELEASE_HOLD
    assert release_gate["human_qa_required"] is True
    assert release_gate["gates"]["bengali_human_listening_qa_9_5"] is False

    assert (original / "nested-book.mp3").read_bytes() == original_hash
    assert (missing / "missing-sidecars.mp3").read_bytes() == missing_hash


def test_malformed_vtt_and_public_urls_are_reported(tmp_path: Path):
    source = tmp_path / "bundles" / "ben"
    write_bundle(source, "bad-vtt", malformed_vtt=True, public_url=True)

    ingest_bengali_store_candidates(input_dir=source, output_dir=OUTPUT_DIR, mode="review")

    sidecars = json.loads((OUTPUT_DIR / "bad-vtt" / "sidecar_integrity_report.json").read_text(encoding="utf-8"))
    issues = [issue for report in sidecars["files"] for issue in report["issues"]]
    assert "missing WEBVTT header" in issues
    assert any("public URL" in issue or "public path" in issue for issue in issues)


def test_copy_internal_stays_internal_and_audio_binaries_are_ignored(tmp_path: Path):
    source = tmp_path / "bundles" / "ben"
    write_bundle(source, "copy-book")

    ingest_bengali_store_candidates(input_dir=source, output_dir=OUTPUT_DIR, mode="review", copy_internal=True)

    copied_audio = OUTPUT_DIR / "copy-book" / "audio_internal" / "copy-book.mp3"
    assert copied_audio.exists()
    assert str(copied_audio).startswith(str(ROOT / "internal" / "audiobook_lab"))
    assert not str(copied_audio).startswith(str(ROOT / "frontend" / "public"))
    assert not str(copied_audio).startswith(str(ROOT / "frontend" / "build"))
    check_ignore = subprocess.run(["git", "check-ignore", str(copied_audio)], check=False, capture_output=True, text=True)
    assert check_ignore.returncode == 0


def test_no_public_cta_or_metadata_claims_are_introduced(tmp_path: Path):
    source = tmp_path / "bundles" / "ben"
    write_bundle(source, "safe-book")

    ingest_bengali_store_candidates(input_dir=source, output_dir=OUTPUT_DIR, mode="review")

    generated_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (OUTPUT_DIR / "safe-book").glob("*")
        if path.is_file() and path.suffix in {".md", ".json"}
    )
    release_gate = json.loads((OUTPUT_DIR / "safe-book" / "release_gate_report.json").read_text(encoding="utf-8"))
    assert "Listen Now" not in generated_text
    assert "AudioObject" not in generated_text
    assert release_gate["release_status"] == RELEASE_HOLD
    assert release_gate["gates"]["bengali_human_listening_qa_9_5"] is False
