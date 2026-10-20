"""Execute the workflow's real shell gates against disposable Git repositories."""
import os
import io
import datetime as dt
from contextlib import redirect_stdout
from unittest.mock import patch
from scripts import verify_reader_alias_bindings as gate
import copy
import datetime
import json
import hashlib
import shlex
import shutil
from unittest import mock
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/reader-frontend-production.yml'
SOURCE = WORKFLOW.read_text()
REGRESSION = (ROOT / '.github/workflows/regression.yml').read_text()


def step_script(name):
    block = SOURCE.split(f'      - name: {name}\n', 1)[1].split('\n      - name:', 1)[0]
    run = next(line.strip()[5:] for line in block.splitlines() if line.startswith('        run: '))
    if run.startswith('*'):
        start = SOURCE.index('        run: &' + run[1:] + ' |\n') + len('        run: &' + run[1:] + ' |\n')
    else:
        start = SOURCE.index('        run: ' + run + '\n', SOURCE.index(f'      - name: {name}\n')) + len('        run: ' + run + '\n')
    lines = []
    for line in SOURCE[start:].splitlines():
        if line and not line.startswith('          '):
            break
        lines.append(line)
    return textwrap.dedent('\n'.join(lines)).rstrip() + '\n'


def python_gate(name):
    script = step_script(name)
    return script.split("python3 - <<'PYCODE'\n", 1)[1].split('\nPYCODE', 1)[0]


class ManualReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'remote.git'
        self.repo = self.root / 'checkout'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        subprocess.run(['git', 'init', '-b', 'main', str(self.repo)], check=True, capture_output=True)
        self.git('config', 'user.name', 'Release fixture')
        self.git('config', 'user.email', 'release@example.invalid')
        (self.repo / 'fixture.txt').write_text('repository-owned release fixture\n')
        (self.repo / 'backend').mkdir()
        (self.repo / 'backend/server.py').write_text('unchanged backend fixture\n')
        (self.repo / 'frontend').mkdir()
        (self.repo / 'frontend/index.html').write_text('base frontend fixture\n')
        self.git('add', '.')
        self.git('commit', '-m', 'backend fixture')
        self.backend = self.git('rev-parse', 'HEAD').strip()
        self.backend_tree = self.git('rev-parse', 'HEAD:backend').strip()
        (self.repo / 'frontend/index.html').write_text('approved frontend fixture\n')
        self.git('add', 'frontend')
        self.git('commit', '-m', 'frontend artifact fixture')
        self.frontend = self.git('rev-parse', 'HEAD').strip()
        self.frontend_tree = self.git('rev-parse', 'HEAD^{tree}').strip()
        (self.repo / 'controller.txt').write_text('reviewed controller fixture\n')
        self.git('add', 'controller.txt')
        self.git('commit', '-m', 'controller fixture')
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', 'origin', 'main')
        self.output = self.root / 'github-output'
        self.forbidden = self.root / 'forbidden-action.log'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for command in ('vercel', 'railway', 'npm'):
            stub = self.bin / command
            stub.write_text('#!/bin/bash\necho forbidden-action >> "$FORBIDDEN_ACTION_LOG"\nexit 97\n')
            stub.chmod(0o700)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, text=True, check=True, capture_output=True).stdout

    def execute(self, name, **overrides):
        env = {'PATH': str(self.bin) + os.pathsep + os.environ['PATH'], 'HOME': str(self.root),
               'FORBIDDEN_ACTION_LOG': str(self.forbidden),
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_TERMINAL_PROMPT': '0',
               'GITHUB_REPOSITORY': 'ronik18/earnalism-digital-library',
               'GITHUB_REF': 'refs/heads/main', 'GITHUB_SHA': self.sha,
               'CONTROLLER_SHA': self.sha, 'FRONTEND_SHA': self.frontend,
               'FRONTEND_TREE': self.frontend_tree, 'BACKEND_SHA': self.backend,
               'BACKEND_TREE': self.backend_tree, 'TARGET_SHA': self.frontend,
               'CONFIRM_PRODUCTION': 'DEPLOY_PRODUCTION', 'RUNNER_TEMP': str(self.root),
               'FRONTEND_DIR': str(self.root / 'reader-frontend-source'),
               'GITHUB_ENV': str(self.root / 'github-env'),
               'GITHUB_OUTPUT': str(self.output), 'RELEASE_EVENT': 'workflow_dispatch',
               'VERCEL_TOKEN': 'test-only', 'VERCEL_ORG_ID': 'test-only',
               'VERCEL_PROJECT_ID': 'prj_kxPN55TOJ23lDgoXIXrvqHtzy607',
               **overrides}
        # Actions resolves this trusted event SHA before launching the shell.
        script = step_script(name).replace('${{ github.event.before }}', self.sha)
        return subprocess.run(['bash', '-e', '-c', script], cwd=self.repo,
                              env=env, text=True, capture_output=True)

    def test_prepare_source_exports_runner_temp_for_later_steps(self):
        runner_temp = self.root / 'runner temp with spaces'
        runner_temp.mkdir()
        github_env = self.root / 'github-env'
        result = self.execute('Prepare exact frontend artifact source',
                              FRONTEND_DIR='', RUNNER_TEMP=str(runner_temp),
                              GITHUB_ENV=str(github_env))
        self.assertEqual(result.returncode, 0, result.stderr)
        exported = dict(line.split('=', 1) for line in github_env.read_text().splitlines())
        expected = runner_temp / 'reader-frontend-source'
        self.assertEqual(exported, {'FRONTEND_DIR': str(expected)})
        # Model the next step receiving GITHUB_ENV; execute Git against the real worktree.
        later = subprocess.run(['bash', '-eu', '-c', 'git -C "$FRONTEND_DIR" rev-parse HEAD'],
                               env={**os.environ, **exported}, text=True, capture_output=True)
        self.assertEqual(later.returncode, 0, later.stderr)
        self.assertEqual(later.stdout.strip(), self.frontend)
        self.assertFalse(self.forbidden.exists())

    def test_prepare_source_rejects_existing_temp_destination(self):
        destination = self.root / 'reader-frontend-source'
        destination.mkdir()
        marker = destination / 'preserve.txt'
        marker.write_text('existing evidence')
        result = self.execute('Prepare exact frontend artifact source',
                              GITHUB_ENV=str(self.root / 'github-env'))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), 'existing evidence')
        self.assertFalse(self.forbidden.exists())

    def test_exact_main_and_confirmation_admit_clean_checkout(self):
        for name in ('Verify manual release authorization and clean source', 'Recheck exact main and clean deployment source'):
            result = self.execute(name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('SOURCE_CLEAN=YES', result.stdout)
            self.assertIn(self.sha, result.stdout)

    def test_wrong_sha_and_confirmation_fail_before_dependencies(self):
        for overrides in ({'TARGET_SHA': '0' * 40}, {'TARGET_SHA': 'main'},
                          {'TARGET_SHA': ''}, {'CONFIRM_PRODUCTION': ''},
                          {'CONFIRM_PRODUCTION': 'yes'}, {'GITHUB_REF': 'refs/heads/other'}):
            with self.subTest(overrides=overrides):
                self.assertNotEqual(self.execute('Verify manual release authorization and clean source', **overrides).returncode, 0)
        self.assertLess(SOURCE.index('Verify manual release authorization'), SOURCE.index('Install existing verification clients'))

    def test_stale_main_rejected_by_both_gates(self):
        self.git('commit', '--allow-empty', '-m', 'main advanced')
        self.git('push', 'origin', 'main')
        self.git('checkout', '--detach', self.sha)
        for name in ('Verify manual release authorization and clean source', 'Recheck exact main and clean deployment source'):
            self.assertNotEqual(self.execute(name).returncode, 0)

    def test_tracked_and_untracked_changes_rejected(self):
        for path in ('fixture.txt', 'untracked.txt'):
            with self.subTest(path=path):
                original = self.repo / path
                original.write_text('unexpected change\n')
                for name in ('Verify manual release authorization and clean source', 'Recheck exact main and clean deployment source'):
                    self.assertNotEqual(self.execute(name).returncode, 0)
                if path == 'fixture.txt':
                    original.write_text('repository-owned release fixture\n')

    def test_dispatch_enables_same_deploy_job_and_requires_credentials(self):
        result = self.execute('Check Vercel deploy scope and secrets')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text(), 'enabled=true\n')
        self.assertNotEqual(self.execute('Check Vercel deploy scope and secrets', VERCEL_TOKEN='').returncode, 0)

    def test_push_cannot_enable_manual_deployment(self):
        result = self.execute('Check Vercel deploy scope and secrets', RELEASE_EVENT='push')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_push_frontend_changes_cannot_enable_manual_deployment(self):
        (self.repo / 'frontend' / 'fixture.txt').write_text('frontend fixture\n')
        self.git('add', 'frontend')
        self.git('commit', '-m', 'frontend change')
        result = self.execute('Check Vercel deploy scope and secrets', RELEASE_EVENT='push',
                              GITHUB_SHA=self.git('rev-parse', 'HEAD').strip())
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_frontend_only_environment_hold_follows_real_backend_verification(self):
        regression = SOURCE.split('  deploy_frontend:', 1)[0]
        deploy = SOURCE.split('  deploy_frontend:', 1)[1].split('  frontend_production_canary:', 1)[0]
        canary = SOURCE.split('  frontend_production_canary:', 1)[1]
        self.assertIn('    environment: reader-frontend-production\n', deploy)
        self.assertEqual(SOURCE.count('environment: reader-frontend-production'), 1)
        self.assertNotIn('    environment:', regression)
        self.assertNotIn('    environment:', canary)
        self.assertIn("github.event_name == 'workflow_dispatch'", deploy)
        self.assertIn("github.ref == 'refs/heads/main'", deploy)
        self.assertIn("needs.backend_verify.result == 'success'", deploy)
        self.assertIn('needs: backend_verify', deploy)
        self.assertIn('python scripts/verify_backend_release.py', regression)
        self.assertIn('python scripts/verify_reader_startup_readonly.py', regression)
        self.assertLess(deploy.index('environment: reader-frontend-production'), deploy.index('    steps:'))
        # Static binding is not a claim that the live hold has executed.

    def test_existing_build_and_canary_dependencies_preserved(self):
        deploy = SOURCE.split('  deploy_frontend:', 1)[1].split('  frontend_production_canary:', 1)[0]
        canary = SOURCE.split('  frontend_production_canary:', 1)[1]
        self.assertIn('needs: backend_verify', deploy)
        self.assertIn("needs.backend_verify.result == 'success'", deploy)
        self.assertIn("needs.deploy_frontend.outputs.deployed == 'true'", canary)
        self.assertIn('      - backend_verify\n      - deploy_frontend', canary)
        self.assertIn('python3 -m scripts.frontend_public_build', deploy)
        public_builder = (ROOT / 'scripts/frontend_public_build.py').read_text()
        self.assertIn("'build','--prod','--yes'", public_builder)
        self.assertIn('cwd=root,env=env', public_builder)
        self.assertIn('args=(deploy --prebuilt --prod', deploy)
        self.assertIn('python3 scripts/post_deploy_static_seo_canary.py', canary)
        self.assertIn('bash scripts/run_pr_regression.sh', REGRESSION)
        self.assertIn('scripts/verify_vercel_packaging.py\" --root "$FRONTEND_DIR" --manifest', deploy)
        self.assertNotIn("github.event_name == 'push'", SOURCE)
        self.assertEqual(len(re.findall(r'      target_sha:|      confirm_production:', SOURCE)), 2)

    def test_main_push_has_no_deployment_or_approval_job(self):
        self.assertNotIn('environment:', REGRESSION)
        self.assertNotIn('deploy_frontend:', REGRESSION)
        self.assertNotIn('frontend_production_canary:', REGRESSION)
        self.assertNotIn('vercel deploy', REGRESSION)
        self.assertIn('  push:', REGRESSION)
        self.assertIn('  pull_request:', REGRESSION)
        trigger = SOURCE.split('permissions:', 1)[0]
        self.assertIn('  workflow_dispatch:', trigger)
        for event in ('push:', 'pull_request:', 'workflow_run:', 'workflow_call:', 'schedule:'):
            self.assertNotIn(event, trigger)
        self.assertIn('group: reader-manual-frontend-production', SOURCE)
        self.assertIn('cancel-in-progress: false', SOURCE)
        self.assertNotIn('go-live-regression-', SOURCE)

    def test_failed_backend_dependency_cannot_be_approved_away(self):
        deploy = SOURCE.split('  deploy_frontend:', 1)[1].split('  frontend_production_canary:', 1)[0]
        self.assertIn("needs.backend_verify.result == 'success'", deploy)
        self.assertNotIn('always()', deploy)
        self.assertNotIn('continue-on-error', SOURCE)
        self.assertIn('defaults:\n  run:\n    shell: bash', SOURCE)
        for name in ('Verify actual HTTP and provider serving identity', 'Verify existing read-only startup prerequisites'):
            self.assertIn('set -euo pipefail', step_script(name))

    def test_frontend_source_and_backend_recheck_preserved(self):
        self.assertIn('Reverify serving backend after owner approval', SOURCE)
        self.assertIn("deployment['meta']['githubCommitSha'] == os.environ['FRONTEND_SHA']", SOURCE)
        self.assertIn("deployment['projectId'] == os.environ['VERCEL_PROJECT_ID']", SOURCE)

    def test_workflow_shell_blocks_have_valid_bash_syntax(self):
        for name in ('Verify manual release authorization and clean source', 'Recheck exact main and clean deployment source',
                     'Check Vercel deploy scope and secrets', 'Build frontend for Vercel'):
            self.assertEqual(subprocess.run(['bash', '-n'], input=step_script(name), text=True, capture_output=True).returncode, 0)

    def test_actual_workflow_pins_are_not_dispatch_selectable(self):
        self.assertIn('  FRONTEND_SHA: b2abea1c85cf5b38f248e4af4f3523e0ce1e7252', SOURCE)
        self.assertIn('  FRONTEND_TREE: 1ad8fc5f5cf643b9407b43cd413e5f6ce8a2ec32', SOURCE)
        self.assertIn('  BACKEND_SHA: fda9d5b4a4618447ef75026edf17bba7f28f0c83', SOURCE)
        self.assertIn('  BACKEND_TREE: 94257b759e47705fb16b10a2fbe1aabd28d3347c', SOURCE)
        self.assertEqual(SOURCE.count('--expected-sha "$BACKEND_SHA"'), 3)
        self.assertNotIn('--expected-sha "$TARGET_SHA"', SOURCE)
        canary = SOURCE.split('  frontend_production_canary:', 1)[1]
        self.assertIn('ref: ${{ env.CONTROLLER_SHA }}', canary)
        self.assertNotIn('ref: ${{ env.FRONTEND_SHA }}', canary)
        self.assertIn('contents: read\n  actions: read', SOURCE)
        self.assertNotIn('contents: write', SOURCE)

    def test_canary_checkout_executes_controller_instead_of_frontend_revision(self):
        job = parse_workflow(SOURCE)['jobs']['frontend_production_canary']
        checkout = next(step for step in job['steps'] if step.get('uses', '').startswith('actions/checkout@'))
        revisions = {'${{ env.CONTROLLER_SHA }}': self.sha,
                     '${{ env.FRONTEND_SHA }}': self.frontend}
        self.git('checkout', '--detach', revisions[checkout['with']['ref']])
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(), self.sha)
        self.assertTrue((self.repo / 'controller.txt').is_file())
        self.assertEqual(self.git('rev-parse', 'HEAD:frontend'), self.git('rev-parse', self.frontend + ':frontend'))
        identity = next(step['run'] for step in job['steps'] if step.get('name') == 'Verify canary controller identity')
        for expected, status in [(self.sha, 0), (self.frontend, 1)]:
            result = subprocess.run(['bash', '-c', identity], cwd=self.repo,
                                    env={**os.environ, 'CONTROLLER_SHA': expected}, capture_output=True)
            self.assertEqual(result.returncode, status)

    def test_distinct_controller_frontend_and_backend_admit_only_exact_pair(self):
        self.assertEqual(len({self.sha, self.frontend, self.backend}), 3)
        self.assertEqual(self.execute('Verify manual release authorization and clean source').returncode, 0)
        for override in ({'TARGET_SHA': self.sha}, {'TARGET_SHA': self.backend},
                         {'BACKEND_SHA': self.frontend}, {'BACKEND_TREE': '0' * 40},
                         {'FRONTEND_TREE': '0' * 40}, {'CONTROLLER_SHA': self.frontend},
                         {'BACKEND_SHA': 'main'}, {'RELEASE_EVENT': 'push'},
                         {'GITHUB_REPOSITORY': 'other/fork'}):
            with self.subTest(override=override):
                self.assertNotEqual(self.execute('Verify manual release authorization and clean source', **override).returncode, 0)

    def test_controller_cannot_introduce_backend_or_frontend_changes(self):
        for path in ('backend/server.py', 'frontend/index.html'):
            with self.subTest(path=path):
                (self.repo / path).write_text('unapproved controller mutation\n')
                self.git('add', path)
                self.git('commit', '-m', 'unapproved change fixture')
                changed = self.git('rev-parse', 'HEAD').strip()
                self.git('push', 'origin', 'main')
                self.assertNotEqual(self.execute('Verify manual release authorization and clean source',
                                                GITHUB_SHA=changed, CONTROLLER_SHA=changed).returncode, 0)

    def test_artifact_preparation_is_exact_and_will_not_reuse_existing_directory(self):
        result = self.execute('Prepare exact frontend artifact source')
        self.assertEqual(result.returncode, 0, result.stderr)
        artifact = self.root / 'reader-frontend-source'
        actual = subprocess.check_output(['git', '-C', str(artifact), 'rev-parse', 'HEAD'], text=True).strip()
        self.assertEqual(actual, self.frontend)
        self.assertNotEqual(self.execute('Prepare exact frontend artifact source').returncode, 0)
        fresh_temp = self.root / 'bad-artifact-runner-temp'
        fresh_temp.mkdir()
        self.assertNotEqual(self.execute('Prepare exact frontend artifact source',
                                        RUNNER_TEMP=str(fresh_temp), FRONTEND_SHA='0' * 40).returncode, 0)
        self.assertFalse((fresh_temp / 'reader-frontend-source').exists())

    def test_build_refuses_dirty_or_wrong_artifact_before_vercel(self):
        self.assertEqual(self.execute('Prepare exact frontend artifact source').returncode, 0)
        artifact = self.root / 'reader-frontend-source'
        (artifact / 'frontend/index.html').write_text('tampered artifact fixture\n')
        self.assertNotEqual(self.execute('Build frontend for Vercel').returncode, 0)
        self.assertNotEqual(self.execute('Build frontend for Vercel', FRONTEND_SHA=self.sha).returncode, 0)
        self.assertFalse(self.forbidden.exists(), 'Invalid artifacts must stop before any provider command')
        self.assertIn('--source-root "$FRONTEND_DIR"', step_script('Build frontend for Vercel'))
        self.assertIn('cd "$FRONTEND_DIR"', step_script('Deploy frontend to Vercel production'))

    def artifact_guard(self, **overrides):
        # Execute the production step's complete early guard, stopping before
        # its first backend/provider command. No provider or environment reads.
        code = step_script('Deploy frontend to Vercel production').split(
            'python3 scripts/verify_backend_release.py', 1)[0]
        return subprocess.run(['bash', '-eu', '-c', code], cwd=self.repo,
                              env={**os.environ, 'FRONTEND_DIR': str(self.root / 'reader-frontend-source'),
                                   'FRONTEND_SHA': self.frontend, **overrides},
                              text=True, capture_output=True)

    def test_artifact_guard_accepts_only_the_clean_exact_artifact(self):
        self.assertEqual(self.execute('Prepare exact frontend artifact source').returncode, 0)
        result = self.artifact_guard()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertFalse(self.forbidden.exists())

    def test_artifact_guard_reports_wrong_head_without_provider_execution(self):
        self.assertEqual(self.execute('Prepare exact frontend artifact source').returncode, 0)
        result = self.artifact_guard(FRONTEND_SHA=self.sha)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RELEASE_ARTIFACT_HEAD_MISMATCH', result.stderr)
        self.assertIn('expected=' + self.sha, result.stderr)
        self.assertIn('actual=' + self.frontend, result.stderr)
        self.assertFalse(self.forbidden.exists())

    def test_artifact_guard_reports_tracked_and_untracked_paths_without_contents(self):
        self.assertEqual(self.execute('Prepare exact frontend artifact source').returncode, 0)
        artifact = self.root / 'reader-frontend-source'
        marker = 'PRIVATE_FILE_CONTENT_MUST_NOT_APPEAR_IN_DIAGNOSTICS'
        (artifact / 'frontend/index.html').write_text(marker)
        (artifact / 'unexpected file.txt').write_text(marker)
        result = self.artifact_guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RELEASE_ARTIFACT_DIRTY head=' + self.frontend, result.stderr)
        self.assertIn('frontend/index.html', result.stderr)
        self.assertIn('unexpected file.txt', result.stderr)
        self.assertNotIn(marker, result.stdout + result.stderr)
        actual = subprocess.check_output(['git', '-C', str(artifact), 'rev-parse', 'HEAD'], text=True).strip()
        self.assertEqual(actual, self.frontend)
        self.assertFalse(self.forbidden.exists())

    def approval(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        # Test-only attestations: never written into real environment configuration.
        return {'schema': 'reader-frontend-release-approval.v1', 'controller_sha': self.sha,
                'frontend_sha': self.frontend, 'frontend_tree': self.frontend_tree, 'backend_sha': self.backend,
                'project_id': 'prj_kxPN55TOJ23lDgoXIXrvqHtzy607', 'root_directory': 'frontend',
                'config_path': 'frontend/vercel.json',
                'config_sha256': '3fe071e9df7825404e57800dfaaebba611c190f62548836f5242ae336fc76a3b',
                'git_deployment_enabled': False, 'rollback_deployment': 'dpl_6hzaPakeBuma2y4JB6CGyngzCKJf',
                'rollback_method': 'vercel-instant-rollback', 'rollback_eligible': True,
                'frontend_backend_config_compatible': True, 'no_backend_restart': True, 'approved': True,
                'rollback_artifact_sha256': 'a' * 64, 'rollback_config_sha256': 'b' * 64,
                'operator_evidence_sha256': 'c' * 64, 'rollback_operator': 'synthetic-test-only-operator',
                'approved_at': (now - datetime.timedelta(minutes=1)).isoformat(),
                'expires_at': (now + datetime.timedelta(minutes=10)).isoformat()}

    def test_missing_or_invalid_operator_approval_stops_before_artifact_and_deployment(self):
        gate = 'Verify operator config and rollback approval'
        self.assertNotEqual(self.execute(gate).returncode, 0)
        valid = self.approval()
        self.assertEqual(self.execute(gate, RELEASE_APPROVAL_JSON=json.dumps(valid)).returncode, 0)
        for key, value in [('approved', False), ('controller_sha', '0' * 40), ('frontend_sha', self.sha),
                           ('backend_sha', self.frontend), ('frontend_tree', '0' * 40),
                           ('root_directory', ''), ('git_deployment_enabled', True),
                           ('rollback_eligible', False), ('rollback_eligible', 'true'),
                           ('rollback_operator', ''), ('rollback_artifact_sha256', '0' * 64),
                           ('rollback_config_sha256', ''), ('operator_evidence_sha256', 'bad'),
                           ('no_backend_restart', False), ('frontend_backend_config_compatible', False),
                           ('expires_at', '2000-01-01T00:00:00+00:00')]:
            with self.subTest(key=key):
                altered = {**valid, key: value}
                self.assertNotEqual(self.execute(gate, RELEASE_APPROVAL_JSON=json.dumps(altered)).returncode, 0)
        self.assertLess(SOURCE.index('Verify operator config and rollback approval'), SOURCE.index('Prepare exact frontend artifact source'))
        self.assertIn("vars.READER_FRONTEND_RELEASE_APPROVAL_JSON || ''", SOURCE)
        self.assertEqual(step_script(gate), step_script('Recheck operator config and rollback approval before deployment'))

    def run_ci(self, mutate=None, empty=False, fail_network=False, controller_fail=False):
        code = python_gate('Verify exact frontend review CI')
        records = []
        def response(request, timeout):
            if fail_network:
                raise OSError('synthetic unavailable CI fixture')
            workflow = request.full_url.split('/workflows/')[1].split('/runs')[0]
            required_sha = request.full_url.split('head_sha=')[1].split('&')[0]
            record = {'head_sha': required_sha, 'path': '.github/workflows/' + workflow,
                      'event': 'pull_request', 'head_repository': {'full_name': 'ronik18/earnalism-digital-library'},
                      'run_number': 12, 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success', 'id': 123}
            if controller_fail and required_sha == self.sha:
                record['conclusion'] = 'failure'
            if mutate:
                record.update(mutate)
            records.append(request.full_url)
            import io
            return io.StringIO(json.dumps({'workflow_runs': [] if empty else [record]}))
        with mock.patch.dict(os.environ, {'GITHUB_REPOSITORY': 'ronik18/earnalism-digital-library',
                                         'FRONTEND_SHA': self.frontend, 'CONTROLLER_SHA': self.sha, 'ACTIONS_TOKEN': 'synthetic-ci-only-token'}), \
             mock.patch('urllib.request.urlopen', side_effect=response):
            exec(compile(code, '<actual-workflow-ci-gate>', 'exec'), {})
        return records

    def test_exact_head_ci_success_and_missing_stale_failed_or_untrusted_runs(self):
        self.assertEqual(len(self.run_ci()), 7)
        for altered in ({'head_sha': self.sha}, {'conclusion': 'failure'}, {'status': 'in_progress'},
                        {'event': 'workflow_dispatch'}, {'path': '.github/workflows/unrelated.yml'},
                        {'head_repository': {'full_name': 'other/fork'}}):
            with self.subTest(altered=altered):
                with self.assertRaises(SystemExit):
                    self.run_ci(mutate=altered)
        with self.assertRaises(SystemExit):
            self.run_ci(empty=True)
        with self.assertRaises(OSError):
            self.run_ci(fail_network=True)
        with self.assertRaises(SystemExit):
            self.run_ci(controller_fail=True)
        self.assertEqual(step_script('Verify exact frontend review CI'),
                         step_script('Recheck exact frontend review CI before deployment'))

    def test_wrong_destination_and_incomplete_credentials_fail_closed(self):
        self.assertNotEqual(self.execute('Check Vercel deploy scope and secrets', VERCEL_PROJECT_ID='other').returncode, 0)
        for key in ('VERCEL_TOKEN', 'VERCEL_ORG_ID', 'VERCEL_PROJECT_ID'):
            with self.subTest(key=key):
                self.assertNotEqual(self.execute('Check Vercel deploy scope and secrets', **{key: ''}).returncode, 0)

    def test_all_run_steps_have_valid_shell_and_inline_python(self):
        for name in re.findall(r'^      - name: (.+)$', SOURCE, re.M):
            block = SOURCE.split(f'      - name: {name}\n', 1)[1].split('\n      - name:', 1)[0]
            if '        run: ' not in block:
                continue
            script = step_script(name)
            with self.subTest(name=name):
                syntax = subprocess.run(['bash', '-n'], input=script, text=True, capture_output=True)
                self.assertEqual(syntax.returncode, 0, syntax.stderr)
                for code in re.findall(r"python3 - <<'PYCODE'\n(.*?)\nPYCODE", script, re.S):
                    compile(code, '<actual-inline-python>', 'exec')


    def test_deployed_artifact_identity_must_match_all_three_bindings(self):
        script = step_script('Deploy frontend to Vercel production')
        code = script.rsplit("python3 - <<'PY'\n", 1)[1].split('\nPY', 1)[0]
        env = {'RUNNER_TEMP': str(self.root), 'VERCEL_PROJECT_ID': 'prj_kxPN55TOJ23lDgoXIXrvqHtzy607',
               'FRONTEND_SHA': self.frontend, 'CONTROLLER_SHA': self.sha, 'BACKEND_SHA': self.backend}
        deployment = {'id': 'synthetic-deployment-only', 'projectId': env['VERCEL_PROJECT_ID'],
                      'target': 'production', 'readyState': 'READY',
                      'meta': {'githubCommitSha': self.frontend, 'readerControllerSha': self.sha,
                               'readerBackendSha': self.backend}}
        def execute(value):
            (self.root / 'frontend-deployment.json').write_text(json.dumps(value))
            with mock.patch.dict(os.environ, env):
                exec(compile(code, '<actual-deployed-artifact-gate>', 'exec'), {})
        execute(deployment)
        for key, value in [('projectId', 'wrong-project'), ('target', 'preview'), ('readyState', 'ERROR')]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                execute({**deployment, key: value})
        for key in ('githubCommitSha', 'readerControllerSha', 'readerBackendSha'):
            altered = copy.deepcopy(deployment)
            altered['meta'][key] = '0' * 40
            with self.subTest(key=key), self.assertRaises(AssertionError):
                execute(altered)
        for flag in ('githubCommitSha=$FRONTEND_SHA', 'readerControllerSha=$CONTROLLER_SHA', 'readerBackendSha=$BACKEND_SHA'):
            self.assertIn(flag, script)


class ArtifactPackagingRootTests(unittest.TestCase):
    """Run both real workflow calls with separately located controller and build."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='earnalism packaging roots ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.controller = self.root / 'controller checkout'
        self.artifact = self.root / 'frontend artifact checkout'
        config = {'functions': {'api/journal-page.js': {
            'includeFiles': 'build/journal-app-shell.html'}}}
        for root in (self.controller, self.artifact):
            (root / 'frontend').mkdir(parents=True)
            (root / 'frontend/vercel.json').write_text(json.dumps(config))
        (self.controller / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'scripts/verify_vercel_packaging.py',
                        self.controller / 'scripts/verify_vercel_packaging.py')
        self.asset = self.artifact / 'frontend/build/journal-app-shell.html'
        self.asset.parent.mkdir()
        self.asset.write_text('<html>actual built artifact fixture</html>')
        self.output = self.artifact / '.vercel/output'
        self.function = self.output / 'functions/journal.func'
        self.function.mkdir(parents=True)
        (self.output / 'config.json').write_text('{}')
        self.trace = self.function / '.vc-config.json'
        self.trace.write_text('{}')
        self.link = self.function / 'shell'
        self.link.symlink_to(self.asset)
        self.source_manifest = self.root / 'source manifest.json'
        self.prebuilt_manifest = self.root / 'prebuilt manifest.json'
        self.source_report = self.root / 'source report.json'
        self.prebuilt_report = self.root / 'prebuilt report.json'
        manifest = {'files': [{'path': 'frontend/build/journal-app-shell.html'}]}
        for path in (self.source_manifest, self.prebuilt_manifest):
            path.write_text(json.dumps(manifest))
        script = step_script('Verify source and prebuilt function packaging')
        self.calls = [line for line in script.splitlines()
                      if line.startswith('python3 "$GITHUB_WORKSPACE/scripts/verify_vercel_packaging.py"')]

    def execute(self, index, *, explicit_root=True, root=None):
        command = self.calls[index]
        if not explicit_root:
            command = command.replace(' --root "$FRONTEND_DIR"', '')
        paths = {'/tmp/vercel-source-manifest.json': self.source_manifest,
                 '/tmp/vercel-prebuilt-manifest.json': self.prebuilt_manifest,
                 '/tmp/vercel-source-packaging.json': self.source_report,
                 '/tmp/vercel-prebuilt-packaging.json': self.prebuilt_report}
        for original, path in paths.items():
            command = command.replace(original, shlex.quote(str(path)))
        return subprocess.run(['bash', '-eu', '-c', command], cwd=self.artifact,
                              env={**os.environ, 'GITHUB_WORKSPACE': str(self.controller),
                                   'FRONTEND_DIR': str(root or self.artifact)},
                              text=True, capture_output=True)

    def test_both_workflow_calls_bind_exact_root_and_keep_comparison(self):
        self.assertEqual(len(self.calls), 2)
        for line in self.calls:
            args = shlex.split(line)
            self.assertEqual(args[:4], ['python3', '$GITHUB_WORKSPACE/scripts/verify_vercel_packaging.py',
                                       '--root', '$FRONTEND_DIR'])
            self.assertEqual(args.count('--root'), 1)
        self.assertIn('--prebuilt --compare /tmp/vercel-source-packaging.json', self.calls[1])
        self.assertNotIn('--prebuilt', self.calls[0])

    def test_controller_default_fails_but_real_workflow_calls_accept_space_paths(self):
        result = self.execute(0, explicit_root=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing includeFiles asset build/journal-app-shell.html', result.stderr)
        for index in (0, 1):
            result = self.execute(index)
            self.assertEqual(result.returncode, 0, result.stderr)
        source = json.loads(self.source_report.read_text())['required_assets']
        prebuilt = json.loads(self.prebuilt_report.read_text())['required_assets']
        self.assertEqual(source, prebuilt)
        self.assertEqual(source['frontend/build/journal-app-shell.html'],
                         hashlib.sha256(self.asset.read_bytes()).hexdigest())

    def test_stale_controller_asset_cannot_mask_wrong_prebuilt_root_or_tampering(self):
        stale = self.controller / 'frontend/build/journal-app-shell.html'
        stale.parent.mkdir()
        stale.write_text('<html>plausible stale controller asset</html>')
        stale_output = self.controller / '.vercel/output'
        (stale_output / 'functions/stale.func').mkdir(parents=True)
        (stale_output / 'config.json').write_text('{}')
        self.assertEqual(self.execute(0).returncode, 0)
        wrong = self.execute(1, root=self.controller)
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn('source/prebuilt critical asset differs', wrong.stderr)
        self.asset.write_text('<html>tampered actual artifact</html>')
        changed = self.execute(1)
        self.assertNotEqual(changed.returncode, 0)
        self.assertIn('source/prebuilt critical asset differs', changed.stderr)

    def test_missing_asset_or_unselected_build_file_still_fails(self):
        self.asset.unlink()
        self.assertNotEqual(self.execute(0).returncode, 0)
        self.asset.write_text('restored fixture')
        self.source_manifest.write_text(json.dumps({'files': [
            {'path': 'frontend/build/journal-app-shell.html'},
            {'path': 'frontend/build/index.html'}]}))
        result = self.execute(0)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unneeded generated build files included', result.stderr)

    def test_missing_external_or_parent_escape_mapping_still_fails(self):
        self.assertEqual(self.execute(0).returncode, 0)
        for name in ('frontend/missing.txt', '../outside.txt', str(self.root / 'outside.txt')):
            with self.subTest(name=name):
                (self.root / 'outside.txt').write_text('external fixture')
                self.trace.write_text(json.dumps({'filePathMap': {name: 'mapped.txt'}}))
                result = self.execute(1)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('missing or external mapped function asset', result.stderr)

    def test_external_symlink_and_missing_prebuilt_output_still_fail(self):
        self.assertEqual(self.execute(0).returncode, 0)
        external = self.root / 'outside.txt'
        external.write_text('outside fixture')
        self.link.unlink()
        self.link.symlink_to(external)
        result = self.execute(1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('function trace outside deployment root', result.stderr)
        (self.output / 'config.json').unlink()
        result = self.execute(1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('prebuilt output/config.json missing', result.stderr)


# Context availability is a GitHub expression rule, separate from shell syntax.
# https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability
# js-yaml is already pinned in the root package-lock.json and installed by root npm ci.
def parse_workflow(source):
    result = subprocess.run(
        ['node', '-e', "const fs=require('fs');const yaml=require('js-yaml');"
         "process.stdout.write(JSON.stringify(yaml.safeLoad(fs.readFileSync(0,'utf8'))));"],
        input=source, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError('Existing locked YAML parser failed: ' + result.stderr)
    return json.loads(result.stdout)


ENV_CONTEXTS = {
    'env': {'github', 'secrets', 'inputs', 'vars'},
    'jobs.<job_id>.env': {'github', 'needs', 'strategy', 'matrix', 'vars', 'secrets', 'inputs'},
    'jobs.<job_id>.steps.env': {'github', 'needs', 'strategy', 'matrix', 'job', 'runner',
                                 'env', 'vars', 'secrets', 'steps', 'inputs'},
}


def expression_context_roots(value):
    if not isinstance(value, str):
        return set()
    roots = set()
    for expression in re.findall(r'\$\{\{(.*?)\}\}', value, re.S):
        # Tokenize single-quoted expression literals (including escaped quotes),
        # identifiers and punctuation. Properties/functions are not root contexts.
        tokens = re.findall(r"'(?:[^']|'')*'|[A-Za-z_][A-Za-z0-9_-]*|[^\s]", expression)
        for index, token in enumerate(tokens):
            previous = tokens[index - 1] if index else None
            following = tokens[index + 1] if index + 1 < len(tokens) else None
            if (re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', token)
                    and previous != '.' and following != '('
                    and token.lower() not in {'true', 'false', 'null'}):
                roots.add(token.lower())
    return roots


def environment_context_errors(workflow):
    errors = []
    def inspect(values, location, availability):
        for key, value in (values or {}).items():
            invalid = expression_context_roots(value) - ENV_CONTEXTS[availability]
            if invalid:
                errors.append((location + '.' + key, tuple(sorted(invalid))))
    inspect(workflow.get('env'), 'env', 'env')
    for job_id, job in workflow.get('jobs', {}).items():
        inspect(job.get('env'), 'jobs.' + job_id + '.env', 'jobs.<job_id>.env')
        for index, step in enumerate(job.get('steps', [])):
            inspect(step.get('env'), f'jobs.{job_id}.steps.{index}.env',
                    'jobs.<job_id>.steps.env')
    return errors


class WorkflowContextAvailabilityTests(unittest.TestCase):
    def test_actual_parsed_workflow_environment_contexts_are_available(self):
        self.assertEqual(environment_context_errors(parse_workflow(SOURCE)), [])

    def test_rejects_original_job_runner_context_and_other_forbidden_roots(self):
        workflow = parse_workflow(SOURCE)
        for expression, root in [
                ('${{ runner.temp }}/reader-frontend-source', 'runner'),
                ("${{ runner['temp'] }}", 'runner'),
                ("${{ format('{0}', runner.temp) }}", 'runner'),
                ('${{ toJSON(runner) }}', 'runner'),
                ('${{ env.RUNNER_TEMP }}', 'env'),
                ('${{ steps.prepare.outputs.directory }}', 'steps')]:
            with self.subTest(expression=expression):
                altered = copy.deepcopy(workflow)
                altered['jobs']['deploy_frontend']['env']['DIRECTORY'] = expression
                self.assertEqual(environment_context_errors(altered),
                                 [('jobs.deploy_frontend.env.DIRECTORY', (root,))])

    def test_same_runner_context_is_valid_at_step_scope(self):
        workflow = parse_workflow(SOURCE)
        workflow['jobs']['deploy_frontend']['steps'][0]['env'] = {
            'DIRECTORY': '${{ runner.temp }}', 'DATA': '${{ toJSON(job) }}',
            'PREVIOUS': '${{ steps.prepare.outputs.directory }}'}
        self.assertEqual(environment_context_errors(workflow), [])

    def test_all_documented_job_environment_contexts_are_accepted(self):
        workflow = parse_workflow(SOURCE)
        workflow['jobs']['deploy_frontend']['env'] = {
            root: '${{ toJSON(' + root + ') }}' for root in ENV_CONTEXTS['jobs.<job_id>.env']}
        self.assertEqual(environment_context_errors(workflow), [])

    def test_expression_string_literals_do_not_become_contexts(self):
        workflow = parse_workflow(SOURCE)
        workflow['jobs']['deploy_frontend']['env']['LABEL'] = (
            "${{ format('runner.temp is not a context here; it''s literal', github.ref) }}")
        self.assertEqual(environment_context_errors(workflow), [])


class AliasReleaseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.env = {"VERCEL_PROJECT_ID": gate.PROJECT, "VERCEL_ORG_ID": gate.TEAM,
                    "FRONTEND_SHA": "a" * 40, "CONTROLLER_SHA": "b" * 40,
                    "BACKEND_SHA": "c" * 40}
        self.now = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)
        self.metadata = {"id": "dpl_test", "projectId": gate.PROJECT,
                         "target": "production", "readyState": "READY",
                         "aliasAssigned": True, "aliasError": None,
                         "ready": int(self.now.timestamp() * 1000),
                         "meta": {"githubCommitSha": "a" * 40,
                                  "readerControllerSha": "b" * 40,
                                  "readerBackendSha": "c" * 40}}

    def test_parsed_workflow_guards_canary_admission_and_binds_adapter(self):
        result = subprocess.run(["node", "-e", "const fs=require('fs');const y=require('js-yaml');"
                                 "process.stdout.write(JSON.stringify(y.load(fs.readFileSync(0,'utf8'))));"],
                                input=(ROOT / '.github/workflows/reader-frontend-production.yml').read_text(),
                                text=True, capture_output=True, check=True)
        workflow = json.loads(result.stdout)
        deploy = workflow['jobs']['deploy_frontend']
        names = [s.get('name') for s in deploy['steps']]
        self.assertLess(names.index('Deploy frontend to Vercel production'),
                        names.index('Verify all four exact production alias bindings'))
        binding = next(s for s in deploy['steps'] if s.get('id') == 'alias-binding')
        self.assertIn('verify_reader_alias_bindings.py', binding['run'])
        self.assertNotIn('continue-on-error', binding)
        self.assertEqual(deploy['outputs']['deployment_id'], '${{ steps.alias-binding.outputs.deployment_id }}')
        canary = workflow['jobs']['frontend_production_canary']
        self.assertIn("needs.deploy_frontend.result == 'success'", canary['if'])
        adapter = next(s for s in canary['steps'] if s.get('name') == 'Run three-public one-protected alias contract')
        self.assertIn('--contract three-public-one-protected-v1', adapter['run'])
        self.assertEqual(adapter['env']['VERIFIED_DEPLOYMENT_ID'], '${{ needs.deploy_frontend.outputs.deployment_id }}')
        self.assertEqual(adapter['env']['VERIFIED_READY_AT'], '${{ needs.deploy_frontend.outputs.ready_at }}')
        self.assertEqual(sum('scripts/reader_alias_canaries.py' in s.get('run', '') for s in canary['steps']), 1)
        self.assertEqual(workflow['env']['FRONTEND_SHA'], 'b2abea1c85cf5b38f248e4af4f3523e0ce1e7252')
        self.assertEqual(workflow['env']['BACKEND_SHA'], 'fda9d5b4a4618447ef75026edf17bba7f28f0c83')

    def test_collector_only_reads_four_pinned_aliases_and_emits_binding(self):
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            host = args[2].split('/aliases/', 1)[1].split('?', 1)[0]
            return subprocess.CompletedProcess(args, 0, json.dumps({"alias": host,
                "projectId": gate.PROJECT, "deploymentId": "dpl_test"}), '')
        report = gate.collect(self.metadata, runner=runner, environ=self.env, now=self.now)
        self.assertEqual(report['deployment_id'], 'dpl_test')
        self.assertEqual(report['ready_at'], self.now.isoformat())
        self.assertEqual(len(calls), 4)
        for args, kwargs in calls:
            self.assertEqual(args[0:2], ['vercel', 'api'])
            self.assertEqual(args[3:], ['--method', 'GET', '--raw'])
            self.assertTrue(args[2].endswith('?teamId=' + gate.TEAM))
            self.assertEqual(kwargs['timeout'], 15)
            self.assertTrue(kwargs['check'])

    def test_source_mismatch_rejects_before_provider_reads(self):
        self.metadata['meta']['readerControllerSha'] = 'd' * 40
        with patch.object(gate.subprocess, 'run') as runner:
            with self.assertRaises(ValueError):
                gate.collect(self.metadata, environ=self.env, now=self.now)
            runner.assert_not_called()

    def test_cli_error_fails_without_github_outputs_or_private_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); metadata = root / 'metadata.json'; output = root / 'binding.json'
            github = root / 'github-output'; github.write_text('')
            metadata.write_text(json.dumps(self.metadata))
            args = ['gate', '--metadata', str(metadata), '--output', str(output), '--github-output', str(github)]
            text = io.StringIO()
            with patch('sys.argv', args), patch.object(gate, 'collect', side_effect=ValueError('PRIVATE')):
                with redirect_stdout(text):
                    self.assertEqual(gate.main(), 1)
            self.assertEqual(github.read_text(), '')
            self.assertEqual(json.loads(output.read_text())['status'], 'FAIL')
            self.assertNotIn('PRIVATE', text.getvalue() + output.read_text())


if __name__ == '__main__':
    unittest.main()
