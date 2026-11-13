"""Private, source-bound Wan shot queue with one warm pipeline per invocation.

This separate contract grants no reuse of a legacy pilot's compute authority.
It performs no installation or model download. Real GPU execution is unqualified
until a newly authorized batch is run and reviewed. The caller must retain the
allocation's original provider shutdown guard; a deadline is not a billing cap.
After explicit setup, run with that runtime's venv/bin/python, not an unprepared
notebook kernel. The notebook should supervise that one warm process with the
same original allocation timeout and shutdown guard.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import os
import re
import subprocess
import time
import zipfile

# Standalone loading also supports the exported Colab worker without a package.
_spec = importlib.util.spec_from_file_location('earnalism_wan_worker', Path(__file__).with_name('worker.py'))
w = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w)

SCHEMA = 'earnalism.wan22-batch.v1'
AUTHORITY_SCHEMA = 'earnalism.wan22-batch-authority.v1'
MAX_SHOTS = 64
MAX_WALL_SECONDS = 2700
EXPORT_RESERVE = 120


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate(job):
    if job.get('schema') != SCHEMA or not re.fullmatch(r'[a-z0-9-]+', job.get('run_id', '')):
        raise ValueError('A distinct batch schema and safe run ID are required')
    if job.get('model') != w.MODEL or job.get('model_revision') != w.REVISION:
        raise ValueError('Unreviewed model or revision')
    if job.get('private') is not True or job.get('publication_approved') is not False:
        raise ValueError('Private batch only')
    if type(job.get('wall_seconds')) is not int or not 600 <= job['wall_seconds'] <= MAX_WALL_SECONDS:
        raise ValueError('Explicit bounded 600–2700 second allocation required')
    scenes = job.get('scenes')
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= MAX_SHOTS:
        raise ValueError('One to 64 explicitly named shots required')
    if type(job.get('max_attempts')) is not int or job['max_attempts'] != len(scenes):
        raise ValueError('Exactly one authorized start per named shot; no retries')
    if not isinstance(job.get('prior_attempt_evidence'), dict) or not job['prior_attempt_evidence']:
        raise ValueError('Retain applicable prior profile and quality evidence')
    ids = []
    seconds = 0
    for scene in scenes:
        if not isinstance(scene, dict) or not re.fullmatch(r'[a-z0-9-]+', scene.get('id', '')):
            raise ValueError('Unsafe shot ID')
        ids.append(scene['id'])
        image = scene.get('image')
        if not isinstance(image, str) or Path(image).name != image or image in ('', '.', '..'):
            raise ValueError('Source image must be a basename')
        if not re.fullmatch(r'[a-f0-9]{64}', scene.get('image_sha256', '')):
            raise ValueError('Missing source hash')
        profile = scene.get('profile')
        if profile not in w.PROFILES:
            raise ValueError('Unknown shot profile')
        shape = w.PROFILES[profile]
        for key in ('width', 'height', 'frames', 'fps'):
            if type(scene.get(key)) is not int or scene[key] != shape[key]:
                raise ValueError('Changed pinned shot dimensions, frames or fps')
        if (type(scene.get('inference_steps')) is not int or scene['inference_steps'] != shape['steps']
                or not _number(scene.get('guidance_scale')) or scene['guidance_scale'] != shape['guidance']):
            raise ValueError('Changed pinned sampling settings')
        if type(scene.get('seed')) is not int or not 0 <= scene['seed'] < 2**63:
            raise ValueError('Explicit integer seed required')
        if not isinstance(scene.get('prompt'), str) or not 10 < len(scene['prompt']) < 3000:
            raise ValueError('A source-specific motion direction is required')
        if 'last_image' in scene or 'end_image' in scene:
            raise ValueError('Pinned 5B does not enforce endpoint image conditioning')
        w.scene_negative_prompt(scene)
        seconds += scene['frames'] / scene['fps']
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate shot IDs')
    if not _number(job.get('max_output_seconds')) or abs(job['max_output_seconds'] - seconds) > 1e-6:
        raise ValueError('Output allowance must bind the exact named-shot reservation')
    return job


def open_job(root):
    root = Path(root)
    job = validate(json.loads((root / 'job.json').read_text()))
    for scene in job['scenes']:
        if w.sha(w.inside(root, 'inputs/' + scene['image'])) != scene['image_sha256']:
            raise ValueError('Changed source illustration')
    return job


def unpack_inputs(archive, root, expected_sha):
    """Verify a sealed image/job ZIP completely before writing its members."""
    archive, root = Path(archive), Path(root)
    if w.sha(archive) != expected_sha:
        raise ValueError('Input archive hash mismatch')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in z.infolist()) > 256 * 1024**2:
            raise ValueError('Invalid or oversized input bundle')
        job = validate(json.loads(z.read('job.json')))
        expected = {'job.json'} | {'inputs/' + s['image'] for s in job['scenes']}
        if set(names) != expected:
            raise ValueError('Unexpected input member; audio is not an I2V input')
        data = {}
        for info in z.infolist():
            target = w.inside(root, info.filename)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive symlink')
            value = z.read(info)
            if target.exists() and target.read_bytes() != value:
                raise ValueError('Preserve existing input/job')
            data[info.filename] = value
        for scene in job['scenes']:
            if w.hashlib.sha256(data['inputs/' + scene['image']]).hexdigest() != scene['image_sha256']:
                raise ValueError('Changed source illustration in bundle')
        for name, value in data.items():
            target = w.inside(root, name)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
    return open_job(root)


def _authority(authority, job, job_sha):
    if (authority.get('schema') != AUTHORITY_SCHEMA or authority.get('owner_authorized') is not True
            or authority.get('job_sha256') != job_sha
            or not isinstance(authority.get('evidence_ref'), str) or not authority['evidence_ref'].strip()):
        raise RuntimeError('Fresh, exact-batch owner authority evidence is required')
    rate = authority.get('observed_units_per_hour')
    allowance = authority.get('approved_compute_units')
    if not _number(rate) or not _number(allowance):
        raise RuntimeError('Actual rate and explicit compute allowance are required')
    free = authority.get('free_runtime_confirmed') is True and rate == 0 and allowance == 0
    metered = (authority.get('free_runtime_confirmed') is False and rate > 0 and 0 < allowance <= 5
               and 2 * rate * job['wall_seconds'] / 3600 <= allowance)
    if not (free or metered):
        raise RuntimeError('Actual free allocation or bounded metered authority is missing')
    return authority


def begin(root, authority, *, now=None):
    """Bind a newly inspected allocation; resuming never extends its deadline."""
    root = Path(root)
    job = open_job(root)
    job_sha = w.sha(root / 'job.json')
    _authority(authority, job, job_sha)
    now = time.time() if now is None else now
    started = authority.get('allocation_started_at')
    if not _number(started) or not now - job['wall_seconds'] < started <= now:
        raise RuntimeError('Actual original allocation start is missing or expired')
    auth_path, session_path = root / 'authorization.json', root / 'session.json'
    if session_path.exists():
        if not auth_path.exists() or json.loads(auth_path.read_text()) != authority:
            raise RuntimeError('Do not replace the current allocation authority')
        state = json.loads(session_path.read_text())
        if (state.get('job_sha256') != job_sha or state.get('authority_sha256') != w.sha(auth_path)
                or state.get('started') != started or state.get('deadline') != started + job['wall_seconds']):
            raise RuntimeError('Changed job or original allocation binding')
        if now >= state['deadline']:
            raise RuntimeError('Original deadline expired; do not restart it')
        return state
    if auth_path.exists() and json.loads(auth_path.read_text()) != authority:
        raise RuntimeError('Preserve the prior authorization')
    w.write(auth_path, authority)
    state = {'schema': 'earnalism.wan22-batch-session.v1', 'started': started,
             'deadline': started + job['wall_seconds'], 'job_sha256': job_sha,
             'authority_sha256': w.sha(auth_path), 'guard_is_provider_quota': False,
             'gpu_execution_qualification': 'UNQUALIFIED_BATCH_PATH'}
    w.write(session_path, state)
    return state


def remaining(root, reserve=EXPORT_RESERVE, *, now=None):
    root = Path(root)
    # Step callbacks check the small immutable control records, not every large
    # source image. Images are verified before loading and between shots.
    job = validate(json.loads((root / 'job.json').read_text()))
    state = json.loads((root / 'session.json').read_text())
    auth = json.loads((root / 'authorization.json').read_text())
    _authority(auth, job, w.sha(root / 'job.json'))
    if (state.get('job_sha256') != w.sha(root / 'job.json')
            or state.get('authority_sha256') != w.sha(root / 'authorization.json')
            or state.get('started') != auth.get('allocation_started_at')
            or state.get('deadline') != state.get('started', 0) + job['wall_seconds']):
        raise RuntimeError('Changed original session/job/authority binding')
    n = state['deadline'] - (time.time() if now is None else now) - reserve
    if n <= 0:
        raise RuntimeError('Original deadline reached; preserve output, do not extend')
    return n


def preflight(root):
    remaining(root)
    return w.inspect_hardware(Path(root))


def setup(root):
    """Explicit pinned setup for this schema, using this allocation's clock."""
    root = Path(root)
    open_job(root)
    remaining(root)
    if (root / 'setup.json').exists():
        existing = json.loads((root / 'setup.json').read_text())
        if (existing.get('model') == w.MODEL and existing.get('revision') == w.REVISION
                and existing.get('state') == 'SETUP_COMPLETED_NOT_INFERENCE_QUALIFIED'
                and (root / 'model/model_index.json').is_file()):
            return existing
        raise RuntimeError('Preserve and inspect existing incomplete or changed setup')
    preflight(root)
    def command(root, args, log):
        with (Path(root) / log).open('a') as f:
            subprocess.run([str(v) for v in args], stdout=f, stderr=subprocess.STDOUT,
                    check=True, timeout=remaining(root), env={**os.environ, 'USE_TF': '0',
                    'USE_FLAX': '0', 'PYTHONUNBUFFERED': '1'})
    try:
        w.install_model(root, run_command=command)
    finally:
        export(root)
    return json.loads((root / 'setup.json').read_text())


def _step_guard(root, steps, decode_reserve):
    previous, intervals = None, []
    def callback(pipe, step, timestep, kwargs):
        nonlocal previous
        now = time.monotonic()
        if previous is not None:
            intervals.append(now - previous)
        previous = now
        available = remaining(root)
        if step >= 2:
            steady = sum(intervals[-3:]) / len(intervals[-3:])
            if (steps - step - 1) * steady * 1.15 + decode_reserve > available:
                raise RuntimeError('Measured shot cannot fit the original deadline')
        return kwargs
    return callback


class WanBackend:
    """Production backend: existing local pinned weights, one pipeline load."""
    def __init__(self, root, job):
        root = Path(root)
        setup = json.loads((root / 'setup.json').read_text())
        if (setup.get('model') != w.MODEL or setup.get('revision') != w.REVISION
                or setup.get('state') != 'SETUP_COMPLETED_NOT_INFERENCE_QUALIFIED'):
            raise RuntimeError('Pinned setup evidence required; batch never downloads weights')
        from PIL import Image
        for scene in job['scenes']:
            with Image.open(root / 'inputs' / scene['image']) as image:
                image.verify()
        preflight(root)
        self.pipe = w.load_pipeline(root / 'model')

    def generate(self, scene, image, output, callback):
        w.render_scene(self.pipe, scene, image, output, w.PROFILES[scene['profile']], callback)

    def close(self):
        # The caller's original runtime guard remains responsible for release.
        self.pipe = None


def export(root):
    """Save every completed/partial shot and its immutable input binding locally."""
    root = Path(root)
    open_job(root)
    names = ['job.json', 'authorization.json', 'session.json', 'attempts.json',
             'model-loads.json', 'preflight.json', 'setup.json', 'dependencies.lock.txt',
             'setup.log', 'batch.log']
    files = [root / name for name in names if (root / name).is_file()]
    files += sorted((root / 'outputs').glob('*.mp4')) if (root / 'outputs').exists() else []
    manifest = {'schema': 'earnalism.wan22-batch-export.v1', 'job_sha256': w.sha(root / 'job.json'),
                'model': w.MODEL, 'model_revision': w.REVISION, 'private': True,
                'publication_approved': False, 'quality_acceptance': 'PENDING',
                'files': {str(p.relative_to(root)): w.sha(p) for p in files}}
    w.write(root / 'export-manifest.json', manifest)
    archive, temporary = root / 'wan22-batch-export.zip', root / 'wan22-batch-export.tmp.zip'
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in files + [root / 'export-manifest.json']:
            z.write(p, str(p.relative_to(root)))
    temporary.replace(archive)
    w.write(root / 'export-receipt.json', {'archive_sha256': w.sha(archive),
            'bytes': archive.stat().st_size, 'durable_local_import': 'PENDING'})
    return archive


def _ledger(root, job):
    path = Path(root) / 'attempts.json'
    rows = json.loads(path.read_text()) if path.exists() else []
    scenes = {s['id']: s for s in job['scenes']}
    if not isinstance(rows, list) or len(rows) > job['max_attempts']:
        raise RuntimeError('Invalid or exhausted attempt ledger')
    seen, seconds = set(), 0
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError('Invalid attempt row')
        scene = scenes.get(row.get('scene'))
        if (scene is None or row['scene'] in seen or row.get('source_sha256') != scene['image_sha256']
                or type(row.get('seed')) is not int or row['seed'] != scene['seed']
                or row.get('job_sha256') != w.sha(Path(root) / 'job.json')
                or not _number(row.get('started'))
                or not _number(row.get('reserved_seconds'))
                or row.get('reserved_seconds') != scene['frames'] / scene['fps']):
            raise RuntimeError('Changed or duplicated attempt/source reservation')
        if row.get('status') != 'STARTED' and (not _number(row.get('ended')) or row['ended'] < row['started']):
            raise RuntimeError('Invalid attempt clock')
        if ((row.get('status') == 'TECHNICAL_PASS_REVIEW_PENDING' and row.get('backend') != 'PINNED_WAN_LOCAL')
                or (row.get('status') == 'TEST_FIXTURE_NOT_MODEL_OUTPUT' and row.get('backend') != 'INJECTED_TEST_ONLY')):
            raise RuntimeError('Test fixture cannot become model-output evidence')
        seen.add(row['scene']); seconds += row['reserved_seconds']
        if row.get('status') in ('TECHNICAL_PASS_REVIEW_PENDING', 'TEST_FIXTURE_NOT_MODEL_OUTPUT'):
            output = w.inside(root, 'outputs/' + scene['id'] + '.mp4')
            if not output.is_file() or w.sha(output) != row.get('sha256'):
                raise RuntimeError('Completed output changed; do not regenerate it')
        elif row.get('status') not in ('STARTED', 'FAILED_NO_AUTOMATIC_RETRY', 'TEST_FIXTURE_NOT_MODEL_OUTPUT'):
            raise RuntimeError('Unknown attempt state')
    if seconds > job['max_output_seconds'] + 1e-6:
        raise RuntimeError('Reserved output allowance exceeded')
    return rows


def import_export(archive, destination, expected_archive_sha, job_path):
    """Import a normal private export; decoding never certifies motion quality."""
    archive, destination, job_path = Path(archive), Path(destination), Path(job_path)
    if w.sha(archive) != expected_archive_sha:
        raise ValueError('Export archive hash mismatch')
    job = validate(json.loads(job_path.read_text()))
    if destination.exists():
        raise FileExistsError('Preserve existing imports')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or sum(i.file_size for i in z.infolist()) > 1024**3:
            raise ValueError('Invalid export members or oversized archive')
        for info in z.infolist():
            w.inside(destination, info.filename)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive symlink')
        manifest = json.loads(z.read('export-manifest.json'))
        if (manifest.get('schema') != 'earnalism.wan22-batch-export.v1'
                or manifest.get('model') != w.MODEL or manifest.get('model_revision') != w.REVISION
                or manifest.get('job_sha256') != w.sha(job_path)
                or manifest.get('private') is not True or manifest.get('publication_approved') is not False
                or manifest.get('quality_acceptance') != 'PENDING'):
            raise ValueError('Export provenance mismatch')
        allowed = {'job.json', 'authorization.json', 'session.json', 'attempts.json', 'model-loads.json',
                   'preflight.json', 'setup.json', 'dependencies.lock.txt', 'setup.log', 'batch.log'}
        allowed |= {'outputs/' + s['id'] + '.mp4' for s in job['scenes']}
        if (not isinstance(manifest.get('files'), dict) or not set(manifest['files']).issubset(allowed)
                or set(names) != set(manifest['files']) | {'export-manifest.json'}):
            raise ValueError('Unbound export member')
        for name, expected in manifest['files'].items():
            if w.hashlib.sha256(z.read(name)).hexdigest() != expected:
                raise ValueError('Changed export member')
        if z.read('job.json') != job_path.read_bytes():
            raise ValueError('Changed exported job')
        # Validate source-bound authority and original clock without requiring
        # the allocation to remain live while its normal download is imported.
        authority = json.loads(z.read('authorization.json'))
        session = json.loads(z.read('session.json'))
        _authority(authority, job, w.sha(job_path))
        if (session.get('job_sha256') != w.sha(job_path)
                or session.get('authority_sha256') != w.hashlib.sha256(z.read('authorization.json')).hexdigest()
                or session.get('started') != authority.get('allocation_started_at')
                or not _number(session.get('started'))
                or session.get('deadline') != session['started'] + job['wall_seconds']):
            raise ValueError('Changed original allocation binding')
        destination.mkdir(parents=True)
        for name in names:
            target = w.inside(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
    rows = _ledger(destination, job)
    accepted, rejected = [], []
    for scene in job['scenes']:
        output = destination / 'outputs' / (scene['id'] + '.mp4')
        row = next((r for r in rows if r['scene'] == scene['id']), None)
        if not output.exists():
            continue
        if row is None or row['status'] != 'TECHNICAL_PASS_REVIEW_PENDING':
            rejected.append({'scene': scene['id'], 'reason': 'Not a completed pinned-model attempt'})
            continue
        try:
            w.probe_video(output, scene)
        except (ValueError, subprocess.SubprocessError) as e:
            rejected.append({'scene': scene['id'], 'reason': str(e)})
            continue
        accepted.append({'scene': scene['id'], 'file': str(output), 'sha256': w.sha(output),
                         'source_image_sha256': scene['image_sha256'], 'technical_verified': True,
                         'motion_accepted': False})
    w.write(destination / 'import-receipt.json', {'archive_sha256': expected_archive_sha,
            'clips': accepted, 'rejected': rejected, 'private': True, 'publication_approved': False,
            'quality_review': 'PENDING', 'batch_gpu_path_qualification': 'UNQUALIFIED'})
    return accepted


def run(root, *, resume=False, backend_factory=None, probe=None):
    """Execute never-attempted shots sequentially, loading one backend only.

    Injected backends are explicitly labelled TEST_FIXTURE_NOT_MODEL_OUTPUT and
    cannot produce a production technical-pass receipt. This seam tests control
    flow without pretending that a model, GPU or artistic review was exercised.
    """
    root = Path(root)
    job = open_job(root)
    remaining(root)
    test_backend = backend_factory is not None
    if probe is not None and not test_backend:
        raise ValueError('Probe injection is available only with an explicit test backend')
    with w.gpu_lock(), (root / 'generation.lock').open('a') as lock:
        w.fcntl.flock(lock, w.fcntl.LOCK_EX | w.fcntl.LOCK_NB)
        rows = _ledger(root, job)
        if rows and not resume:
            raise RuntimeError('Existing attempts require explicit resume; never retry spent shots')
        seen = {row['scene'] for row in rows}
        pending = [s for s in job['scenes'] if s['id'] not in seen]
        if not pending:
            return {'state': 'NO_UNATTEMPTED_SHOTS', 'held_shots': [r['scene'] for r in rows
                    if r['status'] != 'TECHNICAL_PASS_REVIEW_PENDING'], 'quality_review': 'PENDING'}
        factory = backend_factory or WanBackend
        backend = None
        loads_path = root / 'model-loads.json'
        loads = json.loads(loads_path.read_text()) if loads_path.exists() else []
        if not isinstance(loads, list) or len(loads) >= job['max_attempts']:
            raise RuntimeError('Model-load cap reached; inspect previous invocation')
        if loads and not resume:
            raise RuntimeError('Existing model-load history requires explicit resume')
        load = {'started': time.time(), 'status': 'STARTED',
                'backend': 'INJECTED_TEST_ONLY' if test_backend else 'PINNED_WAN_LOCAL',
                'model': w.MODEL, 'revision': w.REVISION}
        loads.append(load)
        try:
            # Reserve loading as part of the original clock, before any GPU work.
            first = pending[0]
            start_floor = 1200 if max(first['width'], first['height']) >= 1280 else 600
            if remaining(root) < start_floor:
                raise RuntimeError('Insufficient original deadline headroom before model load')
            w.write(loads_path, loads)
            backend = factory(root, job)
            remaining(root)
            load.update(status='LOADED', ended=time.time()); w.write(loads_path, loads)
            for scene in pending:
                # Recheck every source/job and original deadline between shots.
                open_job(root); remaining(root)
                if len(rows) >= job['max_attempts']:
                    raise RuntimeError('Attempt allowance exhausted')
                floor = 1200 if max(scene['width'], scene['height']) >= 1280 else 600
                completed = [r['ended'] - r['started'] for r in rows
                             if r.get('status') == 'TECHNICAL_PASS_REVIEW_PENDING']
                forecast = max(floor, max(completed, default=0) * 1.15)
                if remaining(root) < forecast:
                    raise RuntimeError('Insufficient original headroom for the next shot; no start spent')
                output = root / 'outputs' / (scene['id'] + '.mp4')
                if output.exists():
                    raise RuntimeError('Preserve unjournaled output; do not overwrite it')
                output.parent.mkdir(exist_ok=True)
                row = {'scene': scene['id'], 'status': 'STARTED', 'started': time.time(),
                       'reserved_seconds': scene['frames'] / scene['fps'], 'seed': scene['seed'],
                       'source_sha256': scene['image_sha256'], 'job_sha256': w.sha(root / 'job.json'),
                       'quality_review': 'PENDING', 'backend': load['backend']}
                rows.append(row); w.write(root / 'attempts.json', rows)
                try:
                    backend.generate(scene, root / 'inputs' / scene['image'], output,
                            _step_guard(root, scene['inference_steps'], 360 if max(scene['width'], scene['height']) >= 1280 else 180))
                    remaining(root)
                    result = (probe or w.probe_video)(output, scene)
                    row.update(status='TEST_FIXTURE_NOT_MODEL_OUTPUT' if test_backend else 'TECHNICAL_PASS_REVIEW_PENDING',
                               ended=time.time(), sha256=w.sha(output), probe=result)
                except BaseException as e:
                    row.update(status='FAILED_NO_AUTOMATIC_RETRY', ended=time.time(),
                               error=type(e).__name__ + ': ' + str(e))
                    raise
                finally:
                    w.write(root / 'attempts.json', rows)
                    export(root)
        except BaseException as e:
            if load['status'] == 'STARTED':
                load.update(status='FAILED_LOAD_NO_AUTOMATIC_RETRY', ended=time.time(),
                            error=type(e).__name__ + ': ' + str(e))
                w.write(loads_path, loads)
            raise
        finally:
            try:
                if backend is not None and hasattr(backend, 'close'):
                    backend.close()
            finally:
                export(root)
        return {'state': 'TECHNICAL_TEST_ONLY' if test_backend else 'GENERATED_REVIEW_PENDING',
                'new_shots': len(pending), 'held_shots': [r['scene'] for r in rows
                    if r['status'] != 'TECHNICAL_PASS_REVIEW_PENDING'], 'quality_review': 'PENDING'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['validate', 'unpack', 'begin', 'preflight', 'setup', 'run', 'export', 'import', 'status'])
    p.add_argument('root', type=Path)
    p.add_argument('--authority', type=Path)
    p.add_argument('--archive', type=Path)
    p.add_argument('--sha256')
    p.add_argument('--job', type=Path, help='Exact original job for normal export import')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--execute', action='store_true', help='Explicit opt-in; authority and original clock still required')
    a = p.parse_args()
    if a.action in ('setup', 'run') and not a.execute:
        print('BATCH_DISABLED: no pipeline, GPU, download, generation or write'); return
    if a.action == 'validate':
        result = open_job(a.root)
    elif a.action in ('unpack', 'import'):
        if a.archive is None or a.sha256 is None or (a.action == 'import' and a.job is None):
            p.error('unpack/import require --archive and --sha256; import also requires --job')
        result = (unpack_inputs(a.archive, a.root, a.sha256) if a.action == 'unpack' else
                  import_export(a.archive, a.root, a.sha256, a.job))
    elif a.action == 'begin':
        if a.authority is None:
            p.error('begin requires --authority')
        result = begin(a.root, json.loads(a.authority.read_text()))
    elif a.action == 'preflight':
        result = preflight(a.root)
    elif a.action == 'setup':
        result = setup(a.root)
    elif a.action == 'run':
        result = run(a.root, resume=a.resume)
    elif a.action == 'export':
        result = str(export(a.root))
    else:
        result = {'job': open_job(a.root), 'session': json.loads((a.root / 'session.json').read_text()),
                  'attempts': _ledger(a.root, open_job(a.root)), 'quality_review': 'PENDING'}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
