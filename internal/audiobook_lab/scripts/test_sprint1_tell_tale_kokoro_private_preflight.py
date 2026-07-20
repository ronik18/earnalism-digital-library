#!/usr/bin/env python3
"""Focused tests for The Tell-Tale Heart's preflight-only Kokoro contract."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_tell_tale_kokoro_private_preflight.py")
SPEC = importlib.util.spec_from_file_location("tell_tale_private_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class TellTalePrivatePreflightTests(unittest.TestCase):
    def test_exact_catalog_source_and_four_risk_passages(self) -> None:
        chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(chapter.name, "chapter-001.json")
        self.assertEqual(
            [item["passage_id"] for item in passages],
            [
                "opening_unreliable_sanity",
                "bedroom_suspense_dialogue",
                "heartbeat_crescendo",
                "final_confession",
            ],
        )
        self.assertEqual(sum(item["characters"] for item in passages), 2149)
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )

    def test_selected_voice_is_exact_unused_local_british_asset(self) -> None:
        self.assertEqual(MODULE.VOICE, "bf_emma")
        voice = MODULE.DEFAULT_ARTIFACT_DIR / "voices/bf_emma.pt"
        self.assertTrue(voice.is_file())
        self.assertEqual(MODULE.sha256_file(voice), MODULE.VOICE_SHA256)
        self.assertTrue(
            all(
                MODULE.VOICE_SHA256 != item["sha256"]
                for item in MODULE.PREVIOUS_VOICES.values()
            )
        )
        self.assertTrue(
            all(
                item["cosine_similarity_to_selected"] < 0.7
                for item in MODULE.PREVIOUS_VOICES.values()
            )
        )

    def test_model_config_voice_and_whisper_are_checksum_bound(self) -> None:
        _paths, evidence = MODULE.validate_artifacts(
            MODULE.DEFAULT_ARTIFACT_DIR, MODULE.DEFAULT_WHISPER_CACHE
        )
        self.assertEqual(evidence["model"]["sha256"], MODULE.MODEL_SHA256)
        self.assertEqual(evidence["config"]["sha256"], MODULE.CONFIG_SHA256)
        self.assertEqual(evidence["voice"]["sha256"], MODULE.VOICE_SHA256)
        self.assertEqual(evidence["whisper"]["sha256"], MODULE.WHISPER_SHA256)

    def test_prior_google_attempts_are_audited_and_not_repeated(self) -> None:
        MODULE.validate_prior_attempts(REPO)
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        self.assertNotIn(
            fingerprint,
            {item["attempt_fingerprint"] for item in MODULE.PRIOR_GOOGLE_ATTEMPTS},
        )

    def test_catalog_audio_enablement_fails_closed(self) -> None:
        original = MODULE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "public_book.json":
                value = copy.deepcopy(value)
                value["audiobook_enabled"] = True
            return value

        with mock.patch.object(MODULE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(MODULE.TellTalePreflightError, "audiobook_enabled"):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_audio_release_approval_change_fails_closed(self) -> None:
        original = MODULE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "approval_evidence.json":
                value = copy.deepcopy(value)
                value["audio_public_release"] = "APPROVED"
            return value

        with mock.patch.object(MODULE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(MODULE.TellTalePreflightError, "audio_public_release"):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_wrong_slug_is_refused(self) -> None:
        with self.assertRaisesRegex(MODULE.TellTalePreflightError, "only the-tell-tale-heart"):
            MODULE.controlled_source(REPO, "the-open-window")

    def test_public_output_path_is_refused(self) -> None:
        with self.assertRaisesRegex(MODULE.TellTalePreflightError, "public audio path"):
            MODULE.assert_private_path(REPO / "frontend/public/audio/the-tell-tale-heart")

    def test_no_repeat_guard_rejects_persisted_fingerprint(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp) / "memory.json"
            memory.write_text(json.dumps({"attempt_fingerprint": fingerprint}), encoding="utf-8")
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", (memory,)):
                with self.assertRaisesRegex(MODULE.TellTalePreflightError, "already exists"):
                    MODULE.ensure_not_repeated(fingerprint, Path(tmp) / "output.json")

    def test_preflight_is_fallback_free_audio_hidden_and_lock_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            MODULE, "NO_REPEAT_FILES", ()
        ):
            payload = MODULE.build_preflight(
                asset_root=REPO,
                slug=MODULE.SLUG,
                profile=MODULE.PROFILE,
                artifact_dir=MODULE.DEFAULT_ARTIFACT_DIR,
                whisper_cache_dir=MODULE.DEFAULT_WHISPER_CACHE,
                private_output_dir=Path(tmp) / "private",
                output=Path(tmp) / "evidence.json",
            )
        self.assertEqual(payload["go_no_go"], "GO_PRIVATE_REPRESENTATIVE_ONLY")
        self.assertEqual(payload["engine"]["g2p_language_code_required_for_future_execution"], "b")
        self.assertIs(payload["engine"]["g2p_fallback_enabled"], False)
        self.assertIs(payload["safety"]["paid_tts_lock_inspected"], False)
        self.assertIs(payload["safety"]["paid_tts_lock_touched"], False)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["upload_performed"], False)
        self.assertIs(payload["safety"]["publication_performed"], False)
        self.assertIs(payload["safety"]["release_gate_mutated"], False)
        self.assertIs(payload["safety"]["public_audio_approved"], False)

    def test_cli_refuses_execution_mode(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--execute"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments: --execute", result.stderr)

    def test_pinned_interpreter_writes_preflight_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            pinned_code = f"""
import importlib.util
from pathlib import Path
script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location('tell_tale_pinned_test', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.NO_REPEAT_FILES = ()
raise SystemExit(module.main(['--preflight', '--output', {str(output)!r}]))
"""
            result = subprocess.run(
                [str(PINNED_PYTHON), "-c", pinned_code],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "READY_FOR_ONE_PRIVATE_REPRESENTATIVE_EXECUTION")
        self.assertEqual(
            payload["runtime_evidence"]["status"], "PINNED_EXECUTION_RUNTIME_VERIFIED"
        )
        self.assertEqual(payload["engine"]["voice"], MODULE.VOICE)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertNotIn("samples", payload)
        self.assertNotIn("asr_results", payload)


if __name__ == "__main__":
    unittest.main()
