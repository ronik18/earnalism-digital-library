#!/usr/bin/env python3
"""Focused tests for the Cop af_sarah exact four-sample listening screen."""

from __future__ import annotations

import importlib.util
import inspect
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_cop_af_sarah_private_listening_qa.py")
SPEC = importlib.util.spec_from_file_location("cop_af_sarah_listening", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = MODULE.BASE
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


def approved_env() -> dict[str, str]:
    return {**MODULE.EXPECTED_ENV, "OPENAI_API_KEY": "test-only"}


def judgment(sample: dict, score: float = 10.0, *, fatal: bool = False) -> dict:
    return {
        **sample,
        "scores": {
            field: (0.95 if field == "confidence_score" else score)
            for field in BASE.LISTENING_THRESHOLDS
        },
        "confidence": 0.95,
        "notes": "mocked source-bound listening judgment",
        "blocker_reason": "",
        "judge_flags": {
            field: (fatal and index == 0)
            for index, field in enumerate(BASE.BINARY_LISTENING_FLAGS)
        },
        "frontmatter_present": False,
    }


class CopAfSarahListeningQATests(unittest.TestCase):
    def test_evidence_binds_four_exact_private_wavs(self) -> None:
        evidence, samples, fingerprint = MODULE.load_evidence(MODULE.DEFAULT_EVIDENCE)
        self.assertEqual(evidence["status"], MODULE.EXPECTED_STATUS)
        self.assertEqual(len(samples), 4)
        self.assertEqual(
            {item["sample_label"] for item in samples},
            set(MODULE.EXPECTED_SAMPLE_BINDINGS),
        )
        self.assertTrue(all(Path(item["sample_audio_path"]).is_file() for item in samples))
        self.assertEqual(len(fingerprint), 64)

    def test_runtime_budget_and_exact_ten_guards(self) -> None:
        env = approved_env()
        self.assertEqual(BASE.runtime_gate_errors(env), [])
        self.assertEqual(BASE.budget_guard(env)["estimated_listening_qa_usd"], 0.2)
        exact = BASE.evaluate_judgments(
            [judgment({"sample_label": str(index)}) for index in range(4)]
        )
        self.assertIs(exact["owner_exact_10_pass"], True)
        platform_only = BASE.evaluate_judgments(
            [judgment({"sample_label": str(index)}, 9.5) for index in range(4)]
        )
        self.assertIs(platform_only["platform_screen_pass"], True)
        self.assertIs(platform_only["next_private_stage_authorized"], False)

    def test_dry_run_makes_no_provider_call_and_preserves_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "paid_tts.lock"
            lock.write_bytes(MODULE.DEFAULT_PAID_LOCK.read_bytes())
            before = lock.read_bytes()
            output = root / "dry-run.json"
            code, result = MODULE.execute(
                MODULE.DEFAULT_EVIDENCE,
                output,
                lock,
                dry_run=True,
                env=approved_env(),
                judge=lambda *_args: self.fail("judge must not run"),
            )
            after = lock.read_bytes()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertIs(result["provider_calls_ran"], False)
        self.assertEqual(after, before)

    def test_mocked_exact_ten_restores_lock_and_never_publishes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "paid_tts.lock"
            lock.write_bytes(MODULE.DEFAULT_PAID_LOCK.read_bytes())
            before = lock.read_bytes()
            output = root / "listening.json"
            code, result = MODULE.execute(
                MODULE.DEFAULT_EVIDENCE,
                output,
                lock,
                env=approved_env(),
                judge=lambda _client, _args, sample: judgment(sample),
                client_factory=lambda: object(),
            )
            after = lock.read_bytes()
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "PRIVATE_COP_AF_SARAH_REPRESENTATIVE_EXACT_10_PASS_NOT_RELEASE_EVIDENCE",
        )
        self.assertIs(result["listening_gate"]["next_private_stage_authorized"], True)
        self.assertIs(result["publication_performed"], False)
        self.assertIs(result["release_gate_mutated"], False)
        self.assertIs(result["lock_restored"], True)
        self.assertEqual(after, before)

    def test_completed_real_fingerprint_cannot_repeat(self) -> None:
        _evidence, _samples, fingerprint = MODULE.load_evidence(
            MODULE.DEFAULT_EVIDENCE
        )
        self.assertTrue(MODULE.DEFAULT_OUTPUT.is_file())
        self.assertIs(
            BASE.prior_attempt_completed(MODULE.DEFAULT_OUTPUT, fingerprint), True
        )

    def test_source_and_cli_have_no_generation_upload_or_publication_path(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn("def synthesize", source)
        self.assertNotIn("--upload", source)
        self.assertNotIn("--publish", source)
        self.assertNotIn("speechSynthesis", source)
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=BASE.ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dry-run", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
