import json
import unittest
from pathlib import Path
from scripts.autonomy_bridge import plan

class BridgeTests(unittest.TestCase):
    def test_waits_for_ci(self):
        out = plan({"tasks":[{"task_id":"x","state":"WAITING_CI","checks":{}}]})
        self.assertEqual(out["actions"], [{"task_id":"x","action":"WAIT"}])

    def test_failed_ci_is_reviewed(self):
        out = plan({"tasks":[{"task_id":"x","state":"WAITING_CI","checks":{"failed":"header assertion"}}]})
        self.assertEqual(out["actions"][0]["action"], "REVIEW_FAILURE")

    def test_merge_is_fail_closed(self):
        out = plan({"tasks":[{"task_id":"x","state":"READY_FOR_MERGE","approved":True,"checks":{"all_passed":False}}]})
        self.assertEqual(out["actions"][0]["action"], "BLOCK")

    def test_owner_wait_is_not_dispatched(self):
        out = plan({"tasks":[{"task_id":"x","state":"WAITING_OWNER_PROVIDER_UPDATE"}]})
        self.assertEqual(out["actions"], [])

    def test_callback_contract_binds_revision_and_attempt(self):
        source = Path(__file__).resolve().parents[1] / "backend" / "server.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn('attempt: int = Field(ge=1)', text)
        self.assertIn('payload.tested_revision != task.get("candidate_sha", "")', text)
        self.assertIn('payload.attempt != task.get("attempt", 1)', text)
        self.assertIn('"consumed_events": {"$ne": payload.event_id}', text)

if __name__ == "__main__":
    unittest.main()
