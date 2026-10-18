import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts.qualify_frontend_build_only import private_environment, selected_inventory
from scripts.test_manual_production_release_workflow import ROOT, REGRESSION, parse_workflow


class BuildQualificationBoundaryTests(unittest.TestCase):
    def test_manual_only_job_cannot_request_production_permissions_or_environment(self):
        workflow = parse_workflow(REGRESSION)
        job = workflow['jobs']['frontend_build_only']
        self.assertEqual(job['permissions'], {'contents': 'read'})
        self.assertNotIn('environment', job)
        self.assertEqual(job['timeout-minutes'], 25)
        self.assertNotIn('strategy', job)
        for expression in ("github.event_name == 'workflow_dispatch'", 'inputs.build_only == true',
                           "github.ref == 'refs/heads/codex/reader-only-strict-fit-20261017'",
                           'inputs.target_sha == github.sha',
                           "inputs.confirm_production == 'BUILD_AND_PACKAGE_ONLY'"):
            self.assertIn(expression, job['if'])
        text = json.dumps(job)
        self.assertNotIn('secrets.', text)
        self.assertNotIn('reader-frontend-production', text)
        checkout = job['steps'][0]
        self.assertFalse(checkout['with']['persist-credentials'])
        for step in job['steps']:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'@[0-9a-f]{40}$')

    def test_normal_ci_coverage_and_concurrency_are_separate_from_new_manual_mode(self):
        workflow = parse_workflow(REGRESSION)
        self.assertFalse(workflow['on']['workflow_dispatch']['inputs']['build_only']['default'])
        self.assertEqual(workflow['jobs']['regression']['if'],
                         "github.event_name != 'workflow_dispatch' || !inputs.build_only")
        commands = '\n'.join(step.get('run', '') for step in workflow['jobs']['regression']['steps'])
        self.assertIn('scripts.test_verify_isolated_seo_build', commands)
        self.assertIn('scripts.test_frontend_build_qualification', commands)
        group = workflow['concurrency']['group']
        self.assertIn("format('frontend-build-only-{0}', github.run_id)", group)
        self.assertIn("format('go-live-regression-{0}', github.ref)", group)
        self.assertEqual(workflow['concurrency']['cancel-in-progress'],
                         "${{ github.event_name != 'workflow_dispatch' || !inputs.build_only }}")
        self.assertNotIn('reader-manual-frontend-production', REGRESSION)

    def test_child_environment_discards_credentials_and_disables_live_api(self):
        with mock.patch.dict(os.environ, {'VERCEL_TOKEN': 'never-forward',
                                         'GITHUB_TOKEN': 'never-forward',
                                         'RAILWAY_TOKEN': 'never-forward',
                                         'REACT_APP_BACKEND_URL': 'https://api.theearnalism.com'}):
            env = private_environment(Path('/task-private'))
        for key in ('VERCEL_TOKEN', 'GITHUB_TOKEN', 'RAILWAY_TOKEN'):
            self.assertNotIn(key, env)
        self.assertEqual(env['REACT_APP_BACKEND_URL'], '')
        self.assertEqual(env['REACT_APP_API_URL'], '')
        self.assertEqual(env['SEO_API_BASE_URL'], '')
        self.assertEqual(env['HOME'], '/task-private/home')
        self.assertNotEqual(env['NPM_CONFIG_USERCONFIG'], env['NPM_CONFIG_GLOBALCONFIG'])

    def test_runner_contains_only_pinned_local_build_and_file_inspection_path(self):
        source = (ROOT / 'scripts/qualify_frontend_build_only.py').read_text()
        constants = [node.value for node in ast.walk(ast.parse(source))
                     if isinstance(node, ast.Constant) and isinstance(node.value, str)]
        for command in ('deploy', 'promote', 'alias', 'rollback', 'railway'):
            self.assertNotIn(command, constants)
        self.assertIn("str(cli / 'dist/vc.js'), 'build', '--prod', '--yes'", source)
        self.assertIn('inspectDeploymentFiles', source)
        self.assertNotIn('createDeployment', source)
        self.assertNotIn('shell=True', source)
        self.assertIn("'vercel@63.1.2'", source)
        self.assertIn('PENDING_INDEPENDENT_EXACT_LINUX_RESOLUTION_REVIEW', source)
        # Read-only unit/static checks never invoke the new build runner.

    def test_inventory_hashes_selected_bytes_and_rejects_change_escape_and_env_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / 'asset.txt'
            file.write_bytes(b'actual selected bytes')
            row = {'path': file.name, 'mode': 33188,
                   'sha': hashlib.sha1(file.read_bytes()).hexdigest()}
            result = selected_inventory(root, {'files': [row]})
            self.assertEqual(result['files'][0]['sha256'], hashlib.sha256(file.read_bytes()).hexdigest())
            file.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'changed'):
                selected_inventory(root, {'files': [row]})
            with self.assertRaisesRegex(ValueError, 'external'):
                selected_inventory(root, {'files': [{'path': '../outside', 'sha': '', 'mode': 0}]})
            file = root / '.env.production.local'
            file.write_text('fixture contents never inspected')
            with self.assertRaisesRegex(ValueError, 'Environment file'):
                selected_inventory(root, {'files': [{'path': file.name, 'sha': '', 'mode': 0}]})


if __name__ == '__main__':
    unittest.main()
