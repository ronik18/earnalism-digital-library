import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import prepare_inactive_reader_segment_plans as plans


class InactivePlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'data/controlled_publications/example'
        (self.package / 'chapters').mkdir(parents=True)
        self.write(self.root / 'data/controlled_launch.json', {'live_approved_slugs': []})
        self.write(self.package / 'rights_decision.json', {'status': 'ACCEPTED', 'decision_id': 'local', 'components': {}})
        self.write(self.package / 'publication_manifest.json', {'reader_release': {'exposed': False}, 'audio_release': {'exposed': False}})
        self.write(self.package / 'public_book.json', {'chapters': [{'id': 'one', 'order': 1}]})
        for name in ('reader_manifest', 'source_evidence', 'approval_evidence', 'checksum_manifest'):
            self.write(self.package / (name + '.json'), {})
        self.write(self.package / 'chapters/one.json', {'id': 'one', 'order': 1, 'title': 'One', 'content': 'Private text', 'content_hash': hashlib.sha256(b'Private text').hexdigest()})

    def write(self, path, value):
        path.write_text(json.dumps(value))

    @patch.object(plans, 'evaluate_accepted_record', return_value=SimpleNamespace(passed=True))
    def test_hash_only_and_no_source_mutation(self, gate):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*.json')}
        with patch.object(plans, 'canonical_page_records', return_value=[{'page_index': 1, 'chapter_id': 'one', 'content_sha256': 'abc', 'is_public_preview': True, 'content': 'Private text'}]), patch.object(plans, 'segment_manifest', return_value={'sha256': 'abc'}):
            output = plans.prepare(self.root)
        self.assertNotIn('Private text', json.dumps(output))
        self.assertEqual(output[0]['state'], 'INACTIVE_LOCAL_PLAN_NOT_PROMOTED')
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*.json')})
        self.assertEqual(gate.call_args.kwargs['use'], 'reader_preview')
        self.assertEqual(set(gate.call_args.kwargs['required_components']), plans.REQUIRED_COMPONENTS)

    def test_live_title_is_not_prepared(self):
        self.write(self.root / 'data/controlled_launch.json', {'live_approved_slugs': ['example']})
        self.assertEqual(plans.prepare(self.root), [])

    def test_exposed_package_rejected(self):
        self.write(self.package / 'publication_manifest.json', {'reader_release': {'exposed': False}, 'audio_release': {'exposed': True}})
        with self.assertRaisesRegex(ValueError, 'unexposed'):
            plans.prepare(self.root)

    @patch.object(plans, 'evaluate_accepted_record', return_value=SimpleNamespace(passed=False, reasons=['mismatch']))
    def test_invalid_local_record_rejected(self, gate):
        with self.assertRaisesRegex(ValueError, 'local record mismatch'):
            plans.prepare(self.root)

    @patch.object(plans, 'evaluate_accepted_record', return_value=SimpleNamespace(passed=True))
    def test_changed_chapter_rejected_before_pagination(self, gate):
        chapter = self.package / 'chapters/one.json'
        value = json.loads(chapter.read_text())
        value['content'] = 'Changed after approval'
        self.write(chapter, value)
        with self.assertRaisesRegex(ValueError, 'chapter identity mismatch'):
            plans.prepare(self.root)


if __name__ == '__main__':
    unittest.main()
