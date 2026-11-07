"""Exact current application protocol custody; no providers, native operations or DB."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts import purchase_guard_source as guard

ROOT = Path(__file__).resolve().parents[1]


class ApplicationProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = json.loads((ROOT / guard.PATH).read_text())
        cls.protocol = json.loads((ROOT / guard.PROTOCOL_PATH).read_text())
        refs = {cls.native['approved_merged_584_sha'], cls.native['application_source_sha'], cls.protocol['application_source_sha']}
        cls.sources = {ref: guard.exact_git_server(ROOT, ref) for ref in refs}

    def check(self, *, edit=None, actual=None, owner=None, historical=None, application=None, native=False, paired=False):
        protocol = copy.deepcopy(self.protocol)
        sources = dict(self.sources)
        if application is not None:
            # Protocol and native refs may now legitimately coincide. Keep the
            # native approved bytes immutable while exercising a new protocol.
            protocol['application_source_sha']='a'*40
            sources[protocol['application_source_sha']] = application
            protocol['application_server_sha256'] = guard.sha(application)
            protocol['application_closed_server_sha256'] = guard.sha(guard.guard_only_server(guard.sha(application), application))
        if edit:
            protocol.update(edit)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'internal/legal').mkdir(parents=True)
            (root/'backend').mkdir()
            (root/guard.PATH).write_bytes((ROOT/guard.PATH).read_bytes() if historical is None else historical)
            (root/guard.PROTOCOL_PATH).write_text(json.dumps(protocol))
            receipt = self.native['owner_receipt_path']
            (root/receipt).write_bytes((ROOT/receipt).read_bytes() if owner is None else owner)
            (root/'backend/server.py').write_bytes((application if application is not None else sources[self.protocol['application_source_sha']]) if actual is None else actual)
            def reader(_root, ref):
                if ref not in sources:
                    raise ValueError('Unexpected unqualified source')
                return sources[ref]
            if native:
                return guard.validate(root, base_reader=reader)
            if paired:
                return guard.validate_paired_source(root)
            return guard.validate_purchase_protocol_source(root, base_reader=reader)

    def test_exact_current_protocol_is_explicitly_not_native_recovery(self):
        manifest, source, closed = self.check()
        self.assertEqual(manifest['scope'], 'SOURCE_PROTOCOL_ONLY_NOT_NATIVE_RECOVERY')
        self.assertNotEqual(manifest['schema'], guard.PAIRED_SCHEMA)
        self.assertEqual(source, (ROOT/'backend/server.py').read_bytes())
        self.assertIn(b'PURCHASE_INITIATION_CLOSED', closed)

    def test_diagnostic_protocol_does_not_qualify_retained_native_pair(self):
        guard.validate_purchase_protocol_source(ROOT)
        with self.assertRaisesRegex(ValueError,'Whole server equality'):
            guard.validate_paired_source(ROOT)

    def test_actual_disk_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Whole application protocol'):
            self.check(actual=(ROOT/'backend/server.py').read_bytes()+b'\n# unbound\n')

    def test_exact_state_digest_commit_and_contract_are_required(self):
        for edit in ({'state':'CLOSED'}, {'scope':'NATIVE_RECOVERY'}, {'application_source_sha':'f'*40},
                     {'application_source_sha':None}, {'application_server_sha256':'0'*64},
                     {'application_closed_server_sha256':'0'*64}, {'historical_contract_sha256':'0'*64}):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                self.check(edit=edit)

    def test_original_owner_receipt_is_still_mandatory(self):
        with self.assertRaisesRegex(ValueError, 'Owner receipt'):
            self.check(owner=b'{}')

    def test_protected_handler_edits_are_not_authorized_by_audio_work(self):
        application=(ROOT/'backend/server.py').read_bytes().replace(b'async def payments_verify(', b'async def renamed_payments_verify(', 1)
        with self.assertRaisesRegex(ValueError, 'protected purchase'):
            self.check(application=application)

    def test_historical_contract_bytes_cannot_be_substituted(self):
        historical=(ROOT/guard.PATH).read_bytes()+b'\n'
        with self.assertRaisesRegex(ValueError, 'Historical operational contract'):
            self.check(historical=historical)

    def test_native_whole_server_gate_still_rejects_unbound_application(self):
        # A newly qualified current source pair can be valid; the protocol
        # manifest must never bypass exact native bytes or act as that pair.
        with self.assertRaisesRegex(ValueError, 'Whole server equality'):
            self.check(native=True,actual=(ROOT/'backend/server.py').read_bytes()+b'\n# unbound native bytes\n')
        with self.assertRaisesRegex(ValueError, 'Operational source contract malformed'):
            self.check(native=True,historical=json.dumps(self.protocol).encode())


if __name__ == '__main__':
    unittest.main()
