"""Synthetic account-source eligibility only; no real identity, DB, or runtime."""
import asyncio
import hashlib
import json
from datetime import datetime, timezone

import pytest
from backend import sredni_initial_review_scope as scope
from backend.domain.reading_pass import ReadingPassError

OWNER = 'a' * 64
UID = 'SYNTHETIC-account'
SID = 'SYNTHETIC-session-1'
V2 = 'earnalism.sredni_initial_review_authority.v2'


def policy(uid=UID, owner=OWNER):
    return {'schema': V2, 'accepted': [{'owner_receipt_sha256': owner,
        'member_account_sha256': scope.member_account_binding(uid)}]}


def grant(uid=UID, sid=SID, owner=OWNER):
    return {'user_id': uid, 'auth_session_id': sid, 'owner_receipt_sha256': owner,
        'identity_binding_sha256': scope.identity_binding(uid, sid)}


def test_account_binding_exact_canonical_schema_and_distinct_from_session():
    raw = json.dumps({'schema': 'earnalism.sredni_initial_review_member_account_binding.v1',
        'user_id': UID}, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    assert scope.AUTHORITY_SCHEMA == V2
    assert scope.member_account_binding(UID) == hashlib.sha256(raw).hexdigest()
    assert scope.member_account_binding(UID) != scope.identity_binding(UID, SID)


@pytest.mark.parametrize('uid', [None, '', 0, True, [], {}])
def test_account_binding_invalid_uid_denied(uid):
    with pytest.raises(ReadingPassError): scope.member_account_binding(uid)


def test_v2_empty_denies_before_profile_or_db(monkeypatch, tmp_path):
    f = tmp_path / 'empty.json'; f.write_text(json.dumps({'schema': V2, 'accepted': []}))
    monkeypatch.setattr(scope, 'AUTHORITY_PATH', f)
    assert scope.load_authority() == {'schema': V2, 'accepted': []}
    assert scope.authority_allows(grant()) is False
    monkeypatch.setattr(scope.profile, 'candidate', lambda *_: pytest.fail('PROFILE_BEFORE_AUTHORITY'))
    class NoDB:
        def __getattr__(self, name): pytest.fail('DB_BEFORE_AUTHORITY')
        def __getitem__(self, name): pytest.fail('DB_BEFORE_AUTHORITY')
    assert asyncio.run(scope.member_budget(NoDB(), {}, UID, SID, country='IN', now=datetime.now(timezone.utc))) is None


@pytest.mark.parametrize('mutation', ['v1', 'v1-row', 'mixed-row', 'top-extra', 'row-extra',
    'duplicate', 'bad-owner', 'bad-account', 'accepted-not-list'])
def test_loader_rejects_legacy_mixed_extra_duplicate_and_bad_hashes(monkeypatch, tmp_path, mutation):
    value = policy()
    if mutation == 'v1': value['schema'] = 'earnalism.sredni_initial_review_authority.v1'
    elif mutation == 'v1-row': value['accepted'][0] = {'owner_receipt_sha256': OWNER, 'identity_binding_sha256': scope.identity_binding(UID, SID)}
    elif mutation == 'mixed-row': value['accepted'][0]['identity_binding_sha256'] = scope.identity_binding(UID, SID)
    elif mutation == 'top-extra': value['extra'] = True
    elif mutation == 'row-extra': value['accepted'][0]['extra'] = True
    elif mutation == 'duplicate': value['accepted'] *= 2
    elif mutation == 'bad-owner': value['accepted'][0]['owner_receipt_sha256'] = 'not-sha'
    elif mutation == 'bad-account': value['accepted'][0]['member_account_sha256'] = 'F' * 64
    else: value['accepted'] = {}
    f = tmp_path / 'invalid.json'; f.write_text(json.dumps(value)); monkeypatch.setattr(scope, 'AUTHORITY_PATH', f)
    with pytest.raises(ReadingPassError): scope.load_authority()


def test_two_sessions_same_account_eligible_only_with_their_exact_identity(monkeypatch):
    monkeypatch.setattr(scope, 'load_authority', policy)
    first, second = grant(), grant(sid='SYNTHETIC-session-2')
    assert scope.authority_allows(first) is True
    assert scope.authority_allows(second) is True
    assert first['identity_binding_sha256'] != second['identity_binding_sha256']
    copied = {**second, 'identity_binding_sha256': first['identity_binding_sha256']}
    with pytest.raises(ReadingPassError): scope.authority_allows(copied)


@pytest.mark.parametrize('mutation', ['other-user', 'other-owner', 'copied-full-hash', 'renamed-sid', 'injected-account'])
def test_nonmatching_owner_member_identity_and_injected_account_denied(monkeypatch, mutation):
    monkeypatch.setattr(scope, 'load_authority', policy)
    value = grant()
    if mutation == 'other-user': value = grant(uid='SYNTHETIC-other')
    elif mutation == 'other-owner': value['owner_receipt_sha256'] = 'b' * 64
    elif mutation == 'copied-full-hash': value['identity_binding_sha256'] = scope.identity_binding('SYNTHETIC-other', SID)
    elif mutation == 'renamed-sid': value['auth_session_id'] = 'SYNTHETIC-session-2'
    else:
        value = grant(uid='SYNTHETIC-other'); value['member_account_sha256'] = scope.member_account_binding(UID)
    if mutation in ('copied-full-hash', 'renamed-sid'):
        with pytest.raises(ReadingPassError): scope.authority_allows(value)
    else: assert scope.authority_allows(value) is False


def test_caller_account_field_does_not_override_derived_account(monkeypatch):
    monkeypatch.setattr(scope, 'load_authority', policy)
    assert scope.authority_allows({**grant(), 'member_account_sha256': 'f' * 64}) is True


def test_v1_session_hash_cannot_be_renamed_into_account_trust(monkeypatch):
    monkeypatch.setattr(scope, 'load_authority', lambda: {'schema': V2, 'accepted': [
        {'owner_receipt_sha256': OWNER, 'member_account_sha256': scope.identity_binding(UID, SID)}]})
    assert scope.authority_allows(grant()) is False


def test_workflow_key_is_stable_across_login_not_new_allowance():
    assert scope.workflow_id(OWNER, UID) == scope.workflow_id(OWNER, UID)
    assert scope.workflow_id(OWNER, UID) != scope.workflow_id(OWNER, 'SYNTHETIC-other')
    assert (scope.MAXIMUM_MICROSECONDS, scope.MAXIMUM_SECONDS, scope.MAXIMUM_STARTS, scope.MAXIMUM_LIFETIME_SECONDS) == (60000000, 60, 3, 900)


def test_existing_grant_remains_exact_sid_even_when_account_eligible(monkeypatch):
    from backend.tests import test_sredni_initial_review_domain as domain
    now = datetime.now(timezone.utc); db, workflow, actual = domain.seeded(now)
    monkeypatch.setattr(scope, 'load_authority', lambda: policy(actual['user_id'], actual['owner_receipt_sha256']))
    doc = domain.document(workflow, actual)
    rotated = {**doc, 'auth_session_id': 'SYNTHETIC-new-login'}
    assert scope.authority_allows(grant(actual['user_id'], 'SYNTHETIC-new-login', actual['owner_receipt_sha256'])) is True
    before = domain.snapshot(db)
    with pytest.raises(ReadingPassError): asyncio.run(scope.resolve(db, rotated, now, starting=True))
    assert domain.snapshot(db) == before
