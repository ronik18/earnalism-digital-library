"""One isolated attended story run. Uses unchanged original worker; never production writes."""
from pathlib import Path
import json,subprocess,sys,time,hashlib,zipfile,traceback
ROOT=Path('/content/earnalism-refraction-v1');OUT=ROOT/'result';SOFT=ROOT/'software'
OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(SOFT))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def status(state,**more):
 (ROOT/'status.json').write_text(json.dumps({'state':state,'time':time.time(),**more}));print(state,more,flush=True)
try:
 import notebook_runtime as runtime
 runtime.BASE_VENV_DIR=ROOT/'venvs'
 def isolated_snapshot(python,repo,revision,output_file):
  code="from huggingface_hub import snapshot_download;from pathlib import Path;import sys,json;r=json.loads(sys.argv[1]);p=snapshot_download(repo_id=r['repo'],revision=r['rev'],cache_dir=r['cache']);Path(r['out']).parent.mkdir(parents=True,exist_ok=True);Path(r['out']).write_text(json.dumps({'model_id':r['repo'],'model_revision':r['rev'],'model_path':p}))"
  subprocess.run([python,'-c',code,json.dumps({'repo':repo,'rev':revision,'cache':str(ROOT/'hf-cache'),'out':str(output_file)})],check=True)
  return json.loads(Path(output_file).read_text())
 runtime.snapshot=isolated_snapshot
 if subprocess.run(['nvidia-smi','-L']).returncode:raise RuntimeError('CUDA required; no alternate speech provider')
 status('SETUP')
 py,model=runtime.setup_qwen(OUT)
 units=json.loads((ROOT/'units.json').read_text());baseline=json.loads((ROOT/'baseline-job.json').read_text())
 (OUT/'raw').mkdir(exist_ok=True);(OUT/'logs').mkdir(exist_ok=True)
 segments=[dict(segment_id=u['id'],text=u['text'],instruct=baseline['segments'][0]['instruct'],speaker='Ryan',seed=baseline['segments'][0]['seed'],cache_key=hashlib.sha256(json.dumps(u,sort_keys=True).encode()).hexdigest(),output_path=str(OUT/'raw'/(u['id']+'.wav'))) for u in units]
 job={**model,'generation':baseline['generation'],'slug':'refraction-v1','journal_path':str(OUT/'logs/qwen.jsonl'),'report_path':str(OUT/'logs/qwen-report.json'),'stop_flag_path':str(OUT/'STOP'),'max_attempts':3,'device':'cuda:0','dtype':baseline['dtype'],'attention':baseline['attention'],'segments':segments}
 jobfile=OUT/'qwen-job.json'
 if jobfile.exists() and json.loads(jobfile.read_text())!=job:raise RuntimeError('Job changed: preserve existing attempt ledger')
 if not jobfile.exists():jobfile.write_text(json.dumps(job,indent=2))
 status('GENERATING',requested=len(segments))
 subprocess.run([py,str(SOFT/'qwen_worker.py'),str(jobfile)],check=True,timeout=1100)
 status('SPEECH_READY')
 # Export speech immediately before ASR setup so the guard never leaves the only completed speech unexported.
 def export(name):
  dest=ROOT/name
  if dest.exists():return dest
  paths=[p for p in OUT.rglob('*') if p.is_file()]
  with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
   for p in paths:z.write(p,str(p.relative_to(OUT)))
   z.writestr('transfer-manifest.json',json.dumps({str(p.relative_to(OUT)):sha(p) for p in paths}))
  status('EXPORT',file=str(dest),sha256=sha(dest),bytes=dest.stat().st_size);return dest
 export('refraction-speech.zip')
 status('ASR_SETUP')
 asrpy,env=runtime.pip_env('video-asr',[['faster-whisper==1.2.1','av==15.1.0','rapidfuzz==3.14.1','huggingface-hub>=0.34,<1']])
 model=isolated_snapshot(asrpy,'Systran/faster-whisper-large-v3','edaa852ec7e145841d8ffdb056a99866b5f0a478',OUT/'asr-model.json')
 asrcode=r'''
from faster_whisper import WhisperModel
from pathlib import Path
import json,sys,hashlib
out=Path(sys.argv[1]);model=WhisperModel(sys.argv[2],device='cuda',compute_type='float16',local_files_only=True)
(out/'alignment').mkdir(exist_ok=True)
for wav in sorted((out/'raw').glob('*.wav')):
 path=out/'alignment'/(wav.stem+'.json')
 if path.exists():continue
 segments,_=model.transcribe(str(wav),language='en',word_timestamps=True,condition_on_previous_text=False,vad_filter=False,beam_size=5)
 words=[{'word':w.word.strip(),'start':w.start,'end':w.end} for seg in segments for w in (seg.words or [])]
 path.write_text(json.dumps({'audio_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'model_revision':'edaa852ec7e145841d8ffdb056a99866b5f0a478','word_times':words,'recognized':' '.join(w['word'] for w in words)},indent=2))
 print('ALIGNED',wav.stem,flush=True)
'''
 from asr_cuda_env import cuda_asr_environment
 status('ALIGNING');subprocess.run([asrpy,'-c',asrcode,str(OUT),model['model_path']],env=cuda_asr_environment(ROOT/'venvs/qwen-py312'),check=True,timeout=300)
 (OUT/'units.json').write_text((ROOT/'units.json').read_text());export('refraction-aligned.zip');status('COMPLETE',units=len(segments))
except Exception as exc:
 status('FAILED',error=repr(exc));traceback.print_exc()
 try:
  # A partial export is explicitly partial, retains every completed file and attempt record.
  paths=[p for p in OUT.rglob('*') if p.is_file()];dest=ROOT/'refraction-partial.zip'
  if not dest.exists():
   with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
    for p in paths:z.write(p,str(p.relative_to(OUT)))
    z.writestr('transfer-manifest.json',json.dumps({str(p.relative_to(OUT)):sha(p) for p in paths}))
 except Exception:traceback.print_exc()
