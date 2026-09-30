"""Preserve derived reports without laundering unrelated changes or source."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.catalogue_compliance_generated_evidence import CANONICAL, WORKER, preserve_generated_evidence


class GeneratedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True)
        folder = self.root / CANONICAL
        folder.mkdir(parents=True)
        (folder / "catalogue_state.json").write_text('{"historical":true}\n')
        package = self.root / "data/controlled_publications/fixture"
        package.mkdir(parents=True)
        (package / "checksum_manifest.json").write_text('{"fixture":"old"}\n')
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "fixture"], check=True)

    def preserve(self):
        archive = preserve_generated_evidence(self.root)
        self.addCleanup(shutil.rmtree, archive)
        return archive

    def test_retains_generated_bytes_and_proposal_while_restoring_approved_reports(self):
        canonical = self.root / CANONICAL
        (canonical / "catalogue_state.json").write_text('{"current":true}\n')
        (canonical / "processing_checksums.json").write_text('{"derived":true}\n')
        worker = self.root / WORKER
        worker.mkdir()
        (worker / "catalogue_state.json").write_text('{"worker":true}\n')
        proposal = self.root / "data/controlled_publications/fixture/checksum_manifest.json"
        proposal.write_text('{"fixture":"proposed"}\n')
        archive = self.preserve()
        self.assertEqual((archive / canonical.name / "catalogue_state.json").read_text(), '{"current":true}\n')
        self.assertEqual((archive / worker.name / "catalogue_state.json").read_text(), '{"worker":true}\n')
        self.assertEqual((canonical / "catalogue_state.json").read_text(), '{"historical":true}\n')
        self.assertFalse((canonical / "processing_checksums.json").exists())
        self.assertFalse(worker.exists())
        self.assertEqual(proposal.read_text(), '{"fixture":"proposed"}\n')
        self.assertIn(b'proposed', (archive / "held-title-proposal.diff").read_bytes())
        status = subprocess.check_output(["git", "-C", str(self.root), "status", "--porcelain"], text=True)
        self.assertIn("checksum_manifest.json", status)
        self.assertNotIn("earnalism_intelligence", status)

    def test_tracked_alternate_output_is_not_moved(self):
        worker = self.root / WORKER
        worker.mkdir()
        (worker / "source.json").write_text('{}')
        subprocess.run(["git", "-C", str(self.root), "add", WORKER], check=True)
        with self.assertRaisesRegex(ValueError, "tracked source"):
            self.preserve()
        self.assertTrue((worker / "source.json").is_file())

    def test_symlinks_and_non_report_files_are_rejected_without_source_loss(self):
        worker = self.root / WORKER
        worker.mkdir()
        bad = worker / "unexpected.py"
        bad.write_text("synthetic non-report source\n")
        with self.assertRaisesRegex(ValueError, "non-report"):
            self.preserve()
        self.assertTrue(bad.is_file())
        bad.unlink()
        bad.symlink_to(self.root / CANONICAL / "catalogue_state.json")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.preserve()
        self.assertTrue(bad.is_symlink())


if __name__ == "__main__":
    unittest.main()
