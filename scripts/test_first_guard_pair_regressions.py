"""Behavioral regression tests; temporary dummy receipts, no provider calls.

May be installed as scripts/test_first_guard_pair_regressions.py.
Fixtures are reused by composition so their tests are not inherited/repeated.
"""
import copy
import unittest
from unittest.mock import patch
from scripts import india_release_provider_adapter as a
from scripts import first_guard_pair as pair
from scripts import test_first_guard_pair as fixtures

class FirstGuardFinalizationRegressions(unittest.TestCase):
    setUp = fixtures.RepairTests.setUp
    tearDown = fixtures.RepairTests.tearDown
    component = fixtures.RepairTests.component
    child = fixtures.RepairTests.child
    make_child = fixtures.RepairTests.make_child

    def full_pair_observation(self):
        pending = self.adapter._read_pending()
        child = a._read_journal(self.j / (pending['child_operation_id'] + '.json'))
        flags = ('reader_public_preview_verified', 'reader_protected_entitlement_verified',
                 'reader_free_pilot_entitlement_preserved', 'listener_protected_accounting_preserved',
                 'native_can_rollback', 'config_compatible', 'existing_reader_listener_preserved')
        return {**self.actual,
            'component_receipt_sha256': pending['component_receipt_sha256'],
            'child_record_sha256': pair.digest(child), 'both_aliases_verified': True,
            'paired_reader_listener_financial_preserved': True,
            'recovery_receipt_sha256': '9' * 64,
            'guarded_backend_deployment_id': self.actual['deployment_id'],
            'serving_frontend_deployment_id': 'dpl_NEW',
            'serving_frontend_source_sha': '2' * 40,
            **{name: True for name in flags}}

    def test_invalid_original_baseline_cannot_finalize_or_retire_pending(self):
        self.make_child()
        actual = self.full_pair_observation()
        self.adapter.observe = lambda *args: actual
        parent = self.j / (self.r['operation_id'] + '.json')
        parent_bytes = parent.read_bytes()
        pending_bytes = (self.j / '.first-guard-pending').read_bytes()
        a._durable_json(self.j / '.native-action-baseline.receipt', {'tampered': True})
        with self.assertRaises(ValueError):
            self.adapter.finalize_first_guard_pair(self.r['operation_id'])
        self.assertEqual(parent.read_bytes(), parent_bytes)
        self.assertEqual((self.j / '.first-guard-pending').read_bytes(), pending_bytes)
        self.assertFalse((self.j / ('.first-guard-final-' + self.r['operation_id'] + '.receipt')).exists())

    def test_retirement_crash_cannot_skip_original_baseline_on_recovery(self):
        self.make_child()
        actual = self.full_pair_observation()
        self.adapter.observe = lambda *args: actual
        unlink = a.os.unlink
        def crash_retirement(name, *args, **kwargs):
            if name == '.first-guard-pending':
                raise OSError('Dummy crash after terminal parent, before pending retirement')
            return unlink(name, *args, **kwargs)
        with patch.object(a.os, 'unlink', side_effect=crash_retirement), self.assertRaises(OSError):
            self.adapter.finalize_first_guard_pair(self.r['operation_id'])
        parent = self.j / (self.r['operation_id'] + '.json')
        terminal_bytes = parent.read_bytes()
        self.assertEqual(a._read_journal(parent)['state'], 'APPLIED_VERIFIED')
        pending_bytes = (self.j / '.first-guard-pending').read_bytes()
        a._durable_json(self.j / '.native-action-baseline.receipt', {'tampered': True})
        with self.assertRaises(ValueError):
            self.adapter.finalize_first_guard_pair(self.r['operation_id'])
        self.assertEqual(parent.read_bytes(), terminal_bytes)
        self.assertEqual((self.j / '.first-guard-pending').read_bytes(), pending_bytes)

    def test_parent_frontend_source_cannot_escape_owner_accepted_projection(self):
        binding = copy.deepcopy(self.b)
        binding['frontend_source_sha'] = '9' * 40
        with self.assertRaises(ValueError):
            pair.validate(binding)

    def test_parent_frontend_deployment_cannot_escape_owner_accepted_projection(self):
        binding = copy.deepcopy(self.b)
        binding['frontend_deployment_id'] = 'dpl_UNEXPECTED'
        with self.assertRaises(ValueError):
            pair.validate(binding)

if __name__ == '__main__':
    unittest.main(verbosity=2)
