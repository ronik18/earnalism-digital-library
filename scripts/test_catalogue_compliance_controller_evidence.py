import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("controller_evidence", Path(__file__).with_name("catalogue_compliance_controller_evidence.py"))
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class ControllerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name) / "repo"
        self.root.mkdir()
        self.baseline = Path(self.folder.name) / "baseline.json"
        self.report = self.root / evidence.REPORT
        self.original = b"# Smoke report\n- latest_smoke_status: PASS\n- latest_smoke_output: output/ux-journey-regression/2026-08-16T05-17-57-156Z\n- latest_test_auth_state_status: NOT_CONFIGURED\n"
        self.fresh = self.original.replace(b"2026-08-16T05-17-57-156Z", b"2026-09-30T22-39-23-221Z")
        self.report.write_bytes(self.original)
        (self.root / "source.txt").write_text("approved source\n")
        for args in (("init", "-q"), ("config", "user.name", "fixture"), ("config", "user.email", "fixture@example.invalid"), ("add", "."), ("commit", "-qm", "baseline")):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        (self.root / "source.txt").write_text("validated proposal\n")
        self.archives = []

    def tearDown(self):
        for archive in self.archives:
            shutil.rmtree(archive)
        self.folder.cleanup()

    def test_retains_exact_new_report_and_preserves_validated_proposal(self):
        evidence.snapshot(self.root, self.baseline)
        self.report.write_bytes(self.fresh)
        archive = evidence.retain(self.root, self.baseline)
        self.archives.append(archive)
        self.assertEqual((archive / evidence.REPORT).read_bytes(), self.fresh)
        self.assertEqual(self.report.read_bytes(), self.original)
        self.assertEqual((self.root / "source.txt").read_text(), "validated proposal\n")

    def test_authentication_or_result_claim_changes_are_rejected_without_restoration(self):
        evidence.snapshot(self.root, self.baseline)
        changed = self.fresh.replace(b"NOT_CONFIGURED", b"PASS")
        self.report.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, "report facts"):
            evidence.retain(self.root, self.baseline)
        self.assertEqual(self.report.read_bytes(), changed)

    def test_worker_report_edits_are_rejected_at_snapshot(self):
        self.report.write_bytes(self.fresh)
        with self.assertRaisesRegex(ValueError, "worker changed"):
            evidence.snapshot(self.root, self.baseline)
        self.assertFalse(self.baseline.exists())

    def test_tracked_source_change_after_validation_is_rejected_and_preserved(self):
        evidence.snapshot(self.root, self.baseline)
        (self.root / "source.txt").write_text("unexpected later change\n")
        with self.assertRaisesRegex(ValueError, "source changed"):
            evidence.retain(self.root, self.baseline)
        self.assertEqual((self.root / "source.txt").read_text(), "unexpected later change\n")

    def test_untracked_source_change_after_validation_is_rejected_and_preserved(self):
        (self.root / "new-source.txt").write_text("validated new file\n")
        evidence.snapshot(self.root, self.baseline)
        (self.root / "new-source.txt").write_text("unexpected later bytes\n")
        with self.assertRaisesRegex(ValueError, "source changed"):
            evidence.retain(self.root, self.baseline)
        self.assertEqual((self.root / "new-source.txt").read_text(), "unexpected later bytes\n")

    def test_report_symlink_is_rejected_without_touching_target(self):
        evidence.snapshot(self.root, self.baseline)
        target = Path(self.folder.name) / "external.txt"
        target.write_bytes(self.fresh)
        self.report.unlink()
        self.report.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "regular tracked"):
            evidence.retain(self.root, self.baseline)
        self.assertEqual(target.read_bytes(), self.fresh)


if __name__ == "__main__":
    unittest.main()
