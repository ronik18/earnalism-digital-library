"""Private driver lookup qualification before storage authentication.

Import and the default CLI are inert. The caller supplies fresh owner authority,
one original allocation clock and an already armed independent shutdown guard.
This entry never allocates, connects storage, downloads, imports Torch or trains.
"""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import types
import venv
import zlib

HELPER_BYTES = 6686
HELPER_SHA256 = 'd1cdf9474e6932ee5fe278b0c6ab2aba12eb8f08ca027a8d46cd4224cf04b9ec'
HELPER_ZLIB_B64 = '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'
MINIMAL_ENV = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
               'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
               'HF_HUB_DISABLE_TELEMETRY': '1'}


def _capsule():
    raw = zlib.decompress(base64.b64decode(HELPER_ZLIB_B64, validate=True))
    if len(raw) != HELPER_BYTES or hashlib.sha256(raw).hexdigest() != HELPER_SHA256:
        raise ValueError('EXACT_REVIEWED_HELPER_CAPSULE_REQUIRED')
    return raw


def _load_helper():
    module = types.ModuleType('_earnalism_exact_provider_driver_bootstrap')
    module.__file__ = '<sha256:' + HELPER_SHA256 + '>'
    exec(compile(_capsule(), module.__file__, 'exec'), module.__dict__)
    return module


def _runtime_supported():
    return sys.platform == 'linux' and platform.machine() == 'x86_64' and sys.version_info[:2] == (3, 12)


def _scope(scope):
    if scope.get('approved') is not True or scope.get('shutdown_guard_armed') is not True:
        raise PermissionError('FRESH_APPROVAL_AND_INDEPENDENT_ORIGINAL_DEADLINE_GUARD_REQUIRED')
    if not isinstance(scope.get('actual_scope_ref'), str) or not scope['actual_scope_ref']:
        raise PermissionError('ACTUAL_CURRENT_OWNER_SCOPE_REFERENCE_REQUIRED')
    keys = ['allocation_started_at', 'original_deadline_epoch', 'observed_units_per_hour', 'approved_compute_units']
    if any(type(scope.get(k)) not in (int, float) or not math.isfinite(scope[k]) for k in keys):
        raise ValueError('ACTUAL_FINITE_CLOCK_RATE_AND_CU_REQUIRED')
    start, end, rate, cap = (scope[k] for k in keys)
    if not start <= time.time() < end <= start + 2700 or not 0 < rate or not 0 < cap <= 3:
        raise PermissionError('ORIGINAL_SCOPE_EXPIRED_OR_OUTSIDE_LIMITS')
    if 2 * rate * (end - start) / 3600 > cap:
        raise PermissionError('CONSERVATIVE_ORIGINAL_WINDOW_CU_BOUND_EXCEEDED')
    if end - time.time() < 20:
        raise TimeoutError('INSUFFICIENT_TIME_FOR_LOOKUP_EXPORT_AND_SHUTDOWN')
    return end


def _write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def _fresh_probe(python, timeout):
    return subprocess.run([str(python), '-I', '-B', '-c',
        "import ctypes,json; ctypes.CDLL('libcuda.so.1'); print(json.dumps({'state':'FRESH_MINIMALENV_DRIVER_LOOKUP_PASS','Torch_or_TTS_imports':False}))"],
        env=dict(MINIMAL_ENV), stdin=subprocess.DEVNULL, capture_output=True,
        text=True, timeout=timeout, check=True)


def run(scope, output_dir):
    """One local prerequisite check; caller subsequently exports and unassigns.

    This can establish driver lookup only. It does not establish Torch/CUDA
    compute, a model load, training, speech quality or production readiness.
    """
    deadline = _scope(scope)
    if not _runtime_supported():
        raise RuntimeError('ACTUAL_LINUX_X86_64_CPYTHON312_REQUIRED')
    output = Path(output_dir).resolve()
    if not output.is_absolute() or output.exists():
        raise FileExistsError('FRESH_OWNED_OUTPUT_REQUIRED_NO_REPLAY')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    result = {'state': 'PRE_STORAGE_DRIVER_LOOKUP_STARTED',
              'original_deadline_epoch': deadline, 'helper_sha256': HELPER_SHA256,
              'storage_connection_attempts': 0, 'network_requests': 0,
              'Torch_imports': 0, 'TTS_model_loads': 0, 'training_updates': 0,
              'GPU_allocations_created_by_entry': 0, 'CUDA_compute_qualified': False,
              'production_ready': False, 'publication': False}
    _write(output / 'INTENT.json', {**result, 'actual_scope_ref': scope['actual_scope_ref']})
    try:
        helper = _load_helper()
        provider = helper.resolve_provider_driver()
        _write(output / 'PROVIDER-BINDING.json', provider)
        _scope(scope)
        owned_venv = output / 'python312-venv'
        venv.EnvBuilder(with_pip=False, symlinks=False).create(owned_venv)
        site = owned_venv / 'lib/python3.12/site-packages'
        helper.install_preload(provider, site, output)
        _scope(scope)
        probe = _fresh_probe(owned_venv / 'bin/python', min(20, deadline - time.time() - 10))
        # This exact output comes from the fresh child, not the parent library load.
        stdout = probe.stdout.strip()
        if json.loads(stdout).get('state') != 'FRESH_MINIMALENV_DRIVER_LOOKUP_PASS':
            raise ValueError('FRESH_CHILD_LOOKUP_RECEIPT_REQUIRED')
        result.update(state='FRESH_MINIMALENV_DRIVER_LOOKUP_PASS_NOT_TORCH_OR_TTS_QUALIFICATION',
                      child_stdout=stdout, child_stderr=probe.stderr,
                      library=provider['library'])
    except BaseException as error:
        result.update(state='PRE_STORAGE_DRIVER_LOOKUP_FAILED_NO_RETRY',
                      error_type=type(error).__name__, error=str(error)[:250])
        if isinstance(error, subprocess.CalledProcessError):
            result['child_stdout'] = (error.stdout or '')[-1000:]
            result['child_stderr'] = (error.stderr or '')[-1000:]
    finally:
        result['finished_epoch'] = time.time()
        receipt = output / 'RESULT.json'
        _write(receipt, result)
        # Bounded JSON makes the small actual receipt retainable in notebook output
        # before any interactive storage-authentication prompt is shown.
        summary = {key: result[key] for key in [
            'state', 'original_deadline_epoch', 'finished_epoch', 'helper_sha256',
            'storage_connection_attempts', 'network_requests', 'Torch_imports',
            'TTS_model_loads', 'training_updates', 'GPU_allocations_created_by_entry',
            'CUDA_compute_qualified', 'production_ready', 'publication']}
        summary['receipt_sha256'] = hashlib.sha256(receipt.read_bytes()).hexdigest()
        summary['receipt_bytes'] = receipt.stat().st_size
        if 'error_type' in result:
            summary['error_type'] = result['error_type']
            summary['error'] = result['error']
        encoded = json.dumps(summary, sort_keys=True, allow_nan=False)
        if len(encoded.encode()) > 2048:
            raise ValueError('BOUNDED_NOTEBOOK_RECEIPT_REQUIRED')
        print(encoded, flush=True)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--scope')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({'state': 'PRE_STORAGE_ENTRY_PREPARED_EXECUTION_DISABLED',
                          'helper_sha256': HELPER_SHA256, 'helper_bytes': len(_capsule()),
                          'storage_network_allocation_or_model_actions': 0}))
        return
    if not args.scope or not args.scope_sha256 or not args.output:
        parser.error('Execution requires exact scope file/hash and a fresh output path')
    raw = Path(args.scope).read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.scope_sha256:
        raise ValueError('EXACT_APPROVED_SCOPE_BYTES_REQUIRED')
    run(json.loads(raw), args.output)


if __name__ == '__main__':
    main()
