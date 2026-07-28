#!/usr/bin/env python3
"""Tests for Alice's bounded retained-WAV ASR repair."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_alice_kokoro_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("alice_asr_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AliceASRRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "repair.json"

    def exact_decoder(self, _model, _arm, sample):
        _chapter, passages = MODULE.PROFILE.controlled_source(
            MODULE.ROOT, MODULE.PROFILE.SLUG
        )
        by_id = {str(item["passage_id"]): str(item["text"]) for item in passages}
        return by_id[str(sample["passage_id"])]

    def test_input_is_bound_to_exact_retained_wavs_and_prior_transcripts(self) -> None:
        evidence, samples, passages = MODULE.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(
            evidence["asr"]["config_fingerprint"],
            MODULE.EXPECTED_PRIOR_ASR_FINGERPRINT,
        )
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            {item["passage_id"]: item["audio_sha256"] for item in samples},
            {
                key: value["audio_sha256"]
                for key, value in MODULE.EXPECTED_SAMPLE_BINDINGS.items()
            },
        )

    def test_only_armchair_tokenization_equivalence_is_allowed(self) -> None:
        tea, applied = MODULE.apply_equivalences(
            "mad_tea_party_exchange", "and sat down in a large armchair"
        )
        self.assertEqual(tea, "and sat down in a large arm chair")
        self.assertEqual(len(applied), 1)
        with self.assertRaisesRegex(
            MODULE.AliceASRRepairError, "count mismatch"
        ):
            MODULE.apply_equivalences(
                "mad_tea_party_exchange", "an armchair beside another armchair"
            )

    def test_missing_repeated_i_and_the_end_cannot_be_normalized(self) -> None:
        transcript = "Who are you? I hardly know. The end."
        evaluated, applied = MODULE.apply_equivalences(
            "caterpillar_identity_dialogue", transcript
        )
        self.assertEqual(evaluated, transcript)
        self.assertEqual(applied, [])

    def test_fingerprint_binds_prompted_and_unprompted_decoder_arms(self) -> None:
        self.assertEqual(
            MODULE.repair_fingerprint(),
            "59ee181f736e534ccab753a355696de7cc2d40c22e647e68092fec3a056ba20c",
        )
        self.assertIsNotNone(MODULE.DECODING_ARMS[0]["initial_prompt"])
        self.assertEqual(MODULE.DECODING_ARMS[0]["beam_size"], 5)
        self.assertIsNone(MODULE.DECODING_ARMS[1]["initial_prompt"])

    def test_dry_run_never_loads_whisper_or_writes_output(self) -> None:
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                dry_run=True,
            )
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "DRY_RUN_PASS")
        self.assertFalse(result["asr_performed"])
        self.assertFalse(result["synthesis_performed"])
        self.assertFalse(self.output.exists())

    def test_exact_transcripts_pass_without_resynthesis(self) -> None:
        input_before = MODULE.DEFAULT_INPUT.read_bytes()
        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                model_loader=lambda _path: object(),
                decoder=self.exact_decoder,
            )
        self.assertEqual(code, 0)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
        )
        self.assertTrue(all(item["score"] == 10.0 for item in result["asr"]["reports"]))
        self.assertTrue(all(item["pass"] for item in result["asr"]["reports"]))
        self.assertFalse(result["asr_repair"]["resynthesis_performed"])
        self.assertEqual(MODULE.DEFAULT_INPUT.read_bytes(), input_before)

    def test_extra_ending_fails_objective_integrity(self) -> None:
        def bad_decoder(model, arm, sample):
            transcript = self.exact_decoder(model, arm, sample)
            if sample["passage_id"] == "caterpillar_identity_dialogue":
                return f"{transcript} The end."
            return transcript

        with mock.patch.object(MODULE, "NO_REPEAT_FILES", ()):
            code, result = MODULE.execute(
                MODULE.DEFAULT_INPUT,
                self.output,
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                model_loader=lambda _path: object(),
                decoder=bad_decoder,
            )
        self.assertEqual(code, 4)
        report = next(
            item
            for item in result["asr"]["reports"]
            if item["passage_id"] == "caterpillar_identity_dialogue"
        )
        self.assertFalse(report["no_unexpected_content"])
        self.assertFalse(report["pass"])

    def test_public_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            MODULE.AliceASRRepairError, "public output"
        ):
            MODULE.execute(
                MODULE.DEFAULT_INPUT,
                MODULE.ROOT / "frontend/public/audio/alice-repair.json",
                MODULE.DEFAULT_WHISPER_CACHE,
                MODULE.DEFAULT_PAID_LOCK,
                dry_run=True,
            )

    def test_audio_hash_drift_fails_before_decoder(self) -> None:
        payload = json.loads(MODULE.DEFAULT_INPUT.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(payload)
        mutated["samples"][0]["audio_sha256"] = "0" * 64
        local_input = self.root / "input.json"
        local_input.write_text(json.dumps(mutated), encoding="utf-8")
        with mock.patch.object(
            MODULE,
            "EXPECTED_INPUT_SHA256",
            MODULE.PROFILE.BASE.sha256_file(local_input),
        ):
            with self.assertRaisesRegex(
                MODULE.AliceASRRepairError, "sample audio_sha256"
            ):
                MODULE.validate_input(local_input)


if __name__ == "__main__":
    unittest.main()
