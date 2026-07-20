from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))

import sprint1_gift_kokoro_full_title_private_qa as full


ARTIFACT_DIR = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/artifacts"
)
WHISPER_CACHE = Path(
    "/Users/ronikbasak/Documents/GitHub/earnalism-digital-library-audio-v2/"
    ".venv-audio/whisper-cache"
)


def pinned_runtime_available() -> bool:
    if importlib.util.find_spec("misaki") is None:
        return False
    try:
        full.representative.runtime_evidence()
    except Exception:
        return False
    return True


PINNED_RUNTIME_AVAILABLE = pinned_runtime_available()


class GiftFullTitlePrivateQATest(unittest.TestCase):
    def test_controlled_source_is_exact_and_lossless(self) -> None:
        chapter, manuscript, sections = full.controlled_source(full.ROOT)
        self.assertEqual(chapter.name, "chapter-001.json")
        self.assertEqual(full.sha256_text(manuscript), full.NORMALIZED_SOURCE_SHA256)
        self.assertEqual(len(manuscript), full.NORMALIZED_SOURCE_CHARACTERS)
        self.assertEqual(len(sections), 19)
        self.assertEqual(
            [item["word_count"] for item in sections], list(full.SECTION_WORD_COUNTS)
        )
        self.assertEqual(
            [item["text_sha256"] for item in sections], list(full.SECTION_HASHES)
        )
        self.assertEqual(" ".join(item["text"] for item in sections), manuscript)
        self.assertTrue(all(item["text"][-1] in '.!?\"”’' for item in sections))

    def test_predecessor_evidence_is_hash_bound_and_platform_passed(self) -> None:
        binding = full.validate_predecessor_evidence(
            full.DEFAULT_REPRESENTATIVE_EVIDENCE,
            full.DEFAULT_LISTENING_EVIDENCE,
        )
        self.assertTrue(binding["platform_screen_pass"])
        self.assertGreaterEqual(binding["minimum_overall_listening_score"], 9.2)
        self.assertGreaterEqual(binding["minimum_confidence_score"], 0.90)
        self.assertEqual(binding["fatal_flags"], [])
        self.assertFalse(binding["exact_10_is_private_full_title_gate"])

    @unittest.skipUnless(PINNED_RUNTIME_AVAILABLE, "requires checksum-pinned audio runtime")
    def test_full_title_g2p_has_no_fallback_or_unresolved_tokens(self) -> None:
        _chapter, _manuscript, sections = full.controlled_source(full.ROOT)
        result = full.full_title_g2p_preflight(sections)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["fallback_enabled"])
        self.assertIsNone(result["settings"]["fallback"])
        self.assertEqual(result["unresolved_token_count"], 0)
        self.assertEqual(
            result["canonical_proper_names_encountered"],
            sorted(full.CANONICAL_PROPER_NAMES),
        )
        self.assertEqual(len(result["sections"]), 19)
        self.assertTrue(all(item["pass"] for item in result["sections"]))

    def test_full_fingerprint_is_new_and_binds_material_inputs(self) -> None:
        _chapter, _manuscript, sections = full.controlled_source(full.ROOT)
        baseline = full.full_title_fingerprint(sections)
        self.assertEqual(len(baseline), 64)
        self.assertNotIn(
            baseline,
            {
                full.REPRESENTATIVE_ATTEMPT_FINGERPRINT,
                full.REPRESENTATIVE_LISTENING_FINGERPRINT,
                full.REPRESENTATIVE_ASR_FINGERPRINT,
            },
        )
        with mock.patch.object(full, "VOICE_SHA256", "0" * 64):
            self.assertNotEqual(baseline, full.full_title_fingerprint(sections))
        with mock.patch.object(full, "ASR_SETTINGS", {**full.ASR_SETTINGS, "temperature": 0.1}):
            self.assertNotEqual(baseline, full.full_title_fingerprint(sections))
        changed = dict(full.PRONUNCIATION_OVERRIDES)
        changed["Sofronie"] += "changed"
        with mock.patch.object(full, "PRONUNCIATION_OVERRIDES", changed):
            self.assertNotEqual(baseline, full.full_title_fingerprint(sections))

    def test_non_repeat_allows_dry_run_but_blocks_generated_attempt(self) -> None:
        _chapter, _manuscript, sections = full.controlled_source(full.ROOT)
        fingerprint = full.full_title_fingerprint(sections)
        with tempfile.TemporaryDirectory(prefix="gift-full-repeat-") as temporary:
            output = Path(temporary) / "evidence.json"
            with mock.patch.object(full, "NO_REPEAT_FILES", ()):
                output.write_text(
                    json.dumps(
                        {
                            "engine": {"attempt_fingerprint": fingerprint},
                            "safety": {"full_title_generated": False},
                        }
                    ),
                    encoding="utf-8",
                )
                full.ensure_not_repeated(fingerprint, output)
                output.write_text(
                    json.dumps(
                        {
                            "engine": {"attempt_fingerprint": fingerprint},
                            "safety": {"full_title_generated": True},
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(full.GiftFullTitleError, "already generated"):
                    full.ensure_not_repeated(fingerprint, output)

    def test_ordered_metrics_fail_missing_duplicate_reordered_and_unexpected(self) -> None:
        exact = full.ordered_metrics("one two three four five six", "one two three four five six")
        self.assertTrue(exact["pass"])
        self.assertTrue(exact["no_missing_content"])
        self.assertTrue(exact["no_duplicate_content"])
        self.assertTrue(exact["no_reordered_content"])
        self.assertTrue(exact["no_unexpected_content"])
        failures = (
            full.ordered_metrics("one two three four five six", "one two four five six"),
            full.ordered_metrics("one two three four five six", "one two three three four five six"),
            full.ordered_metrics("one two three four five six", "one three two four five six"),
            full.ordered_metrics("one two three four five six", "one two three four five six seven"),
        )
        self.assertTrue(all(not item["pass"] for item in failures))

    def test_exact_semantic_equivalences_do_not_weaken_integrity(self) -> None:
        source = "Mr. Young paid $8 and said yer gift was wise."
        transcript = "Mister Young paid eight dollars and said your gift was wise."
        result = full.ordered_metrics(source, transcript)
        self.assertTrue(result["pass"])
        self.assertEqual(result["score"], 10.0)
        bad = full.ordered_metrics(source, transcript + " tomorrow")
        self.assertFalse(bad["pass"])
        self.assertFalse(bad["no_unexpected_content"])

    def test_measured_section_sync_is_frame_and_audio_derived(self) -> None:
        sections = [
            {
                "passage_id": "section-001",
                "text_sha256": hashlib.sha256(b"one two three").hexdigest(),
            }
        ]
        samples = [
            {
                "passage_id": "section-001",
                "source_text_sha256": sections[0]["text_sha256"],
                "audio_sha256": "a" * 64,
                "duration_seconds": 1.0,
            }
        ]
        boundaries = [
            {
                "section_id": "section-001",
                "start_frame": 0,
                "end_frame": full.SAMPLE_RATE,
                "audio_sha256": "a" * 64,
            }
        ]
        report = {
            "section_id": "section-001",
            "source_text_sha256": sections[0]["text_sha256"],
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
            "full_audio_frame_count": full.SAMPLE_RATE,
            "objective_format_pass": True,
            "audio_sha256": "b" * 64,
        }
        result = full.measured_section_sync(
            sections, samples, boundaries, asr, recomposition
        )
        self.assertTrue(result["sync_pass"])
        self.assertEqual(result["sync_score"], 10.0)
        self.assertTrue(result["audio_derived_or_measured"])
        self.assertFalse(result["auto_estimated_sync"])
        self.assertFalse(result["public_word_level_sync_claim_allowed"])
        bad_boundaries = [{**boundaries[0], "start_frame": 1}]
        self.assertFalse(
            full.measured_section_sync(
                sections, samples, bad_boundaries, asr, recomposition
            )["sync_pass"]
        )

    @unittest.skipUnless(PINNED_RUNTIME_AVAILABLE, "requires checksum-pinned audio runtime")
    def test_preflight_is_private_zero_paid_and_release_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gift-full-preflight-") as temporary:
            output = Path(temporary) / "dry-run.json"
            private = Path(temporary) / "private"
            # The production ledger correctly closes this completed
            # fingerprint. Isolate preflight construction here; the explicit
            # no-repeat test above retains coverage of the production guard.
            with mock.patch.object(full, "NO_REPEAT_FILES", ()):
                payload, sections, _artifacts = full.preflight(
                    asset_root=full.ROOT,
                    artifact_dir=ARTIFACT_DIR,
                    whisper_cache_dir=WHISPER_CACHE,
                    private_dir=private,
                    output=output,
                    paid_lock=full.DEFAULT_PAID_LOCK,
                    representative_evidence=full.DEFAULT_REPRESENTATIVE_EVIDENCE,
                    listening_evidence=full.DEFAULT_LISTENING_EVIDENCE,
                )
            full.write_json(output, payload)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "READY_FOR_PRIVATE_FULL_TITLE_EXECUTION")
        self.assertEqual(payload["status"], "READY_FOR_PRIVATE_FULL_TITLE_EXECUTION")
        self.assertEqual(len(sections), 19)
        self.assertEqual(payload["safety"]["provider_calls"], 0)
        self.assertEqual(payload["safety"]["listening_provider_calls"], 0)
        self.assertFalse(payload["safety"]["paid_tts_lock_touched"])
        self.assertFalse(payload["safety"]["audio_generated"])
        self.assertFalse(payload["safety"]["upload_performed"])
        self.assertFalse(payload["safety"]["publication_performed"])
        self.assertFalse(payload["safety"]["release_gate_mutated"])
        self.assertTrue(payload["source"]["lossless_section_reconstruction"])
        self.assertFalse(payload["engine"]["g2p_fallback_enabled"])
        self.assertNotIn("OWNER_10_TARGET_NOT_VERIFIED", payload["blockers_to_release"])
        self.assertIn("PRIVATE_FULL_TITLE_NOT_GENERATED", payload["blockers_to_release"])

    def test_public_audio_path_is_rejected(self) -> None:
        with self.assertRaises(full.GiftFullTitleError):
            full.assert_private_path(full.ROOT / "frontend/public/forbidden.wav")


if __name__ == "__main__":
    unittest.main()
