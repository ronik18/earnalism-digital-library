#!/usr/bin/env python3
"""Focused tests for the one-title private Google English TTS pipeline."""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_google_english_private_pipeline.py")
SPEC = importlib.util.spec_from_file_location(
    "sprint1_google_english_private_pipeline", SCRIPT
)
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = pipeline
SPEC.loader.exec_module(pipeline)


@contextmanager
def paid_runtime_env() -> None:
    updates = {
        "EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_AUDITION": "true",
        "EARNALISM_APPROVE_GOOGLE_ENGLISH_PRIVATE_FULL": "true",
        "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
        "GOOGLE_CLOUD_PROJECT": "test-project",
    }
    before = {name: os.environ.get(name) for name in updates}
    try:
        os.environ.update(updates)
        yield
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class MockProvider:
    def __init__(self, *, fail_on_synthesis: int | None = None) -> None:
        self.fail_on_synthesis = fail_on_synthesis
        self.voice_checks: list[tuple[str, str]] = []
        self.synthesis_calls: list[dict] = []

    def ensure_voice(self, *, voice: str, language_code: str) -> None:
        self.voice_checks.append((voice, language_code))

    def synthesize(self, **kwargs) -> bytes:
        self.synthesis_calls.append(dict(kwargs))
        if self.fail_on_synthesis == len(self.synthesis_calls):
            raise RuntimeError("mock provider failure")
        return b"ID3-private-mock\x00" + kwargs["text"].encode("utf-8")


class GoogleEnglishPrivatePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source_path = self.root / "sanitized_source.txt"
        self.manifest_path = self.root / "input_manifest.json"
        self.lock_path = self.root / "paid_tts.lock"
        self.output_dir = self.root / "private-output"
        self.source = (
            "The rain stopped before dawn. "
            "A narrow road shone beneath the lamps. "
            "Clara crossed the empty square. "
            "A clock sounded from the tower. "
            "She found a letter beneath the gate. "
            '"Who waits beyond the wall?" Clara asked. '
            "No answer came from the garden. "
            "The hinges complained as she entered. "
            "Halfway through the orchard, the wind changed. "
            "Branches struck the glass with a measured rhythm. "
            "She read the warning twice; then folded it carefully. "
            "A footstep answered from the dark. "
            "Clara lifted the lamp and continued. "
            "The eastern sky slowly brightened. "
            "Birdsong returned to the hedges. "
            "At sunrise, she closed the gate behind her.\n"
        )
        source_bytes = self.source.encode("utf-8")
        self.source_path.write_bytes(source_bytes)
        self.manifest = {
            "schema_version": pipeline.INPUT_SCHEMA,
            "slug": "private-test-title",
            "title": "Private Test Title",
            "author": "Test Author",
            "language": "en",
            "sanitized_source_sha256": pipeline.sha256_bytes(source_bytes),
            "sanitization_status": "PASS",
            "rights_status": "PASS",
            "commercial_use_allowed": True,
        }
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )
        self.original_lock = (
            b'{ "status" : "active", "current_holder" : "none", '
            b'"allowed_next_holders" : [], "note" : "preserve spacing" }\n\n'
        )
        self.lock_path.write_bytes(self.original_lock)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def config(self, mode: str, **overrides) -> pipeline.PipelineConfig:
        values = {
            "mode": mode,
            "source_path": self.source_path,
            "manifest_path": self.manifest_path,
            "lock_path": self.lock_path,
            "private_output_dir": self.output_dir,
            "voice": "en-GB-Studio-C",
            "usd_per_million_chars": 16.0,
            "run_budget_usd": 1.0,
            "title_budget_usd": 5.0,
            "sprint_budget_usd": 175.0,
            "title_spend_usd": 0.25,
            "sprint_spend_usd": 4.25,
            "project_id": "test-project",
            "execute": True,
        }
        values.update(overrides)
        return pipeline.PipelineConfig(**values)

    def run_with(self, config: pipeline.PipelineConfig, provider: MockProvider) -> dict:
        with paid_runtime_env():
            return pipeline.run_pipeline(
                config, provider_factory=lambda _config: provider
            )

    def complete_listening_evidence(self, result: dict, *, score: float = 9.5) -> Path:
        path = Path(result["listening_evidence_path"])
        evidence = json.loads(path.read_text(encoding="utf-8"))
        evidence["status"] = "PASS"
        for sample in evidence["samples"]:
            sample["overall_listening_score"] = score
            sample["confidence_score"] = 0.95
            sample["fatal_flags"] = []
        path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        return path

    def test_selects_opening_middle_dialogue_or_risk_and_ending(self) -> None:
        passages = pipeline.select_representative_passages(self.source)
        self.assertEqual(
            [item["passage_id"] for item in passages], list(pipeline.PASSAGE_IDS)
        )
        self.assertTrue(passages[0]["text"].startswith("The rain stopped"))
        self.assertIn("Who waits beyond the wall", passages[2]["text"])
        self.assertGreaterEqual(len(passages[2]["text"]), 200)
        self.assertGreater(len(passages[2]["source_sentence_indexes"]), 1)
        self.assertTrue(passages[-1]["text"].endswith("closed the gate behind her."))
        self.assertEqual(len({item["text_sha256"] for item in passages}), 4)

    def test_source_must_match_hash_bound_manifest(self) -> None:
        changed = dict(self.manifest)
        changed["sanitized_source_sha256"] = "0" * 64
        self.manifest_path.write_text(json.dumps(changed), encoding="utf-8")
        provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(self.config("audition"), provider)
        self.assertEqual(raised.exception.status, "BLOCKED_SOURCE_HASH_MISMATCH")
        self.assertEqual(provider.synthesis_calls, [])
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)

    def test_reader_boilerplate_is_rejected_before_provider(self) -> None:
        contaminated = self.source + "*** END OF THIS PROJECT GUTENBERG EBOOK ***\n"
        self.source_path.write_text(contaminated, encoding="utf-8")
        self.manifest["sanitized_source_sha256"] = pipeline.sha256_bytes(
            contaminated.encode("utf-8")
        )
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(self.config("audition"), provider)
        self.assertEqual(raised.exception.status, "BLOCKED_SOURCE_SANITATION")
        self.assertEqual(provider.synthesis_calls, [])

    def test_repo_public_output_is_rejected(self) -> None:
        provider = MockProvider()
        public_path = pipeline.ROOT / "frontend/public/private-pipeline-test"
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(
                self.config("audition", private_output_dir=public_path), provider
            )
        self.assertEqual(raised.exception.status, "BLOCKED_NON_PRIVATE_OUTPUT")
        self.assertEqual(provider.synthesis_calls, [])
        self.assertFalse(public_path.exists())

    def test_external_public_named_output_is_rejected(self) -> None:
        provider = MockProvider()
        public_path = self.root / "public" / "candidate"
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(
                self.config("audition", private_output_dir=public_path), provider
            )
        self.assertEqual(raised.exception.status, "BLOCKED_NON_PRIVATE_OUTPUT")
        self.assertEqual(provider.synthesis_calls, [])
        self.assertFalse(public_path.exists())

    def test_budget_blocks_before_provider_or_lock_write(self) -> None:
        provider = MockProvider()
        config = self.config("audition", run_budget_usd=0.000001)
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(config, provider)
        self.assertEqual(raised.exception.status, "BLOCKED_BUDGET")
        self.assertEqual(provider.voice_checks, [])
        self.assertEqual(provider.synthesis_calls, [])
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)

    def test_utf8_byte_limit_blocks_oversized_google_unit(self) -> None:
        units = [{"passage_id": "opening", "text": "\u2019" * 1600}]
        with self.assertRaises(pipeline.PipelineError) as raised:
            pipeline.validate_google_unit_sizes(units)
        self.assertEqual(raised.exception.status, "BLOCKED_GOOGLE_INPUT_LIMIT")

    def test_audition_calls_mock_for_four_passages_and_restores_lock_bytes(
        self,
    ) -> None:
        provider = MockProvider()
        result = self.run_with(self.config("audition"), provider)
        self.assertEqual(
            result["status"], "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED"
        )
        self.assertEqual(len(provider.voice_checks), 1)
        self.assertEqual(len(provider.synthesis_calls), 4)
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)
        self.assertTrue(result["paid_lock_restored_byte_for_byte"])
        self.assertTrue(Path(result["result_manifest_path"]).is_file())
        evidence = json.loads(
            Path(result["listening_evidence_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["status"], "PENDING_LISTENING_REVIEW")
        self.assertEqual(
            [item["passage_id"] for item in evidence["samples"]],
            list(pipeline.PASSAGE_IDS),
        )
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["release_mutation_performed"])
        command = shlex.split(result["next_exact_command"])
        title_spend_index = command.index("--title-spend-usd") + 1
        sprint_spend_index = command.index("--sprint-spend-usd") + 1
        self.assertEqual(
            float(command[title_spend_index]),
            result["budget"]["projected_title_spend_usd"],
        )
        self.assertEqual(
            float(command[sprint_spend_index]),
            result["budget"]["projected_sprint_spend_usd"],
        )

    def test_provider_failure_still_restores_lock_byte_for_byte(self) -> None:
        provider = MockProvider(fail_on_synthesis=1)
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(self.config("audition"), provider)
        self.assertEqual(raised.exception.status, "PROVIDER_EXECUTION_FAILED")
        self.assertEqual(len(provider.synthesis_calls), 1)
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)
        result_path = Path(raised.exception.details["result_manifest_path"])
        result = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertTrue(result["paid_lock_restored_byte_for_byte"])
        self.assertTrue(result["private_output_only"])

    def test_provider_construction_failure_does_not_poison_fingerprint(self) -> None:
        config = self.config("audition")

        def failing_factory(_config):
            raise RuntimeError("mock construction failure")

        with paid_runtime_env(), self.assertRaises(pipeline.PipelineError) as raised:
            pipeline.run_pipeline(config, provider_factory=failing_factory)
        self.assertEqual(raised.exception.status, "PROVIDER_EXECUTION_FAILED")
        self.assertFalse(raised.exception.details["provider_calls_ran"])
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)

        provider = MockProvider()
        result = self.run_with(config, provider)
        self.assertEqual(
            result["status"], "AUDITION_AUDIO_READY_LISTENING_REVIEW_REQUIRED"
        )
        self.assertEqual(len(provider.synthesis_calls), 4)

    def test_fingerprint_dedupe_blocks_second_provider_attempt(self) -> None:
        provider = MockProvider()
        first = self.run_with(self.config("audition"), provider)
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(self.config("audition"), provider)
        self.assertEqual(raised.exception.status, "BLOCKED_DUPLICATE_FINGERPRINT")
        self.assertEqual(
            raised.exception.details["attempt_fingerprint"],
            first["attempt_fingerprint"],
        )
        self.assertEqual(len(provider.synthesis_calls), 4)
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)

    def test_full_mode_requires_listening_evidence_before_provider(self) -> None:
        provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(self.config("full"), provider)
        self.assertEqual(raised.exception.status, "BLOCKED_AUDITION_EVIDENCE")
        self.assertEqual(provider.voice_checks, [])
        self.assertEqual(provider.synthesis_calls, [])
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)

    def test_pending_or_low_listening_evidence_blocks_full_mode(self) -> None:
        audition_provider = MockProvider()
        audition = self.run_with(self.config("audition"), audition_provider)
        evidence_path = Path(audition["listening_evidence_path"])
        full_provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as pending:
            self.run_with(
                self.config("full", audition_evidence_path=evidence_path), full_provider
            )
        self.assertEqual(pending.exception.status, "BLOCKED_AUDITION_EVIDENCE")
        self.assertEqual(full_provider.synthesis_calls, [])

        self.complete_listening_evidence(audition, score=9.1)
        with self.assertRaises(pipeline.PipelineError) as low:
            self.run_with(
                self.config("full", audition_evidence_path=evidence_path), full_provider
            )
        self.assertEqual(low.exception.status, "BLOCKED_AUDITION_EVIDENCE")
        self.assertTrue(
            any("below 9.3" in item for item in low.exception.details["blockers"])
        )
        self.assertEqual(full_provider.synthesis_calls, [])

    def test_fatal_flag_blocks_full_mode_before_provider(self) -> None:
        audition = self.run_with(self.config("audition"), MockProvider())
        evidence_path = self.complete_listening_evidence(audition)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["samples"][2]["judge_flags"]["mechanical_cadence_detected"] = True
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(
                self.config("full", audition_evidence_path=evidence_path), provider
            )
        self.assertEqual(raised.exception.status, "BLOCKED_AUDITION_EVIDENCE")
        self.assertEqual(provider.synthesis_calls, [])

    def test_non_finite_listening_evidence_blocks_full_mode(self) -> None:
        audition = self.run_with(self.config("audition"), MockProvider())
        evidence_path = self.complete_listening_evidence(audition)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["samples"][0]["overall_listening_score"] = float("nan")
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(
                self.config("full", audition_evidence_path=evidence_path), provider
            )
        self.assertEqual(raised.exception.status, "BLOCKED_AUDITION_EVIDENCE")
        self.assertTrue(
            any(
                "must be finite" in item
                for item in raised.exception.details["blockers"]
            )
        )
        self.assertEqual(provider.synthesis_calls, [])

    def test_passing_hash_bound_audition_evidence_unlocks_private_full_mode(
        self,
    ) -> None:
        audition = self.run_with(self.config("audition"), MockProvider())
        evidence_path = self.complete_listening_evidence(audition)
        full_provider = MockProvider()
        result = self.run_with(
            self.config("full", audition_evidence_path=evidence_path),
            full_provider,
        )
        self.assertEqual(result["status"], "FULL_GENERATION_PRIVATE_QA_PENDING")
        self.assertGreaterEqual(len(full_provider.synthesis_calls), 1)
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)
        self.assertEqual(
            result["source_sha256"], self.manifest["sanitized_source_sha256"]
        )
        self.assertEqual(
            result["input_manifest_sha256"],
            pipeline.sha256_bytes(self.manifest_path.read_bytes()),
        )
        self.assertTrue(result["audition_evidence_sha256"])
        self.assertFalse(result["public_release_approved"])
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["release_mutation_performed"])
        for artifact in result["generated_audio"]:
            self.assertTrue(
                pipeline.is_within(
                    Path(artifact["audio_path"]), self.output_dir.resolve()
                )
            )

    def test_voice_or_source_binding_change_invalidates_audition_evidence(self) -> None:
        audition = self.run_with(self.config("audition"), MockProvider())
        evidence_path = self.complete_listening_evidence(audition)
        provider = MockProvider()
        changed_voice = self.config(
            "full",
            voice="en-US-Neural2-J",
            audition_evidence_path=evidence_path,
        )
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(changed_voice, provider)
        self.assertEqual(raised.exception.status, "BLOCKED_AUDITION_EVIDENCE")
        self.assertEqual(provider.synthesis_calls, [])

    def test_tampered_audition_manifest_invalidates_listening_evidence(self) -> None:
        audition = self.run_with(self.config("audition"), MockProvider())
        evidence_path = self.complete_listening_evidence(audition)
        audition_manifest = Path(audition["result_manifest_path"])
        audition_manifest.write_bytes(audition_manifest.read_bytes() + b" ")
        provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(
                self.config("full", audition_evidence_path=evidence_path), provider
            )
        self.assertEqual(raised.exception.status, "BLOCKED_AUDITION_EVIDENCE")
        self.assertIn(
            "audition manifest hash mismatch", raised.exception.details["blockers"]
        )
        self.assertEqual(provider.synthesis_calls, [])

    def test_preflight_is_non_paid_and_does_not_touch_lock(self) -> None:
        provider = MockProvider()
        config = self.config("audition", execute=False)
        result = pipeline.run_pipeline(
            config, provider_factory=lambda _config: provider
        )
        self.assertEqual(result["status"], "AUDITION_PREFLIGHT_PASS")
        self.assertFalse(result["provider_calls_ran"])
        self.assertFalse(result["paid_lock_touched"])
        self.assertEqual(provider.synthesis_calls, [])
        self.assertEqual(self.lock_path.read_bytes(), self.original_lock)
        self.assertIn("--execute", result["next_exact_command"])

    def test_policy_minimums_cannot_be_lowered(self) -> None:
        provider = MockProvider()
        with self.assertRaises(pipeline.PipelineError) as raised:
            self.run_with(
                self.config("audition", minimum_listening_score=9.2), provider
            )
        self.assertEqual(raised.exception.status, "BLOCKED_CONFIG")
        self.assertEqual(provider.synthesis_calls, [])

    def test_cli_parses_mode_and_google_voice_argument(self) -> None:
        args = pipeline.parse_args(
            [
                "audition",
                "--sanitized-source",
                str(self.source_path),
                "--input-manifest",
                str(self.manifest_path),
                "--paid-lock",
                str(self.lock_path),
                "--private-output-dir",
                str(self.output_dir),
                "--voice",
                "en-US-Neural2-J",
                "--usd-per-million-chars",
                "16",
                "--run-budget-usd",
                "1",
                "--title-budget-usd",
                "5",
                "--sprint-budget-usd",
                "175",
            ]
        )
        config = pipeline.config_from_args(args)
        self.assertEqual(config.mode, "audition")
        self.assertEqual(config.voice, "en-US-Neural2-J")
        self.assertEqual(config.max_chunk_chars, 1600)


if __name__ == "__main__":
    unittest.main()
