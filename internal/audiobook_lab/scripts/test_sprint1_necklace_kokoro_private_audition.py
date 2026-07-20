#!/usr/bin/env python3
"""Focused tests for The Necklace's private Kokoro preflight."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_necklace_kokoro_private_audition.py")
SPEC = importlib.util.spec_from_file_location("necklace_private_audition", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.BASE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class NecklacePrivatePreflightTests(unittest.TestCase):
    def test_exact_catalog_source_and_four_risk_passages(self) -> None:
        chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(chapter.name, "chapter-001.json")
        self.assertEqual([item["passage_id"] for item in passages], [
            "opening_social_cadence",
            "invitation_dialogue",
            "necklace_loss_panic",
            "final_ironic_reveal",
        ])
        self.assertEqual(sum(item["characters"] for item in passages), 2387)
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )

    def test_profile_uses_materially_different_hash_pinned_local_voice(self) -> None:
        self.assertEqual(MODULE.VOICE, "af_sarah")
        self.assertNotEqual(MODULE.VOICE_SHA256, MODULE.PREVIOUS_KOKORO_VOICE_SHA256)
        voice = MODULE.DEFAULT_ARTIFACT_DIR / f"voices/{MODULE.VOICE}.pt"
        self.assertTrue(voice.is_file())
        self.assertEqual(MODULE.BASE.sha256_file(voice), MODULE.VOICE_SHA256)

    def test_preflight_pins_model_config_voice_and_whisper_hashes(self) -> None:
        _paths, evidence = MODULE.BASE.validate_artifacts(
            MODULE.DEFAULT_ARTIFACT_DIR, MODULE.DEFAULT_WHISPER_CACHE
        )
        self.assertEqual(evidence["model"]["sha256"], MODULE.MODEL_SHA256)
        self.assertEqual(evidence["config"]["sha256"], MODULE.CONFIG_SHA256)
        self.assertEqual(evidence["voice"]["sha256"], MODULE.VOICE_SHA256)
        self.assertEqual(evidence["whisper"]["sha256"], MODULE.WHISPER_SHA256)

    def test_audio_enabled_catalog_mutation_fails_closed(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "public_book.json":
                value = copy.deepcopy(value)
                value["audiobook_enabled"] = True
            return value

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError, "audiobook_enabled"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_wrong_title_or_author_fails_closed(self) -> None:
        original = MODULE.BASE.read_json
        for key in ("title", "author"):
            def changed(path: Path, target: str = key):
                value = original(path)
                if path.name == "public_book.json":
                    value = copy.deepcopy(value)
                    value[target] = "synthetic metadata"
                return value

            with self.subTest(key=key), mock.patch.object(
                MODULE.BASE, "read_json", side_effect=changed
            ):
                with self.assertRaisesRegex(
                    MODULE.BASE.KokoroTitlePilotError, f"catalog truth changed for {key}"
                ):
                    MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_wrong_slug_is_refused(self) -> None:
        with self.assertRaisesRegex(MODULE.BASE.KokoroTitlePilotError, "only the-necklace"):
            MODULE.controlled_source(REPO, "the-open-window")

    def test_public_output_path_is_refused(self) -> None:
        with self.assertRaisesRegex(MODULE.BASE.KokoroTitlePilotError, "public audio path"):
            MODULE.BASE.assert_private_audio_path(
                REPO / "frontend/public/audio/the-necklace"
            )

    def test_fingerprint_is_title_specific_and_not_a_prior_attempt(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.BASE.attempt_fingerprint(passages)
        self.assertEqual(len(fingerprint), 64)
        self.assertNotIn(
            fingerprint,
            {str(item["fingerprint"]) for item in MODULE.PRIOR_ATTEMPTS},
        )
        self.assertNotEqual(fingerprint, hashlib.sha256(b"the-necklace").hexdigest())

    def test_no_repeat_guard_rejects_persisted_executed_fingerprint(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.BASE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "memory.json"
            ledger.write_text(
                json.dumps({"attempt_fingerprint": fingerprint}), encoding="utf-8"
            )
            with mock.patch.object(MODULE.BASE, "NO_REPEAT_FILES", (ledger,)):
                with self.assertRaisesRegex(
                    MODULE.BASE.KokoroTitlePilotError, "already exists"
                ):
                    MODULE.BASE.ensure_not_repeated(
                        fingerprint, Path(tmp) / "missing-evidence.json"
                    )

    def test_g2p_and_release_contract_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            lock = Path(tmp) / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "none", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE.BASE, "runtime_evidence", return_value={"pinned": True}), \
                 mock.patch.object(MODULE.BASE, "NO_REPEAT_FILES", ()):
                payload, _passages, _artifacts = MODULE.necklace_preflight(
                    asset_root=REPO,
                    slug=MODULE.SLUG,
                    profile=MODULE.PROFILE,
                    artifact_dir=MODULE.DEFAULT_ARTIFACT_DIR,
                    whisper_cache_dir=MODULE.DEFAULT_WHISPER_CACHE,
                    private_output_dir=MODULE.DEFAULT_PRIVATE_OUTPUT,
                    output=output,
                    paid_lock=lock,
                )
        self.assertIs(payload["engine"]["g2p_fallback_enabled"], False)
        self.assertIs(payload["next_stage_contract"]["g2p_fallback_enabled"], False)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["upload_performed"], False)
        self.assertIs(payload["safety"]["publication_performed"], False)
        self.assertIs(payload["safety"]["release_gate_mutated"], False)
        self.assertIn("--execute", payload["next_stage_contract"]["exact_execute_command"])
        self.assertIn("af-sarah", payload["next_stage_contract"]["exact_execute_command"])

    def test_pinned_interpreter_dry_run_writes_preflight_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            # The completed attempt is now correctly closed in production
            # memory. Isolate only that persisted input for this pinned-runtime
            # preflight test; dedicated tests retain no-repeat guard coverage.
            pinned_code = f"""
import importlib.util
from pathlib import Path

script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location("necklace_pinned_test", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.configure_base()
module.BASE.NO_REPEAT_FILES = ()
raise SystemExit(module.BASE.main(module.expand_defaults([
    "--preflight", "--output", {str(output)!r}
])))
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
        self.assertEqual(payload["status"], "READY_FOR_PRIVATE_REPRESENTATIVE_EXECUTION")
        self.assertEqual(payload["scope"]["slug"], MODULE.SLUG)
        self.assertEqual(payload["scope"]["title"], MODULE.TITLE)
        self.assertEqual(payload["scope"]["author"], MODULE.AUTHOR)
        self.assertEqual(payload["engine"]["voice"], MODULE.VOICE)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertNotIn("samples", payload)
        self.assertNotIn("asr", payload)


if __name__ == "__main__":
    unittest.main()
