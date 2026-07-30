#!/usr/bin/env python3
"""Tests for the read-only Jekyll chunk_0009 repair preflight."""

from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import sprint1_jekyll_chunk9_sentence_safe_repair_preflight as preflight


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JekyllChunk9SentenceSafePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def parent_fixture(
        self,
    ) -> tuple[Path, Path, str, dict[str, str]]:
        run_dir = self.root / "repaired_full" / "candidate"
        audio_dir = run_dir / "audio"
        audio_dir.mkdir(parents=True)
        target_text = (
            "Utterson though he took charge of it now that it was made, "
            f"{preflight.SYNTHESIS_CONTEXT} "
            "where his friend, the great Dr."
        )
        texts = [f"source text {index}" for index in range(92)]
        texts[8] = "prefix The will was holograph, for Mr."
        texts[9] = target_text
        texts[10] = (
            "Lanyon, had his house and received his crowding patients. suffix"
        )
        source = run_dir / "sanitized_source.txt"
        source.write_text(" ".join(texts), encoding="utf-8")
        input_manifest = run_dir / "input_manifest.json"
        input_manifest.write_text("{}\n", encoding="utf-8")
        records: list[dict[str, object]] = []
        current_hashes: list[str] = []
        for index, text in enumerate(texts):
            unit_id = f"chunk_{index:04d}"
            audio = audio_dir / f"{unit_id}.mp3"
            payload = f"ID3-{unit_id}-current".encode()
            audio.write_bytes(payload)
            audio_hash = sha256_file(audio)
            current_hashes.append(audio_hash)
            records.append(
                {
                    "unit_id": unit_id,
                    "characters": len(text),
                    "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "audio_path": str(audio),
                    "audio_sha256": audio_hash,
                    "audio_size_bytes": len(payload),
                }
            )
        root_hashes = list(current_hashes)
        root_hashes[36] = "0" * 64
        manifest = {
            "status": "FULL_GENERATION_PRIVATE_QA_PENDING",
            "slug": preflight.SLUG,
            "title": preflight.TITLE,
            "author": preflight.AUTHOR,
            "provider": preflight.PROVIDER,
            "voice": preflight.VOICE,
            "language_code": preflight.LANGUAGE_CODE,
            "speaking_rate": preflight.SPEAKING_RATE,
            "pitch": preflight.PITCH,
            "source_sha256": sha256_file(source),
            "input_manifest_sha256": sha256_file(input_manifest),
            "unit_count": 92,
            "candidate_audio_sequence_sha256": (
                preflight.candidate_qa.sha256_json(current_hashes)
            ),
            "private_output_only": True,
            "public_release_approved": False,
            "upload_performed": False,
            "publication_performed": False,
            "release_mutation_performed": False,
            "sanitized_source_copy": str(source),
            "input_manifest_copy": str(input_manifest),
            "generated_audio": records,
            "bounded_chunk_repair": {
                "base_ordered_audio_hashes": root_hashes,
                "changed_chunk_indexes": [36],
                "base_full_manifest_sha256": "1" * 64,
            },
        }
        manifest_path = run_dir / "full_generation_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        repair = {
            "slug": preflight.SLUG,
            "repair_attempt_fingerprint": "2" * 64,
            "replacement_full_manifest_sha256": sha256_file(manifest_path),
            "candidate_audio_sequence_sha256": (
                preflight.candidate_qa.sha256_json(current_hashes)
            ),
            "candidate_binding_sha256": "3" * 64,
            "replacement_audio_sha256": current_hashes[36],
            "changed_chunk_indexes": [36],
            "preserved_audio_file_count": 91,
            "provider_calls_ran": True,
            "paid_lock_restored_byte_for_byte": True,
            "budget": {
                "projected_title_spend_usd": 3.51777,
                "projected_sprint_spend_usd": 18.72386,
            },
        }
        repair_path = run_dir / "bounded_chunk_repair_evidence.json"
        repair_path.write_text(
            json.dumps(repair, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        constants = {
            "EXPECTED_PARENT_MANIFEST_SHA256": sha256_file(manifest_path),
            "EXPECTED_CHUNK36_REPAIR_EVIDENCE_SHA256": (
                sha256_file(repair_path)
            ),
            "EXPECTED_SOURCE_SHA256": sha256_file(source),
            "EXPECTED_INPUT_MANIFEST_SHA256": sha256_file(input_manifest),
            "EXPECTED_PARENT_AUDIO_SEQUENCE_SHA256": (
                preflight.candidate_qa.sha256_json(current_hashes)
            ),
            "EXPECTED_PARENT_CANDIDATE_BINDING_SHA256": "3" * 64,
            "EXPECTED_ROOT_MANIFEST_SHA256": "1" * 64,
            "EXPECTED_CHUNK36_REPAIR_FINGERPRINT": "2" * 64,
            "EXPECTED_CHUNK36_AUDIO_SHA256": current_hashes[36],
            "TARGET_TEXT_SHA256": records[9]["text_sha256"],
            "TARGET_AUDIO_SHA256": current_hashes[9],
            "TARGET_AUDIO_SIZE_BYTES": records[9]["audio_size_bytes"],
        }
        return manifest_path, repair_path, target_text, constants

    def patched_constants(self, values: dict[str, object]) -> ExitStack:
        stack = ExitStack()
        for name, value in values.items():
            stack.enter_context(mock.patch.object(preflight, name, value))
        return stack

    def test_exact_missing_span_and_context_contract(self) -> None:
        self.assertEqual(
            len(preflight.normalized_tokens(preflight.MISSING_CANONICAL_SPAN)),
            16,
        )
        self.assertEqual(len(preflight.SYNTHESIS_CONTEXT), 192)
        target = (
            "prefix "
            + preflight.SYNTHESIS_CONTEXT
            + " suffix"
        )
        with mock.patch.object(
            preflight,
            "TARGET_TEXT_SHA256",
            hashlib.sha256(target.encode()).hexdigest(),
        ):
            result = preflight.validate_text_contract(target)
        self.assertEqual(result["missing_span_token_count"], 16)
        self.assertEqual(result["synthesis_context_characters"], 192)
        self.assertIn("doctor’s household", result["replacement_clause"])

    def test_parent_validation_preserves_chunk36_and_other_91_hashes(
        self,
    ) -> None:
        manifest, repair, _target, constants = self.parent_fixture()
        with self.patched_constants(constants):
            _payload, _segments, preserved, hashes = (
                preflight.validate_parent_candidate(manifest, repair)
            )
        self.assertEqual(len(preserved), 91)
        self.assertNotIn("chunk_0009", preserved)
        self.assertEqual(
            preserved["chunk_0036"],
            constants["EXPECTED_CHUNK36_AUDIO_SHA256"],
        )
        self.assertEqual(len(hashes), 92)

    def test_parent_validation_rejects_tampered_non_target_audio(self) -> None:
        manifest, repair, _target, constants = self.parent_fixture()
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        Path(payload["generated_audio"][12]["audio_path"]).write_bytes(b"tampered")
        with (
            self.patched_constants(constants),
            self.assertRaisesRegex(
                preflight.Chunk9PreflightError,
                "chunk_0012 audio hash changed",
            ),
        ):
            preflight.validate_parent_candidate(manifest, repair)

    def test_omission_evidence_binds_exact_measured_splice(self) -> None:
        diagnostic = self.root / "diagnostic.json"
        report = self.root / "report.json"
        raw = self.root / "raw.json"
        raw_payload = {
            "segments": [
                {
                    "words": [
                        {"word": " delay", "start": 29.72, "end": 30.10},
                        {"word": " and", "start": 30.10, "end": 30.62},
                        {"word": " free", "start": 30.62, "end": 30.90},
                        {"word": " from", "start": 30.90, "end": 31.14},
                        {"word": " any", "start": 31.14, "end": 31.34},
                        {"word": " burthen", "start": 31.34, "end": 31.76},
                        {"word": " or", "start": 31.76, "end": 31.92},
                        {"word": " this", "start": 31.92, "end": 32.42},
                    ]
                }
            ]
        }
        raw.write_text(json.dumps(raw_payload) + "\n", encoding="utf-8")
        diagnostic.write_text(
            json.dumps(
                {
                    "decision": (
                        "FULL_TITLE_MLX_RUN_BLOCKED_CHUNK9_"
                        "NARRATION_OMISSION_CONFIRMED"
                    ),
                    "unit_comparison": [
                        {
                            "unit_id": preflight.TARGET_UNIT_ID,
                            "source_text_sha256": preflight.TARGET_TEXT_SHA256,
                            "audio_sha256": preflight.TARGET_AUDIO_SHA256,
                            "cross_model_finding": (
                                "ACTUAL_NARRATION_CONTENT_OMISSION"
                            ),
                            "missing_source_token_count": 16,
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        report.write_text(
            json.dumps(
                {
                    "reports": [
                        {
                            "unit_id": preflight.TARGET_UNIT_ID,
                            "source_text_sha256": preflight.TARGET_TEXT_SHA256,
                            "audio_sha256": preflight.TARGET_AUDIO_SHA256,
                            "raw_result_sha256": sha256_file(raw),
                            "strict_objective_pass": False,
                        }
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        patches = {
            "EXPECTED_DIAGNOSTIC_EVIDENCE_SHA256": sha256_file(diagnostic),
            "EXPECTED_TURBO_REPORT_SHA256": sha256_file(report),
            "EXPECTED_TURBO_RAW_SHA256": sha256_file(raw),
        }
        with self.patched_constants(patches):
            result = preflight.validate_omission_evidence(
                diagnostic,
                report,
                raw,
            )
        self.assertEqual(result["replace_start_seconds"], 30.10)
        self.assertEqual(result["replace_end_seconds"], 31.92)
        self.assertEqual(result["missing_audio_gap_seconds"], 0.0)

    def test_paid_lock_is_read_only_and_scoped(self) -> None:
        lock = self.root / "paid_tts.lock"
        lock.write_text(
            json.dumps(
                {
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                    "allowed_slugs": [preflight.SLUG],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        before = lock.read_bytes()
        with mock.patch.object(
            preflight,
            "EXPECTED_PAID_LOCK_SHA256",
            hashlib.sha256(before).hexdigest(),
        ):
            payload, observed = preflight.validate_paid_lock_read_only(lock)
        self.assertEqual(payload["current_holder"], "none")
        self.assertEqual(observed, hashlib.sha256(before).hexdigest())
        self.assertEqual(lock.read_bytes(), before)

    def test_budget_is_bounded_and_deterministic(self) -> None:
        result = preflight.budget_plan(
            {
                "budget": {
                    "projected_title_spend_usd": 3.51777,
                    "projected_sprint_spend_usd": 18.72386,
                }
            }
        )
        self.assertEqual(result["estimated_run_usd"], 0.00576)
        self.assertEqual(result["projected_title_spend_usd"], 3.52353)
        self.assertEqual(result["projected_sprint_spend_usd"], 18.72962)

    def test_cli_has_no_execute_or_provider_path(self) -> None:
        parser = preflight.build_parser()
        option_strings = {
            option
            for action in parser._actions
            for option in action.option_strings
        }
        self.assertNotIn("--execute", option_strings)
        source = Path(preflight.__file__).read_text(encoding="utf-8")
        self.assertNotIn("GoogleCloudTTSProvider", source)
        self.assertNotIn(".synthesize(", source)

    def test_output_is_private_and_immutable(self) -> None:
        parent = self.root / "candidate" / "full_generation_manifest.json"
        parent.parent.mkdir()
        parent.write_text("{}\n", encoding="utf-8")
        allowed = (
            parent.parent
            / "chunk9_repair_preflight"
            / "sentence_safe_plan.json"
        )
        self.assertEqual(
            preflight.validate_output_path(allowed, parent),
            allowed.resolve(),
        )
        with self.assertRaisesRegex(
            preflight.Chunk9PreflightError,
            "private chunk9_repair_preflight",
        ):
            preflight.validate_output_path(self.root / "public.json", parent)
        allowed.parent.mkdir()
        allowed.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(
            preflight.Chunk9PreflightError,
            "already exists",
        ):
            preflight.validate_output_path(allowed, parent)


if __name__ == "__main__":
    unittest.main()
