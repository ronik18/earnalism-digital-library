"""Synthetic tests: no venv, interpreter, provider, model or network is run."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ENTRY_PATH = Path(__file__).resolve().parent/'earnalism_voice_runtime/pre_drive_loader_entry.py'
spec = importlib.util.spec_from_file_location('_staged_failure_export_entry', ENTRY_PATH)
ENTRY = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ENTRY)
PREFIX = 'EARNALISM_PRE_STORAGE_EVIDENCE='


class EvidenceRetention(unittest.TestCase):
    def run_fixture(self, probe):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / 'synthetic-owned-output'
        class FakeHelper:
            def resolve_provider_driver(self):
                return {'fixture': 'SYNTHETIC_PROVIDER_NOT_A_REAL_LIBRARY', 'library': {'fixture': 'SYNTHETIC_NOT_A_LIBRARY_DESCRIPTOR'}}
            def install_preload(self, provider, site, destination):
                result={'fixture': 'SYNTHETIC_PRELOAD_NOT_EXECUTED', 'provider_binding': provider,
                        'bootstrap': {'fixture': 'SYNTHETIC_BOOTSTRAP_NOT_EXECUTED'}}
                ENTRY._write(destination / 'PROVIDER-DRIVER-PRELOAD.json',result)
                return result
        class FakeBuilder:
            def __init__(self, **kwargs): pass
            def create(self, path):
                (path / 'lib/python3.12/site-packages').mkdir(parents=True)
        with mock.patch.object(ENTRY, '_scope', return_value=10000), \
             mock.patch.object(ENTRY, '_runtime_supported', return_value=True), \
             mock.patch.object(ENTRY, '_load_helper', return_value=FakeHelper()), \
             mock.patch.object(ENTRY.venv, 'EnvBuilder', FakeBuilder), \
             mock.patch.object(ENTRY, '_fresh_probe', side_effect=probe) as called, \
             contextlib.redirect_stdout(io.StringIO()) as stream:
            result = ENTRY.run({'actual_scope_ref': 'SYNTHETIC_TEST_ONLY_NOT_AUTHORITY',
                'approved':True,'shutdown_guard_armed':True,'allocation_started_at':1,
                'original_deadline_epoch':10000,'observed_units_per_hour':1.94,'approved_compute_units':3,
                'unrelated_private_context':'DO_NOT_RETAIN'}, output)
        captured = stream.getvalue()
        actual_files = {p.name: p.read_bytes() for p in output.glob('*.json')}
        temporary.cleanup()  # Simulate losing ephemeral runtime files after return.
        self.assertFalse(output.exists())
        self.assertEqual(called.call_count, 1)
        envelopes = [json.loads(line[len(PREFIX):]) for line in captured.splitlines()
                     if line.startswith(PREFIX)]
        self.assertEqual(len(envelopes), 1)
        envelope = envelopes[0]
        recovered = {}
        for item in envelope['files']:
            self.assertEqual(item['state'], 'EXACT_BYTES')
            raw = base64.b64decode(item['base64'], validate=True)
            self.assertEqual(len(raw), item['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])
            recovered[item['name']] = raw
        self.assertEqual(recovered, actual_files)
        self.assertFalse(envelope['runtime_or_CUDA_or_model_qualification'])
        self.assertEqual(json.loads(recovered['RESULT.json']), result)
        intent=json.loads(recovered['INTENT.json'])
        self.assertEqual(set(intent['driver_scope']),{'approved','actual_scope_ref','allocation_started_at',
            'original_deadline_epoch','observed_units_per_hour','approved_compute_units','shutdown_guard_armed'})
        self.assertNotIn('unrelated_private_context',intent['driver_scope'])
        return result, recovered

    def test_failed_child_diagnostics_remain_exact_after_ephemeral_output_is_lost(self):
        def probe(*args, **kwargs):
            raise subprocess.CalledProcessError(73, ['SYNTHETIC_NOT_EXECUTED'],
                                               output='SYNTHETIC_STDOUT', stderr='SYNTHETIC_CHILD_STDERR')
        result, recovered = self.run_fixture(probe)
        self.assertEqual(result['state'], 'PRE_STORAGE_DRIVER_LOOKUP_FAILED_NO_RETRY')
        self.assertEqual(result['child_returncode'], 73)
        self.assertEqual(result['child_stderr'], 'SYNTHETIC_CHILD_STDERR')
        self.assertEqual(result['child_stdout'], 'SYNTHETIC_STDOUT')
        self.assertEqual(set(recovered), {'INTENT.json', 'PROVIDER-BINDING.json',
                                         'PROVIDER-DRIVER-PRELOAD.json', 'RESULT.json'})
        self.assertFalse(result['CUDA_compute_qualified'] or result['production_ready'])
        self.assertEqual(result['TTS_model_loads'], 0)

    def test_timeout_captures_byte_output_without_claiming_child_exit_status(self):
        def probe(*args, **kwargs):
            raise subprocess.TimeoutExpired(['SYNTHETIC_NOT_EXECUTED'], 1,
                                            output=b'PARTIAL_SYNTHETIC_OUT', stderr=b'PARTIAL_SYNTHETIC_ERR')
        result, _ = self.run_fixture(probe)
        self.assertEqual(result['error_type'], 'TimeoutExpired')
        self.assertEqual(result['child_stderr'], 'PARTIAL_SYNTHETIC_ERR')
        self.assertEqual(result['child_stdout'], 'PARTIAL_SYNTHETIC_OUT')
        self.assertNotIn('child_returncode', result)

    def test_preload_metadata_cannot_promote_a_failed_original_basename_lookup(self):
        def probe(*args,**kwargs):
            raise subprocess.CalledProcessError(1,['SYNTHETIC_NOT_EXECUTED'],
                output='{"state":"EXACT_PROVIDER_BOOTSTRAP_LOADED_BEFORE_LOOKUP"}\n',
                stderr='SYNTHETIC_OSError: libcuda.so.1 lookup failed')
        result,_=self.run_fixture(probe)
        self.assertEqual(result['state'],'PRE_STORAGE_DRIVER_LOOKUP_FAILED_NO_RETRY')
        self.assertEqual(result['child_returncode'],1)
        self.assertIn('EXACT_PROVIDER_BOOTSTRAP_LOADED_BEFORE_LOOKUP',result['child_stdout'])
        self.assertFalse(result['CUDA_compute_qualified'])

    def test_completed_child_output_survives_rejected_final_state(self):
        def probe(*args,**kwargs):
            return subprocess.CompletedProcess(['SYNTHETIC_NOT_EXECUTED'],0,
                stdout='{"state":"EXACT_PROVIDER_BOOTSTRAP_LOADED_BEFORE_LOOKUP"}\nUNEXPECTED_FINAL_LINE',
                stderr='SYNTHETIC_COMPLETED_CHILD_DIAGNOSTIC')
        result,_=self.run_fixture(probe)
        self.assertEqual(result['state'],'PRE_STORAGE_DRIVER_LOOKUP_FAILED_NO_RETRY')
        self.assertEqual(result['child_returncode'],0)
        self.assertIn('UNEXPECTED_FINAL_LINE',result['child_stdout'])
        self.assertEqual(result['child_stderr'],'SYNTHETIC_COMPLETED_CHILD_DIAGNOSTIC')

    def test_success_lookup_receipts_still_do_not_qualify_cuda_or_models(self):
        def probe(*args, **kwargs):
            return subprocess.CompletedProcess(['SYNTHETIC_NOT_EXECUTED'], 0,
                stdout='{"state":"FRESH_MINIMALENV_DRIVER_LOOKUP_PASS"}', stderr='')
        # The fake provider contains the same library key consumed by the
        # existing successful code path; no driver file exists or is loaded.
        original_write = ENTRY._write
        def provider_write(path, value):
            if Path(path).name == 'PROVIDER-BINDING.json':
                value['library'] = {'fixture': 'SYNTHETIC_NOT_A_LIBRARY_DESCRIPTOR'}
            return original_write(path, value)
        with mock.patch.object(ENTRY, '_write', side_effect=provider_write):
            result, _ = self.run_fixture(probe)
        self.assertTrue(result['state'].startswith('FRESH_MINIMALENV_DRIVER_LOOKUP_PASS'))
        self.assertFalse(result['CUDA_compute_qualified'] or result['production_ready'])
        self.assertEqual(result['Torch_imports'], 0)

    def test_evidence_export_bounds_and_missing_files_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            original = b'x' * 16385
            (output / 'RESULT.json').write_bytes(original)
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                ENTRY._emit_notebook_evidence(output)
            envelope = json.loads(stream.getvalue().strip()[len(PREFIX):])
            indexed = {item['name']: item for item in envelope['files']}
            self.assertEqual(indexed['RESULT.json']['state'], 'OMITTED_EXCEEDS_BOUND')
            self.assertEqual(indexed['RESULT.json']['bytes'], len(original))
            self.assertEqual(indexed['PROVIDER-BINDING.json']['state'], 'MISSING_OR_NOT_REGULAR')
            self.assertEqual((output / 'RESULT.json').read_bytes(), original)
            self.assertLess(len(stream.getvalue()), 4096)


if __name__ == '__main__':
    unittest.main(verbosity=2)
