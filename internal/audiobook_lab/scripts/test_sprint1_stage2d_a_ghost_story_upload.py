#!/usr/bin/env python3
"""Focused tests for the Stage 2D release-safe upload wrapper."""

from __future__ import annotations

import importlib.util
import os
import unittest
from contextlib import contextmanager
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_stage2d_a_ghost_story_upload.py")
SPEC = importlib.util.spec_from_file_location("stage2d_upload", SCRIPT)
stage2d = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(stage2d)


@contextmanager
def temporary_env(**updates):
    before = {name: os.environ.get(name) for name in updates}
    try:
        for name, value in updates.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class Stage2DUploadTests(unittest.TestCase):
    def complete_env(self) -> dict[str, str]:
        return {
            **stage2d.EXPECTED_ENV,
            **{name: "set" for name in stage2d.REQUIRED_STORAGE_ENV},
        }

    def test_missing_upload_approval_blocks(self):
        env = self.complete_env()
        env["EARNALISM_APPROVE_STAGE2D_PUBLIC_UPLOAD"] = None
        with temporary_env(**env):
            self.assertIn(
                "EARNALISM_APPROVE_STAGE2D_PUBLIC_UPLOAD must equal true",
                stage2d.runtime_gate_errors(),
            )

    def test_missing_storage_key_blocks_before_upload(self):
        env = self.complete_env()
        env["B2_SECRET_ACCESS_KEY"] = None
        with temporary_env(**env):
            self.assertIn("B2_SECRET_ACCESS_KEY is required", stage2d.runtime_gate_errors())

    def test_complete_runtime_gates_pass(self):
        with temporary_env(**self.complete_env()):
            self.assertEqual(stage2d.runtime_gate_errors(), [])

    def test_lock_scope_is_narrow(self):
        payload = stage2d.acquired_lock_payload(
            {"status": "active", "current_holder": "none", "allowed_next_holders": []}
        )
        self.assertEqual(payload["current_holder"], "sprint1_publication_stage2d")
        self.assertEqual(payload["allowed_slugs"], ["a-ghost-story"])
        self.assertIn("no TTS", payload["approved_scope"])

    def test_preupload_evidence_is_not_public_release(self):
        payload = stage2d.preupload_qa({"status": "PASS"})
        self.assertTrue(payload["auto_approval_decision"])
        self.assertEqual(payload["audio_public_release"], "PENDING_VERIFIED_UPLOAD")
        self.assertEqual(payload["release_gates"]["endpoint_validation"], "PENDING")
        self.assertNotEqual(payload["quality_target_claimed"], "10_OF_10")


if __name__ == "__main__":
    unittest.main()
