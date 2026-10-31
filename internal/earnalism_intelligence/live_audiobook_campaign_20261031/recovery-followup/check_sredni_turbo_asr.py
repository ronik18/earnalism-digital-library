import os
os.environ['HF_HUB_OFFLINE']='1';os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
from pathlib import Path
import json,re,time,hashlib,datetime
from faster_whisper import WhisperModel
R=Path('/tmp/earnalism-audiobook-recovery-followup-20261031');wav=R/'sredni-retained.mp3';sha=hashlib.sha256(wav.read_bytes()).hexdigest();assert sha=='2b328a80b90684ddf2fe3df1a1447481067c6cb277484f97432e882c7844d31a'
revision='0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf';path='/Users/ronikbasak/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/'+revision;assert (Path(path)/'model.bin').is_file()
p=Path('/tmp/earnalism-main-approved-integration/backend/data/controlled_publications/sredni-vashtar/chapters/chapter-001.json');expected=json.loads(p.read_text())['content']
model=WhisperModel(path,device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
started=time.monotonic();segments,info=model.transcribe(str(wav),beam_size=5,language='en',word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
rows=[]
for s in segments:
 rows.append({'start':s.start,'end':s.end,'text':s.text,'words':[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability} for w in s.words or []]})
 (R/'sredni-turbo-asr-progress.json').write_text(json.dumps({'audio_sha256':sha,'rows':rows,'complete':False}))
text=' '.join(s['text'].strip() for s in rows)
def tok(x):return re.findall(r"[a-z0-9]+(?:'[a-z]+)?",x.lower().replace('’',"'"))
a,b=tok(expected),tok(text);row=list(range(len(b)+1))
for i,x in enumerate(a,1):
 new=[i]
 for j,y in enumerate(b,1):new.append(min(new[-1]+1,row[j]+1,row[j-1]+(x!=y)))
 row=new
wer=row[-1]/len(a)
d={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'audio_sha256':sha,'source_sha256':hashlib.sha256(expected.encode()).hexdigest(),'model':'mobiuslabsgmbh/faster-whisper-large-v3-turbo','revision':revision,'execution':'LOCAL_CPU_INT8_FOUR_THREADS_NO_NETWORK_NO_NEW_COLAB_ALLOCATION','duration':info.duration,'cpu_elapsed':time.monotonic()-started,'expected_words':len(a),'observed_words':len(b),'edits':row[-1],'raw_match_score':max(0,10*(1-wer)),'first_words':{'expected':a[:12],'observed':b[:12]},'last_words':{'expected':a[-12:],'observed':b[-12:]},'transcript':text,'segments':rows,'metric':'10*(1-WER), supplementary diagnostic; canonical release score must use repository transcript_similarity','interpretation':'Raw ASR differences require audio/source adjudication; not listening or pronunciation approval. Generation-source binding remains separate.','release_ready':False}
(R/'sredni-turbo-local-asr.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:d[k] for k in ['audio_sha256','raw_match_score','edits','expected_words','observed_words','cpu_elapsed','release_ready']}),flush=True)
