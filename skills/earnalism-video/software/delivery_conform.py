"""Single-pass sentence delivery conform from original Qwen takes, with source bindings."""
import pathlib,re,json,subprocess,array,math,sys

def sentences(text):
 return [m.group().strip() for m in re.finditer(r'[^.!?]+(?:[.!?]+|$)',text) if m.group().strip()]

def word_map(episode,records):
 from asr_review import tokens
 canonical=tokens(' '.join(s['text'] for s in episode['scenes']));recognized=[];mapped=[]
 for sid,record in records:
  if record.get('unresolved_asr_edits'):raise ValueError('Resolve actual source ASR before delivery conform')
  for w in record.get('display_word_times',record['word_times']):
   for token in tokens(w['word']):recognized.append(token);mapped.append({'source':sid,'start':w['start'],'end':w['end']})
 if recognized!=canonical:raise ValueError('Source speech does not match complete canonical script')
 return mapped

def plan(episode,mapped,source_seconds,target=137,source_words=None,audio_samples=None):
 from asr_review import tokens
 if not 125<=target<=150:raise ValueError('Unreviewed sentence pace target')
 cursor=0;result=[]
 for scene in episode['scenes']:
  phrases=[]
  for phrase in sentences(scene['text']):
   n=len(tokens(phrase));words=mapped[cursor:cursor+n];cursor+=n
   if len(words)!=n:raise ValueError('Incomplete word map')
   parts=[]
   for w in words:
    if not parts or parts[-1]['source']!=w['source']:parts.append(dict(source=w['source'],start=w['start'],end=w['end']))
    else:parts[-1]['end']=w['end']
   spoken=sum(p['end']-p['start'] for p in parts);count=len(phrase.split())
   if spoken<=0:raise ValueError('Invalid source speech timing')
   raw_wpm=count*60/spoken;wanted=target/raw_wpm
   factor=max(.75,min(1.25,wanted)) if count>=6 else max(.9,min(1.1,wanted))
   achieved=raw_wpm*factor
   if count>=6 and not 118<=achieved<=145:raise ValueError('Source sentence cannot reach the consistent speech band within safe conform bounds')
   for part in parts:
    # Preserve a small phonetic shoulder, never cross an adjacent recognized word.
    same=source_words[part['source']] if source_words else [w for w in mapped if w['source']==part['source']]
    previous=max((w['end'] for w in same if w['end']<=part['start']),default=0)
    following_times=[w['start'] for w in same if w['start']>=part['end']]
    following=min(following_times,default=source_seconds[part['source']])
    if audio_samples:
     samples=audio_samples[part['source']]
     part['start']=quiet_boundary(samples,max(0,previous+.02,part['start']-.25),max(0,part['start']-.01)) if part['start']>.03 else 0
     part['end']=quiet_boundary(samples,part['end']+.02,min(following-.04,part['end']+.35)) if following_times else source_seconds[part['source']]
    else:
     part['start']=max(0,part['start']-.05,(previous+part['start'])/2)
     part['end']=min(source_seconds[part['source']],part['end']+.08,(part['end']+following)/2)
   phrases.append({'text':phrase,'words':count,'source_spoken_wpm':round(raw_wpm,2),'expected_spoken_wpm':round(achieved,2),'tempo':factor,'parts':parts,'pad_after':.50})
  phrases[-1]['pad_after']=.65
  result.append({'scene':scene['id'],'text':scene['text'],'target_spoken_wpm':target,'phrases':phrases})
 if cursor!=len(mapped):raise ValueError('Unconsumed source speech')
 return result

def validate(folder,meta):
 from audio_derivation import check_unit,sha
 d=meta['derivation']
 if d.get('pitch_shift') is not False or d.get('passes_from_original')!=1:raise ValueError('Invalid delivery conform generation')
 for sid,row in d['sources'].items():
  if not re.fullmatch(r'[a-z0-9-]+',sid):raise ValueError('Unsafe conform source')
  parent=pathlib.Path(folder)/'delivery-source';source=check_unit(parent,sid)
  if sha(parent/'raw'/(sid+'.wav'))!=row['wav_sha256'] or sha(parent/'raw'/(sid+'.wav.json'))!=row['meta_sha256']:raise ValueError('Changed delivery source')
  if source['settings'].get('speaker')!='Ryan' or source['settings'].get('instruct')!=meta['settings'].get('instruct'):raise ValueError('Conform voice profile changed')
  for key in ('model_id','model_revision','worker_sha256'):
   if source['provenance'].get(key)!=meta['provenance'].get(key):raise ValueError('Conform provider provenance changed')
 for row in d['sources'].values():
  if not -2<=row.get('tone_eq_db',0)<=2:raise ValueError('Unbounded source-tone edit')
 for phrase in d['plan']['phrases']:
  if not .75<=phrase['tempo']<=1.25 or not 0<=phrase['pad_after']<=.75:raise ValueError('Unbounded delivery edit')
  for part in phrase['parts']:
   row=d['sources'][part['source']]
   if not 0<=part['start']<part['end']<=row['seconds']+.001:raise ValueError('Invalid sentence source range')
 return meta

def render_scene(folder,source,scene_plan,gains,source_eq=None):
 from audio_derivation import check_unit,sha,VALIDATION_DEFAULTS
 from narration_edit import _copy_unit
 folder=pathlib.Path(folder);source=pathlib.Path(source);sid=scene_plan['scene'];out=folder/'raw'/(sid+'.wav');out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():raise FileExistsError(out)
 ids=list(dict.fromkeys(p['source'] for ph in scene_plan['phrases'] for p in ph['parts']));rows={};metas={};inputs=[]
 for src in ids:
  meta=check_unit(source,src);metas[src]=meta;parent=folder/'delivery-source'
  if not (parent/'raw'/(src+'.wav')).exists():_copy_unit(source,parent,src)
  wav=parent/'raw'/(src+'.wav');rows[src]={'wav_sha256':sha(wav),'meta_sha256':sha(str(wav)+'.json'),'seconds':meta['audio']['duration_seconds'],'gain_db':gains[src],'tone_eq_db':(source_eq or {}).get(src,0)}
  if not -6<=gains[src]<=6:raise ValueError('Excessive source-level correction')
  if not -2<=rows[src]['tone_eq_db']<=2:raise ValueError('Excessive source-tone correction')
  inputs+=['-i',str(wav)]
 filters=[];outputs=[]
 for i,ph in enumerate(scene_plan['phrases']):
  labels=[]
  for j,part in enumerate(ph['parts']):
   label=f'p{i}_{j}';idx=ids.index(part['source']);gain=gains[part['source']];tone=rows[part['source']]['tone_eq_db']
   filters.append(f'[{idx}:a]atrim=start={part["start"]}:end={part["end"]},asetpts=PTS-STARTPTS,atempo={ph["tempo"]:.9f},volume={gain:.4f}dB,equalizer=f=180:t=q:w=0.7:g={tone:.4f},aformat=sample_rates=24000:channel_layouts=mono[{label}]');labels.append('['+label+']')
  filters.append(''.join(labels)+f'concat=n={len(labels)}:v=0:a=1,apad=pad_dur={ph["pad_after"]}[sentence{i}]');outputs.append(f'[sentence{i}]')
 filters.append(''.join(outputs)+f'concat=n={len(outputs)}:v=0:a=1[out]')
 subprocess.run(['ffmpeg','-v','error','-n',*inputs,'-filter_complex',';'.join(filters),'-map','[out]','-ar','24000','-c:a','pcm_f32le',str(out)],check=True)
 values=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-f','f32le','-']))
 if sys.byteorder!='little':values.byteswap()
 if not values or not all(math.isfinite(v) for v in values):raise ValueError('Invalid conformed waveform')
 seconds=len(values)/24000;peak=max(abs(v) for v in values);rms=math.sqrt(sum(v*v for v in values)/len(values));clipped=sum(abs(v)>=.9999 for v in values)/len(values);wpm=len(scene_plan['text'].split())*60/seconds;lim=VALIDATION_DEFAULTS
 if not lim['min_segment_seconds']<=seconds<=lim['max_segment_seconds'] or peak>=lim['max_peak'] or rms<lim['min_rms'] or clipped>lim['max_clipped_sample_fraction'] or not lim['min_words_per_minute']<=wpm<=lim['max_words_per_minute']:raise ValueError('Conformed audio failed original mechanical safeguards')
 first=metas[ids[0]]
 meta={**first,'schema':'earnalism.video.sentence-delivery.v1','status':'DERIVED_REQUIRES_REVIEW','segment_id':sid,'output_path':str(out),'wav_sha256':sha(out),'settings':{**first['settings'],'text':scene_plan['text']},'audio':{'duration_seconds':seconds,'sample_rate':24000,'samples':len(values),'peak':peak,'rms':rms,'clipped_sample_fraction':clipped,'estimated_words_per_minute':wpm,'mechanical_checks':'PASS','human_listening_review':'PENDING','text_completeness':'FRESH_ASR_REQUIRED'},'derivation':{'kind':'sentence_delivery_conform','sources':rows,'plan':scene_plan,'pitch_shift':False,'passes_from_original':1,'fresh_alignment_required':True,'listening_review':'PENDING; consistency metrics cannot establish human delivery or age'}}
 pathlib.Path(str(out)+'.json').write_text(json.dumps(meta,indent=2));return validate(folder,meta)


def apply_replacements(episode,mapped,replacements):
 from asr_review import tokens
 canonical=tokens(' '.join(s['text'] for s in episode['scenes']));result=list(mapped)
 for replacement in replacements:
  phrase=tokens(replacement['text']);matches=[i for i in range(len(canonical)-len(phrase)+1) if canonical[i:i+len(phrase)]==phrase]
  if len(matches)!=1:raise ValueError('Replacement must match exactly one canonical passage')
  record=replacement['record']
  if record.get('unresolved_asr_edits'):raise ValueError('Unresolved replacement speech')
  new_tokens=[];times=[]
  for word in record.get('display_word_times',record['word_times']):
   for token in tokens(word['word']):new_tokens.append(token);times.append(dict(source=replacement['source'],start=word['start'],end=word['end']))
  if new_tokens!=phrase:raise ValueError('Replacement changes spoken words')
  i=matches[0];result[i:i+len(phrase)]=times
 return result


def quiet_boundary(samples,low,high,rate=24000):
 if high<=low:return max(0,min(len(samples)/rate,(low+high)/2))
 candidates=[]
 for index in range(max(0,round(low*rate)),min(len(samples),round(high*rate))+1,120):
  a=max(0,index-360);b=min(len(samples),index+360)
  if b>a:candidates.append((sum(v*v for v in samples[a:b])/(b-a),index))
 if not candidates:return max(0,min(len(samples)/rate,low))
 _,best=min(candidates)
 a=max(0,math.ceil(low*rate),best-48);b=min(len(samples),math.floor(high*rate)+1,best+49)
 return min(range(a,b),key=lambda i:abs(samples[i]))/rate
