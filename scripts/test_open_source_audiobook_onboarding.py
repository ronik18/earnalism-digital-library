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
        controlled_publications_root=tmp_path / "controlled_publications",
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


def _write_controlled_packet(
    tmp_path: Path,
    *,
    slug: str,
    title: str,
    chapter_title: str,
    chapter_content: str,
    audio_approved: bool = False,
) -> Path:
    packet = tmp_path / "controlled_publications" / slug
    chapters = packet / "chapters"
    chapters.mkdir(parents=True)
    release_status = "PUBLIC_AUDIO_RELEASE_APPROVED" if audio_approved else "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
    qa_status = "QA_PASSED" if audio_approved else ""
    (packet / "approval_evidence.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "approved_to_publish": True,
                "audiobook_enabled": audio_approved,
                "audio_public_release": release_status,
                "audio_qa_status": qa_status,
                "release_blockers": [],
            }
        ),
        encoding="utf-8",
    )
    (packet / "public_book.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "title": title,
                "author": "Earnalism",
                "is_published": True,
                "audiobook_enabled": audio_approved,
            }
        ),
        encoding="utf-8",
    )
    (packet / "reader_manifest.json").write_text(
        json.dumps(
            {
                "slug": slug,
                "audiobook_enabled": audio_approved,
                "chapter_count": 1,
            }
        ),
        encoding="utf-8",
    )
    (chapters / "chapter-001.json").write_text(
        json.dumps(
            {
                "id": "c1",
                "bookSlug": slug,
                "order": 1,
                "title": chapter_title,
                "content": chapter_content,
            }
        ),
        encoding="utf-8",
    )
    return packet


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
    _write_controlled_packet(
        tmp_path,
        slug="tiny-sample",
        title="Tiny Sample",
        chapter_title="Chapter One",
        chapter_content="<p>Hello, reader. This is a tiny local-only sample.</p>",
    )

    result = audio.generate_book(book, _base_args(tmp_path))

    assert result.status == "DRY_RUN"
    assert result.language == "en"
    assert result.expected_units > 0
    assert result.source_reconciliation["status"] == "MATCH"
    assert (tmp_path / "reports" / "texts" / "tiny-sample.txt").exists()


def test_hidden_audio_with_stale_mapped_assets_is_not_ready(tmp_path):
    book = {
        "slug": "hidden-stale",
        "title": "Hidden Stale",
        "author": "Earnalism",
        "is_published": True,
        "audiobook_assets": {
            "mp3": "https://storage.invalid/hidden-stale.mp3",
            "timestamps": "https://storage.invalid/hidden-stale_timestamps.json",
        },
        "chapters": [
            {
                "id": "c1",
                "order": 1,
                "title": "Chapter One",
                "content": "<p>Canonical hidden narration text.</p>",
            }
        ],
    }
    _write_controlled_packet(
        tmp_path,
        slug="hidden-stale",
        title="Hidden Stale",
        chapter_title="Chapter One",
        chapter_content="<p>Canonical hidden narration text.</p>",
        audio_approved=False,
    )
    args = _base_args(tmp_path)

    result = audio.generate_book(book, args)

    assert audio.has_reader_ready_audio_assets(book) is True
    assert audio.has_controlled_release_ready_audio(book, args) is False
    assert result.status == "DRY_RUN"
    assert result.asset_urls == {}
    assert result.controlled_release_truth["approved"] is False
    assert "mapped audiobook assets ignored" in result.detail


def test_controlled_approved_audio_with_mapped_assets_is_ready(tmp_path):
    book = {
        "slug": "approved-audio",
        "title": "Approved Audio",
        "author": "Earnalism",
        "is_published": True,
        "audiobook_assets": {
            "mp3": "https://storage.invalid/approved-audio.mp3",
            "timestamps": "https://storage.invalid/approved-audio_timestamps.json",
        },
        "chapters": [],
    }
    _write_controlled_packet(
        tmp_path,
        slug="approved-audio",
        title="Approved Audio",
        chapter_title="Chapter One",
        chapter_content="<p>Approved narration text.</p>",
        audio_approved=True,
    )
    args = _base_args(tmp_path)

    result = audio.generate_book(book, args)

    assert audio.has_controlled_release_ready_audio(book, args) is True
    assert result.status == "READY"
    assert result.controlled_release_truth["approved"] is True


def test_dry_run_blocks_and_hashes_divergent_live_and_controlled_manuscripts(tmp_path):
    book = {
        "slug": "divergent-source",
        "title": "Divergent Source",
        "author": "Earnalism",
        "is_published": True,
        "chapters": [
            {
                "id": "c1",
                "order": 1,
                "title": "Chapter One",
                "content": "<p>Live manuscript text.</p>",
            }
        ],
    }
    _write_controlled_packet(
        tmp_path,
        slug="divergent-source",
        title="Divergent Source",
        chapter_title="Chapter One",
        chapter_content="<p>Controlled manuscript text.</p>",
    )

    result = audio.generate_book(book, _base_args(tmp_path))

    assert result.status == "BLOCKED"
    assert result.source_reconciliation["status"] == "SOURCE_MANUSCRIPT_MISMATCH"
    assert result.source_reconciliation["byte_equal"] is False
    assert result.source_reconciliation["live_sha256"]
    assert result.source_reconciliation["controlled_sha256"]
    assert (
        result.source_reconciliation["live_sha256"]
        != result.source_reconciliation["controlled_sha256"]
    )
    assert "live_sha256=" in result.detail
    assert "controlled_sha256=" in result.detail
    assert not (tmp_path / "reports" / "texts" / "divergent-source.txt").exists()
    assert (tmp_path / "reports" / "texts" / "divergent-source.live.txt").exists()
    assert (
        tmp_path / "reports" / "texts" / "divergent-source.controlled.txt"
    ).exists()
