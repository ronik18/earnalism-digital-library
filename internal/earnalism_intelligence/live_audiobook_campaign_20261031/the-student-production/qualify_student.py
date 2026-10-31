from pathlib import Path
import json,hashlib,re,sys,datetime
R=Path('/tmp/earnalism-main-approved-integration');O=Path('/tmp/earnalism-student-preflight-20261031');sys.path.insert(0,str(O/'worker'))
import production_adapter as adapter,pipeline_core as core
D=R/'data/controlled_publications/the-student'
load=lambda p:json.loads(p.read_text())
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
book=load(D/'public_book.json');reader=load(D/'reader_manifest.json');source=load(D/'source_evidence.json');approval=load(D/'approval_evidence.json');checks=load(D/'checksum_manifest.json');live=load(O/'live-book.json')
manifest=load(R/'internal/earnalism_intelligence/live_audiobook_campaign_20261031/public-manifests/the-student.json')
assert live['slug']==book['slug']==manifest['book']['slug']=='the-student'
assert live['id']==book['id']==manifest['book']['id']
assert live['publication_status']=='LIVE_APPROVED' and live['reader_enabled'] and live['is_published']
assert book['approved_to_publish'] and book['qa_status']=='QA_PASSED'
assert approval['approved_to_publish'] and approval['qa_status']=='QA_PASSED'
assert source['commercial_use_allowed'] and source['verification_status']=='approved'
checked={}
for e in checks['files']:
 p=(D/e['file']).resolve();assert p.is_relative_to(D.resolve());assert h(p)==e['sha256'],e['file'];checked[e['file']]=e['sha256']
chapters=[];bindings=[]
for m,remote in zip(reader['chapters'],manifest['chapters'],strict=True):
 p=D/'chapters'/(m['id']+'.json');payload=load(p);assert h(p)==checked['chapters/'+m['id']+'.json']
 assert hashlib.sha256(payload['content'].encode()).hexdigest()==payload['content_hash']
 merged={**m,'content':payload['content'],'content_hash':payload['content_hash'],'file_sha256':h(p)}
 version=adapter.reader_content_version(merged);assert version==remote['content_version'],(version,remote['content_version'])
 chapters.append(merged);bindings.append({'chapter':m['id'],'live_content_version':version,'content_sha256':payload['content_hash']})
text='\n\n'.join(c['content'] for c in chapters);raw=(O/'pg1944.txt').read_text()
assert h(O/'pg1944.txt')==source['source_hash']
start=list(re.finditer(r'(?m)^THE STUDENT\s*$',raw))[-1].end();end=raw.index('\nIN THE RAVINE',start)
assert core.collapse(raw[start:end])==core.collapse(text)
assert not re.search(r'project gutenberg|\*\*\*.*(?:START|END)|copyright|trademark',text,re.I)
artifact={'slug':'the-student','book':book,'chapters':chapters,'reader':reader,'source':source,'approval':approval,'files':{n:h(D/n) for n in adapter.REQUIRED},'canonical_text':text,'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'word_count':len(core.words(text)),'live_audio_enabled':False,'live_observation':live,'artifact_path':str(D),'rights_evidence':{'status':'SEPARATE_AUDIO_BASIS_QUALIFIED_FOR_IN_PRIVATE_PRODUCTION; PACKAGE_ACCEPTANCE_PENDING'},'live_reader_evidence':{'bindings':bindings,'manifest_version':manifest['version']},'source_equivalence':'Whole selected story exactly matches verified source under whitespace-only comparison; all canonical bytes and public chapter versions matched; no reader files mutated.'}
import narration_layout
run=O/'production/titles/the-student'/artifact['source_sha256'][:16]
run.mkdir(parents=True,exist_ok=True)
layout=narration_layout.build_reference_layout(artifact['chapters'],(O/'pg1944.txt').read_bytes(),'https://www.gutenberg.org/cache/epub/1944/pg1944.txt',prose_chapter_ids=['chapter-001'])
core.atomic_json(run/'narration_layout.json',layout)
ctx=core.prepare_title(artifact,O/'production')
# Keep the full exact text and conservative reflective direction. No spelling/word substitutions.
ep=core.read_json(ctx['run']/'editorial_plan.json');ep['base_instruction']='Narrate this reflective English literary story clearly in a warm, sincere, unhurried but varied voice. Let the cold opening and gradual sense of human connection emerge through natural phrasing. Keep dialogue subtle and every word exact; pronounce Russian names carefully. Avoid solemn monotony, theatrical biblical voices, whispering and forced emotional emphasis.';ep['music_enabled']=False
core.atomic_json(ctx['run']/'editorial_plan.json',ep);ctx=core.prepare_title(artifact,O/'production')
selected=core.representative_segments(ctx['segments'])
summary={'status':'SOURCE_AND_PRIVATE_AUDIO_BASIS_QUALIFIED_RUNTIME_PENDING','slug':'the-student','word_count':artifact['word_count'],'source_sha256':artifact['source_sha256'],'raw_source_sha256':h(O/'pg1944.txt'),'source_story_start':start,'source_story_end':end,'whole_story_exact_whitespace_match':True,'canonical_chapter_checksums':'PASS','live_chapter_content_bindings':bindings,'source_files_changed':False,'segmented_units':len(ctx['segments']),'narration_layout':ctx['narration_layout'],'layout_source':layout['chapters']['chapter-001'],'representative_units':[{'id':x['segment_id'],'text_sha256':x['text_sha256'],'text':x['text']} for x in selected],'plan_hash':ctx['plan_hash'],'pronunciation_review_terms':['Ivan Velikopolsky','Vasilisa','Lukerya','Rurik','Judas'],'voice_candidate':{'speaker':'Ryan','model':'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice','revision':'0c0e3051f131929182e2c023b9537f8b1c68adfe','qualified_for_this_title':False},'music':'SILENCE_REFLECTIVE_PROSE','private_generation_allowed_basis':{'territories':['IN'],'recording_owner':'Owner-directed new Earnalism recording; no borrowed audio','literary_basis':'Exact Chekhov/Garnett selected story. Documented last creator death 1946; selected publication no later than 1918. India sixty-year term elapsed under sections 22/24; section14 sound-recording right considered independently from prior Reader-only record. New owner task authorizes creating an exact new recording; does not convert old Reader record into audio license.','model_license':'Pinned official model Apache-2.0; built-in Ryan, no cloning; retain upstream model/runtime licenses and notices. Package-specific recording/territorial acceptance remains unperformed.'},'production_cost_envelope':{'preferred_option':'Existing free CUDA runtime, no purchased credits or new subscription','max_provider_spend_usd':0,'max_runtime_minutes':30,'max_allocations':1,'max_attempts_per_unit':1,'automatic_retries':False,'scope':'Representative audition only; full title waits for actual audition quality evidence','fallback':'Do not silently switch provider or use unqualified fallback TTS'},'new_spend_usd':0,'generation_performed':False,'public_release_ready':False,'legacy_adapter_issue':'Old production_adapter requires LIVE_APPROVED in prepared canonical metadata, but current publication derivation leaves canonical public_book READY_FOR_ACTIVATION_GLOBAL_GATE while actual customer API is LIVE_APPROVED. No flags altered or legacy check claimed PASS; current source/checksum/version/whole-story checks performed independently.'}
core.atomic_json(O/'actual-source-preflight.json',summary)
print(json.dumps({k:summary[k] for k in ['status','word_count','segmented_units','plan_hash','source_sha256','source_files_changed']}))
