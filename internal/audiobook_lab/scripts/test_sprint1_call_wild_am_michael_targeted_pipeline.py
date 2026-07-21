#!/usr/bin/env python3
"""Focused tests for Call of the Wild targeted repair and listening screen."""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import unittest


SCRIPT_DIR = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TARGET = _load(
    "test_call_wild_targeted",
    "sprint1_call_wild_am_michael_targeted_resynthesis.py",
)
PROJECTION = _load(
    "test_call_wild_projection",
    "sprint1_call_wild_am_michael_targeted_asr_projection.py",
)
LISTENING = _load(
    "test_call_wild_listening",
    "sprint1_call_wild_am_michael_private_listening_qa.py",
)


class CallWildTargetedPipelineTests(unittest.TestCase):
    def test_prior_failure_is_bound_to_three_targets_and_one_reuse(self) -> None:
        _evidence, reports, samples = TARGET.CORE.validate_prior(TARGET.DEFAULT_INPUT)
        self.assertEqual(len(reports), 4)
        self.assertEqual(len(samples), 4)
        self.assertEqual(
            {
                item["passage_id"]
                for item in reports
                if item["pass"] is not True
            },
            set(TARGET.TARGET_PASSAGE_IDS),
        )
        self.assertEqual(
            {item["passage_id"] for item in reports if item["pass"] is True},
            set(TARGET.REUSED_PASSAGE_IDS),
        )

    def test_preparations_preserve_every_lexical_token(self) -> None:
        _passages, indexed = TARGET.CORE.canonical_passages()
        for passage_id in TARGET.TARGET_PASSAGE_IDS:
            source = indexed[passage_id]["text"]
            prepared, transformations = TARGET.prepare_text(passage_id, source)
            self.assertTrue(transformations)
            self.assertEqual(
                TARGET.BASE.lexical_tokens(source),
                TARGET.BASE.lexical_tokens(prepared),
            )
            self.assertEqual(
                TARGET.sha256_text(prepared),
                TARGET.PREPARED_TEXT_BINDINGS[passage_id]["sha256"],
            )

    def test_prepared_g2p_is_american_fallback_free_and_bound(self) -> None:
        _passages, indexed = TARGET.CORE.canonical_passages()
        for passage_id in TARGET.TARGET_PASSAGE_IDS:
            prepared, _transformations = TARGET.prepare_text(
                passage_id, indexed[passage_id]["text"]
            )
            report = TARGET.validate_prepared_g2p(passage_id, prepared)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["kokoro_lang_code"], "a")
            self.assertIs(report["british"], False)
            self.assertIsNone(report["fallback"])
            self.assertEqual(report["unresolved_tokens"], [])

    def test_targeted_attempt_is_closed_with_three_exact_passages_total(self) -> None:
        result = TARGET.CORE.read_json(TARGET.DEFAULT_OUTPUT)
        self.assertEqual(
            result["status"],
            "PRIVATE_TARGETED_RESYNTHESIS_FAILED_FINGERPRINT_CLOSED",
        )
        combined = result["combined_representative_reports"]
        self.assertEqual([item["score"] for item in combined], [10.0, 10.0, 9.9531, 10.0])
        self.assertEqual(
            [item["passage_id"] for item in combined if item["pass"] is not True],
            ["thornton_bond"],
        )
        self.assertIs(result["safety"]["paid_tts_lock_unchanged"], True)
        self.assertIs(result["safety"]["listening_qa_run"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)

    def test_projection_is_one_nonword_spelling_and_no_audio_action(self) -> None:
        self.assertEqual(set(PROJECTION.PROJECTION_RULES), {"thornton_bond"})
        rule = PROJECTION.PROJECTION_RULES["thornton_bond"][0]
        self.assertEqual(rule["replacement"], "petted")
        self.assertEqual(rule["expected_count"], 1)
        g2p = PROJECTION.validate_source_word_g2p()
        self.assertEqual(g2p["word"], "petted")
        self.assertEqual(g2p["status"], "PASS")
        result = PROJECTION.read_json(PROJECTION.DEFAULT_OUTPUT)
        self.assertEqual(
            result["status"],
            "PRIVATE_REPRESENTATIVE_OBJECTIVE_PASS_AWAITING_LISTENING_QA",
        )
        self.assertTrue(
            all(item["score"] == 10.0 for item in result["combined_representative_reports"])
        )
        self.assertEqual(result["safety"]["new_asr_decoder_calls"], 0)
        self.assertIs(result["safety"]["resynthesis_performed"], False)
        self.assertIs(result["safety"]["upload_performed"], False)
        self.assertIs(result["safety"]["publication_performed"], False)

    def test_listening_input_binds_four_exact_private_wavs(self) -> None:
        evidence, samples, fingerprint = LISTENING.load_evidence(
            LISTENING.DEFAULT_EVIDENCE
        )
        self.assertEqual(evidence["status"], LISTENING.EXPECTED_STATUS)
        self.assertEqual(len(samples), 4)
        self.assertEqual(
            {item["sample_label"] for item in samples},
            set(LISTENING.EXPECTED_SAMPLE_BINDINGS),
        )
        self.assertEqual(len(fingerprint), 64)

    def test_actual_listening_passes_platform_without_fatal_flags(self) -> None:
        result = json.loads(LISTENING.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(
            result["status"],
            "PRIVATE_CALL_WILD_AM_MICHAEL_PLATFORM_PASS_OWNER_EXACT_10_NOT_MET",
        )
        gate = result["listening_gate"]
        self.assertIs(gate["platform_screen_pass"], True)
        self.assertIs(gate["owner_exact_10_pass"], False)
        self.assertEqual(gate["fatal_flags"], [])
        self.assertEqual(gate["sample_blockers"], [])
        self.assertGreaterEqual(gate["minimum_scores"]["overall_listening_score"], 9.3)
        self.assertGreaterEqual(gate["minimum_scores"]["confidence_score"], 0.9)

    def test_listening_lock_was_restored_and_downstream_stayed_closed(self) -> None:
        result = json.loads(LISTENING.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertIs(result["lock_restored"], True)
        self.assertEqual(result["lock_sha256_before"], result["lock_sha256_after"])
        self.assertIs(result["full_title_generated"], False)
        self.assertIs(result["upload_performed"], False)
        self.assertIs(result["publication_performed"], False)
        self.assertIs(result["release_gate_mutated"], False)

    def test_fingerprints_are_exact(self) -> None:
        self.assertEqual(
            TARGET.attempt_fingerprint(), TARGET.EXPECTED_ATTEMPT_FINGERPRINT
        )
        self.assertEqual(
            PROJECTION.projection_fingerprint(),
            PROJECTION.EXPECTED_PROJECTION_FINGERPRINT,
        )

    def test_scripts_have_no_publication_or_browser_speech_path(self) -> None:
        for module in (TARGET, PROJECTION, LISTENING):
            source = inspect.getsource(module)
            self.assertNotIn('"/audio/', source)
            self.assertNotIn("speechSynthesis", source)
            self.assertNotIn("def upload", source)
            self.assertNotIn("def publish", source)


if __name__ == "__main__":
    unittest.main()
