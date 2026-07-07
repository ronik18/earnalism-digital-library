#!/usr/bin/env python3
"""Regression checks for the Bengali audiobook campaign controller."""

from __future__ import annotations

import tempfile
from pathlib import Path

import bengali_audiobook_campaign_controller as campaign


def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def assert_false(value: bool, message: str) -> None:
    if value:
        raise AssertionError(message)


def test_representative_gate_requires_9_2_and_no_fatal_flags() -> None:
    passed, blockers = campaign.representative_passes(
        {
            "representative_score": 9.2,
            "confidence": 0.9,
            "red_flags": {},
            "passage_scores": [{"passage_id": "opening", "overall_listening_score": 8.9}],
        }
    )
    assert_true(passed, f"expected representative pass, got {blockers}")

    passed, blockers = campaign.representative_passes(
        {
            "representative_score": 9.6,
            "confidence": 0.95,
            "red_flags": {"mechanical_cadence_detected": True},
        }
    )
    assert_false(passed, "fatal flag must block representative pass")
    assert_true(any("mechanical_cadence_detected" in blocker for blocker in blockers), "fatal flag missing from blockers")


def test_full_publish_gate_blocks_estimated_sync_and_missing_objective_gates() -> None:
    passed, blockers = campaign.full_audio_publishable(
        {
            "full_pilot_listening_score": 9.4,
            "confidence": 0.95,
            "asr_score": 9.8,
            "sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "auto_estimated_sync": False,
            "upload_checksum_status": "PASS",
            "metadata_status": "PASS",
            "browser_status": "PASS",
            "blocker_list": [],
        }
    )
    assert_true(passed, f"measured paragraph/stanza sync should pass, got {blockers}")

    passed, blockers = campaign.full_audio_publishable(
        {
            "full_pilot_listening_score": 9.6,
            "confidence": 0.95,
            "asr_score": 9.9,
            "sync_tier": "AUTO_ESTIMATED_SYNC",
            "auto_estimated_sync": True,
            "upload_checksum_status": "PASS",
            "metadata_status": "PASS",
            "browser_status": "PASS",
            "blocker_list": [],
        }
    )
    assert_false(passed, "estimated sync must block publishing")
    assert_true(any("estimated" in blocker for blocker in blockers), "estimated sync blocker missing")


def test_plateau_detection_escalates_after_repeated_bad_material_attempts() -> None:
    attempts = [
        {"provider": "sarvam", "model": "bulbul:v3", "voice": "pooja", "style_profile": "a", "overall_listening_score": 8.0},
        {"provider": "sarvam", "model": "bulbul:v3", "voice": "ratan", "style_profile": "b", "overall_listening_score": 8.1},
        {"provider": "sarvam", "model": "bulbul:v3", "voice": "ritu", "style_profile": "c", "overall_listening_score": 8.05},
    ]
    plateau, reason = campaign.plateau_detected(attempts)
    assert_true(plateau, f"expected plateau, got {reason}")


def test_duplicate_setting_key_includes_style_and_text_hash() -> None:
    first = campaign.setting_key({"provider": "sarvam", "model": "bulbul:v3", "voice": "ratan", "style_profile": "a", "text_hash": "x"})
    second = campaign.setting_key({"provider": "sarvam", "model": "bulbul:v3", "voice": "ratan", "style_profile": "b", "text_hash": "x"})
    assert_true(first != second, "style profile must be part of duplicate-attempt cache key")


def test_scale_requires_one_published_pilot() -> None:
    allowed, reason = campaign.scale_allowed({"published_bengali_audiobooks": 0})
    assert_false(allowed, "31-title scale must not start before one pilot publishes")
    assert_true("pilot" in reason, "expected pilot blocker")


def test_fallback_packets_are_generated_without_audio() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        human = campaign.create_human_narration_packet("book-2b9853ec52", base / "human")
        licensed = campaign.create_licensed_audio_import_packet("book-2b9853ec52", base / "licensed")
        assert_true((human / "narrator_brief.md").exists(), "human narrator brief missing")
        assert_true((licensed / "audio_import_requirements.md").exists(), "licensed import requirements missing")


def main() -> int:
    tests = [
        test_representative_gate_requires_9_2_and_no_fatal_flags,
        test_full_publish_gate_blocks_estimated_sync_and_missing_objective_gates,
        test_plateau_detection_escalates_after_repeated_bad_material_attempts,
        test_duplicate_setting_key_includes_style_and_text_hash,
        test_scale_requires_one_published_pilot,
        test_fallback_packets_are_generated_without_audio,
    ]
    for test in tests:
        test()
    print(f"PASS {len(tests)} Bengali audiobook campaign controller tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
