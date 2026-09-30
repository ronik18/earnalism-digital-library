"""Exercise the real controller selection without granting publication authority."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


def held(slug, blockers):
    return {"slug": slug, "title": slug, "state": "EXTERNAL_ACTION_REQUIRED", "blockers": blockers}


class CatalogueBatchTests(unittest.TestCase):
    def select(self, titles):
        workflow = (ROOT / ".github/workflows/catalogue-compliance-go-live.yml").read_text()
        section = workflow.split("      - name: Select bounded compliance batch\n", 1)[1]
        source = textwrap.dedent(section.split("python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0])
        with tempfile.TemporaryDirectory() as folder:
            state, output = Path(folder) / "state.json", Path(folder) / "batch.json"
            state.write_text(json.dumps({"titles": titles}))
            source = source.replace("Path('/tmp/catalogue-before.json')", "Path(" + repr(str(state)) + ")")
            source = source.replace("Path('/tmp/earnalism-catalogue-campaign-batch.json')", "Path(" + repr(str(output)) + ")")
            subprocess.run([sys.executable, "-c", source], check=True, capture_output=True, text=True, timeout=30)
            return json.loads(output.read_text())

    def test_exact_checksum_repairs_precede_approval_holds_with_fewer_blockers(self):
        approval = held("a-approval", ["Rights: verification_status must be approved before publishing."])
        checksum = held("z-checksum", ["ACCEPTED_DECISION_MISSING", "ACCEPTED_HASH_BOUND_TEXT_USE_DECISION_REQUIRED", "RETAINED_CHECKSUM_MISMATCH:public_book.json"])
        result = self.select([approval, checksum])
        self.assertEqual([item["slug"] for item in result["candidates"]], ["z-checksum", "a-approval"])
        self.assertEqual(result["candidates"][0]["blockers"], checksum["blockers"])

    def test_existing_live_titles_are_excluded_and_limits_remain_bounded(self):
        titles = [held(f"held-{i:03d}", ["ACCEPTED_DECISION_MISSING"]) for i in range(30)]
        titles.append({"slug": "live", "state": "READER_ONLY_LIVE_APPROVED", "blockers": []})
        result = self.select(titles)
        self.assertEqual(result["candidate_count"], 20)
        self.assertEqual(len(result["candidates"]), 20)
        self.assertEqual(result["max_titles_to_modify"], 5)
        self.assertNotIn("live", [item["slug"] for item in result["candidates"]])

    def test_selection_is_stable_when_inventory_order_changes(self):
        titles = [held(slug, ["RETAINED_CHECKSUM_MISMATCH:public_book.json"]) for slug in ["z", "b", "a"]]
        self.assertEqual(self.select(titles), self.select(list(reversed(titles))))

    def test_prepared_evidence_precedes_missing_packages_without_clearing_holds(self):
        prepared = held("z-prepared", ["ACCEPTED_DECISION_MISSING"])
        missing = held("a-missing", ["CLEARED_SOURCE_AND_READER_PACKAGE_MISSING"])
        result = self.select([missing, prepared])
        self.assertEqual(result["candidates"], [{"slug": item["slug"], "title": item["title"], "blockers": item["blockers"]} for item in [prepared, missing]])


if __name__ == "__main__":
    unittest.main()
