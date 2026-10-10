"""Execute the workflow's real shell gates against disposable Git repositories."""
import os
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
    return textwrap.dedent(block.split('        run: |\n', 1)[1]).rstrip() + '\n'


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
        self.git('add', 'fixture.txt')
        self.git('commit', '-m', 'fixture')
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', 'origin', 'main')
        self.output = self.root / 'github-output'

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, text=True, check=True, capture_output=True).stdout

    def execute(self, name, **overrides):
        env = {**os.environ, 'GITHUB_REF': 'refs/heads/main', 'GITHUB_SHA': self.sha,
               'TARGET_SHA': self.sha, 'CONFIRM_PRODUCTION': 'DEPLOY_PRODUCTION',
               'GITHUB_OUTPUT': str(self.output), 'RELEASE_EVENT': 'workflow_dispatch',
               'VERCEL_TOKEN': 'test-only', 'VERCEL_ORG_ID': 'test-only', 'VERCEL_PROJECT_ID': 'test-only',
               **overrides}
        # Actions resolves this trusted event SHA before launching the shell.
        script = step_script(name).replace('${{ github.event.before }}', self.sha)
        return subprocess.run(['bash', '-e', '-c', script], cwd=self.repo,
                              env=env, text=True, capture_output=True)

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
        (self.repo / 'frontend').mkdir()
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
        self.assertIn('args=(build --prod --yes', deploy)
        self.assertIn('args=(deploy --prebuilt --prod', deploy)
        self.assertIn('python3 scripts/post_deploy_static_seo_canary.py', canary)
        self.assertIn('bash scripts/run_pr_regression.sh', REGRESSION)
        self.assertIn('scripts/verify_vercel_packaging.py --manifest', deploy)
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
        self.assertIn("deployment['meta']['githubCommitSha'] == os.environ['GITHUB_SHA']", SOURCE)
        self.assertIn("deployment['projectId'] == os.environ['VERCEL_PROJECT_ID']", SOURCE)

    def test_workflow_shell_blocks_have_valid_bash_syntax(self):
        for name in ('Verify manual release authorization and clean source', 'Recheck exact main and clean deployment source',
                     'Check Vercel deploy scope and secrets', 'Build frontend for Vercel'):
            self.assertEqual(subprocess.run(['bash', '-n'], input=step_script(name), text=True, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
