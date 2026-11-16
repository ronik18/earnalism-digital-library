"""Prepare an exact provider CUDA-driver preload for an owned Python venv.

Import is inert. resolve_provider_driver() is for a separately authorized actual
Linux provider runtime only; it loads the existing driver library, not a TTS
model, and supplies no new allocation/compute authority. No paths are guessed.
"""
from pathlib import Path
import ctypes
import hashlib
import json
import os
import sys
import types

_LOADED_PROVIDER_HANDLES=[]
EXPLICIT_MODE='EXPLICIT_FIXED_HASH_BOUND_BOOTSTRAP_V1'
OWNED_MODULE='_earnalism_provider_driver'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def cuda_mapping_paths(maps_text):
    """Pure parser: return absolute non-deleted libcuda.so mapping paths."""
    paths=set()
    for line in maps_text.splitlines():
        columns=line.split(None,5)
        if len(columns)!=6:continue
        path=columns[5]
        if not path.startswith('/') or path.endswith(' (deleted)'):continue
        name=Path(path).name
        if name=='libcuda.so' or name.startswith('libcuda.so.'):
            paths.add(path)
    return sorted(paths)


def resolve_provider_driver():
    """Resolve the provider's real library using its existing loader context.

    LD_LIBRARY_PATH is neither modified nor passed to any credential-stripped
    worker. Record only whether it was present, not its complete contents.
    """
    if sys.platform!='linux':raise RuntimeError('Actual Linux provider required')
    handle=ctypes.CDLL('libcuda.so.1',mode=ctypes.RTLD_GLOBAL)
    maps=Path('/proc/self/maps').read_text()
    aliases=cuda_mapping_paths(maps)
    resolved={str(Path(path).resolve(strict=True)) for path in aliases}
    if len(resolved)!=1:raise RuntimeError('Unique actual loaded provider libcuda mapping required')
    path=Path(next(iter(resolved)))
    if not path.is_absolute() or not path.is_file():raise RuntimeError('Actual ordinary provider driver file required')
    st=path.stat()
    library={'path':str(path),'bytes':st.st_size,'sha256':sha(path)}
    _LOADED_PROVIDER_HANDLES.append(handle)
    return {'schema':'earnalism.provider_driver_binding.v1',
            'state':'ACTUAL_PROVIDER_LIBRARY_RESOLVED_NOT_CUDA_QUALIFIED',
            'library_family':'CUDA_DRIVER','soname':'libcuda.so.1','library':library,
            'resolution':'Existing provider loader context, unique /proc/self/maps realpath',
            'mapped_aliases':aliases,'maps_sha256':hashlib.sha256(maps.encode()).hexdigest(),
            'provider_LD_LIBRARY_PATH_present':bool(os.environ.get('LD_LIBRARY_PATH')),
            'worker_environment_expanded':False,'TTS_model_loads':0,'CUDA_compute_probe_performed':False,
            'fresh_minimalenv_GPU_qualification':False}


def render_preload_source(library):
    """Render a generic hash-bound shared-library startup contract.

    The renderer alone does not establish that its input is a CUDA library. The
    installer below admits only actual provider-resolution records. CPU fixture
    tests may use this generic renderer without making any GPU claim.
    """
    if (set(library)!={'path','bytes','sha256'} or not Path(library['path']).is_absolute()
        or type(library['bytes']) is not int or library['bytes']<=0
        or not isinstance(library['sha256'],str) or len(library['sha256'])!=64
        or any(c not in '0123456789abcdef' for c in library['sha256'])):
        raise ValueError('Exact absolute shared-library descriptor required')
    literal=repr(json.dumps(library,sort_keys=True,separators=(',',':')))
    return '''# Owned Earnalism provider-driver bootstrap; no model/compute initialization.
import ctypes as _ctypes
import hashlib as _hashlib
import json as _json
import os as _os
from pathlib import Path as _Path
import sys as _sys
try:
    _spec=_json.loads('''+literal+''')
    _path=_Path(_spec['path'])
    if not _path.is_absolute() or str(_path.resolve(strict=True))!=_spec['path'] or not _path.is_file():
        raise ValueError('path')
    if _path.stat().st_size!=_spec['bytes']:
        raise ValueError('size')
    _h=_hashlib.sha256()
    with _path.open('rb') as _f:
        for _b in iter(lambda:_f.read(1048576),b''):
            _h.update(_b)
    if _h.hexdigest()!=_spec['sha256']:
        raise ValueError('sha256')
    _EARNALISM_PROVIDER_DRIVER=_ctypes.CDLL(str(_path),mode=_ctypes.RTLD_GLOBAL)
except BaseException as _error:
    _sys.stderr.write('EARNALISM_EXACT_PROVIDER_DRIVER_PRELOAD_FAILED:'+type(_error).__name__+':'+str(_error)[:400]+'\\n')
    _sys.stderr.flush()
    _os._exit(73)
'''


def load_exact_preload(library,bootstrap):
    """Explicitly execute only the fixed hash-bound renderer, before Torch.

    Automatic sitecustomize import can resolve a provider/base module first.
    Preserve that module; do not infer our preload from its name or presence.
    This function verifies exact source and library identity and retains the
    resulting handle in a unique module in THIS process.
    """
    expected=render_preload_source(library)
    render_preload_source(bootstrap)  # Exact ordinary descriptor validation.
    path=Path(bootstrap['path'])
    if (path.is_symlink() or str(path.resolve(strict=True))!=bootstrap['path']
            or not path.is_file() or path.stat().st_size!=bootstrap['bytes'] or sha(path)!=bootstrap['sha256']
            or path.read_text()!=expected):
        raise ValueError('Exact fixed provider bootstrap source required')
    existing=sys.modules.get(OWNED_MODULE)
    if existing is not None:
        if (getattr(existing,'__file__',None)!=str(path)
                or getattr(existing,'_EARNALISM_EXPLICIT_BOOTSTRAP_SHA256',None)!=bootstrap['sha256']
                or getattr(existing,'_spec',None)!=library
                or getattr(getattr(existing,'_EARNALISM_PROVIDER_DRIVER',None),'_name',None)!=library['path']):
            raise ValueError('Preserve foreign or changed owned provider module')
        return existing
    owned=types.ModuleType(OWNED_MODULE);owned.__file__=str(path)
    exec(compile(expected,str(path),'exec'),owned.__dict__)
    owned._EARNALISM_EXPLICIT_BOOTSTRAP_SHA256=bootstrap['sha256']
    sys.modules[OWNED_MODULE]=owned
    return owned


def install_preload(binding,venv_site,evidence_dir):
    """Install once; retain earlier bootstrap files rather than overwriting."""
    if (binding.get('schema')!='earnalism.provider_driver_binding.v1'
        or binding.get('state')!='ACTUAL_PROVIDER_LIBRARY_RESOLVED_NOT_CUDA_QUALIFIED'
        or binding.get('library_family')!='CUDA_DRIVER'
        or binding.get('soname')!='libcuda.so.1'
        or binding.get('fresh_minimalenv_GPU_qualification') is not False):
        raise ValueError('Actual provider driver binding required, never a GPU qualification')
    library=binding['library'];path=Path(library['path'])
    name=path.name
    if not (name=='libcuda.so' or name.startswith('libcuda.so.')):raise ValueError('Provider libcuda family required')
    if not path.is_file() or path.stat().st_size!=library['bytes'] or sha(path)!=library['sha256']:
        raise ValueError('Provider driver changed since actual resolution')
    site=Path(venv_site)
    if site.is_symlink() or not site.is_dir():raise ValueError('Existing owned venv site directory required')
    target=site/'sitecustomize.py'
    source=render_preload_source(library)
    compile(source,str(target),'exec')
    with target.open('x',encoding='utf-8') as f:
        f.write(source);f.flush();os.fsync(f.fileno())
    report={'schema':'earnalism.provider_driver_preload.v1',
            'state':'EXACT_PROVIDER_DRIVER_PRELOAD_INSTALLED_NOT_CUDA_QUALIFIED',
            'provider_binding':binding,
            'bootstrap':{'path':str(target),'bytes':target.stat().st_size,'sha256':sha(target)},
            'explicit_bootstrap_mode':EXPLICIT_MODE,'explicit_module_name':OWNED_MODULE,
            'credential_stripped_worker_env':'UNCHANGED',
            'frozen_phase_model_profile_data_scene_and_schedule_bytes':'UNCHANGED',
            'fresh_actual_minimalenv_GPU_probe':'REQUIRED_BEFORE_TRAIN_INTENT',
            'TTS_model_loads_training_or_GPU_allocations':0}
    write_new(Path(evidence_dir)/'PROVIDER-DRIVER-PRELOAD.json',report)
    return report
