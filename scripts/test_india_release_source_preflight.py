import copy
import hashlib
import json
import unittest
from scripts.india_release_source_preflight import CONTRACT, qualify, SEO_METADATA, ATTRIBUTION_DIGESTS


class SourcePreflightTests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads(CONTRACT.read_text())
        self.values = {}
        for rev in (self.c['application_sha'], self.c['backend_artifact_sha'], self.c['backend_review_sha'],
                    self.c['frontend_artifact_sha'], self.c['frontend_review_sha']):
            self.values[rev + '^{tree}'] = self.c['application_root_tree']
        reuse=self.c['frontend_ui_review_reuse']
        for rev in (reuse['baseline_sha'],reuse['review_sha']):
            self.values[rev+'^{tree}']=reuse['baseline_root_tree']
        self.values[reuse['baseline_sha']+':'+SEO_METADATA]=reuse['old_blob']
        self.values[self.c['application_sha']+':'+SEO_METADATA]=reuse['new_blob']
        self.data={key:'new-'+key+'\n' for key in ATTRIBUTION_DIGESTS}
        self.before={'schema':'fixture','books':[{'slug':'radharani','title':'unchanged'}],
                     'generated_from':{key:'0'*64 for key in ATTRIBUTION_DIGESTS}}
        self.after=copy.deepcopy(self.before)
        self.after['generated_from']={key:hashlib.sha256(value.encode()).hexdigest()
                                     for key,value in self.data.items()}

    def git(self, *args):
        if args[0] == 'status': return ''
        if args[0] == 'merge-base': return ''
        if args[0] == 'diff':return SEO_METADATA
        if args[0] == 'show':
            rev,path=args[1].split(':',1)
            if path==SEO_METADATA:
                return json.dumps(self.before if rev==self.c['frontend_ui_review_reuse']['baseline_sha'] else self.after)
            return self.data[path]
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

    def test_prior_ui_review_is_reused_without_reusing_prior_frontend_artifact(self):
        report=qualify(self.c,self.git,self.checks)
        self.assertNotEqual(self.values[self.c['frontend_ui_review_reuse']['baseline_sha']+'^{tree}'],
                            self.values[self.c['application_sha']+'^{tree}'])
        self.assertEqual(report['frontend_artifact_sha'],self.c['application_sha'])
        self.assertFalse(report['frontend_binary_reuse_approved'])
        self.assertFalse(report['deployment_authorized'])

    def test_reused_frontend_subtree_change_is_denied(self):
        def changed(*args):
            if args[0]=='rev-parse' and args[1]==self.c['frontend_artifact_sha']+':frontend':return 'c'*40
            return self.git(*args)
        with self.assertRaises(ValueError):qualify(self.c,changed,self.checks)

    def test_review_checks_cannot_be_omitted(self):
        for rev in {self.c['frontend_review_sha'],self.c['backend_review_sha'],self.c['frontend_ui_review_reuse']['review_sha']}:
            contract=copy.deepcopy(self.c);del contract['required_checks'][rev]
            with self.assertRaises(ValueError):qualify(contract,self.git,self.checks)

    def test_unreviewed_ui_path_or_blob_change_denied(self):
        def extra_path(*args):
            return SEO_METADATA+'\nfrontend/src/changed.jsx' if args[0]=='diff' else self.git(*args)
        with self.assertRaises(ValueError):qualify(self.c,extra_path,self.checks)
        self.values[self.c['application_sha']+':'+SEO_METADATA]='0'*40
        with self.assertRaises(ValueError):qualify(self.c,self.git,self.checks)

    def test_unrelated_metadata_or_false_derived_hash_denied(self):
        self.after['books'][0]['title']='unreviewed'
        with self.assertRaises(ValueError):qualify(self.c,self.git,self.checks)
        self.after['books'][0]['title']='unchanged'
        self.after['generated_from'][next(iter(ATTRIBUTION_DIGESTS))]='f'*64
        with self.assertRaises(ValueError):qualify(self.c,self.git,self.checks)

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
