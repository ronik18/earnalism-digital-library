"""Original three-second sonic ident: synthesized paper and felt-like harmonic tones."""
import math,random,array,wave,pathlib,json,hashlib
root=pathlib.Path(__file__).resolve().parent.parent;p=root/'public/brand-sting/sonic-4.wav'
if p.exists():raise FileExistsError(p)
rng=random.Random(81727);sr=48000;out=array.array('h');previous=0;low=0
for i in range(sr*3):
 t=i/sr;noise=rng.uniform(-1,1);high=noise-previous;previous=noise;low=.87*low+.13*noise;paper=0
 for start,length,gain in [(.12,.82,.065),(.40,1.05,.08)]:
  u=(t-start)/length
  if 0<u<1:paper+=(.6*low+.14*high)*math.sin(math.pi*u)**1.5*gain*(.8+.2*math.sin(2*math.pi*43*t))
 chord=0
 for start,f,gain in [(.22,174.6141,.027),(.48,261.6256,.022),(.77,349.2282,.017),(1.08,523.2511,.012)]:
  u=t-start
  if u>0:chord+=gain*(1-math.exp(-u/.018))*math.exp(-u/1.05)*(math.sin(2*math.pi*f*u)+.14*math.sin(2*math.pi*f*2.003*u)*math.exp(-u/.30))
 value=(paper+chord)*min(1,max(0,(3-t)/.38));out.extend([int(max(-.95,min(.95,value))*32767)]*2)
with wave.open(str(p),'wb') as w:w.setparams((2,2,sr,0,'NONE','not compressed'));w.writeframes(out.tobytes())
(root/'brand_sting/sound-provenance-4.json').write_text(json.dumps({'description':'Original synthesized paper-turn foley and sparse harmonic ident; no imported audio, samples or melodies.','seed':81727,'recording_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'publication':'Private review'},indent=2))
