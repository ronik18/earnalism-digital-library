#!/usr/bin/env python3
"""Focused tests for the non-provider Sprint 1 human narration packet."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_prepare_human_narration_packet.py")
SPEC = importlib.util.spec_from_file_location("human_packet", SCRIPT)
human_packet = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(human_packet)


class HumanNarrationPacketTests(unittest.TestCase):
    def fixture(self, root: Path, *, warnings=None, rights_basis="Public domain") -> Path:
        publication = root / "data/controlled_publications/the-open-window"
        chapters = publication / "chapters"
        chapters.mkdir(parents=True)
        content = "A clean controlled passage."
        (publication / "public_book.json").write_text(
            json.dumps(
                {
                    "title": "The Open Window",
                    "author": "Saki",
                    "language": "English",
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                }
            ),
            encoding="utf-8",
        )
        (publication / "source_evidence.json").write_text(
            json.dumps({"rights_basis": rights_basis, "source_hash": "source", "provenance_hash": "proof"}),
            encoding="utf-8",
        )
        (chapters / "chapter-001.json").write_text(
            json.dumps(
                {
                    "content": content,
                    "processing_status": "ready",
                    "processing_warnings": [] if warnings is None else warnings,
                    "sanitizedSha256": human_packet.sha256_text(content),
                }
            ),
            encoding="utf-8",
        )
        return publication

    def test_packet_is_source_bound_and_never_mutates_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            result = human_packet.create_packet(slug="the-open-window", asset_root=root, output_root=root / "out")
            metadata = json.loads(Path(result["metadata"]).read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "HUMAN_NARRATION_PACKET_READY")
            self.assertFalse(metadata["provider_calls_ran"])
            self.assertFalse(metadata["release_gate_mutated"])
            self.assertEqual(metadata["public_audio_status"], "AUDIO_HIDDEN_PENDING_FULL_RELEASE_GATES")
            self.assertIn("--received-audio", metadata["validate_received_audio_command"])
            self.assertTrue(Path(result["failed_tts_evidence"]).exists())
            self.assertTrue(Path(result["delivery_checklist"]).exists())
            self.assertTrue(Path(result["qa_release_checklist"]).exists())

    def test_received_audio_preflight_records_hash_without_release_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            packet = human_packet.create_packet(slug="the-open-window", asset_root=root, output_root=root / "out")
            audio = root / "received.wav"
            audio.write_bytes(b"audio")
            probe = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    {
                        "streams": [{"codec_name": "pcm_s24le", "sample_rate": "48000", "channels": 1}],
                        "format": {"duration": "390.5", "size": "5", "bit_rate": "1152000"},
                    }
                ),
                stderr="",
            )
            with mock.patch.object(human_packet.subprocess, "run", return_value=probe):
                result = human_packet.validate_received_audio(audio_path=audio, packet_dir=Path(packet["packet_dir"]))
            self.assertEqual(result["status"], "RECEIVED_AUDIO_PREFLIGHT_PASS_FULL_RELEASE_QA_REQUIRED")
            self.assertFalse(result["provider_calls_ran"])
            self.assertFalse(result["release_gate_mutated"])

    def test_unclean_chapter_blocks_packet(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root, warnings=["OCR residue"])
            with self.assertRaisesRegex(RuntimeError, "not clean and ready"):
                human_packet.create_packet(slug="the-open-window", asset_root=root, output_root=root / "out")

    def test_missing_rights_blocks_packet(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root, rights_basis="")
            with self.assertRaisesRegex(RuntimeError, "rights evidence is incomplete"):
                human_packet.create_packet(slug="the-open-window", asset_root=root, output_root=root / "out")


if __name__ == "__main__":
    unittest.main()
