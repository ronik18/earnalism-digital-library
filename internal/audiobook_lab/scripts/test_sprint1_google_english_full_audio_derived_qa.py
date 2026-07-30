#!/usr/bin/env python3
"""Provider-free tests for Google English full-title audio-derived QA."""

from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import sprint1_google_english_full_audio_derived_qa as qa


class MockWhisperModel:
    def __init__(
        self,
        source_by_stem: dict[str, str],
        *,
        transform=None,
        include_words: bool = True,
    ) -> None:
        self.source_by_stem = source_by_stem
        self.transform = transform or (lambda _stem, text: text)
        self.include_words = include_words
        self.calls: list[tuple[str, dict]] = []

    def transcribe(self, audio_path: str, **settings):
        path = Path(audio_path)
        source = self.source_by_stem[path.stem]
        transcript = self.transform(path.stem, source)
        self.calls.append((audio_path, dict(settings)))
        if not self.include_words:
            return {"text": transcript, "segments": []}
        tokens = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", transcript)
        step = 8.0 / max(len(tokens), 1)
        words = [
            {
                "word": token,
                "start": round(index * step, 6),
                "end": round((index + 1) * step, 6),
                "probability": 0.99,
            }
            for index, token in enumerate(tokens)
        ]
        return {
            "text": transcript,
            "segments": [{"start": 0.0, "end": 8.0, "words": words}],
        }


class GoogleEnglishFullAudioDerivedQATests(unittest.TestCase):
    def test_evaluated_metrics_accepts_only_exact_jekyll_homophone_context(
        self,
    ) -> None:
        accepted = qa._evaluated_metrics(
            "Ah, that's not Jekyll's voice. It's Hyde's! cried Utterson.",
            "Ah, that's not Jekyll's voice. It's hides! cried Utterson.",
            slug="jekyll-and-hyde",
        )
        self.assertTrue(accepted["pass"])
        self.assertEqual(
            accepted["explicit_equivalences_applied"][0]["reason"],
            "EXPLICIT_JEKYLL_CONTEXTUAL_PHONETIC_EQUIVALENCE_HYDES_HIDES",
        )

        rejected = qa._evaluated_metrics(
            "It's Hyde's decision.",
            "It's hides decision.",
            slug="jekyll-and-hyde",
        )
        self.assertFalse(rejected["pass"])
        self.assertEqual(rejected["explicit_equivalences_applied"], [])

        wrong_title = qa._evaluated_metrics(
            "Ah, that's not Jekyll's voice. It's Hyde's! cried Utterson.",
            "Ah, that's not Jekyll's voice. It's hides! cried Utterson.",
            slug="another-title",
        )
        self.assertFalse(wrong_title["pass"])
        self.assertEqual(wrong_title["explicit_equivalences_applied"], [])

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.private_root = Path(self.temporary.name) / "private_audio"
        self.run_dir = self.private_root / "title" / "full" / "fingerprint"
        self.run_dir.mkdir(parents=True)
        paragraphs = [
            (
                f"Section {index + 1} begins beside the old laboratory door. "
                "Henry observes the lamplight, listens to the measured rain, "
                "and records each careful detail before the midnight bell. "
                f"The final sentence of section {index + 1} closes quietly."
            )
            for index in range(16)
        ]
        self.source = "\n\n".join(paragraphs) + "\n"
        self.source_path = self.run_dir / "sanitized_source.txt"
        self.source_path.write_text(self.source, encoding="utf-8")
        self.input_manifest_path = self.run_dir / "input_manifest.json"
        self.input_manifest = {
            "schema_version": qa.google_pipeline.INPUT_SCHEMA,
            "slug": "private-test-title",
            "title": "Private Test Title",
            "author": "Test Author",
            "language": "en",
            "sanitized_source_sha256": qa.sha256_file(self.source_path),
            "sanitization_status": "PASS",
            "rights_status": "PASS",
            "commercial_use_allowed": True,
        }
        self.input_manifest_path.write_text(
            json.dumps(self.input_manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        chunks = qa.google_pipeline.full_generation_chunks(
            self.source,
            max_chars=500,
        )
        self.assertGreaterEqual(len(chunks), 6)
        self.records: list[dict] = []
        self.source_by_stem: dict[str, str] = {}
        audio_dir = self.run_dir / "audio"
        audio_dir.mkdir()
        for chunk in chunks:
            audio_path = audio_dir / f"{chunk['chunk_id']}.mp3"
            audio_path.write_bytes(
                b"ID3" + f"private-google-{chunk['index']}".encode("ascii")
            )
            self.records.append(
                {
                    "unit_id": chunk["chunk_id"],
                    "text_sha256": chunk["text_sha256"],
                    "characters": chunk["characters"],
                    "audio_path": str(audio_path),
                    "audio_sha256": qa.sha256_file(audio_path),
                    "audio_size_bytes": audio_path.stat().st_size,
                }
            )
            self.source_by_stem[chunk["chunk_id"]] = chunk["text"]

        self.manifest_path = self.run_dir / "full_generation_manifest.json"
        manifest_sha = qa.sha256_file(self.input_manifest_path)
        units = [
            {
                "chunk_id": record["unit_id"],
                "text_sha256": record["text_sha256"],
                "characters": record["characters"],
            }
            for record in self.records
        ]
        fingerprint = qa.google_pipeline.attempt_fingerprint(
            mode="full",
            source_sha256=qa.sha256_file(self.source_path),
            manifest_sha256=manifest_sha,
            voice="en-GB-Chirp3-HD-Charon",
            language_code="en-GB",
            speaking_rate=0.94,
            pitch=0.0,
            units=units,
        )
        self.manifest = {
            "schema_version": qa.google_pipeline.PIPELINE_SCHEMA,
            "status": "FULL_GENERATION_PRIVATE_QA_PENDING",
            "mode": "full",
            "slug": self.input_manifest["slug"],
            "title": self.input_manifest["title"],
            "author": self.input_manifest["author"],
            "provider": "google",
            "voice": "en-GB-Chirp3-HD-Charon",
            "language_code": "en-GB",
            "speaking_rate": 0.94,
            "pitch": 0.0,
            "source_sha256": qa.sha256_file(self.source_path),
            "input_manifest_sha256": manifest_sha,
            "input_schema": self.input_manifest["schema_version"],
            "attempt_fingerprint": fingerprint,
            "audition_evidence_sha256": "a" * 64,
            "unit_count": len(self.records),
            "unit_hashes": [
                record["text_sha256"] for record in self.records
            ],
            "provider_calls_ran": True,
            "synthesis_calls": len(self.records),
            "result_manifest_path": str(self.manifest_path),
            "sanitized_source_copy": str(self.source_path),
            "input_manifest_copy": str(self.input_manifest_path),
            "generated_audio": self.records,
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "paid_lock_restored_byte_for_byte": True,
            "errors": [],
        }
        self.write_manifest()
        self.whisper_cache = self.private_root / "whisper-cache"
        self.whisper_cache.mkdir()
        self.model_path = self.whisper_cache / qa.WHISPER_FILENAME
        self.model_path.write_bytes(b"pinned-test-whisper")
        self.model_sha256 = qa.sha256_file(self.model_path)
        self.output_path = self.run_dir / "full_audio_derived_qa.json"

    def write_manifest(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def duration_getter(_path: Path) -> float:
        return 8.0

    def evaluate(
        self,
        *,
        model: MockWhisperModel | None = None,
        output: Path | None = None,
    ):
        selected = model or MockWhisperModel(self.source_by_stem)
        with mock.patch.object(qa, "WHISPER_SHA256", self.model_sha256):
            return qa.evaluate(
                self.manifest_path,
                output or self.output_path,
                whisper_cache=self.whisper_cache,
                model_loader=lambda *_args, **_kwargs: selected,
                duration_getter=self.duration_getter,
            )

    def test_passes_exact_full_title_audio_derived_asr_and_measured_sync(
        self,
    ) -> None:
        model = MockWhisperModel(self.source_by_stem)
        code, report = self.evaluate(model=model)
        self.assertEqual(code, 0)
        self.assertTrue(report["objective_pass"])
        self.assertEqual(
            report["status"],
            "FULL_AUDIO_DERIVED_ASR_SYNC_PASS_PRIVATE_ONLY",
        )
        self.assertEqual(report["audio_derived_asr"]["status"], "PASS")
        aggregate = report["audio_derived_asr"]["full_title_aggregate"]
        self.assertEqual(aggregate["score"], 10.0)
        self.assertEqual(aggregate["coverage"], 1.0)
        self.assertTrue(aggregate["first_words_match"])
        self.assertTrue(aggregate["last_words_match"])
        self.assertTrue(aggregate["ordered_content_integrity_pass"])
        self.assertTrue(report["measured_sync"]["sync_pass"])
        self.assertFalse(report["measured_sync"]["auto_estimated_sync"])
        self.assertFalse(
            report["measured_sync"]["public_word_level_sync_claim_allowed"]
        )
        self.assertEqual(
            report["audio_derived_asr"]["local_asr_run_count"],
            len(self.records),
        )
        self.assertFalse(report["provider_calls_made_by_adapter"])
        self.assertFalse(report["upload_performed"])
        self.assertFalse(report["publication_performed"])
        self.assertFalse(report["release_mutation_performed"])
        self.assertFalse(report["paid_lock_read_or_written"])
        for _path, settings in model.calls:
            self.assertIsNone(settings.get("initial_prompt"))
            self.assertTrue(settings["word_timestamps"])

    def test_report_is_byte_deterministic_for_same_bound_inputs(self) -> None:
        code, _report = self.evaluate()
        self.assertEqual(code, 0)
        first = self.output_path.read_bytes()
        self.output_path.unlink()
        code, _report = self.evaluate()
        self.assertEqual(code, 0)
        self.assertEqual(first, self.output_path.read_bytes())

    def test_one_chunk_omission_blocks_full_title_and_sync(self) -> None:
        target = self.records[len(self.records) // 2]["unit_id"]

        def omit_first_word(stem: str, text: str) -> str:
            if stem != target:
                return text
            return " ".join(text.split()[1:])

        model = MockWhisperModel(
            self.source_by_stem,
            transform=omit_first_word,
        )
        code, report = self.evaluate(model=model)
        self.assertEqual(code, 3)
        self.assertFalse(report["objective_pass"])
        self.assertEqual(report["audio_derived_asr"]["status"], "FAIL")
        self.assertFalse(report["measured_sync"]["sync_pass"])
        self.assertTrue(
            any(target in blocker for blocker in report["blockers"])
        )
        self.assertEqual(
            report["next_stage"],
            "STOP_NO_LISTENING_UPLOAD_OR_RELEASE",
        )

    def test_missing_audio_derived_timestamps_blocks(self) -> None:
        model = MockWhisperModel(
            self.source_by_stem,
            include_words=False,
        )
        code, report = self.evaluate(model=model)
        self.assertEqual(code, 3)
        self.assertFalse(report["objective_pass"])
        self.assertTrue(
            any(
                "AUDIO_DERIVED_TIMESTAMPS_INVALID" in blocker
                for blocker in report["blockers"]
            )
        )
        self.assertFalse(report["measured_sync"]["sync_pass"])

    def test_attempt_fingerprint_tamper_blocks_before_asr(self) -> None:
        self.manifest["attempt_fingerprint"] = "0" * 64
        self.write_manifest()
        model = MockWhisperModel(self.source_by_stem)
        code, report = self.evaluate(model=model)
        self.assertEqual(code, 2)
        self.assertFalse(report["objective_pass"])
        self.assertIn(
            "ATTEMPT_FINGERPRINT_MISMATCH",
            report["blockers"][0],
        )
        self.assertEqual(model.calls, [])

    def test_source_hash_tamper_blocks_before_asr(self) -> None:
        self.source_path.write_text(self.source + "tampered\n", encoding="utf-8")
        model = MockWhisperModel(self.source_by_stem)
        code, report = self.evaluate(model=model)
        self.assertEqual(code, 2)
        self.assertIn("SOURCE_HASH_MISMATCH", report["blockers"][0])
        self.assertEqual(model.calls, [])

    def test_audio_hash_tamper_blocks_before_asr(self) -> None:
        Path(self.records[0]["audio_path"]).write_bytes(b"ID3changed-audio")
        model = MockWhisperModel(self.source_by_stem)
        code, report = self.evaluate(model=model)
        self.assertEqual(code, 2)
        self.assertIn("AUDIO_SIZE_MISMATCH", report["blockers"][0])
        self.assertEqual(model.calls, [])

    def test_non_google_full_manifest_is_rejected(self) -> None:
        self.manifest["provider"] = "other"
        self.write_manifest()
        model = MockWhisperModel(self.source_by_stem)
        code, report = self.evaluate(model=model)
        self.assertEqual(code, 2)
        self.assertIn("PROVIDER_MISMATCH", report["blockers"][0])
        self.assertEqual(model.calls, [])

    def test_output_must_remain_inside_private_run(self) -> None:
        outside = self.private_root / "outside.json"
        code, report = self.evaluate(output=outside)
        self.assertEqual(code, 2)
        self.assertIn("NON_PRIVATE_OUTPUT", report["blockers"][0])
        self.assertFalse(outside.exists())

    def test_existing_output_is_immutable(self) -> None:
        self.output_path.write_text('{"preserve": true}\n', encoding="utf-8")
        original = self.output_path.read_bytes()
        code, report = self.evaluate()
        self.assertEqual(code, 2)
        self.assertIn("OUTPUT_ALREADY_EXISTS", report["blockers"][0])
        self.assertEqual(original, self.output_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
