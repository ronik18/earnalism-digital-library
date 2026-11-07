"""Four connected B generation groups -> six actual-ASR sky-colour scenes.

No synthesis, invented timing, word equivalence, pitch/tempo or source replacement.
Imported WAV/ASR/provenance are checked through the existing pinned B validator.
"""
from pathlib import Path
import argparse,copy,hashlib,json,math,re,shutil,subprocess,tempfile,zipfile
from ..thermal_touch import assemble as common
from ..thermal_touch import import_narration as transfer
from ..caption_layout import compose,quality
load,sha,require,write_new=common.load,common.sha,common.require,common.write_new
KINDS=('question','scattering','sky_path','prediction','sunset_path','callback')
MARKS={'question':('question','light'),'scattering':('mixed','redirect','shorter','red'),'sky_path':('away','toward','direct'),'prediction':('lower','longer','predict'),'sunset_path':('scatter','warm','identity','mixture'),'callback':('variation','sky','direct','callback')}
OPTIONAL_MARKS={'scattering':{'scatter'}}
RESERVED=('.sky-assembly-lock.json','asr-review.json','caption-quality.json','timeline.json','props.json','clean-shorts-props.json','shorts-props.json','captions.srt','captions.vtt','transcript.txt','concat.txt','narration.wav','voice-binding.json','review.json','assembly-manifest.json','continuous-source.json')

def validate_units(groups,scenes=None):
 require(isinstance(groups,list) and len(groups)==4,'Exactly four connected generation groups required')
 ids=[]
 for group in groups:
  require(isinstance(group,dict) and re.fullmatch(r'[A-Za-z0-9_-]+',group.get('id','')) and isinstance(group.get('text'),str),'Invalid generation group')
  text=group['text'];require(common.tokens(text) and len(text.split())<=65 and len(text)<=520,'Original worker65-word/520-character limit exceeded')
  require(text.rstrip().endswith(('.','!','?')) and not {'start','end','marks'}&set(group),'Group must end a complete thought without estimated timing')
  ids.append(group['id'])
 require(len(set(ids))==4,'Duplicate generation group ID')
 if scenes is not None:
  require(isinstance(scenes,list) and tuple(s.get('scene') for s in scenes)==KINDS,'Six sky semantic scenes required in order')
  require(len({s.get('id') for s in scenes})==6,'Semantic scene IDs must be unique')
  for s in scenes:
   actual=set(s.get('anchors',{}));expected=set(MARKS[s['scene']])
   require(not {'start','end','marks'}&set(s) and expected<=actual and actual-expected<=OPTIONAL_MARKS.get(s['scene'],set()),'Missing/unsupported actual-audio scene anchors or invented timing')
   require(all(common.tokens(v) for v in s['anchors'].values()),'Empty anchor')
  require(common.tokens(' '.join(g['text'] for g in groups))==common.tokens(' '.join(s['text'] for s in scenes)),'Grouping changed the spoken word sequence')
 return groups

# Observed episode06 delivery revisions only. These are not general ASR
# equivalences, stemming, spelling cleanup or permission to drop words.
DELIVERY_EDITS={
 'sky-connected-01':('visible colours.','visible colors.',{'tag':'replace','expected':['colours'],'recognized':['colors']}),
 'sky-connected-02':('sunlight scattered toward you','sunlight scatter toward you',{'tag':'replace','expected':['scattered'],'recognized':['scatter']}),
}

def load_delivery_resolution(root,groups,scenes):
 path=Path(root)/'delivery-resolution.json'
 if not path.exists():return None,copy.deepcopy(groups),copy.deepcopy(scenes)
 resolution=load(path)
 require(resolution.get('schema')=='earnalism.sky-delivery-revision.v1' and resolution.get('state')=='ACCEPTED_EDITORIAL_DELIVERY_REVISION','Delivery revision is pending or unsupported')
 require(resolution.get('original_units_sha256')==sha(Path(root)/'units.json') and resolution.get('original_scenes_sha256')==sha(Path(root)/'scene-units.json'),'Delivery revision script binding stale')
 require(set(resolution.get('groups',{}))==set(DELIVERY_EDITS),'Unexpected/missing scoped delivery revision')
 delivered=copy.deepcopy(groups);semantic=copy.deepcopy(scenes)
 for group in delivered:
  if group['id'] not in DELIVERY_EDITS:continue
  old,new,difference=DELIVERY_EDITS[group['id']];record=resolution['groups'][group['id']]
  require(group['text'].count(old)==1,'Delivery revision phrase is not unique')
  text=group['text'].replace(old,new,1)
  require(record.get('original_text_sha256')==hashlib.sha256(group['text'].encode()).hexdigest() and record.get('accepted_delivery_text')==text and record.get('accepted_delivery_text_sha256')==hashlib.sha256(text.encode()).hexdigest(),'Delivery revision changed more than the accepted literal phrase')
  wav=Path(root)/'imported/raw'/f"{group['id']}.wav";alignment=Path(root)/'imported/alignment'/f"{group['id']}.json"
  require(record.get('audio_sha256')==sha(wav) and record.get('alignment_sha256')==sha(alignment),'Delivery revision audio/alignment binding stale')
  raw=load(alignment)
  require(raw.get('audio_sha256')==record['audio_sha256'] and common.differences(group['text'],raw.get('recognized',''))==[difference] and not common.differences(raw.get('recognized',''),' '.join(w['word'] for w in raw.get('word_times',[]))),'Unexpected ASR addition/omission/replacement remains unresolved')
  require(not common.differences(text,raw['recognized']),'Accepted delivery text does not match recognized audio words')
  if group['id']=='sky-connected-02':
   corroboration=record.get('corroboration',{});relative=Path(corroboration.get('file',''))
   require(not relative.is_absolute() and '..' not in relative.parts and relative.parts,'Unsafe second-pass evidence path')
   proof=Path(__file__).resolve().parents[2]/relative
   require(sha(proof)==corroboration.get('sha256'),'Second-pass ASR evidence changed')
   retained_relative=Path(corroboration.get('retained_file',''));require(not retained_relative.is_absolute() and '..' not in retained_relative.parts and retained_relative.parts,'Unsafe retained second-pass path')
   require(sha(Path(root)/retained_relative)==corroboration.get('sha256'),'Retained second-pass ASR evidence changed')
   raw_proof=proof.read_text();require('SECOND_ASR ' in raw_proof and 'RETURN_CODE 0' in raw_proof,'Incomplete second-pass ASR result')
   second=json.loads(raw_proof.split('SECOND_ASR ',1)[1].splitlines()[0])
   require(second.get('audio_sha256')==record['audio_sha256'] and second.get('model',{}).get('model_revision')==common.ASR_REVISION and second.get('beam_size')==1 and second.get('prompt') is None and second.get('source_unchanged') is True,'Second-pass ASR source/control mismatch')
   require(not common.differences(text,' '.join(seg['text'] for seg in second['segments'])),'Second-pass ASR does not corroborate accepted delivered wording')
  group['text']=text
 for scene in semantic:
  if scene['scene']=='scattering':
   scene['text']=scene['text'].replace('visible colours.','visible colors.',1)
   scene['anchors']['mixed']=scene['anchors']['mixed'].replace('visible colours','visible colors',1)
  if scene['scene']=='sky_path':
   scene['text']=scene['text'].replace('sunlight scattered toward you','sunlight scatter toward you',1)
   scene['anchors']['toward']=scene['anchors']['toward'].replace('scattered toward you','scatter toward you',1)
 validate_units(delivered,semantic)
 return resolution,delivered,semantic


def delivery_audit(original_group,delivered_group,alignment,source,resolution,root):
 require(original_group['id'] in DELIVERY_EDITS,'No delivery resolution policy for this source group')
 old,new,expected_difference=DELIVERY_EDITS[original_group['id']]
 require(original_group['text'].count(old)==1 and delivered_group['text']==original_group['text'].replace(old,new,1),'Unsupported delivered wording')
 record=resolution['groups'][original_group['id']]
 alignment_path=Path(root)/'imported/alignment'/f"{original_group['id']}.json"
 require(record['audio_sha256']==source['audio_sha256'] and record['alignment_sha256']==sha(alignment_path) and alignment==load(alignment_path),'Unbound delivery audit source or recognition')
 original,_=common.alignment_audit(original_group,alignment,source['audio_sha256'],source['duration'])
 require(original['raw_differences']==[expected_difference] and not original['word_time_differences'],'Unexpected unresolved source words')
 accepted,words=common.alignment_audit(delivered_group,alignment,source['audio_sha256'],source['duration'])
 require(not accepted['differences'],'Accepted delivery script still has unresolved ASR differences')
 accepted['original_expected']=original['expected'];accepted['expected']=original['expected']
 accepted['accepted_delivery_text']=delivered_group['text']
 accepted['raw_differences']=original['raw_differences'];accepted['word_time_differences']=original['word_time_differences']
 accepted['original_differences']=original['differences'];accepted['automatic_equivalence_applied']=False
 accepted['resolution']={'kind':'EXPLICIT_SOURCE_BOUND_DELIVERY_SCRIPT_REVISION','file':'delivery-resolution.json','sha256':sha(Path(root)/'delivery-resolution.json'),'not_ASR_equivalence':True,'listening':'PENDING','note':'Raw unit, source, recognition and word times preserved. Captions and semantic anchors use the explicitly accepted delivered text. Same-model second ASR pass is not an independent listener.'}
 return accepted,words

def import_archive(archive_path,root):
 root,archive_path=Path(root).resolve(),Path(archive_path).resolve();root.mkdir(parents=True,exist_ok=True)
 require(not any((root/n).exists() for n in ('.sky-import-lock.json','imported','narration-transfer','transfer-receipt.json')),'Preserve previous/partial import; use a fresh source root')
 groups,baseline=load(root/'units.json'),load(root/'baseline-job.json');validate_units(groups,load(root/'scene-units.json'));common.validate_baseline(baseline)
 transfer.preflight_zip_container(archive_path);digest=sha(archive_path);inputs={n:sha(root/n) for n in ('units.json','scene-units.json','baseline-job.json','generation-plan.json')}
 with zipfile.ZipFile(archive_path) as archive:
  manifest,raw_manifest=transfer.inspect_archive(archive,groups)
  with tempfile.TemporaryDirectory(prefix='.sky-source-verify-',dir=root) as temp:
   stage=Path(temp)
   for name in transfer.required_paths(groups):
    dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with archive.open(name) as source:transfer.copy_stream_new(source,dest)
    require(sha(dest)==manifest[name],'Staged archive member changed')
   audits=[]
   for group in groups:
    wav=stage/'raw'/f"{group['id']}.wav";meta=load(Path(str(wav)+'.json'));alignment=load(stage/'alignment'/f"{group['id']}.json")
    source=common.validate_source(group,wav,meta,baseline);audit,_=common.alignment_audit(group,alignment,source['audio_sha256'],source['duration']);audits.append(audit)
   require(sha(archive_path)==digest and all(sha(root/n)==h for n,h in inputs.items()),'Source changed during import')
   write_new(root/'.sky-import-lock.json',{'state':'EXCLUSIVE_PRIVATE_SKY_IMPORT','archive_sha256':digest,'publication_approved':False})
   imported=root/'imported';imported.mkdir();retained=root/'narration-transfer';retained.mkdir()
   for name in transfer.required_paths(groups):
    dest=imported/name;dest.parent.mkdir(parents=True,exist_ok=True)
    with (stage/name).open('rb') as source:transfer.copy_stream_new(source,dest)
   with archive_path.open('rb') as source:transfer.copy_stream_new(source,retained/'source.zip')
   require(sha(retained/'source.zip')==digest,'Retained archive differs')
   (retained/'transfer-manifest.json').write_bytes(raw_manifest)
   receipt={'state':'IMPORTED_PRIVATE_SOURCE_REQUIRES_ASSEMBLY_AND_REVIEW','archive_sha256':digest,'archive_retained_path':'narration-transfer/source.zip','members_verified':len(manifest),'generation_groups_verified':len(groups),'prepared_inputs':inputs,'imported_files':{n:manifest[n] for n in transfer.required_paths(groups)},'asr_audits':audits,'asr_differences_unresolved':sum(len(a['differences']) for a in audits),'new_recording_listening':'PENDING','publication_approved':False}
   write_new(root/'transfer-receipt.json',receipt)
 return receipt

def map_scenes(scenes,words,duration):
 """Map semantic token spans to real word boundaries across connected groups."""
 expected=common.tokens(' '.join(s['text'] for s in scenes));lexical=[];origin=[]
 for i,w in enumerate(words):
  for token in common.tokens(w['word']):lexical.append(token);origin.append(i)
 require(lexical==expected,'Actual aligned words differ from semantic script')
 offsets=[];cursor=0
 for s in scenes:
  n=len(common.tokens(s['text']));require(cursor==0 or origin[cursor]!=origin[cursor-1],'Scene onset falls inside an unsplit ASR word')
  offsets.append((cursor,cursor+n));cursor+=n
 starts=[0.]+[words[origin[a]]['start'] for a,b in offsets[1:]]
 out=[]
 for i,(s,(a,b)) in enumerate(zip(scenes,offsets)):
  start,end=starts[i],starts[i+1] if i+1<len(starts) else duration
  subset=words[origin[a]:origin[b-1]+1]
  marks={key:common.actual_anchor(subset,phrase)-start for key,phrase in s['anchors'].items()}
  require(all(0<=v<end-start for v in marks.values()),'Scene anchor outside its actual-audio hold')
  order=MARKS[s['scene']];require(all(marks[x]<marks[y] for x,y in zip(order,order[1:])),'Actual spoken anchors out of order')
  if s['scene']=='scattering' and 'scatter' in marks:require(marks['mixed']<=marks['scatter']<marks['redirect'],'First-scatter anchor must precede its spoken redirection explanation')
  out.append({**s,'start':start,'end':end,'marks':marks})
 return out

def assemble(root,output_dir=None):
 root=Path(root).resolve();out=Path(output_dir).resolve() if output_dir else root
 groups,scenes,baseline=load(root/'units.json'),load(root/'scene-units.json'),load(root/'baseline-job.json');validate_units(groups,scenes);common.validate_baseline(baseline)
 resolution,delivered_groups,delivered_scenes=load_delivery_resolution(root,groups,scenes)
 delivered_by_id={g['id']:g for g in delivered_groups}
 require(not any((out/n).exists() for n in RESERVED),'Existing/partial assembly preserved; use a fresh output directory');out.mkdir(parents=True,exist_ok=True)
 write_new(out/RESERVED[0],{'state':'EXCLUSIVE_PRIVATE_SKY_ASSEMBLY','publication_approved':False})
 inputs={n:sha(root/n) for n in ('units.json','scene-units.json','baseline-job.json','generation-plan.json')};audits=[];validated=[]
 if resolution is not None:
  inputs['delivery-resolution.json']=sha(root/'delivery-resolution.json')
  for record in resolution['groups'].values():
   if record.get('corroboration'):
    rel=record['corroboration']['retained_file'];inputs[rel]=sha(root/rel)
 for g in groups:
  wav=root/'imported/raw'/f"{g['id']}.wav";meta=Path(str(wav)+'.json');alignment=root/'imported/alignment'/f"{g['id']}.json"
  try:
   source=common.validate_source(g,wav,load(meta),baseline)
   if resolution is not None and g['id'] in DELIVERY_EDITS:audit,words=delivery_audit(g,delivered_by_id[g['id']],load(alignment),source,resolution,root)
   else:audit,words=common.alignment_audit(g,load(alignment),source['audio_sha256'],source['duration'])
   audits.append(audit)
   if audit['differences']:continue
   validated.append((g,wav,source,words))
   for p in (wav,meta,alignment):inputs[str(p.relative_to(root))]=sha(p)
  except (OSError,ValueError,KeyError,TypeError,subprocess.CalledProcessError) as exc:audits.append({'unit':g['id'],'source_validation':'FAIL','differences':[{'error':str(exc)}],'listening':'PENDING'})
 write_new(out/'asr-review.json',audits);require(len(validated)==4 and all(a.get('source_validation')=='PASS' and not a.get('differences') for a in audits),'Unresolved actual source/ASR differences; no narration assembled')
 words=[];offset=0.;source_spans=[]
 for g,wav,source,actual in validated:
  words.extend(dict(w,start=w['start']+offset,end=w['end']+offset) for w in actual);source_spans.append({'id':g['id'],'start':offset,'end':offset+source['duration'],'raw_audio_sha256':source['audio_sha256']});offset+=source['duration']
 actual_scenes=map_scenes(delivered_scenes,words,offset)
 try:cues=compose(words);issues=quality(cues)
 except ValueError as exc:write_new(out/'caption-quality.json',{'issues':[str(exc)]});raise
 write_new(out/'caption-quality.json',{'issues':issues,'cue_count':len(cues),'timing':'Actual ASR word times from four continuous group WAVs'})
 require(not issues and common.tokens(' '.join(c['text'] for c in cues))==common.tokens(' '.join(g['text'] for g in delivered_groups)),'Caption readability/word partition issue')
 write_new(out/'timeline.json',{'duration':offset,'timing':'Actual WAV lengths and actual-ASR semantic anchors, not per-group scene guesses','scenes':actual_scenes})
 props={'duration':offset,'scenes':actual_scenes,'captions':cues,'burnCaptions':False,'outro':True}
 for name,value in [('props.json',props),('clean-shorts-props.json',props),('shorts-props.json',{**props,'burnCaptions':True})]:write_new(out/name,value)
 for ext,sep in [('srt',','),('vtt','.')]:
  body='\n\n'.join((str(i+1)+'\n' if ext=='srt' else '')+f"{common.stamp(c['start'],sep)} --> {common.stamp(c['end'],sep)}\n{c['text']}" for i,c in enumerate(cues));write_new(out/f'captions.{ext}',('WEBVTT\n\n' if ext=='vtt' else '')+body+'\n',as_json=False)
 write_new(out/'transcript.txt','\n\n'.join(s['text'] for s in delivered_scenes)+'\n',as_json=False)
 write_new(out/'concat.txt','ffconcat version 1.0\n'+'\n'.join(common.concat_line(wav) for _,wav,_,_ in validated)+'\n',as_json=False)
 common.normalize_narration(out/'concat.txt',out/'narration.wav');require(abs(common.probe_wav(out/'narration.wav')['duration']-offset)<=.02,'Assembly unexpectedly changed duration')
 for name in ('units.json','scene-units.json','baseline-job.json','generation-plan.json'):
  if out!=root:shutil.copy2(root/name,out/name)
 if resolution is not None:
  if out!=root:shutil.copy2(root/'delivery-resolution.json',out/'delivery-resolution.json')
  write_new(out/'delivered-units.json',delivered_groups);write_new(out/'delivered-scene-units.json',delivered_scenes)
 write_new(out/'continuous-source.json',{'schema':'earnalism.sky-four-groups-six-scenes.v1','physical_generation_groups':source_spans,'semantic_scene_count':6,'group_count':4,'semantic_boundaries_may_be_inside_continuous_take':True,'source_WAVs_untouched':True,'normalization_scope':'One existing whole-body normalization; no per-word, phrase or scene gain/pitch/tempo/pause edits'})
 write_new(out/'voice-binding.json',{'source':'Exact accepted Qwen Ryan B recipe; four connected thought groups, six actual-ASR semantic scenes','baseline_sha256':common.PUBLISHED_BASELINE_SHA256,'worker_sha256':common.WORKER_SHA256,'instruction_sha256':hashlib.sha256(baseline['segments'][0]['instruct'].encode()).hexdigest(),'generation':baseline['generation'],'dtype':baseline['dtype'],'attention':baseline['attention'],'seed_base':baseline['segments'][0]['seed'],'raw_audio':{g['id']:s['audio_sha256'] for g,_,s,_ in validated},'input_files':inputs,'narration_sha256':sha(out/'narration.wav'),'normalization_filter':common.NORMALIZE_FILTER,'output_sample_rate':48000,'no_tempo_or_pitch_change':True,'source_wavs_preserved':True,'new_recording':True,'new_recording_listening':'PENDING','publication_approved':False})
 write_new(out/'review.json',{'state':'PRIVATE_NEW_NARRATION_REQUIRES_REVIEW','factual':'PENDING','graphics_captions':'PENDING','rights':'PENDING','listening_av':'PENDING','technical_delivery':'PENDING','publication_approved':False})
 require(all(sha(root/n)==h for n,h in inputs.items()),'Source changed during assembly')
 write_new(out/'assembly-manifest.json',{'state':'ASSEMBLED_PRIVATE_REQUIRES_REVIEW','source_root':str(root),'input_files':inputs,'output_files':{n:sha(out/n) for n in (*RESERVED,'delivered-units.json','delivered-scene-units.json') if n!='assembly-manifest.json' and (out/n).is_file()},'new_recording_listening':'PENDING','publication_approved':False})
 return {'output':str(out),'duration':offset,'groups':4,'scenes':6,'caption_cues':len(cues),'listening_av':'PENDING','publication_approved':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['import','assemble']);p.add_argument('root',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();print(json.dumps(import_archive(a.archive,a.root) if a.action=='import' else assemble(a.root,a.output),indent=2))
