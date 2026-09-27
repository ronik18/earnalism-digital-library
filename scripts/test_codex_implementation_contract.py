import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.autonomy_worker import load_codex_result


class CodexImplementationContractTests(unittest.TestCase):
    def test_empty_result_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "codex-result.json"
            path.write_text(json.dumps({"summary": ""}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no usable implementation result"):
                load_codex_result(path)

    def test_unknown_task_type_is_rejected(self):
        proc = subprocess.run(["python", "scripts/autonomy_worker.py", "--task-id", "x", "--task-type", "unknown", "--candidate-sha", "0" * 40, "--generation", "1", "--attempt", "1", "--output", "/tmp/worker-contract-test.json"], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("task type is not approved", proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
