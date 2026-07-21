#!/usr/bin/env python3
"""Focused contract tests for the private Call of the Wild full-title pilot."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent


def _load():
    path = SCRIPT_DIR / "sprint1_call_wild_am_michael_full_title_private_qa.py"
    spec = importlib.util.spec_from_file_location("test_call_wild_full_title", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FULL = _load()


def pinned_runtime_available() -> bool:
    if importlib.util.find_spec("misaki") is None:
        return False
    try:
        FULL.PROFILE.BASE.runtime_evidence()
    except Exception:
        return False
    return True


PINNED_RUNTIME_AVAILABLE = pinned_runtime_available()


class CallWildFullTitlePrivateQATests(unittest.TestCase):
    def test_controlled_source_is_exact_lossless_and_sentence_bound(self) -> None:
        chapter_dir, prepared, sections = FULL.controlled_source(FULL.ROOT)
        self.assertEqual(chapter_dir.name, "chapters")
        self.assertEqual(FULL.BASE.sha256_text(prepared), FULL.PREPARED_NORMALIZED_SOURCE_SHA256)
        self.assertEqual(len(prepared), FULL.PREPARED_NORMALIZED_SOURCE_CHARACTERS)
        self.assertEqual(len(prepared.split(" ")), FULL.PREPARED_NORMALIZED_SOURCE_WORDS)
        self.assertEqual(len(sections), FULL.EXPECTED_SECTION_COUNT)
        self.assertEqual(" ".join(item["text"] for item in sections), prepared)
        self.assertTrue(
            all(re.search(r"[.!?][\"”’']*$", item["text"]) for item in sections)
        )

    def test_preparation_changes_punctuation_not_lexical_content(self) -> None:
        publication = FULL.ROOT / "data/controlled_publications" / FULL.SLUG
        chapters = sorted((publication / "chapters").glob("chapter-*.json"))
        manuscript = "\n\n".join(
            str(FULL.BASE.read_json(path).get("content") or "") for path in chapters
        ) + "\n"
        canonical = re.sub(r"\s+", " ", manuscript).strip()
        prepared, transformations = FULL.prepare_manuscript(canonical)
        self.assertEqual(
            FULL.PROFILE.BASE.lexical_tokens(canonical),
            FULL.PROFILE.BASE.lexical_tokens(prepared),
        )
        self.assertEqual(len(transformations), len(FULL.SOURCE_PREPARATIONS) + 1)
        self.assertEqual(transformations[-1]["occurrences"], "272")

    def test_predecessor_and_active_policy_are_hash_bound(self) -> None:
        gate = FULL.validate_predecessor_evidence(
            FULL.DEFAULT_REPRESENTATIVE_EVIDENCE,
            FULL.DEFAULT_LISTENING_EVIDENCE,
        )
        self.assertTrue(gate["platform_screen_pass"])
        self.assertEqual(gate["acceptance_tier"], "PREMIUM_AUDIO_APPROVED")
        self.assertGreaterEqual(gate["minimum_overall_listening_score"], 9.3)
        self.assertGreaterEqual(gate["minimum_confidence_score"], 0.90)
        self.assertEqual(gate["fatal_flags"], [])
        self.assertFalse(gate["exact_10_is_private_full_title_gate"])

    @unittest.skipUnless(PINNED_RUNTIME_AVAILABLE, "requires checksum-pinned audio runtime")
    def test_all_280_sections_are_fallback_free_and_pronunciation_bound(self) -> None:
        _chapter_dir, _prepared, sections = FULL.controlled_source(FULL.ROOT)
        result = FULL.BASE.full_title_g2p_preflight(sections)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["fallback_enabled"])
        self.assertIsNone(result["settings"]["fallback"])
        self.assertEqual(result["unresolved_token_count"], 0)
        self.assertEqual(len(result["sections"]), FULL.EXPECTED_SECTION_COUNT)
        self.assertTrue(all(item["pass"] for item in result["sections"]))

    def test_full_title_fingerprint_is_exact_and_binds_material_inputs(self) -> None:
        _chapter_dir, _prepared, sections = FULL.controlled_source(FULL.ROOT)
        baseline = FULL.BASE.full_title_fingerprint(sections)
        self.assertEqual(baseline, FULL.EXPECTED_FULL_TITLE_FINGERPRINT)
        self.assertNotIn(
            baseline,
            {
                FULL.REPRESENTATIVE_ATTEMPT_FINGERPRINT,
                FULL.REPRESENTATIVE_LISTENING_FINGERPRINT,
                FULL.REPRESENTATIVE_ASR_FINGERPRINT,
            },
        )
        changed = dict(FULL.PRONUNCIATION_OVERRIDES)
        changed["Yeehats"] += "changed"
        with mock.patch.object(FULL.BASE, "PRONUNCIATION_OVERRIDES", changed):
            self.assertNotEqual(baseline, FULL.BASE.full_title_fingerprint(sections))

    def test_non_repeat_allows_preflight_but_blocks_generated_attempt(self) -> None:
        _chapter_dir, _prepared, sections = FULL.controlled_source(FULL.ROOT)
        fingerprint = FULL.BASE.full_title_fingerprint(sections)
        with tempfile.TemporaryDirectory(prefix="call-wild-full-repeat-") as temporary:
            output = Path(temporary) / "evidence.json"
            with mock.patch.object(FULL.BASE, "NO_REPEAT_FILES", ()):
                output.write_text(
                    json.dumps(
                        {
                            "engine": {"attempt_fingerprint": fingerprint},
                            "safety": {"full_title_generated": False},
                        }
                    ),
                    encoding="utf-8",
                )
                FULL.BASE.ensure_not_repeated(fingerprint, output)
                output.write_text(
                    json.dumps(
                        {
                            "engine": {"attempt_fingerprint": fingerprint},
                            "safety": {"full_title_generated": True},
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(FULL.CallWildFullTitleError, "already generated"):
                    FULL.BASE.ensure_not_repeated(fingerprint, output)

    def test_equivalence_policy_does_not_hide_substantive_changes(self) -> None:
        exact = FULL.BASE.ordered_metrics(
            "The St. Bernard manœuvred over tide-water.",
            "The Saint Bernard maneuvered over tidewater.",
        )
        self.assertTrue(exact["pass"])
        changed = FULL.BASE.ordered_metrics(
            "The St. Bernard manœuvred over tide-water.",
            "The Saint Bernard maneuvered over tidewater tomorrow.",
        )
        self.assertFalse(changed["pass"])
        self.assertFalse(changed["no_unexpected_content"])

    def test_measured_sync_requires_exact_audio_and_timestamp_bindings(self) -> None:
        source_hash = hashlib.sha256(b"one two three").hexdigest()
        sections = [{"passage_id": "section-001", "text_sha256": source_hash}]
        samples = [{
            "passage_id": "section-001",
            "source_text_sha256": source_hash,
            "audio_sha256": "a" * 64,
            "duration_seconds": 1.0,
        }]
        boundaries = [{
            "section_id": "section-001",
            "start_frame": 0,
            "end_frame": FULL.SAMPLE_RATE,
            "audio_sha256": "a" * 64,
        }]
        report = {
            "section_id": "section-001",
            "source_text_sha256": source_hash,
            "audio_sha256": "a" * 64,
            "audio_derived_word_timestamps": [
                {"word": "one", "start_seconds": 0.0, "end_seconds": 0.3}
            ],
            "word_timestamp_evidence_valid": True,
            "score": 10.0,
            "coverage": 1.0,
            "pass": True,
        }
        asr = {
            "reports": [report],
            "full_title_aggregate": {"score": 10.0, "coverage": 1.0, "pass": True},
        }
        recomposition = {
            "full_audio_frame_count": FULL.SAMPLE_RATE,
            "objective_format_pass": True,
            "audio_sha256": "b" * 64,
        }
        result = FULL.BASE.measured_section_sync(
            sections, samples, boundaries, asr, recomposition
        )
        self.assertTrue(result["sync_pass"])
        self.assertTrue(result["audio_derived_or_measured"])
        self.assertFalse(result["auto_estimated_sync"])
        self.assertFalse(result["public_word_level_sync_claim_allowed"])
        self.assertFalse(
            FULL.BASE.measured_section_sync(
                sections,
                samples,
                [{**boundaries[0], "start_frame": 1}],
                asr,
                recomposition,
            )["sync_pass"]
        )

    @unittest.skipUnless(PINNED_RUNTIME_AVAILABLE, "requires checksum-pinned audio runtime")
    def test_preflight_binds_catalog_covers_rights_and_stays_private(self) -> None:
        with tempfile.TemporaryDirectory(prefix="call-wild-full-preflight-") as temporary:
            output = Path(temporary) / "preflight.json"
            with mock.patch.object(FULL.BASE, "NO_REPEAT_FILES", ()):
                payload, sections, _artifacts = FULL.preflight(
                    asset_root=FULL.ROOT,
                    artifact_dir=FULL.DEFAULT_ARTIFACT_DIR,
                    whisper_cache_dir=FULL.DEFAULT_WHISPER_CACHE,
                    private_dir=Path(temporary) / "private",
                    output=output,
                    paid_lock=FULL.DEFAULT_PAID_LOCK,
                    representative_evidence=FULL.DEFAULT_REPRESENTATIVE_EVIDENCE,
                    listening_evidence=FULL.DEFAULT_LISTENING_EVIDENCE,
                )
        self.assertEqual(payload["status"], "READY_FOR_PRIVATE_FULL_TITLE_EXECUTION")
        self.assertEqual(len(sections), FULL.EXPECTED_SECTION_COUNT)
        self.assertEqual(payload["catalog_gate"]["status"], "PASS_READER_LIVE_AUDIO_HIDDEN")
        self.assertEqual(payload["cover_gate"]["status"], "PASS_DIRECT_FRONT_BACK")
        self.assertEqual(payload["rights"]["text_rights_status"], "PASS_PUBLIC_DOMAIN_TIER_A")
        self.assertEqual(payload["rights"]["model_and_voicepack_license"], "Apache-2.0")
        self.assertEqual(payload["safety"]["provider_calls"], 0)
        self.assertFalse(payload["safety"]["audio_generated"])
        self.assertFalse(payload["safety"]["upload_performed"])
        self.assertFalse(payload["safety"]["publication_performed"])
        self.assertFalse(payload["safety"]["release_gate_mutated"])

    def test_public_path_and_publication_implementation_are_absent(self) -> None:
        with self.assertRaises(FULL.CallWildFullTitleError):
            FULL.BASE.assert_private_path(FULL.ROOT / "frontend/public/forbidden.wav")
        source = inspect.getsource(FULL)
        self.assertNotIn('"/audio/', source)
        self.assertNotIn("speechSynthesis", source)
        self.assertNotIn("def upload", source)
        self.assertNotIn("def publish", source)

    def test_completed_objective_closeout_is_hash_bound_and_fail_closed(self) -> None:
        evidence_path = FULL.ROOT / (
            "internal/audiobook_lab/sprint1_publication/title_runs/"
            "the-call-of-the-wild_kokoro_am_michael_full_title_private_preflight_v1.json"
        )
        closeout_path = FULL.ROOT / (
            "internal/audiobook_lab/sprint1_publication/title_runs/"
            "the-call-of-the-wild_kokoro_am_michael_full_title_objective_closeout_v1.json"
        )
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        closeout = json.loads(closeout_path.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            closeout["input_evidence"]["sha256"],
        )
        self.assertEqual(evidence["status"], "PRIVATE_FULL_TITLE_REJECTED_OBJECTIVE_QA")
        self.assertEqual(len(evidence["asr"]["reports"]), 280)
        self.assertEqual(sum(bool(item["pass"]) for item in evidence["asr"]["reports"]), 64)
        self.assertEqual(closeout["objective_result"]["section_fail_count"], 216)
        self.assertFalse(closeout["repair_decision"]["source_bound_offline_projection_allowed"])
        self.assertFalse(closeout["repair_decision"]["listening_qa_allowed"])
        self.assertFalse(closeout["repair_decision"]["delivery_allowed"])
        self.assertFalse(closeout["repair_decision"]["publication_allowed"])
        self.assertEqual(
            closeout["safety"]["public_audio_status"], "AUDIO_HIDDEN_NOT_APPROVED"
        )


if __name__ == "__main__":
    unittest.main()
