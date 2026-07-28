#!/usr/bin/env python3
"""Unit tests for the private Pride Chatterbox V3 pilot contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import sprint1_pride_chatterbox_v3_private_pilot as pilot


class FakeModel:
    def __init__(self) -> None:
        self.conds = object()
        self.sr = 24_000
        self.generate_calls: list[tuple[str, dict[str, object]]] = []

    def generate(self, text: str, **kwargs: object) -> bytes:
        self.generate_calls.append((text, kwargs))
        return b"fake-waveform"


class PrideChatterboxV3PilotTests(unittest.TestCase):
    def test_policy_is_one_private_sample_with_no_reference_or_release(self) -> None:
        policy = pilot.validate_policy()
        self.assertEqual(
            policy["decision"],
            "AUTHORIZE_ONE_PRIVATE_CHATTERBOX_V3_BUILTIN_CONDS_SAMPLE",
        )
        self.assertEqual(policy["scope"]["sample_count"], 1)
        self.assertTrue(policy["scope"]["private_only"])
        for key in (
            "full_title_generation_allowed",
            "upload_allowed",
            "publication_allowed",
            "release_gate_mutation_allowed",
            "catalog_mutation_allowed",
            "public_asset_write_allowed",
        ):
            self.assertFalse(policy["scope"][key])
        self.assertEqual(
            policy["voice_contract"]["kind"],
            "MODEL_BUILTIN_CONDITIONAL_NO_EXTERNAL_REFERENCE",
        )
        self.assertFalse(policy["voice_contract"]["audio_prompt_path_allowed"])
        self.assertFalse(policy["transitions"]["release_ready_transition_allowed"])

    def test_controlled_passage_and_catalog_truth_are_exact(self) -> None:
        source = pilot.validate_source()
        catalog = pilot.validate_catalog_truth()
        self.assertEqual(source["passage_text_sha256"], pilot.PASSAGE_SHA256)
        self.assertEqual(hashlib.sha256(pilot.PASSAGE_TEXT.encode()).hexdigest(),
                         pilot.PASSAGE_SHA256)
        self.assertTrue(catalog["front_cover_url"].startswith("https://"))
        self.assertTrue(catalog["back_cover_url"].startswith("https://"))
        self.assertEqual(
            catalog["public_audio_status"], "AUDIO_HIDDEN_NOT_APPROVED"
        )

    def test_private_path_rejects_repository_and_public_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            private_root = Path(temp_dir) / "private"
            accepted = pilot.ensure_private_path(
                private_root / "sample.wav", private_root=private_root
            )
            self.assertTrue(str(accepted).startswith(str(private_root.resolve())))
        with self.assertRaisesRegex(
            pilot.PrideChatterboxPilotError, "configured private root"
        ):
            pilot.ensure_private_path(
                pilot.ROOT / "internal/private.wav",
                private_root=Path(tempfile.gettempdir()) / "private",
            )
        with self.assertRaises(pilot.PrideChatterboxPilotError):
            pilot.ensure_private_path(
                pilot.ROOT / "frontend/public/private.wav",
                private_root=pilot.ROOT / "frontend/public",
            )

    def test_model_bundle_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir)
            for filename in pilot.MODEL_FILE_HASHES:
                (model_dir / filename).write_bytes(b"wrong")
            with self.assertRaisesRegex(
                pilot.PrideChatterboxPilotError, "SHA-256 mismatch"
            ):
                pilot.validate_model_bundle(model_dir)

    def test_synthesis_uses_from_local_signature_and_no_audio_prompt(self) -> None:
        fake = FakeModel()
        factory_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def factory(*args: object, **kwargs: object) -> FakeModel:
            factory_calls.append((args, kwargs))
            return fake

        def saver(path: Path, _audio: object, rate: int) -> None:
            self.assertEqual(rate, 24_000)
            path.write_bytes(b"RIFF-private-test")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = pilot.synthesize(
                model_dir=root / "model",
                output_path=root / "sample.wav",
                device="cpu",
                model_factory=factory,
                audio_saver=saver,
            )
        self.assertEqual(len(factory_calls), 1)
        args, kwargs = factory_calls[0]
        self.assertEqual(args[1], "cpu")
        self.assertEqual(kwargs, {"t3_model": "t3_mtl23ls_v3.safetensors"})
        self.assertEqual(len(fake.generate_calls), 1)
        text, generation_kwargs = fake.generate_calls[0]
        self.assertEqual(text, pilot.PASSAGE_TEXT)
        self.assertNotIn("audio_prompt_path", generation_kwargs)
        self.assertEqual(generation_kwargs, pilot.GENERATION_SETTINGS)
        self.assertFalse(report["audio_prompt_path_used"])

    def test_paid_lock_is_read_only_and_must_allow_pride(self) -> None:
        lock = {
            "status": "active",
            "current_holder": "none",
            "allowed_next_holders": [],
            "allowed_slugs": [pilot.SLUG],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "paid_tts.lock"
            path.write_text(json.dumps(lock), encoding="utf-8")
            before, parsed = pilot.read_and_validate_paid_lock(path)
            self.assertEqual(parsed["current_holder"], "none")
            pilot.assert_paid_lock_unchanged(path, before)
            path.write_text(json.dumps({**lock, "current_holder": "changed"}))
            with self.assertRaisesRegex(
                pilot.PrideChatterboxPilotError, "changed during"
            ):
                pilot.assert_paid_lock_unchanged(path, before)

    @staticmethod
    def _timestamped_result(text: str) -> dict[str, object]:
        words = text.split()
        timestamped = [
            {
                "word": word,
                "start": index * 0.1,
                "end": index * 0.1 + 0.08,
                "probability": 0.99,
            }
            for index, word in enumerate(words)
        ]
        return {"text": text, "segments": [{"words": timestamped}]}

    def test_objective_asr_requires_source_first_last_order_and_timestamps(self) -> None:
        duration = len(pilot.PASSAGE_TEXT.split()) * 0.1 + 0.2
        passed = pilot.evaluate_asr_result(
            self._timestamped_result(pilot.PASSAGE_TEXT),
            duration_seconds=duration,
        )
        self.assertEqual(passed["status"], "PASS")
        self.assertTrue(passed["first_words_match"])
        self.assertTrue(passed["last_words_match"])
        self.assertTrue(passed["ordered_content_integrity_pass"])
        self.assertTrue(passed["word_timestamp_evidence_valid"])

        reordered_words = pilot.PASSAGE_TEXT.split()
        reordered_words[5:10] = reversed(reordered_words[5:10])
        failed = pilot.evaluate_asr_result(
            self._timestamped_result(" ".join(reordered_words)),
            duration_seconds=duration,
        )
        self.assertEqual(failed["status"], "FAIL")
        self.assertFalse(failed["pass"])

        missing_timestamps = pilot.evaluate_asr_result(
            {"text": pilot.PASSAGE_TEXT, "segments": []},
            duration_seconds=duration,
        )
        self.assertEqual(missing_timestamps["status"], "FAIL")
        self.assertFalse(missing_timestamps["word_timestamp_evidence_valid"])

    def test_preflight_reports_no_release_capability_and_preserves_lock(self) -> None:
        lock = {
            "status": "active",
            "current_holder": "none",
            "allowed_next_holders": [],
            "allowed_slugs": [pilot.SLUG],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lock_path = root / "paid_tts.lock"
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            model_dir = root / "model"
            model_dir.mkdir()
            with (
                mock.patch.object(pilot, "validate_policy", return_value={
                    "decision":
                    "AUTHORIZE_ONE_PRIVATE_CHATTERBOX_V3_BUILTIN_CONDS_SAMPLE"
                }),
                mock.patch.object(pilot, "validate_source", return_value={}),
                mock.patch.object(pilot, "validate_catalog_truth", return_value={}),
                mock.patch.object(
                    pilot, "validate_model_bundle", return_value=pilot.MODEL_FILE_HASHES
                ),
                mock.patch.object(pilot, "assert_not_repeated"),
            ):
                report, before = pilot.preflight(
                    model_dir=model_dir,
                    private_root=root / "private",
                    paid_lock=lock_path,
                    version_getter=lambda _package: pilot.RUNTIME_VERSION,
                )
            pilot.assert_paid_lock_unchanged(lock_path, before)
        self.assertEqual(report["status"], "PREFLIGHT_PASS")
        self.assertEqual(report["scope"]["sample_count"], 1)
        self.assertFalse(report["scope"]["upload_allowed"])
        self.assertFalse(report["scope"]["publication_allowed"])
        self.assertFalse(report["scope"]["release_gate_mutation_allowed"])
        self.assertFalse(report["scope"]["full_title_generation_allowed"])


if __name__ == "__main__":
    unittest.main()
