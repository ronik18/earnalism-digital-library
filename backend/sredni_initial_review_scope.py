"""Dedicated, default-denied Sredni review usage; never an account-wide cap.

The proposed 60 seconds / three starts / 900-second window confer no authority.
Only a separately admitted exact owner/member binding can enable this path.
"""
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import hashlib
import json
import re

try:
    from . import sredni_initial_review_profile as profile
    from .domain.reading_pass import ReadingPassError
except ImportError:
    import sredni_initial_review_profile as profile
    from domain.reading_pass import ReadingPassError

GRANTS = 'sredni_initial_review_grants'
WORKFLOWS = 'sredni_initial_review_workflows'
OPERATIONS = 'sredni_initial_review_operations'
GRANT_SCHEMA = 'earnalism.sredni_initial_review_grant.v1'
WORKFLOW_SCHEMA = 'earnalism.sredni_initial_review_workflow.v1'
AUTHORITY_SCHEMA = 'earnalism.sredni_initial_review_authority.v1'
SCOPE_KEY = profile.SCOPE_KEY
WORKFLOW_KEY = 'sredni_initial_review_workflow_id'
MAXIMUM_SECONDS = 60
MAXIMUM_MICROSECONDS = 60_000_000
MAXIMUM_STARTS = 3
MAXIMUM_LIFETIME_SECONDS = 900
AUTHORITY_PATH = Path(__file__).with_name('data') / 'sredni_initial_review_authority.json'
SHA = re.compile(r'^[a-f0-9]{64}$')
_VERIFIED = object()


def need(ok, message):
    if not ok:
        raise ReadingPassError('SREDNI_REVIEW_SCOPE_UNAVAILABLE', 403, message)


def utc(value):
    # Mongo BSON dates may be returned as naive UTC; request clocks are checked
    # by their authenticated caller. Never derive time from client playback.
    need(isinstance(value, datetime), 'Dedicated review clock unavailable')
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _now():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def identity_binding(user_id, auth_session_id):
    need(isinstance(user_id, str) and bool(user_id) and isinstance(auth_session_id, str)
         and bool(auth_session_id), 'Exact dedicated member session required')
    return digest({'schema': 'earnalism.sredni_initial_review_member_binding.v1',
        'user_id': user_id, 'auth_session_id': auth_session_id})


def workflow_id(owner_receipt_sha256, user_id):
    # A different login must not create another ceiling under the same receipt.
    return 'sredni-initial-' + digest({'owner_receipt_sha256': owner_receipt_sha256,
        'user_id': user_id, 'slug': profile.SLUG, 'descriptor_sha256': profile.DESCRIPTOR,
        'package_version': profile.PACKAGE})


def load_authority():
    try:
        value = json.loads(AUTHORITY_PATH.read_text())
    except (OSError, ValueError):
        need(False, 'Dedicated owner authority unavailable')
    need(isinstance(value, dict) and set(value) == {'schema', 'accepted'}
         and value['schema'] == AUTHORITY_SCHEMA and isinstance(value['accepted'], list),
         'Dedicated authority schema unavailable')
    seen = set()
    for row in value['accepted']:
        need(isinstance(row, dict) and set(row) == {'owner_receipt_sha256', 'identity_binding_sha256'}
             and all(isinstance(v, str) and SHA.fullmatch(v) for v in row.values()),
             'Dedicated authority record unavailable')
        pair = (row['owner_receipt_sha256'], row['identity_binding_sha256'])
        need(pair not in seen, 'Ambiguous dedicated authority'); seen.add(pair)
    return value


def authority_allows(grant):
    actual = identity_binding(grant.get('user_id'), grant.get('auth_session_id'))
    need(grant.get('identity_binding_sha256') == actual,
         'Dedicated identity cannot be relabeled onto another member')
    return {'owner_receipt_sha256': grant.get('owner_receipt_sha256'),
            'identity_binding_sha256': actual} in load_authority()['accepted']


def is_scoped_document(document):
    scope = document.get('scope') or {}
    return (isinstance(scope, Mapping) and (SCOPE_KEY in scope or WORKFLOW_KEY in scope
            or scope.get('acceptance_test_id') == profile.TEST_ID)) \
        or document.get('acceptance_test_id') == profile.TEST_ID


def validate_workflow(workflow):
    w = workflow
    need(isinstance(w, Mapping) and w.get('schema') == WORKFLOW_SCHEMA,
         'Dedicated retained workflow unavailable')
    need(isinstance(w.get('owner_receipt_sha256'), str) and SHA.fullmatch(w['owner_receipt_sha256'])
         and w.get('identity_binding_sha256') == identity_binding(w.get('user_id'), w.get('auth_session_id'))
         and w.get('slug') == profile.SLUG and w.get('descriptor_sha256') == profile.DESCRIPTOR
         and w.get('package_version') == profile.PACKAGE and w.get('country') == 'IN',
         'Dedicated workflow identity or edition changed')
    need(type(w.get('maximum_seconds')) is int and w['maximum_seconds'] == MAXIMUM_SECONDS
         and type(w.get('maximum_microseconds')) is int and w['maximum_microseconds'] == MAXIMUM_MICROSECONDS
         and type(w.get('maximum_starts')) is int and w['maximum_starts'] == MAXIMUM_STARTS,
         'Dedicated fixed ceiling changed')
    for key, limit in [('used_microseconds', MAXIMUM_MICROSECONDS),
                       ('used_credit_seconds', MAXIMUM_SECONDS), ('starts_used', MAXIMUM_STARTS)]:
        need(type(w.get(key)) is int and 0 <= w[key] <= limit, 'Dedicated cumulative counter unavailable')
    need(type(w.get('revision')) is int and w['revision'] >= 0, 'Dedicated workflow revision unavailable')
    need(w.get('_id') == workflow_id(w.get('owner_receipt_sha256'), w.get('user_id')),
         'Dedicated original workflow identity changed')
    need(timedelta(0) < utc(w.get('expires_at')) - utc(w.get('created_at'))
         <= timedelta(seconds=MAXIMUM_LIFETIME_SECONDS), 'Dedicated original window changed')
    return w


class SredniReviewBudget(Mapping):
    """Only resolve() produces this verified server object, never JSON scope."""
    def __init__(self, db, grant, workflow, scope, *, cutoff, access_open=False, _verified=None):
        need(_verified is _VERIFIED, 'Dedicated budget must be resolved by the server')
        self.db, self.grant, self.workflow = db, copy.deepcopy(grant), copy.deepcopy(workflow)
        self.scope, self.cutoff = dict(scope), utc(cutoff)
        self.access_open = bool(access_open)

    def _view(self):
        return {'schema': GRANT_SCHEMA, 'test_id': profile.TEST_ID, 'maximum_seconds': MAXIMUM_SECONDS,
            'consumed_seconds': max((self.workflow['used_microseconds'] + 999999) // 1000000,
                                    self.workflow['used_credit_seconds']), 'expires_at': self.cutoff}

    def __getitem__(self, key): return self._view()[key]
    def __iter__(self): return iter(self._view())
    def __len__(self): return len(self._view())

    def wallet_remaining(self):
        return MAXIMUM_SECONDS - self.workflow['used_credit_seconds']

    def remaining(self, now, pending_debit=0):
        need(type(pending_debit) is int and pending_debit >= 0, 'Dedicated pending debit unavailable')
        if not self.access_open or self.grant['state'] != 'OPEN' or utc(now) >= self.cutoff:
            return 0
        return max(0, min((MAXIMUM_MICROSECONDS - self.workflow['used_microseconds']) // 1000000,
                          self.wallet_remaining() - pending_debit))

    def validated_selection_scope(self, *, now):
        need(authority_allows(self.grant) and self.remaining(now) > 0,
             'Dedicated review expired, revoked or exhausted')
        return dict(self.scope)

    def _transaction(self, session):
        need(session is not None and getattr(session, 'in_transaction', False),
             'Dedicated review transaction required')
        need(authority_allows(self.grant), 'Dedicated owner authority changed')

    async def claim(self, session, *, starting=False):
        self._transaction(session)
        g = self.grant
        if starting:
            need(g['state'] == 'OPEN' and self.remaining(_now()) > 0
                 and self.workflow['starts_used'] < MAXIMUM_STARTS,
                 'Dedicated start quota expired or exhausted')
        result = await self.db[GRANTS].update_one(
            {'_id': g['_id'], 'user_id': g['user_id'], 'auth_session_id': g['auth_session_id'],
             'state': g['state'], 'epoch': g['epoch']}, {'$inc': {'epoch': 1}}, session=session)
        need(result.modified_count == 1, 'Dedicated grant changed; no uncapped fallback')
        g['epoch'] += 1
        if starting:
            await self._increment({'starts_used': 1}, session)

    async def _increment(self, increments, session):
        w = self.workflow
        result = await self.db[WORKFLOWS].update_one(
            {'_id': w['_id'], 'user_id': w['user_id'], 'auth_session_id': w['auth_session_id'],
             'revision': w['revision'], 'used_microseconds': w['used_microseconds'],
             'used_credit_seconds': w['used_credit_seconds'], 'starts_used': w['starts_used']},
            {'$inc': {**increments, 'revision': 1}}, session=session)
        need(result.modified_count == 1, 'Dedicated cumulative counter changed')
        for key, value in increments.items(): w[key] += value
        w['revision'] += 1

    async def interval(self, microseconds, session):
        need(type(microseconds) is int and microseconds >= 0, 'Dedicated server interval invalid')
        self._transaction(session)
        value = min(microseconds, MAXIMUM_MICROSECONDS - self.workflow['used_microseconds'])
        if value:
            await self.claim(session)
            await self._increment({'used_microseconds': value}, session)
        return value

    async def debit(self, seconds, session):
        need(type(seconds) is int and 0 <= seconds <= self.wallet_remaining(),
             'Dedicated cumulative wallet ceiling exceeded')
        self._transaction(session)
        if seconds:
            await self.claim(session)
            await self._increment({'used_credit_seconds': seconds}, session)


async def resolve(db, document, now, session=None, *, starting=False, current_access=False):
    need(bool(load_authority()['accepted']), 'No dedicated owner authority is installed')
    scope = document.get('scope') or {}; gid = scope.get(SCOPE_KEY)
    need(isinstance(gid, str) and bool(gid) and document.get('content_type') == 'audio'
         and document.get('content_id') == profile.SLUG, 'Exact dedicated Sredni lease required')
    need(not any(k in scope for k in ('native_audio_review_grant_id', 'native_audio_review_workflow_id',
         'native_replacement_authorization_id')), 'Original120 scope cannot authorize Sredni')
    if not starting:
        need(document.get('acceptance_test_id') == profile.TEST_ID, 'Dedicated lease binding missing')
    uid, sid = document.get('user_id'), document.get('auth_session_id')
    identity_binding(uid, sid)
    user = await db.users.find_one({'id': uid, 'role': 'user'},
        {'status': 1, 'active_user_session_id': 1, 'reader_acceptance_budget': 1,
         'reading_fractional_microseconds': 1}, session=session)
    need(user and 'reader_acceptance_budget' not in user, 'Conflicting retained account cap or missing member')
    carry = user.get('reading_fractional_microseconds', 0)
    need(type(carry) is int and 0 <= carry < 1000000, 'Dedicated current carry unavailable')
    auth = await db.user_sessions.find_one({'id': sid, 'user_id': uid}, session=session)
    need(auth and auth.get('status') in {'active', 'revoked', 'expired'}, 'Dedicated member session unavailable')
    g = await db[GRANTS].find_one({'_id': gid, 'user_id': uid, 'auth_session_id': sid}, session=session)
    need(g and g.get('schema') == GRANT_SCHEMA and g.get('state') in {'OPEN', 'REVOKED', 'CLOSED'}
         and type(g.get('epoch')) is int and g['epoch'] >= 0 and authority_allows(g),
         'Dedicated scoped grant unavailable')
    w = await db[WORKFLOWS].find_one({'_id': g.get('workflow_id'), 'user_id': uid}, session=session)
    validate_workflow(w)
    bindings = {'user_id': uid, 'auth_session_id': sid, 'owner_receipt_sha256': g['owner_receipt_sha256'],
        'identity_binding_sha256': identity_binding(uid, sid), 'slug': profile.SLUG,
        'descriptor_sha256': profile.DESCRIPTOR, 'package_version': profile.PACKAGE, 'country': 'IN'}
    need(all(g.get(k) == v and w.get(k) == v for k, v in bindings.items()), 'Dedicated original workflow binding changed')
    need(utc(w['created_at']) <= utc(g.get('created_at')) <= utc(now)
         and utc(g['created_at']) < utc(g.get('expires_at')) <= utc(w['expires_at']),
         'Dedicated grant cannot extend the original window')
    cutoff = min(utc(g['expires_at']), utc(w['expires_at']), utc(auth.get('idle_expires_at')),
                 utc(auth.get('absolute_expires_at')))
    for state, field in [('REVOKED', 'revoked_at'), ('CLOSED', 'closed_at')]:
        if g['state'] == state:
            terminal = utc(g.get(field)); need(utc(g['created_at']) <= terminal <= utc(now), 'Dedicated terminal cutoff unavailable')
            cutoff = min(cutoff, terminal)
    if auth['status'] == 'revoked':
        cutoff = min(cutoff, utc(auth.get('revoked_at')))
    expected = {SCOPE_KEY: gid, WORKFLOW_KEY: w['_id'], 'acceptance_test_id': profile.TEST_ID,
        'manifest_version': profile.PACKAGE, 'package_version': profile.PACKAGE,
        'segmentation_version': profile.DESCRIPTOR, 'release_descriptor_sha256': profile.DESCRIPTOR,
        'release_country': 'IN'}
    need(all(scope.get(k) == v for k, v in expected.items()), 'Dedicated server scope changed')
    live = user.get('status') == 'active' and user.get('active_user_session_id') == sid and auth['status'] == 'active'
    result = SredniReviewBudget(db, g, w, expected, cutoff=cutoff, access_open=live, _verified=_VERIFIED)
    if starting or current_access:
        need(live and result.remaining(now) > 0,
             'Dedicated authenticated access expired or exhausted')
    if starting: need(w['starts_used'] < MAXIMUM_STARTS, 'Dedicated three-start quota exhausted')
    return result


async def member_budget(db, book, user_id, auth_session_id, *, country, now, session_scope=None):
    if not load_authority()['accepted'] or profile.candidate(book) is None:
        return None
    profile.rights_for_candidate(book, country=country, now=now)
    identity_binding(user_id, auth_session_id)
    query = {'user_id': user_id, 'auth_session_id': auth_session_id, 'slug': profile.SLUG,
             'descriptor_sha256': profile.DESCRIPTOR, 'package_version': profile.PACKAGE}
    gid = (session_scope or {}).get(SCOPE_KEY)
    if session_scope is not None:
        need(isinstance(gid, str) and bool(gid), 'Dedicated existing lease scope missing'); query['_id'] = gid
    else: query['state'] = 'OPEN'
    rows = await db[GRANTS].find(query).max_time_ms(5000).limit(2).to_list(2)
    if not rows:
        need(session_scope is None, 'Dedicated lease grant removed'); return None
    need(len(rows) == 1, 'Ambiguous dedicated review grants')
    g = rows[0]
    scope = {SCOPE_KEY: g['_id'], WORKFLOW_KEY: g['workflow_id'], 'acceptance_test_id': profile.TEST_ID,
        'manifest_version': profile.PACKAGE, 'package_version': profile.PACKAGE,
        'segmentation_version': profile.DESCRIPTOR, 'release_descriptor_sha256': profile.DESCRIPTOR, 'release_country': 'IN'}
    if session_scope is not None:
        need(all(session_scope.get(k) == v for k, v in scope.items()), 'Dedicated existing session changed')
    return await resolve(db, {'user_id': user_id, 'auth_session_id': auth_session_id,
        'content_type': 'audio', 'content_id': profile.SLUG, 'scope': scope,
        'acceptance_test_id': profile.TEST_ID}, now, starting=False, current_access=True)


async def member_scope(db, book, user_id, auth_session_id, *, country, now, session_scope=None):
    budget = await member_budget(db, book, user_id, auth_session_id, country=country, now=now, session_scope=session_scope)
    return None if budget is None else budget.validated_selection_scope(now=now)
