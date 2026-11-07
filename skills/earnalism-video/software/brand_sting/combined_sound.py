import math,random,array,wave,pathlib,json,hashlib
b=pathlib.Path(__file__).resolve().parent.parent;p=b/'public/brand-sting/combined.wav'
if p.exists():raise FileExistsError(p)
sr=48000;rng=random.Random(78192);data=array.array('h');low=0
for i in range(sr*3):
 t=i/sr;low=.85*low+.15*rng.uniform(-1,1);value=0
 for start,end,gain in [(.04,.69,.07),(.20,.89,.065)]:
  if start<t<end:value+=gain*low*math.sin(math.pi*(t-start)/(end-start))**1.4
 if 1.18<t<1.72:
  u=(t-1.18)/.54;value+=.012*math.sin(math.pi*u)**2*math.sin(2*math.pi*(180*(t-1.18)+100*(t-1.18)**2))
 for j,start in enumerate([1.88,2.20]):
  u=t-start
  if u>=0:
   value+=(.035 if j==0 else .020)*(1-math.exp(-u/.008))*math.exp(-u/.44)*math.sin(2*math.pi*[220,293.6648][j]*u)
   if u<.055:value+=.005*rng.uniform(-1,1)*math.exp(-u/.014)
 value*=min(1,max(0,(3-t)/.25));data.extend([int(value*32767)]*2)
with wave.open(str(p),'wb') as w:w.setparams((2,2,sr,0,'NONE','not compressed'));w.writeframes(data.tobytes())
(b/'brand_sting/combined-sound-provenance.json').write_text(json.dumps({'original_synthesis':True,'third_party_samples':[],'paper_seconds':[.04,.89],'hop_start_seconds':1.18,'landings_seconds':[1.88,2.20],'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'recording_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
