"""Offline dummy contracts only: no provider, native, startup or release PASS."""
import copy
from datetime import datetime, timezone, timedelta
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec=importlib.util.spec_from_file_location('candidate_frontend_adapter',Path(__file__).with_name('india_release_provider_adapter.py'))
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
NOW=datetime(2026,11,4,12,tzinfo=timezone.utc)

class FrontendRestore(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.j=Path(self.temp.name)/'operations';self.j.mkdir(mode=0o700)
        self.target={'deployment_id':'dpl_Old','source_sha':'a'*40,'config_sha256':'1'*64}
        pb={'source_sha':'b'*40,'deployment_id':'dpl_Bad','rollback_frontend_deployment_id':'dpl_Old',
            'rollback_frontend_source_sha':'a'*40,'backend_source_sha':'d'*40,'frontend_restore_target':self.target}
        self.parent={'action':'promote_frontend','binding':pb,'state':'APPLIED_VERIFIED',
            'reconciliation_receipt_sha256':'2'*64,'operations_journal_identity_sha256':a._operation_journal_identity(self.j),
            'qualified_frontend_restore_target':copy.deepcopy(self.target),'started_at':NOW.isoformat()}
        self.parent['operation_id']=a.operation_identity('promote_frontend',pb);self.store_parent()
        self.failure={'scope':'ACTUAL_APPLIED_FRONTEND_FAILURE','operation_id':self.parent['operation_id'],
            'promotion_reconciliation_receipt_sha256':'2'*64,'deployment_id':'dpl_Bad','source_sha':'b'*40,
            'project':a.PROJECT,'team':a.TEAM}
        c={'operations_journal_identity_sha256':a._operation_journal_identity(self.j),
           'applied_promotion_operation_id':self.parent['operation_id'],'applied_promotion_record_sha256':a.digest(self.parent),
           'applied_promotion_reconciliation_receipt_sha256':'2'*64,'target_deployment_id':'dpl_Old',
           'target_source_sha':'a'*40,'target_config_sha256':'1'*64,'current_bad_frontend_deployment_id':'dpl_Bad',
           'bad_frontend_failure_receipt_sha256':a.digest(self.failure),'backend_deployment_id':'11111111-1111-4111-8111-111111111111',
           'backend_source_sha':'d'*40,'backend_phase':'BACKEND_UNCHANGED'}
        self.b={'source_sha':'a'*40,'source_root':str(ROOT),'controller_source_sha':'c'*40,
            'applied_promotion_operation_id':self.parent['operation_id'],'config_sha256':'1'*64,'frontend_restore_context':c}
        self.actual={'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,'auto_deploy':False,'authenticated_provider_account':True,
            'cli_version':a.CLI_VERSIONS['vercel'],'provider_identity_sha256':'3'*64,'controller_source_sha':'c'*40,
            'target_project_id':a.PROJECT,'target_team_id':a.TEAM,'current_frontend_deployment_id':'dpl_Bad',
            'config_sha256':'1'*64,'frontend_restore_sha256':a.digest(c),'frontend_restore_target':copy.deepcopy(self.target),
            'backend_deployment_id':c['backend_deployment_id'],'backend_source_sha':'d'*40,'backend_phase':'BACKEND_UNCHANGED',
            'backend_unchanged':True,'native_frontend_restore_available':True,'target_ready':True,'target_source_verified':True,
            'target_config_verified':True,'frontend_backend_compatible':True,'known_frontend_failure_qualified':True,
            'health_book_statuses':[200,200],'guest_manifest_status':401,'bad_frontend_failure_receipt':self.failure}
    def tearDown(self):self.temp.cleanup()
    def store_parent(self):
        p=self.j/(self.parent['operation_id']+'.json');p.write_text(json.dumps(self.parent));p.chmod(0o600)
    def approval(self):
        return {'schema':'earnalism-india-protected-operation.v1','action':'restore_frontend','binding_sha256':a.digest(self.b),
            'project':a.PROJECT,'team':a.TEAM,'railway_project':a.RAILWAY_PROJECT,'service':a.SERVICE,'environment':a.ENVIRONMENT,
            'territories':['IN'],'auto_deploy':False,'approved':True,'provider_identity_sha256':'3'*64,'config_sha256':'1'*64,
            'frontend_restore_sha256':a.digest(self.b['frontend_restore_context']),'rollback_operator':'dummy-not-authority',
            'approved_at':NOW.isoformat(),'expires_at':(NOW+timedelta(minutes=5)).isoformat(),'provider_observed_at':NOW.isoformat()}
    def perform(self,run):
        with patch.object(a.subprocess,'check_output',side_effect=['c'*40,'']):
            return a.ReleaseController(a.ProviderAdapter(self.j,owner_authorized=True,observe=lambda *_:self.actual,run=run,clock=lambda:NOW)).perform('restore_frontend',self.b,self.approval())
    def test_exact_context_and_scalar_rollback_command(self):
        self.assertEqual(a.validate_frontend_restore_context(self.j,self.b,self.actual),self.b['frontend_restore_context'])
        self.assertEqual(a.ProviderAdapter(self.j)._command('restore_frontend',self.b,None),['vercel','rollback','dpl_Old','--yes','--scope',a.TEAM])
    def test_default_disabled(self):
        with self.assertRaisesRegex(ValueError,'prohibits'):a.ProviderAdapter(self.j).perform('restore_frontend',self.b,{})
    def test_target_or_path_cannot_mint_new_return(self):
        old=a.operation_identity('restore_frontend',self.b)
        for k,v in [('source_sha','f'*40),('source_root','/other'),('frontend_restore_context',{})]:
            self.assertEqual(old,a.operation_identity('restore_frontend',{**self.b,k:v}))
    def test_each_context_swap_rejected(self):
        for key in a.FRONTEND_RETURN_FIELDS:
            with self.subTest(key=key):
                b=copy.deepcopy(self.b);b['frontend_restore_context'][key]='9'*64
                with self.assertRaises(ValueError):a.validate_frontend_restore_context(self.j,b,self.actual)
    def test_each_live_prerequisite_required(self):
        for key in ['native_frontend_restore_available','target_ready','target_source_verified','target_config_verified','frontend_backend_compatible','known_frontend_failure_qualified','backend_unchanged']:
            with self.subTest(key=key):
                actual={**self.actual,key:False}
                with self.assertRaises(ValueError):a.validate_frontend_restore_context(self.j,self.b,actual)
    def test_cross_journal_copy_denied(self):
        other=Path(self.temp.name)/'copied';other.mkdir(mode=0o700)
        for p in self.j.glob('*.json'):(other/p.name).write_bytes(p.read_bytes());(other/p.name).chmod(0o600)
        with self.assertRaisesRegex(ValueError,'custody'):a.validate_frontend_restore_context(other,self.b,self.actual)
    def test_unknown_parent_or_legacy_proof_denied(self):
        original=copy.deepcopy(self.parent)
        for key,value in [('state','WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED'),('qualified_frontend_restore_target',None),('operations_journal_identity_sha256',None)]:
            self.parent=copy.deepcopy(original);self.parent[key]=value;self.store_parent()
            b=copy.deepcopy(self.b);b['frontend_restore_context']['applied_promotion_record_sha256']=a.digest(self.parent)
            with self.assertRaises(ValueError):a.validate_frontend_restore_context(self.j,b,self.actual)
    def test_unsigned_old_frontend_against_guard_denied(self):
        self.b['frontend_restore_context']['backend_phase']='GUARD_ACTIVE';self.actual.update(backend_phase='GUARD_ACTIVE',frontend_restore_sha256=a.digest(self.b['frontend_restore_context']))
        with self.assertRaisesRegex(ValueError,'Unsigned'):a.validate_frontend_restore_context(self.j,self.b,self.actual)
        self.actual['target_signed_purchase_ready']=True
        a.validate_frontend_restore_context(self.j,self.b,self.actual)
    def test_timeout_one_dispatch_keeps_claim_barrier_no_replay(self):
        calls=[]
        def timeout(cmd,**kw):
            calls.append(cmd);self.assertTrue((self.j/'_write-barrier.json').exists());self.assertTrue(list(self.j.glob('.frontend-return-*.claim')));self.assertTrue(list(self.j.glob('*.request.json')))
            raise TimeoutError('dummy-no-provider')
        r=self.perform(timeout);self.assertEqual(len(calls),1);self.assertEqual(r['state'],'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED')
        with self.assertRaises(FileExistsError):self.perform(timeout)
        self.assertEqual(len(calls),1)
    def attempted(self):
        return self.perform(lambda *_args,**_kwargs:type('Result',(),{'returncode':0,'stdout':'','stderr':''})())
    def outcome(self,op,outcome='APPLIED'):
        return {**self.actual,'operation_id':op,'action':'restore_frontend','source_sha':'a'*40,'outcome':outcome,'receipt_sha256':'8'*64,
            'deployment_id':'dpl_Old','serving_frontend_deployment_id':'dpl_Old','both_aliases_verified':True}
    def test_applied_requires_actual_target_both_aliases(self):
        r=self.attempted();actual=self.outcome(r['operation_id']);adapter=a.ProviderAdapter(self.j,observe=lambda *_:actual)
        for key,value in [('deployment_id','dpl_Other'),('serving_frontend_deployment_id','dpl_Bad'),('both_aliases_verified',False)]:
            saved=actual[key];actual[key]=value
            with self.assertRaises(ValueError):adapter.reconcile(r['operation_id'])
            self.assertTrue((self.j/'_write-barrier.json').exists());actual[key]=saved
        self.assertEqual(adapter.reconcile(r['operation_id'])['state'],'APPLIED_VERIFIED');self.assertFalse((self.j/'_write-barrier.json').exists())
        with self.assertRaises(FileExistsError):self.perform(lambda *_:self.fail('replay'))
    def test_unknown_and_no_effect_preserve_no_retry(self):
        r=self.attempted();actual=self.outcome(r['operation_id'],'UNKNOWN');adapter=a.ProviderAdapter(self.j,observe=lambda *_:actual)
        with self.assertRaises(ValueError):adapter.reconcile(r['operation_id'])
        actual['outcome']='NOT_APPLIED'
        with self.assertRaises(ValueError):adapter.reconcile(r['operation_id'])
        actual['native_no_effect_proof']={'scope':'ACTUAL_FRONTEND_RESTORE_NOT_APPLIED','operation_id':r['operation_id'],'current_deployment_id':'dpl_Bad','exact_request_not_applied':True,'both_aliases_unchanged':True}
        self.assertEqual(adapter.reconcile(r['operation_id'])['state'],'NOT_APPLIED_VERIFIED')
        with self.assertRaises(FileExistsError):self.perform(lambda *_:self.fail('replay'))
    def test_claim_alone_cannot_be_reset(self):
        claim=self.j/('.frontend-return-'+self.parent['operation_id']+'.claim')
        claim.write_text('{}');claim.chmod(0o600)
        with self.assertRaises(FileExistsError):self.perform(lambda *_:self.fail('provider'))

    def test_durable_failure_before_dispatch_keeps_barrier_and_claim(self):
        real=a._durable_json;calls=[]
        def broken(path,value,**kw):
            if str(path).endswith('.request.json'):raise OSError('dummy-fsync-failure')
            return real(path,value,**kw)
        with patch.object(a,'_durable_json',side_effect=broken):
            with self.assertRaises(OSError):self.perform(lambda *args,**kw:calls.append(args))
        self.assertEqual(calls,[]);self.assertTrue((self.j/'_write-barrier.json').exists())
        self.assertTrue(list(self.j.glob('.frontend-return-*.claim')))

    def test_namespace_swap_before_dispatch_denied(self):
        real=a._durable_json;calls=[];original=self.j;renamed=original.with_name('retained-original')
        def swapped(path,value,**kw):
            result=real(path,value,**kw)
            if str(path).endswith('.request.json'):
                original.rename(renamed);original.mkdir(mode=0o700)
            return result
        with patch.object(a,'_durable_json',side_effect=swapped):
            with self.assertRaises(ValueError):self.perform(lambda *args,**kw:calls.append(args))
        self.assertEqual(calls,[]);self.assertTrue((renamed/'_write-barrier.json').exists())

    def test_promotion_target_capture_is_exact_and_legacy_not_retrofitted(self):
        actual={'frontend_restore_target':self.target,'frontend_restore_target_verified':True}
        self.assertEqual(a.validate_frontend_target(self.parent['binding'],actual),self.target)
        for field in a.FRONTEND_TARGET_FIELDS:
            changed=copy.deepcopy(actual);changed['frontend_restore_target'][field]='wrong'
            with self.assertRaises(ValueError):a.validate_frontend_target(self.parent['binding'],changed)

    def test_wrong_provider_or_newer_frontend_is_never_replaced(self):
        for key in ('target_project_id','target_team_id','current_frontend_deployment_id'):
            saved=self.actual[key];self.actual[key]='unrelated'
            with self.assertRaises(ValueError):self.perform(lambda *_args,**_kw:self.fail('provider'))
            self.actual[key]=saved

    def test_current_frontend_swap_after_request_never_dispatches(self):
        real=a._durable_json;calls=[]
        def swapped(path,value,**kw):
            result=real(path,value,**kw)
            if str(path).endswith('.request.json'):self.actual['current_frontend_deployment_id']='dpl_UnrelatedNew'
            return result
        with patch.object(a,'_durable_json',side_effect=swapped):
            with self.assertRaisesRegex(ValueError,'changed before'):self.perform(lambda *args,**kw:calls.append(args))
        self.assertEqual(calls,[]);self.assertTrue((self.j/'_write-barrier.json').exists())
        self.assertTrue(list(self.j.glob('.frontend-return-*.claim')))

    def test_stale_approval_does_not_dispatch(self):
        approval=self.approval();approval['provider_observed_at']=(NOW-timedelta(minutes=16)).isoformat()
        with self.assertRaisesRegex(ValueError,'Stale'):a.ProviderAdapter(self.j,owner_authorized=True,observe=lambda *_:self.actual,run=lambda *_:self.fail('provider'),clock=lambda:NOW).perform('restore_frontend',self.b,approval)

if __name__=='__main__':unittest.main()
