from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from scripts import approved_to_publish_builder as builder
from scripts import prepare_bengali_candidate as bengali
from scripts import prepare_dracula_candidate as dracula


def dracula_args(**overrides):
    values = {
        "source_url": "https://www.gutenberg.org/ebooks/345",
        "source_text_url": "",
        "source_text_file": "",
        "slug": "dracula",
        "title": "Dracula",
        "author": "Bram Stoker",
        "rollback_owner": "Earnalism launch operator",
        "publication_cap": "Dracula controlled-publication candidate only; public_publish_actions=0.",
        "dry_run": True,
    }
    values.update(overrides)
    return Namespace(**values)


def bengali_args(**overrides):
    values = {
        "slug": "kshudhita-pashan",
        "source_url": bengali.SOURCE_URL,
        "source_text_file": "",
        "allow_fetch": False,
        "dry_run": True,
    }
    values.update(overrides)
    return Namespace(**values)


def bengali_source_fixture() -> str:
    paragraph = (
        "ক্ষুধিত পাষাণ। “মেহের আলি বলিল, তফাৎ যাও।” "
        "প্রাসাদের নীরব বারান্দায় বাতাস থামিয়া গেল, আর অদৃশ্য কণ্ঠে এক দীর্ঘ নিশ্বাস বাজিল। "
        "শুস্তা নদীর ধারে সন্ধ্যার আলো পড়িতে পড়িতে মনে হইল, পাথরের দেওয়াল যেন অতীতের কথা শুনিতেছে।"
    )
    return "\n".join(
        [
            "রবীন্দ্রনাথ ঠাকুর",
            "গল্প-দশক",
            "১৮৯৫",
            "ক্ষুধিত পাষাণ",
            *[paragraph for _ in range(72)],
        ]
    )


def test_dracula_candidate_blocks_without_local_source_or_fetch(monkeypatch):
    monkeypatch.delenv("EARNALISM_ALLOW_SOURCE_FETCH", raising=False)

    evidence = dracula.build_source_evidence(dracula_args())
    gate_results = dracula.build_gate_results(evidence)

    assert evidence["slug"] == "dracula"
    assert evidence["load_status"] == "BLOCKED_SOURCE_TEXT_REQUIRED"
    assert evidence["source_hash"] == ""
    assert evidence["content_hash"] == ""
    assert evidence["provenance_hash"] == ""
    assert evidence["rights_tier"] == "C"
    assert evidence["verification_status"] == "blocked"
    assert evidence["qa_status"] == "BLOCKED_SOURCE_QA"
    assert gate_results["recommendation"] == "HOLD_FOR_FIXES"
    assert "Dracula lacks approved real source evidence." in gate_results["high_blockers"]


def test_bengali_candidate_blocks_without_source_or_fetch(monkeypatch):
    monkeypatch.delenv("EARNALISM_ALLOW_SOURCE_FETCH", raising=False)

    evidence = bengali.build_source_evidence(bengali_args())

    assert evidence["slug"] == "kshudhita-pashan"
    assert evidence["load_status"] == "BLOCKED_SOURCE_TEXT_REQUIRED"
    assert evidence["source_hash"] == ""
    assert evidence["content_hash"] == ""
    assert evidence["provenance_hash"] == ""
    assert evidence["rights_tier"] == "C"
    assert evidence["verification_status"] == "blocked"
    assert evidence["qa_status"] == "BLOCKED_SOURCE_QA"


def test_bengali_candidate_uses_real_metadata_without_committing_full_source(tmp_path, monkeypatch):
    source_file = tmp_path / "kshudhita-source.txt"
    source_file.write_text(bengali_source_fixture(), encoding="utf-8")
    monkeypatch.setattr(
        bengali,
        "load_source_license",
        lambda *, allow_fetch: {
            "text": "Creative Commons Attribution-Share Alike 4.0",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/deed.bn",
        },
    )
    monkeypatch.setattr(bengali, "ROOT", tmp_path)
    monkeypatch.setattr(bengali, "DATA_DIR", tmp_path / "data" / "publication_candidates")
    monkeypatch.setattr(bengali, "OUTPUT_DIR", tmp_path / "output" / "publication_candidates" / "kshudhita-pashan")

    evidence = bengali.build_source_evidence(bengali_args(source_text_file=str(source_file)))
    audio_plan = bengali.build_audio_preview_plan(evidence)
    score = bengali.candidate_score(evidence, audio_plan)
    bengali.write_outputs(evidence, audio_plan, score)

    assert evidence["qa_status"] == "QA_PASSED"
    assert evidence["rights_tier"] == "A"
    assert evidence["verification_status"] == "approved"
    assert evidence["source_hash"]
    assert evidence["content_hash"]
    assert evidence["provenance_hash"]
    assert evidence["cleaned_text_omitted"] is True
    assert evidence["full_source_text_committed"] is False
    assert audio_plan["audio_file_created"] is False
    assert audio_plan["production_storage_upload"] is False
    assert audio_plan["audio_preview_status"] == "AUDIO_PREVIEW_BLOCKED_UNTIL_PROVIDER_QA"
    assert audio_plan["full_audiobook_status"] == "BLOCKED_FULL_AUDIO_QA_REQUIRED"
    assert score["recommendation"] == "READY_FOR_AUDIO_PREVIEW_PLANNING"
    assert evidence["source_license_url"] == "https://creativecommons.org/licenses/by-sa/4.0/deed.bn"
    assert evidence["attribution_required"] is True
    assert evidence["share_alike_required"] is True
    assert "Bengali Wikisource" in evidence["attribution_text"]
    assert evidence["license_compliance_status"] == "CC_BY_SA_ATTRIBUTION_SHAREALIKE_REQUIRED"
    assert evidence["qa"]["unicode_normalization_form"] == "NFC"
    assert "hidden_unicode_counts_raw" in evidence["qa"]
    assert "bengali_punctuation_count" in evidence["qa"]["punctuation_preservation"]
    assert "non_bengali_english_quote_count" in evidence["qa"]["punctuation_preservation"]

    source_record = json.loads((tmp_path / "data" / "publication_candidates" / "kshudhita-pashan.source.json").read_text())
    assert "raw_text" not in source_record
    assert "cleaned_text" not in source_record
    assert source_record["attribution_required"] is True
    assert source_record["share_alike_required"] is True
    rights_evidence = json.loads((tmp_path / "output" / "publication_candidates" / "kshudhita-pashan" / "rights_evidence.json").read_text())
    assert rights_evidence["license_compliance_status"] == "CC_BY_SA_ATTRIBUTION_SHAREALIKE_REQUIRED"
    assert rights_evidence["attribution_required"] is True
    assert rights_evidence["share_alike_required"] is True
    assert (tmp_path / "KSHUDHITA_PASHAN_AUDIO_QA_CHECKLIST.md").exists()


def test_bengali_audio_preview_plan_is_metadata_only(tmp_path, monkeypatch):
    source_file = tmp_path / "kshudhita-source.txt"
    source_file.write_text(bengali_source_fixture(), encoding="utf-8")
    monkeypatch.setattr(
        bengali,
        "load_source_license",
        lambda *, allow_fetch: {
            "text": "Creative Commons Attribution-Share Alike 4.0",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/deed.bn",
        },
    )

    evidence = bengali.build_source_evidence(bengali_args(source_text_file=str(source_file)))
    audio_plan = bengali.build_audio_preview_plan(evidence)

    for provider_plan in audio_plan["provider_plans"].values():
        assert provider_plan["dry_run"] is True
        assert provider_plan["pronunciation_guide_attached"] is True
        assert provider_plan["provider_plan"]["dry_run_only"] is True
        assert provider_plan["mastering_plan"]["executed"] is False
        assert provider_plan["planned_audio_assets"]
        assert all(asset["publishable"] is False for asset in provider_plan["planned_audio_assets"])
        assert all("text" not in chunk for chunk in provider_plan["narration_script"]["chunks"])
    assert any(item["requires_human_spot_check"] for item in audio_plan["pronunciation_dictionary"])


def test_dracula_candidate_writes_dry_run_blocker_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(dracula, "DATA_DIR", tmp_path / "data" / "publication_candidates")
    monkeypatch.setattr(dracula, "DRACULA_DATA_DIR", tmp_path / "data" / "publication_candidates" / "dracula")
    monkeypatch.setattr(dracula, "OUTPUT_DIR", tmp_path / "output" / "publication_candidates" / "dracula")
    monkeypatch.setattr(dracula, "LAUNCH_OUTPUT_DIR", tmp_path / "output" / "launch")
    monkeypatch.setattr(dracula, "ROOT", tmp_path)

    evidence = dracula.build_source_evidence(dracula_args())
    gate_results = dracula.build_gate_results(evidence)
    dracula.write_static_reports(evidence, gate_results)

    assert (tmp_path / "data" / "publication_candidates" / "dracula.source.json").exists()
    assert (tmp_path / "output" / "publication_candidates" / "dracula" / "source_evidence.json").exists()
    assert (tmp_path / "DRACULA_SOURCE_RIGHTS_REPORT.md").exists()
    assert (tmp_path / "DRACULA_GATE_RESULTS.md").exists()


def test_approved_builder_writes_blockers_and_removes_stale_approval(tmp_path, monkeypatch):
    candidate = write_builder_context(tmp_path, {"slug": "dracula", "title": "Dracula", "public_publish_actions": 0})
    approved_file = tmp_path / "APPROVED_TO_PUBLISH.md"
    approved_file.write_text("stale approval\n", encoding="utf-8")

    configure_builder(tmp_path, monkeypatch, approved_file=approved_file)

    result = builder.build(
        Namespace(candidate=str(candidate), dry_run=True, evaluate_only=True, write_approval_artifact=False)
    )

    assert result["status"] == "BLOCKED"
    assert not approved_file.exists()
    assert (tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md").exists()
    assert (tmp_path / "CONTROLLED_PUBLICATION_PRECHECK.md").exists()


def complete_candidate():
    return {
        "title": "Dracula",
        "slug": "dracula",
        "author": "Bram Stoker",
        "author_death_year": 1912,
        "original_publication_year": 1897,
        "source_url": "https://www.gutenberg.org/ebooks/345",
        "source_name": "Project Gutenberg eBook #345",
        "source_license": "Project Gutenberg License",
        "source_hash": "a" * 64,
        "content_hash": "b" * 64,
        "provenance_hash": "c" * 64,
        "rights_basis": "Bram Stoker died in 1912.",
        "rights_tier": "A",
        "verification_status": "approved",
        "publication_region": "global",
        "qa_status": "QA_PASSED",
        "rollback_owner": "Earnalism launch operator",
        "publication_cap": "Dracula only.",
        "rollback_plan": "Disable Dracula draft flag.",
        "public_publish_actions": 0,
        "rights_decision": {"approved": True, "issues": []},
        "ingestion": {
            "source_hash": "a" * 64,
            "content_hash": "b" * 64,
            "provenance_hash": "c" * 64,
        },
    }


def ready_gate_results(**overrides):
    gate = {
        "publishing_workflow_status": "READY_FOR_PUBLICATION_DRAFT_CANDIDATE",
        "workflow": {"blockers": [], "publish_readiness": "READY"},
        "recommendation": builder.GO_RECOMMENDATION,
        "high_blockers": [],
        "readiness_score": 9.9,
    }
    gate.update(overrides)
    return gate


def source_hashes(candidate: dict):
    return {
        "source_hash": candidate["source_hash"],
        "content_hash": candidate["content_hash"],
        "provenance_hash": candidate["provenance_hash"],
    }


def write_builder_context(
    tmp_path: Path,
    candidate: dict,
    *,
    gate_results: dict | None = None,
    source_hash_payload: dict | None = None,
) -> Path:
    output_dir = tmp_path / "output" / "publication_candidates" / "dracula"
    launch_output = tmp_path / "output" / "launch"
    output_dir.mkdir(parents=True)
    launch_output.mkdir(parents=True)
    candidate_path = output_dir / "source_evidence.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    (output_dir / "dracula_gate_results.json").write_text(
        json.dumps(gate_results or ready_gate_results()),
        encoding="utf-8",
    )
    (output_dir / "source_hashes.json").write_text(
        json.dumps(source_hash_payload or source_hashes(candidate) if candidate.get("source_hash") else {}),
        encoding="utf-8",
    )
    (launch_output / "post_deploy_route_canary.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    (launch_output / "payment_smoke.json").write_text('{"status":"PASS_TEST_MODE"}\n', encoding="utf-8")
    return candidate_path


def configure_builder(tmp_path: Path, monkeypatch, *, approved_file: Path | None = None) -> None:
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "APPROVED_FILE", approved_file or tmp_path / "APPROVED_TO_PUBLISH.md")
    monkeypatch.setattr(builder, "BLOCKERS_FILE", tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md")
    monkeypatch.setattr(builder, "PRECHECK_REPORT", tmp_path / "CONTROLLED_PUBLICATION_PRECHECK.md")
    monkeypatch.setattr(builder, "OUTPUT_DIR", tmp_path / "output" / "publication_candidates" / "dracula")
    monkeypatch.setattr(builder, "LAUNCH_OUTPUT_DIR", tmp_path / "output" / "launch")


def test_approved_builder_evaluates_complete_candidate_shape():
    candidate = complete_candidate()

    assert builder.evaluate_candidate(candidate) == []

    bad = dict(candidate)
    bad["source_hash"] = ""
    assert "source_hash is required." in builder.evaluate_candidate(bad)


def test_approved_builder_evaluate_only_does_not_write_approval_for_passing_candidate(tmp_path, monkeypatch):
    candidate_path = write_builder_context(tmp_path, complete_candidate())
    configure_builder(tmp_path, monkeypatch)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=True, write_approval_artifact=False)
    )

    assert result["status"] == "PASS_EVALUATE_ONLY"
    assert result["evidence_passes"] is True
    assert not (tmp_path / "APPROVED_TO_PUBLISH.md").exists()
    assert (tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md").exists()


def test_approved_builder_write_mode_requires_env_flag(tmp_path, monkeypatch):
    candidate_path = write_builder_context(tmp_path, complete_candidate())
    monkeypatch.delenv("EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE", raising=False)
    configure_builder(tmp_path, monkeypatch)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=False, write_approval_artifact=True)
    )

    assert result["status"] == "BLOCKED_APPROVAL_WRITE_DISABLED"
    assert not (tmp_path / "APPROVED_TO_PUBLISH.md").exists()


def test_approved_builder_write_mode_writes_approval_with_env_flag(tmp_path, monkeypatch):
    candidate_path = write_builder_context(tmp_path, complete_candidate())
    monkeypatch.setenv("EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE", "true")
    configure_builder(tmp_path, monkeypatch)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=False, write_approval_artifact=True)
    )

    assert result["status"] == "PASS_APPROVAL_ARTIFACT_WRITTEN"
    assert result["approval_artifact_written"] is True
    assert (tmp_path / "APPROVED_TO_PUBLISH.md").exists()


def test_approved_builder_refuses_blocked_workflow_and_removes_stale_approval(tmp_path, monkeypatch):
    blocked_gate = ready_gate_results(
        publishing_workflow_status="BLOCKED",
        workflow={"blockers": ["Rights verification must be approved."], "publish_readiness": "BLOCKED"},
    )
    candidate_path = write_builder_context(tmp_path, complete_candidate(), gate_results=blocked_gate)
    approved_file = tmp_path / "APPROVED_TO_PUBLISH.md"
    approved_file.write_text("stale approval\n", encoding="utf-8")
    configure_builder(tmp_path, monkeypatch, approved_file=approved_file)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=True, write_approval_artifact=False)
    )

    assert result["status"] == "BLOCKED"
    assert not approved_file.exists()
    assert any("publishing_workflow_status" in issue for issue in result["issues"])


def test_approved_builder_blocks_hash_mismatch(tmp_path, monkeypatch):
    candidate = complete_candidate()
    mismatched_hashes = source_hashes(candidate)
    mismatched_hashes["content_hash"] = "z" * 64
    candidate_path = write_builder_context(tmp_path, candidate, source_hash_payload=mismatched_hashes)
    configure_builder(tmp_path, monkeypatch)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=True, write_approval_artifact=False)
    )

    assert result["status"] == "BLOCKED"
    assert any("content_hash mismatch" in issue for issue in result["issues"])


def test_approved_artifact_uses_relative_paths_and_limited_scope(tmp_path, monkeypatch):
    candidate_path = write_builder_context(tmp_path, complete_candidate())
    monkeypatch.setenv("EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE", "true")
    configure_builder(tmp_path, monkeypatch)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=False, write_approval_artifact=True)
    )
    approval = (tmp_path / "APPROVED_TO_PUBLISH.md").read_text(encoding="utf-8")

    assert result["status"] == "PASS_APPROVAL_ARTIFACT_WRITTEN"
    assert str(tmp_path) not in approval
    assert "output/launch/post_deploy_route_canary.json" in approval
    assert "output/publication_candidates/dracula/source_evidence.json" in approval
    assert "Approved Scope: Dracula core reading candidate only." in approval
    assert "Not Approved: full study guide, full visual edition, full audiobook" in approval
    assert "Audiobook Status: AUDIO_NOT_REQUIRED." in approval


def test_meaningful_chapter_count_excludes_empty_toc_segments():
    chapters = [
        type("Segment", (), {"content": ""})(),
        type("Segment", (), {"content": "Chapter I"})(),
        type("Segment", (), {"content": "word " * 250})(),
        type("Segment", (), {"content": "x" * 1200})(),
    ]

    assert dracula.meaningful_chapter_count(chapters) == 2


def test_source_qa_blocks_when_meaningful_chapter_count_is_too_low():
    status, issues = dracula.source_qa_status(
        raw_text="x" * (dracula.MIN_RAW_CHARACTERS + 1),
        cleaned_text="x" * (dracula.MIN_CLEANED_CHARACTERS + 1),
        source_license="Project Gutenberg License",
        chapter_count=54,
        meaningful_chapters=24,
        source_hash="a" * 64,
        content_hash="b" * 64,
        provenance_hash="c" * 64,
        load_status="FETCHED_SOURCE_TEXT_WITH_EXPLICIT_OPT_IN",
        marker_evidence={name: True for name in dracula.REQUIRED_SOURCE_MARKERS},
    )

    assert status == "BLOCKED_SOURCE_QA"
    assert any("meaningful Dracula chapters" in issue for issue in issues)
