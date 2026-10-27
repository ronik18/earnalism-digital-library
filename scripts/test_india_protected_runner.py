from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from scripts import india_protected_runner as runner
from scripts.india_release_observer import ProtectedReleasePreflight

SHA='a'*40
APP='b'*40


class RunnerTests(unittest.TestCase):
    def env(self):
        return {'GITHUB_REPOSITORY':runner.REPOSITORY,'GITHUB_REF':'refs/heads/main',
            'GITHUB_EVENT_NAME':'workflow_dispatch','RUNNER_ENVIRONMENT':'self-hosted',
            'GITHUB_SHA':SHA,'EXPECTED_CONTROLLER_SHA':SHA,
            'EARNALISM_RUN_MODE':'READ_ONLY_OBSERVATION','EARNALISM_EXECUTION_ENABLED':'false',
            'GITHUB_WORKSPACE':'/workspace','RUNNER_TEMP':'/runner-temp'}

    def git(self,*args):
        return {('rev-parse','HEAD'):SHA,('status','--porcelain','--untracked-files=all'):'',
            ('rev-parse',APP+'^{tree}'):'c'*40,
            ('rev-parse',APP+':frontend'):'d'*40,
            ('rev-parse',APP+':backend'):'e'*40}[args]

    def contract(self):
        return {'application_sha':APP,'application_root_tree':'c'*40,
            'frontend_subtree':'d'*40,'backend_subtree':'e'*40,
            'scope':{'territories':['IN'],'deployment_authorized':False,
                     'publication_authorized':False,'paid_sessions':False}}

    def test_exact_main_only_no_ambient_authority(self):
        self.assertEqual(runner.verified_source(self.env(),self.git),SHA)
        for key,value in [('GITHUB_REF','refs/pull/12/merge'),('GITHUB_EVENT_NAME','push'),
            ('GITHUB_REPOSITORY','attacker/repo'),('RUNNER_ENVIRONMENT','github-hosted'),
            ('EARNALISM_EXECUTION_ENABLED','true'),('EXPECTED_CONTROLLER_SHA','f'*40),
            ('EARNALISM_RUN_MODE','DEPLOY_PRODUCTION')]:
            env=self.env();env[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):runner.verified_source(env,self.git)

    def test_dirty_or_misidentified_source_rejected(self):
        for result in [' M scripts/tool.py','?? private.env']:
            def git(*args):return result if args[0]=='status' else self.git(*args)
            with self.assertRaises(ValueError):runner.verified_source(self.env(),git)

    def test_contract_tamper_stops_before_provider(self):
        observer=mock.Mock()
        contract=self.contract();contract['backend_subtree']='f'*40
        with self.assertRaises(ValueError):runner.observe(self.env(),self.git,observer,contract)
        observer.collect.assert_not_called()

    def test_contract_scope_expansion_cannot_supply_authority(self):
        observer=mock.Mock();contract=self.contract()
        contract['scope']['deployment_authorized']=True
        with self.assertRaises(ValueError):runner.observe(self.env(),self.git,observer,contract)
        observer.collect.assert_not_called()

    def test_complete_metadata_cannot_enable_execution(self):
        observer=mock.Mock()
        observer.collect.return_value={'frontend_auto_deploy_disabled':True,
            'backend_auto_deploy_disabled':True,'deployments':[], 'observation_sha256':'a'*64}
        with tempfile.TemporaryDirectory() as temp,mock.patch.object(ProtectedReleasePreflight,'JOURNAL',Path(temp)/'missing'):
            report=runner.observe(self.env(),self.git,observer,self.contract())
        self.assertFalse(report['execution_permitted']);self.assertEqual(report['provider_mutations'],0)
        self.assertIn('AUTHENTIC_PLATFORM_PROTECTED_EXECUTOR_REQUIRED',report['holds'])
        self.assertIn('FIXED_JOURNAL_NOT_PROVISIONED',report['holds'])
        self.assertEqual(report['controller_sha'],SHA)

    def test_journal_does_not_infer_durability_or_modify_history(self):
        with tempfile.TemporaryDirectory() as temp:
            journal=Path(temp).resolve()/'journal';journal.mkdir(mode=0o700)
            receipt=journal/'intent.json';receipt.write_text('{"state":"UNKNOWN"}')
            original=receipt.read_bytes()
            self.assertEqual(runner.journal_holds(journal,'/workspace','/runner-temp'),
                ['DURABLE_HOST_AND_PROTECTED_EXECUTOR_ATTESTATION_REQUIRED'])
            self.assertEqual(receipt.read_bytes(),original)
            journal.chmod(0o777)
            self.assertEqual(runner.journal_holds(journal,'/workspace','/runner-temp'),
                ['JOURNAL_OWNER_OR_PERMISSIONS_UNQUALIFIED'])

    def test_ephemeral_or_linked_journal_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();journal=root/'journal';journal.mkdir(mode=0o700)
            self.assertEqual(runner.journal_holds(journal,root,'/runner-temp'),
                ['JOURNAL_MUST_BE_OUTSIDE_EPHEMERAL_RUNNER_DIRECTORIES'])
            link=root/'link';link.symlink_to(journal)
            self.assertEqual(runner.journal_holds(link,'/workspace','/runner-temp'),
                ['FIXED_JOURNAL_NOT_A_REAL_DIRECTORY'])

    def test_workflow_protected_nonexecuting_and_serial(self):
        source=(runner.ROOT/'.github/workflows/india-protected-observation.yml').read_text()
        self.assertIn('environment: reader-frontend-production',source)
        self.assertIn('group: reader-manual-frontend-production',source)
        self.assertIn('cancel-in-progress: false',source)
        self.assertIn('runs-on: [self-hosted, earnalism-release]',source)
        self.assertIn("github.ref == 'refs/heads/main'",source)
        self.assertIn('inputs.controller_sha == github.sha',source)
        self.assertIn("EARNALISM_EXECUTION_ENABLED: 'false'",source)
        self.assertNotIn('ProviderAdapter(',source)
        self.assertNotIn('workflow_run:',source)
        self.assertNotIn('push:',source)

    def test_failure_artifact_never_retains_provider_exception_text(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp).resolve()/'safe.json'
            with mock.patch.dict(os.environ,{'RUNNER_TEMP':str(output.parent)}), \
                 mock.patch.object(sys,'argv',['runner','--output',str(output)]), \
                 mock.patch.object(runner,'observe',side_effect=ValueError('PRIVATE_PROVIDER_VALUE')):
                with self.assertRaises(SystemExit) as raised:runner.main()
            self.assertEqual(raised.exception.code,1)
            report=json.loads(output.read_text())
            self.assertNotIn('PRIVATE_PROVIDER_VALUE',output.read_text())
            self.assertFalse(report['execution_permitted'])

    def test_report_cannot_target_workspace_or_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();output=root/'existing.json';output.write_text('preserve')
            with mock.patch.dict(os.environ,{'RUNNER_TEMP':str(root)}), \
                 mock.patch.object(sys,'argv',['runner','--output',str(output)]), \
                 mock.patch.object(runner,'observe',return_value={'holds':[]}):
                with self.assertRaises(FileExistsError):runner.main()
            self.assertEqual(output.read_text(),'preserve')


if __name__=='__main__':unittest.main()
