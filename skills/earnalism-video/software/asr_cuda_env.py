"""Expose an existing isolated Qwen CUDA runtime to a separate ASR child only."""
from pathlib import Path
import os

def cuda_asr_environment(qwen_venv,environ=None):
 root=Path(qwen_venv).resolve()
 libs=sorted(p.resolve() for p in (root/'lib').glob('python*/site-packages/nvidia/*/lib') if p.is_dir())
 if not any((p/'libcublas.so.12').is_file() for p in libs):
  raise ValueError('Existing isolated CUDA12 cuBLAS not found; do not regenerate speech or install an alternate provider')
 result=dict(os.environ if environ is None else environ)
 prior=[str(Path(p).resolve()) if Path(p).exists() else p for p in result.get('LD_LIBRARY_PATH','').split(':') if p]
 result['LD_LIBRARY_PATH']=':'.join(dict.fromkeys([*map(str,libs),*prior]))
 return result
