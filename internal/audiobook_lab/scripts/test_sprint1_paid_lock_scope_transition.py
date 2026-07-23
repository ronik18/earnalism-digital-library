#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sprint1_paid_lock_scope_transition as transition


class PaidLockScopeTransitionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.lock = self.root / "paid_tts.lock"
        self.curation = self.root / "curation.json"
        self.report = self.root / "report.json"
        self.lock.write_text(
            json.dumps(
                {
                    "status": "active",
                    "current_holder": "none",
                    "allowed_next_holders": [],
                    "allowed_slugs": ["nishkriti"],
                    "budget_cap_usd": 75,
                }
            ),
            encoding="utf-8",
        )
        self.curation.write_text(
            json.dumps(
                {
                    "sprint1_active_slugs": ["book-edfcf810c5"],
                    "books": {},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        public_book = (
            self.curation.parent
            / "controlled_publications"
            / "book-edfcf810c5"
            / "public_book.json"
        )
        public_book.parent.mkdir(parents=True)
        public_book.write_text(
            json.dumps(
                {
                    "slug": "book-edfcf810c5",
                    "title": "ক্ষুধিত পাষাণ",
                    "author": "রবীন্দ্রনাথ ঠাকুর",
                    "chapters": [{"language_hint": "ben"}],
                    "allowPublicReading": True,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.args = argparse.Namespace(
            lock_path=self.lock,
            curation_path=self.curation,
            expected_current_slug="nishkriti",
            next_slug="book-edfcf810c5",
            scope="One representative audition; no publication.",
            report=self.report,
        )
        self.env = {
            "EARNALISM_APPROVE_PAID_TTS_SCOPE_TRANSITION": "true",
            "EARNALISM_STOP_ON_BUDGET_EXCEEDED": "true",
            "SPRINT1_TOTAL_AUDIO_BUDGET_USD": "75",
            "SPRINT1_MAX_USD_PER_TITLE": "8",
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_idle_lock_transitions_to_canonical_reader_enabled_title(self) -> None:
        result = transition.transition(self.args, self.env)
        updated = json.loads(self.lock.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(updated["allowed_slugs"], ["book-edfcf810c5"])
        self.assertEqual(updated["current_holder"], "none")
        self.assertFalse(result["provider_call_performed"])
        self.assertFalse(result["publication_performed"])

    def test_current_slug_mismatch_fails_without_mutation(self) -> None:
        before = self.lock.read_bytes()
        self.args.expected_current_slug = "radharani"
        with self.assertRaises(transition.ScopeTransitionError):
            transition.transition(self.args, self.env)
        self.assertEqual(self.lock.read_bytes(), before)

    def test_noncanonical_next_slug_fails_without_mutation(self) -> None:
        before = self.lock.read_bytes()
        self.args.next_slug = "invented-book"
        with self.assertRaises(transition.ScopeTransitionError):
            transition.transition(self.args, self.env)
        self.assertEqual(self.lock.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
