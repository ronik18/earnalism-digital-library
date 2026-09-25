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

ACCESS = MODULE.ACCESS_COPY


def page(*, title: str, description: str, h1: str, canonical: str, robots: str = "index,follow", body: str = "", links: str = "") -> str:
    return f"""<!doctype html><html><head><title>{title}</title><meta name='description' content='{description}'><meta name='robots' content='{robots}'><link rel='canonical' href='{canonical}'></head><body><main><h1>{h1}</h1><div>{body}</div>{links}</main></body></html>"""


class StaticSeoCanaryTests(unittest.TestCase):
    def inspect(self, route: str, html: str, status: int = 200):
        return MODULE.inspect_route(route, MODULE.ROUTES[route], status, {}, html, "https://theearnalism.com" + route)

    def test_current_approved_book_html_passes(self) -> None:
        html = page(title="A Ghost Story by Mark Twain | The Earnalism", description="A Ghost Story reader-ready edition. " + ACCESS, h1="A Ghost Story by <em>Mark Twain</em>", canonical="https://theearnalism.com/book/a-ghost-story", body=ACCESS + " Read the 3-page preview", links="<a href='/reader/a-ghost-story'>Read the 3-page preview</a>")
        html = html.replace("</head>", '<script type="application/ld+json">{"isAccessibleForFree":false}</script></head>')
        self.assertEqual(self.inspect("/book/a-ghost-story", html)["result"], "PASS")

    def test_current_approved_pricing_html_passes(self) -> None:
        html = page(title="Reading Passes | The Earnalism", description="Reading Passes and paid checkout are unavailable in this launch.", h1="Reading Passes", canonical="https://theearnalism.com/pricing", robots="noindex,follow", body="Paid checkout is unavailable.")
        self.assertEqual(self.inspect("/pricing", html)["result"], "PASS")

    def test_obsolete_and_unsafe_html_fails(self) -> None:
        html = page(title="Earnalism | Bengali and English Classics", description="Chapter 1 free", h1="A library made for lingering", canonical="https://theearnalism.com/", body="Free audiobook preview https://storage.example/audio.mp3")
        failures = self.inspect("/book/a-ghost-story", html)["failures"]
        self.assertTrue(any("forbidden phrase" in failure for failure in failures))
        self.assertTrue(any("generic Home" in failure for failure in failures))
        self.assertTrue(any("raw provider" in failure for failure in failures))
        self.assertTrue(any("wrong canonical" in failure for failure in failures))

    def test_safe_markup_variation_passes(self) -> None:
        html = page(title="A Ghost Story by Mark Twain &amp; The Earnalism", description="A Ghost Story reader edition &amp; " + ACCESS, h1="A Ghost Story <span>by Mark Twain</span>", canonical="https://theearnalism.com/book/a-ghost-story?ignored=value", body=ACCESS, links="<a href='/reader/a-ghost-story'>Read the 3-page preview</a>")
        html = html.replace("</head>", '<script type="application/ld+json">{"isAccessibleForFree":false}</script></head>')
        self.assertEqual(self.inspect("/book/a-ghost-story", html)["result"], "PASS")

    def test_full_free_book_metadata_is_rejected(self) -> None:
        html = page(title="A Ghost Story by Mark Twain | The Earnalism", description="A Ghost Story reader-ready edition. " + ACCESS, h1="A Ghost Story by Mark Twain", canonical="https://theearnalism.com/book/a-ghost-story", body=ACCESS + " Read the complete edition free", links="<a href='/reader/a-ghost-story'>Read the complete edition free</a>")
        html = html.replace("</head>", '<script type="application/ld+json">{"isAccessibleForFree":true}</script></head>')
        failures = self.inspect("/book/a-ghost-story", html)["failures"]
        self.assertTrue(any("three-page preview" in failure for failure in failures))
        self.assertTrue(any("full access unavailable" in failure for failure in failures))

    def test_missing_route_identity_or_access_contract_fails(self) -> None:
        html = page(title="The Earnalism", description="Available now", h1="Choose time", canonical="https://theearnalism.com/pricing", body="A quiet digital library.")
        failures = self.inspect("/pricing", html)["failures"]
        self.assertTrue(any("disabled-checkout" in failure for failure in failures))
        self.assertTrue(any("route-specific" in failure for failure in failures))

    def test_reader_requires_noindex_but_keeps_access_contract(self) -> None:
        html = page(title="Read A Ghost Story | The Earnalism Reader", description=ACCESS, h1="Read A Ghost Story", canonical="https://theearnalism.com/book/a-ghost-story", robots="noindex,follow", body=ACCESS)
        self.assertEqual(self.inspect("/reader/a-ghost-story", html)["result"], "PASS")

    def test_held_routes_require_404(self) -> None:
        self.assertEqual(self.inspect("/book/dracula", "", status=404)["result"], "PASS")
        self.assertEqual(self.inspect("/reader/yugalanguriya", "", status=200)["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
