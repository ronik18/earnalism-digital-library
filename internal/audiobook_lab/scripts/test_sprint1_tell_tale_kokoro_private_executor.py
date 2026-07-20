#!/usr/bin/env python3
"""Isolated tests for the Tell-Tale British bf_emma private executor."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_tell_tale_kokoro_private_executor.py")
SPEC = importlib.util.spec_from_file_location("tell_tale_private_executor", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.PREFLIGHT.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class TellTalePrivateExecutorTests(unittest.TestCase):
    def test_executor_pins_existing_preflight_fingerprint(self) -> None:
        _chapter, passages = MODULE.PREFLIGHT.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(
            MODULE.PREFLIGHT.attempt_fingerprint(passages),
            MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
        )

    def test_executor_is_exact_british_and_fallback_free(self) -> None:
        self.assertEqual(MODULE.VOICE, "bf_emma")
        self.assertEqual(MODULE.BRITISH_LANG_CODE, "b")
        self.assertIs(MODULE.BRITISH_G2P, True)
        self.assertIsNone(MODULE.G2P_FALLBACK)
        source = inspect.getsource(MODULE.synthesize_british)
        self.assertIn("lang_code=BRITISH_LANG_CODE", source)
        self.assertIn("british=BRITISH_G2P", source)
        self.assertIn("fallback=G2P_FALLBACK", source)

    def test_pinned_british_g2p_resolves_all_passages_and_hashes(self) -> None:
        program = f"""
import importlib.util, json
from pathlib import Path
script=Path({str(SCRIPT)!r})
spec=importlib.util.spec_from_file_location('executor_g2p_test',script)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
_chapter,passages=module.PREFLIGHT.controlled_source(module.PREFLIGHT.ROOT,module.SLUG)
print(json.dumps(module.validate_british_g2p(passages),sort_keys=True))
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
        self.assertEqual(payload["lang_code"], "b")
        self.assertIs(payload["british"], True)
        self.assertIsNone(payload["fallback"])
        self.assertEqual(
            {item["passage_id"]: item["phoneme_sha256"] for item in payload["reports"]},
            MODULE.BRITISH_PHONEME_HASHES,
        )
        self.assertTrue(all(item["unresolved_tokens"] == [] for item in payload["reports"]))

    def test_executor_reuses_strict_objective_asr_contract(self) -> None:
        MODULE.configure_base()
        self.assertEqual(MODULE.BASE.ASR_SCORE_MIN, 9.7)
        self.assertEqual(MODULE.BASE.ASR_COVERAGE_MIN, 0.98)
        self.assertTrue(all(value == "no_prompt" for value in MODULE.BASE.ASR_PROMPT_POLICY.values()))
        self.assertTrue(all(value == () for value in MODULE.BASE.SOURCE_EQUIVALENCE_POLICY.values()))

    def test_preflight_contract_exposes_exact_execute_command_without_paid_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            MODULE.PREFLIGHT, "NO_REPEAT_FILES", ()
        ), mock.patch.object(
            MODULE, "validate_british_g2p", return_value={"status": "PASS"}
        ):
            payload, passages, _artifacts = MODULE.executor_preflight(
                asset_root=REPO,
                slug=MODULE.SLUG,
                profile=MODULE.PROFILE,
                artifact_dir=MODULE.PREFLIGHT.DEFAULT_ARTIFACT_DIR,
                whisper_cache_dir=MODULE.PREFLIGHT.DEFAULT_WHISPER_CACHE,
                private_output_dir=Path(tmp) / "private",
                output=Path(tmp) / "execution.json",
            )
        self.assertEqual(len(passages), 4)
        command = payload["next_stage_contract"]["exact_execute_command"]
        self.assertIn("--execute", command)
        self.assertIn("the-tell-tale-heart", command)
        self.assertIn("bf-emma", command)
        self.assertNotIn("paid-lock", command)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["executor_run"], False)
        self.assertIs(payload["safety"]["paid_tts_lock_inspected"], False)
        self.assertIs(payload["safety"]["paid_tts_lock_touched"], False)

    def test_no_repeat_guard_rejects_completed_execution(self) -> None:
        _chapter, passages = MODULE.PREFLIGHT.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.PREFLIGHT.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "execution.json"
            output.write_text(
                json.dumps(
                    {
                        "engine": {"attempt_fingerprint": fingerprint},
                        "safety": {"audio_generated": True},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE.PREFLIGHT, "NO_REPEAT_FILES", ()):
                with self.assertRaisesRegex(
                    MODULE.PREFLIGHT.TellTalePreflightError, "already generated audio"
                ):
                    MODULE.PREFLIGHT.ensure_not_repeated(fingerprint, output)

    def test_execute_mocked_objective_pass_never_touches_release_or_lock(self) -> None:
        _chapter, passages = MODULE.PREFLIGHT.controlled_source(REPO, MODULE.SLUG)
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            artifacts = {}
            for name in ("model", "config", "voice", "whisper"):
                path = temp / name
                path.write_bytes(name.encode("utf-8"))
                artifacts[name] = path
            samples = [
                {"passage_id": item["passage_id"], "objective_format_pass": True}
                for item in passages
            ]
            asr = {
                "status": "PASS",
                "reports": [{"passage_id": item["passage_id"], "pass": True} for item in passages],
            }
            payload = {
                "runtime_evidence": {"pinned_execution_runtime_verified": True},
                "engine": {"attempt_fingerprint": MODULE.EXPECTED_ATTEMPT_FINGERPRINT},
                "next_stage_contract": {"status": "EXECUTOR_CODE_REVIEWED_NOT_EXECUTED"},
                "safety": {"audio_generated": False},
            }
            with mock.patch.object(MODULE, "synthesize_british", return_value=samples), \
                 mock.patch.object(MODULE.BASE, "run_asr", return_value=asr):
                code, result = MODULE.execute(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_dir=temp / "private",
                    whisper_cache_dir=temp,
                )
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_INDEPENDENT_LISTENING_QA",
        )
        self.assertIs(result["safety"]["paid_tts_lock_inspected"], False)
        self.assertIs(result["safety"]["paid_tts_lock_touched"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)
        self.assertIs(result["safety"]["release_gate_mutated"], False)

    def test_execute_mocked_asr_fail_stays_rejected(self) -> None:
        _chapter, passages = MODULE.PREFLIGHT.controlled_source(REPO, MODULE.SLUG)
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            artifacts = {}
            for name in ("model", "config", "voice", "whisper"):
                path = temp / name
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
            with mock.patch.object(MODULE, "synthesize_british", return_value=samples), \
                 mock.patch.object(MODULE.BASE, "run_asr", return_value={"status": "FAIL", "reports": []}):
                code, result = MODULE.execute(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_dir=temp / "private",
                    whisper_cache_dir=temp,
                )
        self.assertEqual(code, 4)
        self.assertEqual(result["status"], "PRIVATE_REPRESENTATIVE_PILOT_REJECTED")
        self.assertIn(
            "REPRESENTATIVE_OBJECTIVE_OR_ASR_GATE_FAILED",
            result["blockers_to_release"],
        )

    def test_asr_pass_label_without_four_bound_reports_stays_rejected(self) -> None:
        _chapter, passages = MODULE.PREFLIGHT.controlled_source(REPO, MODULE.SLUG)
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            artifacts = {}
            for name in ("model", "config", "voice", "whisper"):
                path = temp / name
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
            with mock.patch.object(MODULE, "synthesize_british", return_value=samples), \
                 mock.patch.object(MODULE.BASE, "run_asr", return_value={"status": "PASS", "reports": []}):
                code, result = MODULE.execute(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_dir=temp / "private",
                    whisper_cache_dir=temp,
                )
        self.assertEqual(code, 4)
        self.assertEqual(result["status"], "PRIVATE_REPRESENTATIVE_PILOT_REJECTED")

    def test_public_private_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.PREFLIGHT.TellTalePreflightError, "public audio path"):
            MODULE.PREFLIGHT.assert_private_path(
                REPO / "frontend/public/audio/the-tell-tale-heart"
            )

    def test_cli_surface_has_no_paid_lock_option(self) -> None:
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("paid-lock", result.stdout)
        self.assertIn("--execute", result.stdout)

    def test_pinned_cli_preflight_writes_no_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "execution.json"
            pinned_code = f"""
import importlib.util
from pathlib import Path
script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location('tell_tale_executor_pinned_test', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.PREFLIGHT.NO_REPEAT_FILES = ()
raise SystemExit(module.main([
    '--preflight',
    '--asset-root', {str(REPO)!r},
    '--private-output-dir', {str(Path(tmp) / 'private')!r},
    '--output', {str(output)!r},
]))
"""
            result = subprocess.run(
                [
                    str(PINNED_PYTHON),
                    "-c",
                    pinned_code,
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION")
        self.assertEqual(payload["g2p_audit"]["status"], "PASS")
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["asr_run"], False)
        self.assertIs(payload["safety"]["executor_run"], False)
        self.assertNotIn("samples", payload)
        self.assertNotIn("asr", payload)


if __name__ == "__main__":
    unittest.main()
