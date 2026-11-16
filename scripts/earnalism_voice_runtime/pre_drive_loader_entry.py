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

HELPER_BYTES = 8580
HELPER_SHA256 = '4c133509eb422598a626c006873c66e176e4961927e9187313dbbe35f5336cf7'
HELPER_ZLIB_B64 = 'eNqdWltz27YSftevQNIHUBOaTtok7ZEPH5RYqTWj2q4s5/RM6sFQJGTxmCJVgrStZPLfz+7iwots19M8eEQCWAB7+b7dZV6+fHleym1UShblTN5HccW2ZXGbJrJkHy+PxwdJmd7C720psyJK2KoocWZxl8uEne+qdZGzW5nfBoPBdLMtyoqliqW5LKuAlVIV2a0UVqDQsrwhziFBTOHeUSWzHYtqEFamX0EunKKOssEszev75jhlnVfpRrIiz3ZHLK0YHkixai3h4Kmq0vyamdNm6bKMyp3P8qKCXRaLi8GmSGTmw9kTpurtNkulglGWyzsWZVkRR1Va5IdxsdnWlbSHqXYBOy3YNqrWiqGSrmuplEyCwcuXLwerstjQGGzHUn37c3gcmN9xtdtKZZ/WkcKJ9vF/qsjt78JNUjv3Uy8eiNnZ+HhyLM7nZ5+nx5O5OBmfHs8mF+GXq8Hkj/PZ9ON0IX47O56E3D1+mv4BK07GFyfiw9nl6TH8PVtcLObjc/H5DR+c/ecUhmHN5QxWCRmVeZSlatM3FB8MBolcMbWOPLzmcDRg8G8dmqsEMPDju/fekF7fpdWarq/nBsVW5h4vl3zIIjC3Xov/0PJL0PgN+AmYERwiizbLJBqtglJGiffm9dtf3v38fugvOR+O1kG9TcBDPFqityplVZc5WwdreZ+k11JVcAZ91jswmhRgVTqFfxtltTTnxhdhc8Aj/Bug6+dVsLlJ0tLTDypclLX0yadEcUNPrSvSMn25e+7LPC4S8LyQ19Xq4Je9y6KZg6TebD06ir/y0zyBTcIffQVWFjdyZ/ZDL7wTeZSHn6JMyeHRKqDLePzPnOPTKqvV2hseFSpYqV0ee/AqzWReeEN7+7hOIrGJtls4kSCv9eBJiUreV0YL4LjnNXgy3FXJcmR1GS0hVtHz8yI/gEiRFcQh2BglBqpgRqgOhQC936pUhUpWxgfQtBlEP1rWbRwoiLYKXytv2Ggmhv02uQpxQE/xTotc+u+Gbkq6YnA/z8wcvgjfj+ICQCCvpZtDVjUzvry7aq/F4CdrqSoqK4XW8/ghmAhOSe9lnpi3zDN3HoLL7e2RRxvZ8pwAnzsb4XjIG3Vx3ALfdrZuxgPeUoRTZBAlid6h7eXoJlK/V9bOjyKrs/FczyB0tLO4goVRZtGR1QotmlaqwU+EVMBP1ABabkDiZsdiNv0wH8//K87HixNE71zCjWAioGq6SsFVctIpYiOrCkDZHYtLiY6eRtmBqsp0u5WJDqKivJFlwOYyLsqE0JzdrSWJA1C/g/gBslGwVMM3ng9hGc2jDwYhGth7DowJADiDbRZV4IGbF2gKoA4+KqNUSTbXxDEpy6L0+JjIhfXJRf5Vp3BirnW/Bp7IZKgRPPh4PJt1zPeG+8gndny+ABX9Ojv7MJ7p5ej72mH4IWwRHyqZrQ7xLR8SyFFgmKAB7I2UVOEjwWudgeyZhN9AmV7LF82AhzqOKw1WQwpEHMdANPK/D1ohZcVBTL15UEuXefpXLQ0Ta7dIGm0ZVThU6GmvQdocr0kY73YcDgf9+EyVsPjjUXS2RxDjwLGfMCW4UZqjQ7vzmTQAl/bPpqrQYoI1gImH8BvHET5CDZNyfb7cVVLhG5gvFCQnPtekB+8sK2rFPsbTAagIcMbTHtWJ7G9cxWu5ifiIOw4OeiEtlsAXoOLgFnyuAxkcbyBh7fjj4nI8aza2sTqfXJzNPsORTs8WAnM58TvMm36aTo77oowGxCrapNkOZNL04/n082TO4coFYhm87oaAXcZHNt/qSiWT15hXwdKJhZjGiTpY47Nau1wvYAiyyC496eh7MhHGu/nI/PA5EY+1Ui9VwbGAOBt8atjOH3rSnRl64CcMNvHRsigyr0Bpt2kJJH8NLMh7s/mwL1ejnzCLNiBJyPst+AY46IiI3+eQrgpKVwVluHz02tcGMdkpwv4S/soS0a5Z2N1pBQddi02ap5sIQv5W/Hp+Kf6CeAHA1tmuWffdkUqOFzaZvlBFXcbSM6ZtMwtOg6z6WkKan8aU2B4sixoz6zVkUMmBJRgiv3pLJi4BSgyfLNbSbIZyMiB9lhSUjlcMbBEtIRDWwFyRBv80h0sj6URUkdhwDVCOhpIcFmUZCFvC0SGfTza4jpjFAJg150Hjk3AEJCAVsI/nlwAV9xCTWh6EPCzfRMiQyKCwtb2rOzYyegHH2kQ36NRIeKBfFmdRutkjJw8zJKvIFxZnLLo4SPluoY+g08z/oidfDbso6WwNS5CEmula6BUVWcSfecUKVxK58X+Hr9syaKYiTeZxS5o52pUPoEjQjOyxN4qp2du2ONCHF5vtGX/95sef3r57//Mv/4qWMbgaJ36KcWxfVCsz0pj/GRNng/gTqlBdstrzt0SqGDKNqtjj8ww5KMpCqHVLz+Xkyt6kn4ubsrQoVeiBfXzAL8tbBrs55z+wM6qCJxa7Gy8z/AMQUYHeou0RlpoU0q7ChLjE3Cj9SqEYdGtGLCLEg+UjjTxQStL7bk1Jr6C0fKxMpfF2vQo5FL3DIrQqd9oOQm1lHJLogODIg6u/Mvp8Bb+1WihhCUmcR0uc37bZXjxM90i4eujBbOZF2JFo3VX0MoQn3IYWupOIVgJged3tYcLjKWk4314b7vx4NSxataIthEWvEhbLfhksHqyDO+AuXFUsls21OvWwu5ANrCdvpOeYO03G81NIFC5+a3IKnQqEop0QO6sNdTIsHsqG5X0stxX7ANQ8oZ+p8VWJO1sXg+RdVRA4pS15myNM/oD8pn8QeJ5gviU+jaezyfGIvyIM1EKHgRCYrwjxCuL2FR1TD3wZvX39+uoV/xMr6r2tTX2t3wOxAzFDTfrzT8MBeLnhSGJGapNZnnQQ4oK9ocrJPZS1MdS+O6iwZIxhT6SERRkQDmBHizsttfjAYuAYki2KMl4byhzXVbEBpIiZAv3EtYJH8EIbznGU2woBWNLC0OEStI6wU2e4XwlZLAk7xxSmpOIQKFaPHwEFG7xeAXIB9zctP8QPJFRUKtXOlALFMjBsjt28Oo/JtAB7WBAq00vUSQR13SxIp1QVVjt6CWgaAemgRmyZU2eUJup8meoXmxmam8Crxcn0Aq8ZS9UrBSGZkjHUy+HT2YzZ7KEpjR0Z+4FpwnEVRothbgG8EwPe3aLHSdjDQM9CltptoES9aeDvKfTbk9fBggfLJdfi6KNcS5ZBOjqBrWU6Eyxy9LczZ3VV7IvQav0Z3K393hUBbjvrKj3itp2JEANVO4CiVLvdxHT6dX0Mk/tgQ2nU7tR4sDSqQN92ps8FqUwI7uNsuIwr/zr3Nnd/YH0bq0wDtum3XpyMUYdW9t9p9/FdEMydGOPGTy198qA9ODVyYQrVeb1dnBd3OWjfwA5XEL7S6xyPE0McX4PB9QcDZ3ZtSd6o2KRV9rT0ntaEmlR+owULRPmO5Y9oUmCN2DMeoq6HGRcGhXVSv1Xf4wQ+9K2QBMJOiGGze/Ac6z5q1ZbPfmmf+iok4e18Ur/QJGPqGccwpgXg43cWgfjvS9QiIDAcuGzoZqrXAcfEgOcaWpmMyiztBBpqCsrqiDpuQAGwOaA2Ei/2Gdpli+09UGlrehXgF8/rVrTLga4g6lugnH/SuXhUbK+HgfLbXYzHj6ObG8MXYbe98eiCZxTWrvjSrfynUHHcLVBt68rs6ODQZ7m8pbIby8zebp0ulln5xXVnro4aauqH9MC1twnUXWPb5OveP+ls215dFxp6nUNtpT7a95qCf8Nl/ZK2x2R7peVTZjjv6d/iFpTEsWuDthpappkIwagV62LTXQQf9qgeb2cH8IvTQ7pynTKNmSiZ1jBYAABWlHtqA0uAZ4Y46ZB3EsRgu9OOrNn1OVmRhUs9RmCp5Tu4bAocPfD8r2H2k5aW/bcftTQ+YoYbPqtXaq71RK/06WpienqxGM9mz2qZur1NvPGRhenuPIe7fNTuLzuVmg6z0WTXxbvNZrPke28DaYoM4Xai5iEfdb4O+808zUia6kdtWuoJbj7gCPsBRzTtS1Dm5enHk/Hpr/u6gYrhq8zFFqobaTqZoC5iaMiYI6FimUsBCb5Ao9JpjBqekomoqwOxD77UD4XF88nvl9M53OfD5NPZfCKAo6enYNXF5HTRl9drsgpQHAjNr0VRkszmPwVgA1b3+JuPyxTzHRY+5NarDrRXHRivCrB1wn3tx50ekn41+D89WAEq'
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


def _emit_notebook_evidence(output):
    """Print exact bounded receipt bytes before a caller can release the VM.

    The four fixed metadata files contain no model/audio/environment dump. The
    private notebook output is the storage-independent evidence carrier; this
    function makes no claim that Google Drive or another durable sink saved it.
    """
    envelope = {'schema': 'earnalism.pre_storage_notebook_evidence.v1',
                'runtime_or_CUDA_or_model_qualification': False, 'files': []}
    total = 0
    for name in ['INTENT.json', 'PROVIDER-BINDING.json',
                 'PROVIDER-DRIVER-PRELOAD.json', 'RESULT.json']:
        item = {'name': name}
        try:
            path = Path(output) / name
            if path.is_symlink() or not path.is_file():
                item['state'] = 'MISSING_OR_NOT_REGULAR'
            elif path.stat().st_size > 16384 or total + path.stat().st_size > 32768:
                item.update(state='OMITTED_EXCEEDS_BOUND', bytes=path.stat().st_size)
            else:
                with path.open('rb') as stream:
                    raw = stream.read(16385)
                if len(raw) > 16384 or total + len(raw) > 32768:
                    raise ValueError('Changed metadata exceeded notebook evidence bound')
                total += len(raw)
                item.update(state='EXACT_BYTES', bytes=len(raw),
                            sha256=hashlib.sha256(raw).hexdigest(),
                            base64=base64.b64encode(raw).decode('ascii'))
        except Exception as error:
            item.update(state='EVIDENCE_READ_FAILED', error_type=type(error).__name__)
        envelope['files'].append(item)
    print('EARNALISM_PRE_STORAGE_EVIDENCE=' +
          json.dumps(envelope, sort_keys=True, allow_nan=False), flush=True)


def _fresh_probe(python, timeout, *, library, bootstrap):
    # Execute the fixed exact bootstrap explicitly. Automatic sitecustomize can
    # be shadowed by the provider/base interpreter. Keep the original basename
    # lookup gate too; do not infer its success from an absolute loaded handle.
    code = """import base64,ctypes,hashlib,json,sys,types,zlib
expected=json.loads(sys.argv[1]); raw=zlib.decompress(base64.b64decode(sys.argv[2],validate=True))
""" + "if hashlib.sha256(raw).hexdigest() != " + repr(HELPER_SHA256) + ": raise RuntimeError('EXACT_HELPER_CAPSULE_REQUIRED')\n" + """helper=types.ModuleType('_earnalism_exact_child_provider_helper')
exec(compile(raw,'<exact-provider-helper>','exec'),helper.__dict__)
owned=helper.load_exact_preload(expected['library'],expected['bootstrap'])
baseline=sys.modules.get('sitecustomize')
metadata={'state':'EXACT_PROVIDER_BOOTSTRAP_LOADED_BEFORE_LOOKUP','bootstrap_sha256':expected['bootstrap']['sha256'],'bootstrap_file':owned.__file__,'library_path':owned._EARNALISM_PROVIDER_DRIVER._name,'baseline_sitecustomize_file':getattr(baseline,'__file__',None),'Torch_or_TTS_imports':False}
print(json.dumps(metadata),flush=True)
ctypes.CDLL('libcuda.so.1')
print(json.dumps({'state':'FRESH_MINIMALENV_DRIVER_LOOKUP_PASS','exact_bootstrap_verified':True,'basename_lookup_performed':True,'Torch_or_TTS_imports':False}),flush=True)
"""
    return subprocess.run([str(python), '-I', '-B', '-c',
        code,json.dumps({'library':library,'bootstrap':bootstrap},sort_keys=True),HELPER_ZLIB_B64],
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
    _write(output / 'INTENT.json', {**result, 'actual_scope_ref': scope['actual_scope_ref'],
        'driver_scope':{key:scope[key] for key in ['approved','actual_scope_ref','allocation_started_at',
            'original_deadline_epoch','observed_units_per_hour','approved_compute_units','shutdown_guard_armed']}})
    try:
        helper = _load_helper()
        provider = helper.resolve_provider_driver()
        _write(output / 'PROVIDER-BINDING.json', provider)
        _scope(scope)
        owned_venv = output / 'python312-venv'
        venv.EnvBuilder(with_pip=False, symlinks=False).create(owned_venv)
        site = owned_venv / 'lib/python3.12/site-packages'
        preload = helper.install_preload(provider, site, output)
        _scope(scope)
        probe = _fresh_probe(owned_venv / 'bin/python', min(20, deadline - time.time() - 10),
                             library=provider['library'],bootstrap=preload['bootstrap'])
        # Preserve completed-child diagnostics before parsing can reject an
        # unexpected final line/state. Such a rejection is not a lookup PASS.
        result.update(child_stdout=probe.stdout or '',child_stderr=probe.stderr or '',child_returncode=probe.returncode)
        # This exact output comes from the fresh child, not the parent library load.
        stdout = probe.stdout.strip()
        if not stdout or json.loads(stdout.splitlines()[-1]).get('state') != 'FRESH_MINIMALENV_DRIVER_LOOKUP_PASS':
            raise ValueError('FRESH_CHILD_LOOKUP_RECEIPT_REQUIRED')
        result.update(state='FRESH_MINIMALENV_DRIVER_LOOKUP_PASS_NOT_TORCH_OR_TTS_QUALIFICATION',
                      child_stdout=stdout, child_stderr=probe.stderr,
                      library=provider['library'])
    except BaseException as error:
        result.update(state='PRE_STORAGE_DRIVER_LOOKUP_FAILED_NO_RETRY',
                      error_type=type(error).__name__, error=str(error)[:250])
        if isinstance(error, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            for key, value in [('child_stdout', error.stdout), ('child_stderr', error.stderr)]:
                if isinstance(value, bytes):
                    value = value.decode('utf-8', errors='replace')
                value = value or ''
                result[key] = value[-1000:]
                result[key+'_original_characters'] = len(value)
                result[key+'_truncated'] = len(value) > 1000
            if isinstance(error, subprocess.CalledProcessError):
                result['child_returncode'] = error.returncode
    finally:
        result['finished_epoch'] = time.time()
        receipt = output / 'RESULT.json'
        _write(receipt, result)
        _emit_notebook_evidence(output)
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
