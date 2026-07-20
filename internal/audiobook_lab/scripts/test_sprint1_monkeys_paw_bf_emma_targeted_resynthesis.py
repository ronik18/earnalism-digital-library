#!/usr/bin/env python3
"""Focused tests for the one-passage Monkey's Paw targeted repair."""

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
    "sprint1_monkeys_paw_bf_emma_targeted_resynthesis.py"
)
SPEC = importlib.util.spec_from_file_location("monkeys_paw_targeted", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class MonkeysPawTargetedResynthesisTests(unittest.TestCase):
    def test_prior_failure_is_bound_and_only_factory_passage_failed(self) -> None:
        _evidence, reports = MODULE.validate_prior(MODULE.DEFAULT_INPUT)
        self.assertEqual(len(reports), 4)
        self.assertEqual(
            [item["passage_id"] for item in reports if item["pass"] is not True],
            [MODULE.TARGET_PASSAGE_ID],
        )

    def test_preparation_changes_only_punctuation(self) -> None:
        _passages, target = MODULE.canonical_passages()
        prepared, transformations = MODULE.prepare_text(target["text"])
        self.assertEqual(MODULE.sha256_text(prepared), MODULE.PREPARED_TEXT_SHA256)
        self.assertEqual(len(transformations), 2)
        self.assertEqual(
            MODULE.PROFILE.BASE.lexical_tokens(target["text"]),
            MODULE.PROFILE.BASE.lexical_tokens(prepared),
        )
        self.assertIn("I ... was asked", prepared)
        self.assertIn("slower witted husband", prepared)

    def test_prepared_g2p_is_british_fallback_free_and_pinned(self) -> None:
        program = f"""
import importlib.util,json
from pathlib import Path
p=Path({str(SCRIPT)!r})
s=importlib.util.spec_from_file_location('target_g2p',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
_passages,target=m.canonical_passages()
prepared,_=m.prepare_text(target['text'])
print(json.dumps(m.validate_prepared_g2p(prepared),sort_keys=True))
"""
        completed = subprocess.run(
            [str(PINNED_PYTHON), "-c", program],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["kokoro_lang_code"], "b")
        self.assertIs(report["british"], True)
        self.assertIsNone(report["fallback"])
        self.assertEqual(report["phoneme_sha256"], MODULE.PREPARED_PHONEME_SHA256)
        self.assertEqual(report["unresolved_tokens"], [])

    def test_attempt_fingerprint_is_exact_and_recorded_closed(self) -> None:
        fingerprint = MODULE.attempt_fingerprint()
        self.assertEqual(fingerprint, MODULE.EXPECTED_ATTEMPT_FINGERPRINT)
        recorded = set()
        for path in MODULE.NO_REPEAT_FILES:
            if path.is_file():
                recorded.update(
                    MODULE.PROFILE._fingerprints(MODULE.read_json(path))
                )
        self.assertIn(fingerprint, recorded)

    def test_preflight_rejects_completed_targeted_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "evidence.json"
            completed = subprocess.run(
                [
                    str(PINNED_PYTHON),
                    str(SCRIPT),
                    "--preflight",
                    "--output",
                    str(output),
                    "--private-output-dir",
                    str(root / "private"),
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout or completed.stderr)
        self.assertEqual(payload["status"], "BLOCKED_FAIL_CLOSED")
        self.assertIn("attempt fingerprint already exists", payload["error"])
        self.assertFalse(output.exists())

    def mocked_execute(self, transcript_transform):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifacts = {}
            for name in ("model", "config", "voice", "whisper"):
                path = root / name
                path.write_bytes(name.encode("utf-8"))
                artifacts[name] = path
            _all_passages, target = MODULE.canonical_passages()
            prepared_text, _ = MODULE.prepare_text(target["text"])
            prepared = {
                **target,
                "canonical_text_sha256": target["text_sha256"],
                "text": prepared_text,
                "text_sha256": MODULE.PREPARED_TEXT_SHA256,
                "characters": len(prepared_text),
            }
            _prior_evidence, prior_reports = MODULE.validate_prior(MODULE.DEFAULT_INPUT)
            payload = {
                "runtime_evidence": {"pinned_execution_runtime_verified": True},
                "next_stage_contract": {},
                "safety": {},
            }
            sample = {
                "passage_id": MODULE.TARGET_PASSAGE_ID,
                "audio_path": str(root / "target.wav"),
                "audio_sha256": "a" * 64,
                "objective_format_pass": True,
            }
            with mock.patch.object(
                MODULE.PROFILE.BASE, "synthesize", return_value=[sample]
            ):
                code, result = MODULE.execute(
                    payload=payload,
                    prepared=prepared,
                    artifacts=artifacts,
                    prior_reports=prior_reports,
                    private_dir=root / "private",
                    whisper_cache=root,
                    model_loader=lambda _cache: object(),
                    decoder=lambda _model, _arm, _sample: transcript_transform(
                        target["text"]
                    ),
                )
        return code, result

    def test_mocked_exact_target_advances_only_to_listening(self) -> None:
        code, result = self.mocked_execute(lambda text: text)
        self.assertEqual(code, 0)
        self.assertEqual(result["go_no_go"], "GO_PRIVATE_LISTENING_QA_ONLY")
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], True)
        self.assertIs(result["next_stage_contract"]["full_title_generation_allowed"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)

    def test_mocked_missing_word_closes_fingerprint(self) -> None:
        code, result = self.mocked_execute(
            lambda text: text.replace("slower-witted", "slower")
        )
        self.assertEqual(code, 4)
        self.assertEqual(
            result["go_no_go"], "NO_GO_TARGETED_RESYNTHESIS_OBJECTIVE_FAILED"
        )
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], False)

    def test_source_has_no_publication_or_browser_speech_path(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn('"/audio/', source)
        self.assertNotIn("speechSynthesis", source)
        self.assertNotIn("def upload", source)
        self.assertNotIn("def publish", source)

    def test_cli_is_bounded(self) -> None:
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--execute", result.stdout)
        self.assertIn("--preflight", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
