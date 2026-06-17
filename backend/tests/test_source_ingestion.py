from __future__ import annotations

import json
from pathlib import Path

from backend.source_ingestion import (
    SourceIngestionInput,
    clean_source_text,
    detect_chapters,
    detect_language,
    hash_source,
    ingest_source,
)
from scripts.source_ingestion import write_reports


def approved_book(**rights_overrides):
    rights_metadata = {
        "work_title": "Pride and Prejudice",
        "work_slug": "pride-and-prejudice",
        "author_name": "Jane Austen",
        "author_death_year": 1817,
        "original_publication_year": 1813,
        "country_of_origin": "United Kingdom",
        "source_url": "https://www.gutenberg.org/ebooks/1342",
        "source_name": "Project Gutenberg",
        "source_license": "Public domain",
        "translator_name": "",
        "translator_death_year": "",
        "illustrator_name": "",
        "illustrator_death_year": "",
        "editor_name": "",
        "edition_publication_year": 1813,
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "publication_region": "global",
        "verified_at": "2026-06-18T00:00:00+00:00",
    }
    rights_metadata.update(rights_overrides)
    return {
        "title": "Pride and Prejudice",
        "slug": "pride-and-prejudice",
        "author": "Jane Austen",
        "rights_metadata": rights_metadata,
    }


def raw_source_text():
    return """*** START OF THE PROJECT GUTENBERG EBOOK PRIDE AND PREJUDICE ***

Project Gutenberg

Chapter 1

It is a truth universally acknowledged.

Page 2

Chapter 2

Mr. Bennet was among the earliest of those who waited on Mr. Bingley.

*** END OF THE PROJECT GUTENBERG EBOOK PRIDE AND PREJUDICE ***
"""


def test_ingestion_accepts_rights_approved_source_and_keeps_raw_and_cleaned_text_separate():
    record = ingest_source(SourceIngestionInput(book=approved_book(), raw_text=raw_source_text()))

    assert record.ingestion_status == "READY"
    assert record.rights_status == "RIGHTS_APPROVED"
    assert record.connector == "project-gutenberg"
    assert record.raw_text != record.cleaned_text
    assert "Project Gutenberg" in record.raw_text
    assert "Project Gutenberg" not in record.cleaned_text
    assert len(record.chapter_segments) == 2
    assert record.downstream_artifacts_regenerated is True


def test_ingestion_accepts_pending_safe_rights_for_dry_run_review():
    book = approved_book(verification_status="pending", verified_at="")

    record = ingest_source(SourceIngestionInput(book=book, raw_text=raw_source_text()))

    assert record.ingestion_status == "READY"
    assert record.rights_status == "RIGHTS_PENDING_SAFE"


def test_missing_license_blocks_ingestion():
    book = approved_book(source_license="")

    record = ingest_source(SourceIngestionInput(book=book, raw_text=raw_source_text()))

    assert record.ingestion_status == "BLOCKED_RIGHTS"
    assert any("source_license is required" in item for item in record.ingestion_log)
    assert record.cleaned_text == ""


def test_missing_source_url_blocks_ingestion():
    book = approved_book(source_url="")

    record = ingest_source(SourceIngestionInput(book=book, raw_text=raw_source_text()))

    assert record.ingestion_status == "BLOCKED_RIGHTS"
    assert any("source_url is required" in item for item in record.ingestion_log)


def test_tier_c_rights_block_ingestion():
    book = approved_book(rights_tier="C", blocked_reason="unclear source")

    record = ingest_source(SourceIngestionInput(book=book, raw_text=raw_source_text()))

    assert record.ingestion_status == "BLOCKED_RIGHTS"
    assert record.rights_status == "RIGHTS_BLOCKED"


def test_source_hash_prevents_duplicate_downstream_regeneration():
    text = raw_source_text()
    existing_hash = hash_source(text)

    record = ingest_source(
        SourceIngestionInput(
            book=approved_book(),
            raw_text=text,
            previous_source_hashes={existing_hash},
        )
    )

    assert record.ingestion_status == "UNCHANGED"
    assert record.source_hash == existing_hash
    assert record.downstream_artifacts_regenerated is False
    assert any("downstream regeneration skipped" in item for item in record.ingestion_log)


def test_manual_text_connector_and_cleaning_work_without_network():
    book = approved_book(source_url="https://example.test/source.txt", source_name="Manual import")
    record = ingest_source(
        SourceIngestionInput(
            book=book,
            raw_text="Chapter 1\n\n  A line with    extra whitespace.  \n\nChapter 2\n\nAnother line.",
            connector="manual-text",
        )
    )

    assert record.connector == "manual-text"
    assert "extra whitespace" in record.cleaned_text
    assert "    " not in record.cleaned_text
    assert len(record.chapter_segments) == 2


def test_wikisource_connector_is_detected_from_url():
    book = approved_book(
        rights_tier="B",
        publication_region="india",
        source_url="https://en.wikisource.org/wiki/Sultana%27s_Dream",
        source_name="Wikisource",
        source_license="Public domain transcription from Wikisource",
    )

    record = ingest_source(SourceIngestionInput(book=book, raw_text="Chapter 1\n\nA dream begins."))

    assert record.connector == "wikisource"
    assert record.ingestion_status == "READY"


def test_scanned_pdf_placeholder_does_not_attempt_ocr():
    book = approved_book(source_url="https://example.test/scan.pdf", source_name="Manual scan")

    record = ingest_source(SourceIngestionInput(book=book, connector="auto"))

    assert record.connector == "scanned-pdf-placeholder"
    assert record.ingestion_status == "PENDING_OCR"
    assert record.downstream_artifacts_regenerated is False


def test_language_detection_supports_english_bengali_and_unknown():
    assert detect_language("A clean English source text.") == "en"
    assert detect_language("\u0986\u09ae\u09be\u09b0 \u09b8\u09cb\u09a8\u09be\u09b0 \u09ac\u09be\u0982\u09b2\u09be") == "ben"
    assert detect_language("12345") == "unknown"


def test_chapter_detection_falls_back_to_full_text():
    segments = detect_chapters("No chapter heading here, only one body.")

    assert len(segments) == 1
    assert segments[0].title == "Full Text"


def test_clean_source_text_strips_gutenberg_boundaries():
    cleaned = clean_source_text(raw_source_text(), connector="project-gutenberg")

    assert "START OF THE PROJECT GUTENBERG" not in cleaned
    assert "END OF THE PROJECT GUTENBERG" not in cleaned
    assert "It is a truth universally acknowledged." in cleaned


def test_cli_report_writer_outputs_json_csv_and_markdown(tmp_path: Path):
    record = ingest_source(SourceIngestionInput(book=approved_book(), raw_text=raw_source_text()))

    json_path, csv_path, md_path = write_reports(record, tmp_path)

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["raw_text"]
    assert payload["cleaned_text"]
    assert "ingestion_status" in csv_path.read_text(encoding="utf-8")
    assert "Source Ingestion Dry-Run Report" in md_path.read_text(encoding="utf-8")
