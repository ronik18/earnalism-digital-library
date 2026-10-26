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
    state=book['audiobook_active_release'];descriptor=state['candidate_release_descriptor_sha256'] or state['active_release_descriptor_sha256']
    state['active_release_descriptor_sha256']=descriptor;state['candidate_release_descriptor_sha256']='';state['rollout']={'percentage':0,'salt':''}
    p=book['audiobook_packages'][descriptor]
    acceptance={'schema_version':'audiobook_public_package_acceptance.v1','release_descriptor_sha256':descriptor,
        'package_version':p['package_version'],'duration_ms':p['duration_ms'],'segment_count':p['segment_count'],
        'production_proof_sha256':{k:'a'*64 for k in ['playback','business','accounting']},'accounting_commit':'b'*40,'public_activation_performed':False}
    book['audiobook_release_mode']='PROTECTED_PACKAGE_V2'
    book['audiobook_public_package_approval']={'schema_version':'audiobook_protected_package_publication.v1','status':'PUBLIC_APPROVED',
        'audio_rights_decision_id':'india-20261020-the-open-window-corrected-v1-audio-owner-adopted','audio_rights_record_sha256':'7f00f2deb1d2ab014801e5154429983bb9198324d8a8c37e17e7cae5a1511cef',
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


def test_separate_audio_rights_revocation_fails_closed(approved,monkeypatch):
    from backend import protected_package_publication as policy
    accepted,revoked=policy.load_production_registry()
    decision=approved['audiobook_public_package_approval']['audio_rights_decision_id']
    monkeypatch.setattr(policy,'load_production_registry',lambda:(accepted,frozenset(set(revoked)|{decision})))
    assert not policy.protected_package_publication_valid(approved)

def test_checked_in_publication_binds_the_actual_sanitized_production_proofs():
    root=Path(__file__).resolve().parents[2]
    book=json.loads((root/'backend/data/controlled_publications/the-open-window/public_book.json').read_text())
    assert protected_package_publication_valid(book)
    acceptance=book['audiobook_public_package_approval']['acceptance']
    evidence=root/'internal/audiobook_lab/release_gate/open_window_publication_evidence_20261026'
    records={}
    for role,digest in acceptance['production_proof_sha256'].items():
        raw=(evidence/(role+'.json')).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==digest
        records[role]=json.loads(raw)
    assert records['playback']['descriptor']==acceptance['release_descriptor_sha256']
    assert records['playback']['durationMs']==491436
    assert records['business']['fullTitleRepeatedOnThisRevision'] is False
    assert records['accounting']['paidSessionsStarted']==0
    assert records['accounting']['authenticatedUsagePaginationPass'] is True
    assert records['accounting']['sourceCommit']==records['accounting']['deployedCommit']==acceptance['accounting_commit']


def test_title_allowlist_is_required_even_for_valid_package(approved,monkeypatch):
    from backend import catalog_truth as catalog
    monkeypatch.setattr(catalog,'PUBLIC_AUDIO_EXPOSURE_ENABLED',False)
    monkeypatch.setattr(catalog,'PROTECTED_PACKAGE_PUBLIC_SLUGS',set())
    assert not catalog.can_expose_audio(approved)


def test_accepted_reader_record_cannot_be_relabelled_as_audio_rights(approved):
    from backend.rights_decision_gate import load_production_registry
    accepted,_=load_production_registry()
    reader=next(k for k in accepted if k.startswith('india-20261026-the-open-window-protected-package-publication'))
    approved['audiobook_public_package_approval']['audio_rights_decision_id']=reader
    approved['audiobook_public_package_approval']['audio_rights_record_sha256']=accepted[reader]
    assert not protected_package_publication_valid(approved)
