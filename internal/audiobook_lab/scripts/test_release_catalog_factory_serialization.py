#!/usr/bin/env python3
"""Regression tests for paid-call and publication serialization defaults."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_catalog_factory import ReleaseCatalogFactory, parse_args


class ReleaseCatalogFactorySerializationTests(unittest.TestCase):
    def factory(self, temporary: str, *extra: str) -> ReleaseCatalogFactory:
        args = parse_args(
            [
                "--catalog-run-dir",
                str(Path(temporary) / "catalog"),
                "--dry-run",
                *extra,
            ]
        )
        return ReleaseCatalogFactory(args)

    def test_defaults_serialize_paid_tts_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            factory = self.factory(temporary)
        self.assertEqual(factory.args.max_paid_workers, 1)
        self.assertEqual(factory.args.max_metadata_workers, 1)
        self.assertEqual(factory.stage_limits["tts_queue"], 1)
        self.assertEqual(factory.stage_limits["metadata_publish_queue"], 1)

    def test_read_only_preparation_remains_parallel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            factory = self.factory(
                temporary,
                "--max-books-active",
                "8",
                "--max-preflight-workers",
                "8",
                "--max-cover-workers",
                "4",
                "--max-asr-workers",
                "4",
            )
        self.assertEqual(factory.stage_limits["inventory_queue"], 8)
        self.assertEqual(factory.stage_limits["manuscript_queue"], 8)
        self.assertEqual(factory.stage_limits["rights_metadata_preflight_queue"], 8)
        self.assertEqual(factory.stage_limits["cover_queue"], 4)
        self.assertEqual(factory.stage_limits["asr_sync_queue"], 4)
        self.assertEqual(factory.stage_limits["tts_queue"], 1)

    def test_explicit_parallel_paid_workers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "paid/provider TTS"):
                self.factory(temporary, "--max-paid-workers", "2")

    def test_parallel_metadata_is_rejected_when_publication_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "release mutations"):
                self.factory(
                    temporary,
                    "--publish-approved",
                    "--max-metadata-workers",
                    "2",
                )

    def test_zero_aliases_fail_safe_to_one_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            factory = self.factory(
                temporary,
                "--max-paid-workers",
                "0",
                "--max-metadata-workers",
                "0",
            )
        self.assertEqual(factory.stage_limits["tts_queue"], 1)
        self.assertEqual(factory.stage_limits["metadata_publish_queue"], 1)


if __name__ == "__main__":
    unittest.main()
