#!/usr/bin/env python3
"""Focused tests for the one-chunk Jekyll Google repair contract."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sprint1_google_english_full_candidate_qa as candidate_qa
import sprint1_jekyll_google_chunk36_bounded_repair as repair


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class FakeProvider:
    def __init__(self, audio: bytes = b"ID3-replacement-audio") -> None:
        self.audio = audio
        self.calls: list[dict[str, object]] = []

    def synthesize(self, **kwargs: object) -> bytes:
        self.calls.append(dict(kwargs))
        return self.audio


class BoundedJekyllRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def evidence(self) -> candidate_qa.CandidateEvidence:
        source = self.root / "base" / "sanitized_source.txt"
        input_manifest = self.root / "base" / "input_manifest.json"
        manifest = self.root / "base" / "full_generation_manifest.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("source", encoding="utf-8")
        input_manifest.write_text("{}\n", encoding="utf-8")
        manifest.write_text("{}\n", encoding="utf-8")
        records: list[dict[str, object]] = []
        for index in range(repair.EXPECTED_UNIT_COUNT):
            audio = self.root / "base" / "audio" / f"chunk_{index:04d}.mp3"
            audio.parent.mkdir(parents=True, exist_ok=True)
            payload = f"ID3-base-{index:04d}".encode()
            audio.write_bytes(payload)
            text = (
                "target source text"
                if index == repair.TARGET_INDEX
                else f"source text {index}"
            )
            records.append(
                {
                    "unit_id": f"chunk_{index:04d}",
                    "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "characters": len(text),
                    "audio_path": str(audio),
                    "audio_sha256": sha256(payload),
                    "audio_size_bytes": len(payload),
                    "source_text": text,
                    "measured_duration_seconds": 1.0,
                }
            )
        base_hashes = [str(record["audio_sha256"]) for record in records]
        manifest_payload = {
            "schema_version": repair.google_pipeline.PIPELINE_SCHEMA,
            "status": "FULL_GENERATION_PRIVATE_QA_PENDING",
            "mode": "full",
            "slug": repair.SLUG,
            "title": repair.TITLE,
            "author": repair.AUTHOR,
            "provider": "google",
            "voice": repair.BASE_VOICE,
            "language_code": repair.BASE_LANGUAGE_CODE,
            "speaking_rate": repair.BASE_SPEAKING_RATE,
            "pitch": repair.BASE_PITCH,
            "attempt_fingerprint": repair.EXPECTED_BASE_ATTEMPT_FINGERPRINT,
            "audition_evidence_sha256": "a" * 64,
            "unit_count": len(records),
            "unit_hashes": [record["text_sha256"] for record in records],
            "synthesis_calls": len(records),
            "generated_audio": records,
            "input_schema": repair.google_pipeline.INPUT_SCHEMA,
            "private_output_only": True,
            "public_release_approved": False,
            "provider_calls_ran": True,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "paid_lock_restored_byte_for_byte": True,
            "errors": [],
        }
        return candidate_qa.CandidateEvidence(
            manifest=manifest_payload,
            manifest_path=manifest,
            manifest_sha256=sha256(manifest.read_bytes()),
            source_path=source,
            source_sha256=sha256(source.read_bytes()),
            input_manifest_path=input_manifest,
            input_manifest_sha256=sha256(input_manifest.read_bytes()),
            records=records,
            measured_sync={},
            construction={},
            candidate_audio_sequence_sha256=candidate_qa.sha256_json(base_hashes),
            candidate_binding_sha256="b" * 64,
        )

    def config(self, *, execute: bool) -> repair.RepairConfig:
        lock = self.root / "paid_tts.lock"
        lock.write_text(
            json.dumps(
                {
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return repair.RepairConfig(
            full_manifest=self.root / "base" / "full_generation_manifest.json",
            failed_listening_evidence=self.root / "failed_listening.json",
            paid_lock=lock,
            private_output_dir=self.root / "private",
            voice=repair.RECOMMENDED_VOICE,
            language_code=repair.BASE_LANGUAGE_CODE,
            speaking_rate=repair.RECOMMENDED_SPEAKING_RATE,
            pitch=repair.RECOMMENDED_PITCH,
            usd_per_million_chars=30.0,
            run_budget_usd=0.10,
            title_budget_usd=8.0,
            title_spend_usd=1.0,
            sprint_budget_usd=75.0,
            sprint_spend_usd=10.0,
            project_id="earnalism",
            execute=execute,
        )

    def test_fingerprint_is_deterministic_and_differs_from_base_settings(self) -> None:
        first = repair.unit_attempt_fingerprint(
            source_sha256=repair.EXPECTED_SOURCE_SHA256,
            input_manifest_sha256=repair.EXPECTED_INPUT_MANIFEST_SHA256,
            base_full_manifest_sha256=repair.EXPECTED_FULL_MANIFEST_SHA256,
            text_sha256=repair.TARGET_TEXT_SHA256,
            prior_audio_sha256=repair.TARGET_PRIOR_AUDIO_SHA256,
            voice=repair.RECOMMENDED_VOICE,
            language_code=repair.BASE_LANGUAGE_CODE,
            speaking_rate=repair.RECOMMENDED_SPEAKING_RATE,
            pitch=repair.RECOMMENDED_PITCH,
        )
        second = repair.unit_attempt_fingerprint(
            source_sha256=repair.EXPECTED_SOURCE_SHA256,
            input_manifest_sha256=repair.EXPECTED_INPUT_MANIFEST_SHA256,
            base_full_manifest_sha256=repair.EXPECTED_FULL_MANIFEST_SHA256,
            text_sha256=repair.TARGET_TEXT_SHA256,
            prior_audio_sha256=repair.TARGET_PRIOR_AUDIO_SHA256,
            voice=repair.RECOMMENDED_VOICE,
            language_code=repair.BASE_LANGUAGE_CODE,
            speaking_rate=repair.RECOMMENDED_SPEAKING_RATE,
            pitch=repair.RECOMMENDED_PITCH,
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, repair.base_unit_fingerprint())

    def test_exact_base_voice_rate_pitch_is_rejected(self) -> None:
        config = self.config(execute=False)
        duplicate = repair.RepairConfig(
            **{
                **config.__dict__,
                "voice": repair.BASE_VOICE,
                "speaking_rate": repair.BASE_SPEAKING_RATE,
                "pitch": repair.BASE_PITCH,
            }
        )
        with self.assertRaisesRegex(
            repair.BoundedRepairError,
            "must not repeat",
        ):
            repair.validate_config(duplicate)

    def test_closed_provider_fingerprint_is_rejected(self) -> None:
        output = self.root / "private"
        fingerprint = "c" * 64
        state = (
            output / repair.SLUG / "repair_attempts" / f"{fingerprint}.json"
        )
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(
            json.dumps(
                {
                    "attempt_fingerprint": fingerprint,
                    "provider_calls_ran": True,
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.object(repair, "NO_REPEAT_REGISTRIES", ()):
            with self.assertRaisesRegex(
                repair.BoundedRepairError,
                "already reached Google",
            ):
                repair.reject_repeated_fingerprint(output, fingerprint)

    def test_execute_calls_google_once_restores_lock_and_preserves_91_files(
        self,
    ) -> None:
        evidence = self.evidence()
        target = evidence.records[repair.TARGET_INDEX]
        config = self.config(execute=True)
        original_lock = config.paid_lock.read_bytes()
        provider = FakeProvider()

        def validate_repaired(
            manifest_path: Path,
            *,
            duration_probe: object,
        ) -> candidate_qa.CandidateEvidence:
            del duration_probe
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            records = payload["generated_audio"]
            hashes = [record["audio_sha256"] for record in records]
            return candidate_qa.CandidateEvidence(
                manifest=payload,
                manifest_path=manifest_path,
                manifest_sha256=sha256(manifest_path.read_bytes()),
                source_path=Path(payload["sanitized_source_copy"]),
                source_sha256=evidence.source_sha256,
                input_manifest_path=Path(payload["input_manifest_copy"]),
                input_manifest_sha256=evidence.input_manifest_sha256,
                records=records,
                measured_sync={},
                construction={},
                candidate_audio_sequence_sha256=candidate_qa.sha256_json(
                    hashes
                ),
                candidate_binding_sha256="d" * 64,
            )

        patches = (
            mock.patch.object(
                repair,
                "validate_bound_inputs",
                return_value=(evidence, {}, target),
            ),
            mock.patch.object(
                repair.candidate_qa,
                "validate_full_candidate",
                side_effect=validate_repaired,
            ),
            mock.patch.object(repair, "TARGET_TEXT_SHA256", target["text_sha256"]),
            mock.patch.object(
                repair,
                "TARGET_PRIOR_AUDIO_SHA256",
                target["audio_sha256"],
            ),
            mock.patch.object(
                repair,
                "TARGET_PRIOR_AUDIO_SIZE_BYTES",
                target["audio_size_bytes"],
            ),
            mock.patch.object(
                repair,
                "EXPECTED_SOURCE_SHA256",
                evidence.source_sha256,
            ),
            mock.patch.object(
                repair,
                "EXPECTED_INPUT_MANIFEST_SHA256",
                evidence.input_manifest_sha256,
            ),
            mock.patch.object(
                repair,
                "EXPECTED_FULL_MANIFEST_SHA256",
                evidence.manifest_sha256,
            ),
            mock.patch.object(
                repair,
                "EXPECTED_BASE_AUDIO_SEQUENCE_SHA256",
                evidence.candidate_audio_sequence_sha256,
            ),
            mock.patch.object(
                repair,
                "EXPECTED_BASE_CANDIDATE_BINDING_SHA256",
                evidence.candidate_binding_sha256,
            ),
            mock.patch.object(repair, "NO_REPEAT_REGISTRIES", ()),
            mock.patch.dict(
                os.environ,
                {
                    repair.APPROVAL_ENV: "true",
                    repair.STOP_ON_BUDGET_ENV: "true",
                    "GOOGLE_CLOUD_PROJECT": "earnalism",
                },
                clear=False,
            ),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[
            5
        ], patches[6], patches[7], patches[8], patches[9], patches[10], patches[
            11
        ]:
            result = repair.run(
                config,
                provider_factory=lambda _config: provider,
                duration_probe=lambda _path: 1.0,
            )

        self.assertEqual(
            result["status"],
            "REPLACEMENT_FULL_CANDIDATE_PRIVATE_QA_PENDING",
        )
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0]["text"], target["source_text"])
        self.assertEqual(provider.calls[0]["speaking_rate"], 1.0)
        self.assertEqual(config.paid_lock.read_bytes(), original_lock)
        self.assertTrue(result["paid_lock_restored_byte_for_byte"])
        manifest = json.loads(
            Path(result["replacement_full_manifest_path"]).read_text(
                encoding="utf-8"
            )
        )
        before = [record["audio_sha256"] for record in evidence.records]
        after = [record["audio_sha256"] for record in manifest["generated_audio"]]
        changed = [
            index
            for index, (old, new) in enumerate(zip(before, after))
            if old != new
        ]
        self.assertEqual(changed, [repair.TARGET_INDEX])
        self.assertEqual(
            manifest["bounded_chunk_repair"]["preserved_audio_file_count"],
            91,
        )
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["release_mutation_performed"])


if __name__ == "__main__":
    unittest.main()
