from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from scripts import approved_to_publish_builder as builder
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
    candidate = tmp_path / "source_evidence.json"
    candidate.write_text('{"slug":"dracula","title":"Dracula","public_publish_actions":0}\n', encoding="utf-8")
    launch_output = tmp_path / "output" / "launch"
    launch_output.mkdir(parents=True)
    (launch_output / "post_deploy_route_canary.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    (launch_output / "payment_smoke.json").write_text('{"status":"PASS_TEST_MODE"}\n', encoding="utf-8")
    approved_file = tmp_path / "APPROVED_TO_PUBLISH.md"
    approved_file.write_text("stale approval\n", encoding="utf-8")

    monkeypatch.setattr(builder, "APPROVED_FILE", approved_file)
    monkeypatch.setattr(builder, "BLOCKERS_FILE", tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md")
    monkeypatch.setattr(builder, "PRECHECK_REPORT", tmp_path / "CONTROLLED_PUBLICATION_PRECHECK.md")
    monkeypatch.setattr(builder, "OUTPUT_DIR", tmp_path / "output" / "publication_candidates" / "dracula")
    monkeypatch.setattr(builder, "LAUNCH_OUTPUT_DIR", launch_output)

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
    }


def test_approved_builder_evaluates_complete_candidate_shape():
    candidate = complete_candidate()

    assert builder.evaluate_candidate(candidate) == []

    bad = dict(candidate)
    bad["source_hash"] = ""
    assert "source_hash is required." in builder.evaluate_candidate(bad)


def test_approved_builder_evaluate_only_does_not_write_approval_for_passing_candidate(tmp_path, monkeypatch):
    candidate_path = tmp_path / "source_evidence.json"
    candidate_path.write_text(json.dumps(complete_candidate()), encoding="utf-8")
    launch_output = tmp_path / "output" / "launch"
    launch_output.mkdir(parents=True)
    (launch_output / "post_deploy_route_canary.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    (launch_output / "payment_smoke.json").write_text('{"status":"PASS_TEST_MODE"}\n', encoding="utf-8")

    monkeypatch.setattr(builder, "APPROVED_FILE", tmp_path / "APPROVED_TO_PUBLISH.md")
    monkeypatch.setattr(builder, "BLOCKERS_FILE", tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md")
    monkeypatch.setattr(builder, "PRECHECK_REPORT", tmp_path / "CONTROLLED_PUBLICATION_PRECHECK.md")
    monkeypatch.setattr(builder, "OUTPUT_DIR", tmp_path / "output" / "publication_candidates" / "dracula")
    monkeypatch.setattr(builder, "LAUNCH_OUTPUT_DIR", launch_output)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=True, write_approval_artifact=False)
    )

    assert result["status"] == "PASS_EVALUATE_ONLY"
    assert result["evidence_passes"] is True
    assert not (tmp_path / "APPROVED_TO_PUBLISH.md").exists()
    assert (tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md").exists()


def test_approved_builder_write_mode_requires_env_flag(tmp_path, monkeypatch):
    candidate_path = tmp_path / "source_evidence.json"
    candidate_path.write_text(json.dumps(complete_candidate()), encoding="utf-8")
    launch_output = tmp_path / "output" / "launch"
    launch_output.mkdir(parents=True)
    (launch_output / "post_deploy_route_canary.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    (launch_output / "payment_smoke.json").write_text('{"status":"PASS_TEST_MODE"}\n', encoding="utf-8")

    monkeypatch.delenv("EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE", raising=False)
    monkeypatch.setattr(builder, "APPROVED_FILE", tmp_path / "APPROVED_TO_PUBLISH.md")
    monkeypatch.setattr(builder, "BLOCKERS_FILE", tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md")
    monkeypatch.setattr(builder, "PRECHECK_REPORT", tmp_path / "CONTROLLED_PUBLICATION_PRECHECK.md")
    monkeypatch.setattr(builder, "OUTPUT_DIR", tmp_path / "output" / "publication_candidates" / "dracula")
    monkeypatch.setattr(builder, "LAUNCH_OUTPUT_DIR", launch_output)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=False, write_approval_artifact=True)
    )

    assert result["status"] == "BLOCKED_APPROVAL_WRITE_DISABLED"
    assert not (tmp_path / "APPROVED_TO_PUBLISH.md").exists()


def test_approved_builder_write_mode_writes_approval_with_env_flag(tmp_path, monkeypatch):
    candidate_path = tmp_path / "source_evidence.json"
    candidate_path.write_text(json.dumps(complete_candidate()), encoding="utf-8")
    launch_output = tmp_path / "output" / "launch"
    launch_output.mkdir(parents=True)
    (launch_output / "post_deploy_route_canary.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    (launch_output / "payment_smoke.json").write_text('{"status":"PASS_TEST_MODE"}\n', encoding="utf-8")

    monkeypatch.setenv("EARNALISM_ALLOW_APPROVAL_ARTIFACT_WRITE", "true")
    monkeypatch.setattr(builder, "APPROVED_FILE", tmp_path / "APPROVED_TO_PUBLISH.md")
    monkeypatch.setattr(builder, "BLOCKERS_FILE", tmp_path / "APPROVED_TO_PUBLISH_BLOCKERS.md")
    monkeypatch.setattr(builder, "PRECHECK_REPORT", tmp_path / "CONTROLLED_PUBLICATION_PRECHECK.md")
    monkeypatch.setattr(builder, "OUTPUT_DIR", tmp_path / "output" / "publication_candidates" / "dracula")
    monkeypatch.setattr(builder, "LAUNCH_OUTPUT_DIR", launch_output)

    result = builder.build(
        Namespace(candidate=str(candidate_path), dry_run=True, evaluate_only=False, write_approval_artifact=True)
    )

    assert result["status"] == "PASS_APPROVAL_ARTIFACT_WRITTEN"
    assert result["approval_artifact_written"] is True
    assert (tmp_path / "APPROVED_TO_PUBLISH.md").exists()
