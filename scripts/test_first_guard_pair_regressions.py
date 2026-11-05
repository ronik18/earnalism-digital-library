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

    def test_missing_mode_evidence_cannot_seal_or_retire_pair(self):
        self.make_child();actual=self.full_pair_observation();actual.pop('reader_entitlement_mode_observation')
        self.adapter.observe=lambda *args:actual
        parent=self.j/(self.r['operation_id']+'.json');before=parent.read_bytes();pending=(self.j/'.first-guard-pending').read_bytes()
        with self.assertRaises(ValueError):self.adapter.finalize_first_guard_pair(self.r['operation_id'])
        self.assertEqual(parent.read_bytes(),before);self.assertEqual((self.j/'.first-guard-pending').read_bytes(),pending)
        self.assertFalse((self.j/('.first-guard-final-'+self.r['operation_id']+'.receipt')).exists())

    def test_mode_evidence_does_not_waive_protected_reader_acceptance(self):
        self.make_child();actual=self.full_pair_observation();actual['reader_protected_entitlement_verified']=False
        self.adapter.observe=lambda *args:actual
        with self.assertRaisesRegex(ValueError,'reader_protected_entitlement_verified'):
            self.adapter.finalize_first_guard_pair(self.r['operation_id'])

    def commercial_observation(self):
        import json
        raw=json.dumps({'live_approved_slugs':['dummy-pilot'],'text_access_mode':'COMMERCIAL_ENTITLEMENT','title_access_modes':{'dummy-pilot':'COMMERCIAL_ENTITLEMENT'}}).encode()
        actual=self.full_pair_observation();actual['reader_free_pilot_entitlement_preserved']=None
        actual['reader_entitlement_mode_observation']={**actual['reader_entitlement_mode_observation'],
            'controlled_launch_sha256':pair.hashlib.sha256(raw).hexdigest(),
            'effective_mode_map_sha256':pair.digest({'dummy-pilot':'COMMERCIAL_ENTITLEMENT'}),
            'active_free_pilot_slugs':[],'scenario':'NO_CONFIGURED_FULL_FREE_PILOT','free_pilot_results':[]}
        return raw,actual

    def test_commercial_not_applicable_finalizes_with_other_gates_intact(self):
        self.make_child();raw,actual=self.commercial_observation();self.adapter.observe=lambda *args:actual
        with patch.object(pair,'_committed_reader_policy',return_value=(raw,fixtures.DUMMY_READER_SERVICE)):
            result=self.adapter.finalize_first_guard_pair(self.r['operation_id'])
        self.assertEqual(result['state'],'APPLIED_VERIFIED');self.assertFalse((self.j/'.first-guard-pending').exists())
        sealed=a._read_journal(self.j/('.first-guard-final-'+self.r['operation_id']+'.receipt'))
        self.assertIsNone(sealed['actual']['reader_free_pilot_entitlement_preserved'])

    def test_mode_drift_blocks_crash_retirement_without_rewriting_terminal(self):
        self.make_child();raw,actual=self.commercial_observation();self.adapter.observe=lambda *args:actual
        unlink=a.os.unlink
        def crash(name,*args,**kwargs):
            if name=='.first-guard-pending':raise OSError('Dummy retirement crash')
            return unlink(name,*args,**kwargs)
        with patch.object(pair,'_committed_reader_policy',return_value=(raw,fixtures.DUMMY_READER_SERVICE)),patch.object(a.os,'unlink',side_effect=crash),self.assertRaises(OSError):
            self.adapter.finalize_first_guard_pair(self.r['operation_id'])
        parent=self.j/(self.r['operation_id']+'.json');before=parent.read_bytes();pending=(self.j/'.first-guard-pending').read_bytes()
        with patch.object(pair,'_committed_reader_policy',return_value=(raw+b' ',fixtures.DUMMY_READER_SERVICE)),self.assertRaises(ValueError):
            self.adapter.finalize_first_guard_pair(self.r['operation_id'])
        self.assertEqual(parent.read_bytes(),before);self.assertEqual((self.j/'.first-guard-pending').read_bytes(),pending)

class ReaderModeApplicabilityTests(unittest.TestCase):
    def setUp(self):
        import json
        self.json = json
        self.raw = json.dumps({'live_approved_slugs':['pilot','paid'],'text_access_mode':'COMMERCIAL_ENTITLEMENT','title_access_modes':{'pilot':'COMMERCIAL_ENTITLEMENT','paid':'COMMERCIAL_ENTITLEMENT'}}).encode()
        self.service = b'FREE_INDIA_READER_SLUGS = frozenset({"pilot"})'
        self.binding = {'source_sha':'a'*40,'source_delivery_sha256':'b'*64}
        self.actual = {'runtime_sha256':'b'*64,'source_attestation_matches':True,'reader_free_pilot_entitlement_preserved':None}
        self.real_loader = pair._committed_reader_policy
        self.loader = patch.object(pair,'_committed_reader_policy',side_effect=lambda _: (self.raw,self.service))
        self.loader.start(); self.addCleanup(self.loader.stop)
        self.proof = {'schema':'earnalism.reader_entitlement_mode_observation.v1','source_sha':'a'*40,'runtime_sha256':'b'*64,'controlled_launch_sha256':pair.hashlib.sha256(self.raw).hexdigest(),'effective_mode_map_sha256':pair.digest({'paid':'COMMERCIAL_ENTITLEMENT','pilot':'COMMERCIAL_ENTITLEMENT'}),'active_free_pilot_slugs':[],'scenario':'NO_CONFIGURED_FULL_FREE_PILOT','free_pilot_results':[],'receipt_sha256':'c'*64}
        self.actual['reader_entitlement_mode_observation'] = self.proof
    def validate(self):
        return pair.validate_reader_mode_preservation(self.binding,self.actual)
    def active(self):
        config=self.json.loads(self.raw); config['title_access_modes']['pilot']='PILOT_FULL_FREE';self.raw=self.json.dumps(config).encode()
        self.proof.update(controlled_launch_sha256=pair.hashlib.sha256(self.raw).hexdigest(),effective_mode_map_sha256=pair.digest({'paid':'COMMERCIAL_ENTITLEMENT','pilot':'PILOT_FULL_FREE'}),active_free_pilot_slugs=['pilot'])
    def test_commercial_is_explicit_not_applicable_not_free_pass(self):
        self.assertEqual(self.validate()['scenario'],'NO_CONFIGURED_FULL_FREE_PILOT')
        self.assertIsNone(self.actual['reader_free_pilot_entitlement_preserved'])
    def test_no_mode_proof_cannot_use_legacy_boolean(self):
        self.actual.pop('reader_entitlement_mode_observation');self.actual['reader_free_pilot_entitlement_preserved']=True
        with self.assertRaises(ValueError):self.validate()
    def test_inactive_pilot_cannot_fabricate_free_pass(self):
        self.actual['reader_free_pilot_entitlement_preserved']=True
        with self.assertRaises(ValueError):self.validate()
    def test_active_pilot_cannot_use_not_applicable(self):
        self.active()
        with self.assertRaises(ValueError):self.validate()
    def test_active_pilot_requires_exact_actual_results(self):
        self.active();self.actual['reader_free_pilot_entitlement_preserved']=True
        self.proof.update(scenario='ACTIVE_FREE_PILOTS_VERIFIED',free_pilot_results=[{'slug':'pilot','entitlement_kind':'india_pilot_free_text','status':'VERIFIED','receipt_sha256':'d'*64}])
        self.validate();self.proof['free_pilot_results'][0]['slug']='paid'
        with self.assertRaises(ValueError):self.validate()
    def test_source_runtime_policy_or_modes_drift_denied(self):
        for field in ['source_sha','runtime_sha256','controlled_launch_sha256','effective_mode_map_sha256','receipt_sha256']:
            old=self.proof[field];self.proof[field]='0'*len(old)
            with self.subTest(field=field),self.assertRaises(ValueError):self.validate()
            self.proof[field]=old
    def test_policy_changed_after_observation_denied(self):
        self.raw+=b' '
        with self.assertRaises(ValueError):self.validate()
    def test_missing_native_attestation_denied(self):
        self.actual['source_attestation_matches']=False
        with self.assertRaises(ValueError):self.validate()
    def test_legacy_global_free_fallback_still_requires_actual_proof(self):
        self.raw=self.json.dumps({'live_approved_slugs':['pilot'],'text_access_mode':'PILOT_FULL_FREE','title_access_modes':{}}).encode()
        self.proof.update(controlled_launch_sha256=pair.hashlib.sha256(self.raw).hexdigest(),effective_mode_map_sha256=pair.digest({'pilot':'PILOT_FULL_FREE'}),active_free_pilot_slugs=['pilot'])
        with self.assertRaises(ValueError):self.validate()
    def test_policy_loader_reads_bound_commit_not_changed_worktree(self):
        import tempfile,subprocess
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'backend/data').mkdir(parents=True)
            policy=root/'backend/data/controlled_launch.json';policy.write_bytes(self.raw)
            (root/'backend/reading_pass_service.py').write_bytes(self.service)
            def git(*args):return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL).decode().strip()
            git('init','-q');git('add','.');git('-c','user.name=Dummy Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Dummy source fixture')
            source=git('rev-parse','HEAD');policy.write_text('{}')
            with patch.object(pair,'_committed_reader_policy',self.real_loader):
                raw,service=pair._committed_reader_policy({'source_root':str(root),'source_sha':source})
            self.assertEqual(raw,self.raw);self.assertEqual(service,self.service)

    def test_extra_mode_fields_denied(self):
        self.proof['approved']=True
        with self.assertRaises(ValueError):self.validate()

if __name__ == '__main__':
    unittest.main(verbosity=2)
