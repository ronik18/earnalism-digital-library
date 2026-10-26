import copy
import hashlib
import json
from pathlib import Path
import pytest
from backend.protected_package_publication import protected_package_publication_valid

@pytest.fixture
def approved():
    # Real accepted package/receipts, synthetic publication acceptance. Never applied.
    book=json.loads((Path(__file__).resolve().parents[1]/'data/controlled_publications/the-open-window/public_book.json').read_text())
    state=book['audiobook_active_release'];descriptor=state['candidate_release_descriptor_sha256']
    state['active_release_descriptor_sha256']=descriptor;state['candidate_release_descriptor_sha256']='';state['rollout']={'percentage':0,'salt':''}
    p=book['audiobook_packages'][descriptor]
    acceptance={'schema_version':'audiobook_public_package_acceptance.v1','release_descriptor_sha256':descriptor,
        'package_version':p['package_version'],'duration_ms':p['duration_ms'],'segment_count':p['segment_count'],
        'production_proof_sha256':{k:'a'*64 for k in ['playback','business','accounting']},'accounting_commit':'b'*40,'public_activation_performed':False}
    book['audiobook_release_mode']='PROTECTED_PACKAGE_V2'
    book['audiobook_public_package_approval']={'schema_version':'audiobook_protected_package_publication.v1','status':'PUBLIC_APPROVED',
        'slug':book['slug'],'release_descriptor_sha256':descriptor,'endpoint':f"/api/reader/book/{book['slug']}/audiobook/manifest",
        'acceptance':acceptance,'acceptance_sha256':hashlib.sha256(json.dumps(acceptance,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()}
    return book

def test_valid_binding_without_legacy_mp3(approved):
    assert not approved.get('audiobook_assets',{}).get('mp3')
    assert protected_package_publication_valid(approved)

@pytest.mark.parametrize('mutation',['no-approval','bad-hash','wrong-endpoint','candidate','bad-receipt','same-store','wrong-source'])
def test_incomplete_or_mismatched_binding_denied(approved,mutation):
    b=copy.deepcopy(approved);d=b['audiobook_active_release']['active_release_descriptor_sha256']
    if mutation=='no-approval':b.pop('audiobook_public_package_approval')
    if mutation=='bad-hash':b['audiobook_public_package_approval']['acceptance_sha256']='0'*64
    if mutation=='wrong-endpoint':b['audiobook_public_package_approval']['endpoint']='https://example.invalid/master.mp3'
    if mutation=='candidate':b['audiobook_active_release']['candidate_release_descriptor_sha256']=d
    if mutation=='bad-receipt':b['audiobook_package_release_evidence'][d]['primary_receipt_sha256']=''
    if mutation=='same-store':b['audiobook_package_release_evidence'][d]['replica_release_manifest_store']='prod'
    if mutation=='wrong-source':b['source_hash']='0'*64
    assert not protected_package_publication_valid(b)
