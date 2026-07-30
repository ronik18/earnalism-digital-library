#!/usr/bin/env python3
"""Tests for the one-shot private D19 Indic Parler generator."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import wave


SCRIPT = Path(__file__).with_name("sprint1_d19_indic_parler_private_generator.py")
SPEC = importlib.util.spec_from_file_location("d19_indic_parler_generator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.PREFLIGHT.ROOT


class D19IndicParlerPrivateGeneratorTests(unittest.TestCase):
    def _passages(self):
        return MODULE.PREFLIGHT.controlled_source(REPO, MODULE.SLUG)[2]

    def test_exact_fingerprint_passage_order_and_engine_are_bound(self) -> None:
        passages = self._passages()
        self.assertEqual(
            MODULE.PREFLIGHT.attempt_fingerprint(passages),
            MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
        )
        passage = MODULE._passage_contract(passages)
        self.assertEqual(
            tuple(item["passage_id"] for item in passage["passages"]),
            MODULE.EXPECTED_PASSAGE_IDS,
        )
        engine = MODULE._engine_contract(
            model_artifacts=MODULE.PREFLIGHT.MODEL_ARTIFACTS,
            description_tokenizer_artifacts=(MODULE.DESCRIPTION_TOKENIZER_ARTIFACTS),
        )
        self.assertEqual(engine["voice"], "Aditi")
        self.assertEqual(engine["model_revision"], MODULE.PREFLIGHT.MODEL_REVISION)
        self.assertEqual(engine["random_seed"], MODULE.PREFLIGHT.RANDOM_SEED)
        self.assertIs(engine["browser_or_system_speech_fallback"], False)
        self.assertFalse(engine["network_access_allowed"])

    def test_wrong_snapshot_and_nonempty_output_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            MODULE.D19IndicParlerGeneratorError, "exact pinned local snapshot"
        ):
            MODULE._assert_exact_snapshot(
                Path("/tmp/not-the-model"), MODULE.MODEL_SNAPSHOT, "model"
            )
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / "attempt"
            private.mkdir()
            (private / "partial.wav").write_bytes(b"not-audio")
            with self.assertRaisesRegex(
                MODULE.D19IndicParlerGeneratorError, "already contains"
            ), mock.patch.object(
                MODULE,
                "_assert_exact_snapshot",
                side_effect=lambda value, _expected, _label: value,
            ):
                MODULE.build_execution_preflight(
                    asset_root=REPO,
                    slug=MODULE.SLUG,
                    profile=MODULE.PROFILE,
                    model_snapshot=Path(tmp) / "model",
                    description_tokenizer_snapshot=Path(tmp) / "description",
                    private_output_dir=private,
                    evidence_output=Path(tmp) / "evidence.json",
                    require_exact_runtime=False,
                )

    def test_attempt_marker_consumes_fingerprint_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private = Path(tmp) / "private"
            payload = {"generation_contract": {"generation_contract_sha256": "a" * 64}}
            marker = MODULE._write_attempt_marker(private, payload)
            record = json.loads(marker.read_text(encoding="utf-8"))
            self.assertTrue(record["attempt_consumed"])
            self.assertEqual(
                record["attempt_fingerprint"],
                MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
            )
            with self.assertRaises(FileExistsError):
                MODULE._write_attempt_marker(private, payload)

    def test_ffprobe_accepts_only_mono_44100_pcm16(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "test.wav"
            with wave.open(str(target), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(44_100)
                wav.writeframes(struct.pack("<h", 100) * 44_100)
            report = MODULE._ffprobe(target)
            self.assertEqual(report["codec_name"], "pcm_s16le")
            self.assertEqual(report["sample_rate_hz"], 44_100)
            self.assertEqual(report["channels"], 1)
            self.assertEqual(report["duration_seconds"], 1.0)

    def test_failure_payload_never_claims_qa_sync_or_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                raise RuntimeError("bounded failure")
            except RuntimeError as exc:
                payload = MODULE.failure_payload(
                    base={"safety": {"audio_generated": False}},
                    private_dir=Path(tmp),
                    exc=exc,
                )
        self.assertEqual(
            payload["status"], "PRIVATE_GENERATION_FAILED_FINGERPRINT_CONSUMED"
        )
        self.assertEqual(payload["go_no_go"], "NO_GO_DO_NOT_RETRY_EXACT_FINGERPRINT")
        self.assertTrue(payload["safety"]["attempt_consumed"])
        self.assertFalse(payload["safety"]["asr_run"])
        self.assertFalse(payload["safety"]["listening_qa_run"])
        self.assertFalse(payload["safety"]["sync_generated"])
        self.assertFalse(payload["safety"]["upload_performed"])
        self.assertFalse(payload["safety"]["release_gate_mutated"])
        self.assertFalse(payload["safety"]["publication_performed"])
        self.assertFalse(payload["sync"]["estimated_sync_generated"])

    def test_static_scope_has_no_network_upload_or_release_path(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("local_files_only=True", source)
        self.assertIn('os.environ["HF_HUB_OFFLINE"] = "1"', source)
        for forbidden in (
            "requests.",
            "urllib.request",
            "boto3",
            "upload_file",
            "frontend/public/audio",
            "frontend/build/audio",
            "speechSynthesis",
        ):
            self.assertNotIn(forbidden, source)

    def test_committed_generation_evidence_is_hash_bound_and_audio_hidden(
        self,
    ) -> None:
        evidence_path = (
            REPO / "internal/audiobook_lab/sprint1_publication/title_runs/"
            "book-d19e96859f_indic_parler_aditi_private_generation_v1.json"
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(
            evidence["status"],
            "PRIVATE_REPRESENTATIVE_AUDIO_GENERATED_AWAITING_ASR",
        )
        self.assertEqual(
            evidence["engine"]["attempt_fingerprint"],
            MODULE.EXPECTED_ATTEMPT_FINGERPRINT,
        )
        self.assertEqual(
            evidence["code"]["generator_sha256"],
            MODULE.PREFLIGHT.sha256_file(SCRIPT),
        )
        self.assertEqual(
            [item["passage_id"] for item in evidence["samples"]],
            list(MODULE.EXPECTED_PASSAGE_IDS),
        )
        self.assertTrue(
            all(item["objective_format_pass"] for item in evidence["samples"])
        )
        self.assertEqual(evidence["objective_audio_format"]["status"], "PASS")
        self.assertTrue(evidence["safety"]["attempt_consumed"])
        self.assertTrue(evidence["safety"]["audio_generated"])
        self.assertFalse(evidence["safety"]["asr_run"])
        self.assertFalse(evidence["safety"]["listening_qa_run"])
        self.assertFalse(evidence["safety"]["sync_generated"])
        self.assertFalse(evidence["safety"]["upload_performed"])
        self.assertFalse(evidence["safety"]["release_gate_mutated"])
        self.assertFalse(evidence["safety"]["publication_performed"])
        self.assertEqual(
            evidence["safety"]["public_audio_status"], "AUDIO_HIDDEN_NOT_PUBLIC"
        )


if __name__ == "__main__":
    unittest.main()
