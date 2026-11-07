"""Original short musical punctuation matched to the red glyph landings."""
import math,random,array,wave,pathlib,json,hashlib
b=pathlib.Path(__file__).resolve().parent.parent
for variant,landings in [(1,[1.03,1.30]),(2,[.83,1.12,1.42]),(3,[1.02,1.36])]:
 p=b/f'public/brand-sting/jump-{variant}.wav'
 if p.exists():raise FileExistsError(p)
 sr=48000;rng=random.Random(672+variant);data=array.array('h')
 for i in range(sr*3):
  t=i/sr;v=0
  # Soft upward tonal gesture with gentle harmonics; restrained landing punctuation.
  if .16<t<.75:
   u=(t-.16)/.59;v+=.012*math.sin(math.pi*u)**2*math.sin(2*math.pi*(180*(t-.16)+100*(t-.16)**2))
  for j,start in enumerate(landings):
   u=t-start
   if u>=0:
    f=[220,293.6648,440][j%3];v+=(.035 if j==0 else .018)*(1-math.exp(-u/.008))*math.exp(-u/.45)*math.sin(2*math.pi*f*u)
    if u<.055:v+=.007*rng.uniform(-1,1)*math.exp(-u/.014)
  v*=min(1,max(0,(3-t)/.3));data.extend([int(v*32767)]*2)
 with wave.open(str(p),'wb') as w:w.setparams((2,2,sr,0,'NONE','not compressed'));w.writeframes(data.tobytes())
 (b/f'brand_sting/jump-sound-{variant}.json').write_text(json.dumps({'original_synthesis':True,'third_party_samples':[],'landings_seconds':landings,'recording_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()},indent=2))
