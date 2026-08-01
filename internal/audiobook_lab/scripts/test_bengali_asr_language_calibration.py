#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "bengali_asr_language_calibration.py"
SPEC = importlib.util.spec_from_file_location("bengali_asr_language_calibration", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def manifest() -> dict:
    return {
        "slug": "bn-066",
        "chunks": [
            {"index": 0, "path": "opening.wav", "duration_seconds": 100, "text": "শুরু"},
            {"index": 76, "path": "middle.wav", "duration_seconds": 80, "text": "মাঝ"},
            {"index": 151, "path": "ending.wav", "duration_seconds": 50, "text": "শেষ"},
        ],
    }


def passing_env() -> dict[str, str]:
    return {
        "MAX_TTS_BUDGET_USD": "1",
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
        "EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD": "0.25",
        "EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE": "0.008",
        "OPENAI_API_KEY": "present-not-real",
    }


def passing_lock() -> dict:
    return {
        "status": "active",
        "current_holder": MODULE.EXPECTED_HOLDER,
        "allowed_slugs": ["bn-066"],
    }


def test_three_chunk_plan_is_bounded() -> None:
    plan = MODULE.build_plan(manifest(), ["group_0000", "group_0076", "group_0151"], ["auto", "bn", "ben"])
    assert [item["chunk_id"] for item in plan["selected_chunks"]] == ["group_0000", "group_0076", "group_0151"]
    assert plan["planned_provider_calls"] == 5
    assert plan["estimated_cost_usd"] > 0


def test_missing_budget_and_key_block_provider_calls() -> None:
    plan = MODULE.build_plan(manifest(), ["group_0000", "group_0076", "group_0151"], ["auto"])
    guard = MODULE.preflight(plan, environ={}, lock=passing_lock())
    assert guard["status"] == "BLOCKED"
    assert guard["provider_calls_allowed"] is False
    assert any("MAX_TTS_BUDGET_USD" in item for item in guard["blockers"])
    assert any("OPENAI_API_KEY" in item for item in guard["blockers"])


def test_lock_must_be_narrowly_held() -> None:
    plan = MODULE.build_plan(manifest(), ["group_0000", "group_0076", "group_0151"], ["auto"], passing_env())
    lock = {"status": "active", "current_holder": "none", "allowed_slugs": []}
    guard = MODULE.preflight(plan, environ=passing_env(), lock=lock)
    assert guard["provider_calls_allowed"] is False
    assert any("current_holder" in item for item in guard["blockers"])


def test_estimate_over_asr_cap_blocks() -> None:
    env = passing_env()
    env["EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD"] = "0.001"
    plan = MODULE.build_plan(manifest(), ["group_0000", "group_0076", "group_0151"], ["auto", "bn"], env)
    guard = MODULE.preflight(plan, environ=env, lock=passing_lock())
    assert guard["provider_calls_allowed"] is False
    assert any("exceeds EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD" in item for item in guard["blockers"])


def test_valid_caps_and_lock_allow_calibration() -> None:
    env = passing_env()
    plan = MODULE.build_plan(manifest(), ["group_0000", "group_0076", "group_0151"], ["auto", "bn"], env)
    guard = MODULE.preflight(plan, environ=env, lock=passing_lock())
    assert guard["status"] == "PASS"
    assert guard["provider_calls_allowed"] is True


def test_best_result_prefers_bengali_script_then_alignment() -> None:
    results = [
        {
            "status": "PASS",
            "language_option": "auto",
            "transcript_chars": 100,
            "script_profile": {"ratios": {"bengali": 0.4}},
            "alignment": {"score": 9.0},
        },
        {
            "status": "PASS",
            "language_option": "bn",
            "transcript_chars": 80,
            "script_profile": {"ratios": {"bengali": 0.95}},
            "alignment": {"score": 7.5},
        },
    ]
    assert MODULE.best_opening_result(results)["language_option"] == "bn"


if __name__ == "__main__":
    test_three_chunk_plan_is_bounded()
    test_missing_budget_and_key_block_provider_calls()
    test_lock_must_be_narrowly_held()
    test_estimate_over_asr_cap_blocks()
    test_valid_caps_and_lock_allow_calibration()
    test_best_result_prefers_bengali_script_then_alignment()
    print("bengali ASR language calibration tests: PASS")
