import copy
import hashlib
import unittest

from backend.domain.reading_pass import canonical_page_records
from scripts.prepare_reader_completeness_repairs import compare_pages, narrative_digest, render_chapters, complete_preview_matches


class CompletenessRepairTests(unittest.TestCase):
    def setUp(self):
        self.records = canonical_page_records(book_slug="book", chapters=[
            {"id": "one", "order": 1, "content": "<p>Opening</p>"},
            {"id": "two", "order": 2, "content": "<p>Ending</p>"},
        ])
        self.live = {"canonical_pages": {"page_count": 2, "pages": [
            {"page_number": r["page_index"], "chapter_id": r["chapter_id"], "content_hash": r["content_sha256"]}
            for r in self.records]}}

    def test_missing_final_chapter_prepares_complete_inactive_candidate(self):
        self.live["canonical_pages"]["pages"].pop()
        self.live["canonical_pages"]["page_count"] = 1
        r = compare_pages("book", self.records, self.live)
        self.assertFalse(r["source_matches"])
        self.assertEqual(r["missing_chapter_ids"], ["two"])
        self.assertEqual(r["candidate"]["manifest"]["total_pages"], 2)
        self.assertEqual(r["candidate"]["state"], "LOCAL_INACTIVE_NOT_STORED_OR_PROMOTED")

    def test_reordered_or_changed_pages_do_not_match(self):
        for mutate in (lambda x: x.reverse(), lambda x: x[0].update(content_hash="0" * 64)):
            live = copy.deepcopy(self.live)
            mutate(live["canonical_pages"]["pages"])
            self.assertFalse(compare_pages("book", self.records, live)["source_matches"])

    def test_metadata_or_session_admission_is_not_delivery(self):
        r = compare_pages("book", self.records, self.live, {"slug": "book", "status": 200})
        self.assertTrue(r["source_matches"])
        self.assertFalse(r["confirmed_protected_delivery"])

    def test_delivery_requires_exact_final_page_and_authenticated_visible_text(self):
        receipt = {"slug": "book", "status": 200, "authenticated": True, "visible_authorized": True,
                   "nonempty_content": True, "page_index": 2, "page_hash": self.records[-1]["content_sha256"]}
        self.assertTrue(compare_pages("book", self.records, self.live, receipt)["confirmed_protected_delivery"])
        for key, value in (("page_hash", "stale"), ("page_index", 1), ("authenticated", False), ("status", 503)):
            with self.subTest(key=key):
                self.assertFalse(compare_pages("book", self.records, self.live, {**receipt, key: value})["confirmed_protected_delivery"])

    def test_plan_is_hash_only_and_does_not_change_inputs(self):
        before = copy.deepcopy((self.records, self.live))
        r = compare_pages("book", self.records, self.live)
        self.assertNotIn("Opening", str(r))
        self.assertEqual(before, (self.records, self.live))
        self.assertNotIn("expected_activation_generation", r["candidate"])

    def test_formatting_parity_does_not_hide_removed_or_reordered_words(self):
        before = [{"content": "<p>First line<br>second line</p>"}]
        self.assertEqual(narrative_digest(before), narrative_digest([{"content": "First line\nsecond line"}]))
        self.assertNotEqual(narrative_digest(before), narrative_digest([{"content": "First line"}]))
        self.assertNotEqual(narrative_digest(before), narrative_digest([{"content": "second line First line"}]))

    def test_missing_sanitizer_cannot_create_a_misleading_repair_plan(self):
        with self.assertRaisesRegex(ValueError, "renderer warnings must be resolved"):
            render_chapters([{"id": "one", "content": "<p>Text</p>"}],
                            lambda value: ("escaped", ["Content sanitizer unavailable; HTML was escaped."]))

    def test_complete_public_delivery_requires_every_page_and_valid_bytes(self):
        previews = [{"book_slug": "book", "page_index": r["page_index"], "content": r["content"],
                     "content_sha256": r["content_sha256"]} for r in self.records]
        chapters = [{"content": "<p>Opening</p><p>Ending</p>"}]
        self.assertTrue(complete_preview_matches("book", chapters, self.live, previews))
        self.assertFalse(complete_preview_matches("book", chapters, self.live, previews[:1]))
        previews[1]["content"] = "Corrupted"
        self.assertFalse(complete_preview_matches("book", chapters, self.live, previews))

    def test_illustration_labels_require_explicit_source_policy(self):
        content = "<p>Story</p><p>[Picture: Decoration]</p>"
        digest = hashlib.sha256(content.encode()).hexdigest()
        live = {"canonical_pages": {"page_count": 1, "pages": [{"page_number": 1, "content_hash": digest}]}}
        previews = [{"book_slug": "book", "page_index": 1, "content": content, "content_sha256": digest}]
        self.assertFalse(complete_preview_matches("book", [{"content": "Story"}], live, previews))
        self.assertTrue(complete_preview_matches("book", [{"content": "Story"}], live, previews, illustration_labels=True))


if __name__ == "__main__":
    unittest.main()
