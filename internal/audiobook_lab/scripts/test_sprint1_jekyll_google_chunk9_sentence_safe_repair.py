#!/usr/bin/env python3
"""Focused tests for the Jekyll chunk_0009 context synthesis executor."""

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

import sprint1_jekyll_google_chunk9_sentence_safe_repair as repair


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FakeProvider:
    def __init__(self, audio: bytes = b"ID3-context-audio") -> None:
        self.audio = audio
        self.calls: list[dict[str, object]] = []

    def ensure_voice(self, **kwargs: object) -> None:
        self.calls.append({"ensure_voice": kwargs})

    def synthesize(self, **kwargs: object) -> bytes:
        self.calls.append(dict(kwargs))
        return self.audio


class JekyllChunk9ContextRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.context = (
            "without further delay and free from any burthen or obligation "
            "beyond the payment of a few small sums to the members of the "
            "doctor’s household. This document had long been the lawyer’s eyesore."
        )
        self.assertEqual(sha256_text(self.context), repair.EXPECTED_CONTEXT_SHA256)
        self.preflight = self.root / "chunk9_repair_preflight.json"
        self.preflight.write_text(
            json.dumps(
                {
                    "schema_version": "earnalism.jekyll_chunk9_sentence_safe_repair_preflight_evidence.v1",
                    "status": "PREFLIGHT_PASS_NO_PROVIDER_CALL_AUDIO_HIDDEN",
                    "slug": repair.SLUG,
                    "title": "The Strange Case of Dr. Jekyll and Mr. Hyde",
                    "author": "Robert Louis Stevenson",
                    "preflight_binding_sha256": "a" * 64,
                    "parent_candidate": {
                        "parent_full_manifest_sha256": "b" * 64,
                    },
                    "target": {
                        "unit_id": repair.TARGET_UNIT_ID,
                        "source_text_sha256": "c" * 64,
                        "prior_audio_sha256": "d" * 64,
                        "synthesis_context": self.context,
                    },
                    "provider_plan": {
                        "provider": "google",
                        "voice": "en-GB-Chirp3-HD-Charon",
                        "language_code": "en-GB",
                        "speaking_rate": 0.94,
                        "pitch": 0.0,
                        "synthesis_context": self.context,
                        "synthesis_context_sha256": repair.EXPECTED_CONTEXT_SHA256,
                    },
                    "budget": {
                        "estimated_run_usd": 0.00576,
                        "run_budget_usd": 0.10,
                    },
                    "provider_calls_ran": False,
                    "audio_generated": False,
                    "upload_performed": False,
                    "publication_performed": False,
                    "release_mutation_performed": False,
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        self.lock = self.root / "paid_tts.lock"
        self.lock.write_text(
            json.dumps(
                {
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                    "allowed_slugs": [repair.SLUG],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_preflight_mode_makes_no_provider_or_lock_change(self) -> None:
        original_lock = self.lock.read_bytes()

        result = repair.run(
            preflight_path=self.preflight,
            paid_lock=self.lock,
            private_output_dir=self.root / "private",
        )

        self.assertEqual(result["status"], "PREFLIGHT_PASS_PRIVATE_CONTEXT_ONLY")
        self.assertFalse(result["provider_calls_ran"])
        self.assertFalse(result["audio_generated"])
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["release_mutation_performed"])
        self.assertEqual(self.lock.read_bytes(), original_lock)

    def test_execute_requires_runtime_gates_before_provider(self) -> None:
        provider = FakeProvider()
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(repair.Chunk9RepairError, "approval"):
                repair.run(
                    preflight_path=self.preflight,
                    paid_lock=self.lock,
                    private_output_dir=self.root / "private",
                    execute=True,
                    provider_factory=lambda _config: provider,
                )
        self.assertEqual(provider.calls, [])

    def test_execute_calls_provider_once_and_restores_lock(self) -> None:
        original_lock = self.lock.read_bytes()
        provider = FakeProvider()

        with mock.patch.dict(
            os.environ,
            {
                repair.APPROVAL_ENV: "true",
                repair.STOP_ON_BUDGET_ENV: "true",
                "GOOGLE_CLOUD_PROJECT": "earnalism",
            },
            clear=False,
        ):
            result = repair.run(
                preflight_path=self.preflight,
                paid_lock=self.lock,
                private_output_dir=self.root / "private",
                execute=True,
                provider_factory=lambda _config: provider,
            )

        synth_calls = [call for call in provider.calls if "text" in call]
        self.assertEqual(len(synth_calls), 1)
        self.assertEqual(synth_calls[0]["text"], self.context)
        self.assertEqual(synth_calls[0]["voice"], "en-GB-Chirp3-HD-Charon")
        self.assertEqual(synth_calls[0]["speaking_rate"], 0.94)
        self.assertEqual(result["status"], "CONTEXT_AUDIO_PRIVATE_QA_PENDING_ALIGNMENT_AND_SPLICE")
        self.assertTrue(result["provider_calls_ran"])
        self.assertTrue(result["audio_generated"])
        self.assertFalse(result["splice_performed"])
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["release_mutation_performed"])
        self.assertEqual(self.lock.read_bytes(), original_lock)
        self.assertTrue(Path(result["context_audio_path"]).is_file())
        self.assertTrue(Path(result["evidence_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
