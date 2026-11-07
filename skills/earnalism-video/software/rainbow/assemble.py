"""Four connected accepted-B groups -> seven actual-ASR rainbow scenes.

No synthesis, invented timing, word equivalence, pitch/tempo or source replacement.
Imported WAV/ASR/provenance are checked through the existing pinned B validator.
"""
from pathlib import Path
import argparse,copy,hashlib,json,math,re,shutil,subprocess,tempfile,zipfile
from ..thermal_touch import assemble as common
from ..thermal_touch import import_narration as transfer
from ..caption_layout import compose,quality
load,sha,require,write_new=common.load,common.sha,common.require,common.write_new
KINDS=('question','conditions','droplet','cone','move','circle','callback')
MARKS={'question':('question','step','change'),'conditions':('behind','rain'),'droplet':('enter','reflect','leave','dispersion'),'cone':('axis','angle','violet','cone','many'),'move':('move','different'),'circle':('circle','ground','unobstructed','below'),'callback':('callback',)}
OPTIONAL_MARKS={}
RESERVED=('.rainbow-assembly-lock.json','asr-review.json','caption-quality.json','timeline.json','props.json','clean-shorts-props.json','shorts-props.json','captions.srt','captions.vtt','transcript.txt','concat.txt','narration.wav','voice-binding.json','review.json','assembly-manifest.json','continuous-source.json','delivery-resolution.json','delivered-units.json','delivered-scene-units.json')

# This is a literal display-notation resolution for the one inspected archive,
# not a general spelling normalizer, numeric parser, or ASR acceptance threshold.
LITERAL_ARCHIVE_SHA='de2270a5c866ee69cfab63b7f630506a5190b71f88e6ef8f9359255628c42ba0'
LITERAL_INPUTS={'units.json':'00541c7f11bcbd761785c7afa6c94814a6fba0b2ef295ea459b60f1965ebcda7','scene-units.json':'d5da45918861e25d8febe146ea5c44701ae203e22eb15e13f1f3c21296dcf3f3','baseline-job.json':common.PUBLISHED_BASELINE_SHA256,'generation-plan.json':'e837973a9388e673319b7ce982fc5a3588f05d31035f81a53da9331ddb4c8c7c'}
LITERAL_SOURCE={
 'rainbow-connected-01':('dcef5043a4d553eb6836985d36e1724899f21fd70f0ca387b967af7a4172178b','cf3ccdb94d6a6c6391d6f5f9e4fe9ad2c613961728b0b6a22924c8e3909fcac7','27973c18dbcf236e3febe2202cb4e96c7611997ff8036658e8e6a15eedbc8f74'),
 'rainbow-connected-02':('dd1d43c5cdb2e125d98e89e4409047a8c169e49490d2d82068ead8fba7f40b19','066f8c02432c9e95b7647b3bd6b564413dd4e03e1d3ec9e9d38781487a3968ec','3b5820b9d6438fd4bc12e52d59d22e35f089928e476253541453f883876005bc'),
 'rainbow-connected-04':('c0c27ac5ecae63d5e8b4c387c2b07a93273605fd5f6c10ba82d4cdd75c8a24eb','e5c2b18be0ede88424f26a23ff35a682958a78cc86d82ad7b88faaa886a0f732','cc21735280b40c8fcfc5b30202300b58e97a886b189054a91b993d085cfd1f66')}
LITERAL_EDITS={
 'rainbow-connected-01':(('The drops sending colour to your eyes change.','The drops sending color to your eyes change.'),),
 'rainbow-connected-02':(('Different colours bend by different amounts.','Different colors bend by different amounts.'),('about forty-two degrees from that line.','about 42 degrees from that line.')),
 'rainbow-connected-04':(('The colours are real light.','The colors are real light.'),)}
LITERAL_DIFFERENCES={
 'rainbow-connected-01':[{'tag':'replace','expected':['colour'],'recognized':['color']}],
 'rainbow-connected-02':[{'tag':'replace','expected':['colours'],'recognized':['colors']},{'tag':'replace','expected':['forty','two'],'recognized':['42']}],
 'rainbow-connected-04':[{'tag':'replace','expected':['colours'],'recognized':['colors']}]}

def literal_delivery_text(group):
 require(group.get('id') in LITERAL_SOURCE,'No literal resolution policy for this source group')
 require(hashlib.sha256(group['text'].encode()).hexdigest()==LITERAL_SOURCE[group['id']][0],'Original literal source text changed')
 text=group['text']
 for old,new in LITERAL_EDITS[group['id']]:
  require(text.count(old)==1,'Missing/ambiguous exact literal phrase');text=text.replace(old,new,1)
 return text

def literal_semantic_scenes(scenes):
 result=copy.deepcopy(scenes)
 for scene in result:
  if scene['scene']=='question':
   scene['text']=scene['text'].replace('sending colour to your eyes','sending color to your eyes',1)
   scene['anchors']['change']=scene['anchors']['change'].replace('sending colour','sending color',1)
  elif scene['scene']=='droplet':
   scene['text']=scene['text'].replace('Different colours bend','Different colors bend',1)
   scene['anchors']['dispersion']=scene['anchors']['dispersion'].replace('Different colours bend','Different colors bend',1)
  elif scene['scene']=='cone':
   scene['text']=scene['text'].replace('forty-two degrees','42 degrees',1)
   scene['anchors']['angle']='42 degrees'
  elif scene['scene']=='callback':scene['text']=scene['text'].replace('The colours are real light.','The colors are real light.',1)
 return result

def validate_literal_alignment(original,delivered,alignment):
 require(delivered['text']==literal_delivery_text(original),'Delivered text changed beyond the four exact literal edits')
 differences=common.differences(original['text'],alignment.get('recognized',''))
 require(differences==LITERAL_DIFFERENCES[original['id']],'An unreviewed addition/omission/substitution remains')
 require(not common.differences(delivered['text'],alignment.get('recognized','')),'Delivered display text does not match actual recognition')
 require(not common.differences(alignment['recognized'],' '.join(w['word'] for w in alignment.get('word_times',[]))),'Recognized words/timestamps differ')
 return differences

def validate_delivery_resolution(root,resolution,groups,scenes):
 root=Path(root)
 require(resolution.get('schema')=='earnalism.rainbow-literal-delivery-resolution.v1' and resolution.get('state')=='RESOLVED_LITERAL_ORTHOGRAPHY_NUMBER_NOTATION','Unsupported/pending literal resolution')
 require(resolution.get('archive_sha256')==LITERAL_ARCHIVE_SHA and sha(root/'narration-transfer/source.zip')==LITERAL_ARCHIVE_SHA,'Different or changed narration archive')
 require(resolution.get('prepared_inputs')==LITERAL_INPUTS and all(sha(root/n)==h for n,h in LITERAL_INPUTS.items()),'Original prepared inputs changed')
 require(groups==load(root/'units.json') and scenes==load(root/'scene-units.json'),'Loaded source inputs differ from the bound originals')
 require(set(resolution.get('groups',{}))==set(LITERAL_SOURCE),'Unexpected/missing literal resolution group')
 delivered=copy.deepcopy(groups)
 for group in delivered:
  if group['id'] not in LITERAL_SOURCE:continue
  original=next(g for g in groups if g['id']==group['id']);text_hash,audio_hash,alignment_hash=LITERAL_SOURCE[group['id']];record=resolution['groups'][group['id']]
  wav=root/'imported/raw'/f"{group['id']}.wav";alignment_path=root/'imported/alignment'/f"{group['id']}.json"
  require(record.get('original_text_sha256')==text_hash and record.get('audio_sha256')==audio_hash==sha(wav) and record.get('alignment_sha256')==alignment_hash==sha(alignment_path),'Literal resolution source binding stale')
  group['text']=literal_delivery_text(original)
  require(record.get('delivered_text')==group['text'] and record.get('delivered_text_sha256')==hashlib.sha256(group['text'].encode()).hexdigest(),'Literal delivered-text binding changed')
  alignment=load(alignment_path);require(alignment.get('audio_sha256')==audio_hash,'Alignment not bound to current audio')
  require(record.get('raw_differences')==validate_literal_alignment(original,group,alignment),'Literal differences changed')
 semantic=literal_semantic_scenes(scenes);validate_units(delivered,semantic)
 return resolution,delivered,semantic

def create_delivery_resolution(root):
 root=Path(root);groups,scenes=load(root/'units.json'),load(root/'scene-units.json')
 resolution={'schema':'earnalism.rainbow-literal-delivery-resolution.v1','state':'RESOLVED_LITERAL_ORTHOGRAPHY_NUMBER_NOTATION','archive_sha256':LITERAL_ARCHIVE_SHA,'prepared_inputs':LITERAL_INPUTS,'groups':{},'scope':'Only colour/color, colours/colors and forty-two/42 at the four inspected literal positions; no semantic substitutions, automatic stemming or audio/timing changes.','human_listening':'PENDING','publication_approved':False}
 for group in groups:
  if group['id'] not in LITERAL_SOURCE:continue
  text=literal_delivery_text(group);t,a,l=LITERAL_SOURCE[group['id']]
  resolution['groups'][group['id']]={'original_text_sha256':t,'audio_sha256':a,'alignment_sha256':l,'delivered_text':text,'delivered_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'raw_differences':LITERAL_DIFFERENCES[group['id']]}
 validate_delivery_resolution(root,resolution,groups,scenes)
 write_new(root/'delivery-resolution.json',resolution)
 return resolution

def load_delivery_resolution(root,groups,scenes):
 path=Path(root)/'delivery-resolution.json'
 if not path.exists():return None,copy.deepcopy(groups),copy.deepcopy(scenes)
 return validate_delivery_resolution(root,load(path),groups,scenes)

def resolved_alignment_audit(original,delivered,alignment,source,root):
 raw_differences=validate_literal_alignment(original,delivered,alignment)
 original_audit,_=common.alignment_audit(original,alignment,source['audio_sha256'],source['duration'])
 audit,words=common.alignment_audit(delivered,alignment,source['audio_sha256'],source['duration'])
 require(not audit['differences'],'Literal delivery still has unresolved ASR differences')
 audit.update({'expected':original['text'],'delivered_text':delivered['text'],'raw_differences':raw_differences,'word_time_differences':original_audit['word_time_differences'],'original_differences':original_audit['differences'],'automatic_equivalence_applied':False,'resolution':{'kind':'EXACT_SOURCE_BOUND_DISPLAY_ORTHOGRAPHY_AND_NUMBER_NOTATION','file':'delivery-resolution.json','sha256':sha(Path(root)/'delivery-resolution.json'),'original_recognition_and_word_times_preserved':True,'word_timing_changed':False,'listening':'PENDING','note':'Notation-only engineering resolution; not a new pronunciation, naturalness or human-listening decision.'}})
 return audit,words

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
  require(isinstance(scenes,list) and tuple(s.get('scene') for s in scenes)==KINDS,'Seven rainbow semantic scenes required in order')
  require(len({s.get('id') for s in scenes})==7,'Semantic scene IDs must be unique')
  for s in scenes:
   actual=set(s.get('anchors',{}));expected=set(MARKS[s['scene']])
   require(not {'start','end','marks'}&set(s) and expected<=actual and actual-expected<=OPTIONAL_MARKS.get(s['scene'],set()),'Missing/unsupported actual-audio scene anchors or invented timing')
   require(all(common.tokens(v) for v in s['anchors'].values()),'Empty anchor')
  require(common.tokens(' '.join(g['text'] for g in groups))==common.tokens(' '.join(s['text'] for s in scenes)),'Grouping changed the spoken word sequence')
 return groups

def import_archive(archive_path,root):
 root,archive_path=Path(root).resolve(),Path(archive_path).resolve();root.mkdir(parents=True,exist_ok=True)
 require(not any((root/n).exists() for n in ('.rainbow-import-lock.json','imported','narration-transfer','transfer-receipt.json')),'Preserve previous/partial import; use a fresh source root')
 groups,baseline=load(root/'units.json'),load(root/'baseline-job.json');validate_units(groups,load(root/'scene-units.json'));common.validate_baseline(baseline)
 transfer.preflight_zip_container(archive_path);digest=sha(archive_path);inputs={n:sha(root/n) for n in ('units.json','scene-units.json','baseline-job.json','generation-plan.json')}
 with zipfile.ZipFile(archive_path) as archive:
  manifest,raw_manifest=transfer.inspect_archive(archive,groups)
  with tempfile.TemporaryDirectory(prefix='.rainbow-source-verify-',dir=root) as temp:
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
   write_new(root/'.rainbow-import-lock.json',{'state':'EXCLUSIVE_PRIVATE_RAINBOW_IMPORT','archive_sha256':digest,'publication_approved':False})
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
  out.append({**s,'start':start,'end':end,'marks':marks})
 return out

def assemble(root,output_dir=None):
 root=Path(root).resolve();out=Path(output_dir).resolve() if output_dir else root
 groups,scenes,baseline=load(root/'units.json'),load(root/'scene-units.json'),load(root/'baseline-job.json');validate_units(groups,scenes);common.validate_baseline(baseline)
 resolution,delivered_groups,delivered_scenes=load_delivery_resolution(root,groups,scenes)
 delivered_by_id={g['id']:g for g in delivered_groups}
 require(not any((out/n).exists() for n in RESERVED),'Existing/partial assembly preserved; use a fresh output directory');out.mkdir(parents=True,exist_ok=True)
 write_new(out/RESERVED[0],{'state':'EXCLUSIVE_PRIVATE_RAINBOW_ASSEMBLY','publication_approved':False})
 inputs={n:sha(root/n) for n in ('units.json','scene-units.json','baseline-job.json','generation-plan.json')};audits=[];validated=[]
 if resolution is not None:inputs['delivery-resolution.json']=sha(root/'delivery-resolution.json')
 for g in groups:
  wav=root/'imported/raw'/f"{g['id']}.wav";meta=Path(str(wav)+'.json');alignment=root/'imported/alignment'/f"{g['id']}.json"
  try:
   source=common.validate_source(g,wav,load(meta),baseline)
   if resolution is not None and g['id'] in LITERAL_SOURCE:audit,words=resolved_alignment_audit(g,delivered_by_id[g['id']],load(alignment),source,root)
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
 write_new(out/'continuous-source.json',{'schema':'earnalism.rainbow-four-groups-seven-scenes.v1','physical_generation_groups':source_spans,'semantic_scene_count':7,'group_count':4,'semantic_boundaries_may_be_inside_continuous_take':True,'source_WAVs_untouched':True,'normalization_scope':'One existing whole-body normalization; no per-word, phrase or scene gain/pitch/tempo/pause edits'})
 write_new(out/'voice-binding.json',{'source':'Exact accepted Qwen Ryan B recipe; four connected thought groups, seven actual-ASR semantic scenes','baseline_sha256':common.PUBLISHED_BASELINE_SHA256,'worker_sha256':common.WORKER_SHA256,'instruction_sha256':hashlib.sha256(baseline['segments'][0]['instruct'].encode()).hexdigest(),'generation':baseline['generation'],'dtype':baseline['dtype'],'attention':baseline['attention'],'seed_base':baseline['segments'][0]['seed'],'raw_audio':{g['id']:s['audio_sha256'] for g,_,s,_ in validated},'input_files':inputs,'narration_sha256':sha(out/'narration.wav'),'normalization_filter':common.NORMALIZE_FILTER,'output_sample_rate':48000,'no_tempo_or_pitch_change':True,'source_wavs_preserved':True,'new_recording':True,'new_recording_listening':'PENDING','publication_approved':False})
 write_new(out/'review.json',{'state':'PRIVATE_NEW_NARRATION_REQUIRES_REVIEW','factual':'PENDING','graphics_captions':'PENDING','rights':'PENDING','listening_av':'PENDING','technical_delivery':'PENDING','publication_approved':False})
 require(all(sha(root/n)==h for n,h in inputs.items()),'Source changed during assembly')
 write_new(out/'assembly-manifest.json',{'state':'ASSEMBLED_PRIVATE_REQUIRES_REVIEW','source_root':str(root),'input_files':inputs,'output_files':{n:sha(out/n) for n in (*RESERVED,'delivered-units.json','delivered-scene-units.json') if n!='assembly-manifest.json' and (out/n).is_file()},'new_recording_listening':'PENDING','publication_approved':False})
 return {'output':str(out),'duration':offset,'groups':4,'scenes':7,'caption_cues':len(cues),'listening_av':'PENDING','publication_approved':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['import','assemble']);p.add_argument('root',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();print(json.dumps(import_archive(a.archive,a.root) if a.action=='import' else assemble(a.root,a.output),indent=2))
