#!/usr/bin/env python3
"""Focused tests for The Monkey's Paw private Kokoro pilot."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name(
    "sprint1_monkeys_paw_kokoro_private_audition.py"
)
SPEC = importlib.util.spec_from_file_location("monkeys_paw_kokoro_pilot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class MonkeysPawKokoroPilotTests(unittest.TestCase):
    def test_canonical_source_binds_all_three_chapters_and_four_passages(self) -> None:
        chapter_paths, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(len(chapter_paths), 3)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            [item["passage_id"] for item in passages],
            [item["passage_id"] for item in MODULE.PASSAGE_SPECS],
        )
        self.assertEqual(
            sum(item["characters"] for item in passages), MODULE.PASSAGE_CHARACTERS
        )
        self.assertTrue(all(item["text_sha256"] == spec["sha256"] for item, spec in zip(passages, MODULE.PASSAGE_SPECS)))

    def test_attempt_fingerprint_is_exact_and_recorded_closed(self) -> None:
        _chapters, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        self.assertEqual(fingerprint, MODULE.EXPECTED_ATTEMPT_FINGERPRINT)
        recorded = set()
        for path in MODULE.NO_REPEAT_FILES:
            if path.is_file():
                recorded.update(MODULE._fingerprints(MODULE.read_json(path)))
        self.assertIn(fingerprint, recorded)

    def test_prior_google_attempts_are_bound_and_provider_is_distinct(self) -> None:
        audit = MODULE.validate_prior_attempts(REPO)
        self.assertEqual(audit["new_provider_family"], "kokoro")
        self.assertIs(audit["materially_distinct"], True)
        self.assertEqual(
            audit["closed_google_fingerprints"],
            ["14b9ef3e3465b1b0", "8b671c0f3c569295"],
        )

    def test_voice_selection_uses_strongest_retained_local_voice(self) -> None:
        self.assertEqual(MODULE.VOICE, "af_bella")
        self.assertEqual(
            MODULE.VOICE_SHA256,
            "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
        )
        self.assertEqual(MODULE.SPEED, 0.96)
        self.assertEqual(MODULE.AMERICAN_LANG_CODE, "a")
        self.assertIs(MODULE.AMERICAN_G2P, False)
        self.assertIsNone(MODULE.G2P_FALLBACK)

    def test_pinned_g2p_resolves_every_source_token_and_hash(self) -> None:
        program = f"""
import importlib.util,json
from pathlib import Path
script=Path({str(SCRIPT)!r})
spec=importlib.util.spec_from_file_location('monkeys_g2p_test',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
_chapters,passages=module.controlled_source(module.ROOT,module.SLUG)
print(json.dumps(module.validate_g2p(passages),sort_keys=True))
"""
        result = subprocess.run(
            [str(PINNED_PYTHON), "-c", program],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["lang_code"], "a")
        self.assertIs(payload["british"], False)
        self.assertIsNone(payload["fallback"])
        self.assertEqual(
            {item["passage_id"]: item["phoneme_sha256"] for item in payload["reports"]},
            MODULE.PHONEME_HASHES,
        )
        self.assertTrue(all(item["unresolved_tokens"] == [] for item in payload["reports"]))

    def test_objective_contract_has_no_asr_prompt_or_equivalence_escape(self) -> None:
        MODULE.configure_base()
        self.assertEqual(MODULE.BASE.ASR_SCORE_MIN, 9.7)
        self.assertEqual(MODULE.BASE.ASR_COVERAGE_MIN, 0.98)
        self.assertTrue(
            all(value == "no_prompt" for value in MODULE.BASE.ASR_PROMPT_POLICY.values())
        )
        self.assertTrue(
            all(value == () for value in MODULE.BASE.SOURCE_EQUIVALENCE_POLICY.values())
        )

    def test_no_repeat_guard_rejects_completed_output(self) -> None:
        _chapters, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence.json"
            output.write_text(
                json.dumps(
                    {
                        "engine": {"attempt_fingerprint": fingerprint},
                        "safety": {"audio_generated": True},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
                with self.assertRaisesRegex(
                    MODULE.MonkeysPawPilotError, "already generated audio"
                ):
                    MODULE.ensure_not_repeated(fingerprint, output)

    def test_public_output_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.MonkeysPawPilotError, "public audio path"):
            MODULE.assert_private_path(
                REPO / "frontend/public/audio/the-monkeys-paw"
            )

    def test_mocked_objective_pass_does_not_touch_release_or_lock(self) -> None:
        _chapters, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = {}
            for name in ("model", "config", "voice", "whisper"):
                path = root / name
                path.write_bytes(name.encode("utf-8"))
                artifacts[name] = path
            samples = [
                {"passage_id": item["passage_id"], "objective_format_pass": True}
                for item in passages
            ]
            asr = {
                "status": "PASS",
                "reports": [
                    {"passage_id": item["passage_id"], "pass": True}
                    for item in passages
                ],
            }
            payload = {
                "runtime_evidence": {"pinned_execution_runtime_verified": True},
                "engine": {"attempt_fingerprint": MODULE.EXPECTED_ATTEMPT_FINGERPRINT},
                "next_stage_contract": {"status": "EXECUTOR_CODE_REVIEWED_NOT_EXECUTED"},
                "safety": {"audio_generated": False},
            }
            with mock.patch.object(MODULE.BASE, "synthesize", return_value=samples), mock.patch.object(
                MODULE.BASE, "run_asr", return_value=asr
            ):
                code, result = MODULE.execute(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_dir=root / "private",
                    whisper_cache_dir=root,
                )
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_INDEPENDENT_LISTENING_QA",
        )
        self.assertEqual(result["go_no_go"], "GO_PRIVATE_LISTENING_QA_ONLY")
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], True)
        self.assertIs(result["safety"]["paid_tts_lock_inspected"], False)
        self.assertIs(result["safety"]["paid_tts_lock_touched"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)
        self.assertIs(result["safety"]["release_gate_mutated"], False)
        self.assertIs(result["safety"]["public_audio_approved"], False)

    def test_mocked_asr_fail_stays_rejected(self) -> None:
        _chapters, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = {}
            for name in ("model", "config", "voice", "whisper"):
                path = root / name
                path.write_bytes(name.encode("utf-8"))
                artifacts[name] = path
            samples = [
                {"passage_id": item["passage_id"], "objective_format_pass": True}
                for item in passages
            ]
            payload = {
                "runtime_evidence": {"pinned_execution_runtime_verified": True},
                "engine": {"attempt_fingerprint": MODULE.EXPECTED_ATTEMPT_FINGERPRINT},
                "next_stage_contract": {"status": "EXECUTOR_CODE_REVIEWED_NOT_EXECUTED"},
                "safety": {"audio_generated": False},
            }
            with mock.patch.object(MODULE.BASE, "synthesize", return_value=samples), mock.patch.object(
                MODULE.BASE, "run_asr", return_value={"status": "FAIL", "reports": []}
            ):
                code, result = MODULE.execute(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_dir=root / "private",
                    whisper_cache_dir=root,
                )
        self.assertEqual(code, 4)
        self.assertEqual(result["status"], "PRIVATE_REPRESENTATIVE_PILOT_REJECTED")
        self.assertEqual(
            result["go_no_go"], "NO_GO_REPRESENTATIVE_OBJECTIVE_GATE_FAILED"
        )
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], False)
        self.assertIn(
            "REPRESENTATIVE_OBJECTIVE_OR_ASR_GATE_FAILED",
            result["blockers_to_release"],
        )

    def test_cli_has_no_paid_lock_or_release_surface(self) -> None:
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("paid-lock", result.stdout)
        self.assertNotIn("--publish", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertIn("--execute", result.stdout)

    def test_pinned_preflight_rejects_completed_fingerprint_without_audio(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence.json"
            private = Path(temporary) / "private"
            result = subprocess.run(
                [
                    str(PINNED_PYTHON),
                    str(SCRIPT),
                    "--preflight",
                    "--asset-root",
                    str(REPO),
                    "--private-output-dir",
                    str(private),
                    "--output",
                    str(output),
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
            payload = json.loads(result.stdout or result.stderr)
        self.assertEqual(payload["status"], "BLOCKED_FAIL_CLOSED")
        self.assertIn("attempt fingerprint already exists", payload["error"])
        self.assertFalse(output.exists())
        self.assertFalse(private.exists())

    def test_source_contains_no_static_audio_or_browser_speech_fallback(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn('"/audio/', source)
        self.assertNotIn("speechSynthesis", source)
        self.assertNotIn("word-level sync", source.lower())


if __name__ == "__main__":
    unittest.main()
