"""CPU-only shared-library bootstrap contracts; never CUDA qualification."""
import _ctypes
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv as venv_module
from unittest import mock
from scripts.earnalism_voice_runtime import provider_driver_bootstrap as b

ENV={'PATH':__import__('os').defpath,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1',
     'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1'}

class BootstrapTests(unittest.TestCase):
    def test_mapping_parser_selects_cuda_not_cudart_or_deleted(self):
        text='''1-2 r-xp 0 00:1 1 /provider/driver/libcuda.so.580.82.07
2-3 r--p 0 00:1 1 /provider/driver/libcuda.so.580.82.07
3-4 r-xp 0 00:1 2 /provider/driver/libcudart.so.12
4-5 r-xp 0 00:1 3 /provider/old/libcuda.so.1 (deleted)
5-6 rw-p 0 00:0 0 [heap]
'''
        self.assertEqual(b.cuda_mapping_paths(text),['/provider/driver/libcuda.so.580.82.07'])
    def test_exact_descriptor_required(self):
        for bad in [dict(path='relative.so',bytes=1,sha256='0'*64),dict(path='/valid',bytes=True,sha256='0'*64),dict(path='/valid',bytes=1,sha256='x'*64)]:
            with self.assertRaises(ValueError):b.render_preload_source(bad)
    def test_existing_bootstrap_not_overwritten_before_library_touch(self):
        # A fixture is not an actual provider binding and cannot be installed as one.
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);site=root/'site';site.mkdir();sentinel=site/'sitecustomize.py';sentinel.write_text('preserve')
            with self.assertRaises(ValueError):b.install_preload({'library_family':'CPU_FIXTURE'},site,root/'evidence')
            self.assertEqual(sentinel.read_text(),'preserve')
    def test_actual_cpu_shared_library_explicit_startup_and_hash_fail_closed(self):
        # _ctypes is an actual existing CPU shared library; no libcuda, torch,
        # model, package installation, network, GPU runtime or inference is used.
        path=Path(_ctypes.__file__).resolve()
        descriptor={'path':str(path),'bytes':path.stat().st_size,'sha256':b.sha(path)}
        with tempfile.TemporaryDirectory() as raw:
            venv=Path(raw).resolve()/'owned-venv'
            venv_module.EnvBuilder(with_pip=False,symlinks=False).create(venv)
            site=venv/'lib'/('python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor))/'site-packages'
            target=site/'sitecustomize.py';target.write_text(b.render_preload_source(descriptor))
            python=venv/'bin/python'
            code="import importlib.util,json,sys; s=importlib.util.spec_from_file_location('_cpu_helper',sys.argv[1]);h=importlib.util.module_from_spec(s);s.loader.exec_module(h);p=json.loads(sys.argv[2]);owned=h.load_exact_preload(p['library'],p['bootstrap']);assert 'LD_LIBRARY_PATH' not in __import__('os').environ;assert owned._EARNALISM_PROVIDER_DRIVER;print('CPU_FIXTURE_STARTUP_VERIFIED_NOT_GPU_QUALIFIED')"
            def command(current):
                bootstrap={'path':str(target),'bytes':target.stat().st_size,'sha256':b.sha(target)}
                return [str(python),'-I','-B','-c',code,str(Path(b.__file__).resolve()),json.dumps({'library':current,'bootstrap':bootstrap})]
            good=subprocess.run(command(descriptor),env=ENV,capture_output=True,text=True,timeout=15)
            self.assertEqual(good.returncode,0,good.stderr)
            self.assertIn('CPU_FIXTURE_STARTUP_VERIFIED_NOT_GPU_QUALIFIED',good.stdout)
            changed={**descriptor,'sha256':'0'*64};target.write_text(b.render_preload_source(changed))
            bad=subprocess.run(command(changed),env=ENV,capture_output=True,text=True,timeout=15)
            self.assertEqual(bad.returncode,73)
            self.assertEqual(bad.stdout,'')
            self.assertIn('EARNALISM_EXACT_PROVIDER_DRIVER_PRELOAD_FAILED',bad.stderr)

    def test_explicit_loader_preserves_foreign_sitecustomize_and_refuses_other_source(self):
        path=Path(_ctypes.__file__).resolve()
        library={'path':str(path),'bytes':path.stat().st_size,'sha256':b.sha(path)}
        foreign=__import__('types').ModuleType('sitecustomize');foreign.__file__='/provider/base/sitecustomize.py'
        with tempfile.TemporaryDirectory() as raw,mock.patch.dict(sys.modules,{'sitecustomize':foreign}):
            target=Path(raw).resolve()/'sitecustomize.py';target.write_text(b.render_preload_source(library))
            bootstrap={'path':str(target),'bytes':target.stat().st_size,'sha256':b.sha(target)}
            owned=b.load_exact_preload(library,bootstrap)
            self.assertIs(sys.modules['sitecustomize'],foreign)
            self.assertEqual(owned._spec,library)
            self.assertEqual(owned._EARNALISM_PROVIDER_DRIVER._name,str(path))
            target.write_text(target.read_text()+'\n# unexpected bootstrap source\n')
            changed={**bootstrap,'bytes':target.stat().st_size,'sha256':b.sha(target)}
            with self.assertRaisesRegex(ValueError,'Exact fixed provider bootstrap source'):
                b.load_exact_preload(library,changed)

if __name__=='__main__':unittest.main()
