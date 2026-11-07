"""Private source-bound transition refinement; never stack processed audio."""
from pathlib import Path
import json,copy,sys,subprocess,statistics
sys.path.insert(0,str(Path(__file__).resolve().parent))
import studio
from delivery_conform import render_scene
old=studio.BASE/'outputs/moon-mature-55-v8-final';dest=studio.BASE/'outputs/moon-teacher-transitions-v9'
if dest.exists():raise FileExistsError(dest)
ep=studio.load(old/'episode.json');ep['id']=dest.name
path=studio.BASE/'episodes'/f'{dest.name}.json'
if path.exists():
 if studio.load(path)!=ep:raise ValueError('Changed episode definition')
else:studio.write(path,ep)
studio.prepare(path).rename(dest)
plans=copy.deepcopy(studio.load(old/'sentence-delivery-plan.json'));pace={s['scene']:s for s in studio.load(old/'pre-render-pace-review.json')['scenes']}
notes=[]
for item in plans:
 sid=item['scene']
 for j,ph in enumerate(item['phrases']):
  current=pace[sid]['sentence_rates'][j]['wpm'];target=None
  if sid=='s01':target=132 if j==0 else 155
  elif sid=='s05':target=125 if j==1 else (104 if j==2 else None)
  elif sid=='s06':target=118 if j==0 else 112
  elif sid=='s07d' and j==0:target=129
  before=ph['tempo']
  if target:ph['tempo']=max(.75,min(1.25,before*target/current))
  # Opening pause was .93 s: make it deliberate without an isolated command.
  if sid=='s01' and j==0:ph['pad_after']=max(0,ph['pad_after']-.23)
  notes.append({'scene':sid,'sentence':j,'old_tempo':before,'new_tempo':ph['tempo'],'observed_wpm':current,'desired_wpm':target,'bounded':True})
# Broad, restrained low-mid matching from original takes, no pitch change.
# Match measured voiced low-mid / presence energy to the median original take.
import numpy as np
ratios={}
for wav in (old/'delivery-source/raw').glob('*.wav'):
 x=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(wav),'-ar','24000','-ac','1','-f','f32le','-']),dtype='<f4')
 frames=np.lib.stride_tricks.sliding_window_view(x,1024)[::512];frames=frames[np.sqrt(np.mean(frames**2,axis=1))>.01]
 power=np.abs(np.fft.rfft(frames*np.hanning(1024),axis=1))**2;freq=np.fft.rfftfreq(1024,1/24000)
 ratios[wav.stem]=float(10*np.log10(np.sum(power[:,(freq>=100)&(freq<=350)])/np.sum(power[:,(freq>=700)&(freq<=3000)])))
median=statistics.median(ratios.values());tone={k:round(max(-1.5,min(1.5,(median-v)*.45)),3) for k,v in ratios.items()}
for name in ['logs','config']:(dest/name).mkdir(exist_ok=True)
for item in plans:render_scene(dest,old/'delivery-source',item,studio.load(old/'source-level-matching.json')['gain_db'],tone)
for name in ['source-level-matching.json','editorial-change.json','alignment-model.json']:studio.write(dest/name,studio.load(old/name))
studio.write(dest/'sentence-delivery-plan.json',plans);studio.write(dest/'transition-refinement.json',{'parent':str(old),'sentence_edits':notes,'original_low_mid_presence_db':ratios,'source_eq_180hz_db':tone,'pitch_shift':False,'stacked_processing':False,'human_listening':'PENDING','method':'Bounded complete-sentence tempo and restrained broad low-mid matching; no identity/age inference'})
from colab_runner import align
model=Path.home()/'.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf'
align(dest,str(studio.BASE/'.pace-asr-venv/bin/python'),model,model.name)
print('NARRATION_READY',dest,flush=True)
