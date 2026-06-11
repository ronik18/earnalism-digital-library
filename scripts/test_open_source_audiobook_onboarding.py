import argparse
import json
from pathlib import Path

import pytest

import open_source_audiobook_onboarding as audio


def _base_args(tmp_path: Path, **overrides):
    args = argparse.Namespace(
        output_dir=tmp_path / "out",
        public_audio_dir=tmp_path / "public",
        report_dir=tmp_path / "reports",
        manifest_languages={},
        skip_live_audio_assets=True,
        lang=None,
        max_chars=0,
        validate_only=False,
        dry_run=True,
        regenerate=False,
        copy_to_public=False,
        upload_to_cloudinary=False,
        english_provider="piper",
        bengali_provider="mms-tts",
        piper_binary="piper",
        piper_model="model.onnx",
        piper_config="model.onnx.json",
        piper_speaker="",
        piper_length_scale=1.08,
        english_chunk_chars=1100,
        bengali_chunk_chars=420,
        alignment_min_ratio=0.8,
        skip_alignment=True,
    )
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def test_target_manifest_parsing_accepts_books_object(tmp_path):
    manifest = tmp_path / "targets.json"
    manifest.write_text(
        json.dumps(
            {
                "books": [
                    {"slug": "Acres Of Diamonds", "language": "en"},
                    {"slug": "bn-070", "language": "bn"},
                ]
            }
        ),
        encoding="utf-8",
    )

    slugs, languages = audio.load_target_manifest(manifest)

    assert slugs == {"acres-of-diamonds", "bn-070"}
    assert languages == {"acres-of-diamonds": "en", "bn-070": "ben"}


def test_language_routing_prefers_manifest_language():
    assert audio.infer_language("plain English title", "bn") == "ben"
    assert audio.infer_language("বাংলা লেখা", "en") == "en"
    assert audio.infer_language("বাংলা লেখা") == "ben"


def test_local_only_rejects_paid_provider_selection():
    args = argparse.Namespace(local_only=True, english_provider="google", bengali_provider="mms-tts")

    with pytest.raises(RuntimeError, match="local-only"):
        audio.enforce_local_only(args)


def test_bundle_paths_match_reader_schema(tmp_path):
    paths = audio.bundle_paths(tmp_path, "en", "the-secret-garden")

    assert paths["mp3"] == tmp_path / "en" / "the-secret-garden.mp3"
    assert paths["timestamps"] == tmp_path / "en" / "the-secret-garden_timestamps.json"
    assert paths["vtt"] == tmp_path / "en" / "the-secret-garden_highlight.vtt"
    assert paths["chapters"] == tmp_path / "en" / "the-secret-garden_chapters.json"
    assert paths["meta"] == tmp_path / "en" / "the-secret-garden_meta.json"


def test_validate_bundle_rejects_non_monotonic_timestamps(tmp_path, monkeypatch):
    paths = audio.bundle_paths(tmp_path, "en", "sample")
    paths["mp3"].parent.mkdir(parents=True)
    paths["mp3"].write_bytes(b"fake mp3")
    paths["timestamps"].write_text(
        json.dumps(
            [
                {"word": "one", "start_ms": 0, "end_ms": 100},
                {"word": "two", "start_ms": 90, "end_ms": 200},
            ]
        ),
        encoding="utf-8",
    )
    paths["vtt"].write_text("WEBVTT\n", encoding="utf-8")
    paths["chapters"].write_text("[]", encoding="utf-8")
    paths["meta"].write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audio, "duration_ms", lambda _path: 250)

    result = audio.validate_bundle(tmp_path, "en", "sample", expected_units=2)

    assert result.ok is False
    assert "overlap" in result.detail


def test_generate_book_dry_run_uses_canonical_chapter_text(tmp_path):
    book = {
        "slug": "tiny-sample",
        "title": "Tiny Sample",
        "author": "Earnalism",
        "is_published": True,
        "chapters": [
            {
                "id": "c1",
                "order": 1,
                "title": "Chapter One",
                "content": "<p>Hello, reader. This is a tiny local-only sample.</p>",
            }
        ],
    }

    result = audio.generate_book(book, _base_args(tmp_path))

    assert result.status == "DRY_RUN"
    assert result.language == "en"
    assert result.expected_units > 0
    assert (tmp_path / "reports" / "texts" / "tiny-sample.txt").exists()
