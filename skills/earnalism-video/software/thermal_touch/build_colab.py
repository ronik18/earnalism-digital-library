"""Build one isolated, disabled-by-default stock-B narration notebook/job.

No model execution, connection, spending or approval is performed by this builder.
"""
from pathlib import Path
import base64
import hashlib
import json
import sys

SOFTWARE = Path(__file__).resolve().parents[1]
PROJECT = SOFTWARE.parent
RUNTIME_ROOT = '/content/earnalism-thermal-touch-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(folder):
    folder = Path(folder).resolve()
    units = json.loads((folder / 'units.json').read_text())
    if len(units) != 6 or len({u['id'] for u in units}) != 6:
        raise ValueError('Exactly six unique complete thought groups expected')
    for unit in units:
        if not unit['text'].strip() or len(unit['text'].split()) > 65 or len(unit['text']) > 520:
            raise ValueError('Preserve original worker chunk limits')
    baseline_path = PROJECT / 'output/episodes/03-refraction/production-v1/baseline-job.json'
    baseline = json.loads(baseline_path.read_text())
    files = {name: (SOFTWARE / 'vendor' / name).read_text() for name in (
        'pipeline_core.py', 'owner_audio_policy.py', 'narration_layout.py',
        'notebook_runtime.py', 'qwen_worker.py')}
    files['asr_cuda_env.py'] = (SOFTWARE / 'asr_cuda_env.py').read_text()
    # Reviewed adapter: only isolated run/root/export names change. The original
    # worker, supported voice controls, bounded retries and validation stay intact.
    episode = (SOFTWARE / 'refraction/colab_episode.py').read_text()
    episode = episode.replace('earnalism-refraction-v1', 'earnalism-thermal-touch-v1')
    episode = episode.replace("'refraction-v1'", "'thermal-touch-v1'")
    episode = episode.replace('refraction-speech.zip', 'thermal-touch-speech.zip')
    episode = episode.replace('refraction-aligned.zip', 'thermal-touch-aligned.zip')
    episode = episode.replace('refraction-partial.zip', 'thermal-touch-partial.zip')
    files['episode.py'] = episode
    payload = {'software': files, 'units': units, 'baseline': baseline}
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    encoded = base64.b64encode(raw).decode()
    payload_sha = hashlib.sha256(raw).hexdigest()
    cell = f'''# Private episode 04. Safe Run All does not synthesize or authorize spending.
RUN_THERMAL_TOUCH = False
EXISTING_COMPUTE_ALLOWED = False
FREE_RUNTIME_CONFIRMED = False
if not RUN_THERMAL_TOUCH:
 print('THERMAL_TOUCH_DISABLED: connect/run only within the current owner-authorized allowance.')
else:
 if not (EXISTING_COMPUTE_ALLOWED or FREE_RUNTIME_CONFIRMED):
  raise RuntimeError('No compute authorization: leave disconnected until confirmed.')
 import pathlib,json,threading,subprocess,sys,time,hashlib,base64,os
 from google.colab import runtime
 ROOT=pathlib.Path({RUNTIME_ROOT!r});ROOT.mkdir(parents=True,exist_ok=True)
 raw=base64.b64decode({encoded!r})
 assert hashlib.sha256(raw).hexdigest()=={payload_sha!r}
 package=json.loads(raw)
 soft=ROOT/'software';soft.mkdir(exist_ok=True)
 for name,text in package['software'].items():
  p=soft/name
  if p.exists() and p.read_text()!=text:raise RuntimeError('Preserve existing software/attempts: '+name)
  if not p.exists():p.write_text(text)
 for name,value in [('units.json',package['units']),('baseline-job.json',package['baseline'])]:
  p=ROOT/name
  if p.exists() and json.loads(p.read_text())!=value:raise RuntimeError('Preserve existing job/attempts: '+name)
  if not p.exists():p.write_text(json.dumps(value,indent=2))
 pidfile=ROOT/'process.json'
 if pidfile.exists():
  old=json.loads(pidfile.read_text())
  try:os.kill(old['pid'],0)
  except ProcessLookupError:pass
  else:raise RuntimeError('Existing process still present; inspect status instead of duplicating it.')
 if 'thermal_touch_shutdown_guard' not in globals():
  thermal_touch_shutdown_guard=threading.Timer(1500,runtime.unassign)
  thermal_touch_shutdown_guard.daemon=True;thermal_touch_shutdown_guard.start()
 log=open(ROOT/'console.log','a')
 process=subprocess.Popen([sys.executable,str(soft/'episode.py')],stdout=log,stderr=subprocess.STDOUT)
 pidfile.write_text(json.dumps({{'pid':process.pid,'started':time.time(),'payload_sha256':{payload_sha!r},'guard_seconds':1500}}))
 print('THERMAL_TOUCH_STARTED',process.pid,'25-minute shutdown guard; no purchases; private only')
'''
    status = f'''from pathlib import Path
import json
ROOT=Path({RUNTIME_ROOT!r})
print('THERMAL_TOUCH_STATUS', (ROOT/'status.json').read_text() if (ROOT/'status.json').exists() else 'not started')
print('EXPORTS',[(p.name,p.stat().st_size) for p in ROOT.glob('*.zip')])
if (ROOT/'console.log').exists():print((ROOT/'console.log').read_text()[-1800:])
'''
    download = f'''from pathlib import Path
from google.colab import files
ROOT=Path({RUNTIME_ROOT!r})
archive=ROOT/'thermal-touch-aligned.zip'
if not archive.exists():raise RuntimeError('Aligned export not complete; inspect status. Preserve speech/partial exports without regenerating.')
files.download(str(archive))
'''
    notebook = {'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3'},
                     'language_info': {'name': 'python'}, 'accelerator': 'GPU'},
        'cells': [
            {'cell_type': 'markdown', 'metadata': {}, 'source': [
                '# Earnalism — Everyday Science 04: Thermal touch\n',
                'Private original stock-Ryan B narration. Separate runtime, files and logs.\n',
                'Default controls disable synthesis and authorize no metered use. Do not Run All.\n',
                'Original audiobook notebook remains unchanged. No publication, purchases or new speech provider.\n']},
            *[{'cell_type': 'code', 'metadata': {}, 'execution_count': None,
               'outputs': [], 'source': source.splitlines(True)} for source in (cell, status, download)]]}
    outputs = {'colab-launch.py': cell, 'colab-status.py': status,
               'Earnalism_Everyday_Science_04_Narration.ipynb': json.dumps(notebook, indent=2),
               'colab-payload.json': json.dumps({'payload_sha256': payload_sha,
                   'baseline_sha256': sha(baseline_path),
                   'worker_sha256': sha(SOFTWARE / 'vendor/qwen_worker.py'),
                   'units_sha256': sha(folder / 'units.json'),
                   'runtime_root': RUNTIME_ROOT, 'disabled_by_default': True,
                   'metered_authorization_default': False, 'guard_seconds': 1500}, indent=2)}
    for name, text in outputs.items():
        path = folder / name
        if path.exists() and path.read_text() != text:
            raise FileExistsError('Refusing to replace prepared software: ' + str(path))
        if not path.exists():
            path.write_text(text)
    print('Prepared disabled private notebook; payload SHA256', payload_sha)


if __name__ == '__main__':
    build(sys.argv[1])
