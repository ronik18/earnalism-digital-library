import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts.verify_build_dependency_identity import compare_entries, runtime_identity, verify

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / 'scripts/frontend_build_dependency_reference.json').read_text())


class BuildDependencyIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'frontend/node_modules').mkdir(parents=True)
        (self.root / '.gitignore').write_text('frontend/node_modules/\n')
        self.locked = {'': {'name': 'synthetic-fixture'}, 'node_modules/a': {
            'version': '1.0.0', 'resolved': 'https://registry.npmjs.org/a/-/a-1.0.0.tgz', 'integrity': 'sha512-fixture'}}
        for name in REFERENCE['darwin_optional_omissions']:
            self.locked[name] = {'version': '2.0.0', 'os': ['darwin'], 'optional': True}
        (self.root / 'frontend/package.json').write_text('{"name":"synthetic-fixture"}\n')
        (self.root / 'frontend/package-lock.json').write_text(json.dumps({'packages': self.locked}))
        for cmd in (['git', 'init', '-q'], ['git', 'config', 'user.name', 'Synthetic Test'],
                    ['git', 'config', 'user.email', 'fixture@example.invalid'], ['git', 'add', '.'],
                    ['git', 'commit', '-qm', 'synthetic source fixture']):
            subprocess.run(cmd, cwd=self.root, check=True, capture_output=True)
        self.reference = copy.deepcopy(REFERENCE)
        self.reference['frontend_sha'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()
        self.reference['installed_count'] = 5
        for name, key in (('package.json', 'package_json_sha256'), ('package-lock.json', 'package_lock_sha256')):
            self.reference[key] = hashlib.sha256((self.root / 'frontend' / name).read_bytes()).hexdigest()
        self.installed = {'node_modules/a': copy.deepcopy(self.locked['node_modules/a']), **copy.deepcopy(REFERENCE['observed_unlocked_tools'])}
        (self.root / 'frontend/node_modules/.package-lock.json').write_text(json.dumps({'packages': self.installed}))

    def check(self):
        return verify(self.root, self.reference, self.reference['runtime'])

    def test_exact_reference_passes_and_records_complete_installed_identity(self):
        result = self.check()
        self.assertEqual(result['installed_count'], 5)
        self.assertEqual(result['installed'], self.installed)
        self.assertEqual(result['source_full_status'], 'CLEAN')

    def test_any_extra_missing_or_version_resolution_integrity_drift_fails(self):
        for field in ('version', 'resolved', 'integrity'):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.installed)
                changed['node_modules/typescript'][field] = 'unreviewed'
                with self.assertRaisesRegex(ValueError, 'differs from review'):
                    compare_entries(self.locked, changed, self.reference)
        for changed in ({**self.installed, 'node_modules/extra': {}},
                        {k: v for k, v in self.installed.items() if k != 'node_modules/a'}):
            with self.assertRaisesRegex(ValueError, 'set differs'):
                compare_entries(self.locked, changed, self.reference)

    def test_only_evidenced_darwin_optional_omissions_are_allowed(self):
        for change in ({'optional': False}, {'os': ['linux']}, {'os': None}):
            locked = copy.deepcopy(self.locked)
            locked[REFERENCE['darwin_optional_omissions'][0]].update(change)
            with self.assertRaisesRegex(ValueError, 'Unproven'):
                compare_entries(locked, self.installed, self.reference)

    def test_source_sha_dirty_source_and_runtime_drift_fail_closed(self):
        reference = copy.deepcopy(self.reference)
        reference['frontend_sha'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'source SHA'):
            verify(self.root, reference, reference['runtime'])
        with self.assertRaisesRegex(ValueError, 'runtime/CLI'):
            verify(self.root, self.reference, {**self.reference['runtime'], 'npm': 'future-version'})
        (self.root / 'frontend/package-lock.json').write_text('changed tracked lock')
        with self.assertRaisesRegex(ValueError, 'Dirty'):
            self.check()

    def test_external_or_symlinked_installed_manifest_is_rejected(self):
        manifest = self.root / 'frontend/node_modules/.package-lock.json'
        manifest.unlink()  # Only this synthetic owned fixture.
        manifest.symlink_to(self.root.parent / 'unread-external-fixture')
        with self.assertRaisesRegex(ValueError, 'external'):
            self.check()

    def test_version_probes_do_not_forward_release_credentials_or_npm_config(self):
        cli = self.root / 'fake-vercel/dist/vc.js'
        cli.parent.mkdir(parents=True)
        cli.write_text('synthetic fixture never executed')
        (cli.parent.parent / 'package.json').write_text('{"version":"63.1.2"}')
        selector = cli.parent / 'chunks/chunk-GNY6U33Z.js'
        selector.parent.mkdir()
        selector.write_text('synthetic selector never imported')
        def probe(cmd, **kwargs):
            env = kwargs['env']
            self.assertEqual(set(env), {'PATH', 'HOME', 'NPM_CONFIG_USERCONFIG', 'NPM_CONFIG_GLOBALCONFIG'})
            self.assertNotEqual(env['NPM_CONFIG_USERCONFIG'], env['NPM_CONFIG_GLOBALCONFIG'])
            return 'v20.20.2\n' if cmd[0] == 'node' else '10.8.2\n'
        with mock.patch.dict(os.environ, {'VERCEL_TOKEN': 'test-sentinel', 'NODE_OPTIONS': 'test-sentinel'}), \
             mock.patch('scripts.verify_build_dependency_identity.shutil.which', return_value=str(cli)), \
             mock.patch('scripts.verify_build_dependency_identity.subprocess.check_output', side_effect=probe):
            result = runtime_identity()
        self.assertEqual(result['node'], 'v20.20.2')

    def test_production_gate_runs_after_build_and_again_before_deployment(self):
        from scripts.test_manual_production_release_workflow import parse_workflow
        workflow = parse_workflow((ROOT / '.github/workflows/reader-frontend-production.yml').read_text())
        steps = workflow['jobs']['deploy_frontend']['steps']
        index = {step['name']: i for i, step in enumerate(steps)}
        self.assertLess(index['Build frontend for Vercel'], index['Verify exact built dependency identities'])
        self.assertLess(index['Verify exact built dependency identities'], index['Verify source and prebuilt function packaging'])
        deploy = steps[index['Deploy frontend to Vercel production']]['run']
        self.assertLess(deploy.index('verify_build_dependency_identity.py'), deploy.index('args=(deploy --prebuilt --prod'))
        self.assertIn('vercel-dependency-identity.json', json.dumps(steps[index['Publish function packaging evidence']]))
        self.assertIn('scripts.test_verify_build_dependency_identity', (ROOT / '.github/workflows/regression.yml').read_text())


if __name__ == '__main__':
    unittest.main()
