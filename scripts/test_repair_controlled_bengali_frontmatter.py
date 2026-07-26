from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_controlled_bengali_frontmatter.py")
SPEC = importlib.util.spec_from_file_location("repair_controlled_bengali_frontmatter", SCRIPT)
repair = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(repair)


class ControlledBengaliFrontmatterRepairTests(unittest.TestCase):
    def test_strips_all_metadata_through_punctuated_canonical_title(self) -> None:
        content = (
            "রবীন্দ্রনাথ ঠাকুর\n\n"
            "গল্প-দশক\n\n"
            "১৮৯৫ (পৃ. ১৬৫-১৮৮)\n\n"
            "ক্ষুধিত পাষাণ।\n\n"
            "গাড়িটি আসিয়া জংশনে থামিলে আমরা অপেক্ষা করিলাম।"
        )
        cleaned, removed = repair.strip_verified_title_page(content, title="ক্ষুধিত পাষাণ")
        self.assertEqual(cleaned, "গাড়িটি আসিয়া জংশনে থামিলে আমরা অপেক্ষা করিলাম।")
        self.assertIn("গল্প-দশক", removed)
        self.assertIn("ক্ষুধিত পাষাণ।", removed)

    def test_fails_closed_without_leading_metadata(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "No leading metadata"):
            repair.strip_verified_title_page(
                "ক্ষুধিত পাষাণ\n\nগাড়িটি আসিয়া থামিল।",
                title="ক্ষুধিত পাষাণ",
            )

    def test_strips_verified_bengali_edition_page_range(self) -> None:
        cleaned, removed = repair.strip_verified_page_range(
            "১৮৮৩ (পৃ. ১-২)\n\nঅতি বিস্তৃত অরণ্য।"
        )
        self.assertEqual(removed, "১৮৮৩ (পৃ. ১-২)")
        self.assertEqual(cleaned, "অতি বিস্তৃত অরণ্য।")

    def test_rejects_unrecognized_leading_chapter_text(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "page-range marker"):
            repair.repairable_chapter_content(
                "অতি বিস্তৃত অরণ্য।",
                title="আনন্দমঠ",
            )

    def test_already_repaired_publication_is_an_idempotent_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            publication = Path(temporary)
            (publication / "chapters").mkdir()
            (publication / "public_book.json").write_text(
                json.dumps({"title": "আনন্দমঠ"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (publication / "source_evidence.json").write_text(
                json.dumps({"reader_facing_boilerplate_removed": True}),
                encoding="utf-8",
            )
            (publication / "chapters/chapter-001.json").write_text(
                json.dumps({"content": "অতি বিস্তৃত অরণ্য।"}, ensure_ascii=False),
                encoding="utf-8",
            )
            self.assertEqual(repair.publication_repair_plan(publication), [])

    def test_mixed_repair_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            publication = Path(temporary)
            (publication / "chapters").mkdir()
            (publication / "public_book.json").write_text(
                json.dumps({"title": "আনন্দমঠ"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (publication / "source_evidence.json").write_text(
                json.dumps({"reader_facing_boilerplate_removed": True}),
                encoding="utf-8",
            )
            (publication / "chapters/chapter-001.json").write_text(
                json.dumps(
                    {"content": "১৮৮৩ (পৃ. ১-২)\n\nঅতি বিস্তৃত অরণ্য।"},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (publication / "chapters/chapter-002.json").write_text(
                json.dumps({"content": "আরও অরণ্য।"}, ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "mixed repaired/unrepaired"):
                repair.publication_repair_plan(publication)


if __name__ == "__main__":
    unittest.main()
