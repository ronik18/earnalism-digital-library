"""Evidence preparation must never masquerade as publication authority."""
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.bengali_text_compliance_audit import (
    ROOT, audit_package, canonical_identity, existing_comparison,
    normalized_text, source_snapshot,
)
from backend.publication_manifest import build_manifest, validate_manifest
from scripts.publication_manifest_conveyor import run as conveyor_run


class BengaliComplianceTests(unittest.TestCase):
    def test_formatting_normalization_preserves_literary_words_and_punctuation(self):
        self.assertEqual(normalized_text("  গিন্নি\u200b\n\nশিবনাথ। "), "গিন্নি শিবনাথ।")
        self.assertNotEqual(normalized_text("গিন্নি।"), normalized_text("গিন্নি!"))

    def test_indira_exact_existing_evidence_matches_every_current_chapter(self):
        package = ROOT / "data/controlled_publications/bn-060"
        identity = canonical_identity(package)
        self.assertEqual(len(identity["chapters"]), 8)
        result = existing_comparison(package, identity, ROOT)
        self.assertTrue(result["all_chapter_hashes_match"])
        identity["chapters"][0]["content_sha256"] = "0" * 64
        self.assertEqual(existing_comparison(package, identity, ROOT)["status"], "EXISTING_SOURCE_EVIDENCE_STALE")

    def test_held_package_never_receives_publication_or_audio_approval(self):
        result = audit_package(ROOT / "data/controlled_publications/bn-060", ROOT, {}, False)
        self.assertEqual(result["publication_authorization"], "NOT_GRANTED_BY_THIS_AUDIT")
        self.assertEqual(result["proposed_reader_manifest_status"], "BLOCKED")
        self.assertFalse(result["audio_touched"])
        self.assertFalse(result["live_allowlist_touched"])
        self.assertIn("Edition-bound owner/legal publication authorization and accepted registry decision are required.", result["blockers"])

    def test_owner_design_statement_does_not_invent_component_clearance(self):
        result = audit_package(ROOT / "data/controlled_publications/book-0986aeb7e3", ROOT, {}, False)
        self.assertEqual(result["cover_provenance"]["front_binding"], "MISSING")
        self.assertEqual(result["cover_provenance"]["third_party_component_clearance"], "NOT_INFERRED")

    def test_existing_removal_is_preserved(self):
        result = audit_package(ROOT / "data/controlled_publications/book-2b9853ec52", ROOT, {}, False)
        self.assertEqual(result["status"], "EXCLUDED")
        self.assertTrue(any("owner-directed" in issue for issue in result["blockers"]))

    def test_different_provider_is_not_fetched_as_wikisource(self):
        with patch("scripts.bengali_text_compliance_audit.fetch_json") as fetch:
            result, text = source_snapshot("https://example.com/title", {})
        fetch.assert_not_called()
        self.assertEqual(result["status"], "UNSUPPORTED_SOURCE_REQUIRES_REVIEW")
        self.assertEqual(text, "")

    def test_provider_rate_limit_stops_collection_instead_of_hammering(self):
        with patch("scripts.bengali_text_compliance_audit.source_snapshot", side_effect=HTTPError("https://bn.wikisource.org", 429, "Too Many Requests", {}, None)):
            with self.assertRaises(HTTPError):
                audit_package(ROOT / "data/controlled_publications/bn-060", ROOT, {}, True)

    def test_text_preparation_does_not_accept_stale_audio_or_weaken_normal_validation(self):
        package = ROOT / "data/controlled_publications/book-0deb35c750"
        before = (package / "public_book.json").read_bytes()
        ordinary = build_manifest(package)
        self.assertIn("approved audio release requires audio_sha256", validate_manifest(ordinary))
        prepared = build_manifest(package, reader_preparation_only=True)
        self.assertEqual(validate_manifest(prepared), [])
        self.assertEqual(prepared["reader_release"]["status"], "BLOCKED")
        self.assertFalse(prepared["reader_release"]["exposed"])
        self.assertFalse(prepared["audio_release"]["exposed"])
        self.assertNotEqual(prepared["audio_release"]["status"], "APPROVED")
        self.assertEqual((package / "public_book.json").read_bytes(), before)

    def test_preparation_cannot_be_combined_with_publication_or_destructive_audio_option(self):
        with self.assertRaisesRegex(ValueError, "cannot authorize"):
            build_manifest(ROOT / "data/controlled_publications/bn-060", publish_approved=True, reader_preparation_only=True)
        self.assertEqual(conveyor_run(["--slug", "bn-060", "--reader-preparation-only", "--publish-approved"]), 2)
        self.assertEqual(conveyor_run(["--slug", "bn-060", "--reader-preparation-only", "--disable-audio"]), 2)

    def test_pinned_revision_and_license_do_not_equal_edition_clearance(self):
        metadata = {"query": {"pages": [{"title": "গিন্নি", "pageid": 1, "lastrevid": 9, "revisions": [{"timestamp": "2026-01-01T00:00:00Z"}]}]}}
        parsed = {"parse": {"text": '<div class="mw-parser-output"><p>গিন্নি</p><p>সত্য পাঠ।</p></div>', "links": []}}
        with patch("scripts.bengali_text_compliance_audit.SOURCE_METADATA", {}), patch("scripts.bengali_text_compliance_audit.fetch_json", side_effect=[(metadata, {"response_sha256": "a" * 64}), (parsed, {"response_sha256": "b" * 64})]):
            result, text = source_snapshot("https://bn.wikisource.org/wiki/গিন্নি", {"rightsinfo": {"text": "CC BY-SA 4.0"}})
        self.assertEqual(result["revision_id"], 9)
        self.assertIn("oldid=9", result["permalink"])
        self.assertEqual(text, "সত্য পাঠ।")
        self.assertEqual(result["edition_identity_status"], "EXACT_FACSIMILE_AND_EDITORIAL_LAYER_REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
