"""Keep paid proposal work opt-in and independent of release validation."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/catalogue-compliance-go-live.yml"


class CatalogueCostContract(unittest.TestCase):
    def test_main_pr_and_schedules_cannot_start_a_paid_proposal_pass(self):
        trigger = WORKFLOW.read_text().split("\non:\n", 1)[1].split("\nconcurrency:\n", 1)[0]
        self.assertIn("  workflow_dispatch:\n", trigger)
        self.assertIsNone(re.search(r"^  (?:push|pull_request|schedule|workflow_run):", trigger, re.M))

    def test_manual_dispatch_requires_explicit_budget_opt_in_and_open_issue(self):
        source = WORKFLOW.read_text()
        inputs = source.split("      run_paid_implementation:\n", 1)[1].split("\nconcurrency:", 1)[0]
        self.assertIn("type: boolean", inputs)
        self.assertIn("default: false", inputs)
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.run_paid_implementation == true", source)
        worker = source.split("  compliance-campaign:\n", 1)[1]
        self.assertIn("needs: campaign-policy", worker)
        self.assertIn("if: needs.campaign-policy.outputs.is_open == 'true'", worker)
        self.assertIn("Validate catalogue worker permission boundaries", (ROOT / ".github/workflows/regression.yml").read_text())

    def run_state_gate(self, state):
        source = WORKFLOW.read_text().split("      - name: Check campaign state\n", 1)[1]
        script = textwrap.dedent(source.split("        run: |\n", 1)[1].split("\n  compliance-campaign:\n", 1)[0])
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "github-output"
            env = {"PATH": os.defpath, "GITHUB_OUTPUT": str(output), "TRACKING_ISSUE": "477", "GITHUB_REPOSITORY": "fixture/repository", "FIXTURE_ISSUE_STATE": state}
            result = subprocess.run(["bash", "-c", 'gh() { printf "%s\\n" "$FIXTURE_ISSUE_STATE"; }\n' + script], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return output.read_text()

    def test_closed_issue_prevents_the_entire_implementation_job(self):
        self.assertEqual(self.run_state_gate("CLOSED"), "is_open=false\n")

    def test_open_issue_permits_only_the_already_opted_in_job(self):
        self.assertEqual(self.run_state_gate("OPEN"), "is_open=true\n")


if __name__ == "__main__":
    unittest.main()
