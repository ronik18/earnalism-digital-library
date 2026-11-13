"""Build a source-bound warm-shot notebook; default Run all performs no work.

The input job is the separate batch contract. This builder never creates owner
authority, starts an allocation, uploads files, downloads models or runs a GPU.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import io
import json
import zipfile

_spec = importlib.util.spec_from_file_location('earnalism_batch_builder_subject', Path(__file__).with_name('batch.py'))
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)


def _gated(flag, body, prerequisite=None):
    lines = [f'if not {flag}:', f" print('{flag}_DISABLED')", 'else:']
    if prerequisite:
        lines.extend(' ' + line for line in prerequisite.splitlines())
    lines.extend(' ' + line for line in body.splitlines())
    return '\n'.join(lines) + '\n'


def build(destination, job_path, art):
    """Prepare a new notebook bundle from an exact job and its bound images."""
    destination, job_path, art = Path(destination), Path(job_path), Path(art)
    raw = job_path.read_bytes()
    job = b.validate(json.loads(raw))
    sources = {}
    for scene in job['scenes']:
        value = (art / scene['image']).read_bytes()
        if hashlib.sha256(value).hexdigest() != scene['image_sha256']:
            raise ValueError('Changed source illustration')
        sources[scene['image']] = value
    if len(raw) + sum(map(len, sources.values())) > 256 * 1024**2:
        raise ValueError('Input bundle exceeds the batch unpacked-size allowance')
    pack = io.BytesIO()
    with zipfile.ZipFile(pack, 'w', compression=zipfile.ZIP_STORED) as z:
        z.writestr('job.json', raw)
        for name, value in sorted(sources.items()):
            z.writestr('inputs/' + name, value)
    archive = pack.getvalue()
    archive_sha = hashlib.sha256(archive).hexdigest()
    job_sha = hashlib.sha256(raw).hexdigest()
    software = {name: Path(__file__).with_name(name).read_bytes() for name in ['worker.py', 'batch.py']}
    hashes = {name: hashlib.sha256(value).hexdigest() for name, value in software.items()}
    runtime_root = '/content/earnalism-' + job['run_id']
    config = '''# Every action is independently disabled. Supply existing exact-job authority;
# this notebook neither creates approval nor infers it from previous pilots.
RUN_BATCH = False
VERIFY_INPUTS = False
BEGIN_ALLOCATION = False
SETUP_BATCH = False
GENERATE_BATCH = False
RESUME_UNATTEMPTED = False
EXPORT_AND_DOWNLOAD = False
LOCAL_IMPORT_VERIFIED = False
DISCONNECT_RUNTIME = False
AUTHORITY_PATH = '/content/wan22-batch-authority.json'
'''
    bootstrap = _gated('RUN_BATCH', f'''import base64, hashlib, importlib.util, json, pathlib, threading, time
ROOT = pathlib.Path({runtime_root!r})
payloads = {{
 'worker.py': base64.b64decode({base64.b64encode(software['worker.py']).decode()!r}),
 'batch.py': base64.b64decode({base64.b64encode(software['batch.py']).decode()!r}),
 'job.json': {raw!r},
}}
expected = {dict(hashes, **{'job.json': job_sha})!r}
BOUND_SOFTWARE_SHA256 = {{name:expected[name] for name in ['worker.py','batch.py']}}
# Check the entire existing control set before writing anything.
for name, value in payloads.items():
 if hashlib.sha256(value).hexdigest() != expected[name]: raise RuntimeError('Bound software/job changed')
 p = ROOT/name
 if p.exists() and p.read_bytes() != value: raise RuntimeError('Preserve existing software/job: '+name)
ROOT.mkdir(parents=True, exist_ok=True)
for name, value in payloads.items():
 if not (ROOT/name).exists(): (ROOT/name).write_bytes(value)
spec = importlib.util.spec_from_file_location('earnalism_warm_batch', ROOT/'batch.py')
batch = importlib.util.module_from_spec(spec); spec.loader.exec_module(batch)
print('Bound software prepared; no authority, setup or inference started')''')
    prepared = "if not (RUN_BATCH and 'batch' in globals()): raise RuntimeError('Prepare bound software first')"
    verified = prepared + "\nif globals().get('INPUTS_VERIFIED_JOB_SHA256') != batch.w.sha(ROOT/'job.json'): raise RuntimeError('Verify the complete source-bound input pack first')"
    ready = verified + "\nif not globals().get('PREFLIGHT_OK',False): raise RuntimeError('Successful actual allocation/hardware preflight required')\nif not globals().get('BOUND_SOFTWARE_SHA256') or any(batch.w.sha(ROOT/name) != digest for name,digest in BOUND_SOFTWARE_SHA256.items()): raise RuntimeError('Bound software changed; preserve and inspect')\nbatch.open_job(ROOT); batch.remaining(ROOT)"
    verify = _gated('VERIFY_INPUTS', f'''path = pathlib.Path('/content/wan22-batch-inputs.zip')
if not path.is_file(): raise RuntimeError('Upload the input ZIP using Colab Files and await transfer')
batch.unpack_inputs(path, ROOT, {archive_sha!r})
INPUTS_VERIFIED_JOB_SHA256 = batch.w.sha(ROOT/'job.json')
print('Exact input archive and every source hash verified; no compute started')''', prepared)
    begin = _gated('BEGIN_ALLOCATION', '''from google.colab import runtime
PREFLIGHT_OK = False
try:
 if not (RUN_BATCH and 'batch' in globals()): raise RuntimeError('Prepare bound software first')
 if globals().get('INPUTS_VERIFIED_JOB_SHA256') != batch.w.sha(ROOT/'job.json'): raise RuntimeError('Verify the complete source-bound input pack first')
 authority_path = pathlib.Path(AUTHORITY_PATH)
 if not authority_path.is_file(): raise RuntimeError('Supply the separately authorized exact-job authority JSON; do not reuse pilot allowance')
 authority = json.loads(authority_path.read_text())
 session = batch.begin(ROOT, authority)
 guard_key = (session['job_sha256'],session['deadline'])
 if 'wan_batch_guard' in globals():
  if wan_batch_guard_key != guard_key: raise RuntimeError('Preserve original runtime guard; no deadline renewal')
 else:
  wan_batch_guard_key = guard_key
  wan_batch_guard = threading.Timer(max(1,session['deadline']-time.time()),runtime.unassign)
  wan_batch_guard.daemon = True; wan_batch_guard.start()
 print(json.dumps(batch.preflight(ROOT),indent=2))
 PREFLIGHT_OK = True
except BaseException:
 try:
  if RUN_BATCH and 'batch' in globals() and 'ROOT' in globals(): batch.export(ROOT)
 finally: runtime.unassign()
 raise''')
    setup = _gated('SETUP_BATCH', '''try:
 # The shared installer creates ROOT/venv and installs only the pinned route.
 batch.setup(ROOT)
finally:
 batch.export(ROOT)
print((ROOT/'setup.json').read_text())''', ready)
    generate = _gated('GENERATE_BATCH', '''import os, signal, subprocess
python = ROOT/'venv/bin/python'
if not python.is_file(): raise RuntimeError('Complete isolated setup first')
command = [str(python),str(ROOT/'batch.py'),'run',str(ROOT),'--execute']
if RESUME_UNATTEMPTED: command.append('--resume')
process = None
try:
 # One warm process, one pipeline; time is from the ORIGINAL allocation.
 timeout = batch.remaining(ROOT)
 with (ROOT/'batch.log').open('a') as log:
  process = subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,
      env={**os.environ,'PYTHONUNBUFFERED':'1','USE_TF':'0','USE_FLAX':'0'},start_new_session=True)
  result = process.wait(timeout=timeout)
  if result: raise RuntimeError('Warm batch stopped; inspect durable journal and export; no automatic retry')
finally:
 try:
  if process is not None and process.poll() is None:
   os.killpg(process.pid,signal.SIGTERM)
   try: process.wait(timeout=5)
   except subprocess.TimeoutExpired:
    os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=5)
 finally:
  batch.export(ROOT)
print('Private technical output only; GPU batch performance and motion quality remain UNQUALIFIED')''', ready)
    status = '''if RUN_BATCH and 'ROOT' in globals():
 for name in ['session.json','preflight.json','setup.json','model-loads.json','attempts.json','export-receipt.json']:
  p = ROOT/name
  print(name,p.read_text() if p.exists() else 'NOT CREATED')
else: print('BATCH_NOT_STARTED')
'''
    download = _gated('EXPORT_AND_DOWNLOAD', '''from google.colab import files
archive = batch.export(ROOT)
print((ROOT/'export-receipt.json').read_text())
files.download(str(archive))''', prepared)
    shutdown = _gated('DISCONNECT_RUNTIME', '''if not LOCAL_IMPORT_VERIFIED: raise RuntimeError('Verify normal downloaded ZIP/member hashes locally before voluntary disconnect')
from google.colab import runtime
runtime.unassign()''', prepared)
    intro = f'''# Earnalism · private warm Wan2.2 shot queue

**PREPARED, NOT RUN · GPU BATCH PATH UNQUALIFIED**

Exact job `{job['run_id']}` · SHA256 `{job_sha}`. Model `{b.w.MODEL}` at revision `{b.w.REVISION}`. {len(job['scenes'])} individually named, seeded, source-bound shot(s); at most {job['max_attempts']} starts and {job['max_output_seconds']:.6f} seconds of reserved output within the original {job['wall_seconds']}-second allocation. Original narration and score are not inputs and are untouched. No Drive mount, public upload or purchases.

1. Safe **Run all** leaves every operation disabled. First review the exact job, sources, profile and retained prior evidence. This separate contract expands no old pilot or retry authority. Upload the accompanying `wan22-batch-inputs.zip` through normal Colab Files; its SHA256 is `{archive_sha}`. Enable software preparation, then input verification independently.
2. Supply a separately owner-authorized `wan22-batch-authority.json` for this exact job and actual allocation. It must record the actual original allocation-start timestamp, observed rate, finite approved compute allowance and approval evidence. The notebook does not create this record. Free access must be actually verified; metered access needs the batch validator's bounded allowance and twice-rate headroom. No billing setup. The shutdown timer is not a provider-enforced compute-unit cap.
3. Enable begin/preflight only after checking the actual allocation. The original deadline includes startup, setup, all inference, decode and export. Failed hardware/rate/authority checks stop before model setup. The standard conservative hardware floors remain 23,000 MiB VRAM, 28 GiB RAM and 55 GiB free disk; no auto-upgrade. Setup uses an isolated venv and the existing exact pinned model/dependency route.
4. Enable one warm run after setup. One supervised `venv/bin/python` process reuses one loaded pipeline sequentially. Never run this concurrently with another GPU job. Its shared GPU lock spans job roots. Each STARTED attempt is journaled before inference and exported after success or failure. A failed/started shot is never silently retried. Explicit resume may only skip completed shots and continue unattempted shots within the same original authority, deadline and remaining envelope.
5. Export through the normal download, then verify locally with `batch.py import DEST --archive ZIP --sha256 SHA --job ORIGINAL_JOB`. A download click is not durable delivery. Do a small transfer check before costly generation where the browser previously rejected saves. Stop at a policy rejection; do not bypass it. Review actual motion, figure/face edges, identity, action completion and both framings; technical decode does not certify art or audio. No speed, cost or quality improvement is claimed without a fresh metered test.
6. Disconnect this runtime after verified local import. The original automatic unassign guard remains active even on failed setup/generation. Do not reset its clock, duplicate the run or touch unrelated notebooks. Restore flags to False in any saved copy.

Shot profiles: {', '.join(s['id']+' · '+s['profile']+' · '+str(s['width'])+'×'+str(s['height']) for s in job['scenes'])}.
'''
    parts = [('markdown', intro), ('code', config), ('markdown', '## Prepare bound software only'),
             ('code', bootstrap), ('markdown', '## Verify uploaded sources before allocation authority'),
             ('code', verify), ('markdown', '## Bind supplied authority and actual hardware preflight'),
             ('code', begin), ('markdown', '## Explicit isolated setup'), ('code', setup),
             ('markdown', '## One supervised warm subprocess'), ('code', generate),
             ('markdown', '## Status and durable journal'), ('code', status),
             ('markdown', '## Export, download and verify local import'), ('code', download),
             ('markdown', '## Disconnect this runtime'), ('code', shutdown)]
    cells = []
    for index, (kind, text) in enumerate(parts):
        cell = {'id': f'wan-batch-{index:02}', 'cell_type': kind, 'metadata': {},
                'source': text.splitlines(keepends=True)}
        if kind == 'code': cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    notebook = {'nbformat': 4, 'nbformat_minor': 5,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3'},
                             'language_info': {'name': 'python'},
                             'colab': {'name': 'Earnalism_Wan22_Warm_Batch.ipynb'}}, 'cells': cells}
    nb_raw = (json.dumps(notebook, indent=1, ensure_ascii=False)+'\n').encode()
    manifest = {'schema': 'earnalism.wan22-batch-build.v1', 'job_sha256': job_sha,
                'inputs_sha256': archive_sha, 'notebook_sha256': hashlib.sha256(nb_raw).hexdigest(),
                'software_sha256': hashes, 'private': True, 'publication_approved': False,
                'authority_created': False, 'gpu_execution_qualification': 'UNQUALIFIED'}
    outputs = {'job.json': raw, 'wan22-batch-inputs.zip': archive,
               'Earnalism_Wan22_Warm_Batch.ipynb': nb_raw,
               'build-manifest.json': (json.dumps(manifest, indent=2)+'\n').encode()}
    # Never replace any previous prepared job, notebook, archive or receipt.
    if destination.exists() and any((destination/name).exists() for name in outputs):
        raise FileExistsError('Preserve the existing prepared batch bundle')
    destination.mkdir(parents=True, exist_ok=True)
    for name, value in outputs.items():
        with (destination/name).open('xb') as f: f.write(value)
    return destination/'Earnalism_Wan22_Warm_Batch.ipynb'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination', type=Path)
    p.add_argument('--job', required=True, type=Path)
    p.add_argument('--art', required=True, type=Path)
    a = p.parse_args()
    print(build(a.destination, a.job, a.art))
