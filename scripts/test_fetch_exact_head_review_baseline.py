import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from scripts.fetch_exact_head_review_baseline import select_run, extract_verified, verify_package

HEAD='a'*40
class BaselineTests(unittest.TestCase):
    def test_pending_and_other_head_not_accepted(self):
        self.assertIsNone(select_run([dict(id=1,head_sha=HEAD,event='pull_request',status='in_progress')],HEAD))
        self.assertIsNone(select_run([dict(id=1,head_sha='b'*40,event='pull_request',status='completed',conclusion='success')],HEAD))
    def test_failed_newest_never_falls_back(self):
        rows=[dict(id=i,head_sha=HEAD,event='pull_request',status='completed',conclusion=c) for i,c in [(1,'success'),(2,'failure')]]
        with self.assertRaises(ValueError):select_run(rows,HEAD)
    def test_exact_success(self):
        r=dict(id=2,head_sha=HEAD,event='pull_request',status='completed',conclusion='success');self.assertEqual(select_run([r],HEAD),r)
    def test_traversal_and_duplicate_archives_rejected(self):
        for names in [('.. /x'.replace(' ',''),),('x','x'),('/x',)]:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);z=p/'x.zip'
                with zipfile.ZipFile(z,'w') as a:
                    for name in names:a.writestr(name,b'fixture')
                with self.assertRaises(ValueError):extract_verified(z,p/'out')
    def fixture(self,p):
        (p/'image.png').write_bytes(b'dummy-not-rendered-evidence')
        m={'files':[{'path':'image.png','bytes':27,'sha256':hashlib.sha256((p/'image.png').read_bytes()).hexdigest()}]}
        m['files'][0]['bytes']=(p/'image.png').stat().st_size
        (p/'manifest.json').write_text(json.dumps(m));(p/'manifest.sha256').write_text(hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest());(p/'provenance.json').write_text(json.dumps({'package_generation_head':HEAD}))
    def test_hash_bound_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.fixture(p);verify_package(p,HEAD);(p/'image.png').write_bytes(b'tampered')
            with self.assertRaises(ValueError):verify_package(p,HEAD)
    def test_wrong_head_and_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.fixture(p)
            with self.assertRaises(ValueError):verify_package(p,'b'*40)
            (p/'manifest.json').write_text('{}')
            with self.assertRaises(ValueError):verify_package(p,HEAD)
    def test_workflow_requires_current_published_baseline(self):
        t=Path('.github/workflows/pr469-postmerge-recovery-owner-evidence.yml').read_text();self.assertIn('fetch_exact_head_review_baseline.py --head "${{ github.event.pull_request.head.sha }}"',t);self.assertNotIn('artifact-ids: 11025247154',t)
        primary=Path('.github/workflows/seamless-brand-owner-review.yml').read_text()
        for line in t.split('    paths:\n',1)[1].split('\npermissions:',1)[0].splitlines():
            if line.strip().startswith('- '):self.assertIn(line,primary)
        p=Path('scripts/package_pr469_postmerge_owner_review.py').read_text();self.assertIn('baseline.get("head") != exact_head',p);self.assertNotIn('prior_owner_reviewed_head',p)
if __name__=='__main__':unittest.main()
