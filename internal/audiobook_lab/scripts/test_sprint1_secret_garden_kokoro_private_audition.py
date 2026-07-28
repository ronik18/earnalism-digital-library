#!/usr/bin/env python3
"""Focused tests for The Secret Garden's private Kokoro pilot."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name(
    "sprint1_secret_garden_kokoro_private_audition.py"
)
SPEC = importlib.util.spec_from_file_location("secret_garden_private_audition", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.BASE.ROOT


class SecretGardenPrivateAuditionTests(unittest.TestCase):
    def test_exact_catalog_source_and_four_risk_passages(self) -> None:
        source_path, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        self.assertEqual(source_path.name, "chapters")
        self.assertEqual(
            [item["passage_id"] for item in passages],
            [
                "opening_india_character",
                "garden_key_discovery",
                "colin_midnight_dialogue",
                "healing_finale",
            ],
        )
        self.assertEqual(
            [item["chapter_id"] for item in passages],
            ["chapter-001", "chapter-007", "chapter-013", "chapter-027"],
        )
        self.assertEqual(sum(item["characters"] for item in passages), 2_097)
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )

    def test_profile_uses_hash_pinned_british_voice_and_g2p(self) -> None:
        self.assertEqual(MODULE.VOICE, "bf_emma")
        self.assertEqual(MODULE.PIPELINE_LANG_CODE, "b")
        self.assertTrue(MODULE.G2P_BRITISH)
        voice = MODULE.DEFAULT_ARTIFACT_DIR / "voices/bf_emma.pt"
        self.assertTrue(voice.is_file())
        self.assertEqual(MODULE.BASE.sha256_file(voice), MODULE.VOICE_SHA256)

    def test_fingerprint_binds_british_g2p_and_is_closed_in_history(self) -> None:
        _source, passages = MODULE.controlled_source(REPO, MODULE.SLUG)
        fingerprint = MODULE.BASE.attempt_fingerprint(passages)
        self.assertEqual(len(fingerprint), 64)
        self.assertTrue(
            any(
                path.is_file()
                and fingerprint in path.read_text(encoding="utf-8")
                for path in MODULE.BASE.NO_REPEAT_FILES
            )
        )

    def test_wrong_slug_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            MODULE.BASE.KokoroTitlePilotError, "only the-secret-garden"
        ):
            MODULE.controlled_source(REPO, "dracula")

    def test_missing_cover_fails_before_audio(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "public_book.json":
                value = copy.deepcopy(value)
                value["cover_url"] = ""
            return value

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError, "cover_url"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_audio_enabled_catalog_mutation_fails_closed(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "public_book.json":
                value = copy.deepcopy(value)
                value["audiobook_enabled"] = True
            return value

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError, "audiobook_enabled"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_chapter_hash_tamper_fails_closed(self) -> None:
        original = MODULE.BASE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "chapter-013.json":
                value = copy.deepcopy(value)
                value["content"] += " tampered"
            return value

        with mock.patch.object(MODULE.BASE, "read_json", side_effect=changed):
            with self.assertRaisesRegex(
                MODULE.BASE.KokoroTitlePilotError, "chapter hash changed"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_preflight_is_private_zero_cost_and_cannot_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "paid_tts.lock"
            lock.write_text(
                json.dumps(
                    {
                        "status": "active",
                        "current_holder": "none",
                        "allowed_next_holders": [],
                    }
                ),
                encoding="utf-8",
            )
            fake_paths = {
                "model": root / "model",
                "config": root / "config",
                "voice": root / "voice",
                "whisper": root / "whisper",
            }
            fake_evidence = {
                name: {"path": str(path), "sha256": name}
                for name, path in fake_paths.items()
            }
            with mock.patch.object(
                MODULE.BASE,
                "validate_artifacts",
                return_value=(fake_paths, fake_evidence),
            ), mock.patch.object(
                MODULE.BASE, "runtime_evidence", return_value={"pinned": True}
            ), mock.patch.object(MODULE.BASE, "NO_REPEAT_FILES", ()):
                payload, _passages, _artifacts = MODULE.secret_garden_preflight(
                    asset_root=REPO,
                    slug=MODULE.SLUG,
                    profile=MODULE.PROFILE,
                    artifact_dir=root,
                    whisper_cache_dir=root,
                    private_output_dir=root / "private-audio",
                    output=root / "evidence.json",
                    paid_lock=lock,
                )
        self.assertEqual(
            payload["status"], "READY_FOR_PRIVATE_REPRESENTATIVE_EXECUTION"
        )
        self.assertEqual(payload["policy"]["overall_listening_min"], 8.9)
        self.assertEqual(payload["engine"]["pipeline_lang_code"], "b")
        self.assertTrue(payload["engine"]["g2p_british"])
        self.assertEqual(payload["safety"]["provider_calls"], 0)
        self.assertEqual(payload["safety"]["estimated_tts_provider_cost_usd"], 0.0)
        self.assertFalse(payload["safety"]["audio_generated"])
        self.assertFalse(payload["safety"]["upload_performed"])
        self.assertFalse(payload["safety"]["publication_performed"])
        self.assertFalse(payload["safety"]["release_gate_mutated"])
        self.assertFalse(payload["scope"]["full_title_generated"])
        self.assertFalse(payload["next_stage_contract"]["publication_allowed"])
        self.assertTrue(
            payload["policy"][
                "representative_pass_cannot_approve_public_release"
            ]
        )


if __name__ == "__main__":
    unittest.main()
