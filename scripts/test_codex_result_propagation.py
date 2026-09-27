import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scripts.autonomy_worker import load_codex_result


class CodexResultPropagationTests(unittest.TestCase):
    def test_empty_official_result_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "codex-result.json"
            result.write_text(json.dumps({"executor": "openai-codex-action", "summary": ""}))
            with self.assertRaisesRegex(ValueError, "no usable implementation result"):
                load_codex_result(result)

    def test_reviewer_rejects_missing_summary(self):
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        worker = {"tested_revision": actual, "generation": 1, "attempt": 1, "state": "REVIEW", "tests": [{"exit_code": 0}], "codex": {"summary": ""}}
        with tempfile.TemporaryDirectory() as tmp:
            worker_path = Path(tmp) / "worker.json"
            output_path = Path(tmp) / "review.json"
            worker_path.write_text(json.dumps(worker))
            proc = subprocess.run([sys.executable, "scripts/autonomy_reviewer.py", "--task-id", "fixture", "--candidate-sha", actual, "--generation", "1", "--attempt", "1", "--worker-result", str(worker_path), "--output", str(output_path), "--task-type", "codex-implementation-fixture"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(output_path.read_text())["decision"], "CHANGES_REQUIRED")


if __name__ == "__main__":
    unittest.main()
