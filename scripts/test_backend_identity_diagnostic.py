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

if __name__=='__main__':unittest.main()
