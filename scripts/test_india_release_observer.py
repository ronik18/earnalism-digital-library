import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from scripts.india_release_observer import NativeMetadataObserver, ProtectedReleasePreflight, rollback_verdict
from scripts.india_release_provider_adapter import PROJECT, TEAM, CLI_VERSIONS

SHA = 'a4f76c51dfafe50ee35212cb707ea884ae12da62'
class ObserverTests(unittest.TestCase):
    def observer(self, project=None, deployments=None, candidate=None):
        self.calls=[]
        responses=[project if project is not None else {'id':PROJECT,'accountId':TEAM,'link':{'deploymentEnabled':False},'env':[{'value':'DO_NOT_RETAIN'}]}]
        if candidate is not None: responses.append(candidate)
        responses.append(deployments if deployments is not None else [{'id':'old','status':'SUCCESS','meta':{'commitHash':'e68d70bcf35797c5707b58511cad86dffaec5fe3'},'canRollback':True,'secret':'DO_NOT_RETAIN'}])
        def run(argv, **kw):
            if argv[1:] == ['--version']:
                return subprocess.CompletedProcess(argv, 0, CLI_VERSIONS[argv[0]], '')
            self.calls.append(argv)
            return subprocess.CompletedProcess(argv,0,json.dumps(responses.pop(0)),'')
        return NativeMetadataObserver('.',run=run,clock=lambda:datetime(2026,10,28,tzinfo=timezone.utc))

    def test_fixed_read_commands_and_redaction(self):
        data=self.observer().collect()
        self.assertNotIn('DO_NOT_RETAIN',json.dumps(data))
        self.assertTrue(data['frontend_auto_deploy_disabled'])
        self.assertIsNone(data['backend_auto_deploy_disabled'])
        self.assertEqual(self.calls[0][2],'/v9/projects/'+PROJECT)
        self.assertEqual(self.calls[0][4],'GET')
        self.assertEqual(self.calls[1][1:3],['deployment','list'])
        self.assertNotIn('--token',sum(self.calls,[]))

    def test_wrong_scope_blocks(self):
        with self.assertRaises(ValueError):self.observer(project={'id':'other','accountId':TEAM}).collect()

    def test_unknown_suppression_not_false(self):
        data=self.observer(project={'id':PROJECT,'accountId':TEAM,'link':{'deploymentEnabled':{'main':False}}}).collect()
        self.assertFalse(data['frontend_auto_deploy_disabled'])

    def test_invalid_candidate_never_reads(self):
        ob=self.observer()
        with self.assertRaises(ValueError):ob.collect('https://untrusted')
        self.assertEqual(self.calls,[])

    def test_candidate_scope_blocks(self):
        with self.assertRaises(ValueError):self.observer(candidate={'id':'dpl_safe','projectId':'wrong'}).collect('dpl_safe')

    def test_unknown_shape_fails(self):
        with self.assertRaises(ValueError):self.observer(deployments={'unknown':[]}).collect()

    def test_read_error_does_not_expose_output(self):
        def run(argv, **kw):
            if argv[1:] == ['--version']:
                return subprocess.CompletedProcess(argv, 0, CLI_VERSIONS[argv[0]], '')
            return subprocess.CompletedProcess([],1,'private','secret')
        ob=NativeMetadataObserver('.',run=run)
        with self.assertRaisesRegex(ValueError,'Read-only provider observation failed'):ob.collect()

    def test_unreviewed_cli_stops_before_provider_read(self):
        calls=[]
        def run(argv, **kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv,0,'99.0.0','')
        with self.assertRaisesRegex(ValueError,'Reviewed provider CLI version'):
            NativeMetadataObserver('.',run=run).collect()
        self.assertEqual(calls,[['vercel','--version']])

    def test_timeout_is_bounded_hold_without_retry_or_output(self):
        calls=[]
        def run(argv, **kw):
            calls.append(argv)
            if argv[1:] == ['--version']:
                return subprocess.CompletedProcess(argv,0,CLI_VERSIONS[argv[0]],'')
            raise subprocess.TimeoutExpired(argv,60,output='private',stderr='secret')
        with self.assertRaisesRegex(ValueError,'timed out; no retry'):
            NativeMetadataObserver('.',run=run).collect()
        self.assertEqual(len(calls),3)

    def test_capability_never_qualifies(self):
        contract={'rollback':{'deployment_id':'old','source_sha':SHA,'source_manifest_sha256':'a'*64,'config_sha256':'b'*64}}
        result=rollback_verdict([{'id':'old','git_sha':SHA,'status':'SUCCESS','canRollback':True}],contract)
        self.assertFalse(result['qualified']);self.assertTrue(result['capability_only'])

    def test_absent_artifact_held(self):
        contract={'rollback':{'deployment_id':'new','source_sha':SHA,'source_manifest_sha256':'a'*64,'config_sha256':'b'*64}}
        self.assertEqual(rollback_verdict([],contract)['reason'],'GUARDED_ARTIFACT_NOT_OBSERVED')

    def test_preflight_no_write_and_no_approval_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            runner=ProtectedReleasePreflight(self.observer());runner.JOURNAL=Path(temp)/'not-created'
            result=runner.check({'source_sha':SHA,'approved':True,'owner_authorized':True})
            self.assertFalse(result['execution_permitted'])
            self.assertIn('CURRENT_OWNER_PROHIBITS_EXECUTION',result['holds'])
            self.assertFalse(runner.JOURNAL.exists())

    def test_unknown_journal_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            runner=ProtectedReleasePreflight(self.observer());runner.JOURNAL=Path(temp).resolve()
            (runner.JOURNAL/'intent.json').write_text('{"state":"INTENT_RECONCILE_BEFORE_RETRY"}')
            self.assertIn('UNKNOWN_WRITE_REQUIRES_READ_ONLY_RECONCILIATION',runner.check({'source_sha':SHA})['holds'])

    def test_symlinked_journal_is_never_enumerated_or_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();private=root/'private';private.mkdir(mode=0o700)
            (private/'intent.json').write_text('{"private":"DO_NOT_READ"}')
            link=root/'journal';link.symlink_to(private)
            runner=ProtectedReleasePreflight(self.observer());runner.JOURNAL=link
            with mock.patch.object(Path,'glob',side_effect=AssertionError('unsafe enumeration')), \
                 mock.patch('os.open',side_effect=AssertionError('unsafe content read')):
                result=runner.check({'source_sha':SHA})
            self.assertIn('FIXED_JOURNAL_NOT_A_REAL_DIRECTORY',result['holds'])

    def test_permissive_journal_is_never_enumerated_or_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();root.chmod(0o777)
            runner=ProtectedReleasePreflight(self.observer());runner.JOURNAL=root
            with mock.patch.object(Path,'glob',side_effect=AssertionError('unsafe enumeration')), \
                 mock.patch('os.open',side_effect=AssertionError('unsafe content read')):
                result=runner.check({'source_sha':SHA})
            self.assertIn('JOURNAL_OWNER_OR_PERMISSIONS_UNQUALIFIED',result['holds'])

    def test_symlinked_receipt_is_not_opened(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();journal=root/'journal';journal.mkdir(mode=0o700)
            private=root/'private';private.write_text('DO_NOT_READ')
            (journal/'intent.json').symlink_to(private)
            runner=ProtectedReleasePreflight(self.observer());runner.JOURNAL=journal
            with mock.patch('os.open',side_effect=AssertionError('unsafe receipt read')):
                result=runner.check({'source_sha':SHA})
            self.assertIn('UNSAFE_JOURNAL_RECEIPT',result['holds'])

if __name__ == '__main__':unittest.main()
