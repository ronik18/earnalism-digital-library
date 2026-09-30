import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import sys
import subprocess
import tempfile
import textwrap
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

    def run_candidate_handoff(self, error=None):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/catalogue-compliance-go-live.yml"
        section = workflow.read_text().split("      - name: Create compliance candidate PR or retain bridge handoff\n", 1)[1]
        script = textwrap.dedent(section.split("run: |\n", 1)[1].split("\n      - name:", 1)[0])
        script = script[script.index('PR_HEAD_SHA="$(git rev-parse HEAD)"'):]
        folder = Path(self.folder.name)
        script = script.replace("/tmp/", str(folder) + "/")
        summary = {'held_before':224,'held_after':224,'live_before':7,'live_after':7,'blockers_before':919,'blockers_after':912,'newly_live':[],'new_registry_decisions':[]}
        (folder / "campaign-summary.json").write_text(json.dumps(summary))
        response = "printf '%s\\n' 'https://github.com/fixture/repo/pull/42'" if error is None else "printf '%s\\n' " + shlex.quote(error) + " >&2; return 1"
        prefix = "set -euo pipefail\ngit() { if [[ \"$1 $2\" == 'rev-parse HEAD' ]]; then printf '%s\\n' '" + "b"*40 + "'; elif [[ \"$*\" == *' push '* ]]; then :; else return 72; fi; }\ngh() { if [[ \"$1 $2\" == 'pr create' ]]; then " + response + "; elif [[ \"$1 $2\" == 'issue comment' ]]; then :; else return 73; fi; }\n"
        env = {'PATH':str(Path(sys.executable).parent) + os.pathsep + os.defpath,'GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'123','GITHUB_REPOSITORY':'fixture/repo','BRANCH':'codex/main-approved-integration','TRACKING_ISSUE':'477','GITHUB_ENV':str(folder/'github-env'),'GITHUB_OUTPUT':str(folder/'github-output')}
        result = subprocess.run(['bash','-c',prefix + script],cwd=self.root,env=env,text=True,capture_output=True)
        return result, folder / "earnalism-catalogue-bridge-handoff.json", folder / "github-env"

    def test_actions_policy_rejection_retains_exact_candidate_without_merge_claim(self):
        result, handoff, github_env = self.run_candidate_handoff("GraphQL: GitHub Actions is not permitted to create or approve pull requests")
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(handoff.read_text())
        self.assertEqual(record['candidate_head'], 'b'*40)
        self.assertEqual(record['source_head'], 'a'*40)
        self.assertEqual(record['status'], 'VALIDATED_CANDIDATE_AWAITING_BRIDGE_PR_AND_PROTECTED_MERGE')
        self.assertNotIn('PR_NUMBER=', github_env.read_text())
        self.assertNotIn('MERGED_SHA=', github_env.read_text())

    def test_unexpected_pr_error_fails_without_handoff_or_merge(self):
        result, handoff, github_env = self.run_candidate_handoff("GraphQL: Resource not accessible by integration")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(handoff.exists())
        self.assertNotIn('PR_NUMBER=', github_env.read_text())

    def test_normal_pr_creation_retains_required_check_handoff(self):
        result, handoff, github_env = self.run_candidate_handoff()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(handoff.exists())
        self.assertIn('PR_NUMBER=42\n', github_env.read_text())
        self.assertNotIn('MERGED_SHA=', github_env.read_text())


if __name__ == "__main__":
    unittest.main()
