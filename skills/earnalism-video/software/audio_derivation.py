"""Hash-bound, bounded tempo derivatives of unchanged Qwen recordings."""
import pathlib,json,hashlib,subprocess,array,math,re,shutil,sys
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
from qwen_worker import VALIDATION_DEFAULTS

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def check_unit(folder,sid):
 folder=pathlib.Path(folder);wav=folder/'raw'/(sid+'.wav');meta=load(str(wav)+'.json')
 if meta.get('wav_sha256')!=sha(wav):raise ValueError('Worker audio binding mismatch')
 if meta.get('audio',{}).get('mechanical_checks')!='PASS':raise ValueError('Unverified narration unit')
 if meta.get('provenance',{}).get('model_id')!='Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice':raise ValueError('Unexpected speech provider')
 if meta.get('status')=='DERIVED_REQUIRES_REVIEW':
  d=meta.get('derivation',{});source=folder/'source-raw'/(sid+'.wav');source_meta=pathlib.Path(str(source)+'.json')
  if d.get('kind')=='sentence_delivery_conform':
   from delivery_conform import validate
   return validate(folder,meta)
  if d.get('kind')=='source_preserving_voice_finish':
   from voice_finish import validate
   return validate(folder,meta)
  if d.get('kind')=='sentence_content_edit':
   from narration_edit import validate_edit
   return validate_edit(folder,meta)
  if d.get('kind')=='phrase_tempo_repair':
   parent=folder/'pace-source';original=check_unit(parent,sid)
   if sha(parent/'raw'/(sid+'.wav'))!=d['parent_wav_sha256'] or sha(parent/'raw'/(sid+'.wav.json'))!=d['parent_meta_sha256']:raise ValueError('Changed pacing parent')
   if original['provenance']!=meta['provenance']:raise ValueError('Pacing provider provenance changed')
   validate_phrase_plan(d['regions'],d['parent_seconds'])
   return meta
  if d.get('kind')!='pitch_preserving_tempo' or not .85<=d.get('tempo_factor',0)<=1.1:raise ValueError('Unapproved tempo derivative')
  if sha(source)!=d.get('source_wav_sha256') or sha(source_meta)!=d.get('source_meta_sha256'):raise ValueError('Changed derivative source')
  original=load(source_meta)
  if original.get('status')!='GENERATED_REQUIRES_REVIEW' or original.get('wav_sha256')!=sha(source) or original.get('audio',{}).get('mechanical_checks')!='PASS':raise ValueError('Unverified derivative source')
  if meta.get('provenance')!=original.get('provenance'):raise ValueError('Derivative provider provenance changed')
 elif meta.get('status')!='GENERATED_REQUIRES_REVIEW':raise ValueError('Unverified narration unit')
 return meta

def validate_phrase_plan(regions,seconds):
 """Only contiguous whole-phrase edits; no pitch or word-level processing."""
 end=0
 for r in regions:
  if abs(r['start']-end)>.00001 or r['end']<=r['start'] or not .75<=r['tempo']<=1.25:raise ValueError('Invalid phrase pacing plan')
  end=r['end']
 if not regions or abs(end-seconds)>.0001:raise ValueError('Phrase plan must cover original audio')

def repair_phrases(source_folder,dest_folder,scene,regions):
 """Preserve the selected performance, separately retaining its complete chain."""
 source_folder=pathlib.Path(source_folder);dest_folder=pathlib.Path(dest_folder);sid=scene['id'];meta=check_unit(source_folder,sid)
 if meta.get('derivation',{}).get('kind')=='phrase_tempo_repair':raise ValueError('Do not stack phrase repairs')
 wav=source_folder/'raw'/(sid+'.wav');seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(wav)]));validate_phrase_plan(regions,seconds)
 out=dest_folder/'raw'/(sid+'.wav')
 if out.exists():raise FileExistsError(out)
 parent=dest_folder/'pace-source'
 for sub in ('raw','source-raw'):
  (parent/sub).mkdir(parents=True,exist_ok=True)
  for suffix in ('.wav','.wav.json'):
   old=source_folder/sub/(sid+suffix);new=parent/sub/(sid+suffix)
   if old.exists():
    if new.exists():raise FileExistsError(new)
    shutil.copy2(old,new)
 filters=[]
 for i,r in enumerate(regions):
  filters.append(f'[0:a]atrim=start={r["start"]}:end={r["end"]},asetpts=PTS-STARTPTS,atempo={r["tempo"]}[a{i}]')
 filters.append(''.join(f'[a{i}]' for i in range(len(regions)))+f'concat=n={len(regions)}:v=0:a=1[out]')
 subprocess.run(['ffmpeg','-v','error','-n','-i',str(wav),'-filter_complex',';'.join(filters),'-map','[out]','-ar','24000','-c:a','pcm_f32le',str(out)],check=True)
 samples=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-f','f32le','-']))
 if sys.byteorder!='little':samples.byteswap()
 if not samples or not all(math.isfinite(v) for v in samples):raise ValueError('Invalid repaired waveform')
 peak=max(abs(v) for v in samples);rms=math.sqrt(sum(v*v for v in samples)/len(samples));duration=len(samples)/24000;clipped=sum(abs(v)>=.9999 for v in samples)/len(samples);wpm=len(scene['text'].split())*60/duration;limits=VALIDATION_DEFAULTS
 if not limits['min_segment_seconds']<=duration<=limits['max_segment_seconds'] or peak>=limits['max_peak'] or clipped>limits['max_clipped_sample_fraction'] or rms<limits['min_rms'] or not limits['min_words_per_minute']<=wpm<=limits['max_words_per_minute']:raise ValueError('Repaired audio failed original mechanical limits')
 result={**meta,'status':'DERIVED_REQUIRES_REVIEW','wav_sha256':sha(out),'audio':{'sample_rate':24000,'samples':len(samples),'duration_seconds':duration,'peak':peak,'rms':rms,'clipped_sample_fraction':clipped,'estimated_words_per_minute':wpm,'mechanical_checks':'PASS','human_listening_review':'PENDING','text_completeness':'REQUIRES_FRESH_ASR_ON_REPAIRED_AUDIO'},'derivation':{'kind':'phrase_tempo_repair','regions':regions,'parent_seconds':seconds,'parent_wav_sha256':sha(wav),'parent_meta_sha256':sha(str(wav)+'.json'),'pitch_shift':False,'fresh_alignment_required':True}}
 pathlib.Path(str(out)+'.json').write_text(json.dumps(result,indent=2));check_unit(dest_folder,sid);return result['derivation']

def derive_scene(source_folder,dest_folder,scene,target_wpm=122):
 source_folder=pathlib.Path(source_folder);dest_folder=pathlib.Path(dest_folder);sid=scene['id'];meta=check_unit(source_folder,sid)
 wav=source_folder/'raw'/(sid+'.wav');probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(wav)]));duration=float(probe['format']['duration']);words=len(scene['text'].split());raw_wpm=words*60/duration
 factor=max(.85,min(1.1,target_wpm/raw_wpm));out=dest_folder/'raw'/(sid+'.wav')
 for sub in ('raw','source-raw','config'):(dest_folder/sub).mkdir(exist_ok=True)
 if out.exists():raise FileExistsError(out)
 for suffix in ('.wav','.wav.json'):
  old=source_folder/'raw'/(sid+suffix);new=dest_folder/'source-raw'/(sid+suffix)
  if new.exists():raise FileExistsError(new)
  shutil.copy2(old,new)
 subprocess.run(['ffmpeg','-v','error','-n','-i',str(wav),'-af',f'atempo={factor:.9f}','-ar','24000','-c:a','pcm_f32le',str(out)],check=True)
 samples=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-f','f32le','-']))
 if sys.byteorder!='little':samples.byteswap()
 if not samples or not all(math.isfinite(v) for v in samples):raise ValueError('Invalid derived waveform')
 peak=max(abs(v) for v in samples);rms=math.sqrt(sum(v*v for v in samples)/len(samples));seconds=len(samples)/24000;clipped=sum(abs(v)>=.9999 for v in samples)/len(samples);wpm=len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b",scene['text']))*60/seconds;limits=VALIDATION_DEFAULTS
 if not limits['min_segment_seconds']<=seconds<=limits['max_segment_seconds'] or peak>=limits['max_peak'] or clipped>limits['max_clipped_sample_fraction'] or rms<limits['min_rms'] or not limits['min_words_per_minute']<=wpm<=limits['max_words_per_minute']:raise ValueError('Derived audio failed original mechanical limits')
 result={**meta,'status':'DERIVED_REQUIRES_REVIEW','wav_sha256':sha(out),'source_generation_audio':meta['audio'],'audio':{'sample_rate':24000,'samples':len(samples),'duration_seconds':seconds,'peak':peak,'rms':rms,'clipped_sample_fraction':clipped,'input_words':words,'estimated_words_per_minute':wpm,'codec_frames':None,'mechanical_checks':'PASS','failure_reasons':[],'text_completeness':'REQUIRES_FRESH_ASR_ON_DERIVED_AUDIO','human_listening_review':'PENDING'},'derivation':{'kind':'pitch_preserving_tempo','tempo_factor':factor,'target_wpm_including_pauses':target_wpm,'source_wpm_including_pauses':raw_wpm,'output_wpm_including_pauses':words*60/seconds,'source_wav_sha256':sha(wav),'source_meta_sha256':sha(str(wav)+'.json'),'pitch_shift':False,'fresh_alignment_required':True}}
 pathlib.Path(str(out)+'.json').write_text(json.dumps(result,indent=2));check_unit(dest_folder,sid);return result['derivation']
