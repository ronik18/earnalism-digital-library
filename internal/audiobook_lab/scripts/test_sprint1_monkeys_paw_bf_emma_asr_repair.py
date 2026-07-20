#!/usr/bin/env python3
"""Focused tests for the retained-WAV Monkey's Paw ``bf_emma`` repair."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_monkeys_paw_bf_emma_asr_repair.py")
SPEC = importlib.util.spec_from_file_location("monkeys_paw_bf_repair", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPAIR = MODULE.REPAIR
PROFILE = MODULE.BF_PROFILE.PROFILE_BASE
REPO = REPAIR.ROOT
PINNED_PYTHON = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/bin/python"
)


class MonkeysPawBfEmmaASRRepairTests(unittest.TestCase):
    def test_input_binds_exact_bf_emma_wavs_and_transcripts(self) -> None:
        evidence, samples, passages = REPAIR.validate_input(MODULE.DEFAULT_INPUT)
        self.assertEqual(evidence["schema"], MODULE.EXPECTED_INPUT_SCHEMA)
        self.assertEqual(evidence["status"], MODULE.EXPECTED_INPUT_STATUS)
        self.assertEqual(len(samples), 4)
        self.assertEqual(len(passages), 4)
        self.assertEqual(
            {item["passage_id"]: item["audio_sha256"] for item in samples},
            {
                key: value["audio_sha256"]
                for key, value in MODULE.EXPECTED_SAMPLE_BINDINGS.items()
            },
        )

    def test_repair_fingerprint_is_exact_and_recorded_closed(self) -> None:
        fingerprint = REPAIR.repair_fingerprint()
        self.assertEqual(
            fingerprint,
            "12a5b40c13022312a66b96adbc6e7fb6743da1efad9c20b6c5bed2f03935986e",
        )
        recorded = set()
        for path in MODULE.NO_REPEAT_FILES:
            if path.is_file():
                recorded.update(
                    REPAIR.CORE._find_fingerprints(REPAIR.CORE.read_json(path))
                )
        self.assertIn(fingerprint, recorded)

    def test_decoder_matrix_is_bounded(self) -> None:
        self.assertEqual(len(MODULE.DECODING_ARMS), 3)
        self.assertEqual(
            {arm["id"] for arm in MODULE.DECODING_ARMS},
            {
                "unprompted_beam_5",
                "unprompted_greedy",
                "canonical_vocabulary_beam_5",
            },
        )
        self.assertTrue(
            all(arm["condition_on_previous_text"] is False for arm in MODULE.DECODING_ARMS)
        )

    def test_equivalences_are_passage_bound_and_exact_count(self) -> None:
        cases = {
            "opening_domestic_tension": ("come tonight", "come to night"),
            "paw_warning_and_fate": (
                "middle ages won't and the poor",
                "middle age is wont and the paw",
            ),
            "factory_news_and_grief": ("Moore and Meggins", "maw and Meggins"),
            "final_knocking_and_third_wish": ("search of the pour", "search of the paw"),
        }
        for passage_id, (transcript, expected) in cases.items():
            evaluated, applications = REPAIR.apply_equivalences(
                passage_id, transcript
            )
            self.assertEqual(evaluated.lower(), expected.lower())
            self.assertGreaterEqual(len(applications), 1)
        with self.assertRaisesRegex(
            REPAIR.MonkeysPawASRRepairError, "equivalence count mismatch"
        ):
            REPAIR.apply_equivalences(
                "final_knocking_and_third_wish", "poor then pour"
            )

    def test_british_equivalences_are_phoneme_identical(self) -> None:
        program = """
from misaki import en as me
g=me.G2P(trf=False,british=True,fallback=None,unk='')
g.lexicon.golds.update({'Moore':'mˈɔː','moore':'mˈɔː'})
pairs=(('to-night','tonight'),('middle age is wont',"middle ages won't"),('paw','poor'),('paw','pour'),('Maw','Moore'))
for left,right in pairs:
    assert (g(left)[0] or '').replace(' ','') == (g(right)[0] or '').replace(' ',''), (left,right,g(left)[0],g(right)[0])
"""
        result = subprocess.run(
            [str(PINNED_PYTHON), "-c", program],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_mocked_exact_decoders_advance_only_to_listening(self) -> None:
        _chapters, passages = PROFILE.controlled_source(REPO, PROFILE.SLUG)
        source = {item["passage_id"]: item["text"] for item in passages}

        def decoder(_model, _arm, sample):
            return source[sample["passage_id"]]

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "repair.json"
            with mock.patch.object(REPAIR, "NO_REPEAT_FILES", ()):
                code, result = REPAIR.execute(
                    MODULE.DEFAULT_INPUT,
                    output,
                    REPAIR.DEFAULT_WHISPER_CACHE,
                    REPAIR.DEFAULT_PAID_LOCK,
                    model_loader=lambda _cache: object(),
                    decoder=decoder,
                )
        self.assertEqual(code, 0)
        self.assertEqual(result["go_no_go"], "GO_PRIVATE_LISTENING_QA_ONLY")
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], True)
        self.assertIs(result["next_stage_contract"]["full_title_generation_allowed"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)

    def test_missing_word_remains_fail_closed(self) -> None:
        _chapters, passages = PROFILE.controlled_source(REPO, PROFILE.SLUG)
        source = {item["passage_id"]: item["text"] for item in passages}

        def decoder(_model, _arm, sample):
            text = source[sample["passage_id"]]
            return text.replace("slower-witted", "slower")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "repair.json"
            with mock.patch.object(REPAIR, "NO_REPEAT_FILES", ()):
                code, result = REPAIR.execute(
                    MODULE.DEFAULT_INPUT,
                    output,
                    REPAIR.DEFAULT_WHISPER_CACHE,
                    REPAIR.DEFAULT_PAID_LOCK,
                    model_loader=lambda _cache: object(),
                    decoder=decoder,
                )
        self.assertEqual(code, 4)
        self.assertEqual(
            result["go_no_go"], "NO_GO_REPRESENTATIVE_ASR_REPAIR_FAILED"
        )
        self.assertIs(result["next_stage_contract"]["listening_qa_allowed"], False)

    def test_module_is_asr_only(self) -> None:
        source = inspect.getsource(MODULE)
        self.assertNotIn("def synthesize", source)
        self.assertNotIn("--upload", source)
        self.assertNotIn("--publish", source)
        self.assertNotIn("speechSynthesis", source)

    def test_cli_surface_is_repair_only(self) -> None:
        result = subprocess.run(
            [str(PINNED_PYTHON), str(SCRIPT), "--help"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--execute", result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertNotIn("--upload", result.stdout)
        self.assertNotIn("--publish", result.stdout)


if __name__ == "__main__":
    unittest.main()
