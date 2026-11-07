"""Earnalism English candidate pipeline. No production mutation capabilities."""
from __future__ import annotations
from owner_audio_policy import AudioGenerationExcluded, assert_audio_allowed, audio_exclusion_reason, audio_identity
import csv, hashlib, json, re, subprocess, time, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path
import narration_layout

VERSION = 'earnalism.qwen_ace_colab.v3'
QWEN_ID = 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice'
DIMENSIONS = ('expression','emotional_balance','pace','pause_and_punctuation','pronunciation','anti_robotic_texture','anti_choppy_join')
SLUG_RE = re.compile(r'[a-z0-9][a-z0-9_-]*\Z')

def require(condition, message):
    if not condition: raise ValueError(message)

def now(): return datetime.now(timezone.utc).isoformat()
def digest(value): return hashlib.sha256(value).hexdigest()
def hash_text(value): return digest(value.encode('utf-8'))
def canonical_json(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':'))
def object_hash(value): return hash_text(canonical_json(value))
def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp = path.with_name(path.name+'.writing')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); temp.replace(path)
def safe_relative(root, name):
    require(isinstance(name,str) and name and not Path(name).is_absolute(), 'Invalid relative artifact path')
    root=Path(root).resolve(); target=(root/name).resolve()
    require(target.is_relative_to(root), 'Artifact path escapes its root')
    return target
def get_json(url, timeout=40):
    req=urllib.request.Request(url,headers={'User-Agent':'Earnalism-Colab-Candidate/3','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        require(r.status==200,'Read-only HTTP request failed')
        return json.loads(r.read())
def words(text): return re.findall(r"[^\W_]+(?:['’][^\W_]+)?",text,re.UNICODE)
def collapse(text): return re.sub(r'\s+',' ',text).strip()

def read_production_catalog(api_base):
    from production_adapter import read_production_catalog as implementation
    return implementation(api_base)

def book_language(book):
    from production_adapter import book_language as implementation
    return implementation(book)

def validate_artifact(repo, live):
    from production_adapter import validate_artifact as implementation
    return implementation(repo, live)


def inventory(repo, snapshot, root, selected_slugs=()):
    rows=[]; eligible=[]
    for live in snapshot['books']:
        row={'slug':live['slug'],'title':live.get('title'),'language':book_language(live),'audio_already_live':live.get('audio_enabled') is True}
        if audio_exclusion_reason(live): row.update(status='EXCLUDED_OWNER_READER_ONLY',reason=audio_exclusion_reason(live))
        elif row['language']!='en': row.update(status='OUT_OF_SCOPE' if row['language']=='bn' else 'LANGUAGE_REVIEW_REQUIRED',reason='English-only notebook')
        else:
            try:
                a=validate_artifact(repo,live)
                row.update(status='ELIGIBLE_PRIVATE_CANDIDATE',word_count=a['word_count'],source_sha256=a['source_sha256'],reason='')
                if not selected_slugs or live['slug'] in selected_slugs: eligible.append(a)
            except Exception as e: row.update(status='BLOCKED_SOURCE_OR_LIVE_CHECK',reason=str(e))
        rows.append(row)
    missing=set(selected_slugs)-{r['slug'] for r in rows}
    require(not missing,'Requested titles absent from live catalog: '+','.join(sorted(missing)))
    eligible.sort(key=lambda a:(a['word_count'],a['slug']))
    atomic_json(Path(root)/'production_catalog_snapshot.json',snapshot)
    atomic_json(Path(root)/'catalog_queue.json',{'generated_at':now(),'rows':rows,'selected': [a['slug'] for a in eligible]})
    with (Path(root)/'catalog_queue.csv').open('w',newline='',encoding='utf-8') as f:
        keys=['slug','title','language','audio_already_live','status','word_count','source_sha256','reason']; w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    return eligible,rows

ABBREVS={'mr','mrs','ms','dr','st','prof','sr','jr','vs','etc','e.g','i.e','vol','no','fig','p','pp'}
def sentence_spans(text):
    """Conservative source-preserving spans; no arbitrary punctuation deletion."""
    start=0; spans=[]
    for match in re.finditer(r'[.!?]+["\u201d\u2019\')\]]*(?=\s+|$)',text):
        end=match.end(); prefix=text[start:end].rstrip('"\u201d\u2019\')]')
        token=re.search(r'([A-Za-z.]+)\.$',prefix)
        if token and (token.group(1).lower() in ABBREVS or re.fullmatch(r'(?:[A-Za-z]\.)*[A-Za-z]',token.group(1))): continue
        if match.group().startswith('.') and len(match.group().strip('"\u201d\u2019\')]'))>1: continue
        if text[start:end].strip(): spans.append((start,end))
        start=end
        while start<len(text) and text[start].isspace():start+=1
    if text[start:].strip():spans.append((start,len(text)))
    return spans

def segment_chapters(chapters, max_words=65, max_chars=520, manual_boundaries=None):
    segments=[]
    for c in chapters:
        text=c['content']; paras=list(re.finditer(r'\S[\s\S]*?(?=\n[ \t]*\n|\Z)',text))
        for pi,pm in enumerate(paras,1):
            p=pm.group(); boundaries=[0]+sorted({x-pm.start() for x in (manual_boundaries or {}).get(c['id'],[]) if pm.start()<x<pm.end()})+[len(p)]
            spans=[]
            for left,right in zip(boundaries,boundaries[1:]):
                spans.extend((left+a,left+b) for a,b in sentence_spans(p[left:right]))
            pieces=[]
            for a,b in spans:
                chunk=p[a:b]
                if len(words(chunk))>max_words or len(chunk)>max_chars:
                    cuts=[m.end() for m in re.finditer(r'[,;:\u2014]\s+',chunk)]
                    cuts.append(len(chunk)); prior=0
                    for cut in cuts:
                        if chunk[prior:cut].strip():pieces.append((a+prior,a+cut))
                        prior=cut
                else:pieces.append((a,b))
            packed=[]
            for a,b in pieces:
                require(len(words(p[a:b]))<=max_words and len(p[a:b])<=max_chars,'Long clause needs reviewed segmentation in chapter '+c['id']+' at source offsets '+str(pm.start()+a)+'..'+str(pm.start()+b)+'; add a reviewed whitespace-boundary cut in segmentation_plan.json')
                if packed and len(words(p[packed[-1][0]:b]))<=max_words and len(p[packed[-1][0]:b])<=max_chars:
                    packed[-1]=(packed[-1][0],b)
                else:packed.append((a,b))
            for a,b in packed:
                original=p[a:b]; spoken=collapse(original)
                segments.append({'segment_id':f"u{len(segments)+1:06d}",'chapter_id':c['id'],'chapter_title':c.get('title',''),'chapter_order':c['order'],'paragraph_id':f"{c['id']}-p{pi:05d}",'source_start':pm.start()+a,'source_end':pm.start()+b,'canonical_text':original,'text':spoken,'text_sha256':hash_text(spoken)})
    require(segments,'No segments')
    require(collapse(' '.join(s['canonical_text'] for s in segments))==collapse('\n\n'.join(c['content'] for c in chapters)),'Segmentation changed source coverage')
    return segments

MOODS={
 'reflective':{'keys':['memory','remember','thought','life','years','alone'],'voice':'Use thoughtful, restrained phrasing and gentle sentence endings.','cue':'Sparse warm sustained strings and spacious soft piano; reflective, unhurried, understated.'},
 'tender':{'keys':['love','gift','kindness','dear','heart','child'],'voice':'Use warmth and restrained tenderness, with clear articulation.','cue':'Gentle sustained strings with occasional soft piano; tender and quiet, no dramatic swell.'},
 'suspense':{'keys':['ghost','fear','death','dark','blood','murder','terror','dread'],'voice':'Keep tension understated and controlled; never shout or exaggerate horror.','cue':'Sparse low strings and soft dark ambient textures; quietly tense, no sudden impacts or alarms.'},
 'wonder':{'keys':['adventure','island','journey','magic','dream','sea'],'voice':'Use gentle curiosity and a clear, steady narrative pace.','cue':'Airy chamber textures and sparse soft woodwind; gentle wonder and ample silence.'},
 'expository':{'keys':['money','business','principle','rule','method','science','argument'],'voice':'Explain clearly with measured emphasis; avoid a promotional or lecture-like rhythm.','cue':'Minimal soft sustained harmony; neutral contemplative instrumental texture, little rhythmic activity.'}}
BASE_INSTRUCT='Narrate in clear natural English as a thoughtful literary storyteller. Keep the same steady voice, a comfortable moderate pace, precise pronunciation, natural punctuation pauses and restrained expression. The recording should be dry and clean.'
def infer_mood(text):
    toks=[x.lower() for x in words(text)]; scores={name:sum(toks.count(k) for k in v['keys']) for name,v in MOODS.items()}
    winner=max(scores,key=scores.get)
    return winner if scores[winner]>0 else 'reflective'

def prepare_title(artifact, root):
    assert_audio_allowed(artifact, require_identity=True)
    slug=artifact['slug'];run=Path(root)/'titles'/slug/artifact['source_sha256'][:16];run.mkdir(parents=True,exist_ok=True)
    source_path=run/'canonical_text.txt';source_path.write_text(artifact['canonical_text'],encoding='utf-8')
    chapter_meta=[{k:c[k] for k in ('id','order','title','content','file_sha256')} for c in artifact['chapters']]
    atomic_json(run/'canonical_chapters.json',chapter_meta)
    boundary_file=run/'segmentation_plan.json'
    if not boundary_file.exists():atomic_json(boundary_file,{'source_sha256':artifact['source_sha256'],'cuts':[],'note':'Optional chapter-relative character offsets at whitespace boundaries. Supply chapter_id, offset, reviewer, reviewed_at and note for every manual cut; manuscript remains unchanged.'})
    boundary_plan=read_json(boundary_file);require(boundary_plan.get('source_sha256')==artifact['source_sha256'],'Stale segmentation plan')
    boundaries={};by_id={c['id']:c for c in artifact['chapters']}
    for cut in boundary_plan.get('cuts',[]):
        cid=cut.get('chapter_id');offset=cut.get('offset');require(cid in by_id and type(offset) is int,'Invalid manual segmentation boundary')
        text=by_id[cid]['content'];require(0<offset<len(text) and (text[offset].isspace() or text[offset-1].isspace()),'Manual cut must be inside the chapter at whitespace')
        require(cut.get('reviewer') and cut.get('reviewed_at') and cut.get('note'),'Manual cut needs editorial review attribution')
        boundaries.setdefault(cid,[]).append(offset)
    # Layout projection is separate evidence: manuscript/checksums stay unchanged.
    layout_path=run/'narration_layout.json'
    bundled_path=Path(__file__).with_name('narration_layouts.json')
    bundled=read_json(bundled_path) if bundled_path.is_file() else {}
    candidate=bundled.get(slug)
    if not layout_path.exists() and candidate and candidate.get('source_sha256')==artifact['source_sha256']:
        old_editorial=read_json(run/'editorial_plan.json') if (run/'editorial_plan.json').is_file() else {}
        require(not old_editorial.get('segment_overrides'),'Narration layout changes segment IDs; explicitly remap existing segment overrides before adopting the reference layout')
        atomic_json(layout_path,candidate)
    layout=read_json(layout_path) if layout_path.is_file() else None
    if layout:
        segments=narration_layout.segment_with_layout(artifact['chapters'],layout,segment_chapters,manual_boundaries=boundaries)
        layout_info={'status':'EXACT_REFERENCE_WHITESPACE_PROJECTION',
                     'ledger_sha256':object_hash(layout),'ledger_file_sha256':file_hash(layout_path),
                     'reference_url':layout['reference_url'],'reference_bytes_sha256':layout['reference_bytes_sha256'],
                     'paragraph_basis':'REFERENCE_PROSE_PARAGRAPH_FOR_SELECTED_CHAPTERS',
                     'source_offsets':'UNCHANGED_CANONICAL_CHAPTER_CHARACTER_OFFSETS',
                     'canonical_display_block_ordinals_are_not_narration_paragraph_ordinals':True,
                     'human_editorial_approval':False,'editorial_review_required':True}
    else:
        segments=segment_chapters(artifact['chapters'],manual_boundaries=boundaries)
        layout_info={'status':'CANONICAL_LAYOUT_UNPROJECTED','paragraph_basis':'CANONICAL_PARAGRAPH',
                     'source_offsets':'UNCHANGED_CANONICAL_CHAPTER_CHARACTER_OFFSETS'}
    diagnostics=narration_layout.layout_risk_flags(artifact['chapters'])
    for flag in diagnostics:
        flag['resolved_by_exact_reference_projection']=bool(layout and flag['chapter_id'] in layout['chapters'] and flag['code']=='POSSIBLE_PHYSICAL_LINE_WRAPS_AS_PARAGRAPHS')
    layout_blockers=[f for f in diagnostics if not f['resolved_by_exact_reference_projection']]
    atomic_json(run/'narration_layout_diagnostics.json',{'source_sha256':artifact['source_sha256'],'narration_layout':layout_info,'flags':diagnostics})
    gen={'schema_version':VERSION,'slug':slug,'source_sha256':artifact['source_sha256'],'segments':segments,'alignment_granularity':'synthesis_chunk_not_word','all_canonical_chapters_included':True,'narration_layout':layout_info}
    planfile=run/'generation_plan.json'
    # A plan can be edited only through lexicon/instructions, never silent source replacement.
    atomic_json(planfile,gen)
    editorial_path=run/'editorial_plan.json'
    if not editorial_path.exists():
        contexts={c['id']:{'mood':infer_mood(c['content']),'basis':'keyword-based suggestion from this exact chapter; editorially adjustable','source_excerpt':collapse(c['content'])[:300]} for c in artifact['chapters']}
        profiles_path=Path(__file__).with_name('title_profiles.json');profiles=read_json(profiles_path) if profiles_path.exists() else {}
        profile=profiles.get(slug,{})
        atomic_json(editorial_path,{'source_sha256':artifact['source_sha256'],'speaker':'Ryan','base_instruction':profile.get('base_instruction',BASE_INSTRUCT),'title_profile':profile,'music_enabled':profile.get('suggested_music','sparse_reflective')!='none','chapters':contexts,'segment_overrides':{},'pronunciations':[]})
    ep=read_json(editorial_path); require(ep.get('source_sha256')==artifact['source_sha256'],'Stale editorial plan')
    require(ep.get('speaker') in ('Ryan','Aiden'),'Choose Ryan or Aiden')
    ledger=[]
    for s in segments:
        setting=ep['chapters'].get(s['chapter_id'],{});mood=setting.get('mood','reflective');require(mood in MOODS,'Unknown scene mood')
        override=ep.get('segment_overrides',{}).get(s['segment_id'],{})
        s['instruct']=override.get('instruct',ep['base_instruction']+' '+MOODS[mood]['voice'])
        s['speaker']=ep['speaker']
        for lex in ep.get('pronunciations',[]):
            require(lex.get('reviewer') and lex.get('reviewed_at') and lex.get('surface') and lex.get('spoken'),'Pronunciation changes require a reviewed source mapping')
            if lex.get('chapter_id') not in (None,s['chapter_id']):continue
            replacement,count=re.subn(r'(?<!\w)'+re.escape(lex['surface'])+r'(?!\w)',lambda m:lex['spoken'],s['text'])
            if count:ledger.append({'segment_id':s['segment_id'],'surface':lex['surface'],'spoken':lex['spoken'],'count':count,'reviewer':lex['reviewer']});s['text']=replacement
        s['text_sha256']=hash_text(s['text'])
        s['seed']=int(override.get('seed',1701+int(s['segment_id'][1:])))
    atomic_json(run/'spoken_text_map.json',{'source_sha256':artifact['source_sha256'],'changes':ledger,'segments':segments})
    atomic_json(run/'input_manifest.json',{'schema_version':VERSION,'slug':slug,'title':artifact['book']['title'],'author':artifact['book'].get('author'),'source_sha256':artifact['source_sha256'],'evidence_files':artifact['files'],'rights_basis':artifact['source'].get('rights_basis'),'source_url':artifact['source'].get('source_url'),'rights_evidence':artifact.get('rights_evidence',{}),'live_reader_evidence':artifact.get('live_reader_evidence',{}),'rights_status':'EXISTING_SOURCE_EVIDENCE_RETAINED_AUDIO_TERRITORY_REVIEW_REQUIRED','live_audio_initially_enabled':artifact['live_audio_enabled'],'release_ready':False,'observed_at':now(),'source_equivalence':artifact['source_equivalence'],'narration_layout':layout_info,'layout_review_flags':layout_blockers})
    return {'artifact':artifact,'root':Path(root),'run':run,'segments':segments,'editorial':ep,'source_path':source_path,'plan_hash':object_hash(segments),'narration_layout':layout_info,'layout_blockers':layout_blockers}

def representative_segments(segments):
    indices=[0,len(segments)-1,len(segments)//2,max(range(len(segments)),key=lambda i:len(words(segments[i]['text']))),max(range(len(segments)),key=lambda i:sum(segments[i]['text'].count(m) for m in ',;:!?')),next((i for i,s in enumerate(segments) if '?' in s['text']),len(segments)//3)]
    chosen=list(dict.fromkeys(indices))
    for i in range(len(segments)):
        if len(chosen)>=min(6,len(segments)):break
        if i not in chosen:chosen.append(i)
    return [segments[i] for i in chosen]

def qwen_job(ctx,model,stage='audition',minutes=20):
    assert_audio_allowed(ctx, require_identity=True)
    require(stage in ('audition','endurance','narration'),'Unknown Qwen generation stage')
    require(ctx['editorial'].get('speaker') in ('Ryan','Aiden'),'Choose Ryan or Aiden')
    require(isinstance(minutes,(int,float)) and minutes>0,'Endurance duration must be positive')
    run=Path(ctx['run']).resolve(); selected=ctx['segments']
    require(selected,'Cannot generate an empty source plan')
    if stage=='audition': selected=representative_segments(selected)
    elif stage=='endurance':
        out=[];wc=0
        for s in selected:
            out.append(s);wc+=len(words(s['text']))
            if wc>=minutes*150:break
        selected=out
    result=[]
    # Ryan is the chosen narrator. An optional comparison never changes a
    # retained Ryan segment's identity, path, text or synthesis/cache settings.
    compare=ctx['editorial'].get('compare_audition_voices',False)
    require(type(compare) is bool,'compare_audition_voices must be true or false')
    speakers=('Ryan','Aiden') if stage=='audition' and compare else (ctx['editorial']['speaker'],)
    for speaker in speakers:
        for s in selected:
            q={**s,'speaker':speaker}
            # Both audition voices are one worker job: each candidate needs its own ID.
            # Keep the canonical source ID separately for editorial traceability.
            if stage=='audition':
                q['source_segment_id']=s['segment_id']
                q['segment_id']=s['segment_id']+'--audition-'+speaker.lower()
            q['cache_key']=object_hash({'pipeline':VERSION,'source':ctx['artifact']['source_sha256'],'segment':q,'model':model['model_revision']})
            folder=run/'auditions'/speaker if stage=='audition' else run/'units'/speaker
            folder.mkdir(parents=True,exist_ok=True);q['output_path']=str(folder/(s['segment_id']+'.wav'));result.append(q)
    job={**model,**audio_identity(ctx),'segments':result,'journal_path':str(run/'qwen_attempts.jsonl'),'report_path':str(run/(stage+'_generation_report.json')),'max_attempts':3,'device':'cuda:0','dtype':'auto','attention':'eager','generation':{'max_new_tokens':2048,'do_sample':True,'top_k':50,'top_p':1.0,'temperature':0.9,'repetition_penalty':1.05},'stop_flag_path':str(run/'STOP')}
    policy=ctx.get('synthesis',{})
    job['dtype']=policy.get('dtype',job['dtype']);job['attention']=policy.get('attention',job['attention'])
    job['generation'].update(policy.get('generation',{}))
    return job

def human_review_template(ctx,audios,kind):
    return {'schema_version':VERSION,'kind':kind,'slug':ctx['artifact']['slug'],'source_sha256':ctx['artifact']['source_sha256'],'plan_sha256':ctx['plan_hash'],'audio_sha256':audios,'reviewer':'','reviewed_at':'','all_listed_audio_listened':False,'source_checked':False,'dimensions':{k:None for k in DIMENSIONS},'overall_score':None,'confidence':None,'content_errors':[],'unresolved_defects':None,'approved_for_next_stage':False,'notes':''}
def ensure_review(path,template):
    path=Path(path)
    if not path.exists():atomic_json(path,template)
    elif any(read_json(path).get(k)!=template.get(k) for k in ('source_sha256','plan_sha256','audio_sha256')):
        atomic_json(path.with_name(path.stem+'.STALE.'+str(time.time_ns())+'.json'),read_json(path));atomic_json(path,template)
    return read_json(path)
def validate_review(review,expected,score_min=8.9,confidence_min=.90):
    issues=[]
    for key in ('slug','kind','source_sha256','plan_sha256','audio_sha256'):
        if review.get(key)!=expected.get(key):issues.append('Review binding mismatch: '+key)
    if not review.get('reviewer') or not review.get('reviewed_at'):issues.append('Reviewer and timestamp required')
    else:
        try:require(datetime.fromisoformat(review['reviewed_at'].replace('Z','+00:00')).tzinfo is not None,'Timestamp needs timezone')
        except Exception:issues.append('Invalid review timestamp')
    for key in ('all_listed_audio_listened','source_checked','approved_for_next_stage'):
        if review.get(key) is not True:issues.append('Required review statement: '+key)
    d=review.get('dimensions',{})
    if set(d)!=set(DIMENSIONS):issues.append('Missing or unexpected review dimensions')
    numeric=lambda x: type(x) in (int,float) and x==x
    if any(not numeric(d.get(k)) or not score_min<=d[k]<=10 for k in DIMENSIONS):issues.append('Listening dimension threshold not met')
    if not numeric(review.get('overall_score')) or not score_min<=review['overall_score']<=10:issues.append('Overall listening threshold not met')
    if not numeric(review.get('confidence')) or not confidence_min<=review['confidence']<=1:issues.append('Reviewer confidence threshold not met; this is not statistical accuracy')
    if review.get('content_errors')!=[] or type(review.get('unresolved_defects')) is not int or review['unresolved_defects']!=0:issues.append('Unresolved defects/content errors')
    return issues

def propose_cues(ctx,max_cues=3):
    assert_audio_allowed(ctx, require_identity=True)
    segments=ctx['segments'];chapter_ids=list(dict.fromkeys(s['chapter_id'] for s in segments));count=min(max_cues,len(chapter_ids))
    selected=list(dict.fromkeys(chapter_ids[round(i*(len(chapter_ids)-1)/max(1,count-1))] for i in range(count)))
    cues=[]
    for i,cid in enumerate(selected,1):
        rows=[s for s in segments if s['chapter_id']==cid];context=ctx['editorial']['chapters'][cid];mood=context['mood']
        cues.append({'cue_id':f'cue{i:03d}','chapter_id':cid,'start_segment_id':rows[0]['segment_id'],'end_segment_id':rows[min(1,len(rows)-1)]['segment_id'],'context_note':f"{rows[0]['chapter_title']}: {context['source_excerpt']}",'caption':'Instrumental literary audiobook underscore. '+MOODS[mood]['cue']+' No vocals, speech, choir, heavy percussion, sudden rises, sirens or recognizable existing melody.','duration_seconds':30,'bpm':60,'keyscale':'C minor' if mood=='suspense' else 'C major','seed':9200+i})
    path=ctx['run']/'cue_plan.json'
    if not path.exists():atomic_json(path,{'source_sha256':ctx['artifact']['source_sha256'],'cues':cues,'selection':'Deterministic content-based suggestions; inspect/edit for literary fit. No claim of semantic comprehension.'})
    plan=read_json(path);require(plan.get('source_sha256')==ctx['artifact']['source_sha256'],'Stale cue plan')
    return plan['cues']

def production_replacement_plan(ctx, delivery, candidate_issues):
    """Bind replacement intent to actual candidate bytes; never perform a release.

    Existing B2 objects and production caches are not synthesis inputs. Only the
    current Qwen worker's hash-verified unit cache may be resumed. Storage keys,
    active-version preconditions and cache receipts belong to the importer.
    """
    assert_audio_allowed(ctx, require_identity=True)
    run=Path(ctx['run']).resolve(); artifact=ctx['artifact']; assets=[]
    slug=artifact['slug']; require(SLUG_RE.fullmatch(slug),'Unsafe replacement slug')
    audio_paths={str(Path(p).resolve()) for p in delivery['audio_files']}
    for raw in delivery['audio_files']+delivery.get('evidence_files',[]):
        path=Path(raw).resolve()
        require(path.is_relative_to(run) and path.is_file(),'Replacement asset outside candidate or missing')
        relative=str(path.relative_to(run))
        assets.append({'bundle_path':relative,'sha256':file_hash(path),'size_bytes':path.stat().st_size,
                       'role':'audio' if str(path) in audio_paths else 'timing_or_delivery_evidence'})
    require(assets and audio_paths,'Replacement requires generated audio')
    require(len({a['bundle_path'] for a in assets})==len(assets),'Duplicate replacement asset')
    identity={'slug':slug,'book_id':artifact['book'].get('id'),'language':'en',
              'source_sha256':artifact['source_sha256'],'plan_sha256':ctx['plan_hash'],
              'provider':'qwen3-tts','model':QWEN_ID,'model_revision':delivery.get('model_revision'),
              'speaker':ctx['editorial']['speaker'],'assets':sorted(assets,key=lambda a:a['bundle_path'])}
    return {'schema_version':'earnalism.audio_replacement_intent.v1',
            'intent':'REPLACE_ACTIVE_TITLE_AUDIO','authorization_basis':'User requested replacement of existing B2/cache audiobooks on 2026-09-11',
            'scope':identity,'candidate_revision_sha256':object_hash(identity),
            'candidate_review_passed':not candidate_issues,'candidate_blockers':list(candidate_issues),
            'state':'AWAITING_CONTROLLED_IMPORT','production_writes_performed':False,'release_ready':False,
            'existing_audio_observed':artifact.get('live_audio_enabled') is True,
            'live_reader_observation':artifact.get('live_reader_evidence',{}),
            'generation_policy':{'skip_because_existing_production_audio':False,
                                 'reuse_legacy_mp3_or_production_cache':False,
                                 'resume_current_verified_qwen_units':True},
            'storage':{'strategy':'STAGE_COMPLETE_VERSION_THEN_SWITCH_ACTIVE_REFERENCE',
                       'key_namespace':'VERSIONED_BY_CANDIDATE_REVISION_REQUIRES_IMPORTER_MAPPING',
                       'overwrite_live_object_bytes_in_place':False,
                       'delete_superseded_objects':False,'retain_previous_release_for_rollback':True},
            'activation':{'precondition':'READ_AND_COMPARE_CURRENT_ACTIVE_RELEASE_AT_IMPORT_TIME',
                          'switch':'ATOMIC_AUDIO_TIMING_AND_MANIFEST_REFERENCE_UPDATE',
                          'active_modes':['narration','atmosphere'] if delivery.get('atmosphere_included') else ['narration'],
                          'obsolete_modes':'REMOVE_OLD_MODE_REFERENCES_WHEN_ABSENT_FROM_NEW_RELEASE',
                          'existing_approvals_transfer':False,
                          'timing_mapping':'CHAPTER_ID_AND_CANONICAL_SOURCE_OFFSETS; NOT_WORD_ALIGNMENT',
                          'requires_validated_production_schema_adapter':True},
            'inspected_production_contract':{'repository_commit':'babc3d320f5ed6c00b73c90ade2bc4a98f166f08',
                'release_route':'/api/admin/books/{slug}/audiobook/release',
                'known_gaps':['different_active_conveyor_fingerprint_rejected_409',
                              'package_v2_builder_requires_google_manifest_adapter',
                              'package_v2_requires_segments_at_most_12_minutes_and_primary_dr_receipts',
                              'controlled_publication_truth_may_override_database_audio_state',
                              'release_handler_requires_explicit_cache_invalidation'],
                'reinspect_at_import':True},
            'import_transforms':{'if_packaging_changes_media_bytes':'RETAIN_SOURCE_TO_DERIVATIVE_HASH_MANIFEST_AND_REVALIDATE_TIMING_AND_PLAYBACK',
                                 'silent_audio_edits':False,'new_audio_content_or_mix_requires_new_listening_review':True},
            'cache':{'media_identity':'NEW_VERSIONED_URLS_AND_RELEASE_REVISION',
                     'required_refresh':['catalog','reader_manifest','audio_manifest','chapter_audio','server_or_cdn_stable_aliases_if_present'],
                     'client_policy':'REVALIDATE_AUDIO_REVISION; DISCARD_OLD_AUDIO_BLOBS_AND_TIMING_ON_CHANGE',
                     'offline_policy':'MARK_OLD_DOWNLOADS_STALE_ON_RECONNECT; LOCAL_OFFLINE_BYTES_CANNOT_BE_REMOTELY_ERASED',
                     'global_cache_flush':False},
            'completion_requires':['candidate_reviews_and_territory_checks_pass',
                                   'current_importer_accepts_full_master_and_chunk_timing_schema',
                                   'controlled_publication_truth_and_release_records_agree',
                                   'uploaded_assets_match_candidate_or_validated_derivative_manifest_hashes',
                                   'active_release_precondition_still_matches',
                                   'new_manifest_and_media_bytes_verified_after_cache_refresh',
                                   'range_requests_seeking_chapter_starts_and_mode_switch_verified',
                                   'rollback_reference_and_cache_refresh_receipts_recorded'],
            'production_receipt':None}


def export_bundle(ctx,delivery,asr,review,music=None,handoff_issues=None):
    """Always produce review evidence. A failed candidate is never called release-ready."""
    assert_audio_allowed(ctx, require_identity=True)
    run=ctx['run'];expected=human_review_template(ctx,{str(Path(p).relative_to(run)):file_hash(p) for p in delivery['audio_files']},'full_title')
    issues=validate_review(review,expected)
    if ctx.get('layout_blockers'):issues.append('UNRESOLVED_NARRATION_LAYOUT_OR_CAPTION_REVIEW')
    layout_info=ctx.get('narration_layout',{})
    if layout_info.get('status')=='EXACT_REFERENCE_WHITESPACE_PROJECTION':
        ledger_path=run/'narration_layout.json'
        if not ledger_path.is_file() or file_hash(ledger_path)!=layout_info.get('ledger_file_sha256') or object_hash(read_json(ledger_path))!=layout_info.get('ledger_sha256'):
            issues.append('NARRATION_LAYOUT_EVIDENCE_CHANGED_OR_MISSING')
    issues.extend(handoff_issues if handoff_issues is not None else ['CURRENT_ASR_AND_MUSIC_BINDINGS_NOT_CHECKED'])
    if review.get('encoded_seeks_and_chapter_starts_checked') is not True:issues.append('ENCODED_PLAYBACK_REVIEW_REQUIRED')
    if not asr or asr.get('all_segments_processed') is not True:issues.append('ASR_PROCESSING_INCOMPLETE')
    if asr and asr.get('source_sha256')!=ctx['artifact']['source_sha256']:issues.append('ASR_SOURCE_BINDING_MISMATCH')
    if asr and asr.get('flags'):
        resolutions=review.get('asr_flag_resolutions',{})
        for f in asr['flags']:
            r=resolutions.get(f['segment_id'],{})
            if r.get('asr_record_sha256')!=f.get('record_sha256') or r.get('resolution') not in ('ASR_ERROR_AUDIO_CORRECT','REPAIRED_AND_RECHECKED') or not r.get('note'):issues.append('UNRESOLVED_ASR_FLAG:'+f['segment_id'])
    rights=read_json(run/'audio_rights_review.json') if (run/'audio_rights_review.json').exists() else {}
    if not (rights.get('source_sha256')==ctx['artifact']['source_sha256'] and rights.get('plan_sha256')==ctx['plan_hash'] and rights.get('audio_sha256')==expected['audio_sha256'] and rights.get('model')==QWEN_ID and rights.get('model_revision')==delivery.get('model_revision') and rights.get('reviewer') and rights.get('reviewed_at') and rights.get('territories') and rights.get('basis_notes') and rights.get('source_text_audio_use_cleared') is True and rights.get('model_license_obligations_met') is True):issues.append('AUDIO_TERRITORY_RIGHTS_REVIEW_REQUIRED')
    if music:
        mr=read_json(run/'music_review.json') if (run/'music_review.json').exists() else {}
        audio_territories={str(x).upper() for x in rights.get('territories',[])}
        music_territories={str(x).upper() for x in mr.get('territories',[])}
        if not music_territories or not (music_territories & {'GLOBAL','WORLDWIDE'} or audio_territories<=music_territories):issues.append('MUSIC_TERRITORIES_DO_NOT_COVER_REQUESTED_AUDIO_DISTRIBUTION')
    issues=list(dict.fromkeys(issues))
    manifest={'schema_version':VERSION,'slug':ctx['artifact']['slug'],'provider':'qwen3-tts','model':QWEN_ID,'source_sha256':ctx['artifact']['source_sha256'],'source_plan_sha256':ctx['plan_hash'],'narration_layout':ctx.get('narration_layout',{}),'candidate_review_passed':not issues,'state':'READY_FOR_CONTROLLED_HANDOFF' if not issues else 'PRIVATE_CANDIDATE_REVIEW_REQUIRED','release_ready':False,'public_release_performed':False,'production_writes_performed':False,'new_importer_schema_requires_validation':True,'blockers':issues+['CONTROLLED_IMPORT_STORAGE_AND_RELEASE_CHECKS_REQUIRED'],'generated_at':now(),'delivery':delivery,'music':music,'asr_summary':asr}
    replacement=production_replacement_plan(ctx,delivery,issues)
    atomic_json(run/'production_replacement_plan.json',replacement)
    manifest['production_replacement']={'intent':replacement['intent'],
        'candidate_revision_sha256':replacement['candidate_revision_sha256'],
        'plan_file':'production_replacement_plan.json',
        'plan_sha256':file_hash(run/'production_replacement_plan.json'),'production_writes_performed':False}
    atomic_json(run/'qa_candidate_release_evidence.json',manifest)
    required=[run/'input_manifest.json',run/'generation_plan.json',run/'spoken_text_map.json',run/'editorial_plan.json',run/'segmentation_plan.json',run/'narration_layout.json',run/'narration_layout_diagnostics.json',run/'canonical_text.txt',run/'canonical_chapters.json',run/'full_listening_qa.json',run/'audio_rights_review.json',run/'qa_candidate_release_evidence.json',run/'full_generation_manifest.json']
    required.append(run/'production_replacement_plan.json')
    files=[p for p in required if p.is_file()]+[Path(p) for p in delivery['audio_files']+delivery.get('evidence_files',[])]
    for name in ('asr_report.json','music_review.json','cue_plan.json','runtime_lock.json','narration_generation_report.json','audition_review.json','endurance_review.json','qwen_attempts.jsonl','music_generation_report.json'):
        if (run/name).is_file():files.append(run/name)
    # Retain actual per-unit generation settings/hashes and ASR evidence, not only summaries.
    files.extend((run/'units').rglob('*.wav.json'))
    files.extend((run/'asr_segments').rglob('*.json'))
    files.extend((run/'provenance').rglob('*'))
    files=[p for p in files if p.is_file()]
    unique={str(p.resolve()):p for p in files}
    bundle=run/(ctx['artifact']['slug']+'_candidate_bundle.zip')
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
        check={}
        for p in unique.values():
            arc=str(p.resolve().relative_to(run.resolve()));z.write(p,arc);check[arc]=file_hash(p)
        z.writestr('bundle_checksums.json',json.dumps(check,indent=2))
    return manifest,str(bundle)
