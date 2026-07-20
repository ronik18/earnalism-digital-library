#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("b2_live_audio_cleanup.py")
SPEC = importlib.util.spec_from_file_location("b2_live_audio_cleanup", SCRIPT)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)


class FakeClient:
    def __init__(self) -> None:
        self.deleted: list[dict] = []

    def delete_object(self, **kwargs):
        self.deleted.append(kwargs)
        return {}


class B2LiveAudioCleanupTests(unittest.TestCase):
    def test_audiobook_scope_includes_audio_and_package_sidecars(self) -> None:
        self.assertTrue(cleanup.is_audiobook_scoped("legacy/example.wav"))
        self.assertTrue(cleanup.is_audiobook_scoped("storage-containment/title/sidecar/meta.json"))
        self.assertTrue(cleanup.is_audiobook_scoped("earnalism/audiobooks/title/title.vtt"))
        self.assertFalse(cleanup.is_audiobook_scoped("storage-containment-capacity-probe/value"))

    def test_catalog_truth_builds_exact_live_allowlist(self) -> None:
        repo_root = SCRIPT.resolve().parents[3]
        stores = [
            {
                "name": "primary",
                "endpoint": "https://s3.us-west-004.backblazeb2.com",
                "region": "test",
                "bucket": "earnalism-audiobooks",
                "access_key_id": "test",
                "secret_access_key": "test",
            },
            {
                "name": "private_audio",
                "endpoint": "https://s3.us-west-004.backblazeb2.com",
                "region": "test",
                "bucket": "earnalism-private-qa-audio",
                "access_key_id": "test",
                "secret_access_key": "test",
            },
        ]
        assets, blockers = cleanup.load_live_assets(repo_root, stores)
        self.assertEqual([], blockers)
        self.assertEqual(20, len(assets))
        self.assertEqual(
            {"book-2b9853ec52", "a-ghost-story", "sredni-vashtar", "the-open-window"},
            {item["slug"] for item in assets},
        )
        self.assertEqual({"mp3", "timestamps", "vtt", "chapters", "meta"}, {item["asset"] for item in assets})

    def test_execute_requires_explicit_approval(self) -> None:
        report = {
            "blockers": [],
            "deletion_authorized_by_inventory": True,
            "delete_plan_sha256": "plan",
            "delete_plan": [],
        }
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "EARNALISM_APPROVE_B2_LIVE_ONLY_CLEANUP"):
                cleanup.execute_deletion(report, {}, "plan")

    def test_execute_requires_exact_fresh_plan_digest(self) -> None:
        report = {
            "blockers": [],
            "deletion_authorized_by_inventory": True,
            "delete_plan_sha256": "plan",
            "delete_plan": [],
        }
        with patch.dict(os.environ, {"EARNALISM_APPROVE_B2_LIVE_ONLY_CLEANUP": "true"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                cleanup.execute_deletion(report, {}, "stale")

    def test_execute_deletes_only_exact_versions(self) -> None:
        client = FakeClient()
        item = {
            "store": "primary",
            "bucket": "bucket",
            "key": "earnalism/audiobooks/old/old.mp3",
            "version_id": "version-1",
            "delete_marker": False,
            "size_bytes": 99,
            "classification": "DELETE_CANDIDATE_NONLIVE_PUBLIC_ORIGIN",
        }
        report = {
            "blockers": [],
            "deletion_authorized_by_inventory": True,
            "delete_plan_sha256": "plan",
            "delete_plan": [item],
        }
        with patch.dict(os.environ, {"EARNALISM_APPROVE_B2_LIVE_ONLY_CLEANUP": "true"}, clear=True):
            result = cleanup.execute_deletion(report, {"primary": client}, "plan")
        self.assertEqual("PASS", result["status"])
        self.assertEqual(99, result["deleted_bytes"])
        self.assertEqual(
            [{"Bucket": "bucket", "Key": "earnalism/audiobooks/old/old.mp3", "VersionId": "version-1"}],
            client.deleted,
        )


if __name__ == "__main__":
    unittest.main()
