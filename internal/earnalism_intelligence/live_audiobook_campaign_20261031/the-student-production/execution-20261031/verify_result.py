from pathlib import Path
import argparse,json,hashlib,zipfile,subprocess,datetime
p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('--sha256',required=True);a=p.parse_args()
root=Path('/tmp/earnalism-student-audition-execution-20261031');archive=Path(a.archive)
h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
assert h(archive)==a.sha256,'Export ZIP checksum differs from notebook receipt'
dest=root/'result';dest.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
 assert sum(x.file_size for x in z.infolist())<200_000_000,'Unexpectedly large evidence archive'
 for x in z.infolist():
  target=(dest/x.filename).resolve();assert target.is_relative_to(dest.resolve()),'Unsafe archive path'
  assert not x.filename.endswith('.safetensors'),'Model weights must not be exported as audition evidence'
 z.extractall(dest)
job=json.loads((dest/'audition-job.json').read_text());assert job['max_attempts']==1 and len(job['segments'])==7
expected=json.loads(Path('/tmp/earnalism-main-approved-integration/internal/earnalism_intelligence/live_audiobook_campaign_20261031/the-student-production/audition-job.json').read_text())
assert job['segments']==expected['segments'] and job['model_revision']==expected['model_revision']
rows=[]
for s in job['segments']:
 rel=Path(s['output_path']).relative_to('/content/earnalism-student');wav=dest/rel;sidecar=Path(str(wav)+'.json')
 if not wav.exists() or not sidecar.exists():
  rows.append({'segment':s['segment_id'],'status':'MISSING_OUTPUT','audio_quality':'UNVERIFIED'});continue
 m=json.loads(sidecar.read_text());assert h(wav)==m['wav_sha256'],'WAV checksum mismatch'
 assert m['segment_id']==s['segment_id'];assert m['selected_attempt']==1
 cmd=['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,sample_rate,channels','-of','json',str(wav)]
 probe=json.loads(subprocess.check_output(cmd,text=True,timeout=20))
 duration=float(probe['format']['duration']);assert .25<=duration<=120
 rows.append({'segment':s['segment_id'],'wav_path':str(wav),'wav_sha256':h(wav),'duration_seconds':duration,'technical_probe':probe,'worker_acoustic_status':m.get('audio',{}).get('mechanical_checks'),'attempt':1,'content_accuracy':'UNVERIFIED_PENDING_ASR','pronunciation_and_listening':'UNVERIFIED','status':'GENERATED_REQUIRES_REVIEW'})
report={'evaluated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive_sha256':a.sha256,'expected_passages':7,'generated_passages':sum(r['status']=='GENERATED_REQUIRES_REVIEW' for r in rows),'rows':rows,'generation_error':json.loads((dest/'execution-error.json').read_text()) if (dest/'execution-error.json').exists() else None,'publication_ready':False,'objective_or_subjective_checks_not_run_are_not_passed':True}
(root/'result-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'expected':7,'generated':report['generated_passages'],'error':report['generation_error'],'verification':str(root/'result-verification.json')}))
