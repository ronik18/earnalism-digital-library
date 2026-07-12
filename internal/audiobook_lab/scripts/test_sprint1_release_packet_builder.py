#!/usr/bin/env python3
"""Focused tests for the local-only Sprint 1 release packet builder."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("sprint1_release_packet_builder.py")
SPEC = importlib.util.spec_from_file_location("sprint1_release_packet_builder", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(builder)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tree_snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ReleaseFixture:
    slug = "book-test-release"
    chapter_content = "প্রথম বাক্য। শেষ বাক্য।"
    source_hash = sha(chapter_content)
    content_hash = sha("controlled-content")
    provenance_hash = sha("controlled-provenance")
    manuscript_hash = sha("clean-tts-manuscript")
    audio_hash = sha("final-audio")

    def __init__(self, base: Path):
        self.base = base
        self.source_root = base / "repo"
        self.evidence_dir = base / "evidence"
        self.output_dir = base / "release-packet"
        self.qa_path = self.evidence_dir / "title_qa.json"
        self.upload_path = self.evidence_dir / "upload_manifest.json"
        self.endpoint_path = self.evidence_dir / "endpoint_proof.json"
        self.public_sentinel = self.source_root / "frontend/public/release-sentinel.txt"
        self.public_sentinel.parent.mkdir(parents=True, exist_ok=True)
        self.public_sentinel.write_text("must remain unchanged\n", encoding="utf-8")
        self.qa = self._qa()
        self.upload = self._upload()
        self.endpoint = self._endpoint()
        self._write_controlled_source()
        self.write_evidence()

    def _public_book(self) -> dict:
        return {
            "id": f"controlled-{self.slug}",
            "slug": self.slug,
            "title": "পরীক্ষার গল্প",
            "author": "পরীক্ষক",
            "cover_image_url": "https://assets.example.test/cover.png",
            "formats": ["Ebook"],
            "chapters": [
                {
                    "id": "chapter-001",
                    "order": 1,
                    "title": "Full Text",
                    "processing_status": "ready",
                }
            ],
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
            "rights_tier": "A",
            "verification_status": "approved",
            "qa_status": "QA_PASSED",
            "approved_to_publish": True,
            "publication_status": "LIVE_APPROVED",
            "isPublic": True,
            "isLive": True,
            "is_published": True,
            "showInHomepage": False,
            "allowPublicReading": True,
            "allowCheckout": False,
            "allowPayment": False,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "generate_audiobook": False,
        }

    def _reader_manifest(self) -> dict:
        return {
            "slug": self.slug,
            "title": "পরীক্ষার গল্প",
            "author": "পরীক্ষক",
            "language": "ben",
            "chapter_count": 1,
            "chapters": [{"id": "chapter-001", "order": 1, "title": "Full Text"}],
            "preview_chapter_ids": ["chapter-001"],
            "audio_enabled": False,
            "audiobook_enabled": False,
        }

    def _approval(self) -> dict:
        return {
            "slug": self.slug,
            "approved_to_publish": True,
            "rights_tier": "A",
            "verification_status": "approved",
            "qa_status": "QA_PASSED",
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED",
            "audiobook_enabled": False,
            "allowCheckout": False,
            "allowPayment": False,
        }

    def _source_evidence(self) -> dict:
        return {
            "slug": self.slug,
            "source_url": "https://source.example.test/work",
            "source_name": "Legally cleared source",
            "source_license": "Public domain with commercial reuse allowed",
            "rights_basis": "Author and publication dates verified for commercial reuse.",
            "source_hash": self.source_hash,
            "content_hash": self.content_hash,
            "provenance_hash": self.provenance_hash,
            "reader_facing_boilerplate_removed": True,
        }

    def _chapter(self) -> dict:
        return {
            "id": "chapter-001",
            "order": 1,
            "title": "Full Text",
            "content": self.chapter_content,
            "content_hash": self.source_hash,
        }

    def _write_title_dir(self, title_dir: Path) -> None:
        files = {
            "public_book.json": self._public_book(),
            "reader_manifest.json": self._reader_manifest(),
            "approval_evidence.json": self._approval(),
            "source_evidence.json": self._source_evidence(),
            "chapters/chapter-001.json": self._chapter(),
        }
        for relative, payload in files.items():
            write_json(title_dir / relative, payload)
        checksum = {
            "slug": self.slug,
            "generated_at": "2026-07-13T00:00:00Z",
            "files": [
                {
                    "file": relative,
                    "sha256": hashlib.sha256((title_dir / relative).read_bytes()).hexdigest(),
                }
                for relative in sorted(files)
            ],
        }
        write_json(title_dir / "checksum_manifest.json", checksum)

    def _write_controlled_source(self) -> None:
        for relative_root in (
            builder.ROOT_CONTROLLED_PUBLICATIONS,
            builder.BACKEND_CONTROLLED_PUBLICATIONS,
        ):
            self._write_title_dir(self.source_root / relative_root / self.slug)
        root_launch = {
            "live_approved_slugs": ["dracula", self.slug],
            "pipeline_slugs": ["kshudhita-pashan"],
            "audio_enabled_slugs": ["existing-audio"],
        }
        backend_launch = {
            "live_approved_slugs": ["dracula", "backend-only-reader", self.slug],
            "pipeline_slugs": ["kshudhita-pashan"],
            "audio_enabled_slugs": ["existing-audio"],
        }
        write_json(self.source_root / builder.ROOT_CONTROLLED_LAUNCH, root_launch)
        write_json(self.source_root / builder.BACKEND_CONTROLLED_LAUNCH, backend_launch)

    def _qa(self) -> dict:
        return {
            "schema_version": 1,
            "slug": self.slug,
            "status": "FULL_RELEASE_QA_PASS",
            "language": "ben",
            "provider": "sarvam",
            "model": "bulbul:v3",
            "voice": "pooja",
            "style": "dialogue_human_touch",
            "audio_hash": self.audio_hash,
            "source_sha256": self.manuscript_hash,
            "audio_size_bytes": 4096,
            "audio_duration_seconds": 120.25,
            "asr_source_score": 9.8,
            "first_words_match": True,
            "last_words_match": True,
            "owner_listening_gate": {
                "passes": True,
                "sample_count": 6,
                "minimum_overall_score": 9.3,
                "minimum_confidence": 0.95,
                "fatal_flags": [],
            },
            "sync_tier": "PARAGRAPH_OR_STANZA_SYNC_PREMIUM",
            "auto_estimated_sync": False,
            "release_gates": {name: True for name in builder.QA_REQUIRED_GATES},
            "blockers": [],
            "hook_blockers": [],
            "failure_reasons": [],
            "lock_restored": True,
            "publication_performed": False,
            "finished_at": "2026-07-13T01:02:03Z",
        }

    def _upload(self) -> dict:
        hashes = {
            key: self.audio_hash if key == "mp3" else sha(f"uploaded-{key}")
            for key in builder.REQUIRED_ASSET_KEYS
        }
        sizes = {
            key: 4096 if key == "mp3" else 100 + index
            for index, key in enumerate(builder.REQUIRED_ASSET_KEYS)
        }
        urls = {
            key: f"https://storage.example.test/{self.slug}/{key}"
            for key in builder.REQUIRED_ASSET_KEYS
        }
        return {
            "schema_version": 1,
            "slug": self.slug,
            "status": "PASS",
            "storage_backend": "b2_s3",
            "audio_sha256": self.audio_hash,
            "source_sha256": self.manuscript_hash,
            "urls": urls,
            "checksums": {
                key: {
                    "url": urls[key],
                    "status": 200,
                    "resolves": True,
                    "local_sha256": hashes[key],
                    "remote_sha256": hashes[key],
                    "match": True,
                    "local_size": sizes[key],
                    "remote_size": sizes[key],
                }
                for key in builder.REQUIRED_ASSET_KEYS
            },
            "release_gates": {"upload_checksum_pass": True},
            "blockers": [],
            "uploaded_at": "2026-07-13T01:01:00Z",
        }

    def _endpoint(self) -> dict:
        return {
            "schema_version": 1,
            "slug": self.slug,
            "status": "PASS",
            "endpoint_url": f"https://api.example.test/reader/book/{self.slug}/audiobook",
            "http_status": 206,
            "response_size_bytes": 1024,
            "range_request_pass": True,
            "audio_sha256": self.audio_hash,
            "source_sha256": self.manuscript_hash,
            "release_gates": {name: True for name in builder.ENDPOINT_REQUIRED_GATES},
            "blockers": [],
            "checked_at": "2026-07-13T01:02:03Z",
        }

    def write_evidence(self) -> None:
        write_json(self.qa_path, self.qa)
        write_json(self.upload_path, self.upload)
        write_json(self.endpoint_path, self.endpoint)

    def build(self) -> dict:
        return builder.build_release_packet(
            self.qa_path,
            self.upload_path,
            self.endpoint_path,
            self.output_dir,
            self.source_root,
        )


class Sprint1ReleasePacketBuilderTests(unittest.TestCase):
    def assert_blocked_without_mutation(self, fixture: ReleaseFixture) -> None:
        source_before = tree_snapshot(fixture.source_root)
        with self.assertRaises(builder.ReleasePacketBlocked):
            fixture.build()
        self.assertEqual(tree_snapshot(fixture.source_root), source_before)
        self.assertFalse(fixture.output_dir.exists())

    def test_builds_mirrored_review_packet_without_api_or_source_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = ReleaseFixture(Path(temporary))
            source_before = tree_snapshot(fixture.source_root)
            with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network called")), mock.patch(
                "socket.create_connection", side_effect=AssertionError("network called")
            ):
                report = fixture.build()

            self.assertEqual(tree_snapshot(fixture.source_root), source_before)
            self.assertEqual(fixture.public_sentinel.read_text(encoding="utf-8"), "must remain unchanged\n")
            self.assertEqual(report["status"], "STAGED_RELEASE_PACKET_READY")
            self.assertFalse(report["api_calls_performed"])
            self.assertFalse(report["live_state_mutated"])
            self.assertFalse(report["public_paths_mutated"])

            root_title = fixture.output_dir / builder.ROOT_CONTROLLED_PUBLICATIONS / fixture.slug
            backend_title = fixture.output_dir / builder.BACKEND_CONTROLLED_PUBLICATIONS / fixture.slug
            root_files = sorted(path.relative_to(root_title) for path in root_title.rglob("*") if path.is_file())
            backend_files = sorted(path.relative_to(backend_title) for path in backend_title.rglob("*") if path.is_file())
            self.assertEqual(root_files, backend_files)
            for relative in root_files:
                self.assertEqual((root_title / relative).read_bytes(), (backend_title / relative).read_bytes())

            public_book = read_json(root_title / "public_book.json")
            self.assertTrue(public_book["audio_enabled"])
            self.assertTrue(public_book["audiobook_enabled"])
            self.assertEqual(public_book["audiobook"]["audio_sha256"], fixture.audio_hash)
            self.assertEqual(public_book["audiobook"]["source_sha256"], fixture.manuscript_hash)
            self.assertEqual(set(public_book["audiobook_assets"]), set(builder.REQUIRED_ASSET_KEYS))

            reader = read_json(root_title / "reader_manifest.json")
            self.assertFalse(reader["audio_enabled"])
            self.assertFalse(reader["audiobook_enabled"])
            approval = read_json(root_title / "approval_evidence.json")
            self.assertEqual(approval["audio_public_release"], "PUBLIC_AUDIO_RELEASE_APPROVED")
            self.assertEqual(approval["release_blockers"], [])

            for launch_relative in (builder.ROOT_CONTROLLED_LAUNCH, builder.BACKEND_CONTROLLED_LAUNCH):
                launch = read_json(fixture.output_dir / launch_relative)
                self.assertIn(fixture.slug, launch["audio_enabled_slugs"])
            self.assertNotEqual(
                read_json(fixture.output_dir / builder.ROOT_CONTROLLED_LAUNCH)["live_approved_slugs"],
                read_json(fixture.output_dir / builder.BACKEND_CONTROLLED_LAUNCH)["live_approved_slugs"],
            )

            checksum = read_json(root_title / "checksum_manifest.json")
            self.assertNotIn("checksum_manifest.json", {item["file"] for item in checksum["files"]})
            for entry in checksum["files"]:
                self.assertEqual(
                    hashlib.sha256((root_title / entry["file"]).read_bytes()).hexdigest(),
                    entry["sha256"],
                )
            self.assertTrue((fixture.output_dir / "release_packet.json").is_file())

    def test_every_missing_or_failed_publication_gate_blocks_without_writes(self):
        gate_documents = (
            ("qa", builder.QA_REQUIRED_GATES),
            ("upload", builder.UPLOAD_REQUIRED_GATES),
            ("endpoint", builder.ENDPOINT_REQUIRED_GATES),
        )
        for document_name, gates in gate_documents:
            for gate in gates:
                for mode in ("missing", "failed"):
                    with self.subTest(document=document_name, gate=gate, mode=mode):
                        with tempfile.TemporaryDirectory() as temporary:
                            fixture = ReleaseFixture(Path(temporary))
                            payload = getattr(fixture, document_name)
                            if mode == "missing":
                                payload["release_gates"].pop(gate)
                            else:
                                payload["release_gates"][gate] = {"passed": False}
                            fixture.write_evidence()
                            self.assert_blocked_without_mutation(fixture)

    def test_missing_or_mismatched_binding_hashes_block_without_writes(self):
        cases = (
            ("qa_audio_missing", "qa", "audio_hash", None),
            ("qa_manuscript_missing", "qa", "source_sha256", None),
            ("upload_manuscript_missing", "upload", "source_sha256", None),
            ("upload_manuscript_mismatch", "upload", "source_sha256", sha("wrong")),
            ("endpoint_audio_missing", "endpoint", "audio_sha256", None),
            ("endpoint_audio_mismatch", "endpoint", "audio_sha256", sha("wrong")),
            ("endpoint_manuscript_missing", "endpoint", "source_sha256", None),
            ("endpoint_manuscript_mismatch", "endpoint", "source_sha256", sha("wrong")),
        )
        for label, document_name, key, value in cases:
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = ReleaseFixture(Path(temporary))
                    payload = getattr(fixture, document_name)
                    if value is None:
                        payload.pop(key)
                    else:
                        payload[key] = value
                    fixture.write_evidence()
                    self.assert_blocked_without_mutation(fixture)

        for asset in builder.REQUIRED_ASSET_KEYS:
            for field in ("local_sha256", "remote_sha256"):
                with self.subTest(asset=asset, missing=field):
                    with tempfile.TemporaryDirectory() as temporary:
                        fixture = ReleaseFixture(Path(temporary))
                        fixture.upload["checksums"][asset].pop(field)
                        fixture.write_evidence()
                        self.assert_blocked_without_mutation(fixture)
            with self.subTest(asset=asset, mismatch="remote_sha256"):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = ReleaseFixture(Path(temporary))
                    fixture.upload["checksums"][asset]["remote_sha256"] = sha("wrong")
                    fixture.write_evidence()
                    self.assert_blocked_without_mutation(fixture)

    def test_missing_traceability_hash_and_mirrored_source_drift_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = ReleaseFixture(Path(temporary))
            for relative_root in (
                builder.ROOT_CONTROLLED_PUBLICATIONS,
                builder.BACKEND_CONTROLLED_PUBLICATIONS,
            ):
                path = fixture.source_root / relative_root / fixture.slug / "source_evidence.json"
                payload = read_json(path)
                payload.pop("provenance_hash")
                write_json(path, payload)
            self.assert_blocked_without_mutation(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = ReleaseFixture(Path(temporary))
            backend_public = (
                fixture.source_root
                / builder.BACKEND_CONTROLLED_PUBLICATIONS
                / fixture.slug
                / "public_book.json"
            )
            payload = read_json(backend_public)
            payload["title"] = "drifted title"
            write_json(backend_public, payload)
            self.assert_blocked_without_mutation(fixture)

    def test_failed_qa_and_nonempty_output_leave_existing_files_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = ReleaseFixture(Path(temporary))
            fixture.qa["status"] = "FULL_RELEASE_QA_BLOCKED"
            fixture.write_evidence()
            self.assert_blocked_without_mutation(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = ReleaseFixture(Path(temporary))
            fixture.output_dir.mkdir()
            sentinel = fixture.output_dir / "do-not-overwrite.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            source_before = tree_snapshot(fixture.source_root)
            with self.assertRaises(builder.ReleasePacketBlocked):
                fixture.build()
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged\n")
            self.assertEqual(tree_snapshot(fixture.source_root), source_before)

    def test_output_inside_source_or_frontend_public_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = ReleaseFixture(Path(temporary))
            source_before = tree_snapshot(fixture.source_root)
            for output in (
                fixture.source_root / "internal/staged-release",
                fixture.source_root / "frontend/public/staged-release",
            ):
                with self.subTest(output=output):
                    with self.assertRaises(builder.ReleasePacketBlocked):
                        builder.build_release_packet(
                            fixture.qa_path,
                            fixture.upload_path,
                            fixture.endpoint_path,
                            output,
                            fixture.source_root,
                        )
                    self.assertFalse(output.exists())
            self.assertEqual(tree_snapshot(fixture.source_root), source_before)


if __name__ == "__main__":
    unittest.main()
