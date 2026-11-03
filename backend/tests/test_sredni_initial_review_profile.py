"""Pure exact profile tests; no actual grant/admission/DB/financial authority."""
from pathlib import Path
from datetime import datetime,timezone
import copy,json,sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'internal/audiobook_lab/scripts'),str(ROOT/'backend')]
import sredni_initial_review_profile as profile
import native_audiobook_profiles as old_profiles


@pytest.fixture
def staged():
    # Exact owned-copy stage output d794, derived from six genuine retained
    # storage documents by the separately reviewed source-stage helper13fa.
    # This fixed source fixture is not a production grant/runtime receipt.
    # Never depend on mutable canonical pre-stage versus post-stage state.
    return json.loads((Path(__file__).parent/'fixtures/sredni-initial-sourceqa-staged-book.json').read_text())


def test_actual_staged_profile_rights_metadata_without_runtime_authority(staged):
    package,marker=profile.rights_for_candidate(staged,country='IN',now=datetime.now(timezone.utc))
    assert package['package_version']==profile.PACKAGE and marker['narrator_metadata']['narration_disclosure']==profile.DISCLOSURE
    assert marker['private_playback_authorized'] is marker['public_release_authorized'] is False
    assert old_profiles.profile_for_slug(profile.SLUG) is None and old_profiles.review_profile(staged) is None


@pytest.mark.parametrize('input_budget',[None,{}, {'native_audio_review_grant_id':'old120'}, {'sredni_initial_review_grant_id':'client-forgery'}, {'original_ceiling_seconds':120}])
def test_missing_dedicated_transactional_grant_always_denies_selection_and_credits(staged,input_budget):
    assert profile.selected_from_verified_budget(staged,input_budget,country='IN',now=datetime.now(timezone.utc)) is None
    assert profile.listener_metadata_from_verified_budget(staged,input_budget,country='IN',now=datetime.now(timezone.utc)) is None


@pytest.mark.parametrize('kind',['title','active','audio_enabled','public_approval','canary','marker','package','metadata','receipt','manifest','evidence','hold','rights'])
def test_bound_profile_changes_deny(staged,kind):
    book=copy.deepcopy(staged);marker=book[profile.FIELD]
    if kind=='title':book['slug']='the-selfish-giant'
    elif kind=='active':book['audiobook_active_release']={'status':'ACTIVE'}
    elif kind=='audio_enabled':book['audio_enabled']=True
    elif kind=='public_approval':book['audiobook_public_package_approval']={'status':'PUBLIC_APPROVED'}
    elif kind=='canary':book['audiobook_package_canary']={'rollout_percentage':5}
    elif kind=='marker':marker['status']='PROMOTED_PUBLIC'
    elif kind=='package':marker['candidate_package_version']='sha256-'+'0'*64
    elif kind=='metadata':marker['narrator_metadata']['narration_disclosure']='Cedar'
    elif kind=='receipt':
        evidence=book['audiobook_package_release_evidence'][profile.DESCRIPTOR];evidence['primary_receipt_sha256']='f'*64;marker['package_release_evidence_sha256']=profile.digest(evidence)
    elif kind=='manifest':marker['release_manifest_sha256']='a'*64
    elif kind=='evidence':marker['package_release_evidence_sha256']='b'*64
    elif kind=='hold':marker['downstream_gates_unchanged']=[]
    else:marker['audio_use_decision']['valid_until']='2099-01-01T00:00:00Z'
    with pytest.raises(ValueError):profile.rights_for_candidate(book,country='IN',now=datetime.now(timezone.utc))


@pytest.mark.parametrize('country',['US',None,''])
def test_no_other_territory_or_untrusted_country(staged,country):
    with pytest.raises(profile.ProfileError,match='India'):profile.rights_for_candidate(staged,country=country,now=datetime.now(timezone.utc))


def test_not_staged_and_untrusted_clock_denied(staged):
    assert profile.candidate({}) is None
    with pytest.raises(profile.ProfileError):profile.rights_for_candidate(staged,country='IN',now=datetime.now())


def test_revoked_audio_record_denied(staged,monkeypatch):
    accepted,revoked=profile.load_production_registry();decision=staged[profile.FIELD]['audio_use_decision']['decision_id']
    monkeypatch.setattr(profile,'load_production_registry',lambda:(accepted,frozenset(set(revoked)|{decision})))
    with pytest.raises(profile.ProfileError,match='rights denied'):profile.rights_for_candidate(staged,country='IN',now=datetime.now(timezone.utc))
