"""Exact Open Window retained-scored private replacement selection; no grant provisioning or finance writes."""
from __future__ import annotations
import copy,hashlib,json,re
from datetime import datetime,timezone,timedelta
try:
    from .audiobook_packages import validate_audiobook_package,validate_active_release_state
    from .protected_package_publication import protected_package_publication_valid
    from .rights_decision_gate import load_production_registry,load_audio_package_binding,evaluate_accepted_record,record_sha256
except ImportError:
    from audiobook_packages import validate_audiobook_package,validate_active_release_state
    from protected_package_publication import protected_package_publication_valid
    from rights_decision_gate import load_production_registry,load_audio_package_binding,evaluate_accepted_record,record_sha256

FIELD='audiobook_native_replacement'
SCHEMA='audiobook_native_replacement.v1'
SLUG='the-open-window'
PREDECESSOR='028f65d8551523eecaad03bb5b476070f0c48c1fb0771bf9abc9163ecd5ba4b2'
DESCRIPTOR='e41267aae8dca016c76c38f1e7123493eee0f94fe70651ced2211428494a6219'
SOURCE='058d0cda5a3c8449cbce06e0698048251881be4c6fc8d06fd0bc3a1bb8ec8587'
MANUSCRIPT='f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be'
AUDIO='32827f8c28b9815b0fccf50ec8486e23e563dfb952c00920610e6c8e8c5730a9'
TEST_ID='open-window-native-replacement-original-120-v1'
PRIVATE_SCOPE='native_replacement_authorized_member_only'
SHA=re.compile(r'^[a-f0-9]{64}$')
POST_GATES=['PRIVATE_AUTHENTICATED_EXACT_PACKAGE_PLAYBACK','RANGE_TIMESTAMPS_AND_CHAPTER_NAVIGATION','SOURCE_AND_BILLING_IDENTITY','PUBLIC_PROOF_BOUND_PROMOTION_AND_GUARDED_RESTORE']

try:
    from .native_audiobook_replacement import ReplacementError
except ImportError:
    from native_audiobook_replacement import ReplacementError

def need(value,message):
    if not value:raise ReplacementError(message)

def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def mapping(package):
    tracks=[]
    for track in package['tracks']:
        chunks=[]
        for chunk in track['chunks']:
            assets={role:{k:a[k] for k in ('sha256','size_bytes','mime_type')} for role,a in chunk['assets'].items()}
            chunks.append({**{k:v for k,v in chunk.items() if k!='assets'},'assets':assets})
        tracks.append({**{k:v for k,v in track.items() if k!='chunks'},'chunks':chunks})
    return digest(tracks)

def candidate(book):
    """Validate canonical private package while ordinary public predecessor stays unchanged."""
    try:
        marker=book.get(FIELD)
        if not isinstance(marker,dict) or marker.get('status')!='STAGED_PRIVATE':return None
        need(marker.get('schema_version')==SCHEMA and book.get('slug')==marker.get('slug')==SLUG,'Native replacement schema/title')
        state=validate_active_release_state(book['audiobook_active_release'])
        need(state['status']=='ACTIVE' and state['active_release_descriptor_sha256']==PREDECESSOR
             and not state['candidate_release_descriptor_sha256'] and state['rollout']['percentage']==0,'Ordinary active predecessor changed')
        need(protected_package_publication_valid(book),'Ordinary predecessor approval changed')
        need(marker.get('predecessor_descriptor_sha256')==PREDECESSOR
             and marker.get('predecessor_public_approval_sha256')==digest(book['audiobook_public_package_approval'])
             and isinstance(marker.get('snapshot_sha256'),str) and SHA.fullmatch(marker['snapshot_sha256']),'Prior-public snapshot binding')
        need(marker.get('candidate_descriptor_sha256')==DESCRIPTOR and marker.get('private_scope')==PRIVATE_SCOPE
             and marker.get('post_deploy_proof_required')==POST_GATES,'Exact private native scope')
        package=validate_audiobook_package(book['audiobook_packages'][DESCRIPTOR],expected_slug=SLUG,
            expected_source_sha256=SOURCE,expected_manuscript_sha256=MANUSCRIPT,expected_release_descriptor_sha256=DESCRIPTOR)
        need(package['package_version']==marker.get('candidate_package_version')==finalized_package_binding() and package['duration_ms']==491436
             and package['segment_count']==1 and package['word_count']==1208 and package['paragraph_count']==21
             and package.get('release_evidence_version')=='open_window_scored_retained_successor.v1'
             and package['tracks'][0]['chunks'][0]['assets']['audio']['sha256']==AUDIO,'Native package identity')
        evidence=book['audiobook_package_release_evidence'][DESCRIPTOR]
        need(marker.get('package_release_evidence_sha256')==digest(evidence)
             and evidence.get('release_manifest_sha256')==FINAL_RELEASE_MANIFEST_SHA256,'Private storage evidence changed')
        need(evidence.get('schema_version')=='audiobook_package_release_evidence.v1'
             and evidence.get('slug')==SLUG and evidence.get('release_descriptor_sha256')==DESCRIPTOR
             and evidence.get('package_version')==package['package_version'] and evidence.get('release_eligible') is True
             and evidence.get('receipt_roles')==['primary','replica'],'Private release receipts')
        need(evidence.get('release_manifest_key')==f'v1/prod/sprint1/{SLUG}/releases/{DESCRIPTOR}/release-manifest.json'
             and evidence.get('primary_release_manifest_store')=='prod' and evidence.get('replica_release_manifest_store')=='dr'
             and evidence.get('primary_release_manifest_version_id') and evidence.get('replica_release_manifest_version_id')
             and evidence['primary_release_manifest_version_id']!=evidence['replica_release_manifest_version_id'],'Private manifest stores/versions')
        need(all(isinstance(evidence.get(k),str) and SHA.fullmatch(evidence[k]) for k in
             ['primary_receipt_sha256','replica_receipt_sha256','primary_release_manifest_receipt_sha256','replica_release_manifest_receipt_sha256','release_manifest_sha256']),'Private receipt hashes')
        need(all(asset['storage']['store']=='prod' and asset['replicas'] and all(r['store']=='dr' for r in asset['replicas'])
             for t in package['tracks'] for c in t['chunks'] for asset in c['assets'].values()),'Native storage roles changed')
        need(type(evidence.get('release_manifest_size_bytes')) is int and evidence['release_manifest_size_bytes']>0,'Native manifest size missing')
        return package,marker
    except (KeyError,TypeError,AttributeError) as exc:raise ReplacementError('Incomplete native replacement binding') from None

def rights_for_candidate(book, *, country, now):
    selected=candidate(book);need(selected is not None,'Native private candidate unavailable')
    package,marker=selected
    need(country=='IN' and isinstance(now,datetime) and now.tzinfo is not None,'Native country/clock untrusted')
    record=marker['audio_use_decision'];accepted,revoked=load_production_registry()
    binding=load_audio_package_binding(SLUG,DESCRIPTOR)
    need(binding and binding['decision_id']==record['decision_id'] and binding['record_sha256']==record_sha256(record),'Independent native audio-use binding')
    components={'source_file':SOURCE,'selected_manuscript':MANUSCRIPT,'master_mp3':AUDIO,'audio_component_bindings':mapping(package)}
    verdict=evaluate_accepted_record(record,edition_id=SLUG,operator_id='reo-enterprise',country=country,country_trusted=True,
        use='audio_stream',required_components=components,accepted_records=accepted,revoked_decision_ids=revoked,now=now)
    need(verdict.passed,'Native candidate rights denied')
    return package,marker

# Filled only from real immutable storage/finalization; never a fixture value.
ACTUAL_PACKAGE='sha256-c2b0f27571aa437b61a1367c9e5157fd6f43ec2b307db09ba902083f481c9bca'
FINAL_RELEASE_MANIFEST_SHA256='66753bcd655f893a6cfce67a359e9dc6ef879ff07cefc810a575f08ecc9ca089'
GRANT_PREFIX='open-window-'

def finalized_package_binding():
    need(isinstance(ACTUAL_PACKAGE,str) and re.fullmatch(r'sha256-[a-f0-9]{64}',ACTUAL_PACKAGE)
         and isinstance(FINAL_RELEASE_MANIFEST_SHA256,str) and SHA.fullmatch(FINAL_RELEASE_MANIFEST_SHA256),
         'Real finalized Open Window package/manifest is UNBOUND; runtime denied')
    return ACTUAL_PACKAGE

def public_review_package(book):
    """Recognize exact independently approved public e412; never loosen candidate()."""
    marker=book.get(FIELD)
    if not isinstance(marker,dict) or marker.get('status')!='PROMOTED_PUBLIC':return None
    need(book.get('slug')==SLUG and marker.get('schema_version')==SCHEMA
         and marker.get('candidate_package_version')==finalized_package_binding()
         and marker.get('candidate_descriptor_sha256')==DESCRIPTOR
         and marker.get('candidate_package_version')==ACTUAL_PACKAGE,'Exact promoted native marker required')
    need(protected_package_publication_valid(book),'Public native approval unavailable')
    state=validate_active_release_state(book['audiobook_active_release'])
    need(state['active_release_descriptor_sha256']==DESCRIPTOR,'Ordinary public native selection changed')
    package=validate_audiobook_package(book['audiobook_packages'][DESCRIPTOR],expected_slug=SLUG,
        expected_source_sha256=SOURCE,expected_manuscript_sha256=MANUSCRIPT,expected_release_descriptor_sha256=DESCRIPTOR)
    need(package['package_version']==ACTUAL_PACKAGE and package['duration_ms']==491436
         and package['segment_count']==1 and package['word_count']==1208 and package['paragraph_count']==21
         and package['tracks'][0]['chunks'][0]['assets']['audio']['sha256']==AUDIO,'Exact public native media required')
    need(marker.get('promotion_acceptance_sha256')==book['audiobook_public_package_approval']['acceptance_sha256']
         and marker.get('package_release_evidence_sha256')==digest(book['audiobook_package_release_evidence'][DESCRIPTOR]),'Public native acceptance/storage binding changed')
    return package,marker

def rights_for_review_phase(book,*,country,now):
    """Private selection remains strict; public carry needs real public approval."""
    if (book.get(FIELD) or {}).get('status')=='STAGED_PRIVATE':
        return rights_for_candidate(book,country=country,now=now)
    selected=public_review_package(book);need(selected is not None,'Native review phase unavailable')
    package,marker=selected
    need(country=='IN' and isinstance(now,datetime) and now.tzinfo is not None,'Native review country/clock untrusted')
    record=marker['audio_use_decision'];accepted,revoked=load_production_registry();binding=load_audio_package_binding(SLUG,DESCRIPTOR)
    need(binding and binding['decision_id']==record['decision_id'] and binding['record_sha256']==record_sha256(record),'Public native rights binding changed')
    verdict=evaluate_accepted_record(record,edition_id=SLUG,operator_id='reo-enterprise',country=country,country_trusted=True,
        use='audio_stream',required_components={'source_file':SOURCE,'selected_manuscript':MANUSCRIPT,'master_mp3':AUDIO,'audio_component_bindings':mapping(package)},
        accepted_records=accepted,revoked_decision_ids=revoked,now=now)
    need(verdict.passed,'Public native rights denied')
    return package,marker

def selected_from_verified_scope(book,scope):
    """Only called with server-owned state after normal lease authorization and grant recheck."""
    selected=candidate(book) if (book.get(FIELD) or {}).get('status')=='STAGED_PRIVATE' else public_review_package(book)
    if not selected:return None
    package,marker=selected
    need(isinstance(scope,dict) and scope.get('acceptance_test_id')==TEST_ID
         and scope.get('release_descriptor_sha256')==DESCRIPTOR and scope.get('package_version')==package['package_version']
         and scope.get('manifest_version')==package['package_version'] and scope.get('segmentation_version')==DESCRIPTOR
         and scope.get('native_replacement_authorization_id') and scope.get('release_country')=='IN','Native verified lease scope unavailable')
    return package
