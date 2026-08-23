from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_public_page_reference_regions import main


ROOT = Path(__file__).resolve().parents[1]


class PublicPageReferenceRegionsTests(unittest.TestCase):
    def test_audit_rejects_capture_with_horizontal_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "result.json"
            captures = ROOT / "uat/evidence/actual-redesign/convergence-v2/current/capture.json"
            rows = json.loads(captures.read_text())
            rows[0]["scrollWidth"] = rows[0]["clientWidth"] + 1
            altered = Path(tempdir) / "capture.json"
            altered.write_text(json.dumps(rows))
            self.assertEqual(main_args(["--root", str(ROOT), "--captures", str(altered), "--output", str(output)]), 1)


def main_args(args: list[str]) -> int:
    import sys
    previous = sys.argv
    try:
        sys.argv = ["audit_public_page_reference_regions.py", *args]
        return main()
    finally:
        sys.argv = previous


if __name__ == "__main__":
    unittest.main()
