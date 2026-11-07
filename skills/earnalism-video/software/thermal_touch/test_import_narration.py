"""Hostile ZIP regressions and a transfer of immutable existing test evidence.

No narration is synthesized and no actual thermal episode is imported. Integration
fixtures reuse published Spoon bytes only inside temporary test directories.
"""
from pathlib import Path
import copy
import hashlib
import io
import json
import stat
import struct
import tempfile
import unittest
import warnings
import zipfile
from unittest.mock import patch

from . import import_narration as production


def digest(value):
    return hashlib.sha256(value).hexdigest()


def members():
    units = [{"id": "s01", "scene": "test", "text": "Explicit nonmedia security fixture."}]
    return units, {"units.json": json.dumps(units).encode(),
                   "raw/s01.wav": b"Test-only security fixture; this is not an audio recording.",
                   "raw/s01.wav.json": b"{}", "alignment/s01.json": b"{}"}


def archive_bytes(files, manifest=None, extras=(), compression=zipfile.ZIP_STORED):
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, "w", compression) as archive:
            for name, value in files.items():
                archive.writestr(name, value)
            for name, value in extras:
                archive.writestr(name, value)
            archive.writestr("transfer-manifest.json", json.dumps(
                manifest if manifest is not None else {name: digest(value) for name, value in files.items()}))
    return output.getvalue()


class ArchiveSafetyTests(unittest.TestCase):
    def inspect(self, raw, units=None):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return production.inspect_archive(archive, units if units is not None else members()[0])

    def test_every_original_member_hash_and_member_set_are_verified(self):
        units, files = members()
        manifest, raw = self.inspect(archive_bytes(files), units)
        self.assertEqual(manifest, {name: digest(value) for name, value in files.items()})
        self.assertEqual(json.loads(raw), manifest)
        wrong = dict(manifest)
        wrong["raw/s01.wav"] = "0" * 64
        with self.assertRaisesRegex(production.assemble.QualificationError, "hash mismatch"):
            self.inspect(archive_bytes(files, wrong), units)
        omitted = dict(manifest)
        omitted.pop("alignment/s01.json")
        with self.assertRaisesRegex(production.assemble.QualificationError, "member set"):
            self.inspect(archive_bytes(files, omitted), units)

    def test_recovery_archive_requires_local_plan_and_actual_start_ledger(self):
        units, files = members()
        files['recovery-accounting.json'] = b'{}'
        with self.assertRaisesRegex(production.assemble.QualificationError, 'local bounded plan'):
            self.inspect(archive_bytes(files), units)
        with zipfile.ZipFile(io.BytesIO(archive_bytes(files))) as archive:
            with self.assertRaisesRegex(production.assemble.QualificationError, 'actual attempt accounting'):
                production.inspect_archive(archive, units, recovery_plan={'explicit_test_fixture': True})

    def test_traversal_symlink_device_and_reserved_paths_are_rejected(self):
        for name in ("../escape", "/absolute", "raw/../../escape", "raw\\s01.wav", "raw//s01.wav",
                     "raw/./s01.wav", "raw/s01.wav.", "C:/drive", "raw/CON.txt", "raw/.hidden",
                     "raw/NUL", "raw/LPT1.wav", "raw/\x00hidden"):
            with self.subTest(name=name):
                with self.assertRaises(production.assemble.QualificationError):
                    production.safe_member(zipfile.ZipInfo(name))
        for mode in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFDIR, stat.S_IFIFO):
            info = zipfile.ZipInfo("raw/s01.wav")
            info.external_attr = (mode | 0o600) << 16
            with self.assertRaisesRegex(production.assemble.QualificationError, "links/devices"):
                production.safe_member(info)

    def test_duplicate_and_case_colliding_names_are_rejected(self):
        _, files = members()
        for extra in (("raw/s01.wav", files["raw/s01.wav"]), ("RAW/s01.wav", b"case collision")):
            with self.assertRaisesRegex(production.assemble.QualificationError, "Duplicate or case"):
                self.inspect(archive_bytes(files, extras=[extra]))

    def test_unknown_outputs_and_incomplete_export_cannot_enter_production(self):
        _, original = members()
        for name in ("review.json", "imported/raw/overwrite.wav", "raw/s02.wav", "production.json"):
            files = {**original, name: b"not a source transfer record"}
            with self.assertRaisesRegex(production.assemble.QualificationError, "Unexpected/reserved"):
                self.inspect(archive_bytes(files))
        incomplete = dict(original)
        incomplete.pop("alignment/s01.json")
        with self.assertRaisesRegex(production.assemble.QualificationError, "Incomplete"):
            self.inspect(archive_bytes(incomplete))

    def test_expansion_ratio_size_and_member_count_are_bounded(self):
        _, files = members()
        files["logs/qwen.jsonl"] = b"0" * (2 * 1024 * 1024)
        with self.assertRaisesRegex(production.assemble.QualificationError, "expansion ratio"):
            self.inspect(archive_bytes(files, compression=zipfile.ZIP_DEFLATED))
        info = zipfile.ZipInfo("raw/s01.wav")
        info.file_size = production.MAX_MEMBER_BYTES + 1
        with self.assertRaisesRegex(production.assemble.QualificationError, "transfer limits"):
            production.safe_member(info)
        _, files = members()
        with patch.object(production, "MAX_MEMBERS", 2):
            with self.assertRaisesRegex(production.assemble.QualificationError, "member count"):
                self.inspect(archive_bytes(files))

    def test_central_directory_is_bounded_before_zipfile_parses_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.zip"
            _, files = members()
            valid = archive_bytes(files)
            path.write_bytes(valid)
            production.preflight_zip_container(path)
            broken = bytearray(valid)
            end = broken.rfind(b"PK\x05\x06")
            struct.pack_into("<H", broken, end + 10, 65535)
            path.write_bytes(broken)
            with self.assertRaisesRegex(production.assemble.QualificationError, "central directory"):
                production.preflight_zip_container(path)
            path.write_bytes(valid + b"unexpected trailing overlay")
            with self.assertRaises(production.assemble.QualificationError):
                production.preflight_zip_container(path)

    def test_duplicate_json_nonfinite_and_changed_units_are_rejected(self):
        for raw in (b'{"same":1,"same":2}', b'{"not_finite":NaN}'):
            with self.assertRaises(production.assemble.QualificationError):
                production.strict_json(raw)
        units, files = members()
        changed = copy.deepcopy(units)
        changed[0]["text"] = "A different prepared script."
        with self.assertRaisesRegex(production.assemble.QualificationError, "prepared script"):
            self.inspect(archive_bytes(files), changed)

    def test_existing_file_directory_and_dangling_symlink_prevent_any_overwrite(self):
        for kind in ("file", "directory", "symlink"):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / "imported"
                if kind == "file":
                    path.write_bytes(b"preserve")
                elif kind == "directory":
                    path.mkdir()
                else:
                    path.symlink_to(root / "missing")
                with self.assertRaisesRegex(production.assemble.QualificationError, "preserved"):
                    production.preflight_destination(root)
                self.assertFalse((root / ".thermal-import-lock.json").exists())


class ImmutableSourceTransferTest(unittest.TestCase):
    def test_real_sources_import_byte_exact_once_and_asr_difference_stays_unresolved(self):
        source = production.assemble.PUBLISHED_B_ROOT
        units = production.assemble.load(source / "units.json")
        raw_files = {name: (source / "imported" / name).read_bytes() for name in production.required_paths(units)}
        raw_files["units.json"] = (source / "units.json").read_bytes()
        raw_files["logs/qwen.jsonl"] = b'{"test":"retained only inside archive"}\n'
        before = {name: production.file_hash(source / "imported" / name) for name in production.required_paths(units)}
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            archive = temp / "source.zip"
            archive.write_bytes(archive_bytes(raw_files))
            root = temp / "prepared"
            root.mkdir()
            (root / "units.json").write_bytes(raw_files["units.json"])
            (root / "baseline-job.json").write_bytes((source / "baseline-job.json").read_bytes())
            result = production.import_narration(archive, root)
            self.assertEqual(result["source_validation"], "PASS")
            self.assertGreater(result["asr_differences_unresolved"], 0)  # Existing travelling/traveling finding.
            self.assertIsNone(next(a for a in result["asr_audits"] if a["differences"])["resolution"])
            self.assertEqual(result["new_recording_listening"], "PENDING")
            self.assertFalse(result["publication_approved"])
            self.assertEqual((root / "narration-transfer/source.zip").read_bytes(), archive.read_bytes())
            self.assertEqual((root / "narration-transfer/original-units.json").read_bytes(), raw_files["units.json"])
            imported = {p.relative_to(root / "imported").as_posix() for p in (root / "imported").rglob("*") if p.is_file()}
            self.assertEqual(imported, set(production.required_paths(units)))
            for name in imported:
                self.assertEqual((root / "imported" / name).read_bytes(), raw_files[name])
            self.assertFalse((root / "imported/logs").exists())
            with self.assertRaisesRegex(production.assemble.QualificationError, "preserved"):
                production.import_narration(archive, root)
            self.assertEqual(production.assemble.load(root / "transfer-receipt.json"), result)
        self.assertEqual(before, {name: production.file_hash(source / "imported" / name)
                                  for name in production.required_paths(units)})


if __name__ == "__main__":
    unittest.main()
