"""Auditable sentence-boundary content edits; source speech and retries stay immutable."""
import pathlib,json,shutil,subprocess,array,math,sys,re

def _copy_unit(source,dest,sid):
 from audio_derivation import check_unit
 meta=check_unit(source,sid)
 for sub in ('raw','source-raw'):
  for suffix in ('.wav','.wav.json'):
   old=source/sub/(sid+suffix)
   if old.exists():
    new=dest/sub/(sid+suffix);new.parent.mkdir(parents=True,exist_ok=True)
    if new.exists():raise FileExistsError(new)
    shutil.copy2(old,new)
 kind=meta.get('derivation',{}).get('kind')
 if kind=='phrase_tempo_repair':_copy_unit(source/'pace-source',dest/'pace-source',sid)
 if kind=='source_preserving_voice_finish':_copy_unit(source/'finish-source',dest/'finish-source',sid)
 if kind=='sentence_delivery_conform':
  for source_sid in meta['derivation']['sources']:_copy_unit(source/'delivery-source',dest/'delivery-source',source_sid)
 if kind=='sentence_content_edit':
  for row in meta['derivation']['inputs']:_copy_unit(source/'edit-sources'/row['slot'],dest/'edit-sources'/row['slot'],row['scene'])
 return meta

def validate_edit(folder,meta):
 from audio_derivation import check_unit,sha
 d=meta['derivation'];total=0
 if d.get('pitch_shift') is not False or d.get('tempo_changed') is not False:raise ValueError('Content edit must preserve pitch and tempo')
 for row in d['inputs']:
  if not re.fullmatch(r'[a-z0-9-]+',row['slot']) or not re.fullmatch(r'[a-z0-9-]+',row['scene']):raise ValueError('Unsafe edit source')
  parent=pathlib.Path(folder)/'edit-sources'/row['slot'];original=check_unit(parent,row['scene']);wav=parent/'raw'/(row['scene']+'.wav')
  if sha(wav)!=row['wav_sha256'] or sha(str(wav)+'.json')!=row['meta_sha256']:raise ValueError('Changed content edit source')
  if original['settings'].get('speaker')!='Ryan' or original['settings'].get('instruct')!=meta['settings'].get('instruct'):raise ValueError('Content edit voice profile changed')
  for key in ('model_id','model_revision','worker_sha256'):
   if original['provenance'].get(key)!=meta['provenance'].get(key):raise ValueError('Content edit provider changed')
  if not 0<=row['start']<row['end']<=original['audio']['duration_seconds']+.0001:raise ValueError('Invalid content edit range')
  if not -6<=row.get('gain_db',0)<=6:raise ValueError('Unbounded edit gain')
  total+=row['end']-row['start']
 if not d['inputs'] or abs(total-meta['audio']['duration_seconds'])>.005:raise ValueError('Content edit duration mismatch')
 return meta

def edit(scene,dest,parts):
 """parts are source folder, scene id, start/end seconds at reviewed quiet boundaries."""
 from audio_derivation import sha,check_unit,VALIDATION_DEFAULTS
 dest=pathlib.Path(dest);out=dest/'raw'/(scene['id']+'.wav')
 if out.exists():raise FileExistsError(out)
 out.parent.mkdir(parents=True,exist_ok=True);rows=[];inputs=[];filters=[];first=None
 for i,part in enumerate(parts):
  source=pathlib.Path(part['folder']);sid=part['scene'];meta=check_unit(source,sid);first=first or meta
  start,end=part['start'],part['end']
  if not 0<=start<end<=meta['audio']['duration_seconds']+.0001:raise ValueError('Invalid content edit range')
  slot='input-'+str(i);parent=dest/'edit-sources'/slot;_copy_unit(source,parent,sid);wav=parent/'raw'/(sid+'.wav')
  gain=part.get('gain_db',0)
  if not -6<=gain<=6:raise ValueError('Unbounded edit gain')
  inputs+=['-i',str(wav)];filters.append(f'[{i}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,aformat=sample_rates=24000:channel_layouts=mono,volume={gain}dB[a{i}]')
  rows.append(dict(slot=slot,scene=sid,start=start,end=end,gain_db=gain,wav_sha256=sha(wav),meta_sha256=sha(str(wav)+'.json')))
 filters.append(''.join(f'[a{i}]' for i in range(len(parts)))+f'concat=n={len(parts)}:v=0:a=1[out]')
 subprocess.run(['ffmpeg','-v','error','-n',*inputs,'-filter_complex',';'.join(filters),'-map','[out]','-ar','24000','-c:a','pcm_f32le',str(out)],check=True)
 samples=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-f','f32le','-']))
 if sys.byteorder!='little':samples.byteswap()
 if not samples or not all(math.isfinite(v) for v in samples):raise ValueError('Invalid edited audio')
 seconds=len(samples)/24000;peak=max(abs(v) for v in samples);rms=math.sqrt(sum(v*v for v in samples)/len(samples));clipped=sum(abs(v)>=.9999 for v in samples)/len(samples);wpm=len(scene['text'].split())*60/seconds;lim=VALIDATION_DEFAULTS
 if not lim['min_segment_seconds']<=seconds<=lim['max_segment_seconds'] or peak>=lim['max_peak'] or clipped>lim['max_clipped_sample_fraction'] or rms<lim['min_rms'] or not lim['min_words_per_minute']<=wpm<=lim['max_words_per_minute']:raise ValueError('Content edit failed original mechanical safeguards')
 result={**first,'status':'DERIVED_REQUIRES_REVIEW','schema':'earnalism.video.narration-edit.v1','segment_id':scene['id'],'output_path':str(out),'settings':{**first['settings'],'text':scene['text']},'wav_sha256':sha(out),'publication_approved':False,'audio':{'sample_rate':24000,'duration_seconds':seconds,'samples':len(samples),'peak':peak,'rms':rms,'clipped_sample_fraction':clipped,'estimated_words_per_minute':wpm,'mechanical_checks':'PASS','human_listening_review':'PENDING','text_completeness':'REQUIRES_FRESH_ASR'},'derivation':{'kind':'sentence_content_edit','inputs':rows,'pitch_shift':False,'tempo_changed':False,'new_generation':False,'retry_budgets_reset':False,'fresh_alignment_required':True,'cut_review':'Quiet sentence boundaries chosen against source word times; listen to joins'}}
 pathlib.Path(str(out)+'.json').write_text(json.dumps(result,indent=2));return validate_edit(dest,result)
