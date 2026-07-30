#!/usr/bin/env python3
"""Provider-free tests for Ginni's Indic Parler/Aditi preflight packet."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_d19_indic_parler_private_preflight.py")
SPEC = importlib.util.spec_from_file_location("d19_indic_parler_preflight", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REPO = MODULE.ROOT


class D19IndicParlerPrivatePreflightTests(unittest.TestCase):
    def test_exact_catalog_source_mirrors_covers_and_passages(self) -> None:
        chapter, manuscript, passages, covers = MODULE.controlled_source(
            REPO, MODULE.SLUG
        )
        self.assertEqual(chapter.name, "chapter-001.json")
        self.assertEqual(len(manuscript), MODULE.RAW_SOURCE_CHARACTERS)
        self.assertEqual(MODULE.sha256_text(manuscript), MODULE.RAW_SOURCE_SHA256)
        self.assertEqual(
            [item["passage_id"] for item in passages],
            [
                "opening_character_control",
                "satirical_punctuation",
                "play_scene_dialogue",
                "ending_emotional_release",
            ],
        )
        self.assertEqual(
            sum(item["characters"] for item in passages),
            MODULE.PASSAGE_CHARACTERS,
        )
        self.assertEqual(
            [item["text_sha256"] for item in passages],
            [item["sha256"] for item in MODULE.PASSAGE_SPECS],
        )
        self.assertTrue(covers["front_cover_url"].startswith("https://"))
        self.assertTrue(covers["back_cover_url"].startswith("https://"))

    def test_fingerprint_is_deterministic_and_now_consumed(self) -> None:
        _chapter, _manuscript, passages, _covers = MODULE.controlled_source(
            REPO, MODULE.SLUG
        )
        fingerprint = MODULE.attempt_fingerprint(passages)
        self.assertEqual(fingerprint, MODULE.attempt_fingerprint(passages))
        self.assertEqual(len(fingerprint), 64)
        with self.assertRaisesRegex(
            MODULE.D19IndicParlerPreflightError, "already consumed"
        ):
            MODULE.ensure_not_repeated(fingerprint, Path("/tmp/nonexistent-d19.json"))

    def test_catalog_audio_enablement_fails_closed(self) -> None:
        original = MODULE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "public_book.json":
                value = copy.deepcopy(value)
                value["audiobook_enabled"] = True
            return value

        with mock.patch.object(MODULE, "_assert_mirrors"), mock.patch.object(
            MODULE, "read_json", side_effect=changed
        ):
            with self.assertRaisesRegex(
                MODULE.D19IndicParlerPreflightError, "audiobook_enabled"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_audio_release_approval_change_fails_closed(self) -> None:
        original = MODULE.read_json

        def changed(path: Path):
            value = original(path)
            if path.name == "approval_evidence.json":
                value = copy.deepcopy(value)
                value["audio_public_release"] = "APPROVED"
            return value

        with mock.patch.object(MODULE, "_assert_mirrors"), mock.patch.object(
            MODULE, "read_json", side_effect=changed
        ):
            with self.assertRaisesRegex(
                MODULE.D19IndicParlerPreflightError, "audio_public_release"
            ):
                MODULE.controlled_source(REPO, MODULE.SLUG)

    def test_wrong_slug_and_public_output_are_refused(self) -> None:
        with self.assertRaisesRegex(
            MODULE.D19IndicParlerPreflightError, "only book-d19e96859f"
        ):
            MODULE.controlled_source(REPO, "radharani")
        with self.assertRaisesRegex(
            MODULE.D19IndicParlerPreflightError, "public audio path"
        ):
            MODULE.assert_private_path(REPO / "frontend/public/audio/d19")

    def test_preflight_is_provider_free_audio_hidden_and_lock_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            MODULE, "NO_REPEAT_FILES", ()
        ):
            payload = MODULE.build_preflight(
                asset_root=REPO,
                slug=MODULE.SLUG,
                profile=MODULE.PROFILE,
                private_output_dir=Path(tmp) / "private",
                output=Path(tmp) / "evidence.json",
            )
        self.assertEqual(payload["status"], "PACKET_READY_EXECUTION_BLOCKED")
        self.assertEqual(payload["go_no_go"], "NO_GO_AUDIO_EXECUTION")
        self.assertEqual(payload["engine"]["model_repo"], MODULE.MODEL_REPO)
        self.assertEqual(payload["engine"]["voice"], "Aditi")
        self.assertIs(
            payload["selection"]["new_model_voice_has_no_recorded_execution_result"],
            True,
        )
        self.assertIs(payload["safety"]["paid_tts_lock_inspected"], False)
        self.assertIs(payload["safety"]["paid_tts_lock_touched"], False)
        self.assertIs(payload["safety"]["audio_generated"], False)
        self.assertIs(payload["safety"]["upload_performed"], False)
        self.assertIs(payload["safety"]["publication_performed"], False)
        self.assertIs(payload["safety"]["release_gate_mutated"], False)
        self.assertEqual(
            payload["safety"]["public_audio_status"], "AUDIO_HIDDEN_NOT_PUBLIC"
        )
        self.assertEqual(
            payload["rights"]["model_license_status"],
            "VERIFIED_OFFICIAL_MODEL_CARD_APACHE_2_0",
        )
        self.assertIs(
            payload["rights"]["commercial_use_allowed_under_recorded_license"],
            True,
        )
        self.assertIs(
            payload["rights"][
                "repository_access_acknowledgement_is_commercial_rights_gate"
            ],
            False,
        )
        self.assertNotIn(
            "MODEL_ACCESS_TERMS_ACCEPTANCE_MUST_BE_RECORDED_BEFORE_EXECUTION",
            payload["blockers_to_execution_and_release"],
        )
        self.assertIn(
            "HF_REPOSITORY_ACCESS_ACKNOWLEDGEMENT_RECEIPT_NOT_RECORDED",
            payload["non_blocking_provenance_notes"],
        )

    def test_committed_packet_matches_current_source_and_fingerprint(self) -> None:
        packet = MODULE.read_json(
            REPO / "internal/audiobook_lab/sprint1_publication/title_runs/"
            "book-d19e96859f_indic_parler_aditi_private_preflight_v1.json"
        )
        _chapter, _manuscript, passages, _covers = MODULE.controlled_source(
            REPO, MODULE.SLUG
        )
        self.assertEqual(
            packet["source"]["raw_source_sha256"], MODULE.RAW_SOURCE_SHA256
        )
        self.assertEqual(
            packet["engine"]["attempt_fingerprint"],
            MODULE.attempt_fingerprint(passages),
        )
        self.assertEqual(
            [item["text_sha256"] for item in packet["source"]["passages"]],
            [item["text_sha256"] for item in passages],
        )
        self.assertIs(packet["safety"]["audio_generated"], False)
        self.assertIs(packet["safety"]["release_gate_mutated"], False)
        self.assertEqual(
            packet["rights"]["commercial_rights_decision"],
            "ALLOWED_BY_APACHE_2_0_MODEL_LICENSE",
        )
        self.assertIs(
            packet["rights"][
                "repository_access_acknowledgement_is_commercial_rights_gate"
            ],
            False,
        )
        self.assertEqual(
            packet["safety"]["public_audio_status"], "AUDIO_HIDDEN_NOT_PUBLIC"
        )

    def test_runtime_verification_requires_pinned_snapshot(self) -> None:
        with self.assertRaisesRegex(
            MODULE.D19IndicParlerPreflightError,
            "--verify-runtime requires --model-snapshot-dir",
        ):
            MODULE.runtime_evidence(None, True)

    def test_cli_refuses_execution_mode(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--execute"],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments: --execute", result.stderr)

    def test_no_repeat_guard_rejects_persisted_fingerprint(self) -> None:
        _chapter, _manuscript, passages, _covers = MODULE.controlled_source(
            REPO, MODULE.SLUG
        )
        fingerprint = MODULE.attempt_fingerprint(passages)
        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp) / "memory.json"
            memory.write_text(
                json.dumps(
                    {
                        "attempt_fingerprint": fingerprint,
                        "audio_generated": True,
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(MODULE, "NO_REPEAT_FILES", (memory,)):
                with self.assertRaisesRegex(
                    MODULE.D19IndicParlerPreflightError, "already consumed"
                ):
                    MODULE.ensure_not_repeated(fingerprint, Path(tmp) / "output.json")


if __name__ == "__main__":
    unittest.main()
