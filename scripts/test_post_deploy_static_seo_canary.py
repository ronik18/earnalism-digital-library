#!/usr/bin/env python3
"""Focused tests for the static SEO raw-HTML canary."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("post_deploy_static_seo_canary.py")
SPEC = importlib.util.spec_from_file_location("static_seo_canary", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StaticSeoCanaryTests(unittest.TestCase):
    def test_all_routes_accept_current_contract_copy(self) -> None:
        for route, policy in MODULE.ROUTES.items():
            html = " ".join(policy["required"])
            if policy["reader"]:
                html += '<meta name="robots" content="noindex,follow">'
            result = MODULE.inspect_route(route, policy, 200, {}, html, f"https://example.test{route}")
            self.assertEqual(result["result"], "PASS")

    def test_rejects_obsolete_copy_and_reader_indexing(self) -> None:
        policy = MODULE.ROUTES["/reader/dracula"]
        result = MODULE.inspect_route("/reader/dracula", policy, 200, {}, "first 3 canonical pages Get 7-Day Reading Pass", "https://example.test/reader/dracula")
        self.assertEqual(result["result"], "FAIL")
        self.assertTrue(any("forbidden phrase" in failure for failure in result["failures"]))
        self.assertTrue(any("noindex" in failure for failure in result["failures"]))


if __name__ == "__main__":
    unittest.main()
