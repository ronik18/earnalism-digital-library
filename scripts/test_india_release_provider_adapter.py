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
        approval = {**self.approval('release_guarded_bootstrap', b), 'bootstrap_preflight_sha256':'d'*64}
        actual = {**self.observe(), **b, 'bootstrap_preflight_sha256':'d'*64,
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
