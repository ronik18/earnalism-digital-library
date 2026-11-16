"""Source/mock checks only: no actual provider library, GPU, storage or model."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent/'earnalism_voice_runtime'
SPEC = importlib.util.spec_from_file_location('private_pre_drive_entry', HERE/'pre_drive_loader_entry.py')
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)


class PreDriveEntryTests(unittest.TestCase):
    def scope(self):
        now = time.time()
        return {'approved': True, 'actual_scope_ref': 'SOURCE_MOCK_ONLY_NOT_AUTHORITY',
                'shutdown_guard_armed': True, 'allocation_started_at': now-1,
                'original_deadline_epoch': now+100, 'observed_units_per_hour': 1.94,
                'approved_compute_units': 3}

    def test_exact_capsule(self):
        raw = ENTRY._capsule()
        self.assertEqual(len(raw), ENTRY.HELPER_BYTES)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ENTRY.HELPER_SHA256)
        self.assertEqual(raw, (HERE/'provider_driver_bootstrap.py').read_bytes())

    def test_import_and_default_cli_inert(self):
        with mock.patch.object(ENTRY, '_load_helper', side_effect=AssertionError('helper must not load')), \
             mock.patch.object(ENTRY.subprocess, 'run', side_effect=AssertionError('no process')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            ENTRY.main([])
        result = json.loads(output.getvalue())
        self.assertEqual(result['state'], 'PRE_STORAGE_ENTRY_PREPARED_EXECUTION_DISABLED')
        self.assertEqual(result['storage_network_allocation_or_model_actions'], 0)

    def test_expired_scope_before_any_work(self):
        scope = self.scope(); scope['allocation_started_at'] -= 200; scope['original_deadline_epoch'] -= 200
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ENTRY, '_load_helper', side_effect=AssertionError('expired')):
            output = Path(tmp)/'untouched'
            with self.assertRaises(PermissionError): ENTRY.run(scope, output)
            self.assertFalse(output.exists())

    def test_false_guard_and_unapproved_fail_before_work(self):
        for key in ['approved', 'shutdown_guard_armed']:
            scope = self.scope(); scope[key] = False
            with self.assertRaises(PermissionError): ENTRY._scope(scope)

    def test_mock_forward_before_storage_and_no_model(self):
        order = []
        class FakeHelper:
            def resolve_provider_driver(self):
                order.append('resolve')
                return {'library': {'path': '/SOURCE_MOCK_ONLY/libcuda.so.1', 'bytes': 1, 'sha256': '0'*64}}
            def install_preload(self, binding, site, evidence):
                order.append('install_preload')
                self.assert_site = site
                if not site.is_dir(): raise AssertionError('owned site required')
                (site/'sitecustomize.py').write_text('# SOURCE_MOCK_ONLY\n')
                target=site/'sitecustomize.py'
                return {'bootstrap':{'path':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}}
        class FakeBuilder:
            def __init__(self, **kwargs):
                if kwargs != {'with_pip': False, 'symlinks': False}: raise AssertionError(kwargs)
            def create(self, destination):
                order.append('owned_venv')
                (destination/'lib/python3.12/site-packages').mkdir(parents=True)
                (destination/'bin').mkdir()
                (destination/'bin/python').write_text('SOURCE_MOCK_ONLY')
        def probe(python, timeout, *, library, bootstrap):
            order.append('fresh_minimalenv_lookup')
            self.assertGreater(timeout, 0)
            return type('Receipt', (), {'stdout': '{"state":"EXACT_PROVIDER_BOOTSTRAP_LOADED_BEFORE_LOOKUP"}\n{"state":"FRESH_MINIMALENV_DRIVER_LOOKUP_PASS"}', 'stderr': '', 'returncode':0})()
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(ENTRY, '_runtime_supported', return_value=True), \
             mock.patch.object(ENTRY, '_load_helper', return_value=FakeHelper()), \
             mock.patch.object(ENTRY.venv, 'EnvBuilder', FakeBuilder), \
             mock.patch.object(ENTRY, '_fresh_probe', side_effect=probe), \
             contextlib.redirect_stdout(io.StringIO()):
            result = ENTRY.run(self.scope(), Path(tmp)/'source_mock_only')
        self.assertEqual(order, ['resolve', 'owned_venv', 'install_preload', 'fresh_minimalenv_lookup'])
        self.assertEqual(result['state'], 'FRESH_MINIMALENV_DRIVER_LOOKUP_PASS_NOT_TORCH_OR_TTS_QUALIFICATION')
        for key in ['storage_connection_attempts', 'network_requests', 'Torch_imports', 'TTS_model_loads', 'training_updates', 'GPU_allocations_created_by_entry']:
            self.assertEqual(result[key], 0)
        self.assertFalse(result['CUDA_compute_qualified'])

    def test_fresh_child_exact_stripped_env_and_no_skip_site(self):
        completed = type('Receipt', (), {'stdout': '', 'stderr': ''})()
        with mock.patch.object(ENTRY.subprocess, 'run', return_value=completed) as run:
            ENTRY._fresh_probe(Path('/SOURCE_MOCK_ONLY/python'), 12,
                library={'path':'/SOURCE_MOCK_ONLY/libcuda.so.1','bytes':1,'sha256':'0'*64},
                bootstrap={'path':'/SOURCE_MOCK_ONLY/sitecustomize.py','bytes':1,'sha256':'0'*64})
        args, kwargs = run.call_args
        self.assertEqual(args[0][1:4], ['-I', '-B', '-c'])
        self.assertNotIn('-S', args[0])
        self.assertIn("ctypes.CDLL('libcuda.so.1')",args[0][4])
        self.assertIn('load_exact_preload',args[0][4])
        self.assertEqual(kwargs['env'], ENTRY.MINIMAL_ENV)
        self.assertNotIn('LD_LIBRARY_PATH', kwargs['env'])
        self.assertFalse(any('TOKEN' in key or 'KEY' in key for key in kwargs['env']))


if __name__ == '__main__': unittest.main()
