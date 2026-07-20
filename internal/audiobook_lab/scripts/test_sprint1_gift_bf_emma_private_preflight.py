#!/usr/bin/env python3
"""Focused tests for The Gift of the Magi bf_emma private preflight."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_gift_bf_emma_private_preflight.py")
SPEC = importlib.util.spec_from_file_location("gift_bf_emma_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.BASE.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class GiftBfEmmaPrivatePreflightTests(unittest.TestCase):
    def test_exact_catalog_source_and_four_risk_passages(self) -> None:
        chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(chapter.name, "chapter-001.json")
        self.assertEqual(
            [item["passage_id"] for item in passages],
            [
                "opening_money",
                "hair_sale_dialogue",
                "sacrifice_dialogue",
                "magi_ending",
            ],
        )
        self.assertEqual(sum(item["characters"] for item in passages), 1765)
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )

    def test_exact_title_author_or_audio_truth_change_fails_closed(self) -> None:
        original = MODULE.BASE.read_json
        changes = {
            "title": "Synthetic title",
            "author": "Synthetic author",
            "audiobook_enabled": True,
            "audio_enabled": True,
        }
        for key, replacement in changes.items():
            def changed(path: Path, target: str = key, value= replacement):
                payload = original(path)
                if path.name == "public_book.json":
                    payload = copy.deepcopy(payload)
                    payload[target] = value
                return payload

            with self.subTest(key=key), mock.patch.object(
                MODULE.BASE, "read_json", side_effect=changed
            ):
                with self.assertRaisesRegex(
                    MODULE.BASE.KokoroTitlePilotError, "catalog truth changed"
                ):
                    MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_audio_release_approval_change_fails_closed(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            payload = original(path)
            if path.name == "approval_evidence.json":
                payload = copy.deepcopy(payload)
                payload["audio_public_release"] = "PUBLIC_AUDIO_RELEASE_APPROVED"
            return payload

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError, "audio-hidden"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_wrong_slug_is_refused(self) -> None:
        with self.assertRaisesRegex(
            MODULE.BASE.KokoroTitlePilotError, "only the-gift-of-the-magi"
        ):
            MODULE.controlled_source(REPO, "the-open-window")

    def test_recomputed_voice_hash_is_exact_and_materially_different(self) -> None:
        voice = MODULE.DEFAULT_ARTIFACT_DIR / f"voices/{MODULE.VOICE}.pt"
        previous = (
            MODULE.DEFAULT_ARTIFACT_DIR / f"voices/{MODULE.PREVIOUS_VOICE}.pt"
        )
        self.assertTrue(voice.is_file())
        self.assertTrue(previous.is_file())
        self.assertEqual(MODULE.BASE.sha256_file(voice), MODULE.VOICE_SHA256)
        self.assertEqual(
            MODULE.VOICE_SHA256,
            "d0a423deabf4a52b4f49318c51742c54e21bb89bbbe9a12141e7758ddb5da701",
        )
        self.assertEqual(
            MODULE.BASE.sha256_file(previous), MODULE.PREVIOUS_VOICE_SHA256
        )
        self.assertNotEqual(MODULE.VOICE_SHA256, MODULE.PREVIOUS_VOICE_SHA256)

    def test_artifact_validator_pins_model_config_voice_and_whisper(self) -> None:
        _paths, evidence = MODULE.BASE.validate_artifacts(
            MODULE.DEFAULT_ARTIFACT_DIR, MODULE.DEFAULT_WHISPER_CACHE
        )
        self.assertEqual(evidence["model"]["sha256"], MODULE.MODEL_SHA256)
        self.assertEqual(evidence["config"]["sha256"], MODULE.CONFIG_SHA256)
        self.assertEqual(evidence["voice"]["sha256"], MODULE.VOICE_SHA256)
        self.assertEqual(evidence["whisper"]["sha256"], MODULE.WHISPER_SHA256)

    def test_fingerprint_binds_british_g2p_voice_and_prior_history(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        self.assertEqual(len(fingerprint), 64)
        self.assertNotIn(fingerprint, MODULE.PRIOR_FINGERPRINTS)
        self.assertIn(
            "bf5ff8b24d23e4ae912d332b247d26d5efb60eeb0b91ebad0bc179e40a7ea015",
            MODULE.PRIOR_FINGERPRINTS,
        )
        with mock.patch.object(MODULE, "KOKORO_LANG_CODE", "a"):
            self.assertNotEqual(MODULE.attempt_fingerprint(passages), fingerprint)
        with mock.patch.object(MODULE, "G2P_BRITISH", False):
            self.assertNotEqual(MODULE.attempt_fingerprint(passages), fingerprint)

    def test_no_repeat_guard_rejects_persisted_execution_fingerprint(self) -> None:
        _chapter, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
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

    def test_public_output_path_is_refused(self) -> None:
        with self.assertRaisesRegex(
            MODULE.BASE.KokoroTitlePilotError, "public audio path"
        ):
            MODULE.BASE.assert_private_audio_path(
                REPO / "frontend/public/audio/the-gift-of-the-magi"
            )

    def test_pinned_british_g2p_resolves_every_source_token_without_fallback(self) -> None:
        program = f"""
import importlib.util
import json
from pathlib import Path

script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location("gift_emma_g2p_test", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_chapter, passages = module.controlled_source(module.BASE.ROOT, module.SLUG)
print(json.dumps(module.validate_g2p_contract(passages), sort_keys=True))
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
        self.assertIs(payload["british"], True)
        self.assertIsNone(payload["fallback"])
        self.assertIs(payload["all_source_tokens_resolved"], True)
        self.assertEqual(len(payload["reports"]), 4)
        self.assertTrue(
            all(item["unresolved_tokens"] == [] for item in payload["reports"])
        )

    def test_preflight_contract_is_private_zero_cost_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            lock = Path(tmp) / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "none",
                        "allowed_next_holders": [],
                    }
                ),
                encoding="utf-8",
            )
            fake_artifacts = {
                name: Path(tmp) / name
                for name in ("model", "config", "voice", "whisper")
            }
            fake_evidence = {
                name: {"path": str(path), "sha256": "a" * 64, "size_bytes": 1}
                for name, path in fake_artifacts.items()
            }
            fake_g2p = {
                "status": "PASS",
                "british": True,
                "fallback": None,
                "all_source_tokens_resolved": True,
                "reports": [],
            }
            with mock.patch.object(
                MODULE.BASE, "runtime_evidence", return_value={"pinned": True}
            ), mock.patch.object(
                MODULE.BASE,
                "validate_artifacts",
                return_value=(fake_artifacts, fake_evidence),
            ), mock.patch.object(
                MODULE, "validate_g2p_contract", return_value=fake_g2p
            ), mock.patch.object(MODULE.BASE, "NO_REPEAT_FILES", ()):
                payload, _passages, _artifacts = MODULE.gift_emma_preflight(
                    asset_root=REPO,
                    slug=MODULE.SLUG,
                    profile=MODULE.PROFILE,
                    artifact_dir=MODULE.DEFAULT_ARTIFACT_DIR,
                    whisper_cache_dir=MODULE.DEFAULT_WHISPER_CACHE,
                    private_output_dir=MODULE.DEFAULT_PRIVATE_OUTPUT,
                    output=output,
                    paid_lock=lock,
                )
        self.assertEqual(payload["decision"]["representative_execution"], "GO")
        self.assertEqual(payload["decision"]["release"], "NO_GO")
        self.assertEqual(payload["engine"]["voice"], "bf_emma")
        self.assertEqual(payload["engine"]["kokoro_lang_code"], "b")
        self.assertIs(payload["engine"]["g2p_british"], True)
        self.assertIs(payload["engine"]["g2p_fallback_enabled"], False)
        self.assertIs(payload["catalog_truth"]["audiobook_enabled"], False)
        self.assertIs(payload["catalog_truth"]["audio_enabled"], False)
        self.assertEqual(payload["safety"]["provider_calls"], 0)
        self.assertEqual(payload["safety"]["estimated_tts_provider_cost_usd"], 0.0)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["asr_run"], False)
        self.assertIs(payload["safety"]["upload_performed"], False)
        self.assertIs(payload["safety"]["publication_performed"], False)
        self.assertIs(payload["safety"]["release_gate_mutated"], False)

    def test_preflight_exact_command_is_one_bounded_private_execution(self) -> None:
        command = MODULE._exact_command(REPO)
        self.assertIn("--execute", command)
        self.assertIn("the-gift-of-the-magi", command)
        self.assertIn("gift-bf-emma-british-literary-warmth-v1", command)
        self.assertIn("f3ff3571-bf-emma-representative-v1", command)
        self.assertNotIn("frontend/public", command)
        self.assertNotIn("frontend/build", command)

    def test_pinned_interpreter_dry_run_writes_only_preflight_and_preserves_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "preflight.json"
            lock_before = MODULE.DEFAULT_PAID_LOCK.read_bytes()
            # The completed alternative attempt is now correctly closed in
            # production memory. Isolate only no-repeat inputs for this pinned
            # preflight test; explicit tests retain production-guard coverage.
            pinned_code = f"""
import importlib.util
from pathlib import Path

script = Path({str(SCRIPT)!r})
spec = importlib.util.spec_from_file_location("gift_emma_pinned_test", script)
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
            lock_after = MODULE.DEFAULT_PAID_LOCK.read_bytes()
        self.assertEqual(lock_after, lock_before)
        self.assertEqual(
            hashlib.sha256(lock_after).hexdigest(),
            "f586acc793022f28adb3e5fe08969075c2a16f09ef6814ebb31f6e6c90163df3",
        )
        self.assertEqual(
            payload["status"], "READY_FOR_PRIVATE_REPRESENTATIVE_EXECUTION"
        )
        self.assertEqual(payload["decision"]["representative_execution"], "GO")
        self.assertEqual(payload["decision"]["release"], "NO_GO")
        self.assertIs(payload["g2p_preflight"]["all_source_tokens_resolved"], True)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertEqual(payload["safety"]["provider_calls"], 0)
        self.assertNotIn("samples", payload)
        self.assertNotIn("asr", payload)


if __name__ == "__main__":
    unittest.main()
