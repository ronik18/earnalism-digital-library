"""Offline successor contract checks; no provider, settings or financial events."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import purchase_guard_source as guard

ROOT = Path(__file__).resolve().parents[1]


class SuccessorContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / guard.PATH).read_text())
        self.historical = guard.exact_git_server(ROOT, self.manifest['approved_merged_584_sha'])
        self.application = guard.validate(ROOT)[1]

    def check(self, *, manifest_edit=None, application=None, actual=None):
        application = self.application if application is None else application
        manifest = {k: v for k, v in self.manifest.items()
                    if k not in {'application_source_sha', 'application_server_sha256', 'application_closed_server_sha256'}}
        manifest.update(schema=guard.SUCCESSOR_SCHEMA, state='OPEN',
                        application_source_sha='a' * 40,
                        application_server_sha256=guard.sha(application),
                        application_closed_server_sha256=guard.sha(guard.guard_only_server(guard.sha(application), application)))
        if manifest_edit:
            manifest.update(manifest_edit)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'internal/legal').mkdir(parents=True)
            (root / 'backend').mkdir()
            (root / guard.PATH).write_text(json.dumps(manifest))
            receipt = Path(manifest['owner_receipt_path'])
            (root / receipt).write_bytes((ROOT / receipt).read_bytes())
            (root / 'backend/server.py').write_bytes(application if actual is None else actual)
            def reader(_root, ref):
                if ref == 'a' * 40:
                    return application
                if ref == manifest['approved_merged_584_sha']:
                    return self.historical
                raise ValueError('Unexpected source')
            return guard.validate(root, base_reader=reader)

    def test_exact_successor_preserves_historical_receipt_and_guard(self):
        manifest, base, closed = self.check()
        self.assertEqual(base, self.application)
        self.assertEqual(guard.sha(self.historical), manifest['approved_base_server_sha256'])
        self.assertIn(b'PURCHASE_INITIATION_CLOSED', closed)
        self.assertNotIn(b'PURCHASE_INITIATION_CLOSED', base)

    def test_server_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Whole server equality'):
            self.check(actual=self.application + b'\n# unbound source\n')

    def test_candidate_digest_cannot_be_invented(self):
        with self.assertRaisesRegex(ValueError, 'Application source binding'):
            self.check(manifest_edit={'application_server_sha256': '0' * 64})

    def test_financial_handler_change_is_not_authorized_by_cache_work(self):
        altered = self.application.replace(b'async def payments_verify(', b'async def renamed_payments_verify(', 1)
        self.assertNotEqual(altered, self.application)
        with self.assertRaisesRegex(ValueError, 'protected purchase'):
            self.check(application=altered)

    def test_closed_binding_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Successor closed source binding'):
            self.check(manifest_edit={'application_closed_server_sha256': '0' * 64})

    def test_historical_receipt_is_still_required(self):
        with self.assertRaisesRegex(ValueError, 'Owner receipt differs'):
            self.check(manifest_edit={'owner_receipt_sha256': '0' * 64})


if __name__ == '__main__':
    unittest.main()
