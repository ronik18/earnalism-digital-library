import json
import unittest
from scripts.autonomy_bridge import plan, consume_result

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

    def test_duplicate_result_is_idempotent(self):
        state = {"tasks": [{"task_id": "x", "state": "REVIEW", "head": "abc", "generation": 1}]}
        result = {"task_id": "x", "tested_revision": "abc", "generation": 1, "event_id": "evt-1", "decision": "ACCEPT"}
        consume_result(state, result)
        consume_result(state, result)
        self.assertEqual(state["tasks"][0]["state"], "DONE")
        self.assertEqual(state["tasks"][0]["consumed_events"], ["evt-1"])

    def test_stale_result_cannot_advance_new_generation(self):
        state = {"tasks": [{"task_id": "x", "state": "RUNNING", "head": "new", "generation": 2}]}
        with self.assertRaises(ValueError):
            consume_result(state, {"task_id": "x", "tested_revision": "old", "generation": 1, "decision": "ACCEPT"})

if __name__ == "__main__":
    unittest.main()
