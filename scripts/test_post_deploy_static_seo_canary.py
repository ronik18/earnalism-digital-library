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

    def inspect_unavailable_fixture(self, route, html, status=200):
        policy = {"kind": "historical_unavailable", "canonical": "/book/bn-060", "robots": "noindex,nofollow", "title": "ইন্দিরা"}
        return MODULE.inspect_route(route, policy, status, {}, html, "https://theearnalism.com" + route)

    def unavailable_html(self, *, body="", links="", slug="bn-060", title="ইন্দিরা"):
        return page(title=f"{title} unavailable | The Earnalism", description=f"{title} is not currently available as a public Earnalism release.", h1=f"{title} is not currently available.", canonical=f"https://theearnalism.com/book/{slug}", robots="noindex,nofollow", body="This title is not part of the current public release. No book text, reader session, or audio is available from this page. " + body, links=links)

    def test_approved_historical_recovery_page_passes_without_releasing_a_title(self):
        html = self.unavailable_html(links="<a href='/library'>Browse Library</a><a href='/contact?interest=bn-060'>Ask about title</a>")
        for kind in ("book", "reader", "listener"):
            self.assertEqual(self.inspect_unavailable_fixture(f"/{kind}/bn-060", html)["result"], "PASS")
        audio = page(title="Listen to Dracula | The Earnalism", description="Listening is not available for Dracula in the current release.", h1="Dracula", canonical="https://theearnalism.com/book/dracula", robots="noindex,follow", body="Listening is not available for Dracula in the current release. " + ACCESS, links="<a href='/book/dracula'>Book details</a>")
        self.assertEqual(self.inspect("/listener/dracula", audio)["result"], "PASS")
        for extra in ("<audio src='/sample.mp3'></audio>", "<button>Play</button>", '<script type="application/ld+json">{"@type":"Audiobook"}</script>'):
            self.assertEqual(self.inspect("/listener/dracula", audio.replace("</main>", extra + "</main>"))["result"], "FAIL")

    def test_selfish_giant_released_routes_reject_stale_hold_or_audio(self):
        slug, title = "the-selfish-giant", "The Selfish Giant"
        book = page(title=title + " | The Earnalism", description=title + " reader edition. " + ACCESS, h1=title, canonical=f"https://theearnalism.com/book/{slug}", body=ACCESS, links=f"<a href='/reader/{slug}'>Read the 3-page preview</a>" + '<script type="application/ld+json">{"@type":"Book","isAccessibleForFree":false}</script>')
        reader = page(title="Read " + title + " | The Earnalism Reader", description=ACCESS, h1="Read " + title, canonical=f"https://theearnalism.com/book/{slug}", robots="noindex,follow", body=ACCESS)
        audio_copy = "Listening is not available for The Selfish Giant in the current release."
        listener = page(title="Listen to " + title + " | The Earnalism", description=audio_copy, h1=title, canonical=f"https://theearnalism.com/book/{slug}", robots="noindex,follow", body=audio_copy + " " + ACCESS)
        for kind, html in [("book", book), ("reader", reader), ("listener", listener)]:
            route = f"/{kind}/{slug}"
            self.assertEqual(self.inspect(route, html)["result"], "PASS")
            self.assertEqual(self.inspect(route, self.unavailable_html(slug=slug, title=title))["result"], "FAIL")
            self.assertEqual(self.inspect(route, html.replace("</main>", "<audio src='/sample.mp3'></audio></main>"))["result"], "FAIL")
        route = f"/api/reader/book/{slug}/manifest"
        payload = {"slug": slug, "audio_enabled": False, "audiobook_enabled": False, "access": {"authenticated": False, "can_read_paid": False}}
        self.assertEqual(MODULE.inspect_protected_api(route, MODULE.PROTECTED_API_CHECKS[route], 200, payload, "https://theearnalism.com" + route)["result"], "PASS")
        for changed in [{**payload, "slug": "another-title"}, {**payload, "audio_enabled": True}, {**payload, "access": {"authenticated": False, "can_read_paid": True}}]:
            self.assertEqual(MODULE.inspect_protected_api(route, MODULE.PROTECTED_API_CHECKS[route], 200, changed, "https://theearnalism.com" + route)["result"], "FAIL")

    def test_dracula_released_reader_and_book_keep_audio_disabled(self):
        book = page(title="Dracula | The Earnalism", description="Dracula reader edition. " + ACCESS, h1="Dracula", canonical="https://theearnalism.com/book/dracula", body=ACCESS, links="<a href='/reader/dracula'>Read the 3-page preview</a>" + '<script type="application/ld+json">{"@type":"Book","isAccessibleForFree":false}</script>')
        reader = page(title="Read Dracula | The Earnalism Reader", description=ACCESS, h1="Read Dracula", canonical="https://theearnalism.com/book/dracula", robots="noindex,follow", body=ACCESS)
        self.assertEqual(self.inspect("/book/dracula", book)["result"], "PASS")
        self.assertEqual(self.inspect("/reader/dracula", reader)["result"], "PASS")
        route = "/api/reader/book/dracula/manifest"
        payload = {"slug": "dracula", "audio_enabled": False, "audiobook_enabled": False, "access": {"authenticated": False, "can_read_paid": False}}
        self.assertEqual(MODULE.inspect_protected_api(route, MODULE.PROTECTED_API_CHECKS[route], 200, payload, "https://theearnalism.com" + route)["result"], "PASS")
        for changed in ({**payload, "slug": "another-title"}, {**payload, "audio_enabled": True}, {**payload, "access": {"authenticated": False, "can_read_paid": True}}):
            self.assertEqual(MODULE.inspect_protected_api(route, MODULE.PROTECTED_API_CHECKS[route], 200, changed, "https://theearnalism.com" + route)["result"], "FAIL")

    def test_bengali_exact_guest_manifest_and_disabled_listener_remain_fail_closed(self):
        route = "/api/reader/book/book-edfcf810c5/manifest"
        payload = {"slug": "book-edfcf810c5", "audio_enabled": False, "audiobook_enabled": False, "access": {"authenticated": False, "can_read_paid": False}}
        self.assertEqual(MODULE.inspect_protected_api(route, MODULE.PROTECTED_API_CHECKS[route], 200, payload, "https://theearnalism.com" + route)["result"], "PASS")
        for changed in ({**payload, "slug": "dracula"}, {**payload, "audiobook_enabled": True}, {**payload, "access": {"authenticated": True, "can_read_paid": False}}, {**payload, "access": {"authenticated": False, "can_read_paid": True}}):
            self.assertEqual(MODULE.inspect_protected_api(route, MODULE.PROTECTED_API_CHECKS[route], 200, changed, "https://theearnalism.com" + route)["result"], "FAIL")
        audio = page(title="Listen to ক্ষুধিত পাষাণ | The Earnalism", description="Listening is not available for ক্ষুধিত পাষাণ in the current release.", h1="ক্ষুধিত পাষাণ", canonical="https://theearnalism.com/book/book-edfcf810c5", robots="noindex,follow", body="Listening is not available for ক্ষুধিত পাষাণ in the current release. " + ACCESS, links="<a href='/book/book-edfcf810c5'>Book details</a>")
        self.assertEqual(self.inspect("/listener/book-edfcf810c5", audio)["result"], "PASS")
        for extra in ("<audio src='/sample.mp3'></audio>", "<button>Play</button>", '<script type="application/ld+json">{"@type":"Audiobook"}</script>'):
            self.assertEqual(self.inspect("/listener/book-edfcf810c5", audio.replace("</main>", extra + "</main>"))["result"], "FAIL")

    def test_protected_api_contract_does_not_globally_allow_451_or_503(self):
        route = "/api/reader/book/dracula/manifest"
        policy = MODULE.PROTECTED_API_CHECKS[route]
        for status, payload in [
            (200, {"detail": {"code": "RELEASE_RIGHTS_DENIED"}}),
            (451, {"detail": {"code": "RELEASE_RIGHTS_DENIED"}}),
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
        self.assertEqual({route for route, policy in MODULE.PROTECTED_API_CHECKS.items() if policy["expected_status"] == 503}, expected)
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
        failed_route = "/api/reading-pass/books/the-canterville-ghost/manifest"
        def fixture_api(_base, route, _timeout):
            policy = MODULE.PROTECTED_API_CHECKS[route]
            status = policy["expected_status"]
            payload = {"detail": {"code": policy["expected_code"]}}
            if policy.get("kind") == "canonical_manifest":
                payload = {"book_slug": policy["expected_slug"], "version": "explicit-test-fixture-version", "segmentation_version": "explicit-test-fixture-segmentation", "total_pages": max(9, policy["expected_chapters"]), "public_preview_pages": 3, "chapters": [{"chapter_id": chapter_id} for chapter_id in policy["expected_chapter_ids"]]}
            elif status == 200:
                payload = {"slug": policy["expected_slug"], "audio_enabled": False, "audiobook_enabled": False, "access": {"authenticated": False, "can_read_paid": False}}
            if route == failed_route:
                status = 200
            return status, payload, "https://theearnalism.com" + route
        with patch.object(MODULE, "fetch_raw_html", return_value=(200, {}, "", "https://theearnalism.com/")), patch.object(MODULE, "inspect_route", return_value={"result": "PASS"}), patch.object(MODULE, "fetch_protected_api", side_effect=fixture_api):
            report = MODULE.run("https://theearnalism.com", 1)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(len(report["protected_apis"]), len(MODULE.PROTECTED_API_CHECKS))
        self.assertEqual([row["route"] for row in report["protected_apis"] if row["result"] == "FAIL"], [failed_route])

    def test_exact_canonical_manifests_require_actual_version_pages_and_chapters(self):
        for slug, count, total_pages in [
            ("dracula", 28, 276),
            ("book-edfcf810c5", 1, 9),
            ("muchiram-gurer-jibanchorit", 14, 14),
            ("bn-059", 13, 13),
            ("the-call-of-the-wild", 7, 7),
        ]:
            route = "/api/reading-pass/books/" + slug + "/manifest"
            policy = MODULE.PROTECTED_API_CHECKS[route]
            payload = {"book_slug": slug, "version": "preserved-version", "segmentation_version": "operator-existing-version", "total_pages": total_pages, "public_preview_pages": 3, "chapters": [{"chapter_id": chapter_id} for chapter_id in policy["expected_chapter_ids"]]}
            result = MODULE.inspect_protected_api(route, policy, 200, payload, "https://theearnalism.com" + route)
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["observed_canonical_version"], "preserved-version")
            for field, value in [("book_slug", "wrong-title"), ("version", ""), ("segmentation_version", None), ("total_pages", 3), ("total_pages", True), ("public_preview_pages", 4), ("chapters", []), ("chapters", [{}] * count)]:
                with self.subTest(slug=slug, field=field, value=value):
                    result = MODULE.inspect_protected_api(route, policy, 200, {**payload, field: value}, "https://theearnalism.com" + route)
                    self.assertEqual(result["result"], "FAIL")
                    self.assertIsNone(result["observed_canonical_version"])
            result = MODULE.inspect_protected_api(route, policy, 503, {"detail": {"code": "SEGMENTS_NOT_READY"}}, "https://theearnalism.com" + route)
            self.assertEqual(result["result"], "FAIL")
            result = MODULE.inspect_protected_api(route, policy, 451, {"detail": {"code": "RELEASE_TERRITORY_DENIED", "country": "US", "allowed_countries": ["IN"]}}, "https://theearnalism.com" + route)
            self.assertEqual(result["india_backend_contract"], "NOT_PERFORMED")
            self.assertIsNone(result["observed_canonical_version"])

    def test_explicit_overseas_edge_denial_does_not_claim_india_readback(self):
        for route, policy in MODULE.PROTECTED_API_CHECKS.items():
            result = MODULE.inspect_protected_api(route, policy, 451,
                {"detail": {"code": "RELEASE_TERRITORY_DENIED", "country": "US", "allowed_countries": ["IN"]}},
                "https://theearnalism.com" + route, {"Cache-Control": "no-store"})
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["india_backend_contract"], "NOT_PERFORMED")

    def test_territory_policy_matrix_and_historical_mx_regression(self):
        route = "/api/reader/book/dracula/manifest"
        policy = MODULE.PROTECTED_API_CHECKS[route]
        def inspect(country, status=451, code="RELEASE_TERRITORY_DENIED", allowed=None, headers=None):
            return MODULE.inspect_protected_api(route, policy, status,
                {"detail": {"country": country, "code": code, "allowed_countries": ["IN"] if allowed is None else allowed}},
                "https://theearnalism.com" + route,
                {"Cache-Control": "no-store"} if headers is None else headers)
        # Exact old predicate rejected MX, despite the correct denial contract.
        self.assertNotIn("MX", {"US", "GB", "CA", "AU", "DE", "AE", "BD", "SG", "SA"})
        for country in ("MX", "US", "GB", "JP"):
            with self.subTest(country=country):
                result = inspect(country)
                self.assertEqual(result["result"], "PASS")
                self.assertEqual(result["india_backend_contract"], "NOT_PERFORMED")
                self.assertEqual(result["territory_denial_contract"], "CHECKED")
        for country in (None, "", "us", "USA", "1N", "ZZ", "XX", " IN "):
            with self.subTest(country=country):
                result = inspect(country)
                self.assertEqual(result["result"], "FAIL")
                self.assertEqual(result["india_backend_contract"], "NOT_PERFORMED")
                self.assertTrue(any("UNKNOWN" in failure for failure in result["failures"]))
        for kwargs in ({"status": 200}, {"code": "OTHER"}, {"allowed": ["IN", "US"]}, {"headers": {}}, {"headers": {"Cache-Control": "public"}}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(inspect("MX", **kwargs)["result"], "FAIL")
        payload = {"slug": "dracula", "audio_enabled": False, "audiobook_enabled": False,
                   "access": {"authenticated": False, "can_read_paid": False}}
        result = MODULE.inspect_protected_api(route, policy, 200, payload, "https://theearnalism.com" + route)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["india_backend_contract"], "CHECKED")
        self.assertEqual(inspect("IN")["result"], "FAIL")

    def test_territorial_denial_is_not_a_generic_451_exception(self):
        route = "/api/reading-pass/books/the-adventures-of-sherlock-holmes/manifest"
        policy = MODULE.PROTECTED_API_CHECKS[route]
        for country, allowed, status, actual_route in [
            ("IN", ["IN"], 451, route), (None, ["IN"], 451, route),
            ("us", ["IN"], 451, route), ("ZZ", ["IN"], 451, route), ("US", ["IN", "US"], 451, route),
            ("US", ["IN"], 200, route), ("US", ["IN"], 451, "/api/unreviewed"),
        ]:
            with self.subTest(country=country, allowed=allowed, status=status, route=actual_route):
                result = MODULE.inspect_protected_api(actual_route, policy, status,
                    {"detail": {"code": "RELEASE_TERRITORY_DENIED", "country": country, "allowed_countries": allowed}},
                    "https://theearnalism.com" + actual_route)
                self.assertEqual(result["result"], "FAIL")
        result = MODULE.inspect_protected_api(route, policy, 451,
            {"detail": {"code": "RELEASE_TERRITORY_DENIED", "country": "US", "allowed_countries": ["IN"]}},
            "https://theearnalism.com/login")
        self.assertEqual(result["result"], "FAIL")

    def test_genuine_missing_routes_still_require_404(self):
        self.assertEqual(self.inspect("/book/yugalanguriya", "", status=404)["result"], "PASS")
        self.assertEqual(self.inspect("/book/yugalanguriya", "", status=451)["result"], "FAIL")

    def test_historical_home_fallback_and_released_access_copy_are_rejected(self):
        html = page(title="Earnalism | Classics", description=ACCESS, h1="A library made for lingering", canonical="https://theearnalism.com/", body=ACCESS)
        self.assertEqual(self.inspect_unavailable_fixture("/book/bn-060", html)["result"], "FAIL")
        self.assertEqual(self.inspect_unavailable_fixture("/reader/bn-060", self.unavailable_html(body=ACCESS))["result"], "FAIL")

    def test_historical_controls_media_schema_and_non_recovery_links_are_rejected(self):
        unsafe = ["<button>Read</button>", "<audio src='https://media.example/audio.mp3'></audio>", '<script type="application/ld+json">{"@type":"Book","isAccessibleForFree":true}</script>', "<a href='/reader/bn-060'>Open Reader</a>"]
        for content in unsafe:
            with self.subTest(content=content):
                self.assertEqual(self.inspect_unavailable_fixture("/book/bn-060", self.unavailable_html(body=content))["result"], "FAIL")

    def test_historical_routes_require_exact_identity_and_noindex(self):
        html = self.unavailable_html()
        for unsafe in [html.replace("noindex,nofollow", "index,follow"), html.replace("https://theearnalism.com/book/bn-060", "https://theearnalism.com/"), html.replace("ইন্দিরা", "Another title")]:
            self.assertEqual(self.inspect_unavailable_fixture("/book/bn-060", unsafe)["result"], "FAIL")


class HistoricalUnavailableSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="historical-unavailable-snapshots-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source_root = SCRIPT.parent.parent
        files = ["frontend/scripts/static-seo-template.mjs", "frontend/scripts/generate-static-seo-snapshots.mjs", "frontend/scripts/verify-static-seo-snapshots.mjs", "frontend/scripts/unavailable-title-routes.mjs", "frontend/static-seo/controlled-publication-public.json", "frontend/static-seo/editorial-public.json", "frontend/public/index.html", "data/controlled_launch.json"]
        for relative in files:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_root / relative, target)
        fixture = self.root / "frontend/scripts/unavailable-title-routes.mjs"
        fixture.write_text(fixture.read_text().replace("export const unavailableTitles = [\n];", 'export const unavailableTitles = [\n  { slug: "bn-060", title: "ইন্দিরা" },\n];'))
        self.generate()

    def generate(self):
        subprocess.run(["node", str(self.root / "frontend/scripts/generate-static-seo-snapshots.mjs")], check=True, capture_output=True, text=True, timeout=30)

    def verify(self):
        return subprocess.run(["node", str(self.root / "frontend/scripts/verify-static-seo-snapshots.mjs")], capture_output=True, text=True, timeout=30)

    def test_fresh_build_directory_contains_runtime_journal_app_shell(self):
        shell = self.root / "frontend/build/journal-app-shell.html"
        self.assertTrue(shell.is_file())
        self.assertIn('id="root"', shell.read_text())

    def test_real_generator_and_verifier_produce_three_safe_unavailable_snapshots(self):
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.root / "frontend/build/static-seo-snapshot-manifest.json").read_text())
        held = [r for r in manifest["routes"] if r["snapshot_classification"] == "RELEASE_HELD"]
        self.assertEqual(len(held), 3)
        for route in ("/book/dracula", "/reader/dracula", "/listener/dracula", "/book/book-edfcf810c5", "/reader/book-edfcf810c5", "/listener/book-edfcf810c5"):
            html = (self.root / "frontend/build" / route.lstrip("/") / "index.html").read_text()
            report = MODULE.inspect_route(route, MODULE.ROUTES[route], 200, {}, html, "https://theearnalism.com" + route)
            self.assertEqual(report["result"], "PASS", report)
        for entry in held:
            route = entry["route"]
            html = (self.root / "frontend/build" / route.lstrip("/") / "index.html").read_text()
            policy = {"kind": "historical_unavailable", "canonical": "/book/bn-060", "robots": "noindex,nofollow", "title": "ইন্দিরা"}
            report = MODULE.inspect_route(route, policy, 200, {}, html, "https://theearnalism.com" + route)
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
        target = self.root / "frontend/build/book/bn-060/index.html"
        original = target.read_text()
        for html in [original.replace('name="robots" content="noindex,nofollow"', 'name="robots" content="index,follow"'), original.replace("</main>", '<a href="/reader/bn-060">Read the 3-page preview</a></main>')]:
            target.write_text(html)
            self.assertNotEqual(self.verify().returncode, 0)
            self.assertEqual(MODULE.inspect_route("/book/bn-060", {"kind": "historical_unavailable", "canonical": "/book/bn-060", "robots": "noindex,nofollow", "title": "ইন্দিরা"}, 200, {}, html, "https://theearnalism.com/book/bn-060")["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
