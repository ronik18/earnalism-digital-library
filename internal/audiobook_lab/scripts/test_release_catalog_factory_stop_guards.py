#!/usr/bin/env python3
"""Regression checks for release catalog stop-guard counters."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from release_catalog_factory import (
    BookState,
    build_auto_qa,
    catalog_counter_snapshot,
    reconcile_newer_passed_stage_results,
    write_json,
    stop_after_attempted_counter_value,
)


def make_state(index: int) -> BookState:
    return BookState(
        slug=f"book-{index:04d}",
        title=f"Book {index}",
        author="Earnalism",
        language="eng",
        order=index,
        catalog_dir=Path("/tmp/catalog-stop-guard-test"),
        run_dir=Path(f"/tmp/catalog-stop-guard-test/book-{index:04d}"),
    )


def assert_inventory_only_does_not_count_as_attempted() -> None:
    states = []
    for index in range(10):
        state = make_state(index)
        state.inventory_seen = True
        state.stage_results["inventory_queue"] = {"status": "PASS"}
        states.append(state)
    counters = catalog_counter_snapshot(states)
    assert counters["inventory_seen_count"] == 10, counters
    assert counters["book_attempted_count"] == 0, counters
    assert stop_after_attempted_counter_value(states) == 0, counters


def assert_real_stage_counts_once_per_book() -> None:
    states = [make_state(index) for index in range(3)]
    states[0].mark_stage_started("cover_queue")
    states[1].mark_stage_started("tts_queue")
    states[2].stage_results["cover_queue"] = {"status": "PASS"}
    counters = catalog_counter_snapshot(states)
    assert counters["book_attempted_count"] == 3, counters
    assert stop_after_attempted_counter_value(states) == 3, counters


def assert_newer_passed_asr_result_clears_stale_terminal_block() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state = BookState(
            slug="book-2b9853ec52",
            title="দুই বিঘা জমি",
            author="রবীন্দ্রনাথ ঠাকুর",
            language="ben",
            order=1,
            catalog_dir=root / "catalog",
            run_dir=root / "book-2b9853ec52",
        )
        state.stage_results["asr_sync_queue"] = {
            "status": "BLOCKED",
            "retryable": False,
            "blocker_category": "bengali_audio_manuscript_mismatch",
            "blockers": ["stale ASR mismatch"],
        }
        state.add_blocker("bengali_audio_manuscript_mismatch", "stale ASR mismatch")
        state.terminal_status = "TERMINAL_BLOCKED_WITH_EVIDENCE"
        state.terminal_at = "2026-07-07T05:36:16Z"
        state.save()

        result_path = state.run_dir / "stage_result.json"
        write_json(
            result_path,
            {
                "stage": "asr_sync",
                "status": "PASS",
                "ready_for_next_stage": True,
                "blocker_category": "none",
                "blockers": [],
                "metrics": {
                    "tts_by_construction_verified": True,
                    "sync_release_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
                    "auto_estimated_sync": False,
                },
            },
        )
        os.utime(result_path, None)

        assert reconcile_newer_passed_stage_results(state) is True
        assert state.stage_results["asr_sync_queue"]["status"] == "PASS", state.stage_results
        assert state.blockers == [], state.blockers
        assert state.terminal_status == "", state.terminal_status
        assert state.terminal_at == "", state.terminal_at
        assert state.next_stage == "qa_queue", state.next_stage


def make_bengali_qa_state(
    root: Path,
    *,
    mechanical_cadence_detected: bool = False,
    overall_listening_score: float = 9.4,
    listening_confidence_score: float = 0.95,
    auto_estimated_sync: bool = False,
    rights_metadata_ready: bool = True,
    frontmatter_in_body_detected: bool = False,
) -> BookState:
    state = BookState(
        slug="book-2b9853ec52",
        title="দুই বিঘা জমি",
        author="রবীন্দ্রনাথ ঠাকুর",
        language="ben",
        order=1,
        catalog_dir=root / "catalog",
        run_dir=root / "book-2b9853ec52",
    )
    state.stage_results["cover_queue"] = {"status": "PASS"}
    state.stage_results["manuscript_queue"] = {"status": "PASS"}
    state.stage_results["rights_metadata_preflight_queue"] = {
        "status": "PASS",
        "production_metadata_ready": rights_metadata_ready,
    }
    state.stage_results["tts_queue"] = {
        "status": "PASS",
        "fallback_tts_used": False,
        "metrics": {
            "fallback_tts_used": False,
            "local_audio_reused": False,
            "stale_audio_reused": False,
        },
    }
    audio_quality_scores = {
        "listening_sample_count": 6,
        "dialogue_emotional_sections_judged": True,
        "naturalness_score": 9.5,
        "narration_naturalness_score": 9.5,
        "pronunciation_score": 9.6,
        "bengali_pronunciation_score": 9.6,
        "emotional_expression_score": 9.4,
        "punctuation_pause_score": 9.3,
        "pacing_score": 9.2,
        "continuity_score": 9.4,
        "anti_robotic_texture_score": 9.6,
        "robotic_cadence_absence_score": 9.6,
        "mechanical_texture_absence_score": 9.6,
        "list_reading_absence_score": 10.0,
        "anti_choppy_join_score": 9.6,
        "choppy_join_absence_score": 9.6,
        "listener_enjoyment_score": 9.4,
        "overall_listening_score": overall_listening_score,
        "listening_confidence_score": listening_confidence_score,
        "no_robotic_cadence": True,
        "mechanical_texture_detected": mechanical_cadence_detected,
        "list_reading_rhythm_detected": False,
        "choppy_joins_detected": False,
        "repeated_identical_sentence_endings_detected": False,
        "abrupt_tts_resets_detected": False,
        "placeholder_audio_used": False,
        "fallback_tts_used": False,
    }
    state.stage_results["asr_sync_queue"] = {
        "status": "PASS",
        "transcript_match_score": 10.0,
        "sync_score": 10.0,
        "vtt_alignment_score": 10.0,
        "auto_estimated_sync": auto_estimated_sync,
        "metrics": {
            "transcript_match_score": 10.0,
            "sync_score": 10.0,
            "vtt_alignment_score": 10.0,
            "auto_estimated_sync": auto_estimated_sync,
            "sync_release_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "source_verification_method": "clean_tts_source_provenance_static_audit",
            "tts_by_construction_verified": True,
            "audio_quality_scores": audio_quality_scores,
        },
    }
    write_json(
        state.run_dir / "content_integrity_report.json",
        {
            "content_integrity_score": 10.0,
            "completeness_score": 10.0,
            "index_integrity_score": 10.0,
            "chapter_consistency_score": 10.0,
            "toc_links_valid": True,
            "missing_chapters": [],
            "duplicate_chapters": [],
            "broken_toc_links": [],
            "body_junk_detected": False,
            "frontmatter_in_body_detected": frontmatter_in_body_detected,
        },
    )
    write_json(state.run_dir / "rights_metadata_report.json", {"production_metadata_ready": rights_metadata_ready})
    return state


def assert_bengali_92_policy_allows_clean_full_pilot_qa() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = make_bengali_qa_state(Path(tmp))
        qa = build_auto_qa(
            state,
            {"EARNALISM_LISTENING_POLICY_VERSION": True},
            "release_catalog_factory.py --policy bengali_audiobook_acceptance_v2_92",
            phase="pre_upload",
        )
        assert qa["auto_approval_decision"] is True, qa["blocker_list"]
        assert qa["scores"]["overall_listening_score"] == 9.4, qa["scores"]
        assert qa["scores"]["listening_confidence_score"] == 0.95, qa["scores"]
        assert qa["scores"]["overall_premium_score"] >= 9.2, qa["scores"]
        assert qa["scores"]["confidence_score"] >= 0.90, qa["scores"]


def assert_bengali_92_policy_blocks_fatal_listening_flags() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = make_bengali_qa_state(Path(tmp), mechanical_cadence_detected=True)
        qa = build_auto_qa(
            state,
            {"EARNALISM_LISTENING_POLICY_VERSION": True},
            "release_catalog_factory.py --policy bengali_audiobook_acceptance_v2_92",
            phase="pre_upload",
        )
        assert qa["auto_approval_decision"] is False, qa
        assert any("no_mechanical_texture failed" in blocker for blocker in qa["blocker_list"]), qa["blocker_list"]


def assert_bengali_92_policy_blocks_low_listening_score() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = make_bengali_qa_state(Path(tmp), overall_listening_score=9.19)
        qa = build_auto_qa(
            state,
            {"EARNALISM_LISTENING_POLICY_VERSION": True},
            "release_catalog_factory.py --policy bengali_audiobook_acceptance_v2_92",
            phase="pre_upload",
        )
        assert qa["auto_approval_decision"] is False, qa
        assert any("overall_listening_score below threshold" in blocker for blocker in qa["blocker_list"]), qa["blocker_list"]


def assert_bengali_92_policy_blocks_objective_gate_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = make_bengali_qa_state(Path(tmp), rights_metadata_ready=False)
        qa = build_auto_qa(
            state,
            {"EARNALISM_LISTENING_POLICY_VERSION": True},
            "release_catalog_factory.py --policy bengali_audiobook_acceptance_v2_92",
            phase="pre_upload",
        )
        assert qa["auto_approval_decision"] is False, qa
        assert any("rights_metadata_score below threshold" in blocker for blocker in qa["blocker_list"]), qa["blocker_list"]
        assert any("rights_metadata_ready failed" in blocker for blocker in qa["blocker_list"]), qa["blocker_list"]


def assert_bengali_92_policy_blocks_estimated_sync() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = make_bengali_qa_state(Path(tmp), auto_estimated_sync=True)
        qa = build_auto_qa(
            state,
            {"EARNALISM_LISTENING_POLICY_VERSION": True},
            "release_catalog_factory.py --policy bengali_audiobook_acceptance_v2_92",
            phase="pre_upload",
        )
        assert qa["auto_approval_decision"] is False, qa
        assert any("auto_estimated_sync_false failed" in blocker for blocker in qa["blocker_list"]), qa["blocker_list"]


def assert_bengali_92_policy_blocks_frontmatter_contamination() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state = make_bengali_qa_state(Path(tmp), frontmatter_in_body_detected=True)
        qa = build_auto_qa(
            state,
            {"EARNALISM_LISTENING_POLICY_VERSION": True},
            "release_catalog_factory.py --policy bengali_audiobook_acceptance_v2_92",
            phase="pre_upload",
        )
        assert qa["auto_approval_decision"] is False, qa
        assert any("frontmatter_removal_score below threshold" in blocker for blocker in qa["blocker_list"]), qa["blocker_list"]


def main() -> int:
    assert_inventory_only_does_not_count_as_attempted()
    assert_real_stage_counts_once_per_book()
    assert_newer_passed_asr_result_clears_stale_terminal_block()
    assert_bengali_92_policy_allows_clean_full_pilot_qa()
    assert_bengali_92_policy_blocks_fatal_listening_flags()
    assert_bengali_92_policy_blocks_low_listening_score()
    assert_bengali_92_policy_blocks_objective_gate_failure()
    assert_bengali_92_policy_blocks_estimated_sync()
    assert_bengali_92_policy_blocks_frontmatter_contamination()
    print("release_catalog_factory stop-guard regression checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
