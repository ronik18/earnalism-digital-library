import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sprint1_prepare_google_english_input.py")
SPEC = importlib.util.spec_from_file_location("prepare_english_input", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PrepareEnglishInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.controlled = root / "controlled"
        self.output = root / "output"
        self.book = self.controlled / "example"
        (self.book / "chapters").mkdir(parents=True)
        (self.book / "source_evidence.json").write_text(
            json.dumps(
                {
                    "rights_basis": "Public domain test fixture",
                    "reader_facing_boilerplate_removed": True,
                }
            )
        )
        (self.book / "approval_evidence.json").write_text(
            json.dumps(
                {"approved_to_publish": True, "verification_status": "approved"}
            )
        )
        (self.book / "public_book.json").write_text(
            json.dumps(
                {"title": "Example", "author": "Author", "language": "en"}
            )
        )
        self.write_chapter(1, "First chapter.")

    def tearDown(self):
        self.temp.cleanup()

    def write_chapter(self, order, content, **extra):
        payload = {
            "bookSlug": "example",
            "order": order,
            "language": "en",
            "content": content,
            "processing_status": "ready",
            "processing_warnings": [],
        }
        payload.update(extra)
        (self.book / "chapters" / f"chapter-{order:03d}.json").write_text(
            json.dumps(payload)
        )

    def test_builds_hash_bound_private_input(self):
        self.write_chapter(2, "Second chapter.")
        result = MODULE.build_input(
            slug="example", controlled_root=self.controlled, output_root=self.output
        )
        manifest = json.loads(Path(result["input_manifest"]).read_text())
        text = Path(result["sanitized_source"]).read_text()
        self.assertEqual(result["status"], "PASS_PRIVATE_INPUT_READY")
        self.assertEqual(text, "First chapter.\n\nSecond chapter.\n")
        self.assertEqual(manifest["chapter_orders"], [1, 2])
        self.assertEqual(manifest["sanitized_source_sha256"], result["source_sha256"])
        self.assertFalse(manifest["public_audio_release_approved"])

    def test_blocks_incomplete_rights(self):
        (self.book / "approval_evidence.json").write_text(
            json.dumps({"approved_to_publish": False, "verification_status": "hold"})
        )
        with self.assertRaises(MODULE.InputPreparationError):
            MODULE.build_input(
                slug="example", controlled_root=self.controlled, output_root=self.output
            )

    def test_blocks_boilerplate(self):
        self.write_chapter(1, "*** START OF THIS PROJECT GUTENBERG EBOOK")
        with self.assertRaises(MODULE.InputPreparationError):
            MODULE.build_input(
                slug="example", controlled_root=self.controlled, output_root=self.output
            )

    def test_blocks_noncontiguous_order(self):
        (self.book / "chapters" / "chapter-001.json").unlink()
        self.write_chapter(2, "Second chapter.")
        with self.assertRaises(MODULE.InputPreparationError):
            MODULE.build_input(
                slug="example", controlled_root=self.controlled, output_root=self.output
            )


if __name__ == "__main__":
    unittest.main()
