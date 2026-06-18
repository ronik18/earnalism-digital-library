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
from scripts.edition_generator import SAMPLE_TEXT, write_reports


def sample_payload(**overrides):
    text = overrides.pop("cleaned_text", SAMPLE_TEXT)
    payload = {
        "title": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "language": "en",
        "cleaned_text": text,
        "source_hash": hash_source(text),
        "source_name": "Project Gutenberg",
        "source_url": "https://www.gutenberg.org/ebooks/11",
        "source_license": "Public domain",
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
    assert result.state.qa_status == "PASS"
    assert result.state.source_hash
    assert result.state.prompt_version == PROMPT_VERSION
    assert result.state.model_version == MODEL_VERSION
    assert result.state.generated_at
    assert result.state.quality_score >= 75
    assert set(result.generated_sections) == set(SECTION_ORDER)
    assert "Editorial note" in result.sections["clean_reading_edition"]
    assert "Phase 5 does not generate a full book" in result.sections["clean_reading_edition"]


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

    try:
        generate_edition(payload)
    except ValueError as exc:
        assert "source_url" in str(exc)
    else:
        raise AssertionError("missing source_url should block edition generation")


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
    assert rows[0]["prompt_version"] == PROMPT_VERSION
    assert "qa_status" in csv_text
    assert "Earnalism Edition Generator Dry-Run Report" in markdown
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["state"]["prompt_version"] == PROMPT_VERSION
    assert payload["qa"]["missing_sections"]


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
