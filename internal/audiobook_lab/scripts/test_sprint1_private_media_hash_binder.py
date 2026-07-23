#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("sprint1_private_media_hash_binder.py")
SPEC = importlib.util.spec_from_file_location("sprint1_private_media_hash_binder", SCRIPT)
assert SPEC and SPEC.loader
binder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(binder)


class ClosingBytesIO(io.BytesIO):
    pass


class FakeClient:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def get_object(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "Body": ClosingBytesIO(self.payload),
            "ContentLength": len(self.payload),
        }


class Sprint1PrivateMediaHashBinderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.private = self.root / "private-media"
        self.payload = b"exact retained private audio bytes"
        self.expected_hash = hashlib.sha256(self.payload).hexdigest()
        self.key = (
            "storage-containment/the-monkeys-paw/audio-a9ae5b339149aef9/"
            "the-monkeys-paw.mp3"
        )
        self.inventory_path = self.repo / "inventory.json"
        self.evidence_path = self.repo / "evidence.json"
        self.inventory_path.write_text(
            json.dumps(
                {
                    "object_versions": [
                        {
                            "key": self.key,
                            "version_id": "version-1",
                            "is_latest": True,
                            "delete_marker": False,
                            "size_bytes": len(self.payload),
                            "store": "private_audio",
                            "bucket": "private-bucket",
                            "classification": "PRESERVE_REFERENCED_NONLIVE",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.evidence_path.write_text(
            json.dumps(
                {
                    "slug": "the-monkeys-paw",
                    "title": "The Monkey's Paw",
                    "author": "W. W. Jacobs",
                    "repaired_full_candidate": {
                        "audio_sha256": self.expected_hash,
                        "source_sha256": "a" * 64,
                        "status": "BLOCKED_LISTENING_QA",
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def plan(self, **overrides):
        values = {
            "repo_root": self.repo,
            "inventory_path": self.inventory_path,
            "evidence_path": self.evidence_path,
            "slug": "the-monkeys-paw",
            "candidate_name": "repaired_full_candidate",
            "object_key": self.key,
            "expected_audio_sha256": self.expected_hash,
            "private_output_dir": self.private,
        }
        values.update(overrides)
        return binder.build_plan(**values)

    def test_preflight_is_network_free_and_exactly_bound(self) -> None:
        with patch.object(
            binder,
            "private_s3_client",
            side_effect=AssertionError("preflight must not create a client"),
        ):
            plan = self.plan()
        self.assertEqual("READY_FOR_AUTHORIZED_PRIVATE_DOWNLOAD", plan["status"])
        self.assertFalse(plan["network_call_performed"])
        self.assertEqual(self.expected_hash, plan["binding"]["expected_audio_sha256"])
        self.assertEqual("version-1", plan["binding"]["version_id"])

    def test_expected_hash_must_exactly_match_release_evidence(self) -> None:
        plan = self.plan(expected_audio_sha256="b" * 64)
        self.assertEqual("BLOCKED_PREFLIGHT", plan["status"])
        self.assertIn(
            "Command-line expected audio SHA-256 does not exactly match release evidence",
            plan["blockers"],
        )

    def test_object_key_must_be_exact_retained_private_version(self) -> None:
        plan = self.plan(object_key=self.key + ".wrong")
        self.assertEqual("BLOCKED_PREFLIGHT", plan["status"])
        self.assertIn("matched 0", " ".join(plan["blockers"]))

    def test_output_must_be_outside_repository(self) -> None:
        plan = self.plan(private_output_dir=self.repo / "frontend/public/audio")
        self.assertEqual("BLOCKED_PREFLIGHT", plan["status"])
        self.assertIn("outside the repository", " ".join(plan["blockers"]))

    def test_exact_match_writes_private_hash_bound_file(self) -> None:
        plan = self.plan()
        client = FakeClient(self.payload)
        result = binder.download_and_bind(plan, client)
        self.assertEqual("BOUND_EXACT_PRIVATE_CANDIDATE", result["status"])
        self.assertEqual(self.expected_hash, result["actual_audio_sha256"])
        bound = Path(result["bound_private_path"])
        self.assertTrue(bound.is_file())
        self.assertEqual(self.payload, bound.read_bytes())
        self.assertEqual(
            [
                {
                    "Bucket": "private-bucket",
                    "Key": self.key,
                    "VersionId": "version-1",
                }
            ],
            client.calls,
        )
        self.assertFalse(result["upload_performed"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["release_gate_mutated"])
        self.assertFalse(result["paid_tts_lock_read_or_mutated"])

    def test_hash_mismatch_is_unbound_and_leaves_no_media(self) -> None:
        plan = self.plan()
        result = binder.download_and_bind(plan, FakeClient(b"wrong bytes"))
        self.assertEqual("BLOCKED_UNBOUND", result["status"])
        self.assertIn("DOWNLOADED_AUDIO_SHA256_MISMATCH", result["blockers"])
        self.assertEqual("", result["bound_private_path"])
        self.assertEqual([], list(self.private.glob("*.mp3")))

    def test_execute_stops_before_network_without_explicit_approval(self) -> None:
        report = self.root / "report.json"
        args = [
            "--mode",
            "execute",
            "--repo-root",
            str(self.repo),
            "--inventory",
            str(self.inventory_path),
            "--release-evidence",
            str(self.evidence_path),
            "--slug",
            "the-monkeys-paw",
            "--candidate",
            "repaired_full_candidate",
            "--object-key",
            self.key,
            "--expected-audio-sha256",
            self.expected_hash,
            "--private-output-dir",
            str(self.private),
            "--report",
            str(report),
            "--expected-plan-sha256",
            self.plan()["plan_sha256"],
        ]
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(
                binder,
                "private_s3_client",
                side_effect=AssertionError("blocked execution must not create a client"),
            ),
        ):
            result = binder.main(args)
        self.assertEqual(2, result)
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual("BLOCKED_BEFORE_NETWORK", payload["status"])
        self.assertFalse(payload["network_call_performed"])
        self.assertIn(binder.APPROVAL_ENV, " ".join(payload["blockers"]))

    def test_preflight_prints_replayable_plan_bound_command(self) -> None:
        args = binder.parse_args(
            [
                "--repo-root",
                str(self.repo),
                "--inventory",
                str(self.inventory_path),
                "--release-evidence",
                str(self.evidence_path),
                "--slug",
                "the-monkeys-paw",
                "--candidate",
                "repaired_full_candidate",
                "--object-key",
                self.key,
                "--expected-audio-sha256",
                self.expected_hash,
                "--private-output-dir",
                str(self.private),
            ]
        )
        plan = self.plan()
        command = binder.exact_execute_command(
            script_path=SCRIPT,
            args=args,
            plan_sha256=plan["plan_sha256"],
        )
        self.assertIn(f"{binder.APPROVAL_ENV}=true", command)
        self.assertIn("--expected-plan-sha256", command)
        self.assertIn(plan["plan_sha256"], command)
        self.assertIn(self.key, command)


if __name__ == "__main__":
    unittest.main()
