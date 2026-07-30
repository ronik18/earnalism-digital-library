#!/usr/bin/env python3
"""Tests for the generic Google English representative objective adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import sprint1_google_english_representative_objective_qa as adapter
import sprint1_google_english_listening_qa as listening_qa


class FakeWhisper:
    def __init__(self, transcripts: dict[str, str]) -> None:
        self.transcripts = transcripts
        self.calls: list[tuple[str, dict[str, object]]] = []

    def transcribe(self, audio_path: str, **settings: object) -> dict[str, object]:
        self.calls.append((audio_path, settings))
        text = self.transcripts[Path(audio_path).stem]
        words = [
            {
                "word": word,
                "start": index * 0.1,
                "end": index * 0.1 + 0.08,
                "probability": 0.99,
            }
            for index, word in enumerate(text.split())
        ]
        return {"text": text, "segments": [{"words": words}]}


class GoogleObjectiveAdapterTests(unittest.TestCase):
    SOURCE = (
        "Opening sentence is precise and twenty years old. "
        "Second opening sentence remains calm and clear. "
        "Third opening sentence describes a quiet London street. "
        "Fourth opening sentence closes the introductory scene. "
        "Fifth sentence carries the story forward. "
        "Sixth sentence introduces another careful observation. "
        "Seventh sentence preserves exact ordinary language. "
        "Eighth sentence marks a distinct narrative point. "
        "Ninth sentence sits near the centre of the text. "
        "Tenth sentence adds a measured middle detail. "
        "Eleventh sentence continues without ornament. "
        "Twelfth sentence ends the middle sequence. "
        "He asked, \"Will this difficult question be answered correctly?\" "
        "She replied, \"Yes; every exact word must remain in order!\" "
        "Fifteenth sentence begins the final movement. "
        "Sixteenth sentence keeps the ending restrained. "
        "Seventeenth sentence approaches the final boundary. "
        "The final sentence ends this exact sample."
    )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.private_root = Path(self.temporary.name).resolve()
        self.run_dir = self.private_root / "book" / "audition" / "fingerprint"
        self.run_dir.mkdir(parents=True)
        self.source_path = self.run_dir / "sanitized_source.txt"
        self.source_path.write_text(self.SOURCE, encoding="utf-8")
        source_sha = hashlib.sha256(self.SOURCE.encode()).hexdigest()
        self.input_manifest_path = self.run_dir / "input_manifest.json"
        input_manifest = {
            "schema_version": adapter.google_pipeline.INPUT_SCHEMA,
            "slug": "test-english-title",
            "title": "Test English Title",
            "author": "Test Author",
            "language": "en",
            "sanitized_source_sha256": source_sha,
            "sanitization_status": "PASS",
            "rights_status": "PASS",
            "commercial_use_allowed": True,
        }
        self.input_manifest_path.write_text(
            json.dumps(input_manifest, sort_keys=True), encoding="utf-8"
        )
        input_manifest_sha = hashlib.sha256(
            self.input_manifest_path.read_bytes()
        ).hexdigest()
        self.passages = adapter.google_pipeline.select_representative_passages(
            self.SOURCE
        )
        self.fingerprint = adapter.google_pipeline.attempt_fingerprint(
            mode="audition",
            source_sha256=source_sha,
            manifest_sha256=input_manifest_sha,
            voice="en-GB-Studio-C",
            language_code="en-GB",
            speaking_rate=0.94,
            pitch=0.0,
            units=self.passages,
        )
        self.transcripts = {
            passage["passage_id"]: passage["text"] for passage in self.passages
        }
        audio_dir = self.run_dir / "audio"
        audio_dir.mkdir()
        records = []
        evidence_samples = []
        for passage in self.passages:
            passage_id = passage["passage_id"]
            audio_path = audio_dir / f"{passage_id}.mp3"
            audio_path.write_bytes(b"ID3" + passage_id.encode())
            audio_sha = hashlib.sha256(audio_path.read_bytes()).hexdigest()
            records.append(
                {
                    "unit_id": passage_id,
                    "text_sha256": passage["text_sha256"],
                    "characters": passage["characters"],
                    "audio_path": str(audio_path),
                    "audio_sha256": audio_sha,
                    "audio_size_bytes": audio_path.stat().st_size,
                }
            )
            evidence_samples.append(
                {
                    "passage_id": passage_id,
                    "source_text_sha256": passage["text_sha256"],
                    "audio_path": str(audio_path),
                    "audio_sha256": audio_sha,
                    "overall_listening_score": None,
                    "confidence_score": None,
                    "scores": {},
                    "fatal_flags": [],
                    "judge_flags": {
                        flag: False
                        for flag in adapter.google_pipeline.FATAL_LISTENING_FLAGS
                    },
                    "review_notes": "",
                }
            )
        self.audition_manifest_path = self.run_dir / "audition_manifest.json"
        self.audition_manifest = {
            "schema_version": adapter.google_pipeline.PIPELINE_SCHEMA,
            "status": "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED",
            "mode": "audition",
            "slug": "test-english-title",
            "title": "Test English Title",
            "author": "Test Author",
            "provider": "google",
            "voice": "en-GB-Studio-C",
            "language_code": "en-GB",
            "speaking_rate": 0.94,
            "pitch": 0.0,
            "source_sha256": source_sha,
            "input_manifest_sha256": input_manifest_sha,
            "attempt_fingerprint": self.fingerprint,
            "unit_hashes": [item["text_sha256"] for item in self.passages],
            "representative_passages": [
                {key: value for key, value in item.items() if key != "text"}
                for item in self.passages
            ],
            "generated_audio": records,
            "sanitized_source_copy": str(self.source_path),
            "input_manifest_copy": str(self.input_manifest_path),
            "private_output_only": True,
            "provider_calls_ran": True,
            "synthesis_calls": 4,
            "paid_lock_restored_byte_for_byte": True,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
        }
        self._write_manifest()
        self.audition_evidence_path = self.run_dir / "audition_listening_evidence.json"
        evidence = {
            "schema_version": adapter.google_pipeline.LISTENING_SCHEMA,
            "status": "PENDING_LISTENING_REVIEW",
            "slug": "test-english-title",
            "title": "Test English Title",
            "provider": "google",
            "voice": "en-GB-Studio-C",
            "source_sha256": source_sha,
            "input_manifest_sha256": input_manifest_sha,
            "audition_fingerprint": self.fingerprint,
            "audition_manifest_path": str(self.audition_manifest_path),
            "audition_manifest_sha256": hashlib.sha256(
                self.audition_manifest_path.read_bytes()
            ).hexdigest(),
            "minimum_listening_score": 8.9,
            "minimum_listening_confidence": 0.9,
            "per_dimension_score_min": 8.9,
            "anti_robotic_texture_score_min": 8.9,
            "anti_choppy_join_score_min": 8.9,
            "required_passages": list(adapter.PASSAGE_IDS),
            "fatal_flags_required_false": list(
                adapter.google_pipeline.FATAL_LISTENING_FLAGS
            ),
            "private_output_only": True,
            "provider_calls_ran": True,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "samples": evidence_samples,
        }
        self.audition_evidence_path.write_text(
            json.dumps(evidence), encoding="utf-8"
        )
        self.whisper_cache = self.private_root / "whisper"
        self.whisper_cache.mkdir()
        self.whisper_path = self.whisper_cache / adapter.WHISPER_FILENAME
        self.whisper_path.write_bytes(b"pinned-test-whisper")
        self.whisper_sha = hashlib.sha256(self.whisper_path.read_bytes()).hexdigest()
        self.objective_path = self.run_dir / "objective_report.json"
        self.listening_path = self.run_dir / "objective_listening_input.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_manifest(self) -> None:
        self.audition_manifest_path.write_text(
            json.dumps(self.audition_manifest), encoding="utf-8"
        )

    def _run(self, transcripts: dict[str, str]) -> tuple[dict[str, object], FakeWhisper]:
        fake = FakeWhisper(transcripts)
        with mock.patch.object(adapter, "WHISPER_SHA256", self.whisper_sha):
            report = adapter.run_adapter(
                audition_manifest_path=self.audition_manifest_path,
                audition_evidence_path=self.audition_evidence_path,
                private_root=self.private_root,
                whisper_cache=self.whisper_cache,
                objective_report_path=self.objective_path,
                listening_input_path=self.listening_path,
                model_loader=lambda *_args, **_kwargs: fake,
                duration_getter=lambda _path: 1000.0,
            )
        return report, fake

    def test_all_four_pass_and_emit_directly_bindable_listening_input(self) -> None:
        transcripts = dict(self.transcripts)
        transcripts["opening"] = transcripts["opening"].replace("twenty", "20", 1)
        report, fake = self._run(transcripts)
        self.assertTrue(report["objective_pass"])
        self.assertEqual(len(fake.calls), 4)
        self.assertTrue(self.objective_path.is_file())
        self.assertTrue(self.listening_path.is_file())
        for _audio, settings in fake.calls:
            self.assertIsNone(settings["initial_prompt"])
            self.assertTrue(settings["word_timestamps"])
        opening = report["objective_asr"]["reports"][0]
        self.assertLess(opening["raw_metrics"]["coverage"], 1.0)
        self.assertEqual(opening["normalized_metrics"]["score"], 10.0)
        self.assertEqual(
            opening["spoken_number_equivalences_applied"][0]["canonical_token"],
            "num20",
        )
        self.assertNotEqual(
            opening["raw_source_sha256"], opening["normalized_source_sha256"]
        )
        listening = json.loads(self.listening_path.read_text())
        self.assertEqual(
            listening["schema_version"], adapter.google_pipeline.LISTENING_SCHEMA
        )
        self.assertEqual(listening["objective_gate_status"], "PASS")
        self.assertEqual(listening["language_code"], "en-GB")
        self.assertEqual(listening["speaking_rate"], 0.94)
        self.assertEqual(listening["pitch"], 0.0)
        self.assertEqual(len(listening["samples"]), 4)
        self.assertFalse(listening["provider_calls_made_by_adapter"])
        self.assertFalse(listening["listening_qa_called"])
        accepted, accepted_manifest = listening_qa.load_evidence(self.listening_path)
        self.assertEqual(accepted["objective_gate_status"], "PASS")
        self.assertEqual(accepted_manifest["attempt_fingerprint"], self.fingerprint)

    def test_content_word_substitution_fails_and_emits_no_listening_input(self) -> None:
        transcripts = dict(self.transcripts)
        transcripts["middle"] = transcripts["middle"].replace("sentence", "paragraph", 1)
        report, _fake = self._run(transcripts)
        self.assertFalse(report["objective_pass"])
        self.assertTrue(self.objective_path.is_file())
        self.assertFalse(self.listening_path.exists())
        middle = report["objective_asr"]["reports"][1]
        self.assertFalse(middle["ordered_content_integrity_pass"])
        self.assertEqual(middle["spoken_number_equivalences_applied"], [])

    def test_reordered_or_missing_content_fails(self) -> None:
        transcripts = dict(self.transcripts)
        words = transcripts["dialogue_or_risk"].split()
        words[2:7] = reversed(words[2:7])
        transcripts["dialogue_or_risk"] = " ".join(words)
        transcripts["ending"] = " ".join(transcripts["ending"].split()[:-2])
        report, _fake = self._run(transcripts)
        self.assertFalse(report["objective_pass"])
        risk = report["objective_asr"]["reports"][2]
        ending = report["objective_asr"]["reports"][3]
        self.assertFalse(risk["ordered_content_integrity_pass"])
        self.assertFalse(ending["no_missing_content"])
        self.assertFalse(self.listening_path.exists())

    def test_stale_audio_hash_fails_before_asr(self) -> None:
        audio = self.run_dir / "audio" / "opening.mp3"
        audio.write_bytes(audio.read_bytes() + b"changed")
        with self.assertRaisesRegex(adapter.GoogleObjectiveQAError, "audio hash is stale"):
            adapter.validate_input_contract(
                audition_manifest_path=self.audition_manifest_path,
                audition_evidence_path=self.audition_evidence_path,
                private_root=self.private_root,
            )

    def test_private_path_enforcement_blocks_external_audio_and_public_output(self) -> None:
        external = self.private_root.parent / "outside-audio.mp3"
        external.write_bytes(b"ID3outside")
        try:
            self.audition_manifest["generated_audio"][0]["audio_path"] = str(external)
            self._write_manifest()
            evidence = json.loads(self.audition_evidence_path.read_text())
            evidence["audition_manifest_sha256"] = hashlib.sha256(
                self.audition_manifest_path.read_bytes()
            ).hexdigest()
            evidence["samples"][0]["audio_path"] = str(external)
            evidence["samples"][0]["audio_sha256"] = hashlib.sha256(
                external.read_bytes()
            ).hexdigest()
            self.audition_evidence_path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(adapter.GoogleObjectiveQAError, "outside the private root"):
                adapter.validate_input_contract(
                    audition_manifest_path=self.audition_manifest_path,
                    audition_evidence_path=self.audition_evidence_path,
                    private_root=self.private_root,
                )
        finally:
            external.unlink(missing_ok=True)
        with self.assertRaises(adapter.GoogleObjectiveQAError):
            adapter.validate_private_root(adapter.ROOT / "frontend/public/qa")

    def test_number_equivalence_does_not_normalize_names_or_content_words(self) -> None:
        source, transcript, applied = adapter.apply_spoken_number_equivalences(
            "Mrs. Long waited twenty-one minutes.",
            "Mrs. Wong waited 21 minutes.",
        )
        self.assertEqual(len(applied), 1)
        self.assertIn("long", source)
        self.assertIn("wong", transcript)
        metrics = adapter.whisper_common.ordered_token_integrity(source, transcript)
        self.assertFalse(metrics["ordered_content_integrity_pass"])

    def test_explicit_neighbouring_orthography_equivalence_is_auditable(self) -> None:
        source, transcript, applied = adapter.apply_spoken_number_equivalences(
            "They entered a neighbouring thoroughfare.",
            "They entered a neighboring thoroughfare.",
        )
        self.assertEqual(source, transcript)
        self.assertEqual(len(applied), 1)
        self.assertEqual(
            applied[0]["reason"],
            (
                "EXPLICIT_STANDALONE_BRITISH_AMERICAN_ORTHOGRAPHY_"
                "NEIGHBOURING_NEIGHBORING"
            ),
        )
        metrics = adapter.whisper_common.ordered_token_integrity(source, transcript)
        self.assertTrue(metrics["ordered_content_integrity_pass"])

    def test_orthography_equivalence_is_not_a_broad_spelling_rule(self) -> None:
        source, transcript, applied = adapter.apply_spoken_number_equivalences(
            "The neighbour noticed the colour.",
            "The neighbor noticed the color.",
        )
        self.assertEqual(applied, [])
        metrics = adapter.whisper_common.ordered_token_integrity(source, transcript)
        self.assertFalse(metrics["ordered_content_integrity_pass"])

    def test_exact_jekyll_hydes_hides_phonetic_equivalence_is_auditable(self) -> None:
        source, transcript, applied = adapter.apply_spoken_number_equivalences(
            "Ah, that's not Jekyll's voice. It's Hyde's! cried Utterson.",
            "Ah, that's not Jekyll's voice. It's hides! cried Utterson.",
            slug="jekyll-and-hyde",
        )
        self.assertEqual(source, transcript)
        self.assertEqual(len(applied), 1)
        self.assertEqual(
            applied[0]["reason"],
            "EXPLICIT_JEKYLL_CONTEXTUAL_PHONETIC_EQUIVALENCE_HYDES_HIDES",
        )
        self.assertEqual(applied[0]["scope_slug"], "jekyll-and-hyde")
        self.assertEqual(
            applied[0]["source_text_sha256"],
            adapter.google_pipeline.sha256_text(
                "Ah, that's not Jekyll's voice. It's Hyde's! cried Utterson."
            ),
        )
        metrics = adapter.whisper_common.ordered_token_integrity(source, transcript)
        self.assertTrue(metrics["ordered_content_integrity_pass"])

    def test_hydes_hides_is_not_a_generic_phonetic_equivalence(self) -> None:
        for source_text, transcript_text in (
            ("Hyde's house was empty.", "Hides house was empty."),
            ("It's Hyde's decision.", "It's hides decision."),
            ("It's hyde's, cried Utterson.", "It's hides, cried Utterson."),
            ("That is Hyde's, cried Utterson.", "That is hides, cried Utterson."),
            ("It's Hyde's, cried Poole.", "It's hides, cried Poole."),
            ("It's Hyde's, cried Utterson.", "It's Hides, cried Utterson."),
        ):
            with self.subTest(source=source_text):
                source, transcript, applied = adapter.apply_spoken_number_equivalences(
                    source_text,
                    transcript_text,
                    slug="jekyll-and-hyde",
                )
                self.assertEqual(applied, [])
                metrics = adapter.whisper_common.ordered_token_integrity(
                    source,
                    transcript,
                )
                self.assertFalse(metrics["ordered_content_integrity_pass"])

    def test_hydes_hides_context_is_rejected_outside_jekyll_slug(self) -> None:
        source, transcript, applied = adapter.apply_spoken_number_equivalences(
            "Ah, that's not Jekyll's voice. It's Hyde's! cried Utterson.",
            "Ah, that's not Jekyll's voice. It's hides! cried Utterson.",
            slug="another-title",
        )
        self.assertEqual(applied, [])
        metrics = adapter.whisper_common.ordered_token_integrity(source, transcript)
        self.assertFalse(metrics["ordered_content_integrity_pass"])


if __name__ == "__main__":
    unittest.main()
