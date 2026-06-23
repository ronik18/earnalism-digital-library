from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.orchestrate_english_book_onboarding import (
    PUBLIC_AUDIO_RELEASE_BLOCKED,
    PUBLICATION_HOLD,
    ELEVENLABS_INTERNAL_SAMPLE_STAGE,
    TTS_PROVIDER_INTERNAL_EVAL_STAGE,
    ensure_no_public_audio_files,
    run_orchestration,
    write_reports,
)


@pytest.fixture(autouse=True)
def cleanup_internal_sync_test_outputs():
    root = Path.cwd() / "internal" / "audiobook_lab"
    slugs = {"test-book", "frankenstein", "jane-eyre", "latest-book"}
    for slug in slugs:
        target = root / slug
        if target.exists():
            shutil.rmtree(target)
    yield
    for slug in slugs:
        target = root / slug
        if target.exists():
            shutil.rmtree(target)


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
        "selected_model_candidate": "kokoro",
        "preferred_provider": "elevenlabs",
        "selected_provider_voice_id": "OWNER_SELECTION_REQUIRED",
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
  desired_status: internal_only
  public_target: {values['audiobook_public_target']}
  public_audio_target: {values['audiobook_public_target']}
  selected_model_candidate: {values['selected_model_candidate']}
  require_tts_model_license_review: true
  derivative_rights_status: {values['derivative_rights_status']}
  model_voice_license_status: {values['model_voice_license_status']}
  human_review_status:
  accessibility_listening_status:
  rollback_approval_status:
  owner_legal_approval_status:
  refund_support_readiness: false
audiobook_sync:
  enabled: true
  chapter: 1
  language: en
  model_candidate: kokoro
  sync_level: sentence
  public_release_target: false
  require_model_eligibility: true
audiobook_provider_eval:
  enabled: true
  preferred_provider: {values['preferred_provider']}
  selected_voice_id: {values['selected_provider_voice_id']}
  paid_plan_evidence_required: true
  commercial_use_evidence_required: true
  beta_features_allowed: false
  owner_approval_required: true
  legal_review_required: true
  public_release_target: false
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
    assert result.audiobook_gate["sync_status"] in {"INTERNAL_DRY_RUN_ONLY", "HOLD_SYNC_QA_REQUIRED"}


def test_orchestrator_includes_sync_dry_run_stage(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    sync_stage = stage(result, "audiobook_sync_dry_run_stage")

    assert sync_stage.status in {"INTERNAL_DRY_RUN_ONLY", "HOLD_SYNC_QA_REQUIRED"}
    assert sync_stage.details["public_audio_release_status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert sync_stage.details["public_audio_allowed"] is False
    assert sync_stage.details["listen_now_cta"] is False
    assert sync_stage.details["audio_object_metadata"] is False
    assert sync_stage.details["internal_sync_manifest_path"].endswith("sync_manifest.json")
    assert sync_stage.details["scoped_sync_manifest_path"] == "output/onboarding/frankenstein/audiobook_sync/sync_manifest.json"


def test_orchestrator_runs_model_license_stage_before_sync_stage(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    names = [item.name for item in result.stages]

    assert "TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW" in names
    assert "TTS_VOICE_RIGHTS_INTERNAL_EVAL_REVIEW" in names
    assert TTS_PROVIDER_INTERNAL_EVAL_STAGE in names
    assert ELEVENLABS_INTERNAL_SAMPLE_STAGE in names
    assert names.index("TTS_MODEL_LICENSE_AND_SUITABILITY_REVIEW") < names.index("audiobook_sync_dry_run_stage")
    assert names.index("TTS_VOICE_RIGHTS_INTERNAL_EVAL_REVIEW") < names.index("audiobook_sync_dry_run_stage")
    assert names.index(TTS_PROVIDER_INTERNAL_EVAL_STAGE) < names.index("audiobook_sync_dry_run_stage")
    assert names.index(ELEVENLABS_INTERNAL_SAMPLE_STAGE) < names.index("audiobook_sync_dry_run_stage")
    assert names.index("TTS_VOICE_RIGHTS_INTERNAL_EVAL_REVIEW") < names.index(TTS_PROVIDER_INTERNAL_EVAL_STAGE)


def test_provider_internal_eval_stage_records_elevenlabs_hold_before_sync(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    provider_stage = stage(result, TTS_PROVIDER_INTERNAL_EVAL_STAGE)
    names = [item.name for item in result.stages]

    assert provider_stage.status == "HOLD_PROVIDER_REVIEW"
    assert provider_stage.details["selected_provider_id"] == "elevenlabs"
    assert provider_stage.details["selected_provider_decision"] == "HOLD_PROVIDER_REVIEW"
    assert provider_stage.details["selected_provider_internal_eval_status"] == "HOLD_PROVIDER_REVIEW"
    assert provider_stage.details["selected_provider_production_status"] == "PRODUCTION_BLOCKED"
    assert provider_stage.details["selected_provider_voice_id"] == "OWNER_SELECTION_REQUIRED"
    assert provider_stage.details["paid_provider_api_called"] is False
    assert provider_stage.details["public_audio_allowed"] is False
    assert provider_stage.details["real_audio_generation_allowed"] is False
    assert provider_stage.details["listen_now_cta_allowed"] is False
    assert provider_stage.details["audio_object_metadata_allowed"] is False
    assert any("selected provider voice" in blocker for blocker in provider_stage.blockers)
    assert names.index(TTS_PROVIDER_INTERNAL_EVAL_STAGE) < names.index("audiobook_sync_dry_run_stage")


def test_elevenlabs_internal_sample_stage_prepares_files_but_keeps_hold(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    sample_stage = stage(result, ELEVENLABS_INTERNAL_SAMPLE_STAGE)

    assert sample_stage.status == "HOLD_PROVIDER_REVIEW"
    assert sample_stage.details["provider"] == "elevenlabs"
    assert sample_stage.details["provider_internal_eval_status"] == "HOLD_PROVIDER_REVIEW"
    assert sample_stage.details["provider_production_status"] == "PRODUCTION_BLOCKED"
    assert sample_stage.details["selected_voice_name"] == "Rachel"
    assert sample_stage.details["selected_voice_id"] == "21m00Tcm4TlvDq8ikWAM"
    assert sample_stage.details["evidence_file_exists"] is True
    assert sample_stage.details["imported_audio_exists"] is False
    assert sample_stage.details["import_status"] == "NOT_IMPORTED_YET"
    assert sample_stage.details["sync_status"] == "HOLD_SYNC_QA_REQUIRED"
    assert sample_stage.details["public_audio_allowed"] is False
    assert sample_stage.details["provider_api_called"] is False
    assert sample_stage.details["audio_generated_by_repo"] is False
    assert sample_stage.details["full_chapter_generation_allowed"] is False
    assert sample_stage.details["full_book_generation_allowed"] is False
    assert len(sample_stage.details["sample_prep_files"]) == 4
    assert any("sample_text.txt" in path for path in sample_stage.details["sample_prep_files"])


def test_elevenlabs_sample_reports_are_written_to_slug_scoped_output(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "onboarding", write_root_reports=False)
    scoped_dir = tmp_path / "onboarding" / "frankenstein"

    assert (scoped_dir / "ELEVENLABS_DRACULA_INTERNAL_SAMPLE_REPORT.md").exists()
    assert (scoped_dir / "ELEVENLABS_DRACULA_SAMPLE_QA_SCORECARD.md").exists()
    assert (scoped_dir / "ELEVENLABS_DRACULA_HIGHLIGHT_SYNC_QA_REPORT.md").exists()
    assert "HOLD" in (scoped_dir / "ELEVENLABS_DRACULA_SAMPLE_QA_SCORECARD.md").read_text(encoding="utf-8")
    assert "public audio remains blocked" in (
        scoped_dir / "ELEVENLABS_DRACULA_HIGHLIGHT_SYNC_QA_REPORT.md"
    ).read_text(encoding="utf-8").lower()
    assert paths["output/onboarding/frankenstein/ELEVENLABS_DRACULA_INTERNAL_SAMPLE_REPORT.md"] == (
        scoped_dir / "ELEVENLABS_DRACULA_INTERNAL_SAMPLE_REPORT.md"
    )


def test_selected_model_decision_appears_in_orchestrator_json(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "onboarding", write_root_reports=False)
    report = paths["output/onboarding/frankenstein/english_book_onboarding_report.json"].read_text(encoding="utf-8")

    assert '"selected_model_candidate": "kokoro"' in report
    assert '"selected_model_decision": "HOLD_VOICE_RIGHTS"' in report
    assert '"selected_model_internal_eval_status": "HOLD_VOICE_RIGHTS"' in report
    assert '"selected_voice_id": "af_heart"' in report
    assert '"selected_voice_internal_eval_status": "HOLD_VOICE_RIGHTS"' in report
    assert '"model_generation": "HOLD_VOICE_RIGHTS"' in report
    assert '"selected_provider_id": "elevenlabs"' in report
    assert '"selected_provider_decision": "HOLD_PROVIDER_REVIEW"' in report
    assert '"provider_internal_eval_status": "HOLD_PROVIDER_REVIEW"' in report
    assert '"selected_provider_production_status": "PRODUCTION_BLOCKED"' in report
    assert '"elevenlabs_sample_status": "HOLD_PROVIDER_REVIEW"' in report
    assert '"elevenlabs_sample_import_status": "NOT_IMPORTED_YET"' in report
    assert '"elevenlabs_sample_public_audio_allowed": false' in report


def test_voice_rights_internal_eval_stage_records_selected_candidate(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    voice_stage = stage(result, "TTS_VOICE_RIGHTS_INTERNAL_EVAL_REVIEW")

    assert voice_stage.status == "HOLD_VOICE_RIGHTS"
    assert voice_stage.details["selected_model_candidate"] == "kokoro"
    assert voice_stage.details["selected_model_internal_eval_status"] == "HOLD_VOICE_RIGHTS"
    assert voice_stage.details["selected_voice_id"] == "af_heart"
    assert voice_stage.details["selected_voice_internal_eval_status"] == "HOLD_VOICE_RIGHTS"
    assert "selected voice speaker provenance" in voice_stage.details["selected_voice_blockers"]
    assert voice_stage.details["public_audio_allowed"] is False
    assert voice_stage.details["real_audio_generation_allowed"] is False
    assert any("speaker" in blocker.lower() or "voice" in blocker.lower() for blocker in voice_stage.blockers)


def test_next_prompt_requests_voice_rights_evidence_before_audio_generation(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "onboarding", write_root_reports=False)
    prompt = paths["output/onboarding/frankenstein/next_codex_prompt.md"].read_text(encoding="utf-8")

    assert "Do not generate an audio sample yet" in prompt
    assert "Current selected Kokoro voice: `af_heart`" in prompt
    assert "Current selected voice internal-eval status: `HOLD_VOICE_RIGHTS`" in prompt
    assert "Current selected licensed provider: `elevenlabs`" in prompt
    assert "Current selected provider voice: `OWNER_SELECTION_REQUIRED`" in prompt
    assert "Current selected provider voice type: `platform_voice`" in prompt
    assert "Current licensed provider internal-eval status: `HOLD_PROVIDER_REVIEW`" in prompt
    assert "Current licensed provider blockers:" in prompt
    assert "KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md" in prompt
    assert "KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md" in prompt
    assert "ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md" in prompt
    assert "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md" in prompt
    assert "Collect owner/legal-reviewed selected voice or speaker-rights evidence" in prompt
    assert "Do not generate a provider audio sample yet" in prompt
    assert "future separate task may prepare an internal-only 2-3 minute" not in prompt


def test_sync_manifest_path_is_recorded_in_slug_scoped_output(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "onboarding", write_root_reports=False)
    sync_manifest = tmp_path / "onboarding" / "frankenstein" / "audiobook_sync" / "sync_manifest.json"

    assert sync_manifest.exists()
    assert paths["output/onboarding/frankenstein/audiobook_sync/sync_manifest.json"] == sync_manifest
    assert "placeholder-no-audio-generated" in sync_manifest.read_text(encoding="utf-8")


def test_missing_sync_qa_cannot_produce_audiobook_go(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path))
    result = run_orchestration(config_path)

    assert result.audiobook_gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert result.audiobook_gate["public_audio_publish_allowed"] is False
    assert any("public audiobook release is blocked" in blocker for blocker in result.audiobook_gate["blockers"])


def test_missing_model_license_keeps_audio_hold(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, model_voice_license_status=""))
    result = run_orchestration(config_path)

    assert result.audiobook_gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert any("model/voice license evidence is missing" in blocker for blocker in result.audiobook_gate["blockers"])


def test_missing_derivative_rights_keeps_audio_hold(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, derivative_rights_status=""))
    result = run_orchestration(config_path)

    assert result.audiobook_gate["status"] == PUBLIC_AUDIO_RELEASE_BLOCKED
    assert any("derivative audiobook rights evidence is missing" in blocker for blocker in result.audiobook_gate["blockers"])


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


def test_no_listen_now_or_audioobject_metadata_is_generated(tmp_path: Path):
    config_path = write_config(tmp_path, base_config(tmp_path, slug="frankenstein", title="Frankenstein"))
    result = run_orchestration(config_path)
    paths = write_reports(result, tmp_path / "reports", write_root_reports=False)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths.values() if path.is_file())

    assert "Listen Now" not in combined
    assert "AudioObject" not in combined
    assert "public_audio_allowed\": true" not in combined


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
        "KOKORO_AF_HEART_OWNER_LEGAL_REVIEW_FORM.md",
        "KOKORO_AF_HEART_EVIDENCE_COLLECTION_CHECKLIST.md",
        "TTS_PROVIDER_INTERNAL_EVAL_REVIEW.md",
        "TTS_PROVIDER_COMMERCIAL_RIGHTS_SCORECARD.md",
        "ELEVENLABS_PROVIDER_OWNER_LEGAL_REVIEW_FORM.md",
        "ELEVENLABS_PROVIDER_INTERNAL_EVAL_CHECKLIST.md",
        "ELEVENLABS_DRACULA_INTERNAL_SAMPLE_REPORT.md",
        "ELEVENLABS_DRACULA_SAMPLE_QA_SCORECARD.md",
        "ELEVENLABS_DRACULA_HIGHLIGHT_SYNC_QA_REPORT.md",
        "tts_provider_internal_eval_review.json",
        "english_book_onboarding_report.json",
        "next_codex_prompt.md",
    }
    assert expected_files.issubset({path.name for path in scoped_dir.iterdir()})
    assert (scoped_dir / "audiobook_sync" / "sync_manifest.json").exists()
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
