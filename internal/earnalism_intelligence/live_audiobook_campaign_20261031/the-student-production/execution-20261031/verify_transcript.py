import os
os.environ['HF_HUB_OFFLINE']='1';os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
from pathlib import Path
import json,re,time,hashlib,importlib.metadata,datetime
from faster_whisper import WhisperModel
R=Path('/tmp/earnalism-student-audition-execution-20261031');D=R/'result';job=json.loads((D/'audition-job.json').read_text());out=R/'local-asr.json'
revision='d1d751a5f8271d482d14ca55d9e2deeebbae577f';path=Path('/tmp/earnalism-local-asr-20261028/SMALL-MODEL-PATH.txt').read_text().strip();assert Path(path).name==revision
model=WhisperModel(path,device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
def tokens(t):return re.findall(r"[a-z0-9]+(?:'[a-z]+)?",t.lower().replace('’',"'"))
def edits(a,b):
 row=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  new=[i]
  for j,y in enumerate(b,1):new.append(min(new[-1]+1,row[j]+1,row[j-1]+(x!=y)))
  row=new
 return row[-1]
settings={'beam_size':5,'language':'en','word_timestamps':True,'vad_filter':False,'condition_on_previous_text':False,'initial_prompt':None}
prior=json.loads(out.read_text()) if out.exists() else {};cache={x['audio_sha256']:x for x in prior.get('results',[])};rows=[]
for s in job['segments']:
 wav=D/Path(s['output_path']).relative_to('/content/earnalism-student')
 if not wav.exists():continue
 sha=hashlib.sha256(wav.read_bytes()).hexdigest()
 if sha in cache:rows.append(cache[sha]);continue
 started=time.monotonic();segments,info=model.transcribe(str(wav),**settings)
 transcript=[];measured=[]
 for x in segments:
  transcript.append(x.text.strip());measured.extend({'word':w.word,'start':w.start,'end':w.end,'probability':w.probability} for w in x.words or [])
 text=' '.join(transcript);expected,observed=tokens(s['text']),tokens(text);n=edits(expected,observed);wer=n/max(1,len(expected))
 row={'segment':s['segment_id'],'audio_sha256':sha,'expected_text_sha256':hashlib.sha256(s['text'].encode()).hexdigest(),'expected':s['text'],'transcript':text,'word_edits':n,'expected_words':len(expected),'WER':wer,'raw_asr_match_score_0_to_10':max(0,10*(1-wer)),'first_word_match':bool(observed) and expected[0]==observed[0],'last_word_match':bool(observed) and expected[-1]==observed[-1],'word_timestamps':measured,'duration_seconds':info.duration,'cpu_elapsed_seconds':time.monotonic()-started,'interpretation':'ASR comparison is not human listening; differences require source/audio adjudication, not transcript correction.'}
 rows.append(row)
 report={'model':'Systran/faster-whisper-small.en','revision':revision,'runtime_version':importlib.metadata.version('faster-whisper'),'settings':settings,'local_cpu_only':True,'audio_uploaded':False,'results':rows,'listening_quality':'UNVERIFIED','publication_ready':False}
 out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'segment':row['segment'],'raw_match_score':row['raw_asr_match_score_0_to_10'],'first':row['first_word_match'],'last':row['last_word_match']}),flush=True)
print('Local ASR evidence saved; no listening or publication PASS inferred.',flush=True)
