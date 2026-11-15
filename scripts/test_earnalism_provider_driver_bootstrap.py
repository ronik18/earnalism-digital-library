"""CPU-only shared-library bootstrap contracts; never CUDA qualification."""
import _ctypes
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
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
    def test_actual_cpu_shared_library_automatic_startup_and_hash_fail_closed(self):
        # _ctypes is an actual existing CPU shared library; no libcuda, torch,
        # model, package installation, network, GPU runtime or inference is used.
        path=Path(_ctypes.__file__).resolve()
        descriptor={'path':str(path),'bytes':path.stat().st_size,'sha256':b.sha(path)}
        with tempfile.TemporaryDirectory() as raw:
            venv=Path(raw)/'owned-venv'
            subprocess.run([sys.executable,'-m','venv','--without-pip',str(venv)],env=ENV,check=True,capture_output=True,timeout=30)
            site=venv/'lib'/('python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor))/'site-packages'
            target=site/'sitecustomize.py';target.write_text(b.render_preload_source(descriptor))
            python=venv/'bin/python'
            command=[str(python),'-B','-c',"import sys,sitecustomize;assert 'LD_LIBRARY_PATH' not in __import__('os').environ;assert sitecustomize._EARNALISM_PROVIDER_DRIVER;print('CPU_FIXTURE_STARTUP_VERIFIED_NOT_GPU_QUALIFIED')"]
            good=subprocess.run(command,env=ENV,capture_output=True,text=True,timeout=15)
            self.assertEqual(good.returncode,0,good.stderr)
            self.assertIn('CPU_FIXTURE_STARTUP_VERIFIED_NOT_GPU_QUALIFIED',good.stdout)
            changed={**descriptor,'sha256':'0'*64};target.write_text(b.render_preload_source(changed))
            bad=subprocess.run(command,env=ENV,capture_output=True,text=True,timeout=15)
            self.assertEqual(bad.returncode,73)
            self.assertEqual(bad.stdout,'')
            self.assertIn('EARNALISM_EXACT_PROVIDER_DRIVER_PRELOAD_FAILED',bad.stderr)

if __name__=='__main__':unittest.main()
