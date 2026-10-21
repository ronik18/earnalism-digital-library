"""Synthetic changed-scope tests only; no provider/HTTP or database calls."""
import copy
import datetime as dt
import json
import os
import unittest
from unittest.mock import patch
from scripts import verify_backend_release as v


class FrontendOnlyEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 21, 18, tzinfo=dt.timezone.utc)
        self.env = {'FRONTEND_SHA': v.EXACT_FRONTEND, 'FRONTEND_TREE': v.EXACT_FRONTEND_TREE,
                    'BACKEND_SHA': v.EXACT_BACKEND, 'BACKEND_TREE': v.EXACT_BACKEND_TREE}
        self.e = {'schema': 'reader-backend-provider-evidence.v1',
                  'github_source_sha': v.EXACT_BACKEND,
                  'authenticated_provider_ui_receipt': {
                      'observed_at_utc': self.now.isoformat(), 'authenticated_provider_ui': True,
                      'project_id': v.PROJECT, 'service_id': v.SERVICE, 'environment_id': v.ENVIRONMENT,
                      'deployment': {'id': v.EXACT_DEPLOYMENT, 'current_active_card': True,
                                     'status': 'ACTIVE', 'service_status': 'Online',
                                     'deployment_result': 'Deployment successful', 'replicas_display': 1,
                                     'full_source_sha': v.EXACT_BACKEND}},
                  'railway_origin_github_commit_status': {
                      'id': 56859539640, 'state': 'success', 'context': 'earnalism - earnalism',
                      'creator': 'railway-app[bot]', 'description': 'Success - api.theearnalism.com',
                      'target_url': 'https://railway.com/project/'+v.PROJECT+'/service/'+v.SERVICE+
                                    '?id='+v.EXACT_DEPLOYMENT+'&environmentId='+v.ENVIRONMENT}}

    def check(self):
        with patch.dict(os.environ, self.env, clear=True):
            return v.verify_operator_provider_evidence(json.dumps(self.e), v.EXACT_BACKEND, self.now)

    def test_exact_evidence_passes(self):
        self.assertEqual(len(self.check()), 64)

    def test_all_source_scope_dimensions_fail_closed(self):
        for key in self.env:
            with self.subTest(key=key):
                with patch.dict(os.environ, {**self.env, key: 'a'*40}, clear=True):
                    with self.assertRaises(v.VerificationError):
                        v.verify_operator_provider_evidence(json.dumps(self.e), v.EXACT_BACKEND, self.now)

    def test_stale_future_and_naive_observations_fail(self):
        ui = self.e['authenticated_provider_ui_receipt']
        for stamp in ((self.now-dt.timedelta(minutes=15, seconds=1)).isoformat(),
                      (self.now+dt.timedelta(seconds=1)).isoformat(), '2026-10-21T18:00:00'):
            ui['observed_at_utc'] = stamp
            with self.assertRaises(v.VerificationError): self.check()

    def test_provider_and_github_drift_fail(self):
        original = copy.deepcopy(self.e)
        for section, key, value in [
            ('authenticated_provider_ui_receipt', 'authenticated_provider_ui', False),
            ('authenticated_provider_ui_receipt', 'service_id', 'other'),
            ('railway_origin_github_commit_status', 'creator', 'someone'),
            ('railway_origin_github_commit_status', 'state', 'pending'),
            ('railway_origin_github_commit_status', 'id', True),
            ('railway_origin_github_commit_status', 'target_url', 'https://evil.example/')]:
            self.e = copy.deepcopy(original); self.e[section][key] = value
            with self.subTest(key=key), self.assertRaises(v.VerificationError): self.check()
        for key, value in [('current_active_card', False), ('status', 'REMOVED'),
                           ('replicas_display', True), ('id', 'other'), ('full_source_sha', 'a'*40)]:
            self.e = copy.deepcopy(original); self.e['authenticated_provider_ui_receipt']['deployment'][key] = value
            with self.subTest(key=key), self.assertRaises(v.VerificationError): self.check()

    def test_malformed_missing_oversize_evidence_fails(self):
        for raw in ('', '{', '{}', 'x'*32769):
            with patch.dict(os.environ, self.env, clear=True):
                with self.assertRaises((ValueError, KeyError)):
                    v.verify_operator_provider_evidence(raw, v.EXACT_BACKEND, self.now)

    def test_protected_approval_requires_exact_raw_digest_and_mode(self):
        raw = json.dumps(self.e)
        good = {'backend_provider_evidence_sha256': v.evidence_digest(raw),
                'backend_provider_evidence_mode': 'authenticated-ui-and-railway-origin-status.v1'}
        v.verify_protected_evidence_binding(raw, json.dumps(good))
        for bad in ({}, {**good, 'backend_provider_evidence_sha256': '0'*64},
                    {**good, 'backend_provider_evidence_mode': 'CLI'}):
            with self.assertRaises(v.VerificationError): v.verify_protected_evidence_binding(raw, json.dumps(bad))
        with self.assertRaises(v.VerificationError): v.verify_protected_evidence_binding(raw+' ', json.dumps(good))

    def test_live_health_and_admin_contract_are_still_required(self):
        h = {'status': 'ok', 'deployment': {'status': 'AVAILABLE', 'git_sha': v.EXACT_BACKEND,
             'project_id': v.PROJECT, 'service_id': v.SERVICE, 'environment_id': v.ENVIRONMENT,
             'deployment_id': v.EXACT_DEPLOYMENT}}
        schema = {'paths': {p: {'post': {}} for p in ('/api/reading-pass/sessions/start',
                  '/api/reading-pass/leases/renew', '/api/reading-pass/sessions/end')},
                  'components': {'schemas': {'Lease': {'properties': {'text_phase': {}}}}}}
        schema['paths']['/api/admin/books/{book_id}/serving-binding'] = {'get': {}}
        args = (v.EXACT_BACKEND, v.PROJECT, v.SERVICE, v.ENVIRONMENT)
        v.verify_http_without_provider(*args, h, schema, {'Cache-Control': 'no-store'})
        with self.assertRaises(v.VerificationError): v.verify_http_without_provider(*args, h, schema, {})
        h['deployment']['deployment_id'] = 'other'
        with self.assertRaises(v.VerificationError): v.verify_http_without_provider(*args, h, schema, {'Cache-Control':'no-store'})
        h['deployment']['deployment_id'] = v.EXACT_DEPLOYMENT
        del schema['paths']['/api/admin/books/{book_id}/serving-binding']
        with self.assertRaises(v.VerificationError): v.verify_http_without_provider(*args, h, schema, {'Cache-Control':'no-store'})

    def test_protected_binding_failure_precedes_all_network_reads(self):
        argv = ['verify', '--operator-provider-evidence', '--require-protected-binding',
                '--expected-sha', v.EXACT_BACKEND, '--project', v.PROJECT,
                '--service', v.SERVICE, '--environment', v.ENVIRONMENT, '--backend-url', v.ORIGIN]
        env = {**self.env, 'BACKEND_PROVIDER_EVIDENCE_JSON': json.dumps(self.e), 'RELEASE_APPROVAL_JSON': '{}'}
        with patch.dict(os.environ, env, clear=True), patch('sys.argv', argv), \
                patch.object(v, 'verify_operator_provider_evidence', return_value='a'*64), \
                patch.object(v, 'read_json') as http, patch.object(v.subprocess, 'run') as cli, \
                patch('sys.stderr'):
            self.assertEqual(v.main(), 1)
            http.assert_not_called(); cli.assert_not_called()

    def test_evidence_mode_never_invokes_provider_cli(self):
        argv = ['verify', '--operator-provider-evidence', '--expected-sha', v.EXACT_BACKEND,
                '--project', v.PROJECT, '--service', v.SERVICE, '--environment', v.ENVIRONMENT,
                '--backend-url', v.ORIGIN]
        with patch('sys.argv', argv), patch.object(v, 'verify_operator_provider_evidence', return_value='a'*64), \
                patch.object(v, 'read_json', return_value=({}, {})) as http, \
                patch.object(v, 'verify_http_without_provider', return_value={}), \
                patch.object(v.subprocess, 'run') as cli, patch('sys.stdout'):
            self.assertEqual(v.main(), 0)
            self.assertEqual(http.call_count, 2); cli.assert_not_called()


if __name__ == '__main__': unittest.main()
