#!/usr/bin/env python3
"""Tests for the dry-run-only Désirée's Baby Kokoro preflight."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_kokoro_desirees_baby_private_preflight.py")
SPEC = importlib.util.spec_from_file_location("desirees_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.locate_repo(SCRIPT)


class DesireesBabyPreflightTests(unittest.TestCase):
    def test_exact_four_canonical_risk_passages(self) -> None:
        _, _, passages = MODULE.validate_catalog(REPO)
        self.assertEqual(
            [p["id"] for p in passages],
            ["opening_names", "maternal_dialogue", "accusation_dialogue", "final_revelation"],
        )
        self.assertEqual(sum(p["characters"] for p in passages), 1893)
        self.assertEqual(
            [p["sha256"] for p in passages],
            [spec["sha256"] for spec in MODULE.PASSAGE_SPECS],
        )

    def test_fingerprint_is_title_specific_and_not_a_prior_google_attempt(self) -> None:
        _, _, passages = MODULE.validate_catalog(REPO)
        contract = MODULE.attempt_contract(passages)
        fingerprint = hashlib.sha256(MODULE.canonical_json(contract)).hexdigest()
        self.assertEqual(contract["slug"], "dsires-baby")
        self.assertEqual(contract["provider_family"], "local_kokoro")
        self.assertEqual(contract["seed"], 2026071903)
        self.assertNotIn(fingerprint, MODULE.KNOWN_FAILED_FINGERPRINTS)
        self.assertNotIn(fingerprint, MODULE.KNOWN_PRIOR_CANDIDATE_AUDIO_HASHES)
        self.assertEqual(
            fingerprint,
            "b07e30881ec1c1a04944c8f2ba5ccc1b94bf24dc176a784ae12963b9e072f266",
        )

    def test_catalog_audio_hidden_is_fail_closed(self) -> None:
        real_load = MODULE.load_json

        def modified_load(path: Path):
            data = real_load(path)
            if path.name == "public_book.json":
                data = copy.deepcopy(data)
                data["audiobook_enabled"] = True
            return data

        with mock.patch.object(MODULE, "load_json", side_effect=modified_load):
            with self.assertRaisesRegex(MODULE.PreflightError, "audio must remain hidden"):
                MODULE.validate_catalog(REPO)

    def test_public_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "public/static"):
            MODULE.validate_private_output(REPO, Path("frontend/public/desiree"))

    def test_lock_snapshot_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "none", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            before = lock.read_bytes()
            snapshot = MODULE.snapshot_lock(lock)
            self.assertEqual(before, lock.read_bytes())
            self.assertTrue(snapshot["unchanged"])

    def test_prior_executed_fingerprint_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "internal/earnalism_intelligence").mkdir(parents=True)
            fingerprint = "a" * 64
            path = root / "internal/earnalism_intelligence/provider_performance_memory.json"
            path.write_text(
                json.dumps(
                    {
                        "attempt_fingerprint": fingerprint,
                        "safety": {"audio_generated": True},
                    }
                ),
                encoding="utf-8",
            )
            hits = MODULE.find_prior_execution(root, fingerprint, root / "missing.json")
            self.assertEqual(len(hits), 1)

    def test_unexecuted_dry_run_fingerprint_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "internal/earnalism_intelligence").mkdir(parents=True)
            fingerprint = "b" * 64
            path = root / "internal/earnalism_intelligence/provider_performance_memory.json"
            path.write_text(
                json.dumps(
                    {
                        "fingerprint": fingerprint,
                        "safety": {"audio_generated": False, "synthesis_performed": False},
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                MODULE.find_prior_execution(root, fingerprint, root / "missing.json"), []
            )

    def test_non_dry_run_cli_is_refused(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("choose exactly one", result.stderr)

    def test_wrong_slug_and_profile_are_refused_before_preflight(self) -> None:
        for arguments in (
            ["--dry-run", "--slug", "the-open-window"],
            ["--dry-run", "--profile", "generic-v1"],
        ):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), *arguments],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("only the pinned", result.stderr)

    def test_pinned_constants_match_expected_runtime_contract(self) -> None:
        self.assertEqual(MODULE.MODEL_REVISION, "f3ff3571791e39611d31c381e3a41a3af07b4987")
        self.assertEqual(MODULE.VOICE, "af_bella")
        self.assertEqual(
            MODULE.ARTIFACTS["voice"][1],
            "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6",
        )
        self.assertEqual(MODULE.RUNTIME_VERSIONS["kokoro"], "0.9.4")
        self.assertEqual(MODULE.RUNTIME_VERSIONS["openai-whisper"], "20250625")

    def test_execution_contract_is_bound_without_changing_preflight_fingerprint(self) -> None:
        _, _, passages = MODULE.validate_catalog(REPO)
        base = hashlib.sha256(MODULE.canonical_json(MODULE.attempt_contract(passages))).hexdigest()
        g2p = [
            {"passage_id": spec["id"], "phoneme_sha256": phoneme_hash}
            for spec, phoneme_hash in zip(
                MODULE.PASSAGE_SPECS,
                (
                    "8a5ca1ae0fc84229e0b0a09b6af331204f2c887c277884ae0625dca2f5e8f6ba",
                    "4863127e5cd9d43dc94820e9869ac857fb5fccc32aee149542fd6fde26b25eb0",
                    "e9d1459f312b86b5da287d9cb38dd65a5c7ad530bff884cf4da6f07c45364418",
                    "0775bd568265592eea8ba3d8e8b257af7b780c94d9c0a20c838f0c87b1d64c6c",
                ),
            )
        ]
        execute = MODULE.execution_contract(base, g2p)
        self.assertEqual(
            base,
            "b07e30881ec1c1a04944c8f2ba5ccc1b94bf24dc176a784ae12963b9e072f266",
        )
        self.assertEqual(
            hashlib.sha256(MODULE.canonical_json(execute)).hexdigest(),
            "66e0b11cca0c530679ffda849d1069dd4f3f5d6a76ed0b756f719f86256284d3",
        )
        self.assertEqual(execute["source_equivalence_policy"], [])
        self.assertFalse(execute["g2p_fallback_enabled"])

    def test_strict_g2p_rejects_unresolved_token(self) -> None:
        class Token:
            text = "Désirée"
            phonemes = ""

        class G2P:
            def __call__(self, _text):
                return "", [Token()]

        passage = {
            "id": "opening_names",
            "text": "Désirée",
            "sha256": hashlib.sha256("Désirée".encode()).hexdigest(),
        }
        with mock.patch.object(MODULE, "configured_g2p", return_value=G2P()):
            with self.assertRaisesRegex(MODULE.PreflightError, "fallback is disabled"):
                MODULE.validate_g2p_passages([passage])

    def test_asr_integrity_does_not_normalize_unapproved_name_equivalence(self) -> None:
        metrics = MODULE.ordered_token_integrity(
            "Désirée went home in silence.", "Desiree went home in silence."
        )
        self.assertFalse(metrics["ordered_content_integrity_pass"])
        self.assertFalse(metrics["no_missing_content"])
        self.assertFalse(metrics["no_unexpected_content"])

    def test_one_shot_synthesis_refuses_nonempty_private_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / "already-used"
            private.mkdir()
            (private / "sample.wav").write_bytes(b"existing")
            with self.assertRaisesRegex(MODULE.PreflightError, "one-shot execution refused"):
                MODULE.synthesize([], Path(tmp), private)

    def test_execute_preserves_lock_and_never_widens_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {"status": "active", "current_holder": "none", "allowed_next_holders": []}
                ),
                encoding="utf-8",
            )
            lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()
            report = {
                "paid_tts_lock": {"sha256_before": lock_hash},
                "representative_passages": [{"id": "sample", "text": "exact", "sha256": "x"}],
                "execution_contract": {"fingerprint": "bound"},
                "private_output": {},
                "safety": {},
                "editorial": {},
                "release": {},
            }
            samples = [{"passage_id": "sample", "objective_format_pass": True}]
            asr = {"status": "PASS", "reports": []}
            before = lock.read_bytes()
            with mock.patch.object(MODULE, "synthesize", return_value=samples), mock.patch.object(
                MODULE, "run_asr", return_value=asr
            ):
                result = MODULE.execute_representative(
                    report, root, root / "medium.en.pt", lock, root / "private"
                )
            self.assertEqual(before, lock.read_bytes())
            self.assertTrue(result["safety"]["audio_generated"])
            self.assertTrue(result["safety"]["asr_executed"])
            self.assertFalse(result["safety"]["full_title_generated"])
            self.assertFalse(result["safety"]["upload_performed"])
            self.assertFalse(result["safety"]["publication_performed"])
            self.assertFalse(result["safety"]["release_truth_mutated"])

    def test_retained_one_shot_evidence_is_hash_bound_and_failed_closed(self) -> None:
        evidence_path = (
            REPO
            / "internal/audiobook_lab/sprint1_publication/title_runs/"
            "dsires-baby_kokoro_af_bella_representative_preflight_v1.json"
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertIn(
            evidence["status"],
            {
                "BLOCKED_REPRESENTATIVE_ASR_SOURCE_GATE",
                "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
            },
        )
        self.assertEqual(
            evidence["execution"]["execution_fingerprint"],
            "66e0b11cca0c530679ffda849d1069dd4f3f5d6a76ed0b756f719f86256284d3",
        )
        self.assertEqual(
            {
                item["passage_id"]: item["audio_sha256"]
                for item in evidence["execution"]["samples"]
            },
            {
                "opening_names": "fece6253f13c7655f195dd5a7ca27f13e33a82b713da6a02e2f3ff6b408b8abf",
                "maternal_dialogue": "b490ace6cac89b381146236b44d0ce8458ca906a3379ddcf0e46adf3e15381ae",
                "accusation_dialogue": "981beef0d13a017f7c4e2f43a69262bc3455bdb7f27f113b8478c4e11dfaf953",
                "final_revelation": "4cef4b68b3abec2fceaa068fa63b81c0e004061fac7a2fbc6e23c3c502627ced",
            },
        )
        self.assertEqual(evidence["execution"]["asr"]["status"], "FAIL")
        self.assertTrue(evidence["paid_tts_lock"]["unchanged"])
        self.assertFalse(evidence["safety"]["full_title_generated"])
        self.assertFalse(evidence["safety"]["upload_performed"])
        self.assertFalse(evidence["safety"]["publication_performed"])
        self.assertFalse(evidence["safety"]["release_truth_mutated"])

    def test_authorized_equivalences_alone_repair_retained_raw_transcripts(self) -> None:
        evidence = json.loads(
            (
                REPO
                / "internal/audiobook_lab/sprint1_publication/title_runs/"
                "dsires-baby_kokoro_af_bella_representative_preflight_v1.json"
            ).read_text(encoding="utf-8")
        )
        passages = {item["id"]: item for item in evidence["representative_passages"]}
        for original in evidence["execution"]["asr"]["reports"]:
            passage_id = original["passage_id"]
            repaired, applications = MODULE.apply_source_equivalences(
                passage_id, original["transcript"]
            )
            metrics = MODULE.ordered_token_integrity(passages[passage_id]["text"], repaired)
            self.assertEqual(metrics["score"], 10.0)
            self.assertEqual(metrics["coverage"], 1.0)
            self.assertTrue(metrics["first_words_match"])
            self.assertTrue(metrics["last_words_match"])
            self.assertTrue(metrics["ordered_content_integrity_pass"])
            expected = sum(
                int(rule["expected_count"])
                for rule in MODULE.SOURCE_EQUIVALENCE_POLICY[passage_id]
            )
            self.assertEqual(sum(item["match_count"] for item in applications), expected)

    def test_equivalence_policy_fails_if_exact_authorized_pair_is_absent(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightError, "equivalence count mismatch"):
            MODULE.apply_source_equivalences("opening_names", "L’Abri is already canonical")

    def test_asr_repair_fingerprint_is_exact_and_audio_bound(self) -> None:
        evidence = json.loads(
            (
                REPO
                / "internal/audiobook_lab/sprint1_publication/title_runs/"
                "dsires-baby_kokoro_af_bella_representative_preflight_v1.json"
            ).read_text(encoding="utf-8")
        )
        fingerprint = MODULE.asr_repair_fingerprint(evidence["execution"]["samples"])
        self.assertEqual(
            fingerprint,
            "63c614ca791064d7bdcaaf8ad595c20198af55295a7d4b3a08d7fe4106ebac9e",
        )

    def test_completed_asr_repair_is_preserved_and_cannot_repeat(self) -> None:
        evidence_path = (
            REPO
            / "internal/audiobook_lab/sprint1_publication/title_runs/"
            "dsires-baby_kokoro_af_bella_representative_preflight_v1.json"
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(
            evidence["status"],
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
        )
        self.assertEqual(evidence["execution"]["asr_history"][0]["status"], "FAIL")
        self.assertTrue(
            evidence["execution"]["asr_history"][0][
                "original_transcripts_and_operations_preserved"
            ]
        )
        self.assertEqual(evidence["execution"]["asr_repair"]["status"], "PASS")
        with mock.patch.object(MODULE, "run_asr_repair") as rerun:
            with self.assertRaisesRegex(MODULE.PreflightError, "already executed"):
                MODULE.asr_repair_existing(
                    REPO,
                    evidence,
                    MODULE.DEFAULT_WHISPER_MODEL,
                    MODULE.DEFAULT_PAID_LOCK,
                )
            rerun.assert_not_called()


if __name__ == "__main__":
    unittest.main()
