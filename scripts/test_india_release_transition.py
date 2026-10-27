import copy
import json
from pathlib import Path
import unittest
from scripts.india_release_transition import STAGES, next_stage, validate_plan


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((Path(__file__).resolve().parents[1] /
            'internal/legal/india_release_transition.prepared.json').read_text())

    def test_preparation_never_enables_execution_even_with_all_modeled_evidence(self):
        evidence = {key: True for _, _, keys in STAGES for key in keys}
        done = []
        for name, _, _ in STAGES:
            result = next_stage(self.plan, done, evidence)
            self.assertEqual(result['proposed_stage'], name)
            self.assertFalse(result['execution_enabled'])
            self.assertFalse(result['hold'])
            done.append(name)
        self.assertEqual(next_stage(self.plan, done, evidence)['status'],
                         'SIMULATION_COMPLETE_NOT_PRODUCTION_ACCEPTANCE')

    def test_backend_cannot_precede_frontend(self):
        plan = copy.deepcopy(self.plan)
        plan['order'][2], plan['order'][5] = plan['order'][5], plan['order'][2]
        with self.assertRaises(ValueError): validate_plan(plan)
        with self.assertRaises(ValueError): next_stage(self.plan, ['release_backend'], {})

    def test_each_stage_holds_on_every_missing_prerequisite(self):
        done = []
        for name, _, keys in STAGES:
            full = {key: True for key in keys}
            for key in keys:
                result = next_stage(self.plan, done, {**full, key: False})
                self.assertIn(key, result['hold'])
                self.assertFalse(result['execution_enabled'])
            done.append(name)

    def test_unknown_write_outcome_blocks_all_subsequent_actions(self):
        result = next_stage(self.plan, ['source'], {'unknown_write_outcome': True})
        self.assertIsNone(result['proposed_stage'])
        self.assertEqual(result['hold'], ['read_only_reconciliation'])

    def test_unsafe_rollback_and_automatic_retry_denied(self):
        for key in ('restore_unguarded_backend', 'restore_unsigned_frontend_against_guarded_backend'):
            plan = copy.deepcopy(self.plan); plan['rollback'][key] = True
            with self.assertRaises(ValueError): validate_plan(plan)
        for key in ('execution_enabled', 'automatic_retry', 'paid_sessions'):
            plan = copy.deepcopy(self.plan); plan[key] = True
            with self.assertRaises(ValueError): validate_plan(plan)


if __name__ == '__main__': unittest.main()
