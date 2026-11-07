import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_source

class SourceManifestTests(unittest.TestCase):
    def fixture(self, root):
        (root/'lesson.md').write_text('Original source')
        manifest={'files':{'lesson.md':hashlib.sha256((root/'lesson.md').read_bytes()).hexdigest()},'production_or_publication_approval':False}
        (root/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest))
        return manifest

    @patch('check_source.subprocess.run')
    def test_exact_source_passes_but_modified_source_fails(self, git):
        git.return_value.returncode=1
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            self.assertFalse(check_source.check(root)['runtime_assets_or_publication_approved'])
            (root/'lesson.md').write_text('Changed')
            with self.assertRaisesRegex(ValueError,'changed source'):check_source.check(root)

    def test_parent_traversal_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=self.fixture(root);m['files']={'../outside.md':'0'*64}
            (root/'SOURCE_MANIFEST.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'Unsafe'):check_source.check(root)

    @patch('check_source.subprocess.run')
    def test_omitted_tracked_file_is_rejected(self, git):
        git.return_value.returncode=0;git.return_value.stdout=b'lesson.md\0extra.py\0SOURCE_MANIFEST.json\0'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            with self.assertRaisesRegex(ValueError,'inventory differs'):check_source.check(root)
