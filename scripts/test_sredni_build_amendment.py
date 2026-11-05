"""Pure dummy budget/approval tests. No native journal, provider or credentials."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
from scripts import first_guard_pair as p
from scripts import india_release_provider_adapter as adapter

class BuildAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.scope={'baseline_sha256':'b'*64,'owner_scope_receipt_sha256':'be09149041167583000ec12183729c1622c1b74e5326d9aef2d96c8b2d768611'}
        self.base={'historical_terminal_operations':{}}
        self.amendment={'schema':'earnalism.native_build_amendment.v1','owner_receipt_sha256':p.SREDNI_BUILD_OWNER_RECEIPT_SHA256,'original_scope_sha256':p.digest(self.scope),'original_baseline_sha256':self.scope['baseline_sha256'],'title':'sredni-vashtar','additional_builds':1,'cumulative_build_maximum':2}
    def row(self,i,action='stage_frontend',amended=False,state='APPLIED_VERIFIED'):
        binding={'native_action_scope':self.scope}
        if amended:binding['native_build_amendment']=copy.deepcopy(self.amendment)
        return {'operation_id':str(i)*64,'action':action,'binding':binding,'state':state},'c'*64
    def count(self,rows,candidate=None):
        return p.count_scoped_intents(self.scope,self.base,rows,candidate=candidate)
    def test_exact_owner_message_retained(self):
        raw=(Path(__file__).resolve().parents[1]/'internal/legal/sredni_native_build_amendment_owner_acceptance.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),p.SREDNI_BUILD_OWNER_RECEIPT_SHA256)
        receipt=json.loads(raw)
        self.assertFalse(receipt['scope']['counter_reset']);self.assertFalse(receipt['scope']['window_renewal'])
        self.assertEqual(receipt['scope']['bicharak'],'OWNER_HOLD')
    def test_old_cap_unchanged_without_amendment(self):
        with self.assertRaisesRegex(ValueError,'allowance exhausted'):self.count([self.row(1),self.row(2)])
        self.assertEqual(p.ACTION_LIMITS,{'backend':3,'frontend':3,'stage':1})
    def test_second_build_preserves_old_intent(self):
        old=self.row(1);before=copy.deepcopy(old)
        self.assertEqual(self.count([old],self.row(2,amended=True)[0]),{'backend':0,'frontend':2,'stage_builds':2})
        self.assertEqual(old,before)
    def test_third_build_and_fourth_frontend_rejected(self):
        for rows in ([self.row(1),self.row(2,amended=True),self.row(3,amended=True)], [self.row(1),self.row(2,amended=True),self.row(3,'promote_frontend'),self.row(4,'restore_frontend')]):
            with self.assertRaisesRegex(ValueError,'allowance exhausted'):self.count(rows)
    def test_two_builds_and_promotion_fit_three_actions(self):
        self.assertEqual(self.count([self.row(1),self.row(2,amended=True),self.row(3,'promote_frontend')]),{'backend':0,'frontend':3,'stage_builds':2})
    def test_unknown_build_still_consumed(self):
        self.assertEqual(self.count([self.row(1),self.row(2,amended=True,state='WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED')])['stage_builds'],2)
        with self.assertRaises(ValueError):self.count([self.row(1),self.row(2,amended=True,state='UNKNOWN')],self.row(3,amended=True)[0])
    def test_mutations_rejected(self):
        for key,value in [('owner_receipt_sha256','d'*64),('title','bicharak'),('original_scope_sha256','e'*64),('original_baseline_sha256','f'*64),('additional_builds',True),('additional_builds',2),('cumulative_build_maximum',3)]:
            x=copy.deepcopy(self.amendment);x[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):p.validate_build_amendment(self.scope,x)
        x={**self.amendment,'reset':True}
        with self.assertRaises(ValueError):p.validate_build_amendment(self.scope,x)
    def test_other_original_owner_scope_rejected(self):
        scope={**self.scope,'owner_scope_receipt_sha256':'a'*64}
        x={**self.amendment,'original_scope_sha256':p.digest(scope)}
        with self.assertRaises(ValueError):p.validate_build_amendment(scope,x)
    def test_protected_approval_must_bind_extension(self):
        binding={'native_action_scope':self.scope,'native_build_amendment':self.amendment}
        with self.assertRaisesRegex(ValueError,'actual second-build amendment'):adapter.validate_approval('stage_frontend',binding,{},True,None)
    def test_amendment_only_on_exact_stage_and_no_unbound_successor(self):
        for action in ('release_backend','promote_frontend','restore_frontend'):
            with self.subTest(action=action),self.assertRaisesRegex(ValueError,'only to exact stage'):
                self.count([self.row(1),self.row(2,action,amended=True)])
        with self.assertRaisesRegex(ValueError,'Second stage must itself bind'):
            self.count([self.row(1,amended=True)],self.row(2)[0])
    def test_actual_observer_binding_is_required_for_second_build(self):
        from scripts.test_first_guard_pair import fixture
        with tempfile.TemporaryDirectory() as directory:
            journal=Path(directory)/'journal';journal.mkdir(mode=0o700);fixture(journal)
            baseline=json.loads((journal/'.native-action-baseline.receipt').read_text())
            baseline['owner_scope_receipt_sha256']=self.scope['owner_scope_receipt_sha256']
            identity={'domain':'earnalism.native_action_scope.v1',**{k:baseline[k] for k in ('owner_scope_receipt_sha256','intended_closed_source_sha','operations_journal_identity_sha256')}}
            baseline['release_scope_id']=p.digest(identity)
            scope={k:baseline[k] for k in p.SCOPE_KEYS-{'schema','baseline_sha256'}}|{'schema':'earnalism.native_action_scope.v1','baseline_sha256':p.digest(baseline)}
            adapter._durable_json(journal/'.native-action-baseline.receipt',baseline)
            adapter._durable_json(journal/'.native-action-scope.claim',{'schema':'earnalism.native_action_scope_claim.v1','scope':scope})
            for path in journal.glob('*.json'):
                old=json.loads(path.read_text())
                if 'binding' in old:
                    old['binding']['native_action_scope']=scope;adapter._durable_json(path,old)
            amendment={**self.amendment,'original_scope_sha256':p.digest(scope),'original_baseline_sha256':scope['baseline_sha256']}
            binding={'source_sha':'2'*40,'native_action_scope':scope,'native_build_amendment':amendment}
            actual={'native_action_scope':scope,'native_action_baseline_sha256':scope['baseline_sha256'],'native_action_scope_authorization':'ACTUAL_ROOT_PREWRITE_BASELINE'}
            instance=adapter.ProviderAdapter(journal,owner_authorized=False)
            with self.assertRaisesRegex(ValueError,'second-build amendment observation required'):
                instance._native_budget('stage_frontend',binding,actual=actual)
            actual['native_build_amendment_sha256']=p.digest(amendment)
            self.assertEqual(instance._native_budget('stage_frontend',binding,actual=actual)['stage_builds'],2)
            self.assertEqual(json.loads((journal/'.native-action-baseline.receipt').read_text()),baseline)
    def test_shared_parent_is_rejected_without_weakening_custody(self):
        with tempfile.TemporaryDirectory() as directory:
            parent=Path(directory);journal=parent/'journal';journal.mkdir(mode=0o700)
            parent.chmod(0o777)
            try:
                with self.assertRaisesRegex(ValueError,'Private owner-matched journal custody required'):
                    adapter._operation_journal_identity(journal)
            finally:parent.chmod(0o700)
    def test_changed_historical_baseline_is_not_exempt(self):
        row=self.row(1);self.base['historical_terminal_operations']={'1'*64:'d'*64}
        with self.assertRaisesRegex(ValueError,'Historical terminal baseline changed'):self.count([row,self.row(2,amended=True)])
class SourceSuccessorTests(unittest.TestCase):
    def setUp(self):
        BuildAmendmentTests.setUp(self)
        self.scope['intended_closed_source_sha']='6'*40
        self.proof={'controller_source_sha':'a'*40,'bootstrap_source_sha':'b'*40,'scope':'SOURCE_ONLY_NOT_PROVIDER_OR_APPROVAL_QUALIFICATION'}
        self.value={'schema':'earnalism.native_source_successor.v1','owner_receipt_sha256':p.SREDNI_BUILD_OWNER_RECEIPT_SHA256,'original_scope_sha256':p.digest(self.scope),'original_baseline_sha256':self.scope['baseline_sha256'],'original_closed_source_sha':self.scope['intended_closed_source_sha'],'source_pair':self.proof}
        self.binding={'source_root':'/dummy/offline','controller_source_sha':'a'*40,'source_sha':'b'*40,'native_action_scope':self.scope,'native_source_successor':self.value}
    def test_exact_source_successor_does_not_mutate_scope(self):
        before=copy.deepcopy(self.scope)
        with patch('scripts.purchase_guard_source.validate_paired_source',return_value=self.proof):
            self.assertEqual(p.validate_source_successor(self.scope,self.binding),self.value)
        self.assertEqual(self.scope,before)
    def test_wrong_source_or_old_lineage_rejected(self):
        for key,value in [('original_closed_source_sha','c'*40),('original_baseline_sha256','d'*64),('owner_receipt_sha256','e'*64)]:
            binding=copy.deepcopy(self.binding);binding['native_source_successor'][key]=value
            with self.subTest(key=key),patch('scripts.purchase_guard_source.validate_paired_source',return_value=self.proof),self.assertRaises(ValueError):p.validate_source_successor(self.scope,binding)
        for key in ('source_sha','controller_source_sha'):
            binding=copy.deepcopy(self.binding);binding[key]='f'*40
            with self.subTest(key=key),patch('scripts.purchase_guard_source.validate_paired_source',return_value=self.proof),self.assertRaises(ValueError):p.validate_source_successor(self.scope,binding)
    def test_source_successor_never_substitutes_protected_approval(self):
        with patch('scripts.purchase_guard_source.validate_paired_source',return_value=self.proof),self.assertRaisesRegex(ValueError,'Protected approval must bind exact source successor'):
            adapter.validate_approval('release_guarded_bootstrap',self.binding,{},True,None)
        with self.assertRaisesRegex(ValueError,'only to exact guarded bootstrap'):
            adapter.validate_approval('release_backend',self.binding,{},True,None)

if __name__=='__main__':unittest.main()
