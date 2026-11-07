from pathlib import Path
import json
import tempfile
import unittest
from .release import REQUIRED, REVIEW_SCHEMA, SCHEMA, bound_review, sha


class PrivateKitBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='diwali-private-kit-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('test data')
        (self.root / 'STATE.json').write_text(json.dumps({'publication_approved': False, 'uploads': False}))
        self.review = {'schema': REVIEW_SCHEMA, 'private': True, 'publication_approved': False,
                       'files': {name: sha(self.root / name) for name in REQUIRED}}
        self.write_review()

    def write_review(self):
        path = self.root / 'REVIEW_MANIFEST.json'
        path.write_text(json.dumps(self.review))
        self.manifest = {'schema': SCHEMA, 'private': True, 'publication_approved': False,
                         'review_manifest': path.name, 'review_manifest_sha256': sha(path)}

    def test_intact_bound_review_is_read_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = bound_review(self.root, self.manifest)
        self.assertIs(result['publication_approved'], False)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_changed_media_is_rejected(self):
        (self.root / 'landscape/video.mp4').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Changed bound file'):
            bound_review(self.root, self.manifest)

    def test_changed_review_anchor_is_rejected(self):
        (self.root / 'REVIEW_MANIFEST.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Changed review manifest'):
            bound_review(self.root, self.manifest)

    def test_rebound_path_escape_is_rejected(self):
        self.review['files']['../outside'] = '0' * 64
        self.write_review()
        with self.assertRaisesRegex(ValueError, 'escapes'):
            bound_review(self.root, self.manifest)

    def test_unapproved_private_scope_cannot_be_promoted(self):
        self.manifest['publication_approved'] = True
        with self.assertRaisesRegex(ValueError, 'private, unapproved'):
            bound_review(self.root, self.manifest)

    def test_fixture_is_rejected_even_if_other_hashes_match(self):
        self.review['private_test'] = True
        self.write_review()
        with self.assertRaisesRegex(ValueError, 'Test fixture'):
            bound_review(self.root, self.manifest)


if __name__ == '__main__':
    unittest.main()
