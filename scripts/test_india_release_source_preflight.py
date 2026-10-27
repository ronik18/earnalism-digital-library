import copy
import json
import unittest
from scripts.india_release_source_preflight import CONTRACT, qualify


class SourcePreflightTests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads(CONTRACT.read_text())
        self.values = {}
        for rev in (self.c['application_sha'], self.c['frontend_review_sha']):
            self.values[rev + '^{tree}'] = self.c['application_root_tree']
        for rev in (self.c['backend_artifact_sha'], self.c['backend_review_sha']):
            self.values[rev + '^{tree}'] = 'a' * 40

    def git(self, *args):
        if args[0] == 'status': return ''
        if args[0] == 'merge-base': return ''
        ref = args[1]
        if ref == 'HEAD': return 'f' * 40
        if ref.endswith(':backend'): return self.c['backend_subtree']
        if ref.endswith(':frontend'): return self.c['frontend_subtree']
        return self.values[ref]

    def checks(self, rev):
        return [dict(name=n, status='completed', conclusion='success')
                for n in self.c['required_checks'][rev]]

    def test_squash_review_is_supported_without_execution_authority(self):
        report = qualify(self.c, self.git, self.checks)
        self.assertEqual(report['status'], 'SOURCE_QUALIFIED_EXECUTION_HOLD')
        self.assertFalse(report['deployment_authorized'])
        self.assertFalse(report['provider_identity_verified'])

    def test_missing_failed_pending_duplicate_check_denied(self):
        for mode in ('missing', 'failure', 'pending', 'duplicate'):
            def changed(rev):
                rows = self.checks(rev)
                if mode == 'missing': return rows[1:]
                if mode == 'duplicate': return rows + [dict(rows[0], conclusion='failure')]
                rows[0]['conclusion'] = 'failure' if mode == 'failure' else None
                rows[0]['status'] = 'completed' if mode == 'failure' else 'in_progress'
                return rows
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                qualify(self.c, self.git, changed)

    def test_merged_review_root_mismatch_denied(self):
        self.values[self.c['frontend_review_sha'] + '^{tree}'] = 'b' * 40
        with self.assertRaises(ValueError): qualify(self.c, self.git, self.checks)

    def test_controller_subtree_change_denied(self):
        def changed(*args):
            if args[0] == 'rev-parse' and args[1] == 'f' * 40 + ':frontend': return 'c' * 40
            return self.git(*args)
        with self.assertRaises(ValueError): qualify(self.c, changed, self.checks)

    def test_dirty_checkout_denied(self):
        def dirty(*args): return ' M file' if args[0] == 'status' else self.git(*args)
        with self.assertRaises(ValueError): qualify(self.c, dirty, self.checks)

    def test_scope_expansion_denied(self):
        for key, value in (('territories', ['IN', 'US']), ('deployment_authorized', True)):
            changed = copy.deepcopy(self.c); changed['scope'][key] = value
            with self.assertRaises(ValueError): qualify(changed, self.git, self.checks)


if __name__ == '__main__': unittest.main()
