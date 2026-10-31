import runpy,json,sys,hashlib,copy,shutil
from pathlib import Path
B=Path('/tmp/earnalism-student-preflight-20261031')
n=runpy.run_path(str(B/'qualify_student.py'));ctx=n['ctx'];core=n['core'];sys.path.insert(0,str(B/'worker'));import qwen_worker
revision='0c0e3051f131929182e2c023b9537f8b1c68adfe'
model={'model_id':core.QWEN_ID,'model_revision':revision,'model_path':'/content/earnalism-student/hf-cache/models--Qwen--Qwen3-TTS-12Hz-1.7B-CustomVoice/snapshots/'+revision}
job=core.qwen_job(ctx,model,stage='audition');job['max_attempts']=1
# Representative exact units: opening, Russian names, dialogue/narrative texture,
# biblical proper names, emotional response, and ending. No rewritten names.
segments=ctx['segments'];chosen=[]
def add(s):
 if s['segment_id'] not in [x['segment_id'] for x in chosen]:chosen.append(s)
add(segments[0])
for term in ['Velikopolsky','Lukerya','Rurik','Judas','wept']:
 matches=[s for s in segments if term in s['text']]
 if matches:add(matches[0])
add(segments[-1])
assert len(chosen)<=7
prototype=job['segments'][0]
actual=[]
for s in chosen:
 q={**s,'source_segment_id':s['segment_id'],'segment_id':s['segment_id']+'--audition-ryan','output_path':'/content/earnalism-student/audition/'+s['segment_id']+'.wav'}
 q['cache_key']=core.object_hash({'source':ctx['artifact']['source_sha256'],'segment':q,'model_revision':revision,'worker_sha256':hashlib.sha256((B/'worker/qwen_worker.py').read_bytes()).hexdigest()});actual.append(q)
job.update({'segments':actual,'journal_path':'/content/earnalism-student/attempts.jsonl','report_path':'/content/earnalism-student/generation-report.json','stop_flag_path':'/content/earnalism-student/STOP'})
core.atomic_json(B/'audition-job.json',job)
fixture=B/'VALIDATION_FIXTURE_ONLY/models--Qwen--Qwen3-TTS-12Hz-1.7B-CustomVoice/snapshots'/revision
fixture.mkdir(parents=True,exist_ok=True);shutil.copy2(B/'qwen-config.json',fixture/'config.json');(fixture/'speech_tokenizer').mkdir(exist_ok=True)
fake=copy.deepcopy(job);fake['model_path']=str(fixture)
qwen_worker.validate_job(fake)
try:qwen_worker.snapshot_manifest(fixture);raise AssertionError('fixture must not pass real-weight admission')
except ValueError as e:assert 'no safetensors weights' in str(e)
try:
 bad=copy.deepcopy(fake);bad['model_path']=str(B/'invalid-flat-model');qwen_worker.validate_job(bad);raise AssertionError('flat path accepted')
except ValueError:pass
probe={'schema':'earnalism.worker-contract-preflight.v1','actual_worker_sha256':hashlib.sha256((B/'worker/qwen_worker.py').read_bytes()).hexdigest(),'actual_job_sha256':hashlib.sha256((B/'audition-job.json').read_bytes()).hexdigest(),'structural_job_contract':'PASS_WITH_EXPLICIT_CONFIG_ONLY_FIXTURE','real_model_weights':'MISSING_NOT_CLAIMED_PASS','inference':'NOT_RUN','fixture_rejected_by_weight_admission':True,'invalid_flat_path_rejected':True,'sample_count':len(actual),'sample_words':sum(len(core.words(x['text'])) for x in actual),'runtime_scope':'One allocation; 30 min maximum request-to-shutdown; one take/unit; no automatic failed/uncertain replay; no purchases; no full-title generation from this job.'}
core.atomic_json(B/'worker-contract-preflight.json',probe);print(json.dumps(probe))
