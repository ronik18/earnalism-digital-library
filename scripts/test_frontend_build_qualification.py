import ast
import hashlib
import json
import os
import shlex
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts.qualify_frontend_build_only import (build_environment, build_settings, local_build_command, private_environment,
                                                public_local_config, record_public_install_log, selected_inventory)
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

    def test_public_install_pins_the_actual_reviewed_tools_without_disabling_lock(self):
        reference_path = ROOT / 'scripts/frontend_build_dependency_reference.json'
        before = reference_path.read_bytes()
        reviewed = json.loads(before)['observed_unlocked_tools']
        command = shlex.split(build_settings(True)['settings']['installCommand'])
        self.assertEqual(command[:2], ['npm', 'install'])
        self.assertIn('--legacy-peer-deps', command)
        self.assertIn('--no-save', command)
        self.assertIn('--package-lock=true', command)
        self.assertNotIn('--package-lock=false', command)
        actual = dict(arg.rsplit('@', 1) for arg in command[2:] if not arg.startswith('--'))
        expected = {name.removeprefix('node_modules/'): identity['version']
                    for name, identity in reviewed.items()}
        self.assertEqual(len(actual), 4)
        self.assertEqual(actual, expected)
        self.assertEqual(reference_path.read_bytes(), before)

    def test_historical_build_recipe_and_other_settings_remain_unchanged(self):
        historical = build_settings(False)
        public = build_settings(True)
        self.assertEqual(historical['settings']['installCommand'], 'npm install --legacy-peer-deps')
        public['settings']['installCommand'] = historical['settings']['installCommand']
        self.assertEqual(public, historical)
        historical['settings']['installCommand'] = 'fixture-only mutation'
        self.assertEqual(build_settings(False)['settings']['installCommand'], 'npm install --legacy-peer-deps')

    def test_cutoff_is_only_an_explicit_public_build_child_input(self):
        env = private_environment(Path('/fixture'))
        before = dict(env)
        generated = Path('/fixture/generated-seo')
        historical = build_environment(env, generated)
        self.assertEqual(historical, {**env, 'NPM_CONFIG_SAVE': 'false',
                                     'SEO_ASSETS_OUTPUT_DIR': str(generated)})
        self.assertNotIn('NPM_CONFIG_BEFORE', env)
        self.assertNotIn('NPM_CONFIG_BEFORE', historical)
        public = build_environment(env, generated, True)
        self.assertEqual(public.pop('NPM_CONFIG_BEFORE'), '2026-11-17T00:00:00.000Z')
        self.assertEqual(public, historical)
        self.assertEqual(env, before)

    def test_public_external_config_preserves_original_bytes_and_every_other_field(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact, reports = root / 'artifact-F', root / 'reports'
            (artifact / 'frontend').mkdir(parents=True)
            reports.mkdir()
            original = (b'{\n  "installCommand": "npm install --legacy-peer-deps",\n'
                        b'  "framework":"create-react-app", "headers":[{"source":"/(.*)"}],\n'
                        b'  "redirects":[{"source":"/old","destination":"/new"}],\n'
                        b'  "rewrites":[{"source":"/reader","destination":"/index.html"}],\n'
                        b'  "functions":{"api/index.py":{"maxDuration":60}}\n}\n')
            source = artifact / 'frontend/vercel.json'
            source.write_bytes(original)
            settings = build_settings(True)
            config, evidence = public_local_config(artifact, reports, settings)
            command = settings['settings']['installCommand']
            self.assertFalse(config.is_relative_to(artifact))
            self.assertEqual(config.read_bytes(), original.replace(
                b'"npm install --legacy-peer-deps"', json.dumps(command).encode(), 1))
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual((reports / 'public-build-original-vercel.json').read_bytes(), original)
            self.assertEqual(set(json.loads(config.read_bytes())), set(json.loads(original)))
            expected = {**json.loads(original), 'installCommand': command}
            self.assertEqual(json.loads(config.read_bytes()), expected)
            self.assertEqual(evidence['changed_keys'], ['installCommand'])
            self.assertTrue(evidence['additional_changed_build_input'])
            self.assertEqual(evidence['original_sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual(evidence['effective_sha256'], hashlib.sha256(config.read_bytes()).hexdigest())
            cli = root / 'tooling/node_modules/vercel'
            self.assertEqual(local_build_command(cli, config),
                             ['node', str(cli / 'dist/vc.js'), 'build', '--prod', '--yes',
                              '--local-config', str(config.resolve())])

    def test_historical_build_argv_has_no_external_config_and_context_is_unchanged(self):
        cli = Path('/fixture/tooling/node_modules/vercel')
        self.assertEqual(local_build_command(cli),
                         ['node', str(cli / 'dist/vc.js'), 'build', '--prod', '--yes'])
        source = (ROOT / 'scripts/qualify_frontend_build_only.py').read_text()
        tree = ast.parse(source)
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        context = next(node.value for node in ast.walk(main) if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == 'context' for target in node.targets))
        command = next(value for key, value in zip(context.keys, context.values)
                       if isinstance(key, ast.Constant) and key.value == 'build_command')
        self.assertEqual(ast.literal_eval(command), ['node', 'vercel/dist/vc.js', 'build', '--prod', '--yes'])
        self.assertIn('if public_profile:\n            context.update(build_command=build_command', source)

    def test_public_actual_install_command_is_required_and_its_log_is_hash_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log, report = root / 'build.log', root / 'config-evidence.json'
            expected = build_settings(True)['settings']['installCommand']
            log.write_text('Running "install" command: `' + expected + '`...\nBuild completed\n')
            record_public_install_log(log, {'install_command': expected}, report)
            evidence = json.loads(report.read_text())
            self.assertTrue(evidence['exact_install_command_match'])
            self.assertEqual(evidence['observed_install_commands'], [expected])
            self.assertEqual(evidence['install_log_sha256'], hashlib.sha256(log.read_bytes()).hexdigest())
            log.write_text('Running "install" command: `npm install --legacy-peer-deps`...\n')
            with self.assertRaisesRegex(ValueError, 'did not run'):
                record_public_install_log(log, {'install_command': expected}, report)
            evidence = json.loads(report.read_text())
            self.assertFalse(evidence['exact_install_command_match'])
            self.assertEqual(evidence['observed_install_commands'], ['npm install --legacy-peer-deps'])
            self.assertEqual(evidence['install_log_sha256'], hashlib.sha256(log.read_bytes()).hexdigest())

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
