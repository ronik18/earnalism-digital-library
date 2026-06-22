from __future__ import annotations

from pathlib import Path

from scripts.orchestrate_english_book_onboarding import (
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    PUBLICATION_HOLD,
    ensure_no_public_audio_files,
    run_orchestration,
    write_reports,
)


def write_config(tmp_path: Path, content: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "candidate.yml"
    config_path.write_text(content, encoding="utf-8")
    return config_path


def base_config(tmp_path: Path, **overrides) -> str:
    values = {
        "slug": "test-book",
        "title": "Test Book",
        "author": "Test Author",
        "language": "english",
        "source_url": "https://www.gutenberg.org/ebooks/1",
        "source_name": "Project Gutenberg",
        "source_license": "Public Domain",
        "source_license_url": "https://www.gutenberg.org/policy/license.html",
        "commercial_use_evidence": "Public domain commercial use requires final legal review.",
        "local_source_path": "onboarding/books/frankenstein-source-sample.txt",
        "owner_approval_status": "OWNER_APPROVAL_REQUIRED",
        "cover_owner_designed": "false",
        "cover_provenance_note": "",
        "cover_owner_approval_status": "OWNER_APPROVAL_REQUIRED",
        "audiobook_public_target": "false",
        "derivative_rights_status": "separate approval required",
        "model_voice_license_status": "",
    }
    values.update(overrides)
    return f"""slug: {values['slug']}
title: {values['title']}
author: {values['author']}
language: {values['language']}
source_url: {values['source_url']}
source_name: {values['source_name']}
source_license: {values['source_license']}
source_license_url: {values['source_license_url']}
commercial_use_evidence: {values['commercial_use_evidence']}
local_source_path: {values['local_source_path']}
owner_approval_status: {values['owner_approval_status']}
cover:
  front_path:
  back_path:
  owner_designed: {values['cover_owner_designed']}
  provenance_note: {values['cover_provenance_note']}
  owner_approval_status: {values['cover_owner_approval_status']}
audiobook:
  public_target: {values['audiobook_public_target']}
  derivative_rights_status: {values['derivative_rights_status']}
  model_voice_license_status: {values['model_voice_license_status']}
  human_review_status:
  accessibility_listening_status:
  rollback_approval_status:
  owner_legal_approval_status:
  refund_support_readiness: false
"""


def stage(result, name):
    return next(item for item in result.stages if item.name == name)


def test_missing_source_url_blocks(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, source_url=""))
    result = run_orchestration(config_path)

    assert result.final_gate["status"] == PUBLICATION_HOLD
    assert any("source_url" in blocker for blocker in result.final_gate["blockers"])


def test_missing_source_license_blocks(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, source_license=""))
    result = run_orchestration(config_path)

    assert stage(result, "input_validation").status == "BLOCKED"
    assert any("source_license" in blocker for blocker in result.final_gate["blockers"])


def test_missing_commercial_use_evidence_blocks(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, commercial_use_evidence=""))
    result = run_orchestration(config_path)

    assert stage(result, "source_url_license_validation").status == "BLOCKED"
    assert any("commercial-use evidence is required" in blocker for blocker in result.final_gate["blockers"])


def test_missing_owner_cover_provenance_blocks(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path))
    result = run_orchestration(config_path)
    cover_stage = stage(result, "cover_asset_provenance_gate")

    assert cover_stage.status == "BLOCKED"
    assert any("owner-designed cover provenance" in blocker for blocker in cover_stage.blockers)
    assert any("cover provenance note" in blocker for blocker in cover_stage.blockers)


def test_public_audiobook_target_blocks_by_default(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, audiobook_public_target="true"))
    result = run_orchestration(config_path)
    audio_stage = stage(result, "audiobook_planning_packet")

    assert result.audiobook_gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert audio_stage.status == "BLOCKED"
    assert any("public audiobook target is not allowed" in blocker for blocker in audio_stage.blockers)


def test_audio_release_remains_blocked(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path))
    result = run_orchestration(config_path)

    assert result.audiobook_gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result.audiobook_gate["public_audio_publish_allowed"] is False
    assert result.audiobook_gate["listen_now_cta"] is False
    assert result.audiobook_gate["audio_object_metadata"] is False


def test_generated_reports_say_hold_not_go_when_evidence_incomplete(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "reports", write_root_reports=False)

    assert result.final_gate["go_no_go"] == "HOLD"
    assert (tmp_path / "reports" / "test-book").is_dir()
    report_text = paths["ENGLISH_BOOK_PUBLICATION_GATE_REPORT.md"].read_text(encoding="utf-8")
    orchestration_text = paths["BOOK_ONBOARDING_ORCHESTRATION_REPORT.md"].read_text(encoding="utf-8")
    assert "HOLD" in report_text
    assert "GO" not in report_text.replace("GO/HOLD", "")
    assert "does not publish books" in orchestration_text


def test_no_public_audio_files_are_created(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path))
    before = ensure_no_public_audio_files()
    result = run_orchestration(config_path)
    write_reports(result, tmp_path / "reports", write_root_reports=False)
    after = ensure_no_public_audio_files()

    assert before == after == []


def test_no_unsupported_accessibility_claims_are_generated(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "reports", write_root_reports=False)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths.values() if path.suffix == ".md")

    assert "WCAG compliant" not in combined
    assert "blind-user tested" not in combined
    assert "fully accessible" not in combined


def test_slug_scoped_output_directory_contains_all_reports(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "onboarding", write_root_reports=False)
    scoped_dir = tmp_path / "onboarding" / "frankenstein"

    assert scoped_dir.is_dir()
    assert paths["output/onboarding/frankenstein/BOOK_ONBOARDING_ORCHESTRATION_REPORT.md"] == (
        scoped_dir / "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md"
    )
    expected_files = {
        "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md",
        "ENGLISH_BOOK_RIGHTS_EVIDENCE_SCORECARD.md",
        "ENGLISH_BOOK_PUBLICATION_GATE_REPORT.md",
        "ENGLISH_AUDIOBOOK_RELEASE_GATE_REPORT.md",
        "ENGLISH_AUDIOBOOK_QA_PACKET.md",
        "ENGLISH_BOOK_SEO_PREVIEW_REPORT.md",
        "ENGLISH_BOOK_VISUAL_SCORECARD.md",
        "english_book_onboarding_report.json",
        "next_codex_prompt.md",
    }
    assert expected_files.issubset({path.name for path in scoped_dir.iterdir()})
    assert "Frankenstein" in (scoped_dir / "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md").read_text(encoding="utf-8")


def test_two_different_slugs_do_not_overwrite_each_other(tmp_path: Path):
    first_config = write_config(tmp_path / "first", base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    second_config = write_config(tmp_path / "second", base_config(tmp_path, slug="jane-eyre", title="Jane Eyre"))
    output_root = tmp_path / "onboarding"

    first = run_orchestration(first_config)
    second = run_orchestration(second_config)
    write_reports(first, output_root, write_root_reports=False)
    write_reports(second, output_root, write_root_reports=False)

    first_report = output_root / "frankenstein" / "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md"
    second_report = output_root / "jane-eyre" / "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md"
    assert first_report.exists()
    assert second_report.exists()
    assert "Frankenstein" in first_report.read_text(encoding="utf-8")
    assert "Jane Eyre" in second_report.read_text(encoding="utf-8")
    assert first_report.read_text(encoding="utf-8") != second_report.read_text(encoding="utf-8")


def test_top_level_latest_run_reports_still_work(tmp_path: Path, monkeypatch):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="latest-book", title="Latest Book"))
    result = run_orchestration(config_path)
    monkeypatch.setattr("scripts.orchestrate_english_book_onboarding.ROOT", tmp_path)
    monkeypatch.setattr(
        "scripts.orchestrate_english_book_onboarding.CODEX_PROMPT_PATH",
        tmp_path / "output" / "codex_prompts" / "next_english_book_onboarding_prompt.md",
    )
    monkeypatch.setattr(
        "scripts.orchestrate_english_book_onboarding.LATEST_OUTPUT_DIR",
        tmp_path / "output" / "english_book_onboarding",
    )

    paths = write_reports(result, tmp_path / "output" / "onboarding", write_root_reports=True)

    assert (tmp_path / "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md").exists()
    assert (tmp_path / "output" / "onboarding" / "latest-book" / "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md").exists()
    assert (tmp_path / "output" / "onboarding" / "latest-book" / "next_codex_prompt.md").exists()
    assert (tmp_path / "output" / "codex_prompts" / "next_english_book_onboarding_prompt.md").exists()
    assert paths["BOOK_ONBOARDING_ORCHESTRATION_REPORT.md"] == tmp_path / "BOOK_ONBOARDING_ORCHESTRATION_REPORT.md"
