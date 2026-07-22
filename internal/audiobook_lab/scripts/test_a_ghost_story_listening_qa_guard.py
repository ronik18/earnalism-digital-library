#!/usr/bin/env python3
"""Focused no-provider tests for the A Ghost Story listening-QA path."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HOOK_DIR = ROOT / "internal/audiobook_lab/scripts/factory_hooks"
sys.path[:0] = [str(ROOT / "internal/audiobook_lab/scripts"), str(HOOK_DIR)]

from asr_sync_hook import (  # noqa: E402
    audio_derived_asr_gate,
    existing_sidecar_reuse,
    full_title_paid_budget_guard,
    listening_qa_only,
    openai_listening_qa_budget_guard,
    run_openai_listening_judge,
)
from sprint1_stage2a_a_ghost_story_listening_qa import (  # noqa: E402
    completed_attempt_blocker,
    hook_exit_code,
)


@contextmanager
def temporary_env(**updates):
    previous = {name: os.environ.get(name) for name in updates}
    try:
        for name, value in updates.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class Args:
    slug = "a-ghost-story"
    language = "eng"
    title = "A Ghost Story"
    author = "Mark Twain"


class AStoryListeningQAGuardTests(unittest.TestCase):
    def test_full_title_budget_guard_proves_cumulative_five_dollar_envelope(self) -> None:
        with temporary_env(
            EARNALISM_STOP_ON_BUDGET_EXCEEDED="true",
            EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD="3",
            EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE="0.008",
            EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD="0.75",
            EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD="0.05",
            EARNALISM_FULL_TITLE_CUMULATIVE_MAX_ESTIMATED_USD="5",
        ):
            result = full_title_paid_budget_guard(
                audio_duration_seconds=3600,
                tts_estimated_usd=0.25,
                listening_sample_count=6,
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["cumulative_estimated_usd"], 1.03)
        self.assertEqual(result["cumulative_cap_usd"], 5.0)

    def test_full_title_budget_guard_blocks_before_provider_when_cumulative_cap_exceeded(self) -> None:
        with temporary_env(
            EARNALISM_STOP_ON_BUDGET_EXCEEDED="true",
            EARNALISM_ASR_SYNC_MAX_ESTIMATED_USD="5",
            EARNALISM_ASR_SYNC_ESTIMATED_USD_PER_MINUTE="0.008",
            EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD="1",
            EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD="0.05",
            EARNALISM_FULL_TITLE_CUMULATIVE_MAX_ESTIMATED_USD="0.50",
        ):
            result = full_title_paid_budget_guard(
                audio_duration_seconds=3600,
                tts_estimated_usd=0.25,
                listening_sample_count=6,
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "FULL_TITLE_CUMULATIVE_BUDGET_EXCEEDED")

    def test_audio_derived_asr_gate_cannot_be_replaced_by_construction_score(self) -> None:
        passed, blockers = audio_derived_asr_gate(
            {
                "score": 9.69,
                "coverage": 1.0,
                "token_order_similarity": 1.0,
                "first_words_match": True,
                "last_words_match": True,
                "frontmatter_absent": True,
                "tts_by_construction_verified": True,
                "source_match_score": 10.0,
            },
            word_timestamp_count=100,
        )
        self.assertFalse(passed)
        self.assertTrue(any("score 9.69 < 9.7" in blocker for blocker in blockers))

    def test_audio_derived_asr_gate_accepts_exact_strict_boundary(self) -> None:
        passed, blockers = audio_derived_asr_gate(
            {
                "score": 9.7,
                "coverage": 0.98,
                "token_order_similarity": 0.97,
                "first_words_match": True,
                "last_words_match": True,
                "frontmatter_absent": True,
            },
            word_timestamp_count=1,
        )
        self.assertTrue(passed)
        self.assertEqual(blockers, [])

    def test_budget_guard_blocks_missing_cap(self) -> None:
        with temporary_env(
            EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=None,
            EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD="0.05",
            MAX_TTS_BUDGET_USD="175",
        ):
            result = openai_listening_qa_budget_guard(sample_count=6)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "LISTENING_QA_BUDGET_GATE_MISSING")

    def test_budget_guard_blocks_estimate_over_cap(self) -> None:
        with temporary_env(
            EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD="0.20",
            EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD="0.05",
            MAX_TTS_BUDGET_USD="175",
        ):
            result = openai_listening_qa_budget_guard(sample_count=6)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "LISTENING_QA_BUDGET_EXCEEDED")

    def test_budget_guard_allows_bounded_estimate(self) -> None:
        with temporary_env(
            EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD="2",
            EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD="0.05",
            MAX_TTS_BUDGET_USD="175",
        ):
            result = openai_listening_qa_budget_guard(sample_count=6)
        self.assertTrue(result["ok"])
        self.assertEqual(result["estimated_qa_cost_usd"], 0.3)

    def test_provider_is_not_constructed_before_budget_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw, temporary_env(
            EARNALISM_ENABLE_OPENAI_LISTENING_QA="true",
            OPENAI_API_KEY="test-key-not-used",
            EARNALISM_OPENAI_LISTENING_QA_MAX_ESTIMATED_USD=None,
            EARNALISM_OPENAI_LISTENING_QA_ESTIMATED_USD="0.05",
            MAX_TTS_BUDGET_USD="175",
        ):
            result = run_openai_listening_judge(
                Args(),
                Path(raw) / "not-read.mp3",
                Path(raw),
                [{"sample_label": "one"}],
                "hash",
            )
        self.assertIn("LISTENING_QA_BUDGET_GATE_MISSING", result["_external_judge_error"])

    def test_hash_bound_local_sidecars_are_reused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            audio = run_dir / "candidate.mp3"
            audio.write_bytes(b"validated-private-audio")
            manuscript = "A validated source passage."
            audio_hash = hashlib.sha256(audio.read_bytes()).hexdigest()
            source_hash = hashlib.sha256(manuscript.encode("utf-8")).hexdigest()
            (run_dir / "reused_timestamps.json").write_text(
                json.dumps(
                    {
                        "slug": Args.slug,
                        "words": [{"word": "validated", "start": 0.0, "end": 0.5}],
                        "audio_hash": audio_hash,
                        "source_text_hash": source_hash,
                        "auto_estimated_sync": False,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "reused_vtt.vtt").write_text(
                "WEBVTT\n\n00:00.000 --> 00:00.500\nvalidated\n",
                encoding="utf-8",
            )
            (run_dir / "reused_chapters.json").write_text(
                json.dumps({"slug": Args.slug, "chapters": [{"id": "chapter-1"}]}),
                encoding="utf-8",
            )
            (run_dir / "reused_meta.json").write_text(
                json.dumps(
                    {
                        "slug": Args.slug,
                        "audio_hash": audio_hash,
                        "source_text_hash": source_hash,
                        "auto_estimated_sync": False,
                        "sync_score": 9.7882,
                        "vtt_alignment_score": 9.7882,
                        "transcript_match_score": 9.7882,
                    }
                ),
                encoding="utf-8",
            )
            result = existing_sidecar_reuse(Args(), run_dir, {}, audio, manuscript)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["reuse_source"], "local_hash_bound_release_grade_sidecars")

    def test_listening_only_flag_and_blocked_exit_are_fail_closed(self) -> None:
        with temporary_env(EARNALISM_LISTENING_QA_ONLY="true"):
            self.assertTrue(listening_qa_only())
        with temporary_env(EARNALISM_LISTENING_QA_ONLY=None):
            self.assertFalse(listening_qa_only())
        self.assertEqual(hook_exit_code(0, "BLOCKED"), 3)
        self.assertEqual(hook_exit_code(0, "PASS"), 0)
        self.assertEqual(hook_exit_code(7, "PASS"), 7)

    def test_repeat_attempt_guard_recognizes_same_hash_and_model(self) -> None:
        import sprint1_stage2a_a_ghost_story_listening_qa as wrapper

        with tempfile.TemporaryDirectory() as raw:
            original = wrapper.RUN_DIR
            wrapper.RUN_DIR = Path(raw)
            try:
                (wrapper.RUN_DIR / "listening_quality_report.json").write_text(
                    json.dumps(
                        {
                            "audio_hash": "same-hash",
                            "listening_quality": {
                                "model_or_judge": "openai:gpt-audio",
                                "samples": [{"sample_label": str(index)} for index in range(6)],
                            },
                        }
                    ),
                    encoding="utf-8",
                )
                blocker = completed_attempt_blocker("same-hash")
            finally:
                wrapper.RUN_DIR = original
        self.assertIn("REPEAT_QA_ATTEMPT_BLOCKED", blocker)


if __name__ == "__main__":
    unittest.main()
