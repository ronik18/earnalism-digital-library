"""Original chamber score using explicitly licensed VCSL acoustic one-shot recordings."""
import array,hashlib,json,math,pathlib,subprocess,sys,wave
ROOT=pathlib.Path(__file__).resolve().parent
ASSETS=ROOT/'assets/music/vcsl-piano-harp-v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def validate_assets(root=ASSETS):
 root=pathlib.Path(root);m=json.loads((root/'manifest.json').read_text())
 if m['license']!='CC0-1.0' or m['revision']!='c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e':raise ValueError('Unreviewed music asset collection')
 for row in m['samples']+m['documents']:
  if pathlib.PurePath(row['file']).name!=row['file'] or sha(root/row['file'])!=row['sha256']:raise ValueError('Music asset hash mismatch')
 if 'CC0 1.0 Universal' not in (root/'LICENSE').read_text():raise ValueError('Missing music license')
 return m

def plan(seconds,scenes):
 events=[];silences=[]
 def add(t,notes,inst='piano',vel=.5,duration=4.8,phrase='harmony'):
  for j,n in enumerate(notes):
   at=t+j*.065
   if 0<=at<seconds-.65:events.append({'time':round(at,4),'midi':n,'instrument':inst,'velocity':round(vel*(1-.07*j),3),'duration':duration,'phrase':phrase,'pan':-.08 if inst=='piano' else .12})
 def motif(t,notes,spaces,inst,vel,phrase):
  for j,(n,dt) in enumerate(zip(notes,spaces)):add(t+dt,[n],inst,vel*[.88,1.,.70,.82][j],3.8,phrase)
 for s in scenes:
  start=s['start'];kind=s['diagram']
  if kind=='question':silences.append((start,min(s['end'],start+6.2)))
  elif kind=='sunlight':
   add(start+1.05,[50,57,64],vel=.32,duration=6.5,phrase='D open ninth: observation')
   motif(start+6.2,[62,69,64,65],[0,1.65,3.05,4.95],'piano',.52,'question: D A E F')
  elif kind=='orbit':
   add(start+.8,[48,55,62,64],vel=.24,duration=6.2,phrase='C add nine: shift of viewpoint')
   ground=next((a['time'] for a in s.get('anchors',[]) if a.get('phrase')=='From the ground'),start+3.2)
   motif(ground+.55,[62,69,64,65],[0,1.1,3.0,5.4],'harp',.31,'harp answer: stretched question')
  elif kind=='phases':
   add(start+.6,[46,53,57,62],vel=.27,duration=5.6,phrase='B flat major seven: reveal')
   quarter=next((a['time'] for a in s.get('anchors',[]) if a.get('phrase')=='At first quarter'),start+4)
   full=next((a['time'] for a in s.get('anchors',[]) if a.get('phrase')=='Near full Moon'),start+8.8)
   definition=any(a.get('phrase')=='First quarter means' for a in s.get('anchors',[]))
   silences.append((quarter-.25,full-.35 if definition else min(full-.35,quarter+4.2)))
   add(full+.4,[50,57,64],vel=.32,duration=4.2,phrase='D open ninth: full Moon')
  elif kind=='eclipse':
   silences.append((start,start+5.7));add(start+7.2,[55,58,62],vel=.23,duration=5.2,phrase='G minor: distinguish the shadow')
  elif kind=='cycle':
   add(start+.55,[45,52,59],vel=.28,duration=5.6,phrase='A suspended: the cycle returns')
   motif(start+1.35,[65,64,69,62],[0,1.75,4.0,6.3],'piano',.44,'return: F E A D')
  elif kind=='callback':silences.append((start,start+3.05))
 # Clear resolution, then leave space for the already-selected ident sound.
 add(max(0,seconds-5.4),[50,57,64],vel=.30,duration=3.6,phrase='D open ninth: visual callback')
 add(max(0,seconds-3.2),[62],'harp',.27,2.2,'tonic answer into brand ending')
 return sorted(events,key=lambda e:e['time']),silences

def _pcm(path,rate=24000):
 a=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ar',str(rate),'-ac','2','-f','f32le','-']))
 if sys.byteorder!='little':a.byteswap()
 return a

def _wav(path,values,rate):
 if pathlib.Path(path).exists():raise FileExistsError(path)
 pcm=array.array('h',(round(max(-.98,min(.98,x))*32767) for x in values))
 if sys.byteorder!='little':pcm.byteswap()
 with wave.open(str(path),'wb') as w:w.setparams((2,2,rate,0,'NONE','not compressed'));w.writeframes(pcm.tobytes())

def compose(path,seconds,quiet_intervals=(),rate=24000,scenes=(),asset_root=ASSETS,speech_intervals=()):
 from score import quiet_gain
 path=pathlib.Path(path)
 if path.exists():raise FileExistsError(path)
 m=validate_assets(asset_root);events,planned_quiet=plan(seconds,scenes);quiet=sorted(set(tuple(v) for v in [*quiet_intervals,*planned_quiet]))
 size=round(seconds*rate)*2;stems={k:array.array('f',[0.])*size for k in ('piano','harp')};cache={};used={}
 for e in events:
  original_velocity=e['velocity'];e['source_velocity']=original_velocity
  e['velocity']=round(.38*(original_velocity/.38)**.65,4)
  overlap=sum(max(0,min(e['time']+.35,b)-max(e['time'],a)) for a,b in speech_intervals)
  e['speech_attack_overlap_fraction']=round(min(1,overlap/.35),3)
  if overlap>.10 and original_velocity>.34:e['velocity']*=.72
  key=(e['instrument'],e['midi'])
  if key not in cache:
   row=min((s for s in m['samples'] if s['instrument']==key[0]),key=lambda s:abs(s['root_midi']-key[1]))
   shift=key[1]-row['root_midi']
   if abs(shift)>2:raise ValueError('No closely sampled acoustic note; do not stretch instrument across octaves')
   ratio=2**(shift/12)
   raw=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(pathlib.Path(asset_root)/row['file']),'-af',f'aresample={rate},asetrate={rate*ratio},aresample={rate},highpass=f=85,lowpass=f=7000','-ar',str(rate),'-ac','2','-f','f32le','-']))
   if sys.byteorder!='little':raw.byteswap()
   peak=max(abs(x) for x in raw)
   if peak<1e-7:raise ValueError('Silent acoustic sample')
   original_gain=.075/peak
   window=raw[:min(len(raw),round(1.2*rate)*2)]
   energy=math.sqrt(sum(x*x for x in window)/max(1,len(window)))
   energy_gain=.014/max(energy,1e-8)
   gain=max(original_gain*10**(-4/20),min(original_gain*10**(4/20),energy_gain))
   cache[key]=(raw,gain);used[row['file']]=row
  raw,gain=cache[key];start=round(e['time']*rate);frames=min(len(raw)//2,round((e['duration']+.75)*rate),size//2-start)
  pan=e['pan'];lg=math.cos((pan+1)*math.pi/4)*2**.5;rg=math.sin((pan+1)*math.pi/4)*2**.5
  for i in range(frames):
   dt=i/rate;env=min(1,dt/(.085 if e['instrument']=='piano' else .11),max(0,(e['duration']+.75-dt)/.75));g=gain*e['velocity']*env;idx=(start+i)*2
   stems[e['instrument']][idx]+=raw[i*2]*g*lg;stems[e['instrument']][idx+1]+=raw[i*2+1]*g*rg
 for inst,values in stems.items():_wav(path.with_name('score-'+inst+'.wav'),values,rate)
 total=array.array('f',[0.])*size
 for i in range(size//2):
  t=i/rate;g=quiet_gain(t,quiet)*min(1,t/1.5,max(0,(seconds-.4-t)/1.8))
  for c in (0,1):total[i*2+c]=(stems['piano'][i*2+c]+stems['harp'][i*2+c])*g
 rawpath=path.with_name('score-unmastered.wav');_wav(rawpath,total,rate)
 subprocess.run(['ffmpeg','-v','error','-n','-i',str(rawpath),'-af','loudnorm=I=-34:TP=-9:LRA=10','-ar',str(rate),'-ac','2','-c:a','pcm_s16le',str(path)],check=True)
 provenance={'kind':'original acoustic chamber composition','version':'moon-score-v5-balanced-acoustic-chamber','title':'Light, Seen Again','composition':'Original D A E F question, harp response, F E A D return; Dadd9, Cadd9, B-flat major-seven, G minor, Asus and D open-ninth resolution','performance':'Computer-arranged acoustic one-shot notes with written dynamics, nonuniform phrase spacing and modest stereo placement; not a live human ensemble','source_sha256':sha(ROOT/'score.py'),'composition_source_sha256':sha(__file__),'note_leveling':'First 1.2-second energy, bounded +/-4 dB against prior peak normalization; compressed written velocity range; quieter note attacks overlapping actual words; 85/110 ms instrument attack','recording_sha256':sha(path),'seconds':seconds,'quiet_intervals':quiet,'events':events,'third_party_samples':list(used.values()),'external_compositions':[],'sample_collection':'VCSL','asset_manifest_sha256':sha(pathlib.Path(asset_root)/'manifest.json'),'license':'CC0-1.0','license_sha256':sha(pathlib.Path(asset_root)/'LICENSE'),'readme_sha256':sha(pathlib.Path(asset_root)/'README.md'),'stems':{name:sha(path.with_name(name)) for name in ['score-piano.wav','score-harp.wav','score-unmastered.wav']},'mastering':'Stereo 24kHz PCM, -34 LUFS target before gentle speech ducking; real silent intervals and final gap','review':'Private listening, instrumental quality and resemblance review pending; provenance does not establish musical sophistication.'}
 path.with_suffix('.provenance.json').write_text(json.dumps(provenance,indent=2))
 return provenance
