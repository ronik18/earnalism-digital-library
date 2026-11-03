"""Exact Sredni initial SOURCE_QA profile, independent of original120.

No issuer, DB, grant/counter, lease, public promotion or financial operation.
Absent separately implemented and authorized dedicated budget => no selection.
"""
from datetime import datetime
import copy,hashlib,json,re
try:
    from .audiobook_packages import validate_audiobook_package
    from .rights_decision_gate import load_production_registry,load_audio_package_binding,evaluate_accepted_record,record_sha256
except ImportError:
    from audiobook_packages import validate_audiobook_package
    from rights_decision_gate import load_production_registry,load_audio_package_binding,evaluate_accepted_record,record_sha256

SLUG='sredni-vashtar'
FIELD='sredni_source_qa_private_stage'
SCHEMA='earnalism.sredni_source_qa_private_stage.v1'
DESCRIPTOR='dc53e6fdd5f74d71afbb56ea7b97c1484b781ffcceb12390b6546835e37336dc'
PACKAGE='sha256-8185d1b2e20ea325e0a5cfdcf5346f7511c1ccf49937a438f1305ba7566c383e'
MANIFEST='336ec7b7954375e8b8c35e350fac9565b835c62d22d63a430eb76d5f8e4c2a19'
SOURCE='fdcfd2a238a8667549492119a94715d0f64bacc46812252ea2b116deca1bf50a'
MANUSCRIPT='f363729ab6b36e07f8b99f33ffd9405b5596a5d74f01c350ad2ddfaa84c0fc06'
POLICY='sredni_scored_retained_owner_adjudicated.v1'
RIGHTS_RECORD='ae14c22b966bf55927f1183e6cf5281361e647804223abbe0dab921bb988f009'
TEST_ID='sredni-initial-scored-private-review-v1'
SCOPE_KEY='sredni_initial_review_grant_id'
PRIVATE_SCOPE='sredni_initial_review_authorized_member_only'
DISCLOSURE='AI voice: Verse. Music: Heartwarming/Heartbreaking, Kevin MacLeod (https://incompetech.com), CC BY 4.0 https://creativecommons.org/licenses/by/4.0/; edited.'
ASSETS={
 'audio':('60ce9893c5196e35ba8ee0ba7b491a53882f1e65ba3b1f31c01c052ed8cc7692',15316455,'audio/mpeg'),
 'metadata':('34f0f8a4dd14dd0952cb3f9436601be01e585ea964286162d01f894d71679ec3',1240,'application/json'),
 'timestamps':('303d398c02f0efb2ab94716918a73fda91c4935de6bbf499d0b6ae008a4748ee',18100,'application/json'),
 'vtt':('6caf727eb1152c4cfddf7e47cb64a8eb36ed57296940b7def7d7c6bc329b182f',10791,'text/vtt'),
}
RECEIPTS={
 'primary_receipt_sha256':'a04e0e49e58cdedfabf463a28bc1dee2412d4456efcf4773f83a8b923cf4edb4',
 'replica_receipt_sha256':'8e887975fc5f0eb743de355abaeeeb0aa4d47e959287bff2c17b7f4eda85cd67',
 'primary_release_manifest_receipt_sha256':'84a09fa7afc799357ea55be8f1eca7b13b1728946fc78a5f6437f40a9ea9e72b',
 'replica_release_manifest_receipt_sha256':'86554014e57e700f818ed1566de5ca70b825f926ba7584a2cbef2b756ab5f0ae',
}
DOWNSTREAM=['PRIVATE_B2_PRIMARY_UPLOAD_REQUIRED','PRIVATE_B2_DR_REPLICA_REQUIRED','CONTROLLED_RELEASE_ACTIVATION_REQUIRED','PRODUCTION_ENDPOINT_AND_BROWSER_PROOF_REQUIRED']
SHA=re.compile(r'^[a-f0-9]{64}$')
class ProfileError(ValueError):pass
def need(ok,message):
    if not ok:raise ProfileError(message)
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def candidate(book):
    """Source/receipt/ordinary-state validation, never an access grant."""
    try:
        marker=book.get(FIELD)
        if not isinstance(marker,dict):return None
        need(book.get('slug')==marker.get('slug')==SLUG and marker.get('schema_version')==SCHEMA
             and marker.get('status')=='SOURCE_QA_STAGED_PRIVATE','Exact initial Sredni marker required')
        need(book.get('audiobook_active_release')=={'status':'DISABLED_TEXT_READER_ONLY'}
             and book.get('audio_enabled') is False and book.get('audiobook_enabled') is False
             and not book.get('audiobook_public_package_approval') and not book.get('audiobook_package_canary'),
             'Sredni ordinary Reader-only/audio-hidden state required')
        need(marker.get('candidate_descriptor_sha256')==DESCRIPTOR and marker.get('candidate_package_version')==PACKAGE
             and marker.get('release_manifest_sha256')==MANIFEST
             and marker.get('private_playback_authorized') is False and marker.get('public_release_authorized') is False
             and marker.get('downstream_gates_unchanged')==DOWNSTREAM,'Source stage cannot authorize access or erase holds')
        need(isinstance(marker.get('snapshot_sha256'),str) and SHA.fullmatch(marker['snapshot_sha256']),
             'Exact retained Reader source snapshot required')
        package=validate_audiobook_package(book['audiobook_packages'][DESCRIPTOR],expected_slug=SLUG,
            expected_source_sha256=SOURCE,expected_manuscript_sha256=MANUSCRIPT,expected_release_descriptor_sha256=DESCRIPTOR)
        need(package['package_version']==PACKAGE and package['release_evidence_version']==POLICY
             and (package['duration_ms'],package['segment_count'],package['word_count'],package['paragraph_count'])==(638105,1,1784,17)
             and package['sync_tier']=='PARAGRAPH_OR_SECTION_SYNC_PREMIUM' and package['highlight_sync_enabled'] is False,
             'Exact source body, measured timing and stored Sredni package required')
        assets=package['tracks'][0]['chunks'][0]['assets'];need(set(assets)==set(ASSETS),'Exact four Sredni assets required')
        need(all((assets[r]['sha256'],assets[r]['size_bytes'],assets[r]['mime_type'])==fact for r,fact in ASSETS.items()),
             'Exact retained audio/timing/metadata bytes required')
        evidence=book['audiobook_package_release_evidence'][DESCRIPTOR]
        need(marker['package_release_evidence_sha256']==digest(evidence)
             and evidence.get('schema_version')=='audiobook_package_release_evidence.v1'
             and evidence.get('release_eligible') is True and evidence.get('receipt_roles')==['primary','replica']
             and evidence.get('slug')==SLUG and evidence.get('release_descriptor_sha256')==DESCRIPTOR
             and evidence.get('package_version')==PACKAGE,'Actual staged storage evidence required')
        need(all(evidence.get(k)==v for k,v in RECEIPTS.items())
             and evidence.get('release_manifest_sha256')==MANIFEST and evidence.get('release_manifest_size_bytes')==6544
             and evidence.get('release_manifest_key')==f'v1/prod/sprint1/{SLUG}/releases/{DESCRIPTOR}/release-manifest.json'
             and evidence.get('primary_release_manifest_store')=='prod' and evidence.get('replica_release_manifest_store')=='dr'
             and evidence.get('primary_release_manifest_version_id') and evidence.get('replica_release_manifest_version_id')
             and evidence['primary_release_manifest_version_id']!=evidence['replica_release_manifest_version_id'],
             'Exact real primary/DR manifest/receipt identity required')
        need(all(a['storage']['store']=='prod' and len(a['replicas'])==1 and a['replicas'][0]['store']=='dr'
                 for a in assets.values()),'Exact independent storage roles required')
        metadata={'audiobook_provider':'','audiobook_voice':'Verse','narration_disclosure':DISCLOSURE,
                  'duration_ms':638105,'size_bytes':ASSETS['audio'][1]}
        need(marker.get('narrator_metadata')==metadata,'Exact Verse/CC music disclosure required')
        return copy.deepcopy(package),copy.deepcopy(marker)
    except (KeyError,TypeError,AttributeError) as exc:raise ProfileError('Incomplete Sredni initial profile') from None


def rights_for_candidate(book,*,country,now):
    selected=candidate(book);need(selected is not None,'Sredni initial candidate unavailable')
    need(country=='IN' and isinstance(now,datetime) and now.tzinfo is not None,'Trusted India scope and clock required')
    package,marker=selected;record=marker['audio_use_decision'];accepted,revoked=load_production_registry()
    binding=load_audio_package_binding(SLUG,DESCRIPTOR)
    need(record_sha256(record)==RIGHTS_RECORD and binding and binding.get('record_sha256')==RIGHTS_RECORD
         and binding.get('decision_id')==record.get('decision_id'),'Exact independently accepted audio-use record required')
    components={'source_file':SOURCE,'selected_manuscript':MANUSCRIPT,'master_mp3':ASSETS['audio'][0],
                'audio_component_bindings':'d0db339a1d34ff842cee800dc6742a750413a230f0e0aae3e71db4085d9b2061'}
    verdict=evaluate_accepted_record(record,edition_id=SLUG,operator_id='reo-enterprise',country=country,country_trusted=True,
        use='audio_stream',required_components=components,accepted_records=accepted,revoked_decision_ids=revoked,now=now)
    need(verdict.passed and record['territories']==['IN'] and record['uses']==['audio_stream'],'Sredni audio-use rights denied')
    return package,marker


def selected_from_verified_budget(book,budget,*,country,now):
    """Future server-only seam; absent dedicated transactional verifier denies.

    The dedicated scope module is intentionally not supplied by this profile
    patch. It must be separately implemented/tested and admitted against the
    actual new owner receipt; no JSON scope or original120 budget is accepted.
    """
    try:
        from .sredni_initial_review_scope import SredniReviewBudget
    except ImportError:
        try:from sredni_initial_review_scope import SredniReviewBudget
        except ImportError:return None
    if not isinstance(budget,SredniReviewBudget):return None
    package,marker=rights_for_candidate(book,country=country,now=now)
    # Interface required of the future genuine service-transaction verifier;
    # a metadata query/marker alone must never manufacture this typed object.
    scope=budget.validated_selection_scope(now=now)
    need(scope.get('acceptance_test_id')==TEST_ID and scope.get(SCOPE_KEY)
         and scope.get('package_version')==PACKAGE and scope.get('manifest_version')==PACKAGE
         and scope.get('segmentation_version')==DESCRIPTOR and scope.get('release_descriptor_sha256')==DESCRIPTOR
         and scope.get('release_country')=='IN','Dedicated verified Sredni lease scope required')
    return package


def listener_metadata_from_verified_budget(book,budget,*,country,now):
    package=selected_from_verified_budget(book,budget,country=country,now=now)
    if package is None:return None
    return {'enabled':True,'slug':SLUG,'scope':PRIVATE_SCOPE,'package_version':PACKAGE,
            'release_descriptor_sha256':DESCRIPTOR,'duration_ms':638105,'narration_disclosure':DISCLOSURE}
