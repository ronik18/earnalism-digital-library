"""Synthetic verifier tests; these never qualify a real helper/native upload."""
import copy
import hashlib
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
import verify_railway_helper_archive as m


class ArchiveVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve() / 'export'
        (self.root / 'backend').mkdir(parents=True)
        self.data = b'#!/bin/sh\necho closed\n'
        self.file = self.root / 'backend/start_prod.sh'
        self.file.write_bytes(self.data)
        self.file.chmod(0o755)
        row = {'path': 'backend/start_prod.sh', 'bytes': len(self.data), 'sha256': hashlib.sha256(self.data).hexdigest()}
        self.report = {'source': '1' * 40, 'controller_source': '2' * 40,
                       'native_archive_qualification': False, 'files': [row]}
        self.modes = {row['path']: {'mode': 0o755, 'blob_oid': hashlib.sha1(b'blob ' + str(len(self.data)).encode() + b'\0' + self.data).hexdigest()}}
        self.archive = Path(self.temp.name) / 'archive.tgz'

    def tearDown(self):
        self.temp.cleanup()

    def write(self, names=None, data=None, mode=0o755, kind=tarfile.REGTYPE):
        with tarfile.open(self.archive, 'w:gz') as t:
            for name in names or ['./backend/start_prod.sh']:
                item = tarfile.TarInfo(name)
                item.mode = mode
                item.type = kind
                body = self.data if data is None else data
                item.size = len(body) if kind == tarfile.REGTYPE else 0
                t.addfile(item, io.BytesIO(body) if item.size else None)

    def check(self):
        return m.verify_archive(self.archive, self.report, self.root, self.modes)

    def test_exact_member_and_truthful_scope(self):
        self.write()
        r = self.check()
        self.assertEqual(r['regular_members'], 1)
        self.assertFalse(r['native_archive_qualification'])
        self.assertFalse(r['provider_upload_performed'])
        self.assertIsNone(r['provider_git_sha'])
        expected = hashlib.sha256(__import__('json').dumps(self.report['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(r['archive_member_manifest_sha256'], expected)
        modes = [{**self.report['files'][0], 'mode': 0o755}]
        modes_digest = hashlib.sha256(__import__('json').dumps(modes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(r['archive_member_modes_sha256'], modes_digest)

    def test_directory_entries_enumerated_separately(self):
        self.write()
        with tarfile.open(self.archive, 'w:gz') as t:
            d = tarfile.TarInfo('./backend/'); d.type = tarfile.DIRTYPE; t.addfile(d)
            f = tarfile.TarInfo('./backend/start_prod.sh'); f.mode = 0o755; f.size = len(self.data); t.addfile(f, io.BytesIO(self.data))
        self.assertEqual(self.check()['directory_members'], 1)

    def test_bad_paths(self):
        for name in ['/backend/start_prod.sh', 'backend/../start_prod.sh', '././backend/start_prod.sh', 'start_prod.sh', 'backend//start_prod.sh', 'backend\\start_prod.sh']:
            with self.subTest(name=name):
                self.write([name])
                with self.assertRaises(ValueError): self.check()

    def test_duplicate_entries(self):
        self.write(['backend/start_prod.sh', './backend/start_prod.sh'])
        with self.assertRaisesRegex(ValueError, 'duplicate'): self.check()

    def test_content_and_size_changes(self):
        for data in [b'x' * len(self.data), b'x']:
            with self.subTest(data=data):
                self.write(data=data)
                with self.assertRaises(ValueError): self.check()

    def write_raw_mode(self, mode):
        import gzip
        item = tarfile.TarInfo('./backend/start_prod.sh')
        item.size = len(self.data)
        header = bytearray(item.tobuf())
        header[100:108] = f'{mode:07o}\0'.encode()
        header[148:156] = b' ' * 8
        header[148:156] = f'{sum(header):06o}\0 '.encode()
        self.archive.write_bytes(gzip.compress(header + self.data + b'\0' * ((-len(self.data)) % 512) + b'\0' * 1024))
        with tarfile.open(self.archive) as tar:
            member = tar.next()
            self.assertEqual(member.mode, mode)
            self.assertTrue(member.isfile())

    def test_native_regular_type_bits_normalize_to_permission_manifest(self):
        for permissions in (0o644, 0o755):
            with self.subTest(permissions=permissions):
                self.file.chmod(permissions)
                self.modes['backend/start_prod.sh']['mode'] = permissions
                self.write_raw_mode(0o100000 | permissions)
                native = self.check()
                self.assertEqual(native['members'][0]['mode'], permissions)
                self.write(mode=permissions)
                self.assertEqual(native['archive_member_modes_sha256'], self.check()['archive_member_modes_sha256'])

    def test_conflicting_or_unsafe_raw_modes_rejected(self):
        for mode in (0o40755, 0o120755, 0o10755, 0o20755, 0o140755, 0o104755, 0o102755, 0o101755, 0o100775, 0o100777, 0o200755):
            with self.subTest(mode=oct(mode)):
                self.write_raw_mode(mode)
                with self.assertRaisesRegex(ValueError, 'mode'):
                    self.check()

    def test_archive_mode_change(self):
        self.write(mode=0o644)
        with self.assertRaisesRegex(ValueError, 'mode'): self.check()

    def test_all_link_and_special_types_rejected(self):
        for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE]:
            with self.subTest(kind=kind):
                self.write(kind=kind)
                with self.assertRaisesRegex(ValueError, 'link or special'): self.check()

    def test_unexpected_file(self):
        self.write(['backend/extra'])
        with self.assertRaisesRegex(ValueError, 'unexpected'): self.check()

    def test_missing_file(self):
        self.write(['backend'], kind=tarfile.DIRTYPE)
        with self.assertRaisesRegex(ValueError, 'missing'): self.check()

    def test_unexpected_directory(self):
        self.write(['backend/extra'], kind=tarfile.DIRTYPE)
        with self.assertRaisesRegex(ValueError, 'unexpected'): self.check()

    def test_changed_disk_bytes_and_modes(self):
        self.write(); self.file.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'export bytes'): self.check()
        self.file.write_bytes(self.data); self.file.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'mode'): self.check()

    def test_forged_report_hash_cannot_replace_git_blob(self):
        self.write(); self.modes['backend/start_prod.sh']['blob_oid'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'Git blob'): self.check()

    def test_disk_link_rejected_before_read(self):
        self.write(); self.file.unlink(); self.file.symlink_to('/nonexistent')
        with self.assertRaisesRegex(ValueError, 'symlink'): self.check()

    def test_extra_disk_file_rejected(self):
        self.write(); (self.root/'backend/secret').write_bytes(b'no')
        with self.assertRaisesRegex(ValueError, 'inventory'): self.check()

    def test_offline_input_cannot_claim_native(self):
        self.write(); self.report['native_archive_qualification'] = True
        with self.assertRaisesRegex(ValueError, 'nonnative'): self.check()

    def test_additional_ignore_language_rejected(self):
        self.write(); (self.root/'.railwayignore').write_text('*\n')
        with self.assertRaisesRegex(ValueError, 'ignore'): self.check()

    def test_disk_hard_link_rejected(self):
        self.write(); os.link(self.file, Path(self.temp.name) / 'second-link')
        with self.assertRaisesRegex(ValueError, 'hard link'): self.check()

    def test_group_writable_input_rejected(self):
        self.write(); self.file.chmod(0o775)
        with self.assertRaisesRegex(ValueError, 'writable'): self.check()

    def test_unbound_root_ignore_rejected(self):
        self.write(); (self.root/'.gitignore').write_text('changed\n')
        with self.assertRaisesRegex(ValueError, 'root ignore'): self.check()

    def test_added_root_git_boundary_rejected(self):
        self.write(); (self.root/'.git').mkdir()
        with self.assertRaisesRegex(ValueError, 'boundary|ignore'): self.check()

    def test_omitted_required_git_member_rejected(self):
        self.write()
        self.modes['backend/omitted-required.py'] = {'mode': 0o644, 'blob_oid': 'a' * 40}
        with self.assertRaisesRegex(ValueError, 'complete Git backend inventory'):
            self.check()

    def test_duplicate_report_member(self):
        self.write(); self.report['files'].append(copy.deepcopy(self.report['files'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate report'): self.check()


if __name__ == '__main__':
    unittest.main()
