"""Exact Selfish Giant private replacement selection; no grant provisioning or finance writes."""
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
SLUG='the-selfish-giant'
PREDECESSOR='b5b378168211d61ac80341e74cbfacaf0d5590a18300a5c91db4684626e343a2'
DESCRIPTOR='d2dbc302427a535e5a3e89dfb82f0b9b880729ea6c56837fd9d9f18ea1077258'
SOURCE='77ae1b3c7be77aea82b1f935e531e53f4df43db572cbc14af39d6cd0d5ba50da'
MANUSCRIPT='c55bef9dcd5883e156af940deb849c67a78a8fae7fc7a1e50ea814aa9ce866c5'
AUDIO='543117b5c47f0459d0d194156949904d84ecf37107bf7076e679f038c08da817'
TEST_ID='selfish-native-replacement-original-120-v1'
PRIVATE_SCOPE='native_replacement_authorized_member_only'
SHA=re.compile(r'^[a-f0-9]{64}$')
POST_GATES=['PRIVATE_AUTHENTICATED_EXACT_PACKAGE_PLAYBACK','RANGE_TIMESTAMPS_AND_CHAPTER_NAVIGATION','SOURCE_AND_BILLING_IDENTITY','PUBLIC_PROOF_BOUND_PROMOTION_AND_GUARDED_RESTORE']

class ReplacementError(ValueError):pass

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
        need(package['package_version']==marker.get('candidate_package_version') and package['duration_ms']==541807
             and package['segment_count']==1 and package['word_count']==1652 and package['paragraph_count']==23
             and package.get('release_evidence_version')=='owner_produced_native_scored.v1'
             and package['tracks'][0]['chunks'][0]['assets']['audio']['sha256']==AUDIO,'Native package identity')
        evidence=book['audiobook_package_release_evidence'][DESCRIPTOR]
        need(marker.get('package_release_evidence_sha256')==digest(evidence),'Private storage evidence changed')
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

def private_scope(book,user_id,budget,*,country,now,session_scope=None):
    """No builder/reset: only an already authorized, privately installed carried account grant."""
    if not isinstance(budget,dict) or 'native_replacement_authorization' not in budget:return None
    package,marker=rights_for_candidate(book,country=country,now=now)
    return validate_carried_grant(budget,user_id,now=now,package_version=package['package_version'],session_scope=session_scope)

def validate_carried_grant(budget,user_id,*,now,package_version,session_scope=None,current_access=True):
    """Also run inside the existing wallet transaction before CAS/debit."""
    need(isinstance(package_version,str) and re.fullmatch(r'sha256-[a-f0-9]{64}',package_version), 'Finalized grant package version required')
    grant=budget['native_replacement_authorization']
    need(isinstance(grant,dict) and grant.get('schema')=='earnalism.native_replacement_member_grant.v1'
         and grant.get('authorization_id') and grant.get('original_ceiling_seconds')==120
         and grant.get('lineage_status') in ['RECONCILED_EXACT_USED','CONSERVATIVE_RESERVATION']
         and isinstance(grant.get('usage_lineage_sha256'),str) and SHA.fullmatch(grant['usage_lineage_sha256'])
         and isinstance(grant.get('owner_scope_sha256'),str) and SHA.fullmatch(grant['owner_scope_sha256']),'Unreconciled native carried authority')
    prior=grant.get('inherited_reserved_seconds')
    need(type(prior) is int and 51<=prior<=120,'Native prior reservation below documented whole-debit floor')
    need(budget.get('schema')=='reader-acceptance-budget.v1' and budget.get('user_id')==user_id and bool(user_id)
         and budget.get('content_type')=='audio' and budget.get('content_id')==SLUG
         and budget.get('test_id')==TEST_ID and budget.get('status')=='enabled'
         and type(budget.get('maximum_seconds')) is int and 0<budget['maximum_seconds']<=120
         and type(budget.get('consumed_seconds')) is int and prior<=budget['consumed_seconds']<=budget['maximum_seconds']
         and budget.get('manifest_version')==package_version and budget.get('segmentation_version')==DESCRIPTOR,'Native member/package/cumulative cap denied')
    created=budget.get('created_at');expires=budget.get('expires_at');grant_expires=grant.get('expires_at')
    need(all(isinstance(v,datetime) for v in (created,expires,grant_expires))
         and isinstance(now,datetime) and now.tzinfo is not None,'Native grant clock invalid')
    # PyMongo's existing default decoder yields naive BSON UTC datetimes.
    # Normalize local copies only; retain the original document for account CAS.
    utc=lambda v:v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)
    created,expires,grant_expires=(utc(v) for v in (created,expires,grant_expires))
    need(created<=now and timedelta(0)<expires-created<=timedelta(minutes=15)
         and grant_expires==expires,'Native grant expired/unbounded')
    if current_access:need(now<expires and budget['consumed_seconds']<budget['maximum_seconds'],'Native grant exhausted/expired')
    scope={'native_replacement_authorization_id':grant['authorization_id'],'acceptance_test_id':TEST_ID,
        'manifest_version':package_version,'segmentation_version':DESCRIPTOR,
        'package_version':package_version,'release_descriptor_sha256':DESCRIPTOR,'release_country':'IN'}
    if session_scope is not None:
        need(isinstance(session_scope,dict) and all(session_scope.get(k)==v for k,v in scope.items()),'Native lease/package scope changed')
    return scope

def selected_from_verified_scope(book,scope):
    """Only called with server-owned state after normal lease authorization and grant recheck."""
    selected=candidate(book)
    if not selected:return None
    package,marker=selected
    need(isinstance(scope,dict) and scope.get('acceptance_test_id')==TEST_ID
         and scope.get('release_descriptor_sha256')==DESCRIPTOR and scope.get('package_version')==package['package_version']
         and scope.get('manifest_version')==package['package_version'] and scope.get('segmentation_version')==DESCRIPTOR
         and scope.get('native_replacement_authorization_id') and scope.get('release_country')=='IN','Native verified lease scope unavailable')
    return package
