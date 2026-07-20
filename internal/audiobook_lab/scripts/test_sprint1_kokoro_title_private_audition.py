import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name("sprint1_kokoro_title_private_audition.py")
SPEC = importlib.util.spec_from_file_location("sprint1_kokoro_title_private_audition", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ROOT = Path(__file__).resolve().parents[3]


class Sprint1KokoroTitlePrivateAuditionTests(unittest.TestCase):
    @staticmethod
    def generated_payload(samples):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        return {
            "scope": {"slug": MODULE.ALLOWED_SLUG},
            "engine": {"attempt_fingerprint": MODULE.attempt_fingerprint(passages)},
            "samples": samples,
            "asr": {"status": "FAIL", "reports": []},
            "safety": {
                "audio_generated": True,
                "provider_calls": 0,
                "upload_performed": False,
                "publication_performed": False,
                "release_gate_mutated": False,
            },
        }

    def test_profile_is_exactly_bound_to_controlled_gift_passages(self):
        chapter, passages = MODULE.controlled_source(ROOT, "the-gift-of-the-magi")
        self.assertEqual(
            chapter,
            ROOT / "data/controlled_publications/the-gift-of-the-magi/chapters/chapter-001.json",
        )
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            tuple(item["text_sha256"] for item in passages),
            MODULE.EXPECTED_PASSAGE_HASHES,
        )
        self.assertEqual(sum(item["characters"] for item in passages), 1765)

    def test_all_other_slugs_fail_closed(self):
        for slug in ("the-open-window", "the-necklace", "dracula"):
            with self.subTest(slug=slug):
                with self.assertRaisesRegex(MODULE.KokoroTitlePilotError, "not allowed"):
                    MODULE.controlled_source(ROOT, slug)

    def test_attempt_is_distinct_from_every_known_failed_gift_fingerprint(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        self.assertEqual(
            fingerprint,
            "bf5ff8b24d23e4ae912d332b247d26d5efb60eeb0b91ebad0bc179e40a7ea015",
        )
        self.assertNotIn(fingerprint, MODULE.KNOWN_GIFT_FAILED_FINGERPRINTS)

    def test_generation_and_asr_artifact_contract_is_pinned(self):
        self.assertEqual(MODULE.MODEL_REVISION, "f3ff3571791e39611d31c381e3a41a3af07b4987")
        self.assertEqual(
            MODULE.MODEL_SHA256,
            "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
        )
        self.assertEqual(
            MODULE.CONFIG_SHA256,
            "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
        )
        self.assertEqual(
            MODULE.VOICE_SHA256,
            "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
        )
        self.assertEqual(
            MODULE.WHISPER_SHA256,
            "d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f",
        )

    def test_asr_reverification_config_is_hash_bound(self):
        samples = [
            {
                "passage_id": passage_id,
                "audio_sha256": audio_hash,
            }
            for passage_id, audio_hash in MODULE.EXPECTED_EXISTING_AUDIO_HASHES.items()
        ]
        self.assertEqual(
            MODULE.asr_config_fingerprint(samples),
            "1b932d7d1193947aad72e51cc2deba889a4c09468b21618d02b21b38db124755",
        )
        self.assertEqual(
            MODULE.ASR_PROMPT_POLICY["sacrifice_dialogue"], "no_prompt"
        )
        self.assertEqual(
            MODULE.ASR_PROMPT_POLICY["opening_money"],
            "canonical_vocabulary_prompt",
        )

    def test_completed_exact_attempt_cannot_repeat(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "prior.json"
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
                with self.assertRaisesRegex(MODULE.KokoroTitlePilotError, "already generated"):
                    MODULE.ensure_not_repeated(fingerprint, output)

    def test_preflight_record_does_not_poison_first_execution(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "preflight.json"
            output.write_text(
                json.dumps(
                    {
                        "engine": {"attempt_fingerprint": fingerprint},
                        "safety": {"audio_generated": False},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
                MODULE.ensure_not_repeated(fingerprint, output)

    def test_persisted_completed_fingerprint_is_rejected(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-output.json"
            with self.assertRaisesRegex(
                MODULE.KokoroTitlePilotError,
                "attempt fingerprint already exists",
            ):
                MODULE.ensure_not_repeated(fingerprint, output)

    def test_public_audio_paths_are_rejected(self):
        with self.assertRaisesRegex(MODULE.KokoroTitlePilotError, "public audio path"):
            MODULE.assert_private_audio_path(ROOT / "frontend/public/audio/gift")
        with self.assertRaisesRegex(MODULE.KokoroTitlePilotError, "public audio path"):
            MODULE.assert_private_audio_path(ROOT / "frontend/build/audio/gift")

    def test_paid_lock_requires_safe_state_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "none", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            before = lock.read_bytes()
            snapshot = MODULE.lock_snapshot(lock)
            self.assertEqual(lock.read_bytes(), before)
            self.assertTrue(snapshot["read_only"])
            lock.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "someone", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MODULE.KokoroTitlePilotError, "current holder"):
                MODULE.lock_snapshot(lock)

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "artifact.bin"
            candidate.write_bytes(b"not-the-pinned-artifact")
            with self.assertRaisesRegex(MODULE.KokoroTitlePilotError, "SHA-256 mismatch"):
                MODULE.verify_hash(candidate, "0" * 64, "model")

    def test_preflight_contains_no_release_or_provider_side_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "none", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            fake_paths = {
                "model": root / "model",
                "config": root / "config",
                "voice": root / "voice",
                "whisper": root / "whisper",
            }
            fake_evidence = {name: {"path": str(path), "sha256": name} for name, path in fake_paths.items()}
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()), mock.patch.object(
                MODULE, "validate_artifacts", return_value=(fake_paths, fake_evidence)
            ), mock.patch.object(MODULE, "runtime_evidence", return_value={"pinned": True}):
                payload, _passages, _artifacts = MODULE.preflight(
                    asset_root=ROOT,
                    slug=MODULE.ALLOWED_SLUG,
                    profile=MODULE.PROFILE_ID,
                    artifact_dir=root,
                    whisper_cache_dir=root,
                    private_output_dir=root / "private-audio",
                    output=root / "evidence.json",
                    paid_lock=lock,
                )
            self.assertEqual(payload["status"], "READY_FOR_PRIVATE_REPRESENTATIVE_EXECUTION")
            self.assertEqual(payload["safety"]["provider_calls"], 0)
            self.assertFalse(payload["safety"]["audio_generated"])
            self.assertFalse(payload["safety"]["upload_performed"])
            self.assertFalse(payload["safety"]["publication_performed"])
            self.assertFalse(payload["safety"]["release_gate_mutated"])
            self.assertFalse(payload["scope"]["full_title_generated"])

    def test_source_equivalences_are_passage_scoped_and_do_not_discard_speech(self):
        opening, opening_applied = MODULE.apply_source_equivalences(
            "opening_money", "$1.87. That was all. Three times: $1.87."
        )
        self.assertEqual(opening.count("one dollar and eighty-seven cents"), 2)
        self.assertEqual(opening_applied[0]["match_count"], 2)
        hair, hair_applied = MODULE.apply_source_equivalences(
            "hair_sale_dialogue", "Take your hat off."
        )
        self.assertEqual(hair, "Take yer hat off.")
        self.assertEqual(hair_applied[0]["match_count"], 1)
        sacrifice, sacrifice_applied = MODULE.apply_source_equivalences(
            "sacrifice_dialogue", "I've got for you. Thank you."
        )
        self.assertEqual(sacrifice, "I've got for you. Thank you.")
        self.assertEqual(sacrifice_applied, [])

    def test_ordered_integrity_passes_exact_and_rejects_unexpected_speech(self):
        exact = MODULE.ordered_token_integrity(
            "I've got a gift for you.", "I've got a gift for you."
        )
        self.assertEqual(exact["score"], 10.0)
        self.assertEqual(exact["coverage"], 1.0)
        self.assertTrue(exact["ordered_content_integrity_pass"])
        unexpected = MODULE.ordered_token_integrity(
            "I've got a gift for you.", "I've got a gift for you. Thank you."
        )
        self.assertFalse(unexpected["ordered_content_integrity_pass"])
        self.assertFalse(unexpected["no_unexpected_content"])
        self.assertIn("thank", unexpected["unexpected_tokens"])
        self.assertTrue(unexpected["first_words_match"])

    def test_existing_audio_validation_is_exactly_hash_bound(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        with tempfile.TemporaryDirectory() as temporary:
            private = Path(temporary) / "private"
            private.mkdir()
            samples = []
            hashes = {}
            for passage in passages:
                passage_id = passage["passage_id"]
                audio = private / f"{passage_id}.wav"
                audio.write_bytes(f"audio:{passage_id}".encode())
                audio_hash = MODULE.sha256_file(audio)
                hashes[passage_id] = audio_hash
                samples.append(
                    {
                        "passage_id": passage_id,
                        "source_text_sha256": passage["text_sha256"],
                        "audio_path": str(audio),
                        "audio_sha256": audio_hash,
                        "objective_format_pass": True,
                    }
                )
            payload = self.generated_payload(samples)
            with mock.patch.object(MODULE, "EXPECTED_EXISTING_AUDIO_HASHES", hashes):
                validated, snapshot = MODULE.validate_existing_samples(payload, passages)
                self.assertEqual(len(validated), 4)
                self.assertEqual(snapshot, hashes)
                payload["samples"][0]["audio_sha256"] = "0" * 64
                with self.assertRaisesRegex(
                    MODULE.KokoroTitlePilotError, "audio hash changed"
                ):
                    MODULE.validate_existing_samples(payload, passages)

    def test_asr_reverify_never_resynthesizes_and_preserves_lock(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        samples = [
            {
                "passage_id": passage["passage_id"],
                "audio_sha256": MODULE.EXPECTED_EXISTING_AUDIO_HASHES[passage["passage_id"]],
            }
            for passage in passages
        ]
        snapshot = {
            item["passage_id"]: item["audio_sha256"] for item in samples
        }
        payload = self.generated_payload(samples)
        config_fingerprint = MODULE.asr_config_fingerprint(samples)
        asr_result = {
            "status": "PASS",
            "config_fingerprint": config_fingerprint,
            "reports": [],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "none", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            lock_before = lock.read_bytes()
            with mock.patch.object(
                MODULE,
                "validate_existing_samples",
                return_value=(samples, snapshot),
            ) as validate_mock, mock.patch.object(
                MODULE, "verify_hash"
            ), mock.patch.object(
                MODULE, "runtime_evidence", return_value={"pinned": True}
            ), mock.patch.object(
                MODULE, "run_asr", return_value=asr_result
            ), mock.patch.object(
                MODULE, "synthesize", side_effect=AssertionError("resynthesis forbidden")
            ) as synthesize_mock:
                code, updated = MODULE.asr_reverify_existing(
                    payload=payload,
                    asset_root=ROOT,
                    whisper_cache_dir=root,
                    paid_lock=lock,
                )
            self.assertEqual(code, 0)
            self.assertEqual(validate_mock.call_count, 2)
            synthesize_mock.assert_not_called()
            self.assertEqual(lock.read_bytes(), lock_before)
            self.assertTrue(updated["safety"]["paid_tts_lock_unchanged"])
            self.assertFalse(updated["safety"]["resynthesis_performed"])
            self.assertEqual(updated["safety"]["listening_provider_calls"], 0)
            self.assertFalse(updated["safety"]["upload_performed"])
            self.assertFalse(updated["safety"]["publication_performed"])

    def test_asr_reverify_cli_does_not_require_synthesis_artifact_arguments(self):
        args = MODULE.parse_args(
            [
                "--asr-reverify-existing",
                "--slug",
                MODULE.ALLOWED_SLUG,
                "--profile",
                MODULE.PROFILE_ID,
                "--whisper-cache-dir",
                "/private/tmp/whisper",
                "--output",
                "/private/tmp/evidence.json",
                "--paid-lock",
                "/private/tmp/paid_tts.lock",
            ]
        )
        self.assertTrue(args.asr_reverify_existing)
        self.assertIsNone(args.artifact_dir)
        self.assertIsNone(args.private_output_dir)


if __name__ == "__main__":
    unittest.main()
