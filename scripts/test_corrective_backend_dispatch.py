import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import india_release_provider_adapter as a
from scripts.test_india_release_provider_adapter import startup_fixture


class CorrectiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.journal=self.root/'operations';self.journal.mkdir(mode=0o700)
        self.now=datetime(2026,11,3,tzinfo=timezone.utc);self.calls=[]
        (self.root/'backend').mkdir();(self.root/'backend/startup_data_guard.py').write_bytes(b'SYNTHETIC_GUARD')
        guard_sha=hashlib.sha256(b'SYNTHETIC_GUARD').hexdigest()
        self.payload={'runtime_expected_sha256':'d'*64,'files':[{'path':'backend/inert.py','bytes':1,'sha256':'f'*64}]}
        old_binding={'source_sha':'a'*40,'source_root':str(self.root),'source_delivery_sha256':'d'*64}
        self.old_id=a.operation_identity('release_backend',old_binding)
        self.old={'operation_id':self.old_id,'action':'release_backend','binding':old_binding,
                  'state':'NOT_APPLIED_VERIFIED','reconciliation_receipt_sha256':'9'*64}
        self.old_path=self.journal/(self.old_id+'.json');a._durable_json(self.old_path,self.old,exclusive=True)
        b={'source_sha':'e'*40,'source_root':str(self.root),'source_delivery_sha256':'d'*64,
           'frontend_deployment_id':'dpl_SYNTHETIC','frontend_source_sha':'a'*40,
           'guarded_recovery_receipt_sha256':'6'*64,'backend_payload_sha256':a.digest(self.payload)}
        self.binding,self.startup=startup_fixture(b,self.now,guard_sha)
        self.c={'schema':'earnalism.corrective-backend-policy.v1','failed_operation_id':self.old_id,
                'failed_record_sha256':a.digest(self.old),'failed_reconciliation_receipt_sha256':'9'*64,
                'failed_startup_policy_sha256':'7'*64,'failed_policy_marker_identity_sha256':'2'*64,
                'policy_change_approval_sha256':'8'*64}
        self.binding['corrective_backend']=self.c

    def approval(self,binding=None,action='release_backend'):
        b=binding or self.binding
        return {'schema':'earnalism-india-protected-operation.v1','action':action,
            'binding_sha256':a.digest(b),'project':a.PROJECT,'team':a.TEAM,
            'railway_project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT,
            'territories':['IN'],'auto_deploy':False,'approved':True,
            'provider_identity_sha256':'b'*64,'config_sha256':'c'*64,'guarded_rollback_sha256':'d'*64,
            'rollback_operator':'SYNTHETIC','startup_policy_change_receipt_sha256':'8'*64,
            'approved_at':(self.now-timedelta(minutes=1)).isoformat(),
            'expires_at':(self.now+timedelta(minutes=5)).isoformat(),'provider_observed_at':self.now.isoformat()}

    def observe(self,*_):
        return {'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,'auto_deploy':False,
            'authenticated_provider_account':True,'provider_identity_sha256':'b'*64,
            'config_sha256':'c'*64,'guarded_rollback_sha256':'d'*64,
            'guarded_rollback_available':True,'guarded_recovery_receipt_sha256':'6'*64,
            'cli_version':a.CLI_VERSIONS['railway'],'frontend_signed_purchase_ready':True,
            'frontend_deployment_id':'dpl_SYNTHETIC','startup_qualified':True,
            'backend_payload_sha256':a.digest(self.payload),**copy.deepcopy(self.startup),
            'corrective_backend':{**self.c,'scope':'ACTUAL_FAILED_OPERATION_AND_APPROVED_POLICY_CHANGE',
                'policy_change_approved':True,'failed_startup_code':'STARTUP_DATA_GUARD_PUBLICATION',
                'failure_receipt_sha256':'5'*64,'approved_policy_sha256':'1'*64,
                'railway_project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT}}

    def run_fake(self,command,**kwargs):
        self.calls.append(command)
        self.assertTrue((self.journal/('_write-barrier.json')).exists())
        self.assertTrue((self.journal/('.corrective-'+self.old_id+'.claim')).exists())
        self.assertEqual(self.old,json.loads(self.old_path.read_text()))
        return SimpleNamespace(returncode=1,stdout='',stderr='SYNTHETIC_FAILURE')

    def adapter(self,observer=None,runner=None,clock=None):
        return a.ProviderAdapter(self.journal,owner_authorized=True,observe=observer or self.observe,
            run=runner or self.run_fake,clock=clock or (lambda:self.now))

    def dispatch(self,binding=None,approval=None,observer=None,action='release_backend'):
        b=binding or self.binding
        with patch.object(a.subprocess,'check_output',side_effect=[b['source_sha'],'']), \
             patch('scripts.backend_upload_payload.qualify',return_value=self.payload):
            return self.adapter(observer).perform(action,b,approval or self.approval(b,action))

    def test_one_distinct_correction_preserves_failed_record_and_never_retries(self):
        old_bytes=self.old_path.read_bytes();result=self.dispatch()
        self.assertNotEqual(result['operation_id'],self.old_id)
        self.assertEqual(result['state'],'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED')
        self.assertEqual(self.old_path.read_bytes(),old_bytes)
        with self.assertRaises(FileExistsError):self.dispatch()
        self.assertEqual(len(self.calls),1)
        # Even NOT_APPLIED on the correction cannot consume another attempt.
        obs={'scope':'ACTUAL_PROVIDER_AND_SOURCE','action':'release_backend',
            'operation_id':result['operation_id'],'source_sha':self.binding['source_sha'],
            'outcome':'NOT_APPLIED','receipt_sha256':'4'*64}
        self.adapter(lambda *_:obs).reconcile(result['operation_id'])
        changed=copy.deepcopy(self.binding);changed['source_sha']='f'*40
        changed['startup_policy_sha256']='3'*64
        with self.assertRaises(FileExistsError):self.dispatch(changed)
        self.assertEqual(len(self.calls),1)

    def test_ordinary_operation_identity_and_terminal_no_retry_are_preserved(self):
        self.assertEqual(a.operation_identity('release_backend',self.old['binding']),self.old_id)
        b={**self.old['binding'],'source_root':str(self.root/'different')}
        with self.assertRaises(FileExistsError):self.adapter().perform('release_backend',b,self.approval(b))
        self.assertEqual(self.calls,[])

    def test_changed_controller_source_without_correction_cannot_retry_same_delivered_backend(self):
        b=copy.deepcopy(self.binding);b.pop('corrective_backend')
        with self.assertRaisesRegex(ValueError,'explicit corrective binding'):self.dispatch(b)
        self.assertEqual(self.calls,[])

    def test_frontend_receipt_cannot_masquerade_as_successful_backend_correction(self):
        record={'action':'stage_frontend','state':'APPLIED_VERIFIED',
                'binding':self.binding,'operation_id':a.operation_identity('stage_frontend',self.binding),
                'reconciliation_receipt_sha256':'4'*64}
        a._durable_json(self.journal/('f'*64+'.json'),record,exclusive=True)
        b=copy.deepcopy(self.binding);b.pop('corrective_backend')
        with self.assertRaisesRegex(ValueError,'explicit corrective binding'):self.dispatch(b)
        self.assertEqual(self.calls,[])

    def test_pending_unknown_applied_tampered_and_wrong_original_id_deny(self):
        for change in [{'state':'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'},
                       {'state':'APPLIED_VERIFIED'},{'reconciliation_receipt_sha256':'0'*64},
                       {'operation_id':'0'*64},{'binding':{**self.old['binding'],'source_sha':'b'*40}}]:
            a._durable_json(self.old_path,{**self.old,**change})
            with self.subTest(change=change),self.assertRaises(ValueError):self.dispatch()
        a._durable_json(self.old_path,self.old)
        self.assertEqual(self.calls,[])

    def test_corrective_ancestry_is_not_another_ordinary_predecessor(self):
        bad=copy.deepcopy(self.old);bad['binding']['corrective_backend']=dict(self.c)
        a._durable_json(self.old_path,bad)
        b=copy.deepcopy(self.binding);b['corrective_backend']['failed_record_sha256']=a.digest(bad)
        with self.assertRaises(ValueError):self.dispatch(b)
        self.assertEqual(self.calls,[])

    def test_unapproved_unchanged_policy_changed_canary_or_malformed_binding_denies(self):
        for key,value in [('failed_startup_policy_sha256','1'*64),
                          ('failed_policy_marker_identity_sha256','3'*64),
                          ('failed_record_sha256','0'*64),('failed_operation_id','../escape'),
                          ('schema','unknown'),('extra','notallowed')]:
            b=copy.deepcopy(self.binding);b['corrective_backend'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.dispatch(b)
        approval=self.approval();approval.pop('startup_policy_change_receipt_sha256')
        with self.assertRaises(ValueError):self.dispatch(approval=approval)
        with self.assertRaises(ValueError):self.dispatch(action='stage_frontend')
        self.assertEqual(self.calls,[])

    def test_missing_live_policy_approval_failure_target_or_snapshot_fails_before_intent(self):
        for key,value in [('policy_change_approved',False),('scope','PROPOSED_POLICY'),
                          ('failed_startup_code','UNKNOWN'),('service','wrong'),
                          ('failed_record_sha256','4'*64),('approved_policy_sha256','7'*64)]:
            actual=self.observe();actual['corrective_backend'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.dispatch(observer=lambda *_:actual)
        actual=self.observe();actual.pop('startup_data_qualification')
        with self.assertRaises(ValueError):self.dispatch(observer=lambda *_:actual)
        self.assertFalse((self.journal/'_write-barrier.json').exists())
        self.assertEqual(self.calls,[])

    def test_original_altered_during_observation_is_rechecked_under_barrier(self):
        def changed(*_):
            a._durable_json(self.old_path,{**self.old,'state':'APPLIED_VERIFIED'})
            return self.observe()
        with self.assertRaises(ValueError):self.dispatch(observer=changed)
        self.assertEqual(self.calls,[])
        self.assertFalse((self.journal/('.corrective-'+self.old_id+'.claim')).exists())
        self.assertTrue((self.journal/'_write-barrier.json').exists())  # Unknown local intent remains held.
        operation=a.operation_identity('release_backend',self.binding)
        self.assertTrue((self.journal/(operation+'.json')).exists())
        outcome={'scope':'ACTUAL_PROVIDER_AND_SOURCE','operation_id':operation,
            'action':'release_backend','source_sha':self.binding['source_sha'],
            'outcome':'NOT_APPLIED','receipt_sha256':'4'*64}
        result=self.adapter(lambda *_:outcome).reconcile(operation)
        self.assertEqual(result['state'],'NOT_APPLIED_VERIFIED')
        self.assertFalse((self.journal/'_write-barrier.json').exists())

    def test_failure_after_permanent_claim_consumes_correction_without_provider_call(self):
        def interrupted(*_,**__):raise SystemExit('SYNTHETIC_BEFORE_PROCESS_SUBMIT')
        with patch.object(a.subprocess,'check_output',side_effect=[self.binding['source_sha'],'']), \
             patch('scripts.backend_upload_payload.qualify',return_value=self.payload),self.assertRaises(SystemExit):
            self.adapter(runner=interrupted).perform('release_backend',self.binding,self.approval())
        self.assertTrue((self.journal/('.corrective-'+self.old_id+'.claim')).exists())
        with self.assertRaises(FileExistsError):self.dispatch()
        self.assertEqual(self.calls,[])

    def test_compatibility_true_and_fresh_proof_do_not_waive_existing_recovery_gate(self):
        actual=self.observe();actual['guarded_rollback_available']=False
        with self.assertRaises(ValueError):self.dispatch(observer=lambda *_:actual)
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
