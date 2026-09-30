import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.process_full_catalogue import OUTPUT, process, rendered


class CatalogueProcessorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with (self.root / "earnalism_book_inventory_for_launch.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["slug", "title", "language"])
            writer.writeheader()
            writer.writerows([{"slug": "prepared", "title": "Prepared", "language": "eng"}, {"slug": "missing", "title": "Missing", "language": "ben"}])
        registry = self.root / "backend/data/rights_decision_registry.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(rendered({"schema_version": "earnalism.rights-decision-registry.v1", "accepted_records": {}, "revoked_decision_ids": []}))
        self.package = self.root / "data/controlled_publications/prepared"
        self.package.mkdir(parents=True)
        self.write("public_book.json", {"slug": "prepared", "title": "Prepared", "author": "Test author", "chapters": [{"id": "chapter-001", "order": 1, "title": "Opening", "processing_status": "ready"}], "cover_url": "https://example.com/cover.png", "qa_status": "QA_PASSED", "isPublic": False, "isLive": False})
        self.write("reader_manifest.json", {"slug": "prepared", "chapter_count": 1, "chapters": [{"id": "chapter-001"}]})
        self.write("source_evidence.json", {"source_hash": "a" * 64, "content_hash": "b" * 64, "provenance_hash": "c" * 64, "reader_facing_boilerplate_removed": True})
        self.write("approval_evidence.json", {"approved_to_publish": False})
        self.write("chapters/chapter-001.json", {"id": "chapter-001", "content": "A clean paragraph.", "content_hash": hashlib.sha256(b"A clean paragraph.").hexdigest()})
        self.write("checksum_manifest.json", {"files": []})

    def write(self, name, value):
        path = self.package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered(value))

    def run_processor(self):
        return process(self.root, "2026-09-30T00:00:00Z")

    def test_every_title_is_assessed_without_granting_rights_or_publishing(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        outputs, state = self.run_processor()
        self.assertEqual(state["title_count"], 2)
        self.assertEqual(state["missing_package_count"], 1)
        self.assertEqual(state["new_publication_count"], 0)
        manifest = json.loads(outputs["manifests/prepared.json"])["publication_manifest"]
        self.assertFalse(manifest["reader_release"]["exposed"])
        self.assertFalse(manifest["audio_release"]["exposed"])
        self.assertIn("ACCEPTED_HASH_BOUND_TEXT_USE_DECISION_REQUIRED", manifest["reader_release"]["blockers"])
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_unsafe_markup_and_tampered_content_are_explicit_holds(self):
        self.write("chapters/chapter-001.json", {"id": "chapter-001", "content": "<script>alert(1)</script>", "content_hash": "d" * 64})
        _, state = self.run_processor()
        title = next(row for row in state["titles"] if row["slug"] == "prepared")
        self.assertIn("UNSAFE_READER_HTML:chapter-001", title["blockers"])
        self.assertIn("CHAPTER_CONTENT_HASH_MISMATCH:chapter-001", title["blockers"])

    def test_checksum_traversal_is_rejected_without_following_it(self):
        self.write("checksum_manifest.json", {"files": [{"file": "../../outside.json", "sha256": "a" * 64}]})
        _, state = self.run_processor()
        title = next(row for row in state["titles"] if row["slug"] == "prepared")
        self.assertIn("UNSAFE_CHECKSUM_PATH", title["blockers"])

    def test_private_artifacts_reproduce_and_tampering_fails_verification(self):
        outputs, _ = self.run_processor()
        output = self.root / OUTPUT
        for name, value in outputs.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        command = [sys.executable, str(Path(__file__).with_name("process_full_catalogue.py")), "--root", str(self.root), "--check"]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        target = output / "manifests/prepared.json"
        target.write_text("{}\n")
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
        self.assertEqual(target.read_text(), "{}\n")

    def test_duplicate_inventory_slugs_fail_instead_of_silently_dropping_a_title(self):
        path = self.root / "earnalism_book_inventory_for_launch.csv"
        with path.open("a") as handle:
            handle.write("prepared,Duplicate,eng\n")
        with self.assertRaisesRegex(ValueError, "duplicate catalogue slug"):
            self.run_processor()

    def test_outputs_cannot_be_written_into_public_runtime_packages(self):
        command = [sys.executable, str(Path(__file__).with_name("process_full_catalogue.py")), "--root", str(self.root), "--output", str(self.package)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private intelligence directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
