#!/usr/bin/env python3
"""Focused contracts for the semantic static SEO production canary."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("post_deploy_static_seo_canary.py")
SPEC = importlib.util.spec_from_file_location("static_seo_canary", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

ACCESS = "Read the first 3 pages free. Listening requires an active Reading Pass."


def page(*, title: str, description: str, h1: str, canonical: str, robots: str = "index,follow", body: str = "", links: str = "") -> str:
    return f"""<!doctype html><html><head><title>{title}</title><meta name='description' content='{description}'><meta name='robots' content='{robots}'><link rel='canonical' href='{canonical}'></head><body><main><h1>{h1}</h1><div>{body}</div>{links}</main></body></html>"""


class StaticSeoCanaryTests(unittest.TestCase):
    def inspect(self, route: str, html: str):
        return MODULE.inspect_route(route, MODULE.ROUTES[route], 200, {}, html, "https://theearnalism.com" + route)

    def test_current_approved_book_html_passes(self) -> None:
        html = page(title="Dracula by Bram Stoker | The Earnalism", description="Dracula reader-ready edition. " + ACCESS, h1="Dracula by <em>Bram Stoker</em>", canonical="https://theearnalism.com/book/dracula", body=ACCESS, links="<a href='/pricing'>View Reading Passes</a>")
        self.assertEqual(self.inspect("/book/dracula", html)["result"], "PASS")

    def test_current_approved_pricing_html_passes(self) -> None:
        html = page(title="Reading Passes | The Earnalism", description=ACCESS, h1="Choose time for deeper <span>reading</span>.", canonical="https://theearnalism.com/pricing", body=ACCESS + " Reading time is used only while you read.")
        self.assertEqual(self.inspect("/pricing?book=dracula", html)["result"], "PASS")

    def test_obsolete_and_unsafe_html_fails(self) -> None:
        html = page(title="Earnalism | Bengali and English Classics", description="Chapter 1 free", h1="A library made for lingering", canonical="https://theearnalism.com/", body="Free audiobook preview https://storage.example/audio.mp3")
        failures = self.inspect("/book/dracula", html)["failures"]
        self.assertTrue(any("forbidden phrase" in failure for failure in failures))
        self.assertTrue(any("generic Home" in failure for failure in failures))
        self.assertTrue(any("raw provider" in failure for failure in failures))
        self.assertTrue(any("wrong canonical" in failure for failure in failures))

    def test_safe_markup_variation_passes(self) -> None:
        html = page(title="Dracula by Bram Stoker &amp; The Earnalism", description="Dracula reader edition &amp; " + ACCESS, h1="Dracula <span>by Bram Stoker</span>", canonical="https://theearnalism.com/book/dracula?ignored=value", body="Read the first 3 pages free. <strong>Listening requires an active Reading Pass.</strong>", links="<a href='/pricing?source=book'>View&nbsp;Reading&nbsp;Passes</a>")
        self.assertEqual(self.inspect("/book/dracula", html)["result"], "PASS")

    def test_missing_route_identity_or_access_contract_fails(self) -> None:
        html = page(title="The Earnalism", description="Available now", h1="Choose time", canonical="https://theearnalism.com/pricing", body="A quiet digital library.")
        failures = self.inspect("/pricing?book=dracula", html)["failures"]
        self.assertTrue(any("missing approved" in failure for failure in failures))
        self.assertTrue(any("route-specific" in failure for failure in failures))

    def test_reader_requires_noindex_but_keeps_access_contract(self) -> None:
        html = page(title="Read Dracula | The Earnalism Reader", description=ACCESS, h1="Read Dracula", canonical="https://theearnalism.com/book/dracula", robots="noindex,follow", body=ACCESS)
        self.assertEqual(self.inspect("/reader/dracula", html)["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
