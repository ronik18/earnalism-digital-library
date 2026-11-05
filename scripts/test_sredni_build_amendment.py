"""Pure dummy budget/approval tests. No native journal, provider or credentials."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
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
    def test_changed_historical_baseline_is_not_exempt(self):
        row=self.row(1);self.base['historical_terminal_operations']={'1'*64:'d'*64}
        with self.assertRaisesRegex(ValueError,'Historical terminal baseline changed'):self.count([row,self.row(2,amended=True)])
if __name__=='__main__':unittest.main()
