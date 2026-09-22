#!/usr/bin/env python3
"""Regression coverage for the local-only canonical-page seed release hold."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("seed_uat_canonical_pages.py")
SPEC = importlib.util.spec_from_file_location("seed_uat_canonical_pages", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CanonicalPageSeedReleaseHoldTests(unittest.TestCase):
    def write_contracts(self, root: Path, frontend: dict, backend: dict) -> None:
        (root / "data").mkdir(parents=True)
        (root / "backend" / "data").mkdir(parents=True)
        (root / "data" / "controlled_launch.json").write_text(json.dumps(frontend), encoding="utf-8")
        (root / "backend" / "data" / "controlled_launch.json").write_text(json.dumps(backend), encoding="utf-8")

    def test_all_title_hold_exits_before_admin_login(self) -> None:
        contract = {"public_reader_exposure_enabled": False, "live_approved_slugs": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_contracts(root, contract, contract)
            environment = {
                "UAT_API_BASE_URL": "http://127.0.0.1:18007/api",
                "ADMIN_EMAIL": "local-admin@example.invalid",
                "ADMIN_PASSWORD": "not-used",
            }
            with patch.object(MODULE, "ROOT", root), patch.dict(os.environ, environment, clear=False), patch.object(MODULE, "request") as request:
                MODULE.main()
            request.assert_not_called()

    def test_divergent_contracts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_contracts(
                root,
                {"public_reader_exposure_enabled": False, "live_approved_slugs": []},
                {"public_reader_exposure_enabled": True, "live_approved_slugs": ["dracula"]},
            )
            with patch.object(MODULE, "ROOT", root):
                with self.assertRaisesRegex(SystemExit, "divergent controlled-launch contracts"):
                    MODULE.public_reader_release_is_held()

    def test_enabled_contract_does_not_skip_the_seed(self) -> None:
        contract = {"public_reader_exposure_enabled": True, "live_approved_slugs": ["dracula"]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_contracts(root, contract, contract)
            with patch.object(MODULE, "ROOT", root):
                self.assertFalse(MODULE.public_reader_release_is_held())


if __name__ == "__main__":
    unittest.main()
