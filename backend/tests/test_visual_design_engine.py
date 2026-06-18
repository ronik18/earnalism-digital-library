from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.source_ingestion import hash_source
from backend.visual_design_engine import (
    ASSET_TYPES,
    HOOK_ASSETS,
    VISUAL_ASSET_TEMPLATES,
    VisualGenerationInput,
    contains_external_image_reference,
    evaluate_visual_assets,
    external_dependency_issues,
    generate_visual_assets,
    visual_report_csv,
    visual_report_json,
    visual_report_markdown,
)
from scripts.visual_design_engine import SAMPLE_TEXT, load_payload, write_reports


def sample_input(**overrides):
    payload = {
        "source_work": "Alice's Adventures in Wonderland",
        "author": "Lewis Carroll",
        "cleaned_text": SAMPLE_TEXT,
        "source_hash": hash_source(SAMPLE_TEXT),
        "content_hash": hash_source(SAMPLE_TEXT),
        "provenance_hash": "sample-provenance-hash",
        "rights_tier": "A",
        "verification_status": "approved",
        "blocked_reason": "",
        "action_status": "READY_FOR_GENERATION",
        "ingestion_status": "CLEANED",
        "edition_generation_status": "PARTIAL_DRY_RUN",
    }
    payload.update(overrides)
    return VisualGenerationInput(**payload)


def test_all_visual_asset_templates_exist():
    assert ASSET_TYPES == [
        "character_relationship_diagram",
        "timeline",
        "chapter_flow",
        "theme_map",
        "vocabulary_cards",
        "quiz_worksheet",
        "seven_day_reading_plan_card",
        "teacher_handout",
        "reading_edition_epub_hook",
        "study_guide_pdf_hook",
        "mobile_html_edition_hook",
    ]
    assert set(VISUAL_ASSET_TEMPLATES) == set(ASSET_TYPES)


def test_generate_visual_assets_fixture_is_deterministic_and_lightweight():
    result = generate_visual_assets(sample_input(max_assets_per_run=11))

    assert result.generation_status == "READY_FOR_REVIEW"
    assert result.gate_status == "PASS"
    assert result.qa["qa_status"] == "PASS"
    assert len(result.generated_assets) == 11
    assert all(asset.file_size < 120_000 for asset in result.generated_assets)
    assert all(asset.source_hash == hash_source(SAMPLE_TEXT) for asset in result.generated_assets)
    assert result.qa["copyrighted_image_dependency"] is False
    assert result.qa["ai_image_generation_required"] is False


def test_default_cost_control_limits_asset_count():
    result = generate_visual_assets(sample_input())

    assert len(result.generated_assets) == 8
    assert len(result.skipped_assets) == len(ASSET_TYPES) - 8
    assert result.generation_status == "PARTIAL_DRY_RUN"
    assert result.qa["qa_status"] == "NEEDS_MORE_RUNS"


def test_mermaid_and_svg_assets_are_generated_without_external_images():
    result = generate_visual_assets(
        sample_input(
            requested_assets=[
                "character_relationship_diagram",
                "timeline",
                "chapter_flow",
                "theme_map",
            ],
            max_assets_per_run=4,
        )
    )
    assets = {asset.asset_type: asset for asset in result.generated_assets}

    assert assets["character_relationship_diagram"].content.startswith("graph TD")
    assert assets["timeline"].content.startswith("timeline")
    assert assets["chapter_flow"].content.startswith("graph LR")
    assert "<svg" in assets["theme_map"].content
    assert all("<img" not in asset.content for asset in result.generated_assets)


def test_html_assets_are_deterministic_templates():
    result = generate_visual_assets(
        sample_input(
            requested_assets=[
                "vocabulary_cards",
                "quiz_worksheet",
                "seven_day_reading_plan_card",
                "teacher_handout",
            ],
            max_assets_per_run=4,
        )
    )

    assert all(asset.output_format == "html" for asset in result.generated_assets)
    assert all("<!doctype html>" in asset.content for asset in result.generated_assets)
    assert all("https://" not in asset.content for asset in result.generated_assets)


def test_epub_pdf_and_mobile_hooks_are_dry_run_capable():
    result = generate_visual_assets(
        sample_input(
            requested_assets=[
                "reading_edition_epub_hook",
                "study_guide_pdf_hook",
                "mobile_html_edition_hook",
            ],
            max_assets_per_run=3,
        )
    )
    hooks = {asset.asset_type: asset for asset in result.generated_assets}

    assert set(hooks) == HOOK_ASSETS
    assert "pandoc --from=html --to=epub3" in hooks["reading_edition_epub_hook"].generation_hook
    assert "pandoc --from=html --to=pdf" in hooks["study_guide_pdf_hook"].generation_hook
    assert "pandoc --from=html --to=epub3" in hooks["reading_edition_epub_hook"].content
    assert "pandoc --from=html --to=pdf" in hooks["study_guide_pdf_hook"].content
    assert hooks["mobile_html_edition_hook"].generation_hook == "static responsive HTML render"
    assert result.qa["epub_pdf_hooks_dry_run_capable"] is True


def test_asset_metadata_contains_required_fields():
    result = generate_visual_assets(sample_input(requested_assets=["theme_map"], max_assets_per_run=1))
    metadata = result.generated_assets[0].metadata()

    assert metadata["asset_type"] == "theme_map"
    assert metadata["source_work"]
    assert metadata["source_hash"]
    assert metadata["dry_run"] is True
    assert metadata["generated_at"]
    assert metadata["quality_score"] >= 75
    assert metadata["file_size"] > 0


def test_reports_are_preview_only_by_default_and_include_content_when_requested(tmp_path: Path):
    result = generate_visual_assets(sample_input(requested_assets=["teacher_handout"], max_assets_per_run=1))

    json_path, _csv_path, md_path = write_reports(result, tmp_path, content_preview_chars=24)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    full_content = result.generated_assets[0].content

    assert "content" not in payload["generated_assets"][0]
    assert payload["generated_assets"][0]["content_preview"] == full_content[:24]
    assert full_content not in markdown
    assert full_content[:24] in markdown

    json_path, _csv_path, md_path = write_reports(result, tmp_path / "full", include_content=True)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    assert payload["generated_assets"][0]["content"] == full_content
    assert full_content in markdown


def test_report_helpers_include_metadata_and_status():
    result = generate_visual_assets(sample_input(requested_assets=["quiz_worksheet"], max_assets_per_run=1))
    json_payload = visual_report_json(result)
    csv_text = visual_report_csv(result)
    markdown = visual_report_markdown(result)

    assert json_payload["generation_status"] == "READY_FOR_REVIEW"
    assert json_payload["generated_assets"][0]["asset_type"] == "quiz_worksheet"
    assert "file_size" in csv_text
    assert "gate_status" in csv_text
    assert "Visual Design Engine Dry-Run Report" in markdown
    assert json_payload["gate_status"] == "PASS"


def test_non_dry_run_is_blocked_even_when_called_as_library():
    result = generate_visual_assets(sample_input(dry_run=False))

    assert result.generation_status == "BLOCKED_NON_DRY_RUN"
    assert result.generated_assets == []
    assert result.qa["issues"] == ["Phase 6 visual generation is dry-run only."]


def test_missing_source_traceability_blocks_generation():
    result = generate_visual_assets(sample_input(source_hash=""))

    assert result.generation_status == "BLOCKED_TRACEABILITY"
    assert result.generated_assets == []


def test_tier_c_blocks_rights_before_visual_generation():
    result = generate_visual_assets(sample_input(rights_tier="C"))

    assert result.generation_status == "BLOCKED_RIGHTS"
    assert result.generated_assets == []


def test_missing_or_unknown_rights_blocks_review_required():
    result = generate_visual_assets(sample_input(rights_tier="", verification_status=""))

    assert result.generation_status == "BLOCKED_RIGHTS_REVIEW_REQUIRED"


def test_tier_b_requires_region_gated_review():
    result = generate_visual_assets(sample_input(rights_tier="B"))

    assert result.generation_status == "REGION_GATED_REVIEW"


def test_blocked_reason_blocks_rights():
    result = generate_visual_assets(sample_input(blocked_reason="unsafe visual rights"))

    assert result.generation_status == "BLOCKED_RIGHTS"
    assert "unsafe visual rights" in result.blocking_reason


def test_non_ready_action_status_blocks_priority_gate():
    result = generate_visual_assets(sample_input(action_status="READY_FOR_RIGHTS_REVIEW"))

    assert result.generation_status == "BLOCKED_PRIORITY_GATE"


def test_incomplete_ingestion_blocks_visual_generation():
    result = generate_visual_assets(sample_input(ingestion_status="PENDING_OCR"))

    assert result.generation_status == "BLOCKED_INGESTION"


def test_missing_or_failed_edition_status_blocks_visual_generation():
    missing = generate_visual_assets(sample_input(edition_generation_status=""))
    failed = generate_visual_assets(sample_input(edition_generation_status="BLOCKED_QA"))

    assert missing.generation_status == "BLOCKED_EDITION_GATE"
    assert failed.generation_status == "BLOCKED_EDITION_GATE"


def test_missing_content_or_provenance_hash_blocks_traceability():
    no_content = generate_visual_assets(sample_input(content_hash=""))
    no_provenance = generate_visual_assets(sample_input(provenance_hash=""))

    assert no_content.generation_status == "BLOCKED_TRACEABILITY"
    assert no_provenance.generation_status == "BLOCKED_TRACEABILITY"


def test_allowed_edition_statuses_pass_gate():
    for status in ["READY_FOR_REVIEW", "PARTIAL_DRY_RUN", "QA_PASSED"]:
        result = generate_visual_assets(
            sample_input(
                edition_generation_status=status,
                requested_assets=["quiz_worksheet"],
                max_assets_per_run=1,
            )
        )
        assert result.gate_status == "PASS"
        assert result.generated_assets


def test_external_image_dependency_patterns_are_detected():
    patterns = [
        "<img alt='x'>",
        "<source src='cover.png'>",
        "<source srcset='cover.png 2x'>",
        "<div style='background-image: cover.png'>",
        "<style>.x{background:url(cover.png)}</style>",
        "http://example.test/cover",
        "https://example.test/cover",
        "data:image/png;base64,abc",
        "//cdn.example.test/cover.png",
    ]

    assert all(contains_external_image_reference(pattern) for pattern in patterns)
    issues = external_dependency_issues(patterns)
    assert "<img" in issues
    assert "src=" in issues
    assert "srcset=" in issues
    assert "background-image" in issues
    assert "url(" in issues
    assert "http://" in issues
    assert "https://" in issues
    assert "data:image" in issues
    assert "//cdn" in issues


def test_external_image_dependency_blocks_qa():
    class FakeAsset:
        asset_type = "fake"
        content = "<div style='background-image:url(https://cdn.example.test/a.png)'></div>"
        file_size = 64
        qa_status = "PASS"

    qa = evaluate_visual_assets([FakeAsset()], ["fake"], [])

    assert qa["qa_status"] == "BLOCKED_QA"
    assert qa["copyrighted_image_dependency"] is True
    assert any("External image dependency" in issue for issue in qa["issues"])


def test_preview_only_phase4_payload_fails_clearly(tmp_path: Path):
    payload = tmp_path / "preview.json"
    payload.write_text(
        json.dumps({
            "source_work": "Preview",
            "cleaned_text_preview": "Only preview",
            "source_hash": "hash",
            "content_hash": "hash",
            "provenance_hash": "prov",
        }),
        encoding="utf-8",
    )

    try:
        load_payload(payload, sample=False)
    except ValueError as exc:
        assert "rerun Phase 4 with --include-text" in str(exc)
    else:
        raise AssertionError("preview-only payload should fail")


def test_cli_sample_is_dry_run_and_rejects_commit():
    repo_root = Path(__file__).resolve().parents[2]
    ok = subprocess.run(
        [sys.executable, "scripts/visual_design_engine.py", "--sample", "--output-dir", "/tmp/earnalism-visual-test"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    blocked = subprocess.run(
        [sys.executable, "scripts/visual_design_engine.py", "--sample", "--commit"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert ok.returncode == 0
    assert "Visual design dry-run complete" in ok.stdout
    assert blocked.returncode != 0
    assert "dry-run only" in blocked.stderr
