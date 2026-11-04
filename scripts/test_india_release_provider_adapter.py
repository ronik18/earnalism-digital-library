from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import patch
from scripts import india_release_provider_adapter as a


def startup_fixture(binding, now, guard_sha, *, config_sha='c'*64):
    """Synthetic proof only; never a provider or database acceptance receipt."""
    proof = {'schema':'earnalism.startup-data-dispatch-qualification.v1',
        'scope':'ACTUAL_STARTUP_POLICY_AND_CANARIES',
        'phase':'INSTALLED_POLICY_BEFORE_BACKEND_DISPATCH',
        'source_sha':binding['source_sha'], 'source_delivery_sha256':binding['source_delivery_sha256'],
        'config_sha256':config_sha, 'policy_sha256':'1'*64, 'guard_source_sha256':guard_sha,
        'marker_identity_sha256':'2'*64, 'markers_sha256':'3'*64, 'marker_count':2,
        'context_sha256':'4'*64, 'method':'DIRECT_AUTHORIZED_METADATA_READ',
        'snapshot_sha256':None, 'observed_at':now.isoformat(), 'guard_verified':True}
    bound = {**binding, 'startup_policy_sha256':proof['policy_sha256'],
        'startup_guard_source_sha256':guard_sha, 'startup_marker_identity_sha256':'2'*64,
        'startup_context_sha256':'4'*64, 'startup_data_receipt_sha256':a.digest(proof)}
    return bound, {'startup_policy_sha256':proof['policy_sha256'], 'startup_data_qualification':proof}


class ProviderAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.calls = []
        self.now = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
        self.binding = {'source_sha': 'a' * 40, 'source_root': str(self.root)}

    def approval(self, action='stage_frontend', binding=None):
        return {'schema': 'earnalism-india-protected-operation.v1', 'action': action,
            'binding_sha256': a.digest(binding or self.binding), 'project': a.PROJECT,
            'team': a.TEAM, 'railway_project': a.RAILWAY_PROJECT, 'service': a.SERVICE,
            'environment': a.ENVIRONMENT, 'territories': ['IN'], 'auto_deploy': False,
            'approved': True, 'provider_identity_sha256': 'b' * 64,
            'config_sha256': 'c' * 64, 'guarded_rollback_sha256': 'd' * 64,
            'rollback_operator': 'synthetic-test-operator',
            'approved_at': (self.now - timedelta(minutes=1)).isoformat(),
            'expires_at': (self.now + timedelta(minutes=5)).isoformat(),
            'provider_observed_at': self.now.isoformat()}

    def observe(self, *args):
        r = self.approval()
        return {**{k: r[k] for k in ('provider_identity_sha256', 'config_sha256', 'guarded_rollback_sha256')},
                'scope': 'ACTUAL_PROVIDER_AND_SOURCE', 'qualified': True,
                'auto_deploy': False, 'guarded_rollback_available': True,
                'cli_version': a.CLI_VERSIONS['vercel'],
                'authenticated_provider_account': True}

    def fake_run(self, command, **kwargs):
        self.calls.append(command); return SimpleNamespace(returncode=0)

    def adapter(self, **overrides):
        return a.ProviderAdapter(self.root / 'journal', owner_authorized=overrides.pop('owner_authorized', True),
            observe=overrides.pop('observe', self.observe), run=overrides.pop('run', self.fake_run),
            clock=lambda: self.now, **overrides)

    def test_current_owner_prohibition_blocks_every_provider_call(self):
        with self.assertRaises(ValueError):
            self.adapter(owner_authorized=False).perform('stage_frontend', self.binding, self.approval())
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / 'journal').exists())

    def test_expiry_scope_and_changed_evidence_denied(self):
        for key, value in [('expires_at', self.now.isoformat()), ('auto_deploy', True),
                           ('binding_sha256', 'e' * 64), ('guarded_rollback_sha256', None)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.adapter().perform('stage_frontend', self.binding, {**self.approval(), key: value})
        self.assertEqual(self.calls, [])

    def test_live_rollback_or_auth_missing_denies_before_write(self):
        for key in ['guarded_rollback_available', 'authenticated_provider_account', 'qualified']:
            observer = lambda *args: {**self.observe(), key: False}
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.adapter(observe=observer).perform('stage_frontend', self.binding, self.approval())
        self.assertEqual(self.calls, [])

    def test_intent_precedes_write_and_no_duplicate_even_on_success(self):
        def fake(command, **kwargs):
            records = list((self.root / 'journal').glob('*.json'))
            self.assertTrue(any(json.loads(p.read_text()).get('state') == 'INTENT_RECONCILE_BEFORE_RETRY' for p in records))
            return self.fake_run(command, **kwargs)
        adapter = self.adapter(run=fake)
        result = adapter.perform('stage_frontend', self.binding, self.approval())
        self.assertEqual(result['state'], 'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED')
        request = next((self.root / 'journal').glob('*.request.json'))
        self.assertFalse(json.loads(request.read_text())['autoAssignCustomDomains'])
        self.assertEqual(json.loads(request.read_text())['target'], 'production')
        with self.assertRaises(FileExistsError): adapter.perform('stage_frontend', self.binding, self.approval())
        self.assertEqual(len(self.calls), 1)

    def test_timeout_stays_unknown_and_never_retries(self):
        def failure(*args, **kwargs): raise TimeoutError('synthetic failure')
        adapter = self.adapter(run=failure)
        result = adapter.perform('stage_frontend', self.binding, self.approval())
        self.assertIsNone(result['process_exit_code'])
        with self.assertRaises(FileExistsError): adapter.perform('stage_frontend', self.binding, self.approval())

    def test_unqualified_candidate_and_backend_first_denied(self):
        binding = {**self.binding, 'deployment_id': 'dpl_TEST'}
        with self.assertRaises(ValueError): self.adapter().perform('promote_frontend', binding, self.approval('promote_frontend', binding))
        with self.assertRaises(ValueError): self.adapter().perform('release_backend', self.binding, self.approval('release_backend'))
        self.assertEqual(self.calls, [])

    def test_changed_local_path_cannot_bypass_unknown_write(self):
        adapter = self.adapter()
        adapter.perform('stage_frontend', self.binding, self.approval())
        changed = {**self.binding, 'source_root': str(self.root / 'another-checkout')}
        with self.assertRaises(FileExistsError):
            adapter.perform('stage_frontend', changed, self.approval(binding=changed))
        self.assertEqual(len(self.calls), 1)

    def test_unknown_stage_blocks_even_a_different_promotion(self):
        adapter = self.adapter()
        adapter.perform('stage_frontend', self.binding, self.approval())
        changed = {**self.binding, 'deployment_id': 'dpl_OTHER'}
        with self.assertRaises(FileExistsError):
            adapter.perform('promote_frontend', changed, self.approval('promote_frontend', changed))
        self.assertEqual(len(self.calls), 1)

    def test_nonzero_exit_is_unknown_not_automatic_rollback(self):
        adapter = self.adapter(run=lambda *args, **kwargs: SimpleNamespace(returncode=1))
        result = adapter.perform('stage_frontend', self.binding, self.approval())
        self.assertEqual(result['process_exit_code'], 1)
        self.assertIn('RECONCILIATION_REQUIRED', result['state'])

    def test_failed_cli_diagnostic_is_durable_without_raw_output_or_retry(self):
        secret = 'synthetic-output-never-store'
        def failed(*args, **kwargs):
            self.calls.append(args)
            return SimpleNamespace(returncode=1, stdout='',
                stderr='dns error: failed to lookup address information '+secret)
        adapter = self.adapter(run=failed)
        result = adapter.perform('stage_frontend', self.binding, self.approval())
        persisted = json.loads((self.root / 'journal' / (result['operation_id']+'.json')).read_text())
        self.assertEqual(persisted['process_diagnostic']['class'], 'DNS_LOOKUP_FAILED')
        self.assertNotIn(secret, json.dumps(persisted))
        self.assertEqual(persisted['state'], 'WRITE_ATTEMPTED_READ_ONLY_RECONCILIATION_REQUIRED')
        with self.assertRaises(FileExistsError):
            adapter.perform('stage_frontend', self.binding, self.approval())
        self.assertEqual(len(self.calls), 1)

    def test_backend_payload_seal_binds_actual_input_before_intent(self):
        payload = {'source': 'a'*40, 'runtime_expected_sha256': 'd'*64,
                   'files': [{'path':'backend/inert.py','sha256':'f'*64,'bytes':1}]}
        b = {**self.binding, 'native_pause_acceptance_sha256':'b'*64,
             'closed_server_sha256':'c'*64, 'source_delivery_sha256':'d'*64,
             'purchase_mode':'CLOSED', 'current_backend_deployment_id':'inert-current',
             'current_backend_source_sha':'e'*40, 'config_sha256':'c'*64,
             'frontend_deployment_id':'dpl_INERT', 'backend_payload_sha256':a.digest(payload)}
        (self.root/'backend').mkdir()
        (self.root/'backend/startup_data_guard.py').write_bytes(b'SYNTHETIC_GUARD_SOURCE')
        b, startup = startup_fixture(b, self.now, a.hashlib.sha256(b'SYNTHETIC_GUARD_SOURCE').hexdigest())
        approval = {**self.approval('release_guarded_bootstrap', b), 'bootstrap_preflight_sha256':'d'*64}
        actual = {**self.observe(), **b, **startup, 'bootstrap_preflight_sha256':'d'*64,
                  'current_backend_healthy':True, 'native_healthcheck_traffic_gating':True,
                  'new_resources_or_config_changes':False, 'frontend_signed_purchase_ready':True,
                  'cli_version':a.CLI_VERSIONS['railway']}
        with patch.object(a.subprocess, 'check_output', side_effect=['a'*40,'']), \
             patch('scripts.backend_upload_payload.qualify', return_value=payload):
            with self.assertRaisesRegex(ValueError,'upload payload'):
                self.adapter(observe=lambda *x:{**actual,'backend_payload_sha256':'0'*64}).perform('release_guarded_bootstrap',b,approval)
        self.assertEqual(self.calls,[])
        self.assertFalse((self.root/'journal').exists())
        with patch.object(a.subprocess, 'check_output', side_effect=['a'*40,'']), \
             patch('scripts.backend_upload_payload.qualify', return_value=payload):
            result=self.adapter(observe=lambda *x:actual).perform('release_guarded_bootstrap',b,approval)
        self.assertEqual(result['binding']['backend_payload_sha256'],a.digest(payload))
        self.assertEqual(self.calls[0][-1],str(self.root.resolve()/'backend'))
        self.assertIn('RECONCILIATION_REQUIRED',result['state'])

    def test_process_interruption_leaves_exclusive_intent(self):
        def interrupted(*args, **kwargs): raise SystemExit('synthetic process stop')
        adapter = self.adapter(run=interrupted)
        with self.assertRaises(SystemExit):
            adapter.perform('stage_frontend', self.binding, self.approval())
        with self.assertRaises(FileExistsError):
            self.adapter().perform('stage_frontend', self.binding, self.approval())

    def test_reconciliation_requires_actual_bound_receipt(self):
        adapter = self.adapter()
        result = adapter.perform('stage_frontend', self.binding, self.approval())
        with self.assertRaises(ValueError): adapter.reconcile(result['operation_id'])
        adapter.observe = lambda *args: {'scope': 'ACTUAL_PROVIDER_AND_SOURCE',
            'operation_id': result['operation_id'], 'action': 'stage_frontend',
            'source_sha': self.binding['source_sha'], 'deployment_id': 'dpl_TEST',
            'outcome': 'APPLIED', 'receipt_sha256': 'f' * 64}
        self.assertEqual(adapter.reconcile(result['operation_id'])['state'], 'APPLIED_VERIFIED')
        with self.assertRaises(FileExistsError):
            adapter.perform('stage_frontend', self.binding, self.approval())

    def test_controller_rejects_unreconciled_stage_and_backend_first(self):
        controller = a.ReleaseController(self.adapter())
        binding = {**self.binding, 'deployment_id': 'dpl_TEST'}
        with self.assertRaises(ValueError):
            controller.perform('promote_frontend', binding, self.approval('promote_frontend', binding))
        with self.assertRaises(ValueError):
            controller.perform('release_backend', self.binding, self.approval('release_backend'))
        self.assertEqual(self.calls, [])

    def test_controller_rejects_wrong_candidate_source_and_not_applied_predecessor(self):
        journal = self.root / 'journal'; journal.mkdir()
        binding = {**self.binding, 'deployment_id': 'dpl_TEST'}
        record = {'state': 'APPLIED_VERIFIED', 'action': 'stage_frontend',
                  'binding': self.binding, 'provider_deployment_id': 'dpl_TEST',
                  'reconciliation_receipt_sha256': 'f' * 64}
        for change in [{'state': 'NOT_APPLIED_VERIFIED'}, {'provider_deployment_id': 'dpl_WRONG'},
                       {'binding': {**self.binding, 'source_sha': 'e' * 40}}]:
            (journal / 'fixture.json').write_text(json.dumps({**record, **change}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                a.ReleaseController(self.adapter()).perform('promote_frontend', binding,
                    self.approval('promote_frontend', binding))
        self.assertEqual(self.calls, [])

    def test_concurrent_different_writes_share_one_exclusive_barrier(self):
        ready = threading.Barrier(2)
        def observer(*args):
            result = self.observe(); ready.wait(timeout=3); return result
        def invoke(sha):
            binding = {**self.binding, 'source_sha': sha}
            try:
                self.adapter(observe=observer).perform('stage_frontend', binding, self.approval(binding=binding))
                return 'attempted'
            except FileExistsError:
                return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(invoke, sha) for sha in ['a' * 40, 'e' * 40]]
            self.assertEqual(sorted(f.result() for f in futures), ['attempted', 'blocked'])
        self.assertEqual(len(self.calls), 1)

class PairedBootstrapAdapterTests(unittest.TestCase):
    """Deterministic mocked adapter boundary; no Git refs, provider or real receipt."""
    def setUp(self):
        import copy
        self.copy = copy.deepcopy
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root/'controller'; self.export = self.root/'export'
        (self.source/'backend').mkdir(parents=True); (self.export/'backend').mkdir(parents=True)
        self.guard = b'SYNTHETIC_COMBINED_GUARD_SOURCE'
        (self.source/'backend/startup_data_guard.py').write_bytes(self.guard)
        self.journal = self.root/'journal'; self.calls=[]
        self.now=datetime(2026,11,4,0,0,tzinfo=timezone.utc)
        self.payload={'scope':'OFFLINE_EXACT_COMMITTED_EXPORT_NOT_NATIVE_ARCHIVE_OR_PROVIDER_UPLOAD',
            'cli_version':a.CLI_VERSIONS['railway'],'source':'a'*40,'controller_source':'c'*40,
            'input_path':str(self.export.resolve()/'backend'),'archive_prefix':str(self.export.resolve()),
            'path_as_root':False,'archive_member_prefix':'backend/','native_archive_qualification':False,
            'files':[{'path':'backend/inert.py','bytes':1,'sha256':'f'*64}],
            'runtime_expected_sha256':'5'*64,'provider_writes':0}
        b={'source_sha':'a'*40,'source_root':str(self.source),'backend_export_root':str(self.export),
            'controller_source_sha':'c'*40,'native_pause_acceptance_sha256':'2'*64,
            'closed_server_sha256':'3'*64,'source_delivery_sha256':'5'*64,'purchase_mode':'CLOSED',
            'current_backend_deployment_id':'11111111-1111-4111-8111-111111111111',
            'current_backend_source_sha':'e'*40,'config_sha256':'1'*64,'frontend_deployment_id':'dpl_SYNTHETIC',
            'backend_payload_sha256':a.digest(self.payload)}
        self.binding,self.startup=startup_fixture(b,self.now,a.hashlib.sha256(self.guard).hexdigest(),config_sha='1'*64)
        self.actual={**self.binding,**self.startup,'scope':'ACTUAL_PROVIDER_AND_SOURCE','qualified':True,
            'provider_identity_sha256':'b'*64,'config_sha256':'1'*64,'bootstrap_preflight_sha256':'8'*64,
            'auto_deploy':False,'authenticated_provider_account':True,'guarded_rollback_available':True,
            'current_backend_healthy':True,'native_healthcheck_traffic_gating':True,
            'new_resources_or_config_changes':False,'frontend_signed_purchase_ready':True,
            'cli_version':a.CLI_VERSIONS['railway']}
    def approval(self, binding=None, action='release_guarded_bootstrap'):
        b=binding or self.binding
        return {'schema':'earnalism-india-protected-operation.v1','action':action,
            'binding_sha256':a.digest(b),'project':a.PROJECT,'team':a.TEAM,'railway_project':a.RAILWAY_PROJECT,
            'service':a.SERVICE,'environment':a.ENVIRONMENT,'territories':['IN'],'auto_deploy':False,
            'approved':True,'provider_identity_sha256':'b'*64,'config_sha256':'1'*64,
            'bootstrap_preflight_sha256':'8'*64,'guarded_rollback_sha256':'d'*64,'guarded_restore_sha256':'d'*64,
            'rollback_operator':'synthetic-only','approved_at':(self.now-timedelta(minutes=1)).isoformat(),
            'expires_at':(self.now+timedelta(minutes=5)).isoformat(),'provider_observed_at':self.now.isoformat()}
    def fake_run(self, command, **kwargs):
        self.assertTrue((self.journal/'_write-barrier.json').exists())
        self.calls.append((command,kwargs));return SimpleNamespace(returncode=0,stdout='',stderr='')
    def invoke(self, *, binding=None, actual=None, approval=None, action='release_guarded_bootstrap',
               owner_authorized=True, head='c'*40, dirty='', export_effect=None, normal_payload=None):
        b=binding or self.binding;observed=self.actual if actual is None else actual
        with patch.object(a.subprocess,'check_output',side_effect=[head,dirty]), \
             patch('scripts.backend_upload_payload.qualify_committed_export',side_effect=export_effect,
                   return_value=self.payload) as exported, \
             patch('scripts.backend_upload_payload.qualify',return_value=normal_payload) as normal:
            adapter=a.ProviderAdapter(self.journal,owner_authorized=owner_authorized,
                observe=lambda *_:observed,run=self.fake_run,clock=lambda:self.now)
            try:return adapter.perform(action,b,approval or self.approval(b,action))
            finally:self.export_calls=exported.call_args_list;self.normal_calls=normal.call_args_list
    def reseal(self, payload):
        b=self.copy(self.binding);actual=self.copy(self.actual)
        b['backend_payload_sha256']=actual['backend_payload_sha256']=a.digest(payload)
        return b,actual
    def test_paired_default_disabled_does_not_observe_or_dispatch(self):
        with self.assertRaises(ValueError):self.invoke(owner_authorized=False)
        self.assertFalse(self.calls);self.assertFalse(self.export_calls);self.assertFalse(self.journal.exists())
    def test_export_override_is_rejected_on_every_other_action(self):
        for action in ['stage_frontend','promote_frontend','release_backend','restore_guarded_bootstrap']:
            with self.subTest(action=action),self.assertRaisesRegex(ValueError,'paired CLOSED bootstrap'):
                self.invoke(action=action)
        self.assertFalse(self.calls);self.assertFalse(self.journal.exists())
    def test_controller_head_observer_or_nonimmutable_label_cannot_match_target(self):
        with self.assertRaisesRegex(ValueError,'exact/clean'):self.invoke(head='d'*40)
        actual={**self.actual,'controller_source_sha':'d'*40}
        with self.assertRaisesRegex(ValueError,'normal controller'):self.invoke(actual=actual)
        b={**self.binding,'controller_source_sha':'main'}
        with self.assertRaisesRegex(ValueError,'Exact normal controller'):self.invoke(binding=b)
        self.assertFalse(self.calls);self.assertFalse(self.journal.exists())
    def test_dirty_controller_and_uncommitted_pair_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'exact/clean'):self.invoke(dirty=' M unreviewed.py')
        with self.assertRaisesRegex(ValueError,'Committed source pair'):
            self.invoke(export_effect=ValueError('Committed source pair required'))
        self.assertFalse(self.calls);self.assertFalse(self.normal_calls);self.assertFalse(self.journal.exists())
    def test_open_role_or_nonpaired_closed_ancestor_cannot_upload(self):
        b={**self.binding,'purchase_mode':'OPEN'};actual={**self.actual,'purchase_mode':'OPEN'}
        with self.assertRaisesRegex(ValueError,'CLOSED bootstrap'):self.invoke(binding=b,actual=actual)
        with self.assertRaisesRegex(ValueError,'paired CLOSED ancestor'):
            self.invoke(export_effect=ValueError('Export source must be explicitly paired CLOSED ancestor'))
        self.assertFalse(self.calls);self.assertFalse(self.journal.exists())
    def test_qualified_report_cannot_conflate_target_and_controller(self):
        for key in ['source','controller_source']:
            payload={**self.payload,key:'d'*40};b,actual=self.reseal(payload)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'export report differs'):
                self.invoke(binding=b,actual=actual,export_effect=lambda *x:payload)
        self.assertFalse(self.calls);self.assertFalse(self.journal.exists())
    def test_binding_observer_seal_and_closed_delivery_must_match(self):
        with self.assertRaisesRegex(ValueError,'upload payload'):
            self.invoke(binding={**self.binding,'backend_payload_sha256':'9'*64})
        with self.assertRaisesRegex(ValueError,'upload payload'):
            self.invoke(actual={**self.actual,'backend_payload_sha256':'9'*64})
        payload={**self.payload,'runtime_expected_sha256':'9'*64};b,actual=self.reseal(payload)
        with self.assertRaisesRegex(ValueError,'upload payload'):
            self.invoke(binding=b,actual=actual,export_effect=lambda *x:payload)
        self.assertFalse(self.calls);self.assertFalse(self.journal.exists())
    def test_startup_proof_cannot_substitute_controller_for_closed_source(self):
        b=self.copy(self.binding);actual=self.copy(self.actual)
        actual['startup_data_qualification']['source_sha']=b['controller_source_sha']
        b['startup_data_receipt_sha256']=a.digest(actual['startup_data_qualification'])
        with self.assertRaises(ValueError):self.invoke(binding=b,actual=actual)
        self.assertFalse(self.calls);self.assertFalse(self.export_calls)
    def test_qualified_command_paths_prefix_and_modes_cannot_be_changed(self):
        changes={'input_path':str(self.source/'backend'),'archive_prefix':str(self.source),
            'path_as_root':True,'archive_member_prefix':'other/','native_archive_qualification':True}
        for key,value in changes.items():
            payload={**self.payload,key:value};b,actual=self.reseal(payload)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'export report differs'):
                self.invoke(binding=b,actual=actual,export_effect=lambda *x:payload)
        self.assertFalse(self.calls);self.assertFalse(self.journal.exists())
    def test_export_admission_failure_never_falls_back_to_normal_upload(self):
        with self.assertRaisesRegex(ValueError,'member missing'):
            self.invoke(export_effect=ValueError('Committed export member missing'))
        self.assertFalse(self.normal_calls);self.assertFalse(self.calls);self.assertFalse(self.journal.exists())
    def test_changed_export_after_intent_blocks_dispatch_and_replay(self):
        changed=self.copy(self.payload);changed['files'][0]['sha256']='9'*64
        with self.assertRaisesRegex(ValueError,'changed before dispatch'):
            self.invoke(export_effect=[self.payload,changed])
        self.assertFalse(self.calls);self.assertTrue((self.journal/'_write-barrier.json').exists())
        with self.assertRaises(FileExistsError):self.invoke()
        self.assertFalse(self.calls)
    def test_unknown_closed_write_cannot_reset_with_path_controller_or_approval(self):
        result=self.invoke();self.assertIn('RECONCILIATION_REQUIRED',result['state'])
        b={**self.binding,'source_root':str(self.root/'another-controller'),
           'backend_export_root':str(self.root/'another-export'),'controller_source_sha':'d'*40}
        app=self.approval(b);app['rollback_operator']='another-synthetic-operator'
        with self.assertRaises(FileExistsError):self.invoke(binding=b,approval=app)
        self.assertEqual(len(self.calls),1)
    def test_restore_command_never_uses_export_or_upload_fallback(self):
        from scripts.test_current_guarded_bootstrap_restore import fixture
        journal=self.root/'restore-journal';journal.mkdir(mode=0o700);b,actual,boot,normal=fixture(journal)
        adapter=a.ProviderAdapter(journal)
        command=adapter._command('restore_guarded_bootstrap',b,None)
        self.assertEqual(command[:2],['railway','api']);self.assertNotIn('up',command)
        with self.assertRaises(ValueError):adapter._command('restore_guarded_bootstrap',{**b,'backend_export_root':str(self.export)},None)
        with self.assertRaises(ValueError):adapter._command('unreviewed-action',b,None)
        self.assertFalse(self.calls)
    def test_digest_only_bootstrap_or_missing_normal_uuid_cannot_restore(self):
        from scripts.test_current_guarded_bootstrap_restore import fixture
        for kind in ['digest-only','missing-normal-uuid']:
            journal=self.root/kind;journal.mkdir(mode=0o700);b,actual,boot,normal=fixture(journal)
            if kind=='digest-only':boot.pop('qualified_bootstrap_evidence')
            else:normal.pop('provider_backend_deployment_id')
            for record in [boot,normal]:
                path=journal/(record['operation_id']+'.json');path.write_text(json.dumps(record));path.chmod(0o600)
            b['restore_context']['bootstrap_record_sha256']=a.digest(boot)
            b['restore_context']['applied_normal_record_sha256']=a.digest(normal)
            with self.subTest(kind=kind),self.assertRaises(ValueError):a.validate_guarded_restore_context(journal,b,actual)
        self.assertFalse(self.calls)
    def test_paired_bootstrap_uses_qualified_export_input_cwd_and_one_intent(self):
        result=self.invoke();self.assertEqual(len(self.calls),1)
        argv,kwargs=self.calls[0];self.assertEqual(argv[-1],self.payload['input_path'])
        self.assertEqual(kwargs['cwd'],self.payload['archive_prefix']);self.assertNotIn('--path-as-root',argv)
        self.assertEqual(len(self.export_calls),2);self.assertFalse(self.normal_calls)
        self.assertEqual(result['binding']['source_sha'],'a'*40)
        self.assertEqual(result['binding']['controller_source_sha'],'c'*40)
        self.assertEqual(result['operations_journal_identity_sha256'],a._operation_journal_identity(self.journal))
    def normal_fixture(self):
        b={k:v for k,v in self.binding.items() if k not in {'backend_export_root','controller_source_sha'}}
        b.update(source_sha='c'*40,guarded_recovery_receipt_sha256='7'*64)
        payload={'scope':'OFFLINE_CLI_EQUIVALENT_FILE_MEMBERSHIP_NOT_PROVIDER_UPLOAD',
            'source':'c'*40,'runtime_expected_sha256':'5'*64,'files':[]}
        b['backend_payload_sha256']=a.digest(payload)
        b,startup=startup_fixture(b,self.now,a.hashlib.sha256(self.guard).hexdigest(),config_sha='1'*64)
        actual={**self.actual,**b,**startup,'guarded_rollback_sha256':'d'*64,'startup_qualified':True,
            'guarded_recovery_receipt_sha256':'7'*64}
        return b,actual,payload
    def test_ordinary_normal_backend_uses_original_source_path_and_qualifier(self):
        b,actual,payload=self.normal_fixture()
        self.invoke(binding=b,actual=actual,action='release_backend',normal_payload=payload)
        argv,kwargs=self.calls[0];self.assertEqual(argv[-1],str(self.source.resolve()/'backend'))
        self.assertEqual(kwargs['cwd'],self.source.resolve())
        self.assertEqual(len(self.normal_calls),1);self.assertFalse(self.export_calls)
    def test_ordinary_normal_backend_cannot_use_wrong_head(self):
        b,actual,payload=self.normal_fixture()
        with self.assertRaisesRegex(ValueError,'exact/clean'):
            self.invoke(binding=b,actual=actual,action='release_backend',normal_payload=payload,head='a'*40)
        self.assertFalse(self.calls);self.assertFalse(self.normal_calls);self.assertFalse(self.export_calls)
