import contextlib
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from scripts import verify_backend_release as gate

class DiagnosticOnly(unittest.TestCase):
    def invoke(self, provider=None, error=None, reads=None):
        args=['gate','--expected-sha','0f2bb1e728890f1f0e41ded9b12f07c76246bce0','--project',gate.PROJECT,'--service',gate.SERVICE,'--environment',gate.ENVIRONMENT,'--backend-url',gate.ORIGIN]
        out=io.StringIO()
        with patch('sys.argv',args),patch.object(gate.subprocess,'run',return_value=provider,side_effect=error),patch.object(gate,'read_json',side_effect=reads),contextlib.redirect_stderr(out):
            self.assertEqual(gate.main(),1)
        return json.loads(out.getvalue())
    def test_provider_error_sanitized(self):
        e=subprocess.CalledProcessError(9,['railway'],output='private-output',stderr='private-stderr')
        d=self.invoke(error=e)
        self.assertEqual(d['stage'],'provider_cli_read');self.assertEqual(d['provider_exit_code'],9)
        self.assertNotIn('private',json.dumps(d))
    def test_http_error_not_logged(self):
        d=self.invoke(provider=subprocess.CompletedProcess([],0,'{}'),reads=OSError('private-url'))
        self.assertEqual(d['stage'],'health_http_read');self.assertNotIn('private',json.dumps(d))
    def test_validation_reason_preserved(self):
        d=self.invoke(provider=subprocess.CompletedProcess([],0,'{}'),reads=[({'status':'bad'},{}),({}, {})])
        self.assertEqual(d['stage'],'identity_health_schema_validation');self.assertEqual(d['reason'],'Backend unhealthy or malformed')
    def test_runner_is_diagnostic_only(self):
        text=Path('.github/workflows/backend-identity-diagnostic.yml').read_text()
        self.assertEqual(text.count('secrets.'),1)
        self.assertIn('secrets.RAILWAY_TOKEN',text)
        for forbidden in ('workflow_call:', 'pull_request:', 'push:', 'VERCEL_TOKEN','railway run','railway ssh','verify_reader_startup','reader-frontend-production.yml','vercel deploy','vercel promote','environment:'):
            self.assertNotIn(forbidden,text)
        self.assertIn('timeout-minutes: 5',text)
        self.assertIn("github.ref == 'refs/heads/main'",text)

class ProviderClassification(unittest.TestCase):
    def error(self, text):
        return subprocess.CalledProcessError(1, ['railway'], output='private-stdout', stderr=text)
    def test_explicit_categories_only(self):
        cases = {
            'Error: token has expired': 'CREDENTIAL_EXPIRED_REPORTED',
            'Error: invalid token': 'CREDENTIAL_INVALID_REPORTED',
            'Error: insufficient token scope': 'TOKEN_TYPE_OR_SCOPE_REPORTED',
            'Error: not authorized to access this project': 'PROJECT_ACCESS_DENIED_REPORTED',
            'Error: project not found': 'PROJECT_UNAVAILABLE_REPORTED',
            'Error: not logged in': 'AUTHENTICATION_REQUIRED_REPORTED',
            'Error: could not resolve host': 'TRANSPORT_DNS_REPORTED',
            'Error: certificate verify failed': 'TRANSPORT_TLS_REPORTED',
            'Error: connection refused': 'TRANSPORT_CONNECTION_REPORTED',
            'Error: unexpected argument': 'COMMAND_ARGUMENT_ERROR_REPORTED',
            'Error: cannot find module': 'RUNTIME_DEPENDENCY_ERROR_REPORTED',
            'Error: invalid configuration': 'CONFIGURATION_ERROR_REPORTED',
        }
        for text, category in cases.items():
            with self.subTest(category=category):
                self.assertEqual(gate.classify_provider_error(self.error(text)), (category, 'REPORTED_STDERR_PATTERN'))
    def test_unknown_empty_ambiguous_and_oversized_fail_closed(self):
        for text in (None, '', 'unexpected private failure', 'invalid token; connection refused', 'x'*65537):
            with self.subTest(kind=type(text).__name__):
                self.assertEqual(gate.classify_provider_error(self.error(text))[0], 'UNKNOWN')
    def test_bytes_ansi_and_local_errors(self):
        self.assertEqual(gate.classify_provider_error(self.error(b'\x1b[31mError: connection refused\x1b[0m'))[0], 'TRANSPORT_CONNECTION_REPORTED')
        self.assertEqual(gate.classify_provider_error(FileNotFoundError('private-path'))[0], 'COMMAND_UNAVAILABLE')
        self.assertEqual(gate.classify_provider_error(subprocess.TimeoutExpired('private-command',40))[0], 'TRANSPORT_OR_COMMAND_TIMEOUT')
        self.assertEqual(gate.classify_provider_error(RuntimeError('invalid token'))[0], 'UNKNOWN')
    def test_boundary_never_emits_raw_stderr_or_stdout(self):
        args=['gate','--expected-sha','0f2bb1e728890f1f0e41ded9b12f07c76246bce0','--project',gate.PROJECT,'--service',gate.SERVICE,'--environment',gate.ENVIRONMENT,'--backend-url',gate.ORIGIN]
        out=io.StringIO();error=self.error('Error: invalid token; private-token=fixture-secret https://user:fixture-secret@private.invalid')
        with patch('sys.argv',args),patch.object(gate.subprocess,'run',side_effect=error),contextlib.redirect_stderr(out):
            self.assertEqual(gate.main(),1)
        d=json.loads(out.getvalue());self.assertEqual(d['stage'],'provider_cli_read');self.assertEqual(d['provider_exit_code'],1)
        self.assertEqual(d['provider_error_category'],'CREDENTIAL_INVALID_REPORTED')
        for fragment in ('fixture-secret','private-stdout','private.invalid','private-token'):
            self.assertNotIn(fragment,out.getvalue())

if __name__=='__main__':unittest.main()
