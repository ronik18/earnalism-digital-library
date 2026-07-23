"""Focused tests for the generic narration/import packet generator."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("build_narration_import_packet.py")
SPEC = importlib.util.spec_from_file_location("narration_import_packet", SCRIPT)
packet = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(packet)


class NarrationImportPacketTests(unittest.TestCase):
    def fixture(
        self,
        root: Path,
        *,
        slug: str = "sample-book",
        language_hint: str = "en",
        title: str = "Sample Book",
        author: str = "Example Author",
        content: str = "A clean opening.\n\nA clean ending.",
        rights_basis: str = "Commercial audiobook use is cleared.",
        recorded_hash: str | None = None,
    ) -> Path:
        publication = root / "data/controlled_publications" / slug
        chapters = publication / "chapters"
        chapters.mkdir(parents=True)
        source_hash = packet.sha256_text(content.strip())
        (publication / "public_book.json").write_text(
            json.dumps(
                {
                    "slug": slug,
                    "title": title,
                    "author": author,
                    "chapters": [{"language_hint": language_hint}],
                    "source_hash": source_hash,
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (publication / "source_evidence.json").write_text(
            json.dumps(
                {
                    "rights_basis": rights_basis,
                    "source_hash": source_hash,
                    "provenance_hash": "provenance-proof",
                }
            ),
            encoding="utf-8",
        )
        (chapters / "chapter-001.json").write_text(
            json.dumps(
                {
                    "title": "Full Text",
                    "content": content,
                    "processing_status": "ready",
                    "processing_warnings": [],
                    "sanitizedSha256": recorded_hash or packet.sha256_text(content.strip()),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return publication

    def test_bengali_packet_is_sanitized_source_bound_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            slug = "bangla-sample"
            title = "রামকানাইয়ের নির্বুদ্ধিতা"
            author = "রবীন্দ্রনাথ ঠাকুর"
            content = (
                f"{author}\n\nগল্পগুচ্ছ\n\n১৯৫০ (পৃ. ৪০-৪৫)\n\n{title}\n\n"
                "যাহারা বলে, তাহারা ভুল করে।\n\nশেষ কথা এখানে।\n\n১২৯৮?"
            )
            self.fixture(
                root,
                slug=slug,
                language_hint="ben",
                title=title,
                author=author,
                content=content,
            )
            title_runs = root / "internal/audiobook_lab/sprint1_publication/title_runs"
            audition = title_runs / "bangla-audition"
            audition.mkdir(parents=True)
            (title_runs / f"{slug}_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": slug,
                        "release_gate_state": "INCOMPLETE_FAIL_CLOSED",
                        "quality_score": "7.8 representative",
                        "exact_blocker": "LISTENING_GATE_FAILED",
                    }
                ),
                encoding="utf-8",
            )
            (audition / "bengali_representative_audition_report.json").write_text(
                json.dumps(
                    {
                        "status": "BLOCKED",
                        "provider": "example-provider",
                        "model": "example-model",
                        "voice": "example-voice",
                        "representative_score": 7.8,
                        "confidence": 0.85,
                        "passage_scores": [
                            {
                                "passage_slug": slug,
                                "overall_listening_score": 7.8,
                                "red_flags": {"mechanical_cadence_detected": True},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            output = root / "packets"
            with mock.patch.object(packet.subprocess, "run") as run:
                first = packet.create_packet(slug=slug, asset_root=root, output_root=output)
            run.assert_not_called()
            packet_dir = Path(first["packet_dir"])
            first_bytes = {path.name: path.read_bytes() for path in sorted(packet_dir.iterdir())}
            second = packet.create_packet(slug=slug, asset_root=root, output_root=output)
            second_bytes = {path.name: path.read_bytes() for path in sorted(packet_dir.iterdir())}

            self.assertEqual(first["packet_fingerprint_sha256"], second["packet_fingerprint_sha256"])
            self.assertEqual(first_bytes, second_bytes)
            manuscript = (packet_dir / "clean_manuscript.txt").read_text(encoding="utf-8")
            self.assertEqual(manuscript, "যাহারা বলে, তাহারা ভুল করে।\n\nশেষ কথা এখানে।\n")
            metadata = json.loads((packet_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["language"], {"code": "ben", "name": "Bengali"})
            self.assertEqual(metadata["release_requirements"]["listening_score_min"], 9.2)
            self.assertEqual(metadata["source_binding"]["status"], "VERIFIED_SOURCE_AND_CHAPTER_HASHES")
            self.assertEqual(len(metadata["prior_provider_evidence"]["failed_attempts"]), 1)
            self.assertFalse(metadata["safety"]["provider_calls_ran"])
            self.assertNotIn(str(root), metadata["exact_received_audio_validation_command"])
            brief = (packet_dir / "narrator_brief.md").read_text(encoding="utf-8")
            self.assertIn("archaic সাধু form", brief)

    def test_punctuated_bengali_title_page_is_removed_with_leading_metadata(self):
        content = (
            "রবীন্দ্রনাথ ঠাকুর\n\n"
            "গল্প-দশক\n\n"
            "১৮৯৫ (পৃ. ১৬৫-১৮৮)\n\n"
            "ক্ষুধিত পাষাণ।\n\n"
            "গাড়িটি আসিয়া জংশনে থামিলে আমরা অপেক্ষা করিলাম।"
        )
        cleaned, removed = packet.sanitize_chapter(content, title="ক্ষুধিত পাষাণ")
        self.assertEqual(cleaned, "গাড়িটি আসিয়া জংশনে থামিলে আমরা অপেক্ষা করিলাম।")
        self.assertEqual(removed[0]["reason"], "frontmatter_through_exact_title")

    def test_english_licensed_import_uses_evidence_threshold_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            slug = "english-sample"
            self.fixture(
                root,
                slug=slug,
                title="English Sample",
                author="Example Author",
                content="Framton met Nuttel.\n\nFramton answered Nuttel.",
            )
            title_runs = root / "internal/audiobook_lab/sprint1_publication/title_runs"
            title_runs.mkdir(parents=True)
            attempt_path = title_runs / "english-sample-final.json"
            attempt_path.write_text(
                json.dumps(
                    {
                        "slug": slug,
                        "status": "AUDITION_REPAIR_REQUIRED",
                        "attempt_fingerprint": "failed-fingerprint",
                        "blockers": ["twilight: overall score below owner minimum 9.4"],
                    }
                ),
                encoding="utf-8",
            )
            (title_runs / f"{slug}_release_gate_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": slug,
                        "classification": "ALTERNATE_PATH_REQUIRED",
                        "stage2e_studio_b_final_audition": {
                            "status": "AUDITION_REPAIR_REQUIRED",
                            "provider": "google",
                            "voice": "en-GB-Studio-B",
                            "scores": [9.4, 7.2],
                            "minimum_confidence": 0.9,
                            "fatal_flags": ["robotic_texture_detected"],
                            "evidence": packet.portable_path(attempt_path, root),
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = packet.create_packet(
                slug=slug,
                asset_root=root,
                output_root=root / "packets",
                candidate_kind="licensed_audio_import",
            )
            packet_dir = Path(result["packet_dir"])
            metadata = json.loads((packet_dir / "metadata.json").read_text(encoding="utf-8"))
            attempt = metadata["prior_provider_evidence"]["failed_attempts"][0]
            self.assertEqual(metadata["release_requirements"]["listening_score_min"], 9.4)
            self.assertEqual(attempt["attempt_fingerprint"], "failed-fingerprint")
            self.assertEqual(attempt["voice"], "en-GB-Studio-B")
            delivery = (packet_dir / "delivery_checklist.md").read_text(encoding="utf-8")
            self.assertIn("License chain proves commercial digital-audiobook rights", delivery)
            summary = (packet_dir / "failed_tts_evidence_summary.md").read_text(encoding="utf-8")
            self.assertIn("robotic_texture_detected", summary)

    def test_hash_mismatch_and_missing_rights_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root, recorded_hash="wrong")
            with self.assertRaisesRegex(RuntimeError, "sanitized hash changed"):
                packet.create_packet(slug="sample-book", asset_root=root, output_root=root / "out")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root, rights_basis="")
            with self.assertRaisesRegex(RuntimeError, "rights evidence is incomplete"):
                packet.create_packet(slug="sample-book", asset_root=root, output_root=root / "out")

    def test_received_audio_preflight_is_local_and_keeps_release_hidden(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            created = packet.create_packet(slug="sample-book", asset_root=root, output_root=root / "out")
            audio = root / "received.mp3"
            audio.write_bytes(b"audio-bytes")
            probe = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    {
                        "streams": [
                            {
                                "codec_name": "mp3",
                                "sample_rate": "48000",
                                "channels": 1,
                                "bit_rate": "192000",
                            }
                        ],
                        "format": {"duration": "123.456", "size": "11", "bit_rate": "192000"},
                    }
                ),
                stderr="",
            )
            with mock.patch.object(packet.subprocess, "run", return_value=probe) as run:
                result = packet.validate_received_audio(
                    audio_path=audio,
                    packet_dir=Path(created["packet_dir"]),
                )
            run.assert_called_once()
            self.assertEqual(result["status"], "RECEIVED_AUDIO_PREFLIGHT_PASS_FULL_RELEASE_QA_REQUIRED")
            self.assertEqual(result["audio"]["file_name"], "received.mp3")
            self.assertFalse(result["provider_calls_ran"])
            self.assertFalse(result["release_gate_mutated"])
            self.assertEqual(result["public_audio_status"], "AUDIO_HIDDEN_PENDING_COMPLETE_RELEASE_GATES")


if __name__ == "__main__":
    unittest.main()
