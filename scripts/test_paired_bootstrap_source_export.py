"""Isolated source-role/export tests; no provider or live application/database."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts import purchase_guard_source as guard
from scripts.backend_upload_payload import qualify, qualify_committed_export
from scripts.build_runtime_source_manifest import build

ROOT = Path(__file__).resolve().parents[1]


class PairFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'controller'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'core.hooksPath', '/dev/null')
        self.git('config', 'user.name', 'Source fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.repo / 'backend/utils').mkdir(parents=True)
        (self.repo / 'internal/legal').mkdir(parents=True)
        self.write('backend/utils/runtime_source_attestation.py',
            (ROOT / 'backend/utils/runtime_source_attestation.py').read_bytes())
        self.write('scripts/build_runtime_source_manifest.py',
            (ROOT / 'scripts/build_runtime_source_manifest.py').read_bytes())
        self.normal = b'''ENVIRONMENT = "production"
COMMERCE_ORDER_PATH = "/orders"
async def enforce_public_release_country(request):
    if ENVIRONMENT == "production" and request.method == "POST" and request.url.path == COMMERCE_ORDER_PATH:
        commerce = commerce_territory_verdict(
            request)
    return None
'''
        for name in ('payments_create_topup', 'payments_verify', 'payments_webhook',
                     '_credit_wallet_for_intent', 'admin_wallet_adjust',
                     'admin_wallet_refund_review', 'admin_wallet_refund_approve',
                     'reading_pass_lease_renew'):
            self.normal += ('\ndef ' + name + '():\n    return "fixture"\n').encode()
        self.closed = guard.guard_only_server(guard.sha(self.normal), self.normal)
        self.write('backend/server.py', self.normal)
        for name in ('railway.json', 'requirements-runtime.txt', 'start_prod.sh'):
            self.write('backend/' + name, b'fixture\n')
        os.chmod(self.repo / 'backend/start_prod.sh', 0o755)
        self.write('backend/Dockerfile', b'COPY --from=builder /x /x\n')
        self.write('.gitignore', b'__pycache__/\n.env\n')
        self.receipt = {'answer': 'Approve temporary purchase pause', 'scope': {
            key: True for key in ('guarded_recovery_bootstrap_on_existing_backend',
            'temporary_new_pass_purchase_pause', 'reopen_after_verified_final_rollout',
            'remain_closed_if_safe_recovery_not_complete', 'existing_reader_listener_preserved',
            'verify_refund_webhook_code_preserved')}}
        self.receipt_path = 'internal/legal/purchase_guard_owner_acceptance.json'
        self.write_json(self.receipt_path, self.receipt)
        self.inventory()
        self.historical = self.commit('historical fixture')
        self.contract = {'schema': guard.SUCCESSOR_SCHEMA, 'state': 'OPEN',
            'approved_merged_584_sha': self.historical,
            'approved_base_server_sha256': guard.sha(self.normal),
            'closed_server_sha256': guard.sha(self.closed),
            'owner_receipt_path': self.receipt_path,
            'owner_receipt_sha256': guard.sha((self.repo / self.receipt_path).read_bytes()),
            'application_source_sha': self.historical,
            'application_server_sha256': guard.sha(self.normal),
            'application_closed_server_sha256': guard.sha(self.closed)}
        self.write_json(guard.PATH, self.contract)
        self.parent = self.commit('normal A')
        self.normal_manifest = (self.repo / 'backend/.runtime-source-manifest.json').read_bytes()
        self.write('backend/server.py', self.closed)
        self.write_json(guard.PATH, {**self.contract, 'state': 'CLOSED'})
        self.inventory()
        self.bootstrap = self.commit('CLOSED B')
        self.write('backend/server.py', self.normal)
        self.write('backend/.runtime-source-manifest.json', self.normal_manifest)
        self.paired = {**self.contract, 'schema': guard.PAIRED_SCHEMA,
            'guarded_bootstrap_source_sha': self.bootstrap}
        self.write_json(guard.PATH, self.paired)
        self.controller = self.commit('normal C pin B')
        self.export = Path(self.tmp.name) / 'export'
        self.make_export()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo,
            env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}, stderr=subprocess.PIPE)

    def write(self, name, data):
        target = self.repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def write_json(self, name, value):
        self.write(name, (json.dumps(value, indent=2) + '\n').encode())

    def inventory(self):
        self.git('add', '.')
        self.write_json('backend/.runtime-source-manifest.json', build(self.repo))

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD').decode().strip()

    def make_export(self):
        self.export.mkdir(mode=0o700)
        rows = guard.backend_tree(self.repo, self.bootstrap)
        mode, kind, oid, name = self.git('ls-tree', self.bootstrap, '--', '.gitignore').decode().split()
        rows[name] = {'mode': mode, 'oid': oid}
        for name, row in rows.items():
            path = self.export / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.git('cat-file', 'blob', row['oid']))
            os.chmod(path, 0o755 if row['mode'] == '100755' else 0o644)

    def qualify(self):
        return qualify_committed_export(self.repo, self.bootstrap, self.export)

    def assert_bad_pair(self, mutate_closed=None, mutate_normal=None, regex=None):
        # Each test uses an isolated fixture branch; no product ref is changed.
        self.git('switch', '-q', '-c', 'negative-fixture', self.parent)
        self.write('backend/server.py', self.closed)
        self.write_json(guard.PATH, {**self.contract, 'state': 'CLOSED'})
        self.inventory()
        if mutate_closed:
            mutate_closed()
        self.bootstrap = self.commit('malformed B fixture')
        self.write('backend/server.py', self.normal)
        os.chmod(self.repo / 'backend/server.py', 0o644)
        self.write('backend/.runtime-source-manifest.json', self.normal_manifest)
        self.write_json(self.receipt_path, self.receipt)
        self.write_json(guard.PATH, {**self.paired,
            'guarded_bootstrap_source_sha': self.bootstrap})
        if mutate_normal:
            mutate_normal()
        self.commit('normal C fixture')
        context = self.assertRaisesRegex(ValueError, regex) if regex else self.assertRaises(ValueError)
        with context:
            guard.validate_paired_source(self.repo)


class SourcePairTests(PairFixture):
    def test_valid_pair_binds_distinct_retained_roles(self):
        result = guard.validate_paired_source(self.repo)
        self.assertEqual(result['bootstrap_source_sha'], self.bootstrap)
        self.assertEqual(result['controller_source_sha'], self.controller)
        self.assertEqual(result['normal_parent_source_sha'], self.parent)
        self.assertNotEqual(result['closed_runtime_sha256'], result['normal_runtime_sha256'])
        self.assertEqual(result['provider_writes'], 0)

    def test_existing_v2_still_validates_without_pair(self):
        self.write_json(guard.PATH, self.contract)
        self.commit('ordinary existing v2')
        self.assertEqual(guard.validate(self.repo)[0]['schema'], guard.SUCCESSOR_SCHEMA)
        with self.assertRaisesRegex(ValueError, 'Explicit committed'):
            guard.validate_paired_source(self.repo)

    def test_pure_source_validation_allows_unrelated_test_artifact(self):
        self.write('unreviewed.txt', b'fixture')
        result = guard.validate_paired_source(self.repo)
        self.assertEqual(result['bootstrap_source_sha'], self.bootstrap)
        with self.assertRaisesRegex(ValueError, 'Clean exact controller'):
            self.qualify()

    def test_unknown_ref_rejected(self):
        self.write_json(guard.PATH, {**self.paired, 'guarded_bootstrap_source_sha': 'main'})
        self.commit('bad label')
        with self.assertRaisesRegex(ValueError, 'Exact committed'):
            guard.validate_paired_source(self.repo)

    def test_controller_itself_cannot_be_closed_role(self):
        self.write_json(guard.PATH, {**self.paired, 'guarded_bootstrap_source_sha': self.controller})
        self.commit('old controller is not a closed source')
        with self.assertRaises(ValueError):
            guard.validate_paired_source(self.repo)

    def test_extra_closed_path_rejected(self):
        self.assert_bad_pair(mutate_closed=lambda: self.write('backend/unrelated.py', b'bad'),
            regex='three-path')

    def test_unrelated_closed_mode_rejected(self):
        self.assert_bad_pair(mutate_closed=lambda: os.chmod(self.repo / 'backend/start_prod.sh', 0o644),
            regex='three-path')

    def test_closed_receipt_mutation_rejected(self):
        self.assert_bad_pair(mutate_closed=lambda: self.write_json(self.receipt_path, {'answer': 'invented'}),
            regex='three-path')

    def test_closed_contract_mutation_rejected(self):
        self.assert_bad_pair(mutate_closed=lambda: self.write_json(guard.PATH,
            {**self.contract, 'state': 'CLOSED', 'owner_receipt_sha256': '0' * 64}),
            regex='underlying approval')

    def test_closed_server_extra_comment_rejected(self):
        self.assert_bad_pair(mutate_closed=lambda: self.write('backend/server.py', self.closed + b'\n# drift\n'),
            regex='deterministic')

    def test_invented_closed_inventory_rejected(self):
        def alter():
            p = self.repo / 'backend/.runtime-source-manifest.json'
            data = json.loads(p.read_text())
            data['expected_sha256'] = '0' * 64
            self.write_json('backend/.runtime-source-manifest.json', data)
        self.assert_bad_pair(mutate_closed=alter, regex='runtime inventory')

    def test_normal_backend_drift_after_pair_rejected(self):
        self.write('backend/extra.py', b'drift')
        self.commit('normal backend drift')
        with self.assertRaisesRegex(ValueError, 'Normal controller backend differs'):
            guard.validate_paired_source(self.repo)

    def test_normal_ignore_drift_after_pair_rejected(self):
        self.write('.gitignore', b'__pycache__/\n.env\nbackend/server.py\n')
        self.commit('ignore drift')
        with self.assertRaisesRegex(ValueError, 'ignore semantics'):
            guard.validate_paired_source(self.repo)

    def hidden_helper_check(self, path):
        helper = self.repo / path
        original = helper.read_bytes()
        marker = Path(self.tmp.name) / 'unreviewed-helper-ran'
        for flag, undo in (('--assume-unchanged', '--no-assume-unchanged'),
                           ('--skip-worktree', '--no-skip-worktree')):
            with self.subTest(flag=flag, helper=path):
                helper.write_bytes(original + ("\nfrom pathlib import Path\nPath(" + repr(str(marker))
                    + ").write_text('unreviewed code ran')\n").encode())
                self.git('update-index', flag, path)
                self.assertEqual(self.git('status', '--porcelain'), b'')
                try:
                    with self.assertRaisesRegex(ValueError, 'inventory helper bytes/mode differ'):
                        self.qualify()
                    self.assertFalse(marker.exists())
                finally:
                    self.git('update-index', undo, path)
                    helper.write_bytes(original)

    def test_hidden_runtime_contract_rejected_before_any_execution(self):
        self.hidden_helper_check('backend/utils/runtime_source_attestation.py')

    def test_hidden_manifest_builder_rejected_before_any_execution(self):
        self.hidden_helper_check('scripts/build_runtime_source_manifest.py')

    def test_hidden_helper_mode_drift_rejected(self):
        path = 'backend/utils/runtime_source_attestation.py'
        os.chmod(self.repo / path, 0o755)
        self.git('update-index', '--assume-unchanged', path)
        self.assertEqual(self.git('status', '--porcelain'), b'')
        with self.assertRaisesRegex(ValueError, 'inventory helper bytes/mode differ'):
            self.qualify()

    def test_closed_source_must_be_actual_ancestor(self):
        branch = self.git('symbolic-ref', '--short', 'HEAD').decode().strip()
        self.git('switch', '-q', '-c', 'unrelated-fixture', self.historical)
        self.write('unrelated.txt', b'fixture')
        unrelated = self.commit('unrelated fixture')
        self.git('switch', '-q', branch)
        self.write_json(guard.PATH, {**self.paired, 'guarded_bootstrap_source_sha': unrelated})
        self.commit('pin nonancestor fixture')
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            guard.validate_paired_source(self.repo)

    def test_mode_change_within_allowed_three_paths_rejected(self):
        self.assert_bad_pair(mutate_closed=lambda: os.chmod(self.repo / 'backend/server.py', 0o755),
            regex='executable mode')

    def test_normal_role_cannot_stay_closed(self):
        self.write('backend/server.py', self.closed)
        self.write_json(guard.PATH, {**self.paired, 'state': 'CLOSED'})
        self.commit('wrong normal role')
        with self.assertRaisesRegex(ValueError, 'normal OPEN'):
            guard.validate_paired_source(self.repo)


class ExportTests(PairFixture):
    def test_exact_export_preserves_modes_members_and_runtime(self):
        result = self.qualify()
        self.assertEqual(result['source'], self.bootstrap)
        self.assertEqual(result['controller_source'], self.controller)
        self.assertFalse(result['native_archive_qualification'])
        self.assertEqual(result['archive_member_prefix'], 'backend/')
        self.assertEqual(result['provider_writes'], 0)
        self.assertFalse(result['path_as_root'])
        self.assertEqual(result['input_path'], str(self.export.resolve() / 'backend'))
        self.assertEqual(result['archive_prefix'], str(self.export.resolve()))
        self.assertIn('backend/.runtime-source-manifest.json', [row['path'] for row in result['files']])
        self.assertIn('backend/start_prod.sh', [row['path'] for row in result['files']])

    def test_target_must_equal_exact_pair(self):
        with self.assertRaisesRegex(ValueError, 'explicitly paired'):
            qualify_committed_export(self.repo, self.parent, self.export)

    def test_export_cannot_be_controller(self):
        with self.assertRaisesRegex(ValueError, 'isolated'):
            qualify_committed_export(self.repo, self.bootstrap, self.repo)

    def test_export_root_symlink_rejected(self):
        link = self.export.parent / 'alias'; link.symlink_to(self.export)
        with self.assertRaisesRegex(ValueError, 'non-symlink'):
            qualify_committed_export(self.repo, self.bootstrap, link)

    def test_inner_symlink_rejected(self):
        (self.export / 'backend/server.py').unlink()
        (self.export / 'backend/server.py').symlink_to(self.repo / 'backend/server.py')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.qualify()

    def test_hard_link_to_controller_rejected(self):
        target = self.export / 'backend/railway.json'
        target.unlink()
        os.link(self.repo / 'backend/railway.json', target)
        with self.assertRaisesRegex(ValueError, 'hard links'):
            self.qualify()

    def test_extra_input_rejected_even_if_ignored(self):
        (self.export / 'backend/.env').write_text('synthetic value')
        with self.assertRaisesRegex(ValueError, 'Unreviewed export'):
            self.qualify()

    def test_extra_empty_directory_rejected(self):
        (self.export / 'unreviewed').mkdir()
        with self.assertRaisesRegex(ValueError, 'Extra export directory'):
            self.qualify()

    def test_missing_member_rejected(self):
        (self.export / 'backend/railway.json').unlink()
        with self.assertRaisesRegex(ValueError, 'member missing'):
            self.qualify()

    def test_same_size_changed_bytes_rejected(self):
        p = self.export / 'backend/railway.json'; p.write_bytes(b'changed\n')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            self.qualify()

    def test_mode_drift_rejected(self):
        os.chmod(self.export / 'backend/start_prod.sh', 0o644)
        with self.assertRaisesRegex(ValueError, 'mode differs'):
            self.qualify()

    def test_root_ignore_bytes_must_match_commit(self):
        (self.export / '.gitignore').write_text('backend/server.py\n')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            self.qualify()

    def test_group_writable_root_rejected(self):
        os.chmod(self.export, 0o770)
        with self.assertRaisesRegex(ValueError, 'owned non-writable'):
            self.qualify()

    def test_group_writable_directory_rejected(self):
        os.chmod(self.export / 'backend', 0o775)
        with self.assertRaisesRegex(ValueError, 'Unsafe export directory'):
            self.qualify()

    def test_fifo_rejected_without_open(self):
        p = self.export / 'backend/railway.json'; p.unlink(); os.mkfifo(p)
        with self.assertRaisesRegex(ValueError, 'Nonregular'):
            self.qualify()

    def test_additional_native_ignore_language_rejected(self):
        (self.export / '.railwayignore').write_text('*.py')
        with self.assertRaisesRegex(ValueError, 'Additional ignore'):
            self.qualify()


if __name__ == '__main__':
    unittest.main()
