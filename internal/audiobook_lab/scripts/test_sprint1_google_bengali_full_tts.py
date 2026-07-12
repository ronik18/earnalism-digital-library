#!/usr/bin/env python3
"""Focused safety tests for the private Google Bengali full-TTS wrapper."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import fcntl
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_google_bengali_full_tts.py")
SPEC = importlib.util.spec_from_file_location("sprint1_google_bengali_full_tts", SCRIPT)
google_full = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = google_full
SPEC.loader.exec_module(google_full)


SLUG = "book-test-bengali"
VOICE = "bn-IN-Wavenet-C"
MANUSCRIPT = (
    "আজ নদীর ধারে ছোট্ট ছেলেটি দাঁড়িয়ে ছিল। বাতাসে কাশফুল দুলছিল। "
    "সে ধীরে ধীরে বাড়ির পথে ফিরে গেল। আকাশে তখন সন্ধ্যার আলো।\n"
)


class FakeGoogle:
    def __init__(self, *, fail_on_chunk: int | None = None) -> None:
        self.fail_on_chunk = fail_on_chunk
        self.voice_queries: list[str] = []
        self.texts: list[str] = []

    def available_voice_names(self, language_code: str) -> set[str]:
        self.voice_queries.append(language_code)
        return {VOICE}

    def synthesize(self, *, text: str, voice: str, language_code: str) -> bytes:
        index = len(self.texts)
        self.texts.append(text)
        if self.fail_on_chunk == index:
            raise RuntimeError("mock Google synthesis failure")
        return f"mock-mp3-{index}:{text}".encode("utf-8")


def fake_concat(paths: list[Path], target: Path) -> dict:
    target.write_bytes(b"".join(path.read_bytes() for path in paths))
    return {"ok": True}


class GoogleBengaliFullTTSTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.private_root = self.root / "internal/audiobook_lab"
        self.input_dir = self.private_root / "inputs"
        self.input_dir.mkdir(parents=True)
        self.manuscript = self.input_dir / "clean_manuscript.txt"
        self.manuscript.write_text(MANUSCRIPT, encoding="utf-8")
        self.evidence = self.input_dir / "representative_evidence.json"
        self.evidence.write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "slug": SLUG,
                    "provider": "google",
                    "model": google_full.MODEL,
                    "voice": VOICE,
                    "best_style_profile": google_full.STYLE_PROFILE,
                    "representative_score": 9.4,
                    "confidence": 0.95,
                    "fatal_flags": {name: False for name in google_full.FATAL_FLAGS},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.lock = self.root / "internal/earnalism_intelligence/locks/paid_tts.lock"
        self.lock.parent.mkdir(parents=True)
        self.lock_bytes = (
            b'{\n  "status": "active",\n  "current_holder": "none",\n'
            b'  "allowed_next_holders": [],\n  "sentinel": "exact bytes"\n}\n'
        )
        self.lock.write_bytes(self.lock_bytes)
        self.run_dir = self.private_root / "runs" / "google-full"

    def env(self) -> dict[str, str]:
        return {
            "EARNALISM_APPROVE_GOOGLE_FULL_TTS": "true",
            "EARNALISM_APPROVE_BENGALI_FULL_PILOT_TTS": "true",
            "EARNALISM_APPROVE_BENGALI_31_AUDIO_CAMPAIGN": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "EARNALISM_BENGALI_TTS_PROVIDER": "google",
            "EARNALISM_BENGALI_FULL_PILOT_SLUG": SLUG,
            "EARNALISM_BENGALI_TTS_VOICE": VOICE,
            "EARNALISM_GOOGLE_TTS_ESTIMATED_USD_PER_1K_CHARS": "0.02",
            "EARNALISM_GOOGLE_TTS_FULL_MAX_ESTIMATED_USD": "1",
            "EARNALISM_BENGALI_MAX_ESTIMATED_USD_PER_TITLE": "8",
            "EARNALISM_BENGALI_CAMPAIGN_MAX_ESTIMATED_USD": "75",
            "SPRINT1_MAX_USD_PER_TITLE": "30",
            "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "175",
            "MAX_TTS_BUDGET_USD": "175",
            "GOOGLE_APPLICATION_CREDENTIALS": "/private/mock-google.json",
            "GOOGLE_CLOUD_PROJECT": "mock-project",
        }

    def config(self, *, run_dir: Path | None = None, max_chars: int = 45) -> google_full.RunConfig:
        return google_full.RunConfig(
            asset_root=self.root,
            slug=SLUG,
            voice=VOICE,
            manuscript_path=self.manuscript,
            run_dir=run_dir or self.run_dir,
            representative_evidence_path=self.evidence,
            expected_manuscript_sha256=google_full.sha256_text(MANUSCRIPT),
            prior_title_estimated_spend_usd=0.4,
            prior_sprint_estimated_spend_usd=4.0,
            lock_path=self.lock,
            max_chars=max_chars,
        )

    def test_missing_gate_fails_closed_without_constructing_google(self) -> None:
        env = self.env()
        env.pop("EARNALISM_APPROVE_GOOGLE_FULL_TTS")
        constructions = 0

        def provider_factory() -> FakeGoogle:
            nonlocal constructions
            constructions += 1
            return FakeGoogle()

        result = google_full.run(self.config(), execute=True, environ=env, provider_factory=provider_factory)

        self.assertEqual(result["status"], "BLOCKED_PREFLIGHT")
        self.assertFalse(result["provider_calls_ran"])
        self.assertEqual(constructions, 0)
        self.assertEqual(self.lock.read_bytes(), self.lock_bytes)
        self.assertFalse(self.run_dir.exists())

    def test_title_and_sprint_budgets_block_before_any_google_call(self) -> None:
        constructions = 0

        def provider_factory() -> FakeGoogle:
            nonlocal constructions
            constructions += 1
            return FakeGoogle()

        cases = (
            ("SPRINT1_MAX_USD_PER_TITLE", "0.4001", "estimated title spend"),
            ("SPRINT1_TOTAL_AUDIO_BUDGET_USD", "4.0001", "estimated sprint spend"),
        )
        for name, cap, blocker in cases:
            with self.subTest(name=name):
                env = self.env()
                env[name] = cap
                result = google_full.run(
                    self.config(),
                    execute=True,
                    environ=env,
                    provider_factory=provider_factory,
                )
                self.assertEqual(result["status"], "BLOCKED_PREFLIGHT")
                self.assertTrue(any(item.startswith(blocker) for item in result["blockers"]))
        self.assertEqual(constructions, 0)
        self.assertEqual(self.lock.read_bytes(), self.lock_bytes)

    def test_non_finite_representative_score_fails_closed(self) -> None:
        evidence = json.loads(self.evidence.read_text(encoding="utf-8"))
        evidence["representative_score"] = "NaN"
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        constructions = 0

        def provider_factory() -> FakeGoogle:
            nonlocal constructions
            constructions += 1
            return FakeGoogle()

        result = google_full.run(
            self.config(),
            execute=True,
            environ=self.env(),
            provider_factory=provider_factory,
        )

        self.assertEqual(result["status"], "BLOCKED_PREFLIGHT")
        self.assertIn("representative listening score must be at least 9.2", result["blockers"])
        self.assertEqual(constructions, 0)

    def test_malformed_lock_fails_closed_without_constructing_google(self) -> None:
        self.lock.write_bytes(b"not-json")
        constructions = 0

        def provider_factory() -> FakeGoogle:
            nonlocal constructions
            constructions += 1
            return FakeGoogle()

        result = google_full.run(
            self.config(),
            execute=True,
            environ=self.env(),
            provider_factory=provider_factory,
        )

        self.assertEqual(result["status"], "BLOCKED_PREFLIGHT")
        self.assertTrue(any("lock is unreadable or invalid" in item for item in result["blockers"]))
        self.assertEqual(constructions, 0)

    def test_lock_bytes_restore_after_mock_google_failure(self) -> None:
        provider = FakeGoogle(fail_on_chunk=1)
        result = google_full.run(
            self.config(),
            execute=True,
            environ=self.env(),
            provider_factory=lambda: provider,
            concat_fn=fake_concat,
        )

        self.assertEqual(result["status"], "FULL_TTS_BLOCKED")
        self.assertTrue(result["provider_calls_ran"])
        self.assertTrue(result["lock_restored"])
        self.assertEqual(self.lock.read_bytes(), self.lock_bytes)
        self.assertIn("mock Google synthesis failure", result["errors"][0])

    def test_busy_lock_blocks_before_constructing_google(self) -> None:
        constructions = 0

        def provider_factory() -> FakeGoogle:
            nonlocal constructions
            constructions += 1
            return FakeGoogle()

        with self.lock.open("r+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                result = google_full.run(
                    self.config(),
                    execute=True,
                    environ=self.env(),
                    provider_factory=provider_factory,
                )
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        self.assertEqual(result["status"], "FULL_TTS_BLOCKED")
        self.assertFalse(result["provider_calls_ran"])
        self.assertIn("held by another process", result["errors"][0])
        self.assertEqual(constructions, 0)
        self.assertEqual(self.lock.read_bytes(), self.lock_bytes)

    def test_chunks_are_ordered_and_manifests_are_deterministic(self) -> None:
        first_provider = FakeGoogle()
        first = google_full.run(
            self.config(),
            execute=True,
            environ=self.env(),
            provider_factory=lambda: first_provider,
            concat_fn=fake_concat,
        )
        self.assertEqual(first["status"], "PRIVATE_FULL_TTS_PASS_QA_REQUIRED")
        expected_chunks = google_full.chunk_text(MANUSCRIPT, max_chars=45)
        expected_tts_texts = [google_full.google_safe_tts_text(chunk["text"]) for chunk in expected_chunks]
        self.assertEqual(first_provider.texts, expected_tts_texts)
        manifest_path = self.run_dir / google_full.MANIFEST_NAME
        first_manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(first_manifest_bytes)
        self.assertEqual([chunk["index"] for chunk in manifest["chunks"]], list(range(len(expected_chunks))))
        self.assertEqual(
            [chunk["text_sha256"] for chunk in manifest["chunks"]],
            [chunk["text_hash"] for chunk in expected_chunks],
        )
        self.assertEqual(manifest["source"]["sha256"], google_full.sha256_text(MANUSCRIPT))
        self.assertFalse(manifest["public_audio_approved"])
        self.assertFalse(manifest["upload_performed"])
        self.assertFalse(manifest["release_gate_mutated"])
        recorded_hash = (self.run_dir / google_full.MANIFEST_HASH_NAME).read_text().split()[0]
        self.assertEqual(recorded_hash, hashlib.sha256(first_manifest_bytes).hexdigest())

        second_run_dir = self.private_root / "runs" / "google-full-second"
        second_provider = FakeGoogle()
        second = google_full.run(
            self.config(run_dir=second_run_dir),
            execute=True,
            environ=self.env(),
            provider_factory=lambda: second_provider,
            concat_fn=fake_concat,
        )
        self.assertEqual(second["status"], "PRIVATE_FULL_TTS_PASS_QA_REQUIRED")
        self.assertEqual(first_manifest_bytes, (second_run_dir / google_full.MANIFEST_NAME).read_bytes())
        self.assertEqual(self.lock.read_bytes(), self.lock_bytes)

    def test_public_run_dir_is_rejected_without_public_write(self) -> None:
        public_dir = self.root / "frontend/public/audio"
        marker = public_dir.parent / "keep.txt"
        marker.parent.mkdir(parents=True)
        marker.write_text("unchanged", encoding="utf-8")
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.glob("frontend/public/**/*")
            if path.is_file()
        }
        constructions = 0

        def provider_factory() -> FakeGoogle:
            nonlocal constructions
            constructions += 1
            return FakeGoogle()

        result = google_full.run(
            self.config(run_dir=public_dir),
            execute=True,
            environ=self.env(),
            provider_factory=provider_factory,
            concat_fn=fake_concat,
        )
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.glob("frontend/public/**/*")
            if path.is_file()
        }

        self.assertEqual(result["status"], "BLOCKED_PREFLIGHT")
        self.assertIn("repo-local run directory must be below internal/audiobook_lab", result["blockers"])
        self.assertEqual(constructions, 0)
        self.assertEqual(before, after)
        self.assertFalse(public_dir.exists())

    def test_successful_private_run_does_not_touch_public_tree(self) -> None:
        marker = self.root / "frontend/public/existing.txt"
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b"public-sentinel")
        before = marker.read_bytes()

        result = google_full.run(
            self.config(),
            execute=True,
            environ=self.env(),
            provider_factory=FakeGoogle,
            concat_fn=fake_concat,
        )

        self.assertEqual(result["status"], "PRIVATE_FULL_TTS_PASS_QA_REQUIRED")
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(list(marker.parent.iterdir()), [marker])


if __name__ == "__main__":
    unittest.main()
