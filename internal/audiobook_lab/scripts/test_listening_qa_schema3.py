#!/usr/bin/env python3
"""Regression checks for schema-3 listening QA validation."""

from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
HOOK_DIR = SCRIPTS_DIR / "factory_hooks"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(HOOK_DIR))

from asr_sync_hook import (  # noqa: E402
    BENGALI_AUDIOBOOK_92_POLICY,
    BENGALI_PREMIUM_MVP_POLICY,
    evaluate_listening_evidence,
    validate_bengali_mvp_hard_gates,
    validate_listening_quality_report,
)
from bengali_tts_provider_bakeoff import ProviderVoice, summarize_voice  # noqa: E402


EXPECTED_HASH = "a" * 64


def pass_report() -> dict:
    samples = [
        {
            "sample_label": label,
            "start_time": index * 60,
            "duration": 60,
            "sample_audio_path": f"sample_{index}.mp3",
            "sample_audio_hash": "b" * 64,
            "scores": {},
            "confidence": 0.99,
            "notes": "pass",
            "blocker_reason": "",
        }
        for index, label in enumerate(["first_60s", "middle_60s", "final_60s", "random_1", "random_2", "random_3"], 1)
    ]
    return {
        "qa_schema_version": 3,
        "rubric_version": "earnalism_listening_quality_v1",
        "audio_judge_hook_version": "asr_sync_hook_listening_schema3_v1",
        "language": "eng",
        "audio_hash": EXPECTED_HASH,
        "listening_quality": {
            "status": "PASS",
            "model_or_judge": "test",
            "audio_hash": EXPECTED_HASH,
            "samples": samples,
            "aggregate": {
                "naturalness_score": 9.8,
                "pronunciation_score": 9.8,
                "emotional_expression_score": 9.8,
                "punctuation_pause_score": 9.8,
                "pacing_score": 9.8,
                "continuity_score": 9.8,
                "anti_robotic_texture_score": 9.8,
                "anti_choppy_join_score": 9.8,
                "listener_enjoyment_score": 9.8,
                "overall_listening_score": 9.8,
                "confidence_score": 0.96,
            },
            "robotic_texture_detected": False,
            "mechanical_cadence_detected": False,
            "choppy_joins_detected": False,
            "fallback_tts_detected": False,
            "list_reading_rhythm_detected": False,
            "repeated_identical_sentence_endings_detected": False,
            "abrupt_tts_resets_detected": False,
            "placeholder_audio_detected": False,
            "dialogue_emotional_sections_judged": True,
            "blockers": [],
        },
    }


def assert_missing_schema_blocks() -> None:
    valid, blockers = validate_listening_quality_report({}, expected_audio_hash=EXPECTED_HASH, language="eng")
    assert not valid
    assert any("LISTENING_QA_SCHEMA_MISSING" in item for item in blockers), blockers


def assert_complete_schema_passes() -> None:
    valid, blockers = validate_listening_quality_report(pass_report(), expected_audio_hash=EXPECTED_HASH, language="eng")
    assert valid, blockers


def assert_robotic_sample_blocks() -> None:
    report = pass_report()
    report["listening_quality"]["robotic_texture_detected"] = True
    valid, blockers = validate_listening_quality_report(report, expected_audio_hash=EXPECTED_HASH, language="eng")
    assert not valid
    assert any("robotic_texture_detected" in item for item in blockers), blockers


def assert_old_schema_or_hash_blocks() -> None:
    report = pass_report()
    report["qa_schema_version"] = 2
    valid, blockers = validate_listening_quality_report(report, expected_audio_hash=EXPECTED_HASH, language="eng")
    assert not valid
    assert any("qa_schema_version 3" in item for item in blockers), blockers
    report = pass_report()
    valid, blockers = validate_listening_quality_report(report, expected_audio_hash="c" * 64, language="eng")
    assert not valid
    assert any("audio hash" in item.lower() for item in blockers), blockers
    report = pass_report()
    report["rubric_version"] = "old"
    valid, blockers = validate_listening_quality_report(report, expected_audio_hash=EXPECTED_HASH, language="eng")
    assert not valid
    assert any("rubric version" in item.lower() for item in blockers), blockers
    report = pass_report()
    report["language"] = "ben"
    valid, blockers = validate_listening_quality_report(report, expected_audio_hash=EXPECTED_HASH, language="eng")
    assert not valid
    assert any("language changed" in item.lower() for item in blockers), blockers


def bengali_mvp_scores() -> dict:
    return {
        "naturalness_score": 9.4,
        "pronunciation_score": 9.4,
        "emotional_expression_score": 9.3,
        "punctuation_pause_score": 9.2,
        "pacing_score": 9.2,
        "continuity_score": 9.4,
        "anti_robotic_texture_score": 9.6,
        "anti_choppy_join_score": 9.6,
        "listener_enjoyment_score": 9.4,
        "overall_listening_score": 9.4,
        "confidence_score": 0.95,
    }


def bengali_92_scores() -> dict:
    return {
        "naturalness_score": 9.0,
        "pronunciation_score": 9.0,
        "emotional_expression_score": 8.9,
        "punctuation_pause_score": 8.9,
        "pacing_score": 8.9,
        "continuity_score": 9.0,
        "anti_robotic_texture_score": 9.3,
        "anti_choppy_join_score": 9.3,
        "listener_enjoyment_score": 9.0,
        "overall_listening_score": 9.2,
        "confidence_score": 0.90,
    }


def clean_flags() -> dict:
    return {
        "robotic_texture_detected": False,
        "mechanical_cadence_detected": False,
        "choppy_joins_detected": False,
        "fallback_tts_detected": False,
        "list_reading_rhythm_detected": False,
        "repeated_identical_sentence_endings_detected": False,
        "abrupt_tts_resets_detected": False,
        "placeholder_audio_detected": False,
    }


def assert_bengali_mvp_policy_passes_ratan_like_scores() -> None:
    valid, blockers, policy = evaluate_listening_evidence(
        bengali_mvp_scores(),
        clean_flags(),
        language="ben",
        release_policy=BENGALI_PREMIUM_MVP_POLICY,
    )
    assert valid, blockers
    assert policy["name"] == BENGALI_PREMIUM_MVP_POLICY


def assert_bengali_mvp_policy_fails_fatal_flags() -> None:
    flags = clean_flags()
    flags["robotic_texture_detected"] = True
    valid, blockers, _ = evaluate_listening_evidence(
        bengali_mvp_scores(),
        flags,
        language="ben",
        release_policy=BENGALI_PREMIUM_MVP_POLICY,
    )
    assert not valid
    assert any("robotic_texture_detected" in item for item in blockers), blockers
    flags = clean_flags()
    flags["fallback_tts_detected"] = True
    valid, blockers, _ = evaluate_listening_evidence(
        bengali_mvp_scores(),
        flags,
        language="ben",
        release_policy=BENGALI_PREMIUM_MVP_POLICY,
    )
    assert not valid
    assert any("fallback_tts_detected" in item for item in blockers), blockers


def assert_bengali_mvp_policy_does_not_apply_to_english() -> None:
    valid, blockers, _ = evaluate_listening_evidence(
        bengali_mvp_scores(),
        clean_flags(),
        language="eng",
        release_policy=BENGALI_PREMIUM_MVP_POLICY,
    )
    assert not valid
    assert any("only available for Bengali" in item for item in blockers), blockers
    valid, blockers, _ = evaluate_listening_evidence(
        bengali_mvp_scores(),
        clean_flags(),
        language="eng",
    )
    assert not valid
    assert any("naturalness_score" in item for item in blockers), blockers


def assert_bengali_92_policy_passes_only_clean_bengali() -> None:
    valid, blockers, policy = evaluate_listening_evidence(
        bengali_92_scores(),
        clean_flags(),
        language="ben",
        release_policy=BENGALI_AUDIOBOOK_92_POLICY,
    )
    assert valid, blockers
    assert policy["name"] == BENGALI_AUDIOBOOK_92_POLICY

    flags = clean_flags()
    flags["list_reading_rhythm_detected"] = True
    valid, blockers, _ = evaluate_listening_evidence(
        bengali_92_scores(),
        flags,
        language="ben",
        release_policy=BENGALI_AUDIOBOOK_92_POLICY,
    )
    assert not valid
    assert any("list_reading_rhythm_detected" in item for item in blockers), blockers

    valid, blockers, _ = evaluate_listening_evidence(
        bengali_92_scores(),
        clean_flags(),
        language="eng",
        release_policy=BENGALI_AUDIOBOOK_92_POLICY,
    )
    assert not valid
    assert any("only available for Bengali" in item for item in blockers), blockers


def hard_gate_pass_payload() -> dict:
    return {
        "transcript_match_score": 9.8,
        "content_integrity_pass": True,
        "rights_metadata_pass": True,
        "cover_qa_pass": True,
        "provider_provenance_pass": True,
        "first_span_match": True,
        "last_span_match": True,
        "no_missing_content": True,
        "no_duplicate_content": True,
        "no_reordered_content": True,
        "upload_checksum_pass": True,
        "metadata_approval_pass": True,
        "browser_playback_pass": True,
        "stale_local_audio_used": False,
        "fallback_tts_used": False,
        "placeholder_audio_used": False,
        "mismatched_audio_used": False,
        "highlight_sync_enabled": False,
    }


def assert_bengali_mvp_hard_gates_fail_asr_and_fallback() -> None:
    valid, blockers = validate_bengali_mvp_hard_gates(hard_gate_pass_payload())
    assert valid, blockers
    payload = hard_gate_pass_payload()
    payload["transcript_match_score"] = 8.0
    valid, blockers = validate_bengali_mvp_hard_gates(payload)
    assert not valid
    assert any("ASR/source match" in item for item in blockers), blockers
    payload = hard_gate_pass_payload()
    payload["fallback_tts_used"] = True
    valid, blockers = validate_bengali_mvp_hard_gates(payload)
    assert not valid
    assert any("fallback_tts_used" in item for item in blockers), blockers


def assert_bengali_mvp_duplicate_passage_ids_can_pass() -> None:
    samples = []
    for index, passage_id in enumerate(["narrative_opening", "dialogue", "punctuation_heavy", "punctuation_heavy"], 1):
        samples.append(
            {
                "provider": "sarvam",
                "voice": "pooja",
                "status": "PASS",
                "passage_id": passage_id,
                "scores": bengali_mvp_scores(),
                "judge_flags": clean_flags(),
                "judge_blockers": [],
            }
        )
    summary = summarize_voice(
        ProviderVoice("sarvam", "pooja"),
        samples,
        release_policy=BENGALI_PREMIUM_MVP_POLICY,
        expected_sample_count=4,
    )
    assert summary["status"] == "PASS", summary


def main() -> int:
    assert_missing_schema_blocks()
    assert_complete_schema_passes()
    assert_robotic_sample_blocks()
    assert_old_schema_or_hash_blocks()
    assert_bengali_mvp_policy_passes_ratan_like_scores()
    assert_bengali_mvp_policy_fails_fatal_flags()
    assert_bengali_mvp_policy_does_not_apply_to_english()
    assert_bengali_92_policy_passes_only_clean_bengali()
    assert_bengali_mvp_hard_gates_fail_asr_and_fallback()
    assert_bengali_mvp_duplicate_passage_ids_can_pass()
    print("listening QA schema 3 regression checks PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
