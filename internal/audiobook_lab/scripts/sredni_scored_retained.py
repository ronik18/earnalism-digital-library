"""Exact Sredni Verse scored SOURCE_QA; never upload, activate or publish."""
from pathlib import Path
from datetime import datetime, timezone
import json,hashlib,copy,math,re,subprocess
import owner_produced_package as common
import native_scored_package as media
from rights_decision_gate import evaluate_accepted_record,load_production_registry

POLICY='sredni_scored_retained_owner_adjudicated.v1'
ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/'internal/audiobook_lab/release_gate/sredni-scored-20261103'
REGISTRY=ROOT/'internal/audiobook_lab/release_gate/sredni_scored_adoptions.json'
INDEX_SHA='f9b12378eef95de4f5b41fed24f73f637cf62c59e483124f0cbe0ca7a32a9658'
DESCRIPTOR_SHA='dc53e6fdd5f74d71afbb56ea7b97c1484b781ffcceb12390b6546835e37336dc'
OWNER_SHA='f49328353c0bef72e6a45d20cdecbc940bb0d78c8ceac6d181f57ad9bb52adad'
FULL_SHA='3fdbdb790bcf21288cee948e49c699fbc411fe5c6fdc9d2bc35ee9c67ba69f4b'
REVIEW_SHA='7a1a2a6eb471c8002c6d20bbac29e998ea843a197131353947feea566692d7f4'
SYNC='PARAGRAPH_OR_SECTION_SYNC_PREMIUM'
EVIDENCE_ROLES = common.EVIDENCE_ROLES | {'scored_mix_acceptance', 'music_rights', 'measured_alignment', 'container_metadata_reuse'}
class Error(ValueError):pass
def require(ok,message):
    if not ok:raise Error(message)
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def load(p):return json.loads(Path(p).read_text())

def bound_file(base, fact):
    """Read only a regular contained file, with every path component nonsymlink."""
    base = Path(base).resolve()
    candidate = base / fact['path']
    require(not any(part.is_symlink() for part in (candidate, *candidate.parents)), 'Local symlink forbidden')
    resolved = candidate.resolve()
    require(resolved.is_relative_to(base) and resolved.is_file(), 'Local asset escape')
    raw = resolved.read_bytes()
    require(common.validsha(fact.get('sha256')) and sha(raw) == fact['sha256'], 'Local exact asset changed')
    return resolved, raw


def evidence():
    require(sha((DATA/'evidence-index.json').read_bytes())==INDEX_SHA,'Frozen source evidence index changed')
    index=load(DATA/'evidence-index.json');by_sha={}
    for name,fact in index['files'].items():
        p,b=bound_file(DATA, {'path':name, **fact})
        require(len(b)==fact['bytes'],'Frozen source evidence changed')
        by_sha[sha(b)]=b
    return by_sha

def verify_source_facts(by_sha):
    full=json.loads(by_sha[FULL_SHA]);owner=json.loads(by_sha[OWNER_SHA])
    require(owner['scored_parent_audio_sha256']==full['scored_audio_sha256']=='8c767405472944fcd1a2cf4a0f2b548f517b32340e459b5a670bd3a51366f790','Exact listened scored master required')
    scores=full['scores'];require(len(scores)==10 and all(type(v) in (int,float) and math.isfinite(v) and 8.9<=v<=10 for v in scores.values()),'Actual named full-book dimensions required')
    require(math.fsum(scores.values())/10>=9.8 and full['overall']>=9.8 and .9<=full['confidence']<=1,'Per-book actual mean/confidence threshold')
    require(full['full_10m38_listening_confirmed'] is True and full['music_audible_speech_clear_normal_and_low_volume_confirmed'] is True,'Full scored listening/music required')
    require(owner['all_nine_source_phrases_heard_without_additions'] is True and len(owner['fatal_flags'])==5 and all(v is False for v in owner['fatal_flags'].values()),'Actual scoped wording/fatal response required')
    require(REVIEW_SHA in by_sha,'Independent source/audio review required')
    source=(DATA/'manuscript.txt').read_text();require(sha(source.encode())=='f363729ab6b36e07f8b99f33ffd9405b5596a5d74f01c350ad2ddfaa84c0fc06' and len(source.split())==1784,'Exact source body/count required')
    current=load(ROOT/'data/controlled_publications/sredni-vashtar/chapters/chapter-001.json')
    require(current['content']==source,'Current source version changed')
    reader=common.reader_paragraph_map(source);require(len(reader['paragraphs'])==17 and reader['reader_content_sha256']=='a907b196084880f214eac8cc479dad5fbfc8102e05899aa3937b7622d7b6b349','Actual supported Reader mapping changed')
    # These exact reviewed records preserve raw evidence and scoped associations;
    # source coverage is not inferred from a structural source plan or a score.
    qualified=next(json.loads(b) for b in by_sha.values() if b.startswith(b'{') and 'PASS_ALL17_ACTUAL_SUPPORTED_READER_PARAGRAPHS' in b.decode(errors='ignore'))
    require(qualified['actual_reader_paragraphs']==17 and qualified['raw_source_blocks']==158 and qualified['measured_boundary_times_not_estimated'] is True,'Complete actual measured Reader boundaries required')
    asr=next(json.loads(b) for b in by_sha.values() if b.startswith(b'{') and 'PASS_TWO_FULL_ORIGINAL_RECOGNIZER_STREAMS_WITH_ONLY_ACTUAL_REPLACEMENT_REGION_UPDATED' in b.decode(errors='ignore'))
    require(len(asr['results'])==2 and asr['minimum_score']>=9.7 and all(x['first12_match'] and x['last12_match'] for x in asr['results']),'Reused unchanged-audio full ASR threshold/edges required')
    return source,reader

def validate_source_units(source, units, reader, package):
    require(len(units)==len(reader['paragraphs'])==17, 'Exact source unit count')
    word=0
    for i,(unit,paragraph) in enumerate(zip(units,reader['paragraphs'])):
        a,z=paragraph['source_start'],paragraph['source_end']
        text=source[a:z]
        require(unit['id']==f'paragraph-{i+1:05}'
                and (unit['source_start'],unit['source_end'])==(a,z)
                and unit['raw_source_span_sha256']==sha(text.encode())
                and unit['actual_whitespace_word_count']==len(text.split()), 'Exact actual source unit span')
        word+=len(text.split())
    chunks=[c for t in package['tracks'] for c in t['chunks']]
    require(word==1784 and len(chunks)==1
            and chunks[0]['source_unit_ids']==[u['id'] for u in units], 'Exact complete source grouping')


def validate_publication_tags(tags):
    require(isinstance(tags,dict), 'Publication tags missing')
    tags={str(k).lower():str(v) for k,v in tags.items()}
    comment=tags.get('comment','');combined='\n'.join(tags.values()).lower()
    require(tags.get('title')=='Sredni Vashtar'
            and 'openai verse' in tags.get('artist','').lower(), 'Sredni title/Verse tags')
    require(not re.search(r'\b(?:draft|private|pending|review)\b',combined)
            and all(x not in combined for x in ('proposed changes','planned credits','not evidence of rendering')), 'Stale publication tags')
    require(not re.search(r'(?:file://|/(?:users|home|tmp|private|var/folders|volumes)/|[a-z]:[\\/](?:users|temp)[\\/])',combined)
            and all(x not in combined for x in ('x-amz-signature=','x-amz-credential=','authorization:','bearer ')), 'Private publication metadata')
    require('ai narration' in comment.lower() and 'openai verse' in comment.lower()
            and 'gpt-4o-mini-tts' in comment and 'Heartwarming' in comment
            and 'Heartbreaking' in comment and 'Kevin MacLeod' in comment
            and 'https://creativecommons.org/licenses/by/4.0/' in comment
            and 'USUAN1100208' in comment and 'USUAN1100207' in comment
            and 'Changes:' in comment, 'Actual AI disclosure/music attribution')

def publication_tags(path):
    result=subprocess.run(['ffprobe','-v','error','-protocol_whitelist','file,pipe',
        '-f','mp3','-show_entries','format_tags','-of','json',str(path)],
        capture_output=True,text=True,timeout=20,check=True)
    tags=json.loads(result.stdout).get('format',{}).get('tags',{})
    validate_publication_tags(tags)
    return tags


def load_adoption():
    r=load(REGISTRY);require(r.get('schema')=='earnalism.sredni-scored-adoptions.v1','Sredni adoption registry unavailable')
    entries=[x for x in r['adoptions'] if x['record'].get('descriptor_sha256')==DESCRIPTOR_SHA]
    require(len(entries)==1,'One exact Sredni adoption required');e=entries[0];a=e['record']
    require(e.get('record_sha256')==sha(canonical(a)) and a.get('status')=='ADOPTED','Actual reviewed adoption required;proposal is not acceptance')
    require(a.get('scope')=='SOURCE_QA_ONLY_STORAGE_AND_RUNTIME_PENDING' and a.get('policy')==POLICY,'Source-only adoption scope')
    require(a.get('adopted_by') and a.get('authority_reference') and common.validsha(a.get('authority_evidence_sha256')),'Actual adoption attribution required')
    require(a.get('independent_source_review_sha256')==REVIEW_SHA,'Independent changed-scope review binding')
    return a

def validate(descriptor,package,controlled_language,downstream_gates):
    try:
        require(sha(canonical(descriptor))==DESCRIPTOR_SHA,'Exact reviewed Sredni descriptor required')
        require(str(controlled_language).lower() in ('en','eng','english'),'English source required')
        require(descriptor['release_candidate_evidence']['acceptance_policy']==POLICY and descriptor['known_release_blockers']==downstream_gates==common.DOWNSTREAM,'All storage/runtime gates preserved')
        require(descriptor['release_candidate_evidence']['all_release_gates_passed'] is False and descriptor['highlight_sync_enabled'] is False,'No release/highlight inflation')
        common.validate_topology(package,expected_sync_tier=SYNC)
        require((package['slug'],package['source_sha256'],package['manuscript_sha256'],package['release_descriptor_sha256'],package['duration_ms'],package['segment_count'],package['word_count'],package['paragraph_count'])==('sredni-vashtar',descriptor['controlled_source_sha256'],descriptor['manuscript_sha256'],DESCRIPTOR_SHA,638105,1,1784,17),'Exact actual body/package counts required')
        by_sha=evidence();source,reader=verify_source_facts(by_sha)
        require(sha(canonical(reader))==descriptor['reader_paragraph_map_sha256'], 'Exact actual Reader map')
        units=load(DATA/'source-units.json')
        require(sha(canonical(units))==descriptor['source_units_sha256'], 'Exact frozen source units')
        validate_source_units(source,units,reader,package)
        a=load_adoption()
        require(a['generation']==descriptor['generation'] and a['evidence_sha256']==descriptor['evidence_sha256'],'Exact retained Verse generation/evidence')
        require(a['identity']=={k:descriptor[k] for k in a['identity']} and a['chunk_mapping_sha256']==common.mapping(package),'Exact source/master/chunk mapping')
        require(a['unresolved_material_audio_defects']==[] and a['source_coverage']==1.0,'Material/source hold remains')
        rights=a['audio_use_decision'];proposed=load(DATA/'AUDIO-USE-DECISION.PROPOSED.json');accepted,revoked=load_production_registry()
        require(rights['components']==proposed['components'] and rights['territories']==['IN'] and rights['uses']==['audio_stream'],'Exact India streaming components only')
        verdict=evaluate_accepted_record(rights,edition_id='sredni-vashtar',operator_id='reo-enterprise',country='IN',country_trusted=True,use='audio_stream',required_components=proposed['components'],accepted_records=accepted,revoked_decision_ids=revoked,now=datetime.now(timezone.utc))
        require(verdict.passed,'Actual accepted rights registry required:'+','.join(verdict.reasons))
        return copy.deepcopy(descriptor)
    except (OSError,KeyError,TypeError,StopIteration) as exc:raise Error('Incomplete Sredni source/adoption evidence') from None

def prepare(bundle_path,output_dir):
    """Actual source-only file preparation. No storage or runtime operations."""
    p=Path(bundle_path).resolve();base=p.parent;b=load(p)
    require(b.get('schema')=='earnalism.sredni-scored-local-package.v1','Sredni bundle schema')
    d=b['release_descriptor'];package=b['package_identity'];validate(d,package,'en',common.DOWNSTREAM)
    def file(fact):
        return bound_file(base, fact)
    require(set(b['evidence_files']) == EVIDENCE_ROLES == set(d['evidence_sha256']), 'Exact evidence role set required')
    for role,fact in b['evidence_files'].items():
        _,raw=file(fact);require(sha(raw)==d['evidence_sha256'][role],'Exact evidence file changed')
    _,wav=file(b['master_wav'])
    require(sha(wav)==d['master_wav_sha256'], 'Exact descriptor lossless master required')
    facts=media.wav_identity(wav)
    require(facts['frames']==d['master_samples']==30629040, 'Actual lossless sample count')
    del wav
    published_path,published=file(b['master_mp3'])
    require(sha(published)==d['master_mp3_sha256'], 'Exact descriptor publication MP3 required')
    listened_path,listened=file(b['listened_master_mp3'])
    require(sha(listened)==d['listened_master_mp3_sha256'], 'Exact descriptor listened MP3 required')
    _,manuscript=file(b['manuscript'])
    require(sha(manuscript)==d['manuscript_sha256'] and len(manuscript.decode().split())==1784, 'Exact descriptor manuscript required')
    units=b['source_units']
    require(sha(canonical(units))==d['source_units_sha256'], 'Exact source units required')
    reader=common.reader_paragraph_map(manuscript.decode())
    require(sha(canonical(reader))==d['reader_paragraph_map_sha256'], 'Exact actual Reader mapping required')
    validate_source_units(manuscript.decode(),units,reader,package)
    proof=json.loads(file(b['evidence_files']['container_metadata_reuse'])[1])
    media.validate_container_reuse(proof,listened=sha(listened),published=sha(published),frames=facts['frames'])
    publication_tags(published_path)
    prior_pcm=media.decoded_pcm_identity(listened_path)
    delivery_pcm=media.decoded_pcm_identity(published_path)
    require(prior_pcm==delivery_pcm
            and prior_pcm['sha256']==proof['items']['listened']['canonical_decoded_PCM']['sha256']
            and prior_pcm['packet_sha256']==proof['items']['listened']['elementary_encoded_audio_packets']['sha256']
            and prior_pcm['packet_bytes']==proof['items']['listened']['elementary_encoded_audio_packets']['bytes']
            and prior_pcm['frames']==facts['frames'], 'Actual metadata-successor PCM differs')
    assets=[];tracks=[];prefix=f'v1/prod/sprint1/sredni-vashtar/releases/{DESCRIPTOR_SHA}/'
    expected_ids={chunk['segment_id']+'-'+role for track in package['tracks'] for chunk in track['chunks'] for role in chunk['assets']}
    require(set(b['asset_files'])==expected_ids, 'Exact delivery asset set required')
    for track in package['tracks']:
        chunks=[]
        for chunk in track['chunks']:
            ids={}
            for role,fact in chunk['assets'].items():
                aid=chunk['segment_id']+'-'+role;f,raw=file(b['asset_files'][aid]);require(len(raw)==fact['size_bytes'] and sha(raw)==fact['sha256'] and fact['mime_type']==common.ROLES[role],'Exact delivery asset facts')
                if role=='audio':require(sha(raw)==d['master_mp3_sha256'],'Exact served audio required')
                assets.append({'asset_id':aid,'local_path':str(f),'key':prefix+'delivery/'+aid+'-sha256-'+sha(raw)+f.suffix,**fact})
                ids[role]=aid
            chunks.append({**{k:v for k,v in chunk.items() if k!='assets'},'asset_ids':ids})
        tracks.append({**{k:v for k,v in track.items() if k!='chunks'},'chunks':chunks})
    semantics={k:package[k] for k in ('slug','release_descriptor_sha256','source_sha256','manuscript_sha256','duration_ms','segment_count','word_count','paragraph_count','sync_tier','highlight_sync_enabled')}
    semantics.update(schema_version='audiobook_package_semantics.v2',package_schema_version='audiobook_package_manifest.v2',release_evidence_version=POLICY,tracks=tracks)
    out=Path(output_dir);require(not out.exists(),'Preserve previous output');out.mkdir(parents=True)
    for name,value in [('release-descriptor.json',d),('package-semantics.json',semantics),('upload-plan.json',{'schema_version':'audiobook_package_upload_plan.v2','slug':'sredni-vashtar','release_descriptor_sha256':DESCRIPTOR_SHA,'immutable_prefix':prefix,'release_status':'RELEASE_CANDIDATE','assets':assets})]:
        with (out/name).open('x') as f:json.dump(value,f,indent=2)
    return {'status':'LOCAL_SREDNI_SOURCE_QA_PREPARED_STORAGE_PENDING','uploads':False,'public_release_approved':False,'output_dir':str(out)}
