"""Attended, bounded Qwen narration; separate writable Colab roots only."""
import hashlib,json,os,pathlib,subprocess,sys,time,zipfile
ROOT=pathlib.Path('/content/earnalism-video')
def execute(episode_path,free_runtime_confirmed=False,budget_seconds=1200,run_id="private-test-v1",approved_compute_units=0.0,observed_units_per_hour=0.0,runtime_limit_seconds=1800):
 if not (0 < budget_seconds <= 1200 and budget_seconds <= runtime_limit_seconds <= 1800):raise RuntimeError('Bounded runtime allowance required')
 if not free_runtime_confirmed:
  if not (0 < approved_compute_units <= 5 and observed_units_per_hour > 0 and 2*observed_units_per_hour*runtime_limit_seconds/3600 <= approved_compute_units):
   raise RuntimeError('Free runtime or explicit bounded compute allowance required')
 started=time.monotonic()
 if not subprocess.run(['nvidia-smi','-L'],capture_output=True).returncode==0:raise RuntimeError('Free CUDA GPU unavailable; do not substitute another speech provider')
 from studio import prepare,make_job,write,sha
 sys.path.insert(0,str(pathlib.Path(__file__).parent/'vendor'))
 import notebook_runtime as runtime
 runtime.BASE_VENV_DIR=ROOT/'venvs'
 # Original runtime setup recipe, overridden cache path only; never share audiobook roots.
 def isolated_snapshot(python,repo,revision,output_file):
  code="from huggingface_hub import snapshot_download;import json,sys;from pathlib import Path;r=json.loads(sys.argv[1]);p=snapshot_download(repo_id=r['repo'],revision=r['revision'],cache_dir=r['cache']);Path(r['output']).write_text(json.dumps({'model_id':r['repo'],'model_revision':r['revision'],'model_path':p}))"
  if not revision:raise ValueError('Pinned revision required')
  pathlib.Path(output_file).parent.mkdir(parents=True,exist_ok=True)
  runtime.command([python,'-c',code,json.dumps({'repo':repo,'revision':revision,'cache':str(ROOT/'hf-cache'),'output':str(output_file)})]);return runtime.read_json(output_file)
 runtime.snapshot=isolated_snapshot
 # prepare() checksum is local only; this Colab package contains no original audiobook.
 import studio
 studio.verify_original=lambda: 'original verified locally; not present in Colab'
 import re
 if not re.fullmatch(r'[a-z0-9-]+',run_id):raise ValueError('Invalid run ID')
 folder=studio.BASE/'outputs'/run_id
 episode=studio.normalize_episode(json.loads(pathlib.Path(episode_path).read_text()))
 if folder.exists():
  if json.loads((folder/'episode.json').read_text())!=episode:raise ValueError('Changed episode: choose a new run ID; old attempts remain')
 else:
  prepared=prepare(episode_path);prepared.rename(folder)
 from audience_plan import validate_generation
 validate_generation(folder)
 (folder/'logs').mkdir(exist_ok=True)
 python,model=runtime.setup_qwen(folder)
 remaining=budget_seconds-(time.monotonic()-started)
 if remaining<60:raise RuntimeError('Setup consumed wall budget; stop and resume after inspection')
 job=make_job(folder,model);job_path=folder/'config/qwen-job.json'
 if job_path.exists():
  if json.loads(job_path.read_text())!=job:raise ValueError('Job configuration changed; inspect before resume')
 else:write(job_path,job)
 result=subprocess.run([python,str(pathlib.Path(__file__).parent/'vendor/qwen_worker.py'),str(job_path)],timeout=remaining)
 if result.returncode:raise RuntimeError('Qwen worker failed; inspect logs, do not skip failed narration')
 return folder

def align(folder,python,model_path,revision):
 """Independent local ASR with actual word timing; does not grant listening approval."""
 code=r'''
from faster_whisper import WhisperModel
from pathlib import Path
import json,sys,hashlib,difflib,re
folder=Path(sys.argv[1]);sys.path.insert(0,str(folder.parent.parent))
from asr_review import tokens,resolve_numeric
model=WhisperModel(sys.argv[2],device='cpu',compute_type='int8',local_files_only=True)
(folder/'alignment').mkdir(exist_ok=True)
ep=json.loads((folder/'episode.json').read_text());failures=[]
for s in ep['scenes']:
 wav=folder/'raw'/(s['id']+'.wav');segments,_=model.transcribe(str(wav),language='en',word_timestamps=True,vad_filter=False,condition_on_previous_text=False,beam_size=5)
 cues=[];recognized=[];word_times=[]
 for seg in segments:
  words=seg.words or []
  word_times.extend({'word':w.word.strip(),'start':w.start,'end':w.end} for w in words)
  for i in range(0,len(words),7):
   chunk=words[i:i+7];cues.append({'start':chunk[0].start,'end':chunk[-1].end,'text':''.join(w.word for w in chunk).strip()})
  recognized.append(seg.text)
 normalize=lambda x:re.findall(r"[a-z0-9]+",x.lower())
 ratio=difflib.SequenceMatcher(None,normalize(s['text']),normalize(' '.join(recognized))).ratio()
 edits=[{'tag':tag,'reference':normalize(s['text'])[a:b],'recognized':normalize(' '.join(recognized))[c:d]} for tag,a,b,c,d in difflib.SequenceMatcher(None,normalize(s['text']),normalize(' '.join(recognized))).get_opcodes() if tag!='equal']
 record={'word_times':word_times,'unresolved_asr_edits':edits,'audio_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'cues':cues,'recognized':' '.join(recognized),'similarity':ratio,'model_revision':sys.argv[3],'human_listening_required':True}
 if edits and tokens(record['recognized'])==tokens(s['text']):record=resolve_numeric(record,s['text'],wav)
 (folder/'alignment'/(s['id']+'.json')).write_text(json.dumps(record,indent=2))
 if record['unresolved_asr_edits']:failures.append(s['id'])
if failures:raise RuntimeError('ASR discrepancy; listen and resolve before release: '+','.join(failures))
'''
 result=subprocess.run([python,'-c',code,str(folder),str(model_path),revision],capture_output=True,text=True,timeout=600)
 (pathlib.Path(folder)/'logs/asr-stderr.txt').write_text(result.stderr)
 (pathlib.Path(folder)/'logs/asr-stdout.txt').write_text(result.stdout)
 result.check_returncode()
