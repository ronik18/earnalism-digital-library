from pathlib import Path
from faster_whisper import WhisperModel
import json,re
D=Path(__file__).parent
models=[('small.en',Path('/tmp/earnalism-local-asr-20261028/SMALL-MODEL-PATH.txt').read_text().strip()),('large-v3-turbo','/Users/ronikbasak/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf')]
rows=[]
for label,path in models:
 m=WhisperModel(path,device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
 for file in ['replacement-canonical.wav','both-joins-review.wav']:
  seg,info=m.transcribe(str(D/file),language='en',beam_size=5,word_timestamps=True,condition_on_previous_text=False)
  segments=[{'text':z.text,'start':z.start,'end':z.end,'words':[{'word':w.word,'start':w.start,'end':w.end} for w in z.words]} for z in seg]
  transcript=' '.join(z['text'].strip() for z in segments);expected=json.loads((D/'preflight.json').read_text())['request']['input'];norm=lambda x:re.findall(r'[a-z]+',x.lower())
  row={'model':label,'file':file,'transcript':transcript,'exact_sentence':norm(transcript)==norm(expected) if file.startswith('replacement') else None,'segments':segments};rows.append(row);print(label,file,transcript,flush=True)
 del m
(D/'local-asr.json').write_text(json.dumps(rows,indent=2))
