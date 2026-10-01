#!/usr/bin/env python3
"""Focused contracts for the semantic static SEO production canary."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import json
import unittest
from unittest.mock import patch
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

    def test_sherlock_text_reader_book_and_reader_routes_have_release_safe_metadata(self) -> None:
        book = page(title="The Adventures of Sherlock Holmes | The Earnalism", description="The Adventures of Sherlock Holmes reader edition. " + ACCESS, h1="The Adventures of Sherlock Holmes", canonical="https://theearnalism.com/book/the-adventures-of-sherlock-holmes", body=ACCESS, links="<a href='/reader/the-adventures-of-sherlock-holmes'>Read the 3-page preview</a>")
        book = book.replace("</head>", '<script type="application/ld+json">{"isAccessibleForFree":false}</script></head>')
        reader = page(title="Read The Adventures of Sherlock Holmes | The Earnalism Reader", description=ACCESS, h1="Read The Adventures of Sherlock Holmes", canonical="https://theearnalism.com/book/the-adventures-of-sherlock-holmes", robots="noindex,follow", body=ACCESS)
        self.assertEqual(self.inspect("/book/the-adventures-of-sherlock-holmes", book)["result"], "PASS")
        self.assertEqual(self.inspect("/reader/the-adventures-of-sherlock-holmes", reader)["result"], "PASS")

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
        self.assertEqual(self.inspect("/book/yugalanguriya", "", status=404)["result"], "PASS")
        self.assertEqual(self.inspect("/reader/yugalanguriya", "", status=200)["result"], "FAIL")

    def unavailable_html(self, *, body="", links=""):
        return page(title="Dracula unavailable | The Earnalism", description="Dracula is not currently available as a public Earnalism release.", h1="Dracula is not currently available.", canonical="https://theearnalism.com/book/dracula", robots="noindex,nofollow", body="This title is not part of the current public release. No book text, reader session, or audio is available from this page. " + body, links=links)

    def test_approved_historical_recovery_page_passes_without_releasing_a_title(self):
        html = self.unavailable_html(links="<a href='/library'>Browse Library</a><a href='/contact?interest=dracula'>Ask about title</a>")
        self.assertEqual(self.inspect("/book/dracula", html)["result"], "PASS")
        self.assertEqual(self.inspect("/reader/dracula", html)["result"], "PASS")
        self.assertEqual(self.inspect("/listener/dracula", html)["result"], "PASS")

    def test_dracula_browser_routes_are_reachable_but_protected_reader_access_is_denied(self):
        html = self.unavailable_html(links="<a href='/library'>Browse Library</a>")
        self.assertEqual(self.inspect("/book/dracula", html, status=200)["result"], "PASS")
        self.assertEqual(self.inspect("/reader/dracula", html, status=200)["result"], "PASS")

        route = "/api/reader/book/dracula/manifest"
        policy = MODULE.PROTECTED_API_CHECKS[route]
        denied = MODULE.inspect_protected_api(
            route,
            policy,
            451,
            {"detail": {"code": "RELEASE_RIGHTS_DENIED"}},
            "https://theearnalism.com" + route,
        )
        self.assertEqual(denied["result"], "PASS")

    def test_protected_api_contract_does_not_globally_allow_451_or_503(self):
        route = "/api/reader/book/dracula/manifest"
        policy = MODULE.PROTECTED_API_CHECKS[route]
        for status, payload in [
            (200, {"detail": {"code": "RELEASE_RIGHTS_DENIED"}}),
            (451, {"detail": {"code": "COUNTRY_NOT_AUTHORIZED"}}),
            (503, {"detail": {"code": "SEGMENTS_NOT_READY"}}),
        ]:
            with self.subTest(status=status, payload=payload):
                result = MODULE.inspect_protected_api(route, policy, status, payload, "https://theearnalism.com" + route)
                self.assertEqual(result["result"], "FAIL")

    def test_sherlock_and_canterville_segment_readiness_is_endpoint_scoped(self):
        expected = {
            "/api/reading-pass/books/the-adventures-of-sherlock-holmes/manifest",
            "/api/reading-pass/books/the-canterville-ghost/manifest",
        }
        self.assertEqual(set(MODULE.PROTECTED_API_CHECKS) - {"/api/reader/book/dracula/manifest"}, expected)
        for route in expected:
            result = MODULE.inspect_protected_api(
                route,
                MODULE.PROTECTED_API_CHECKS[route],
                503,
                {"detail": {"code": "SEGMENTS_NOT_READY"}},
                "https://theearnalism.com" + route,
            )
            self.assertEqual(result["result"], "PASS")

    def test_overall_canary_fails_if_one_scoped_api_contract_fails(self):
        with patch.object(MODULE, "fetch_raw_html", return_value=(200, {}, "", "https://theearnalism.com/")), patch.object(
            MODULE, "inspect_route", return_value={"result": "PASS"}
        ), patch.object(MODULE, "fetch_protected_api", side_effect=[
            (451, {"detail": {"code": "RELEASE_RIGHTS_DENIED"}}, "https://theearnalism.com/api/reader/book/dracula/manifest"),
            (503, {"detail": {"code": "SEGMENTS_NOT_READY"}}, "https://theearnalism.com/api/reading-pass/books/the-adventures-of-sherlock-holmes/manifest"),
            (200, {"detail": {"code": "SEGMENTS_NOT_READY"}}, "https://theearnalism.com/api/reading-pass/books/the-canterville-ghost/manifest"),
        ]):
            report = MODULE.run("https://theearnalism.com", 1)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual([row["result"] for row in report["protected_apis"]], ["PASS", "PASS", "FAIL"])

    def test_genuine_missing_routes_still_require_404(self):
        self.assertEqual(self.inspect("/book/yugalanguriya", "", status=404)["result"], "PASS")
        self.assertEqual(self.inspect("/book/yugalanguriya", "", status=451)["result"], "FAIL")

    def test_historical_home_fallback_and_released_access_copy_are_rejected(self):
        html = page(title="Earnalism | Classics", description=ACCESS, h1="A library made for lingering", canonical="https://theearnalism.com/", body=ACCESS)
        self.assertEqual(self.inspect("/book/dracula", html)["result"], "FAIL")
        self.assertEqual(self.inspect("/reader/dracula", self.unavailable_html(body=ACCESS))["result"], "FAIL")

    def test_historical_controls_media_schema_and_non_recovery_links_are_rejected(self):
        unsafe = ["<button>Read</button>", "<audio src='https://media.example/audio.mp3'></audio>", '<script type="application/ld+json">{"@type":"Book","isAccessibleForFree":true}</script>', "<a href='/reader/dracula'>Open Reader</a>"]
        for content in unsafe:
            with self.subTest(content=content):
                self.assertEqual(self.inspect("/book/dracula", self.unavailable_html(body=content))["result"], "FAIL")

    def test_historical_routes_require_exact_identity_and_noindex(self):
        html = self.unavailable_html()
        for unsafe in [html.replace("noindex,nofollow", "index,follow"), html.replace("https://theearnalism.com/book/dracula", "https://theearnalism.com/"), html.replace("Dracula", "Another title")]:
            self.assertEqual(self.inspect("/book/dracula", unsafe)["result"], "FAIL")


class HistoricalUnavailableSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="historical-unavailable-snapshots-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source_root = SCRIPT.parent.parent
        files = ["frontend/scripts/generate-static-seo-snapshots.mjs", "frontend/scripts/verify-static-seo-snapshots.mjs", "frontend/scripts/unavailable-title-routes.mjs", "frontend/static-seo/controlled-publication-public.json", "frontend/static-seo/editorial-public.json", "frontend/public/index.html", "data/controlled_launch.json"]
        for relative in files:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, target)
        self.generate()

    def generate(self):
        subprocess.run(["node", str(self.root / "frontend/scripts/generate-static-seo-snapshots.mjs")], check=True, capture_output=True, text=True, timeout=30)

    def verify(self):
        return subprocess.run(["node", str(self.root / "frontend/scripts/verify-static-seo-snapshots.mjs")], capture_output=True, text=True, timeout=30)

    def test_real_generator_and_verifier_produce_six_safe_unavailable_snapshots(self):
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.root / "frontend/build/static-seo-snapshot-manifest.json").read_text())
        held = [r for r in manifest["routes"] if r["snapshot_classification"] == "RELEASE_HELD"]
        self.assertEqual(len(held), 6)
        for entry in held:
            route = entry["route"]
            html = (self.root / "frontend/build" / route.lstrip("/") / "index.html").read_text()
            report = MODULE.inspect_route(route, MODULE.ROUTES[route], 200, {}, html, "https://theearnalism.com" + route)
            self.assertEqual(report["result"], "PASS", report)

    def test_first_matching_rewrite_uses_the_snapshot_and_preserves_old_app_rules(self):
        config = json.loads((SCRIPT.parent.parent / "frontend/vercel.json").read_text())
        for slug in ["dracula", "the-selfish-giant"]:
            for kind in ["book", "reader", "listener"]:
                route = "/" + kind + "/" + slug
                for source in [route, route + "/"]:
                    winning = next(r for r in config["rewrites"] if r["source"] == source)
                    self.assertEqual(winning["destination"], route + "/index.html")
                    self.assertIn({"source": source, "destination": "/index.html"}, config["rewrites"])
                self.assertTrue((self.root / "frontend/build" / route.lstrip("/") / "index.html").is_file())
        for kind in ["book", "reader", "listener"]:
            self.assertIn({"source": "/" + kind + "/:slug", "destination": "/api/not-found"}, config["rewrites"])

    def test_snapshot_tampering_cannot_pass_the_build_or_production_canary(self):
        target = self.root / "frontend/build/book/dracula/index.html"
        original = target.read_text()
        for html in [original.replace('name="robots" content="noindex,nofollow"', 'name="robots" content="index,follow"'), original.replace("</main>", '<a href="/reader/dracula">Read the 3-page preview</a></main>')]:
            target.write_text(html)
            self.assertNotEqual(self.verify().returncode, 0)
            self.assertEqual(MODULE.inspect_route("/book/dracula", MODULE.ROUTES["/book/dracula"], 200, {}, html, "https://theearnalism.com/book/dracula")["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
