#!/usr/bin/env python3

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
BACKEND_DIR = ROOT / "backend"
for candidate in (SCRIPT_DIR, BACKEND_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import audiobook_active_release_v2 as manager
from audiobook_packages import with_canonical_package_version


class ActiveReleaseManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.slug = "sample-book"
        self.source = "1" * 64
        self.manuscript = "2" * 64
        self.legacy = "9" * 64
        for relative in manager.MIRROR_RELATIVE_ROOTS:
            publication = self.repo / relative / self.slug
            publication.mkdir(parents=True)
            self._write_initial_publication(publication)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _write(path: Path, value: object) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _write_initial_publication(self, publication: Path) -> None:
        public_book = {
            "slug": self.slug,
            "title": "Sample Book",
            "source_hash": self.source,
            "content_hash": self.source,
            "audiobook_legacy_release_descriptor_sha256": self.legacy,
            "audio_enabled": False,
            "audiobook_enabled": False,
        }
        reader_manifest = {
            "slug": self.slug,
            "chapter_count": 1,
            "audio_enabled": False,
            "audiobook_enabled": False,
        }
        source_evidence = {
            "slug": self.slug,
            "source_hash": self.source,
            "content_hash": self.source,
            "manuscript_sha256": self.manuscript,
        }
        approval_evidence = {
            "slug": self.slug,
            "audiobook_enabled": False,
            "audio_public_release": "BLOCKED",
        }
        documents = {
            "public_book.json": public_book,
            "reader_manifest.json": reader_manifest,
            "source_evidence.json": source_evidence,
            "approval_evidence.json": approval_evidence,
        }
        for filename, value in documents.items():
            self._write(publication / filename, value)
        checksum = {
            "slug": self.slug,
            "generated_at": "2026-07-29T00:00:00Z",
            "files": [
                {
                    "file": filename,
                    "sha256": hashlib.sha256((publication / filename).read_bytes()).hexdigest(),
                }
                for filename in documents
            ]
            + [{"file": "checksum_manifest.json", "sha256": "0" * 64}],
        }
        self._write(publication / "checksum_manifest.json", checksum)

    def _refresh_checksums(self, publication: Path) -> None:
        checksum = manager.read_json(publication / "checksum_manifest.json")
        for row in checksum["files"]:
            filename = row["file"]
            if filename != "checksum_manifest.json":
                row["sha256"] = manager.sha256_file(publication / filename)
        self._write(publication / "checksum_manifest.json", checksum)

    def _prepare_approved_reader_only(self) -> None:
        for publication in manager.publication_dirs(self.repo, self.slug):
            public_book = manager.read_json(publication / "public_book.json")
            public_book.pop("audiobook_legacy_release_descriptor_sha256", None)
            public_book.update(
                {
                    "approved_to_publish": True,
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                    "isPublic": True,
                    "isLive": True,
                    "is_published": True,
                    "allowPublicReading": True,
                    "audio_enabled": False,
                    "audiobook_enabled": False,
                    "audiobook": {},
                    "audiobook_assets": {},
                    "chapters": [
                        {
                            "id": "chapter-001",
                            "processing_status": "ready",
                        }
                    ],
                }
            )
            reader_manifest = manager.read_json(
                publication / "reader_manifest.json"
            )
            reader_manifest.update(
                {
                    "audio_enabled": False,
                    "audiobook_enabled": False,
                    "chapter_count": 1,
                    "chapters": [{"id": "chapter-001"}],
                }
            )
            approval = manager.read_json(publication / "approval_evidence.json")
            approval.update(
                {
                    "approved_to_publish": True,
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                    "audiobook_enabled": False,
                    "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED_QA_REQUIRED",
                }
            )
            self._write(publication / "public_book.json", public_book)
            self._write(publication / "reader_manifest.json", reader_manifest)
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)

    def _prepare_package_audio_approval(
        self,
        *,
        upload_status: str = "UPLOADED_CHECKSUM_VERIFIED",
    ) -> None:
        for publication in manager.publication_dirs(self.repo, self.slug):
            public_book = manager.read_json(publication / "public_book.json")
            public_book.update(
                {
                    "approved_to_publish": True,
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                    "isPublic": True,
                    "isLive": True,
                    "is_published": True,
                    "allowPublicReading": True,
                    "audio_enabled": True,
                    "audiobook_enabled": True,
                    "chapters": [
                        {
                            "id": "chapter-001",
                            "processing_status": "ready",
                        }
                    ],
                }
            )
            reader_manifest = manager.read_json(
                publication / "reader_manifest.json"
            )
            reader_manifest.update(
                {
                    "audio_enabled": True,
                    "audiobook_enabled": True,
                    "chapter_count": 1,
                    "chapters": [{"id": "chapter-001"}],
                }
            )
            approval = manager.read_json(publication / "approval_evidence.json")
            approval.update(
                {
                    "approved_to_publish": True,
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                    "audio_qa_status": "QA_PASSED",
                    "audio_public_release": "PUBLIC_AUDIO_RELEASE_APPROVED",
                    "audiobook_enabled": True,
                    "upload_status": upload_status,
                    "approval_scope": "test_release_packet_all_gates_passed",
                    "release_blockers": [],
                }
            )
            self._write(publication / "public_book.json", public_book)
            self._write(publication / "reader_manifest.json", reader_manifest)
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)

    def _prepare_approved_legacy(
        self,
        *,
        upload_status: str = "UPLOADED_CHECKSUM_VERIFIED",
    ) -> None:
        assets = {
            "mp3": "https://audio.example.invalid/sample-book.mp3",
            "timestamps": "https://audio.example.invalid/sample-book.timestamps.json",
            "vtt": "https://audio.example.invalid/sample-book.vtt",
            "chapters": "https://audio.example.invalid/sample-book.chapters.json",
            "meta": "https://audio.example.invalid/sample-book.meta.json",
        }
        for publication in manager.publication_dirs(self.repo, self.slug):
            public_book = manager.read_json(publication / "public_book.json")
            public_book.pop("audiobook_legacy_release_descriptor_sha256", None)
            public_book.update(
                {
                    "audio_enabled": True,
                    "audiobook_enabled": True,
                    "approved_to_publish": True,
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                    "isPublic": True,
                    "isLive": True,
                    "is_published": True,
                    "allowPublicReading": True,
                    "audiobook_provider": "test-provider",
                    "audiobook_voice": "test-voice",
                    "audiobook_model": "test-model",
                    "audiobook_style_profile": "test-style",
                    "audiobook_assets": assets,
                    "audiobook": {
                        "url": assets["mp3"],
                        "provider": "test-provider",
                        "size": 123456,
                        "duration_ms": 654321,
                        "assets": assets,
                    },
                    "chapters": [
                        {
                            "id": "chapter-001",
                            "processing_status": "ready",
                        }
                    ],
                }
            )
            reader_manifest = manager.read_json(publication / "reader_manifest.json")
            reader_manifest.pop("audiobook_legacy_release_descriptor_sha256", None)
            reader_manifest.update(
                {
                    "audio_enabled": True,
                    "audiobook_enabled": True,
                    "chapter_count": 1,
                    "chapters": [{"id": "chapter-001"}],
                }
            )
            approval = manager.read_json(publication / "approval_evidence.json")
            approval.update(
                {
                    "approved_to_publish": True,
                    "verification_status": "approved",
                    "qa_status": "QA_PASSED",
                    "audio_qa_status": "QA_PASSED",
                    "audio_public_release": "PUBLIC_AUDIO_RELEASE_APPROVED",
                    "audiobook_enabled": True,
                    "upload_status": upload_status,
                    "audio_sha256": "6" * 64,
                    "source_sha256": self.source,
                    "approval_scope": "test_release_packet_all_gates_passed",
                }
            )
            self._write(publication / "public_book.json", public_book)
            self._write(publication / "reader_manifest.json", reader_manifest)
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)

    def _release_descriptor(self, descriptor_digit: str) -> dict:
        return {
            "schema_version": "audiobook_release_descriptor.v1",
            "slug": self.slug,
            "controlled_source_sha256": self.source,
            "manuscript_sha256": self.manuscript,
            "known_release_blockers": [],
            "release_candidate_status": "RELEASE_CANDIDATE",
            "release_candidate_evidence": {
                "status": "PASS",
                "all_release_gates_passed": True,
            },
            "evidence_sha256": {"full-release-qa.json": descriptor_digit * 64},
        }

    def _package(
        self,
        descriptor_digit: str,
        release_descriptor: dict | None = None,
    ) -> dict:
        descriptor = manager.sha256_bytes(
            manager.canonical_json_bytes(
                release_descriptor or self._release_descriptor(descriptor_digit)
            )
        )
        prefix = f"v1/prod/sprint1/{self.slug}/releases/{descriptor}/"

        def storage(store: str, bucket: str, key: str, suffix: str) -> dict:
            return {
                "store": store,
                "bucket": bucket,
                "key": key,
                "version_id": f"{store}-{suffix}-version",
            }

        assets = {}
        definitions = {
            "audio": ("a", 1000, "audio/mpeg", "segment.mp3"),
            "timestamps": ("b", 200, "application/json", "segment.timestamps.json"),
            "vtt": ("c", 150, "text/vtt", "segment.vtt"),
            "metadata": ("d", 175, "application/json", "segment.metadata.json"),
        }
        for name, (digest_digit, size, mime_type, filename) in definitions.items():
            key = f"{prefix}delivery/{filename}"
            assets[name] = {
                "sha256": digest_digit * 64,
                "size_bytes": size,
                "mime_type": mime_type,
                "storage": storage("prod", "prod-bucket", key, name),
                "replicas": [storage("dr", "dr-bucket", key, name)],
            }
        return with_canonical_package_version(
            {
                "schema_version": "audiobook_package_manifest.v2",
                "slug": self.slug,
                "release_evidence_version": f"evidence-{descriptor_digit}",
                "release_descriptor_sha256": descriptor,
                "source_sha256": self.source,
                "manuscript_sha256": self.manuscript,
                "duration_ms": 100_000,
                "segment_count": 1,
                "word_count": 10,
                "paragraph_count": 1,
                "sync_tier": "paragraph_or_stanza",
                "highlight_sync_enabled": False,
                "tracks": [
                    {
                        "id": "chapter-001",
                        "chapter_id": "chapter-001",
                        "order": 0,
                        "title": "Chapter 1",
                        "start_word": 0,
                        "end_word": 9,
                        "start_paragraph": 0,
                        "end_paragraph": 0,
                        "chunks": [
                            {
                                "segment_id": "c001-s001",
                                "order": 0,
                                "start_word": 0,
                                "end_word": 9,
                                "start_paragraph": 0,
                                "end_paragraph": 0,
                                "cumulative_start_ms": 0,
                                "duration_ms": 100_000,
                                "assets": assets,
                            }
                        ],
                    }
                ],
            }
        )

    def _receipts(self, package: dict) -> tuple[dict, dict]:
        primary_rows = []
        replica_rows = []
        for asset_id, asset in package["tracks"][0]["chunks"][0]["assets"].items():
            base = {
                "asset_id": asset_id,
                "sha256": asset["sha256"],
                "size_bytes": asset["size_bytes"],
                "mime_type": asset["mime_type"],
                "full_download_verified": True,
            }
            primary_rows.append({**base, **asset["storage"]})
            replica_rows.append({**base, **asset["replicas"][0]})
        common = {
            "receipt_schema": manager.RECEIPT_SCHEMA,
            "passed": True,
            "slug": self.slug,
            "release_descriptor_sha256": package["release_descriptor_sha256"],
        }
        primary = {
            **common,
            "receipt_role": "primary",
            "release_eligible": True,
            "store": {
                "role": "prod",
                "endpoint_host": "prod.example.invalid",
                "region": "prod-region",
                "bucket": "prod-bucket",
                "account_fingerprint": "prod-account",
                "release_eligible": True,
            },
            "objects": primary_rows,
        }
        replica = {
            **common,
            "receipt_role": "replica",
            "release_eligible": True,
            "store": {
                "role": "dr",
                "endpoint_host": "dr.example.invalid",
                "region": "dr-region",
                "bucket": "dr-bucket",
                "account_fingerprint": "dr-account",
                "release_eligible": True,
            },
            "objects": replica_rows,
        }
        return primary, replica

    def _release_manifest_receipts(self, package: dict) -> tuple[dict, dict, str, int]:
        manifest_bytes = manager.json_bytes(package)
        manifest_sha256 = manager.sha256_bytes(manifest_bytes)
        manifest_size = len(manifest_bytes)
        key = (
            f"v1/prod/sprint1/{self.slug}/releases/"
            f"{package['release_descriptor_sha256']}/release-manifest.json"
        )
        primary, replica = self._receipts(package)
        primary["objects"] = [
            {
                "asset_id": "release.manifest",
                "store": "prod",
                "bucket": "prod-bucket",
                "key": key,
                "sha256": manifest_sha256,
                "size_bytes": manifest_size,
                "mime_type": "application/json",
                "version_id": "prod-release-manifest-version",
                "full_download_verified": True,
            }
        ]
        replica["objects"] = [
            {
                "asset_id": "release.manifest",
                "store": "dr",
                "bucket": "dr-bucket",
                "key": key,
                "sha256": manifest_sha256,
                "size_bytes": manifest_size,
                "mime_type": "application/json",
                "version_id": "dr-release-manifest-version",
                "full_download_verified": True,
            }
        ]
        return primary, replica, manifest_sha256, manifest_size

    def _snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.repo)): path.read_bytes()
            for path in sorted(self.repo.rglob("*.json"))
        }

    def _stage(self, descriptor_digit: str = "3") -> dict:
        package = self._package(descriptor_digit)
        return self._invoke_stage(
            package,
            self._release_descriptor(descriptor_digit),
            rollout_salt=f"sticky-{descriptor_digit}",
        )

    def _invoke_stage(
        self,
        package: dict,
        release_descriptor: dict,
        *,
        rollout_salt: str = "sticky",
        primary: dict | None = None,
        replica: dict | None = None,
        manifest_primary: dict | None = None,
        manifest_replica: dict | None = None,
        manifest_sha256: str = "",
        manifest_size: int = 0,
        legacy_descriptor: str | None = None,
    ) -> dict:
        default_primary, default_replica = self._receipts(package)
        (
            default_manifest_primary,
            default_manifest_replica,
            default_manifest_sha256,
            default_manifest_size,
        ) = self._release_manifest_receipts(package)
        primary = primary or default_primary
        replica = replica or default_replica
        manifest_primary = manifest_primary or default_manifest_primary
        manifest_replica = manifest_replica or default_manifest_replica
        return manager.stage_candidate(
            self.repo,
            self.slug,
            package,
            release_descriptor,
            primary,
            replica,
            manifest_primary,
            manifest_replica,
            rollout_salt=rollout_salt,
            legacy_descriptor=(
                self.legacy if legacy_descriptor is None else legacy_descriptor
            ),
            expected_manuscript_sha256=self.manuscript,
            release_manifest_sha256=manifest_sha256 or default_manifest_sha256,
            release_manifest_size_bytes=manifest_size or default_manifest_size,
            generated_at="2026-07-29T12:00:00Z",
            apply=True,
            primary_receipt_sha256="e" * 64,
            replica_receipt_sha256="f" * 64,
            primary_release_manifest_receipt_sha256="7" * 64,
            replica_release_manifest_receipt_sha256="8" * 64,
        )

    def _invoke_initial(
        self,
        package: dict,
        release_descriptor: dict,
        *,
        primary: dict | None = None,
        replica: dict | None = None,
        manifest_primary: dict | None = None,
        manifest_replica: dict | None = None,
        manifest_sha256: str = "",
        manifest_size: int = 0,
        apply: bool = True,
    ) -> dict:
        default_primary, default_replica = self._receipts(package)
        (
            default_manifest_primary,
            default_manifest_replica,
            default_manifest_sha256,
            default_manifest_size,
        ) = self._release_manifest_receipts(package)
        return manager.activate_initial_release(
            self.repo,
            self.slug,
            package,
            release_descriptor,
            primary or default_primary,
            replica or default_replica,
            manifest_primary or default_manifest_primary,
            manifest_replica or default_manifest_replica,
            expected_manuscript_sha256=self.manuscript,
            release_manifest_sha256=(
                manifest_sha256 or default_manifest_sha256
            ),
            release_manifest_size_bytes=manifest_size or default_manifest_size,
            generated_at="2026-07-29T12:00:00Z",
            apply=apply,
            primary_receipt_sha256="e" * 64,
            replica_receipt_sha256="f" * 64,
            primary_release_manifest_receipt_sha256="7" * 64,
            replica_release_manifest_receipt_sha256="8" * 64,
        )

    def test_stage_validates_then_updates_identical_mirrors_and_checksums(self) -> None:
        result = self._stage()
        self.assertEqual(result["status"], "CANDIDATE_STAGED")
        publications = manager.publication_dirs(self.repo, self.slug)
        for filename in ("public_book.json", "reader_manifest.json", "checksum_manifest.json"):
            self.assertEqual(
                (publications[0] / filename).read_bytes(),
                (publications[1] / filename).read_bytes(),
            )
        public_book = manager.read_json(publications[0] / "public_book.json")
        state = public_book["audiobook_active_release"]
        candidate = self._package("3")["release_descriptor_sha256"]
        self.assertEqual(state["active_release_descriptor_sha256"], self.legacy)
        self.assertEqual(state["candidate_release_descriptor_sha256"], candidate)
        self.assertEqual(state["rollout"]["percentage"], 0)
        self.assertIn(candidate, public_book["audiobook_packages"])
        self.assertFalse(public_book["audiobook_enabled"])
        evidence = public_book["audiobook_package_release_evidence"][candidate]
        self.assertRegex(evidence["release_manifest_sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(evidence["primary_release_manifest_receipt_sha256"], "7" * 64)
        self.assertEqual(evidence["replica_release_manifest_receipt_sha256"], "8" * 64)
        checksum = manager.read_json(publications[0] / "checksum_manifest.json")
        checksums = {row["file"]: row["sha256"] for row in checksum["files"]}
        self.assertEqual(
            checksums["public_book.json"],
            manager.sha256_file(publications[0] / "public_book.json"),
        )
        self.assertEqual(
            checksums["reader_manifest.json"],
            manager.sha256_file(publications[0] / "reader_manifest.json"),
        )

    def test_initial_activation_binds_first_package_without_approving_audio(self) -> None:
        self._prepare_approved_reader_only()
        package = self._package("3")
        before = manager.load_mirrored_publication(self.repo, self.slug)
        public_flags_before = {
            key: before["public_book"].get(key)
            for key in ("audio_enabled", "audiobook_enabled")
        }
        reader_flags_before = {
            key: before["reader_manifest"].get(key)
            for key in ("audio_enabled", "audiobook_enabled")
        }
        approval_before = copy.deepcopy(before["approval_evidence"])

        dry_run_snapshot = self._snapshot()
        dry_run = self._invoke_initial(
            package,
            self._release_descriptor("3"),
            apply=False,
        )
        self.assertEqual(
            dry_run["status"],
            "INITIAL_RELEASE_ACTIVATION_VALIDATED",
        )
        self.assertFalse(dry_run["applied"])
        self.assertEqual(dry_run_snapshot, self._snapshot())

        result = self._invoke_initial(package, self._release_descriptor("3"))
        self.assertEqual(result["status"], "INITIAL_RELEASE_ACTIVATED")
        self.assertFalse(result["audio_approval_flags_changed"])
        context = manager.load_mirrored_publication(self.repo, self.slug)
        state = context["public_book"]["audiobook_active_release"]
        descriptor = package["release_descriptor_sha256"]
        self.assertEqual(state["status"], "ACTIVE")
        self.assertEqual(state["active_release_descriptor_sha256"], descriptor)
        self.assertEqual(state["candidate_release_descriptor_sha256"], "")
        self.assertEqual(state["retained_release_descriptor_sha256s"], [descriptor])
        self.assertEqual(
            context["public_book"]["audiobook_release_descriptor_sha256"],
            descriptor,
        )
        self.assertEqual(
            context["public_book"]["audiobook_legacy_release_descriptor_sha256"],
            "",
        )
        self.assertEqual(context["public_book"]["audiobook_packages"], {descriptor: package})
        self.assertIn(
            descriptor,
            context["public_book"]["audiobook_package_release_evidence"],
        )
        self.assertEqual(
            {
                key: context["public_book"].get(key)
                for key in ("audio_enabled", "audiobook_enabled")
            },
            public_flags_before,
        )
        self.assertEqual(
            {
                key: context["reader_manifest"].get(key)
                for key in ("audio_enabled", "audiobook_enabled")
            },
            reader_flags_before,
        )
        self.assertEqual(context["approval_evidence"], approval_before)
        manager._verify_controlled_checksums(context)

    def test_initial_activation_rejects_unapproved_or_nonempty_release_slot(self) -> None:
        package = self._package("3")
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "approved live reader/publication truth",
        ):
            self._invoke_initial(package, self._release_descriptor("3"))
        self.assertEqual(before, self._snapshot())

        self._prepare_approved_reader_only()
        for publication in manager.publication_dirs(self.repo, self.slug):
            public_book = manager.read_json(publication / "public_book.json")
            public_book["audiobook_legacy_release_descriptor_sha256"] = self.legacy
            reader_manifest = manager.read_json(
                publication / "reader_manifest.json"
            )
            reader_manifest["audiobook_legacy_release_descriptor_sha256"] = (
                self.legacy
            )
            self._write(publication / "public_book.json", public_book)
            self._write(publication / "reader_manifest.json", reader_manifest)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "empty release pointer slot",
        ):
            self._invoke_initial(package, self._release_descriptor("3"))
        self.assertEqual(before, self._snapshot())

    def test_initial_package_can_stage_promote_and_rollback_without_legacy(self) -> None:
        self._prepare_approved_reader_only()
        package_3 = self._package("3")
        package_4 = self._package("4")
        self._invoke_initial(package_3, self._release_descriptor("3"))
        staged = self._invoke_stage(
            package_4,
            self._release_descriptor("4"),
            legacy_descriptor="",
        )
        self.assertEqual(staged["status"], "CANDIDATE_STAGED")
        manager.set_rollout(self.repo, self.slug, 100, apply=True)
        context = manager.load_mirrored_publication(self.repo, self.slug)
        self.assertEqual(
            context["public_book"]["audiobook_active_release"][
                "active_release_descriptor_sha256"
            ],
            package_4["release_descriptor_sha256"],
        )
        previous = manager.rollback_release(
            self.repo,
            self.slug,
            "previous",
            apply=True,
        )
        self.assertEqual(
            previous["selected_release_descriptor_sha256"],
            package_3["release_descriptor_sha256"],
        )
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "No approved legacy release",
        ):
            manager.rollback_release(
                self.repo,
                self.slug,
                "legacy",
                apply=True,
            )
        self.assertEqual(before, self._snapshot())

    def test_bind_legacy_is_deterministic_dry_run_then_single_field_apply(self) -> None:
        self._prepare_approved_legacy()
        before = self._snapshot()
        dry_run = manager.bind_legacy_release(self.repo, self.slug)
        self.assertEqual(dry_run["status"], "LEGACY_BINDING_VALIDATED")
        self.assertFalse(dry_run["applied"])
        self.assertEqual(before, self._snapshot())
        descriptor = dry_run["audiobook_legacy_release_descriptor_sha256"]
        self.assertRegex(descriptor, r"^[a-f0-9]{64}$")

        publications = manager.publication_dirs(self.repo, self.slug)
        public_before = manager.read_json(publications[0] / "public_book.json")
        reader_before = manager.read_json(publications[0] / "reader_manifest.json")
        approval_before = manager.read_json(publications[0] / "approval_evidence.json")
        applied = manager.bind_legacy_release(
            self.repo,
            self.slug,
            generated_at="2026-07-29T14:00:00Z",
            apply=True,
        )
        self.assertEqual(applied["status"], "LEGACY_BOUND")
        self.assertTrue(applied["applied"])
        for publication in publications:
            public_after = manager.read_json(publication / "public_book.json")
            reader_after = manager.read_json(publication / "reader_manifest.json")
            approval_after = manager.read_json(publication / "approval_evidence.json")
            self.assertEqual(
                public_after.pop("audiobook_legacy_release_descriptor_sha256"),
                descriptor,
            )
            self.assertEqual(
                reader_after.pop("audiobook_legacy_release_descriptor_sha256"),
                descriptor,
            )
            self.assertEqual(public_after, public_before)
            self.assertEqual(reader_after, reader_before)
            self.assertEqual(approval_after, approval_before)
            manager._verify_controlled_checksums(
                manager.load_mirrored_publication(self.repo, self.slug)
            )

        idempotent = manager.bind_legacy_release(self.repo, self.slug, apply=True)
        self.assertEqual(idempotent["status"], "LEGACY_ALREADY_BOUND")
        self.assertFalse(idempotent["applied"])

    def test_bind_legacy_rejects_unapproved_audio(self) -> None:
        self._prepare_approved_legacy()
        for publication in manager.publication_dirs(self.repo, self.slug):
            approval = manager.read_json(publication / "approval_evidence.json")
            approval["audio_public_release"] = "PUBLIC_AUDIO_RELEASE_BLOCKED"
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(manager.ReleasePointerError, "not already approved"):
            manager.bind_legacy_release(self.repo, self.slug, apply=True)
        self.assertEqual(before, self._snapshot())

    def test_bind_legacy_accepts_only_narrow_checksum_verified_upload_statuses(
        self,
    ) -> None:
        self._prepare_approved_legacy(
            upload_status="UPLOADED_CHECKSUM_VERIFIED_PRIVATE_ORIGIN"
        )
        result = manager.bind_legacy_release(self.repo, self.slug)
        self.assertEqual(result["status"], "LEGACY_BINDING_VALIDATED")

        for publication in manager.publication_dirs(self.repo, self.slug):
            approval = manager.read_json(publication / "approval_evidence.json")
            approval["upload_status"] = "UPLOADED_CHECKSUM_VERIFIED_SOMETHING_ELSE"
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "checksum-verified upload evidence",
        ):
            manager.bind_legacy_release(self.repo, self.slug, apply=True)
        self.assertEqual(before, self._snapshot())

    def test_bind_legacy_accepts_only_exact_canonical_reader_proxy_endpoint(
        self,
    ) -> None:
        self._prepare_approved_legacy(
            upload_status="UPLOADED_CHECKSUM_VERIFIED_PRIVATE_ORIGIN"
        )
        for publication in manager.publication_dirs(self.repo, self.slug):
            approval = manager.read_json(publication / "approval_evidence.json")
            approval["endpoint_url"] = (
                f"https://api.theearnalism.com/api/reader/book/"
                f"{self.slug}/audiobook"
            )
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)
        result = manager.bind_legacy_release(self.repo, self.slug)
        self.assertEqual(result["status"], "LEGACY_BINDING_VALIDATED")

        for publication in manager.publication_dirs(self.repo, self.slug):
            approval = manager.read_json(publication / "approval_evidence.json")
            approval["endpoint_url"] = (
                f"https://api.theearnalism.com/api/reader/book/"
                f"{self.slug}/audiobook?bypass=1"
            )
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "endpoint and legacy MP3 identities conflict",
        ):
            manager.bind_legacy_release(self.repo, self.slug, apply=True)
        self.assertEqual(before, self._snapshot())

    def test_bind_legacy_rejects_missing_exact_audio_hash(self) -> None:
        self._prepare_approved_legacy()
        for publication in manager.publication_dirs(self.repo, self.slug):
            approval = manager.read_json(publication / "approval_evidence.json")
            approval.pop("audio_sha256")
            self._write(publication / "approval_evidence.json", approval)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(manager.ReleasePointerError, "exact controlled MP3"):
            manager.bind_legacy_release(self.repo, self.slug, apply=True)
        self.assertEqual(before, self._snapshot())

    def test_bind_legacy_rejects_conflicting_existing_descriptor(self) -> None:
        self._prepare_approved_legacy()
        for publication in manager.publication_dirs(self.repo, self.slug):
            public_book = manager.read_json(publication / "public_book.json")
            public_book["audiobook_legacy_release_descriptor_sha256"] = "8" * 64
            self._write(publication / "public_book.json", public_book)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(manager.ReleasePointerError, "conflicts"):
            manager.bind_legacy_release(self.repo, self.slug, apply=True)
        self.assertEqual(before, self._snapshot())

    def test_invalid_package_or_private_qa_receipt_cannot_mutate_catalog(self) -> None:
        package = self._package("3")
        release_descriptor = self._release_descriptor("3")
        primary, replica = self._receipts(package)
        manifest_primary, manifest_replica, manifest_sha256, manifest_size = (
            self._release_manifest_receipts(package)
        )
        before = self._snapshot()
        broken = copy.deepcopy(package)
        broken["package_version"] = f"sha256-{'0' * 64}"
        with self.assertRaisesRegex(manager.ReleasePointerError, "Canonical package validation failed"):
            manager.stage_candidate(
                self.repo,
                self.slug,
                broken,
                release_descriptor,
                primary,
                replica,
                manifest_primary,
                manifest_replica,
                rollout_salt="sticky",
                legacy_descriptor=self.legacy,
                expected_manuscript_sha256=self.manuscript,
                release_manifest_sha256=manifest_sha256,
                release_manifest_size_bytes=manifest_size,
                apply=True,
                primary_receipt_sha256="e" * 64,
                replica_receipt_sha256="f" * 64,
                primary_release_manifest_receipt_sha256="7" * 64,
                replica_release_manifest_receipt_sha256="8" * 64,
            )
        self.assertEqual(before, self._snapshot())

        private_receipt = copy.deepcopy(primary)
        private_receipt["receipt_role"] = "private_qa_staging"
        private_receipt["release_eligible"] = False
        private_receipt["store"] = {
            "role": "private_qa_staging",
            "release_eligible": False,
        }
        with self.assertRaisesRegex(manager.ReleasePointerError, "receipt role is invalid"):
            manager.stage_candidate(
                self.repo,
                self.slug,
                package,
                release_descriptor,
                private_receipt,
                replica,
                manifest_primary,
                manifest_replica,
                rollout_salt="sticky",
                legacy_descriptor=self.legacy,
                expected_manuscript_sha256=self.manuscript,
                release_manifest_sha256=manifest_sha256,
                release_manifest_size_bytes=manifest_size,
                apply=True,
                primary_receipt_sha256="e" * 64,
                replica_receipt_sha256="f" * 64,
                primary_release_manifest_receipt_sha256="7" * 64,
                replica_release_manifest_receipt_sha256="8" * 64,
            )
        self.assertEqual(before, self._snapshot())

    def test_matching_private_audio_receipts_cannot_stage_candidate(self) -> None:
        package = copy.deepcopy(self._package("3"))
        for track in package["tracks"]:
            for chunk in track["chunks"]:
                for asset in chunk["assets"].values():
                    asset["storage"]["store"] = "private_audio"
        package = with_canonical_package_version(package)
        primary, replica = self._receipts(package)
        primary["store"]["role"] = "private_audio"
        (
            manifest_primary,
            manifest_replica,
            manifest_sha256,
            manifest_size,
        ) = self._release_manifest_receipts(package)
        manifest_primary["store"]["role"] = "private_audio"
        manifest_primary["objects"][0]["store"] = "private_audio"
        before = self._snapshot()

        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "canonical prod store",
        ):
            self._invoke_stage(
                package,
                self._release_descriptor("3"),
                primary=primary,
                replica=replica,
                manifest_primary=manifest_primary,
                manifest_replica=manifest_replica,
                manifest_sha256=manifest_sha256,
                manifest_size=manifest_size,
            )
        self.assertEqual(before, self._snapshot())

    def test_rollout_accepts_only_0_5_25_100_and_100_promotes(self) -> None:
        self._stage()
        before = self._snapshot()
        with self.assertRaisesRegex(manager.ReleasePointerError, "one of 0, 5, 25, 100"):
            manager.set_rollout(self.repo, self.slug, 10, apply=True)
        self.assertEqual(before, self._snapshot())

        manager.set_rollout(self.repo, self.slug, 5, apply=True)
        public_book = manager.load_mirrored_publication(self.repo, self.slug)["public_book"]
        self.assertEqual(public_book["audiobook_active_release"]["rollout"]["percentage"], 5)
        manager.set_rollout(self.repo, self.slug, 25, apply=True)
        public_book = manager.load_mirrored_publication(self.repo, self.slug)["public_book"]
        self.assertEqual(public_book["audiobook_active_release"]["rollout"]["percentage"], 25)

        manager.set_rollout(self.repo, self.slug, 100, apply=True)
        public_book = manager.load_mirrored_publication(self.repo, self.slug)["public_book"]
        state = public_book["audiobook_active_release"]
        self.assertEqual(
            state["active_release_descriptor_sha256"],
            self._package("3")["release_descriptor_sha256"],
        )
        self.assertEqual(state["candidate_release_descriptor_sha256"], "")
        self.assertEqual(state["rollout"]["percentage"], 0)
        self.assertLessEqual(len(state["retained_release_descriptor_sha256s"]), 3)

    def test_two_promotions_retain_current_plus_two_prior_and_rollback(self) -> None:
        self._stage("3")
        manager.set_rollout(self.repo, self.slug, 100, apply=True)
        self._stage("4")
        manager.set_rollout(self.repo, self.slug, 100, apply=True)
        context = manager.load_mirrored_publication(self.repo, self.slug)
        retained = context["public_book"]["audiobook_active_release"][
            "retained_release_descriptor_sha256s"
        ]
        release_3 = self._package("3")["release_descriptor_sha256"]
        release_4 = self._package("4")["release_descriptor_sha256"]
        self.assertEqual(retained, [release_4, release_3, self.legacy])

        previous = manager.rollback_release(self.repo, self.slug, "previous", apply=True)
        self.assertEqual(previous["selected_release_descriptor_sha256"], release_3)
        legacy = manager.rollback_release(self.repo, self.slug, "legacy", apply=True)
        self.assertEqual(legacy["selected_release_descriptor_sha256"], self.legacy)
        state = manager.load_mirrored_publication(self.repo, self.slug)["public_book"][
            "audiobook_active_release"
        ]
        self.assertEqual(state["active_release_descriptor_sha256"], self.legacy)
        self.assertEqual(state["rollout"]["percentage"], 0)

    def test_deactivate_blocks_mutators_and_reactivation_requires_current_approval(
        self,
    ) -> None:
        self._stage("3")
        manager.set_rollout(self.repo, self.slug, 100, apply=True)
        context = manager.load_mirrored_publication(self.repo, self.slug)
        public_flags_before = {
            key: context["public_book"].get(key)
            for key in ("audio_enabled", "audiobook_enabled")
        }
        active = context["public_book"]["audiobook_active_release"][
            "active_release_descriptor_sha256"
        ]

        dry_run_snapshot = self._snapshot()
        dry_run = manager.deactivate_release(self.repo, self.slug)
        self.assertEqual(dry_run["status"], "RELEASE_DEACTIVATION_VALIDATED")
        self.assertEqual(dry_run_snapshot, self._snapshot())

        result = manager.deactivate_release(self.repo, self.slug, apply=True)
        self.assertEqual(result["status"], "RELEASE_DEACTIVATED")
        self.assertFalse(result["audio_approval_flags_changed"])
        status = manager.release_status(self.repo, self.slug)
        self.assertEqual(status["status"], "RELEASE_POINTER_INACTIVE")
        self.assertEqual(status["release_state_status"], "INACTIVE")
        self.assertEqual(status["blockers"], ["ACTIVE_RELEASE_STATE_INACTIVE"])
        context = manager.load_mirrored_publication(self.repo, self.slug)
        self.assertEqual(
            {
                key: context["public_book"].get(key)
                for key in ("audio_enabled", "audiobook_enabled")
            },
            public_flags_before,
        )
        before = self._snapshot()
        for action in (
            lambda: manager.set_rollout(self.repo, self.slug, 0, apply=True),
            lambda: manager.rollback_release(
                self.repo,
                self.slug,
                "previous",
                apply=True,
            ),
            lambda: self._stage("4"),
        ):
            with self.assertRaisesRegex(
                manager.ReleasePointerError,
                "explicitly reactivated",
            ):
                action()
            self.assertEqual(before, self._snapshot())

        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "current approved, checksum-verified public audio truth",
        ):
            manager.reactivate_release(self.repo, self.slug, apply=True)
        self.assertEqual(before, self._snapshot())

        self._prepare_package_audio_approval()
        approval_snapshot = manager.load_mirrored_publication(
            self.repo,
            self.slug,
        )["approval_evidence"]
        reactivated = manager.reactivate_release(
            self.repo,
            self.slug,
            apply=True,
        )
        self.assertEqual(reactivated["status"], "RELEASE_REACTIVATED")
        self.assertFalse(reactivated["audio_approval_flags_changed"])
        context = manager.load_mirrored_publication(self.repo, self.slug)
        self.assertEqual(
            context["public_book"]["audiobook_active_release"]["status"],
            "ACTIVE",
        )
        self.assertEqual(
            context["public_book"]["audiobook_active_release"][
                "active_release_descriptor_sha256"
            ],
            active,
        )
        self.assertEqual(context["approval_evidence"], approval_snapshot)

        already_active = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "already active",
        ):
            manager.reactivate_release(self.repo, self.slug, apply=True)
        self.assertEqual(already_active, self._snapshot())

    def test_reactivate_rejects_tampered_release_evidence(self) -> None:
        self._stage("3")
        manager.set_rollout(self.repo, self.slug, 100, apply=True)
        manager.deactivate_release(self.repo, self.slug, apply=True)
        self._prepare_package_audio_approval()
        for publication in manager.publication_dirs(self.repo, self.slug):
            public_book = manager.read_json(publication / "public_book.json")
            descriptor = public_book["audiobook_active_release"][
                "active_release_descriptor_sha256"
            ]
            public_book["audiobook_package_release_evidence"][descriptor][
                "release_eligible"
            ] = False
            self._write(publication / "public_book.json", public_book)
            reader_manifest = manager.read_json(
                publication / "reader_manifest.json"
            )
            reader_manifest["audiobook_package_release_evidence"][descriptor][
                "release_eligible"
            ] = False
            self._write(publication / "reader_manifest.json", reader_manifest)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "not bound to release-eligible",
        ):
            manager.reactivate_release(self.repo, self.slug, apply=True)
        self.assertEqual(before, self._snapshot())

    def test_release_descriptor_with_blockers_cannot_be_staged(self) -> None:
        release_descriptor = self._release_descriptor("3")
        release_descriptor["known_release_blockers"] = ["ASR_REVALIDATION_REQUIRED"]
        package = self._package("3", release_descriptor)
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "known release blockers",
        ):
            self._invoke_stage(package, release_descriptor)
        self.assertEqual(before, self._snapshot())

        no_candidate_evidence = self._release_descriptor("4")
        no_candidate_evidence.pop("release_candidate_evidence")
        package_without_evidence = self._package("4", no_candidate_evidence)
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "lacks passing release-candidate evidence",
        ):
            self._invoke_stage(package_without_evidence, no_candidate_evidence)
        self.assertEqual(before, self._snapshot())

    def test_release_manifest_receipts_fail_closed(self) -> None:
        package = self._package("3")
        release_descriptor = self._release_descriptor("3")
        manifest_primary, manifest_replica, manifest_sha256, manifest_size = (
            self._release_manifest_receipts(package)
        )
        before = self._snapshot()

        wrong_hash = copy.deepcopy(manifest_primary)
        wrong_hash["objects"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "does not match the finalized manifest",
        ):
            self._invoke_stage(
                package,
                release_descriptor,
                manifest_primary=wrong_hash,
                manifest_replica=manifest_replica,
                manifest_sha256=manifest_sha256,
                manifest_size=manifest_size,
            )
        self.assertEqual(before, self._snapshot())

        private_manifest = copy.deepcopy(manifest_primary)
        private_manifest["receipt_role"] = "private_qa_staging"
        private_manifest["release_eligible"] = False
        private_manifest["store"]["role"] = "private_qa_staging"
        private_manifest["store"]["release_eligible"] = False
        with self.assertRaisesRegex(manager.ReleasePointerError, "receipt role is invalid"):
            self._invoke_stage(
                package,
                release_descriptor,
                manifest_primary=private_manifest,
                manifest_replica=manifest_replica,
            )
        self.assertEqual(before, self._snapshot())

        same_identity = copy.deepcopy(manifest_replica)
        same_identity["objects"][0]["store"] = "prod"
        same_identity["objects"][0]["bucket"] = "prod-bucket"
        same_identity["store"] = copy.deepcopy(manifest_primary["store"])
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "canonical dr store|not independent",
        ):
            self._invoke_stage(
                package,
                release_descriptor,
                manifest_primary=manifest_primary,
                manifest_replica=same_identity,
            )
        self.assertEqual(before, self._snapshot())

    def test_arbitrary_legacy_descriptor_is_rejected(self) -> None:
        package = self._package("3")
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "not bound to controlled truth",
        ):
            self._invoke_stage(
                package,
                self._release_descriptor("3"),
                legacy_descriptor="8" * 64,
            )
        self.assertEqual(before, self._snapshot())

        for publication in manager.publication_dirs(self.repo, self.slug):
            public_book = manager.read_json(publication / "public_book.json")
            public_book.pop("audiobook_legacy_release_descriptor_sha256")
            self._write(publication / "public_book.json", public_book)
            self._refresh_checksums(publication)
        missing_controlled_legacy = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "pre-existing controlled legacy release descriptor",
        ):
            self._invoke_stage(
                package,
                self._release_descriptor("3"),
                legacy_descriptor=self.legacy,
            )
        self.assertEqual(missing_controlled_legacy, self._snapshot())

    def test_status_is_validated_and_read_only(self) -> None:
        self._stage()
        before = self._snapshot()
        result = manager.release_status(self.repo, self.slug)
        self.assertEqual(result["status"], "RELEASE_POINTER_VALID")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(
            result["candidate_release_descriptor_sha256"],
            self._package("3")["release_descriptor_sha256"],
        )
        self.assertEqual(result["rollout"]["percentage"], 0)
        self.assertTrue(
            result["package_presence"][
                self._package("3")["release_descriptor_sha256"]
            ]
        )
        self.assertEqual(before, self._snapshot())

    def test_stale_release_plan_cannot_overwrite_newer_catalog_state(self) -> None:
        self._stage()
        context = manager.load_mirrored_publication(self.repo, self.slug)
        managed = {
            field: copy.deepcopy(context["public_book"][field])
            for field in manager.MANAGED_FIELDS
        }
        fingerprint = manager.publication_fingerprint(context)
        for publication in manager.publication_dirs(self.repo, self.slug):
            changed = manager.read_json(publication / "public_book.json")
            changed["title"] = "Concurrent catalog update"
            self._write(publication / "public_book.json", changed)
            self._refresh_checksums(publication)
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "changed during release planning",
        ):
            manager.mutate_mirrors(
                self.repo,
                self.slug,
                managed,
                generated_at="2026-07-29T13:00:00Z",
                apply=True,
                expected_fingerprint=fingerprint,
            )
        self.assertEqual(before, self._snapshot())

    def test_checksum_stale_mirrored_truth_cannot_be_mutated(self) -> None:
        for publication in manager.publication_dirs(self.repo, self.slug):
            source = manager.read_json(publication / "source_evidence.json")
            source["audit_note"] = "tampered without checksum refresh"
            self._write(publication / "source_evidence.json", source)
        before = self._snapshot()
        with self.assertRaisesRegex(
            manager.ReleasePointerError,
            "checksum is stale or missing: source_evidence.json",
        ):
            self._stage()
        self.assertEqual(before, self._snapshot())

    def test_diverged_mirrors_fail_before_any_mutation(self) -> None:
        publications = manager.publication_dirs(self.repo, self.slug)
        changed = manager.read_json(publications[1] / "public_book.json")
        changed["title"] = "Diverged"
        self._write(publications[1] / "public_book.json", changed)
        before = self._snapshot()
        package = self._package("3")
        primary, replica = self._receipts(package)
        manifest_primary, manifest_replica, manifest_sha256, manifest_size = (
            self._release_manifest_receipts(package)
        )
        with self.assertRaisesRegex(manager.ReleasePointerError, "mirrors diverge"):
            manager.stage_candidate(
                self.repo,
                self.slug,
                package,
                self._release_descriptor("3"),
                primary,
                replica,
                manifest_primary,
                manifest_replica,
                rollout_salt="sticky",
                legacy_descriptor=self.legacy,
                expected_manuscript_sha256=self.manuscript,
                release_manifest_sha256=manifest_sha256,
                release_manifest_size_bytes=manifest_size,
                apply=True,
                primary_receipt_sha256="e" * 64,
                replica_receipt_sha256="f" * 64,
                primary_release_manifest_receipt_sha256="7" * 64,
                replica_release_manifest_receipt_sha256="8" * 64,
            )
        self.assertEqual(before, self._snapshot())


if __name__ == "__main__":
    unittest.main()
