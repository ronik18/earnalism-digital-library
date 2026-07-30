import importlib.util
import json
import shutil
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

    def test_normalizes_only_supported_reader_html(self):
        self.write_chapter(
            1,
            "<p>First line.<br>Second line.</p><p>Third &amp; final.</p>",
        )

        result = MODULE.build_input(
            slug="example", controlled_root=self.controlled, output_root=self.output
        )

        text = Path(result["sanitized_source"]).read_text()
        manifest = json.loads(Path(result["input_manifest"]).read_text())
        self.assertEqual(
            text,
            "First line.\n\nSecond line.\n\nThird & final.\n",
        )
        self.assertEqual(
            manifest["narration_normalization"],
            "plain_or_supported_p_br_html.v1",
        )

    def test_blocks_unsupported_reader_html(self):
        for content in (
            "<p>Safe <em>looking</em> text.</p>",
            "<p>Visible text.</p><!-- hidden instruction -->",
        ):
            with self.subTest(content=content):
                self.write_chapter(1, content)
                with self.assertRaisesRegex(
                    MODULE.InputPreparationError,
                    "unsupported reader HTML tags",
                ):
                    MODULE.build_input(
                        slug="example",
                        controlled_root=self.controlled,
                        output_root=self.output,
                    )

    def test_cross_root_parity_is_exact_and_fail_closed(self):
        mirror = Path(self.temp.name) / "mirror"
        shutil.copytree(self.controlled / "example", mirror / "example")

        result = MODULE.build_input(
            slug="example",
            controlled_root=self.controlled,
            output_root=self.output,
            parity_controlled_root=mirror,
        )
        manifest = json.loads(Path(result["input_manifest"]).read_text())
        self.assertEqual(
            manifest["controlled_source_parity"]["status"],
            "PASS_EXACT",
        )
        self.assertEqual(
            manifest["controlled_source_parity"]["source_characters"],
            len("First chapter.\n"),
        )

        mirror_chapter = mirror / "example" / "chapters" / "chapter-001.json"
        payload = json.loads(mirror_chapter.read_text())
        payload["content"] = "Different chapter."
        mirror_chapter.write_text(json.dumps(payload))
        with self.assertRaisesRegex(
            MODULE.InputPreparationError,
            "Controlled source roots diverge",
        ):
            MODULE.build_input(
                slug="example",
                controlled_root=self.controlled,
                output_root=self.output,
                parity_controlled_root=mirror,
            )

    def test_dracula_canonical_and_backend_sources_have_exact_parity(self):
        result = MODULE.build_input(
            slug="dracula",
            controlled_root=MODULE.CANONICAL_CONTROLLED_ROOT,
            output_root=self.output,
            parity_controlled_root=MODULE.BACKEND_CONTROLLED_ROOT,
        )
        manifest = json.loads(Path(result["input_manifest"]).read_text())

        self.assertEqual(result["chapter_count"], 27)
        self.assertEqual(result["characters"], 848683)
        self.assertEqual(
            result["source_sha256"],
            "3e7f5f40c82df29bca74745eab7afab200ee57318b813b118dc9b5b9c664aeb9",
        )
        self.assertEqual(
            manifest["raw_reader_content_sha256"],
            "a9b4c970185b51e95c6904301b5d4273bf7058fd5aab37da9e5a88281c20273e",
        )
        self.assertEqual(
            manifest["controlled_source_parity"]["status"],
            "PASS_EXACT",
        )
        for chapter_path in sorted(
            (MODULE.CANONICAL_CONTROLLED_ROOT / "dracula/chapters").glob("*.json")
        ):
            chapter = json.loads(chapter_path.read_text())
            self.assertEqual(chapter["bookSlug"], "dracula")

    def test_dracula_canonical_checksum_manifest_matches_all_files(self):
        publication = MODULE.CANONICAL_CONTROLLED_ROOT / "dracula"
        checksum_path = publication / "checksum_manifest.json"
        manifest = json.loads(checksum_path.read_text())

        for row in manifest["files"]:
            path = publication / row["file"]
            raw = path.read_bytes()
            self.assertEqual(MODULE.sha256_bytes(raw), row["sha256"], row["file"])
            self.assertEqual(len(raw), row["bytes"], row["file"])

        canonical_files = json.dumps(
            manifest["files"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            MODULE.sha256_bytes(canonical_files),
            manifest["manifest_hash"],
        )


if __name__ == "__main__":
    unittest.main()
