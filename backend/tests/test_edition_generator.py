from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.edition_generator import (
    EDITION_TEMPLATES,
    MODEL_VERSION,
    PROMPT_VERSION,
    SECTION_ORDER,
    EditionGenerationInput,
    edition_report_csv,
    edition_report_json,
    edition_report_markdown,
    generate_edition,
    generation_cache_key,
)
from backend.source_ingestion import hash_source
from scripts.edition_generator import SAMPLE_BOOK, SAMPLE_TEXT, load_payload, write_reports


def sample_payload(**overrides):
    text = overrides.pop("cleaned_text", SAMPLE_TEXT)
    source_hash = hash_source(text)
    payload = {
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "language": "en",
        "cleaned_text": text,
        "source_hash": source_hash,
        "content_hash": source_hash,
        "provenance_hash": "sample-provenance-hash",
        "source_name": "Project Gutenberg",
        "source_url": "https://www.gutenberg.org/ebooks/11",
        "source_license": "Public domain",
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "action_status": "READY_FOR_GENERATION",
        "ingestion_status": "CLEANED",
    }
    payload.update(overrides)
    return payload


def generation_input(**overrides):
    payload = sample_payload(**overrides)
    return EditionGenerationInput(**payload)


def test_all_required_edition_templates_exist_with_prompts():
    assert SECTION_ORDER == [
        "clean_reading_edition",
        "chapter_summary",
        "character_map",
        "historical_context",
        "glossary",
        "themes",
        "quiz",
        "seven_day_reading_plan",
        "teacher_parent_notes",
        "why_this_book_matters_today",
        "audiobook_ready_script",
        "seo_copy",
        "landing_page_copy",
        "social_excerpts",
    ]
    assert set(EDITION_TEMPLATES) == set(SECTION_ORDER)
    assert all(EDITION_TEMPLATES[section_id].prompt for section_id in SECTION_ORDER)


def test_pipeline_generates_fixture_sections_and_state_fields():
    result = generate_edition(generation_input(max_sections_per_run=14, max_generation_budget=100_000))

    assert result.generation_status == "READY_FOR_REVIEW"
    assert result.gate_status == "PASS"
    assert result.state.qa_status == "PASS"
    assert result.state.source_hash
    assert result.state.prompt_version == PROMPT_VERSION
    assert result.state.model_version == MODEL_VERSION
    assert result.state.generated_at
    assert result.state.quality_score >= 75
    assert set(result.generated_sections) == set(SECTION_ORDER)
    assert "Editorial note" in result.sections["clean_reading_edition"]
    assert "Phase 5 does not generate a full book" in result.sections["clean_reading_edition"]
    assert all("section_status" in row for row in result.section_metadata)


def test_default_cost_controls_limit_sections_without_blocking_quality():
    result = generate_edition(generation_input())

    assert len(result.generated_sections) == 4
    assert len(result.skipped_sections) == len(SECTION_ORDER) - 4
    assert result.generation_status == "PARTIAL_DRY_RUN"
    assert result.state.qa_status == "NEEDS_MORE_RUNS"
    assert result.cost_controls["max_sections_per_run"] == 4
    assert result.cost_controls["dry_run_default"] is True


def test_max_generation_budget_skips_sections():
    result = generate_edition(generation_input(max_sections_per_run=14, max_generation_budget=10))

    assert result.generated_sections == []
    assert result.skipped_sections == SECTION_ORDER
    assert result.state.qa_status == "BLOCKED_QA"
    assert result.qa["missing_sections"] == SECTION_ORDER


def test_caching_skips_unchanged_source_hash_prompt_and_model():
    payload = generation_input()
    cache_key = generation_cache_key(
        source_hash=payload.source_hash,
        prompt_version=PROMPT_VERSION,
        model_version=MODEL_VERSION,
    )
    payload.existing_cache_keys = {cache_key}

    result = generate_edition(payload)

    assert result.generation_status == "SKIPPED_UNCHANGED"
    assert result.gate_status == "PASS"
    assert result.state.qa_status == "SKIPPED_UNCHANGED"
    assert result.sections == {}
    assert result.skipped_sections == SECTION_ORDER


def test_qa_blocks_low_quality_short_source():
    text = "Too short."
    result = generate_edition(generation_input(cleaned_text=text, source_hash=hash_source(text)))

    assert result.state.qa_status == "BLOCKED_QA"
    assert result.qa["hallucination_risk"] is True
    assert any("too short" in issue for issue in result.qa["qa_issues"])


def test_qa_reports_citation_coverage_readability_and_age_flag():
    text = SAMPLE_TEXT + "\nThis passage mentions explicit danger for age review."
    result = generate_edition(
        generation_input(
            cleaned_text=text,
            source_hash=hash_source(text),
            max_sections_per_run=14,
            max_generation_budget=100_000,
        )
    )

    assert result.qa["citation_source_coverage"] == 1
    assert result.qa["readability_score"] > 0
    assert result.qa["age_appropriateness_flag"] is True


def test_missing_metadata_blocks_generation():
    payload = generation_input(source_url="")

    result = generate_edition(payload)

    assert result.gate_status == "BLOCKED_TRACEABILITY"
    assert "source_url" in result.blocking_reason


def test_requested_sections_can_be_subset():
    result = generate_edition(
        generation_input(
            requested_sections=["quiz", "seo-copy"],
            max_sections_per_run=4,
            max_generation_budget=100_000,
        )
    )

    assert result.generated_sections == ["quiz", "seo_copy"]
    assert "Quiz" in result.sections["quiz"]
    assert "SEO Copy" in result.sections["seo_copy"]


def test_reports_include_state_and_qa(tmp_path: Path):
    result = generate_edition(generation_input(max_sections_per_run=2, max_generation_budget=100_000))

    json_path, csv_path, md_path = write_reports(result, tmp_path)
    rows = edition_report_json(result)
    csv_text = edition_report_csv(result)
    markdown = edition_report_markdown(result)

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()
    assert rows["prompt_version"] == PROMPT_VERSION
    assert "content" not in rows["sections"][0]
    assert "content_preview" in rows["sections"][0]
    assert "qa_status" in csv_text
    assert "gate_status" in csv_text
    assert "Earnalism Edition Generator Dry-Run Report" in markdown
    assert "Content preview" in markdown
    assert "Full generated content" not in markdown
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["state"]["prompt_version"] == PROMPT_VERSION
    assert "content" not in payload["sections"][0]
    assert payload["gate_status"] == "PASS"
    assert payload["qa"]["missing_sections"]


def test_default_markdown_excludes_full_generated_content(tmp_path: Path):
    result = generate_edition(generation_input(max_sections_per_run=1, max_generation_budget=100_000))

    _json_path, _csv_path, md_path = write_reports(result, tmp_path, content_preview_chars=24)

    markdown = md_path.read_text(encoding="utf-8")
    full_content = result.sections[result.generated_sections[0]]
    assert full_content not in markdown
    assert full_content[:24] in markdown


def test_include_content_report_writer_outputs_full_section_content_in_json_and_markdown(tmp_path: Path):
    result = generate_edition(generation_input(max_sections_per_run=1, max_generation_budget=100_000))

    json_path, _csv_path, md_path = write_reports(result, tmp_path, include_content=True)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    full_content = result.sections[result.generated_sections[0]]
    markdown = md_path.read_text(encoding="utf-8")
    assert payload["sections"][0]["content"] == full_content
    assert full_content in markdown
    assert "Full generated content" in markdown


def test_content_preview_chars_limits_default_json(tmp_path: Path):
    result = generate_edition(generation_input(max_sections_per_run=1, max_generation_budget=100_000))

    json_path, _csv_path, _md_path = write_reports(result, tmp_path, content_preview_chars=20)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(payload["sections"][0]["content_preview"]) == 20


def test_section_level_review_metadata_flags_conversion_sections():
    result = generate_edition(
        generation_input(
            requested_sections=["historical_context", "seo_copy", "quiz"],
            max_sections_per_run=3,
            max_generation_budget=100_000,
        )
    )

    metadata = {row["section_id"]: row for row in result.section_metadata}
    assert metadata["historical_context"]["editorial_review_required"] is True
    assert metadata["seo_copy"]["editorial_review_required"] is True
    assert metadata["quiz"]["editorial_review_required"] is False
    assert metadata["historical_context"]["source_coverage_status"] == "SOURCE_COVERED"


def test_tier_c_blocks_rights_before_generation():
    result = generate_edition(generation_input(rights_tier="C"))

    assert result.gate_status == "BLOCKED_RIGHTS"
    assert result.generated_sections == []


def test_missing_rights_blocks_review_required():
    result = generate_edition(generation_input(rights_tier="", verification_status=""))

    assert result.gate_status == "BLOCKED_RIGHTS_REVIEW_REQUIRED"


def test_tier_b_requires_region_gated_review_not_generation():
    result = generate_edition(generation_input(rights_tier="B"))

    assert result.gate_status == "REGION_GATED_REVIEW"
    assert result.generated_sections == []


def test_blocked_reason_blocks_rights():
    result = generate_edition(generation_input(blocked_reason="unsafe edition"))

    assert result.gate_status == "BLOCKED_RIGHTS"
    assert "unsafe edition" in result.blocking_reason


def test_non_ready_action_status_blocks_priority_gate():
    result = generate_edition(generation_input(action_status="READY_FOR_RIGHTS_REVIEW"))

    assert result.gate_status == "BLOCKED_PRIORITY_GATE"


def test_incomplete_ingestion_blocks_generation():
    result = generate_edition(generation_input(ingestion_status="PENDING_OCR"))

    assert result.gate_status == "BLOCKED_INGESTION"


def test_missing_content_or_provenance_hash_blocks_traceability():
    no_content = generate_edition(generation_input(content_hash=""))
    no_provenance = generate_edition(generation_input(provenance_hash=""))

    assert no_content.gate_status == "BLOCKED_TRACEABILITY"
    assert no_provenance.gate_status == "BLOCKED_TRACEABILITY"


def test_core_generator_blocks_non_dry_run_library_calls():
    result = generate_edition(generation_input(dry_run=False))

    assert result.gate_status == "BLOCKED_NON_DRY_RUN"
    assert result.blocking_reason == "Phase 5 edition generation is dry-run only."
    assert result.generated_sections == []
    assert result.dry_run is False


def test_phase4_full_text_payload_is_compatible(tmp_path: Path):
    payload_path = tmp_path / "phase4-full.json"
    source_hash = hash_source(SAMPLE_TEXT)
    payload_path.write_text(
        json.dumps({
            **SAMPLE_BOOK,
            "cleaned_text": SAMPLE_TEXT,
            "source_hash": source_hash,
            "content_hash": source_hash,
            "provenance_hash": "phase4-provenance",
            "rights_tier": "A",
            "verification_status": "approved",
            "action_status": "READY_FOR_GENERATION",
            "ingestion_status": "INGESTED",
        }),
        encoding="utf-8",
    )

    payload = load_payload(payload_path, sample=False)
    result = generate_edition(EditionGenerationInput(**payload))

    assert result.gate_status == "PASS"
    assert result.generated_sections


def test_phase4_nested_source_ingestion_payload_is_compatible(tmp_path: Path):
    payload_path = tmp_path / "phase4-nested.json"
    source_hash = hash_source(SAMPLE_TEXT)
    payload_path.write_text(
        json.dumps({
            "source_ingestion_result": {
                **SAMPLE_BOOK,
                "cleaned_text": SAMPLE_TEXT,
                "source_hash": source_hash,
                "content_hash": source_hash,
                "provenance_hash": "phase4-provenance",
                "rights_tier": "A",
                "verification_status": "approved",
                "action_status": "READY_FOR_GENERATION",
                "ingestion_status": "CLEANED",
            }
        }),
        encoding="utf-8",
    )

    payload = load_payload(payload_path, sample=False)

    assert payload["cleaned_text"] == SAMPLE_TEXT
    assert payload["source_hash"] == source_hash


def test_phase4_preview_only_payload_fails_with_clear_error(tmp_path: Path):
    payload_path = tmp_path / "phase4-preview-only.json"
    payload_path.write_text(
        json.dumps({
            **SAMPLE_BOOK,
            "cleaned_text_preview": SAMPLE_TEXT[:100],
            "source_hash": hash_source(SAMPLE_TEXT),
            "content_hash": hash_source(SAMPLE_TEXT),
            "provenance_hash": "phase4-provenance",
        }),
        encoding="utf-8",
    )

    try:
        load_payload(payload_path, sample=False)
    except ValueError as exc:
        assert "rerun Phase 4 with --include-text" in str(exc)
    else:
        raise AssertionError("preview-only Phase 4 payload should fail clearly")


def test_cli_sample_is_dry_run_and_rejects_commit():
    repo_root = Path(__file__).resolve().parents[2]
    ok = subprocess.run(
        [sys.executable, "scripts/edition_generator.py", "--sample", "--output-dir", "/tmp/earnalism-edition-test"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    blocked = subprocess.run(
        [sys.executable, "scripts/edition_generator.py", "--sample", "--commit"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert ok.returncode == 0
    assert "Edition generation dry-run complete" in ok.stdout
    assert blocked.returncode != 0
    assert "dry-run only" in blocked.stderr

    payload = json.loads(Path("/tmp/earnalism-edition-test/edition_generation_report.json").read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
