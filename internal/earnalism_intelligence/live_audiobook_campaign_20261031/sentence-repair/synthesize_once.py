from pathlib import Path
import os,json,hashlib,urllib.request,datetime,sys,wave
D=Path(__file__).parent
text='Further back in the gloom stood a large hutch, divided into two compartments, one of which was fronted with close iron bars.'
instructions='Narrate as a warm classic literary audiobook narrator with clear pacing, natural pauses, and restrained emotion.'
parent=Path('/tmp/earnalism-audiobook-recovery-followup-20261031/sredni-retained.mp3')
assert hashlib.sha256(parent.read_bytes()).hexdigest()=='2b328a80b90684ddf2fe3df1a1447481067c6cb277484f97432e882c7844d31a'
assert len(text.split())==22 and len(text)<200
assert os.environ.get('OPENAI_API_KEY'), 'Existing provider credential unavailable'
payload=dict(model='gpt-4o-mini-tts',voice='verse',input=text,instructions=instructions,response_format='wav',speed=1.0)
record=dict(approved=True,authority='Explicit owner instruction: Approve one bounded synthesis of Sredni Vashtar’s replacement sentence in the same qualified voice, no new allocation.',request=payload,input_sha256=hashlib.sha256(text.encode()).hexdigest(),parent_master_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),max_requests=1,retries=0,timeout_seconds=45,new_allocation=False,estimated_usd=0.004,estimated_cost_ceiling_usd=0.03,actual_invoice_usd=None,cost_basis='Fixed 22-word sentence; official estimated $0.015/min speech rate; conservative allowance under 16 seconds. No whole-book regeneration. API returns no usage receipt; invoice unknown.',status='PREFLIGHT_PASS_NO_REQUEST')
if '--execute' not in sys.argv:
 assert not (D/'synthesis-attempt.json').exists(),'Attempt consumed or uncertain'
 (D/'preflight.json').write_text(json.dumps(record,indent=2));print('PASS: fixed 22-word Verse job, existing credential, parent hash, one request, no allocation');sys.exit()
assert os.environ.get('EARNALISM_APPROVE_PAID_OPENAI_TTS')=='true'
assert os.environ.get('EARNALISM_STOP_ON_BUDGET_EXCEEDED')=='true'
assert float(os.environ['EARNALISM_TTS_MAX_ESTIMATED_USD'])==.03
record.update(status='ATTEMPT_RESERVED_OUTCOME_PENDING',recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
with (D/'synthesis-attempt.json').open('x') as f:json.dump(record,f,indent=2)
try:
 req=urllib.request.Request('https://api.openai.com/v1/audio/speech',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=45) as r:
  data=r.read(2400001);status=r.status;rid=r.headers.get('x-request-id');ctype=r.headers.get('content-type')
 assert len(data)<=2400000
 (D/'replacement.wav').write_bytes(data)
 with wave.open(str(D/'replacement.wav')) as w:
  audio=dict(seconds=w.getnframes()/w.getframerate(),sample_rate=w.getframerate(),channels=w.getnchannels(),sample_width=w.getsampwidth())
 assert audio['channels']==1 and 3<audio['seconds']<20
 record.update(status='GENERATED_NOT_QUALIFIED',http_status=status,request_id=rid,content_type=ctype,audio=audio,audio_sha256=hashlib.sha256(data).hexdigest())
except Exception as e:
 record.update(status='BLOCKED_ATTEMPT_CONSUMED_NO_RETRY',error_type=type(e).__name__)
 (D/'synthesis-result.json').write_text(json.dumps(record,indent=2));raise SystemExit('Attempt consumed; '+type(e).__name__+'; no retry')
(D/'synthesis-result.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:record[k] for k in ['status','audio','audio_sha256','estimated_usd','actual_invoice_usd']}))
