import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name("sprint1_cop_kokoro_private_audition.py")
SPEC = importlib.util.spec_from_file_location("sprint1_cop_kokoro_private_audition", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ROOT = Path(__file__).resolve().parents[3]


class Sprint1CopKokoroPrivateAuditionTests(unittest.TestCase):
    @staticmethod
    def safe_lock(path: Path) -> bytes:
        path.write_text(
            json.dumps(
                {
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                }
            ),
            encoding="utf-8",
        )
        return path.read_bytes()

    @staticmethod
    def fake_preflight(root: Path):
        lock = root / "paid_tts.lock"
        Sprint1CopKokoroPrivateAuditionTests.safe_lock(lock)
        paths = {
            "model": root / "model",
            "config": root / "config",
            "voice": root / "voice",
            "whisper": root / "whisper",
        }
        artifact_evidence = {
            name: {"path": str(path), "sha256": name, "size_bytes": 1}
            for name, path in paths.items()
        }
        with mock.patch.object(
            MODULE, "NO_REPEAT_FILES", ()
        ), mock.patch.object(
            MODULE, "validate_artifacts", return_value=(paths, artifact_evidence)
        ), mock.patch.object(
            MODULE, "runtime_evidence", return_value={"pinned": True}
        ), mock.patch.object(
            MODULE,
            "validate_g2p_passages",
            return_value=[
                {
                    "passage_id": passage_id,
                    "unresolved_tokens": [],
                    "fallback_enabled": False,
                }
                for passage_id in (
                    "opening_winter",
                    "waiter_dialogue",
                    "church_reckoning",
                    "ironic_ending",
                )
            ],
        ):
            payload, passages, artifacts = MODULE.preflight(
                asset_root=ROOT,
                slug=MODULE.ALLOWED_SLUG,
                profile=MODULE.PROFILE_ID,
                artifact_dir=root,
                whisper_cache_dir=root,
                private_output_dir=root / "private-audio",
                output=root / "evidence.json",
                paid_lock=lock,
            )
        return payload, passages, artifacts, lock

    def test_exact_controlled_truth_and_four_risk_passages_are_bound(self):
        chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        self.assertEqual(
            chapter,
            ROOT
            / "data/controlled_publications/the-cop-and-the-anthem/chapters/chapter-001.json",
        )
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            [item["risk"] for item in passages],
            [
                "opening_and_narrative_tone",
                "comic_dialogue_and_dialect",
                "emotional_reversal_and_restraint",
                "sustained_emotion_dialogue_and_ironic_ending",
            ],
        )
        self.assertEqual(
            tuple(item["text_sha256"] for item in passages),
            MODULE.EXPECTED_PASSAGE_HASHES,
        )
        self.assertEqual(sum(item["characters"] for item in passages), 2016)

    def test_source_title_author_reader_and_audio_hidden_truth_are_current(self):
        book = json.loads(
            (
                ROOT
                / "data/controlled_publications/the-cop-and-the-anthem/public_book.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(book["title"], MODULE.TITLE)
        self.assertEqual(book["author"], MODULE.AUTHOR)
        self.assertEqual(book["readerStatus"], "reader_ready")
        self.assertTrue(book["allowPublicReading"])
        self.assertFalse(book["audio_enabled"])
        self.assertFalse(book["audiobook_enabled"])
        self.assertEqual(book["audiobook"], {})

    def test_other_slugs_and_profiles_fail_closed(self):
        for slug in ("the-gift-of-the-magi", "the-open-window", "the-necklace"):
            with self.subTest(slug=slug):
                with self.assertRaisesRegex(MODULE.CopKokoroPilotError, "not allowed"):
                    MODULE.controlled_source(ROOT, slug)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "lock"
            self.safe_lock(lock)
            with self.assertRaisesRegex(MODULE.CopKokoroPilotError, "unsupported profile"):
                MODULE.preflight(
                    asset_root=ROOT,
                    slug=MODULE.ALLOWED_SLUG,
                    profile="gift-v1",
                    artifact_dir=root,
                    whisper_cache_dir=root,
                    private_output_dir=root / "private-audio",
                    output=root / "evidence.json",
                    paid_lock=lock,
                )

    def test_attempt_fingerprint_is_exact_and_distinct_from_google_attempts(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        self.assertEqual(
            fingerprint,
            "b693be6196019d6e44b22ac1cdcc7e1ea7099550f69eb326bb3cdacf4f27c6bf",
        )
        MODULE.ensure_materially_distinct(fingerprint)
        for blocked in MODULE.KNOWN_GOOGLE_FINGERPRINTS:
            self.assertNotEqual(fingerprint, blocked)
            self.assertFalse(fingerprint.startswith(blocked))

    def test_google_fingerprint_prefix_is_rejected(self):
        for blocked in ("bd4b31c2312dfa26", "9311f74b6465c550"):
            with self.subTest(blocked=blocked):
                with self.assertRaisesRegex(MODULE.CopKokoroPilotError, "Google fingerprint"):
                    MODULE.ensure_materially_distinct(blocked + "0" * 48)

    def test_profile_is_title_specific_and_evidence_based(self):
        self.assertEqual(MODULE.PROFILE_ID, "cop-ironic-restraint-v1")
        self.assertEqual(MODULE.SPEED, 0.98)
        self.assertEqual(MODULE.VOICE, "af_bella")
        self.assertEqual(MODULE.PRONUNCIATION_OVERRIDES["Soapy"], "sˈoʊpi")
        self.assertEqual(MODULE.PRONUNCIATION_OVERRIDES["doin'"], "dˈuːɪn")
        self.assertEqual(MODULE.PRONUNCIATION_OVERRIDES["nothin'"], "nˈʌθɪn")
        self.assertEqual(
            MODULE.SOURCE_DIALECT_PRONUNCIATION_BINDINGS["doin’"],
            {"lexicon_key": "doin'", "phonemes": "dˈuːɪn"},
        )
        self.assertEqual(
            MODULE.SOURCE_DIALECT_PRONUNCIATION_BINDINGS["Nothin’"],
            {"lexicon_key": "nothin'", "phonemes": "nˈʌθɪn"},
        )
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        ending = next(item["text"] for item in passages if item["passage_id"] == "ironic_ending")
        self.assertIn("doin’", ending)
        self.assertIn("Nothin’", ending)
        with tempfile.TemporaryDirectory() as temporary:
            payload, _passages, _artifacts, _lock = self.fake_preflight(Path(temporary))
        selection = payload["engine"]["selection_evidence"]
        self.assertEqual(selection["same_author_prior_title"], "the-gift-of-the-magi")
        self.assertEqual(selection["representative_asr_scores"], [10.0] * 4)
        self.assertGreaterEqual(min(selection["representative_listening_overall"]), 9.5)
        self.assertTrue(payload["engine"]["materially_distinct_from_prior"]["distinct"])

    def test_prior_fingerprint_is_recorded_as_pre_synthesis_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload, _passages, _artifacts, _lock = self.fake_preflight(Path(temporary))
        prior_attempts = payload["engine"]["superseded_pre_synthesis_attempts"]
        self.assertEqual(
            [item["attempt_fingerprint"] for item in prior_attempts],
            [
                "473233a16da8afc80e6a30c56a9a7d56c2bf964f7d99198d11ca6a80132df38f",
                "18caca9ef65a850cda74a27991600f6b2a640eb8100a6c1e209b46dcef4aceda",
            ],
        )
        for prior in prior_attempts:
            self.assertEqual(prior["status"], "G2P_PRECHECK_BLOCKED_BEFORE_SYNTHESIS")
            self.assertFalse(prior["audio_generated"])
            self.assertFalse(prior["asr_run"])
            self.assertEqual(prior["private_audio_files_written"], 0)
            self.assertFalse(prior["eligible_to_retry_exact_fingerprint"])
            self.assertNotEqual(
                payload["engine"]["attempt_fingerprint"], prior["attempt_fingerprint"]
            )

    def test_generation_and_asr_artifacts_are_checksum_pinned(self):
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

    def test_public_audio_paths_are_rejected(self):
        for path in (
            ROOT / "frontend/public/audio/cop",
            ROOT / "frontend/build/audio/cop",
            ROOT / "public/audio/cop",
        ):
            with self.subTest(path=path):
                with self.assertRaisesRegex(MODULE.CopKokoroPilotError, "public audio path"):
                    MODULE.assert_private_audio_path(path)

    def test_paid_lock_requires_safe_state_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "paid_tts.lock"
            before = self.safe_lock(lock)
            snapshot = MODULE.lock_snapshot(lock)
            self.assertEqual(lock.read_bytes(), before)
            self.assertTrue(snapshot["read_only"])
            lock.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "another-lane",
                        "allowed_next_holders": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MODULE.CopKokoroPilotError, "current holder"):
                MODULE.lock_snapshot(lock)

    def test_completed_exact_attempt_cannot_repeat_but_preflight_can(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence.json"
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
                with self.assertRaisesRegex(MODULE.CopKokoroPilotError, "already generated"):
                    MODULE.ensure_not_repeated(fingerprint, output)

    def test_persisted_completed_fingerprint_is_rejected(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-output.json"
            with self.assertRaisesRegex(
                MODULE.CopKokoroPilotError,
                "attempt fingerprint already exists",
            ):
                MODULE.ensure_not_repeated(fingerprint, output)

    def test_preflight_has_no_audio_provider_upload_publish_or_gate_side_effect(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload, passages, _artifacts, lock = self.fake_preflight(root)
            self.assertEqual(payload["status"], "READY_FOR_PRIVATE_REPRESENTATIVE_EXECUTION")
            self.assertEqual(len(passages), 4)
            self.assertEqual(payload["safety"]["provider_calls"], 0)
            self.assertFalse(payload["safety"]["audio_generated"])
            self.assertFalse(payload["safety"]["asr_run"])
            self.assertFalse(payload["safety"]["upload_performed"])
            self.assertFalse(payload["safety"]["publication_performed"])
            self.assertFalse(payload["safety"]["release_gate_mutated"])
            self.assertFalse(payload["scope"]["full_title_generated"])
            self.assertFalse(payload["scope"]["public_audio_hidden"] is False)
            self.assertEqual(MODULE.lock_snapshot(lock), payload["safety"]["paid_tts_lock"])

    def test_execute_contract_preserves_lock_and_remains_private_and_unpublished(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload, passages, artifacts, lock = self.fake_preflight(root)
            lock_before = lock.read_bytes()
            samples = [
                {
                    "passage_id": passage["passage_id"],
                    "source_text_sha256": passage["text_sha256"],
                    "audio_sha256": str(index) * 64,
                    "objective_format_pass": True,
                }
                for index, passage in enumerate(passages, start=1)
            ]
            asr = {"status": "PASS", "reports": [{"pass": True}] * 4}
            with mock.patch.object(MODULE, "synthesize", return_value=samples), mock.patch.object(
                MODULE, "run_asr", return_value=asr
            ):
                code, updated = MODULE.execute_private_representative(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_output_dir=root / "private-audio",
                    whisper_cache_dir=root,
                    paid_lock=lock,
                )
            self.assertEqual(code, 0)
            self.assertEqual(lock.read_bytes(), lock_before)
            self.assertEqual(
                updated["status"],
                "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
            )
            self.assertEqual(updated["safety"]["provider_calls"], 0)
            self.assertEqual(updated["safety"]["listening_provider_calls"], 0)
            self.assertFalse(updated["safety"]["upload_performed"])
            self.assertFalse(updated["safety"]["publication_performed"])
            self.assertFalse(updated["safety"]["release_gate_mutated"])
            self.assertFalse(updated["safety"]["public_audio_approved"])
            self.assertIn("INDEPENDENT_LISTENING_QA_NOT_RUN", updated["blockers_to_release"])

    def test_asr_integrity_fails_for_missing_or_reordered_content(self):
        exact = MODULE.ordered_token_integrity("Soapy came along", "Soapy came along")
        self.assertEqual(exact["score"], 10.0)
        self.assertTrue(exact["ordered_content_integrity_pass"])
        missing = MODULE.ordered_token_integrity("Soapy came along", "Soapy along")
        self.assertFalse(missing["ordered_content_integrity_pass"])
        self.assertFalse(missing["no_missing_content"])
        reordered = MODULE.ordered_token_integrity("Soapy came along", "along Soapy came")
        self.assertFalse(reordered["ordered_content_integrity_pass"])
        self.assertFalse(reordered["no_reordered_content"])

    def test_asr_reverify_policy_is_audio_hash_bound_and_unprompted_for_waiter(self):
        samples = [
            {"passage_id": passage_id, "audio_sha256": audio_hash}
            for passage_id, audio_hash in MODULE.EXPECTED_EXISTING_AUDIO_HASHES.items()
        ]
        self.assertEqual(
            MODULE.asr_reverify_config_fingerprint(samples),
            "3610d60e9094c3f80f4c22d65b63db45f622f48b7ea927301acf01a221444075",
        )
        waiter = MODULE.ASR_REVERIFY_POLICY["waiter_dialogue"]
        self.assertEqual(waiter["prompt_mode"], "no_prompt")
        self.assertEqual(waiter["beam_size"], 10)
        self.assertEqual(waiter["hallucination_silence_threshold"], 0.5)
        self.assertIsNone(
            MODULE.ASR_DIAGNOSTIC_SUMMARY["selected_unprompted_waiter"][
                "trailing_unexpected_speech"
            ]
        )
        self.assertFalse(
            MODULE.ASR_DIAGNOSTIC_SUMMARY["selected_unprompted_waiter"][
                "manual_transcript_deletion_performed"
            ]
        )

    def test_only_authorized_sound_equivalences_are_applied(self):
        opening, opening_rules = MODULE.apply_source_equivalences(
            "opening_winter", "women without seal-skin coats"
        )
        self.assertEqual(opening, "women without sealskin coats")
        self.assertEqual(opening_rules[0]["match_count"], 1)
        waiter, waiter_rules = MODULE.apply_source_equivalences(
            "waiter_dialogue",
            "No cop for yous. The callous pavement. Thank you for watching.",
        )
        self.assertEqual(
            waiter,
            "No cop for youse. The callous pavement. Thank you for watching.",
        )
        self.assertEqual(waiter_rules[0]["match_count"], 1)
        self.assertIn("Thank you for watching", waiter)
        ending, ending_rules = MODULE.apply_source_equivalences(
            "ironic_ending", "Tomorrow, what are you doing? Nothing."
        )
        self.assertEqual(ending, "to-morrow, what are you doin’? nothin’.")
        self.assertEqual(len(ending_rules), 3)
        church, church_rules = MODULE.apply_source_equivalences(
            "church_reckoning", "No change at all."
        )
        self.assertEqual(church, "No change at all.")
        self.assertEqual(church_rules, [])

    def test_existing_sample_validation_rejects_audio_hash_drift(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            samples = []
            hashes = {}
            for passage in passages:
                passage_id = passage["passage_id"]
                audio = root / f"{passage_id}.wav"
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
            payload = {
                "scope": {"slug": MODULE.ALLOWED_SLUG},
                "engine": {"attempt_fingerprint": MODULE.attempt_fingerprint(passages)},
                "safety": {
                    "audio_generated": True,
                    "provider_calls": 0,
                    "upload_performed": False,
                    "publication_performed": False,
                },
                "samples": samples,
            }
            with mock.patch.object(MODULE, "EXPECTED_EXISTING_AUDIO_HASHES", hashes):
                validated, snapshot = MODULE.validate_existing_samples(payload, passages)
                self.assertEqual(len(validated), 4)
                self.assertEqual(snapshot, hashes)
                payload["samples"][0]["audio_sha256"] = "0" * 64
                with self.assertRaisesRegex(
                    MODULE.CopKokoroPilotError, "audio hash changed"
                ):
                    MODULE.validate_existing_samples(payload, passages)

    def test_asr_only_reverify_never_resynthesizes_and_preserves_prior_failure(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        samples = [
            {
                "passage_id": passage["passage_id"],
                "audio_sha256": MODULE.EXPECTED_EXISTING_AUDIO_HASHES[
                    passage["passage_id"]
                ],
            }
            for passage in passages
        ]
        snapshot = {item["passage_id"]: item["audio_sha256"] for item in samples}
        payload = {
            "asr": {
                "status": "FAIL",
                "model": MODULE.WHISPER_MODEL,
                "model_sha256": MODULE.WHISPER_SHA256,
                "prompt_sha256": "prior",
                "reports": [{"passage_id": "waiter_dialogue", "pass": False}],
            },
            "safety": {},
            "blockers_to_release": [
                "REPRESENTATIVE_ASR_OBJECTIVE_QA_FAIL",
                "INDEPENDENT_LISTENING_QA_NOT_RUN",
            ],
        }
        repaired = {
            "status": "PASS",
            "mode": "ASR_REVERIFY_EXISTING_AUDIO_ONLY",
            "config_fingerprint": MODULE.asr_reverify_config_fingerprint(samples),
            "reports": [{"pass": True}] * 4,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "paid_tts.lock"
            lock_before = self.safe_lock(lock)
            with mock.patch.object(
                MODULE,
                "validate_existing_samples",
                return_value=(samples, snapshot),
            ) as validate_mock, mock.patch.object(
                MODULE, "verify_hash"
            ), mock.patch.object(
                MODULE, "runtime_evidence", return_value={"pinned": True}
            ), mock.patch.object(
                MODULE, "run_asr_reverify", return_value=repaired
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
            self.assertEqual(updated["asr_history"][0]["status"], "FAIL")
            self.assertTrue(updated["asr_history"][0]["preserved_before_reverify"])
            self.assertFalse(updated["safety"]["resynthesis_performed"])
            self.assertTrue(updated["safety"]["audio_hashes_unchanged"])
            self.assertEqual(updated["safety"]["listening_provider_calls"], 0)
            self.assertFalse(updated["safety"]["upload_performed"])
            self.assertFalse(updated["safety"]["publication_performed"])
            self.assertEqual(
                updated["status"],
                "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
            )

    def test_failed_asr_only_reverify_closes_lane(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        samples = [
            {
                "passage_id": passage["passage_id"],
                "audio_sha256": MODULE.EXPECTED_EXISTING_AUDIO_HASHES[
                    passage["passage_id"]
                ],
            }
            for passage in passages
        ]
        snapshot = {item["passage_id"]: item["audio_sha256"] for item in samples}
        payload = {
            "asr": {"status": "FAIL", "reports": []},
            "safety": {},
            "blockers_to_release": ["REPRESENTATIVE_ASR_OBJECTIVE_QA_FAIL"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "lock"
            self.safe_lock(lock)
            with mock.patch.object(
                MODULE, "validate_existing_samples", return_value=(samples, snapshot)
            ), mock.patch.object(MODULE, "verify_hash"), mock.patch.object(
                MODULE, "runtime_evidence", return_value={"pinned": True}
            ), mock.patch.object(
                MODULE,
                "run_asr_reverify",
                return_value={"status": "FAIL", "reports": [{"pass": False}]},
            ):
                code, updated = MODULE.asr_reverify_existing(
                    payload=payload,
                    asset_root=ROOT,
                    whisper_cache_dir=root,
                    paid_lock=lock,
                )
        self.assertEqual(code, 2)
        self.assertEqual(
            updated["status"], "PRIVATE_REPRESENTATIVE_ASR_ONLY_REPAIR_FAIL_CLOSED"
        )
        self.assertIn("ASR_ONLY_REPAIR_FAILED", updated["blockers_to_release"])
        self.assertIn("COP_REPRESENTATIVE_LANE_CLOSED", updated["blockers_to_release"])

    def test_exact_asr_only_config_cannot_run_twice(self):
        _chapter, passages = MODULE.controlled_source(ROOT, MODULE.ALLOWED_SLUG)
        samples = [
            {
                "passage_id": passage["passage_id"],
                "audio_sha256": MODULE.EXPECTED_EXISTING_AUDIO_HASHES[
                    passage["passage_id"]
                ],
            }
            for passage in passages
        ]
        snapshot = {item["passage_id"]: item["audio_sha256"] for item in samples}
        payload = {
            "asr": {
                "status": "PASS",
                "mode": "ASR_REVERIFY_EXISTING_AUDIO_ONLY",
                "config_fingerprint": MODULE.asr_reverify_config_fingerprint(samples),
            }
        }
        with mock.patch.object(
            MODULE, "validate_existing_samples", return_value=(samples, snapshot)
        ):
            with self.assertRaisesRegex(
                MODULE.CopKokoroPilotError, "already executed"
            ):
                MODULE.asr_reverify_existing(
                    payload=payload,
                    asset_root=ROOT,
                    whisper_cache_dir=Path("/private/tmp/whisper"),
                    paid_lock=Path("/private/tmp/paid_tts.lock"),
                )

    def test_execute_failure_records_asr_fail_not_stale_not_run_blockers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload, passages, artifacts, lock = self.fake_preflight(root)
            samples = [
                {
                    "passage_id": passage["passage_id"],
                    "source_text_sha256": passage["text_sha256"],
                    "audio_sha256": str(index) * 64,
                    "objective_format_pass": True,
                }
                for index, passage in enumerate(passages, start=1)
            ]
            with mock.patch.object(MODULE, "synthesize", return_value=samples), mock.patch.object(
                MODULE, "run_asr", return_value={"status": "FAIL", "reports": []}
            ):
                code, updated = MODULE.execute_private_representative(
                    payload=payload,
                    passages=passages,
                    artifacts=artifacts,
                    private_output_dir=root / "private-audio",
                    whisper_cache_dir=root,
                    paid_lock=lock,
                )
        self.assertEqual(code, 2)
        self.assertEqual(updated["status"], "PRIVATE_REPRESENTATIVE_OBJECTIVE_QA_FAIL")
        self.assertIn("REPRESENTATIVE_ASR_OBJECTIVE_QA_FAIL", updated["blockers_to_release"])
        self.assertNotIn("REPRESENTATIVE_AUDIO_NOT_GENERATED", updated["blockers_to_release"])
        self.assertNotIn("REPRESENTATIVE_ASR_NOT_RUN", updated["blockers_to_release"])

    def test_cli_exposes_only_preflight_private_execute_or_asr_reverify_modes(self):
        args = MODULE.parse_args(
            [
                "--preflight",
                "--slug",
                MODULE.ALLOWED_SLUG,
                "--profile",
                MODULE.PROFILE_ID,
                "--asset-root",
                str(ROOT),
                "--artifact-dir",
                "/private/tmp/artifacts",
                "--whisper-cache-dir",
                "/private/tmp/whisper",
                "--private-output-dir",
                "/private/tmp/cop",
                "--output",
                "/private/tmp/cop.json",
                "--paid-lock",
                "/private/tmp/paid_tts.lock",
            ]
        )
        self.assertTrue(args.preflight)
        self.assertFalse(args.execute)
        self.assertFalse(hasattr(args, "upload"))
        self.assertFalse(hasattr(args, "publish"))
        reverify = MODULE.parse_args(
            [
                "--asr-reverify-existing",
                "--slug",
                MODULE.ALLOWED_SLUG,
                "--profile",
                MODULE.PROFILE_ID,
                "--asset-root",
                str(ROOT),
                "--whisper-cache-dir",
                "/private/tmp/whisper",
                "--output",
                "/private/tmp/cop.json",
                "--paid-lock",
                "/private/tmp/paid_tts.lock",
            ]
        )
        self.assertTrue(reverify.asr_reverify_existing)
        self.assertIsNone(reverify.artifact_dir)
        self.assertIsNone(reverify.private_output_dir)


if __name__ == "__main__":
    unittest.main()
