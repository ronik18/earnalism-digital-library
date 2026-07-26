#!/usr/bin/env python3
"""Focused tests for the provider-free factory evidence normalizer."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "sprint1_factory_release_evidence_normalizer.py"
SPEC = importlib.util.spec_from_file_location(
    "sprint1_factory_release_evidence_normalizer",
    SCRIPT,
)
normalizer = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(normalizer)
builder = normalizer.packet_builder


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FactoryFixture:
    slug = "book-factory-pass"
    audio_hash = sha("full-title-audio")
    manuscript_hash = sha("narrated-manuscript")

    def __init__(self, base: Path):
        self.base = base
        self.source_root = base / "repo"
        self.evidence_dir = base / "factory-run"
        self.output_dir = base / "normalized"
        self.qa_path = self.evidence_dir / "goliveevidence.json"
        self.upload_path = self.evidence_dir / "upload_manifest.json"
        self.endpoint_path = self.evidence_dir / "browser_hook_result.json"
        self.diagnosis_path = self.evidence_dir / "asr_alignment_diagnosis.json"
        self.timestamps_path = self.evidence_dir / "timestamps.json"
        self.listening_path = self.evidence_dir / "listening_quality_report.json"
        self.source_root.mkdir(parents=True)
        self.qa = self.factory_qa()
        self.upload = self.upload_manifest()
        self.endpoint = self.endpoint_evidence()
        self.diagnosis = {
            "slug": self.slug,
            "score": 9.91,
            "coverage": 1.0,
            "token_order_similarity": 1.0,
            "first_words_match": True,
            "last_words_match": True,
            "frontmatter_absent": True,
        }
        self.timestamps = {
            "slug": self.slug,
            "alignment_method": "openai_verbose_json_word_timestamps",
            "auto_estimated_sync": False,
            "granularity": "word",
            "audio_hash": self.audio_hash,
            "source_text_hash": self.manuscript_hash,
            "words": [{"word": "প্রথম", "start": 0.0, "end": 0.5}],
        }
        self.listening = {
            "qa_schema_version": 3,
            "slug": self.slug,
            "language": "ben",
            "audio_hash": self.audio_hash,
            "listening_quality": {
                "status": "PASS",
                "audio_hash": self.audio_hash,
                "samples": [{"sample_label": f"sample-{index}"} for index in range(6)],
                "aggregate": {
                    "overall_listening_score": 9.4,
                    "confidence_score": 0.95,
                },
                "robotic_texture_detected": False,
                "mechanical_cadence_detected": False,
                "list_reading_rhythm_detected": False,
                "choppy_joins_detected": False,
                "fallback_tts_detected": False,
                "placeholder_audio_detected": False,
                "blockers": [],
            },
        }
        self.write()

    def factory_qa(self) -> dict:
        return {
            "qa_schema_version": 4,
            "phase": "final",
            "slug": self.slug,
            "language": "ben",
            "timestamp": "2026-07-23T10:00:00Z",
            "auto_approval_decision": True,
            "blocker_list": [],
            "lock_restored": True,
            "scores": {
                "transcript_match_score": 9.91,
                "truncation_score": 10.0,
                "duplicate_segment_score": 10.0,
                "overall_listening_score": 9.4,
                "listening_confidence_score": 0.95,
            },
            "hard_flags": {
                "fallback_tts_used_false": True,
                "auto_estimated_sync_false": True,
                "no_robotic_cadence": True,
                "no_mechanical_texture": True,
                "no_list_reading_rhythm": True,
                "no_choppy_joins": True,
                "no_placeholder_audio": True,
            },
            "stage_results": {
                "cover_queue": {
                    "status": "PASS",
                    "cover_status": {"status": "PASS"},
                },
                "manuscript_queue": {
                    "status": "PASS",
                    "content_integrity_status": "PASS",
                    "clean_text_hash": self.manuscript_hash,
                },
                "rights_metadata_preflight_queue": {
                    "status": "PASS",
                    "production_metadata_ready": True,
                },
                "tts_queue": {
                    "status": "PASS",
                    "blockers": [],
                    "metrics": {
                        "provider": "sarvam",
                        "model": "bulbul:v3",
                        "voice": "ratan",
                        "profile": "literary_warm_pacing",
                        "fallback_tts_used": False,
                        "duration_seconds": 120.25,
                    },
                },
                "asr_sync_queue": {
                    "status": "PASS",
                    "blockers": [],
                    "artifacts": {
                        "asr_alignment_diagnosis": str(self.diagnosis_path),
                        "timestamps": str(self.timestamps_path),
                        "listening_quality_report": str(self.listening_path),
                    },
                    "metrics": {
                        "transcript_match_score": 9.91,
                        "auto_estimated_sync": False,
                        "listening_qa_status": "PASS",
                    },
                    "updated_fields": {"auto_estimated_sync": False},
                },
                "upload_queue": {"status": "PASS", "blockers": []},
                "metadata_publish_queue": {
                    "status": "PASS",
                    "blockers": [],
                    "artifacts": {
                        "audiobook_endpoint": {
                            "url": f"https://api.example.test/reader/book/{self.slug}/audiobook",
                            "status": 206,
                            "ok": True,
                        }
                    },
                    "updated_fields": {
                        "rights_metadata_status": "PASS",
                        "production_approval_succeeded": True,
                        "audiobook_release_gate": "APPROVED",
                    },
                },
                "browser_gate_queue": {
                    "status": "PASS",
                    "blockers": [],
                    "updated_fields": {"browser_gate_status": "PASS"},
                },
            },
        }

    def upload_manifest(self) -> dict:
        urls = {
            key: f"https://storage.example.test/{self.slug}/{key}"
            for key in builder.REQUIRED_ASSET_KEYS
        }
        checksums = {}
        for index, key in enumerate(builder.REQUIRED_ASSET_KEYS, 1):
            digest = self.audio_hash if key == "mp3" else sha(f"{key}-artifact")
            size = 4096 if key == "mp3" else 100 + index
            checksums[key] = {
                "url": urls[key],
                "status": 200,
                "resolves": True,
                "local_sha256": digest,
                "remote_sha256": digest,
                "match": True,
                "local_size": size,
                "remote_size": size,
            }
        return {
            "slug": self.slug,
            "uploaded_at": "2026-07-23T09:58:00Z",
            "storage_backend": "b2_s3",
            "urls": urls,
            "checksums": checksums,
            "status": "PASS",
        }

    def endpoint_evidence(self) -> dict:
        routes = {
            "detail": {
                "url": f"https://www.example.test/book/{self.slug}",
                "status": 200,
                "ok": True,
            },
            "reader": {
                "url": f"https://www.example.test/reader/{self.slug}",
                "status": 200,
                "ok": True,
            },
            "audiobook": {
                "url": f"https://api.example.test/reader/book/{self.slug}/audiobook",
                "status": 206,
                "ok": True,
                "headers": {
                    "Accept-Ranges": "bytes",
                    "Content-Range": "bytes 0-1023/4096",
                    "Content-Length": "1024",
                },
            },
        }
        assets = {
            key: {
                "url": self.upload["urls"][key],
                "status": 206 if key == "mp3" else 200,
                "ok": True,
            }
            for key in builder.REQUIRED_ASSET_KEYS
        }
        return {
            "slug": self.slug,
            "stage": "browser",
            "status": "PASS",
            "blockers": [],
            "metrics": {
                "routes": routes,
                "assets": assets,
                "browser": {
                    "audio_control_visible": True,
                    "audio_start_latency_ms": 125.0,
                    "audio_probe": {
                        "audio_found": True,
                        "playback_advanced": True,
                    },
                    "console_errors": [],
                },
                "private_origin_checks": {
                    "mp3": {"anonymous_access_denied": True},
                },
            },
            "updated_fields": {"browser_gate_status": "PASS"},
            "finished_at": "2026-07-23T10:00:00Z",
        }

    def write(self) -> None:
        write_json(self.qa_path, self.qa)
        write_json(self.upload_path, self.upload)
        write_json(self.endpoint_path, self.endpoint)
        write_json(self.diagnosis_path, self.diagnosis)
        write_json(self.timestamps_path, self.timestamps)
        write_json(self.listening_path, self.listening)

    def normalize(self) -> dict:
        return normalizer.normalize_factory_evidence(
            self.qa_path,
            self.upload_path,
            self.endpoint_path,
            self.output_dir,
            self.source_root,
        )


class FactoryReleaseEvidenceNormalizerTests(unittest.TestCase):
    def assert_blocked_without_output(self, fixture: FactoryFixture) -> None:
        with self.assertRaises(normalizer.NormalizationBlocked):
            fixture.normalize()
        self.assertFalse(fixture.output_dir.exists())

    def test_normalizes_factory_evidence_into_builder_compatible_documents(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = FactoryFixture(Path(temporary))
            source_before = {
                path.relative_to(fixture.source_root): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in fixture.source_root.rglob("*")
                if path.is_file()
            }
            with mock.patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("network called"),
            ), mock.patch(
                "subprocess.run",
                side_effect=AssertionError("subprocess called"),
            ):
                result = fixture.normalize()

            self.assertEqual(result["status"], "NORMALIZED_FACTORY_EVIDENCE_READY")
            self.assertFalse(result["provider_calls_performed"])
            self.assertFalse(result["network_calls_performed"])
            self.assertFalse(result["paid_lock_touched"])
            self.assertEqual(
                {path.name for path in fixture.output_dir.iterdir()},
                set(normalizer.OUTPUT_FILENAMES),
            )
            source_after = {
                path.relative_to(fixture.source_root): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in fixture.source_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(source_after, source_before)

            qa = read_json(fixture.output_dir / "normalized_release_qa.json")
            upload = read_json(fixture.output_dir / "normalized_upload_manifest.json")
            endpoint = read_json(fixture.output_dir / "endpoint_proof.json")
            evidence = builder._validate_evidence(
                qa,
                upload,
                endpoint,
                {
                    "documents": {
                        "reader_manifest.json": {"language": "ben"},
                    }
                },
                fixture.slug,
            )
            self.assertEqual(evidence["audio_sha256"], fixture.audio_hash)
            self.assertEqual(evidence["manuscript_sha256"], fixture.manuscript_hash)
            self.assertEqual(evidence["sync_tier"], "WORD_OR_PHRASE_SYNC_FLAGSHIP")
            self.assertEqual(endpoint["response_size_bytes"], 1024)

    def test_projection_or_construction_score_cannot_replace_raw_asr_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = FactoryFixture(Path(temporary))
            fixture.diagnosis.update(
                {
                    "score": 1.2,
                    "raw_asr_score": 1.2,
                    "source_match_score": 10.0,
                    "asr_release_status": "SUPPORTING_DIAGNOSTIC_WEAK",
                }
            )
            fixture.qa["scores"]["transcript_match_score"] = 10.0
            fixture.write()
            self.assert_blocked_without_output(fixture)

    def test_inexact_content_or_failed_underlying_gate_blocks_without_output(self):
        cases = (
            ("missing_content", "diagnosis", "coverage", 0.998),
            ("reordered_content", "diagnosis", "token_order_similarity", 0.998),
            ("duplicate_content", "qa_score", "duplicate_segment_score", 9.99),
            ("estimated_sync", "timestamps", "auto_estimated_sync", True),
            ("listening_flag", "listening", "mechanical_cadence_detected", True),
            ("checksum_mismatch", "upload", "remote_sha256", sha("wrong")),
            ("endpoint_not_ranged", "endpoint", "status", 200),
            ("rights_not_ready", "rights", "production_metadata_ready", False),
            ("metadata_not_approved", "metadata", "production_approval_succeeded", False),
            ("browser_not_approved", "browser", "browser_gate_status", "BLOCKED"),
        )
        for label, document, key, value in cases:
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = FactoryFixture(Path(temporary))
                    if document == "diagnosis":
                        fixture.diagnosis[key] = value
                    elif document == "qa_score":
                        fixture.qa["scores"][key] = value
                    elif document == "timestamps":
                        fixture.timestamps[key] = value
                    elif document == "listening":
                        fixture.listening["listening_quality"][key] = value
                    elif document == "upload":
                        fixture.upload["checksums"]["mp3"][key] = value
                    elif document == "endpoint":
                        fixture.endpoint["metrics"]["routes"]["audiobook"][key] = value
                    elif document == "rights":
                        fixture.qa["stage_results"]["rights_metadata_preflight_queue"][key] = value
                    elif document == "metadata":
                        fixture.qa["stage_results"]["metadata_publish_queue"]["updated_fields"][key] = value
                    elif document == "browser":
                        fixture.qa["stage_results"]["browser_gate_queue"]["updated_fields"][key] = value
                    fixture.write()
                    self.assert_blocked_without_output(fixture)

    def test_missing_explicit_source_lock_proof_has_exact_blocker(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = FactoryFixture(Path(temporary))
            fixture.qa.pop("lock_restored")
            fixture.write()
            with self.assertRaises(normalizer.NormalizationBlocked) as caught:
                fixture.normalize()
            self.assertIn(
                "factory QA must include explicit lock_restored=true",
                caught.exception.blockers,
            )
            self.assertFalse(fixture.output_dir.exists())

    def test_duplicate_json_keys_and_nonempty_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = FactoryFixture(Path(temporary))
            fixture.qa_path.write_text(
                '{"slug":"book-factory-pass","slug":"other"}\n',
                encoding="utf-8",
            )
            with self.assertRaises(builder.ReleasePacketBlocked):
                fixture.normalize()
            self.assertFalse(fixture.output_dir.exists())

        with tempfile.TemporaryDirectory() as temporary:
            fixture = FactoryFixture(Path(temporary))
            fixture.output_dir.mkdir()
            sentinel = fixture.output_dir / "unchanged.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            with self.assertRaises(normalizer.NormalizationBlocked):
                fixture.normalize()
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged\n")


if __name__ == "__main__":
    unittest.main()
