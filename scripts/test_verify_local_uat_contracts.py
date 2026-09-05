#!/usr/bin/env python3
"""Synthetic fail-closed tests for the local System UAT reader contracts."""
from __future__ import annotations

import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("verify_local_uat_contracts.py")
SPEC = importlib.util.spec_from_file_location("local_uat_contracts", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LocalUatContractTests(unittest.TestCase):
    def setUp(self) -> None:
        MODULE.FRONTEND = "http://127.0.0.1:13000"
        MODULE.API = "http://127.0.0.1:18000/api"
        self.manifest = {
            "canonical_pages": {
                "schema_version": "canonical-pages-v1",
                "preview_policy": {"unit": "canonical_page", "public_limit": 3, "enforced_by": "server", "ready": True},
                "pages": [{"number": 1}, {"number": 2}, {"number": 3}],
            }
        }

    def responses(self, manifest: dict | None = None, book: dict | None = None):
        manifest = manifest or self.manifest
        book = book or {"audio_enabled": False, "audiobook_enabled": False, "audiobook": None, "audiobook_assets": {}, "audio_url": ""}
        def fake_get(url: str, headers: dict[str, str] | None = None):
            if url.endswith("/product/patterned-wrap-dress"):
                return 410, {"X-Robots-Tag": "noindex, nofollow, noarchive"}, None
            if url.endswith("/not-a-real-route"):
                return 404, {"X-Robots-Tag": "noindex, nofollow, noarchive"}, None
            if url.endswith("/payments/packs"):
                return 200, {"Access-Control-Allow-Origin": MODULE.FRONTEND}, {}
            if url.endswith("/books/dracula"):
                return 200, {}, book
            if url.endswith("/reader/book/dracula/manifest"):
                return 200, {}, manifest
            if url.endswith("/pages/4"):
                return 401, {}, {"detail": {"code": "AUTH_REQUIRED"}}
            if url.endswith("/pages/999999") or url.endswith("/audiobook"):
                return 404, {}, None
            if "/pages/" in url:
                return 200, {}, {"content": "cleared public page"}
            return 200, {}, {}
        return fake_get

    def assert_rejected(self, manifest: dict | None = None, book: dict | None = None) -> None:
        with patch.object(MODULE, "get", self.responses(manifest, book)):
            with self.assertRaises(SystemExit):
                MODULE.main()

    def test_accepts_complete_synthetic_contract(self) -> None:
        with patch.object(MODULE, "get", self.responses()):
            MODULE.main()

    def test_rejects_empty_schema_wrong_unit_limit_enforcement_and_readiness(self) -> None:
        for key, value in (
            ("schema_version", ""), ("unit", "paragraph"), ("public_limit", 4),
            ("enforced_by", "client"), ("ready", False),
        ):
            manifest = deepcopy(self.manifest)
            target = manifest["canonical_pages"] if key == "schema_version" else manifest["canonical_pages"]["preview_policy"]
            target[key] = value
            self.assert_rejected(manifest)

    def test_rejects_protected_metadata_and_audio_leaks(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["canonical_pages"]["pages"][0]["content"] = "protected text"
        self.assert_rejected(manifest)
        self.assert_rejected(book={"audio_enabled": True, "audiobook_enabled": False, "audiobook": None, "audiobook_assets": {}, "audio_url": ""})


if __name__ == "__main__":
    unittest.main()
