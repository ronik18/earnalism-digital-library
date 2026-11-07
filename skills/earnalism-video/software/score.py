"""Project-original ambient instrumental: synthesized oscillators, no samples or imported melody."""
import array, hashlib, json, math, pathlib, wave

def quiet_gain(t, intervals):
 gain=1.
 for a,b in intervals:
  # Smooth one-second shoulders prevent amplitude clicks around important words.
  if a<=t<=b:g=0.
  elif a-1<t<a:g=1.*(1-math.cos(math.pi*(a-t)))/2
  elif b<t<b+1:g=1.*(1-math.cos(math.pi*(t-b)))/2
  else:g=1.
  gain=min(gain,g)
 return gain

def score_plan(seconds,scenes):
 # Original four-note motif; spacing follows explanation beats rather than a loop.
 motif=[293.6648,440.,329.6276,349.2282]
 events=[]
 for scene in scenes:
  start=scene['start'];kind=scene['diagram']
  if kind=='orbit':
   for dt,hz in zip((1.1,2.05,3.45,5.2),motif):events.append((start+dt,hz,.0034))
  elif kind=='phases':
   for dt,hz in ((1.5,motif[0]),(5.9,motif[1])):events.append((start+dt,hz,.0024))
  elif kind=='cycle':
   for dt,hz in zip((1.0,2.35,4.0,6.2),reversed(motif)):events.append((start+dt,hz,.0028))
 # A restrained two-note answer echoes the motif and hands over to the fixed ident.
 events.extend([(max(0,seconds-4.6),220.,.002),(max(0,seconds-3.2),293.6648,.0016)])
 return sorted((t,hz,g) for t,hz,g in events if 0<=t<seconds)

def felt_key(dt,hz):
 # Synthesized felt-key timbre: rounded attack, differently decaying partials.
 attack=1-math.exp(-dt/.035)
 return attack*(math.exp(-dt/1.7)*math.sin(2*math.pi*hz*dt)+.19*math.exp(-dt/.8)*math.sin(2*math.pi*hz*2.002*dt)+.045*math.exp(-dt/.32)*math.sin(2*math.pi*hz*4.006*dt))

def compose(path, seconds, quiet_intervals=(), rate=24000, scenes=(), palette="legacy", speech_intervals=()):
 if palette=="acoustic_editorial_v12":
  from editorial_score import compose as editorial_compose
  return editorial_compose(path,seconds,quiet_intervals,rate,scenes,speech_intervals=speech_intervals)
 if palette=="acoustic_v8":
  from final_chamber_score import compose as refined_compose
  return refined_compose(path,seconds,quiet_intervals,rate,scenes,speech_intervals=speech_intervals)
 if palette=="acoustic_v7":
  from balanced_score import compose as balanced_compose
  return balanced_compose(path,seconds,quiet_intervals,rate,scenes,speech_intervals=speech_intervals)
 if palette=="acoustic_v4":
  from acoustic_score import compose as acoustic_compose
  return acoustic_compose(path,seconds,quiet_intervals,rate,scenes)
 if palette!="legacy":raise ValueError("Unknown score palette")
 path=pathlib.Path(path)
 if path.exists():raise FileExistsError(path)
 chords=[(146.8324,220.,329.6276),(130.8128,195.9977,293.6648),(110.,164.8138,246.9417),(146.8324,220.,293.6648)]
 events=score_plan(seconds,scenes);data=array.array('h')
 for i in range(round(seconds*rate)):
  t=i/rate;block=t/18;k=int(block);blend=block-k;blend=blend*blend*(3-2*blend);val=0.
  for j,hz in enumerate(chords[k%4]):
   nxt=chords[(k+1)%4][j]
   # Slow, bounded amplitude movement; no imported recording or random noise.
   tone=lambda f:math.sin(2*math.pi*f*t)+.045*math.sin(4*math.pi*f*t+.11*math.sin(t*.47))
   swell=.86+.14*math.sin(t*.38+j*.8)
   val+=((1-blend)*tone(hz)+blend*tone(nxt))*(.44**j)*.0065*swell
  for start,hz,gain in events:
   dt=t-start
   if 0<=dt<7:
    # Discrete, quiet early reflections add depth without a reverberant wash.
    val+=gain*felt_key(dt,hz)
    if dt>.13:val+=gain*.13*felt_key(dt-.13,hz)
    if dt>.27:val+=gain*.06*felt_key(dt-.27,hz)
  fade=min(1,t/3,max(0,(seconds-t)/2.5))
  data.append(round(32767*val*fade*quiet_gain(t,quiet_intervals)))
 with wave.open(str(path),'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(data.tobytes())
 provenance={'kind':'original scene-aware instrumental recording','version':'moon-score-v3-felt-motif','timbres':'Original oscillator-synthesized felt-key partials and warm sustained tones; no sampled instruments','motif_hz':[293.6648,440.,329.6276,349.2282],'third_party_samples':[],'external_compositions':[],'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'recording_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'seconds':seconds,'quiet_intervals':list(quiet_intervals),'events':events,'review':'Source/provenance inspected; no imported melody or recordings. Full owner listening and resemblance review pending.'}
 path.with_suffix('.provenance.json').write_text(json.dumps(provenance,indent=2))

def anchors(scene,words,offset):
 import re
 norm=lambda s:re.findall(r"[a-z0-9]+",s.lower())
 tokens=[]
 for w in words:
  for token in norm(w.get('word',w.get('text',''))):tokens.append((token,w['start']))
 result=[]
 for anchor in scene.get('anchors',[]):
  phrase=norm(anchor['phrase']);matches=[i for i in range(len(tokens)-len(phrase)+1) if [x[0] for x in tokens[i:i+len(phrase)]]==phrase]
  if not matches:raise ValueError('Spoken animation anchor missing: '+anchor['phrase'])
  result.append({**anchor,'time':offset+tokens[matches[0]][1]})
 return result
