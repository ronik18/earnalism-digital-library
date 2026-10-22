"""Read-only, bounded startup identity gate. Never imports application startup.

The policy is nonsecret configuration, qualified against the intended dataset
before a separately approved cutover. Missing policy never disables this gate.
No connection strings, server error text or customer records are returned.
"""
import asyncio
import json
import re
from uuid import UUID

POLICY_ENV = 'EARNALISM_STARTUP_DATA_GUARD_JSON'


class StartupDataGuardError(RuntimeError):
    pass


def _fail(stage):
    raise StartupDataGuardError('STARTUP_DATA_GUARD_' + stage) from None


def _pairs(items, left, right):
    if not isinstance(items, list) or not items:
        _fail('AUTH_RESPONSE')
    result = []
    for row in items:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in (left, right)):
            _fail('AUTH_RESPONSE')
        result.append((row[left], row[right]))
    if len(set(result)) != len(result):
        _fail('AUTH_RESPONSE')
    return set(result)


def parse_policy(raw):
    try:
        if not isinstance(raw, str) or len(raw) > 8192:
            _fail('POLICY')
        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    _fail('POLICY')
                out[key] = value
            return out
        p = json.loads(raw, object_pairs_hook=unique)
        if set(p) != {'database', 'principal', 'authentication_database', 'markers'}:
            _fail('POLICY')
        for key in ('database', 'principal', 'authentication_database'):
            if not isinstance(p[key], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', p[key]):
                _fail('POLICY')
        if p['database'] in {'admin', 'local', 'config', 'test'}:
            _fail('POLICY')
        markers = p['markers']
        if not isinstance(markers, list) or not 2 <= len(markers) <= 4:
            _fail('POLICY')
        ids, slugs = set(), set()
        for m in markers:
            if set(m) != {'uuid', 'slug', 'version', 'segmentation_version', 'generation'}:
                _fail('POLICY')
            if str(UUID(m['uuid'])) != m['uuid'] or m['uuid'] in ids:
                _fail('POLICY')
            if not isinstance(m['slug'], str) or not re.fullmatch(r'[a-z0-9-]{1,150}', m['slug']) or m['slug'] in slugs:
                _fail('POLICY')
            for key in ('version', 'segmentation_version'):
                if not isinstance(m[key], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,150}', m[key]):
                    _fail('POLICY')
            if type(m['generation']) is not int or m['generation'] < 0:
                _fail('POLICY')
            ids.add(m['uuid']); slugs.add(m['slug'])
        return p
    except StartupDataGuardError:
        raise
    except Exception:
        _fail('POLICY')


async def _verify(client, db, p):
    if db.name != p['database']:
        _fail('DATABASE')
    result = await client.admin.command({'connectionStatus': 1, 'showPrivileges': False})
    if not isinstance(result, dict) or result.get('ok') != 1:
        _fail('AUTH_RESPONSE')
    auth = result.get('authInfo')
    if not isinstance(auth, dict):
        _fail('AUTH_RESPONSE')
    if _pairs(auth.get('authenticatedUsers'), 'user', 'db') != {(p['principal'], p['authentication_database'])}:
        _fail('PRINCIPAL')
    # A separate restricted principal, never Atlas admin or an unidentified old user.
    if _pairs(auth.get('authenticatedUserRoles'), 'role', 'db') != {('readWrite', p['database'])}:
        _fail('ROLES')
    for m in p['markers']:
        rows = await db.books.find({'id': m['uuid']}, {'_id': 0, 'id': 1, 'slug': 1}).max_time_ms(1000).to_list(2)
        if rows != [{'id': m['uuid'], 'slug': m['slug']}]:
            _fail('CATALOGUE')
        rows = await db.reader_segment_manifests.find({'book_slug': m['slug'], 'status': 'active'},
            {'_id': 0, 'version': 1, 'segmentation_version': 1}).max_time_ms(1000).to_list(2)
        if rows != [{'version': m['version'], 'segmentation_version': m['segmentation_version']}]:
            _fail('PUBLICATION')
        rows = await db.reader_segment_activation_state.find({'book_slug': m['slug']},
            {'_id': 0, 'active_segmentation_version': 1, 'generation': 1}).max_time_ms(1000).to_list(2)
        # Existing resolver defines absent activation state as generation zero.
        if not rows and m['generation'] == 0:
            continue
        if len(rows) != 1 or type(rows[0].get('generation')) is not int or rows[0] != {
                'active_segmentation_version': m['segmentation_version'], 'generation': m['generation']}:
            _fail('ACTIVATION')


async def verify_startup_data(client, db, raw_policy):
    p = parse_policy(raw_policy)
    try:
        await asyncio.wait_for(_verify(client, db, p), timeout=10)
    except StartupDataGuardError:
        raise
    except asyncio.TimeoutError:
        _fail('TIMEOUT')
    except Exception:
        _fail('READ_UNAVAILABLE')
