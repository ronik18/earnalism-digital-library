import json
import tempfile
import unittest
from pathlib import Path
from scripts.verify_vercel_packaging import verify


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'frontend/build').mkdir(parents=True)
        (self.root / 'frontend/build/journal-app-shell.html').write_text('<html>journal</html>')
        (self.root / 'frontend/vercel.json').write_text(json.dumps({'functions': {
            'api/journal-page.js': {'includeFiles': 'build/journal-app-shell.html'}}}))
        self.manifest = {'files': [{'path': 'frontend/build/journal-app-shell.html'}]}

    def test_required_shell_selected(self):
        self.assertEqual(verify(self.root, self.manifest)['status'], 'PASS')

    def test_old_exclusion_fails(self):
        with self.assertRaisesRegex(ValueError, 'excluded.*journal-app-shell'):
            verify(self.root, {'files': []})

    def test_broad_build_exclusion_is_preserved(self):
        self.manifest['files'].append({'path': 'frontend/build/index.html'})
        with self.assertRaisesRegex(ValueError, 'unneeded generated build'):
            verify(self.root, self.manifest)

    def test_missing_shell_fails(self):
        (self.root / 'frontend/build/journal-app-shell.html').unlink()
        with self.assertRaisesRegex(ValueError, 'missing includeFiles'):
            verify(self.root, self.manifest)

    def test_additional_function_asset_is_not_implicitly_allowed(self):
        (self.root / 'frontend/build/other.html').write_text('other')
        (self.root / 'frontend/vercel.json').write_text(json.dumps({'functions': {
            'api/other.js': {'includeFiles': 'build/*.html'}}}))
        with self.assertRaisesRegex(ValueError, 'other.html'):
            verify(self.root, self.manifest)

    def prepare_trace(self, target):
        output = self.root / '.vercel/output'
        (output / 'functions/api/journal.func').mkdir(parents=True)
        (output / 'config.json').write_text('{}')
        (output / 'functions/api/journal.func/asset').symlink_to(target)

    def test_traced_source_asset_must_be_selected(self):
        asset = self.root / 'frontend/other.txt'
        asset.write_text('actual trace')
        self.prepare_trace(asset)
        with self.assertRaisesRegex(ValueError, 'other.txt'):
            verify(self.root, self.manifest, prebuilt=True)
        self.manifest['files'].append({'path': 'frontend/other.txt'})
        self.assertEqual(verify(self.root, self.manifest, prebuilt=True)['status'], 'PASS')

    def test_broken_trace_fails(self):
        self.prepare_trace(self.root / 'missing')
        with self.assertRaisesRegex(ValueError, 'broken function trace'):
            verify(self.root, self.manifest, prebuilt=True)

    def test_missing_prebuilt_output_fails(self):
        with self.assertRaisesRegex(ValueError, 'prebuilt output'):
            verify(self.root, self.manifest, prebuilt=True)

    def test_file_path_map_asset_must_be_selected(self):
        asset = self.root / 'frontend/extra.txt'
        asset.write_text('mapped asset')
        self.prepare_trace(self.root / 'frontend/build/journal-app-shell.html')
        (self.root / '.vercel/output/functions/api/journal.func/.vc-config.json').write_text(
            json.dumps({'filePathMap': {'frontend/extra.txt': 'frontend/extra.txt'}}))
        with self.assertRaisesRegex(ValueError, 'extra.txt'):
            verify(self.root, self.manifest, prebuilt=True)
