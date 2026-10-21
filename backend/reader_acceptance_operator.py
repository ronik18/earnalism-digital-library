"""Protected-runtime operator, not a public/admin HTTP endpoint.

Execute only through an authorized Railway SSH session with an explicitly
approved identity file. No credentials are acquired or printed. Fixed budget;
no balance reads, credit, entitlement grant, reset or automatic mutation retry.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

MODE_VARIABLE = 'READER_ACCEPTANCE_RELEASE_MODE'
MODE = 'cap-only-v1'
PROJECT = 'a8533934-35c4-463e-9f43-577a9ac391ee'
ENVIRONMENT = '580b250c-80ee-48ad-bfbe-fa4e31a6b378'
SERVICE = '5af42e7e-f518-4f6a-b602-d9950866501f'
ACCOUNT_SELECTOR_SHA256 = 'c4ac3285d74eeba22185ccd4cb61c00a17e477c085f3d8c3a01f427f03e74a3a'
TEST_ID = 'reader-desiree-complete-book-acceptance-20261020-v1'
BOOK = 'dsires-baby'
MANIFEST = '124f8b020c4fa88eba42a6d4'
SEGMENTATION = 'canonical-html-blocks-v1'
MAXIMUM = 180
EXPIRY_SECONDS = 900


class OperatorStop(ValueError):
    pass


class CommitOutcomeUnknown(OperatorStop):
    pass


def containment_enabled(environ=None):
    value = (os.environ if environ is None else environ).get(MODE_VARIABLE, '')
    if value not in ('', MODE):
        raise OperatorStop('Unknown acceptance release mode; startup stopped')
    return value == MODE


def verify_runtime(server, expected_revision, *, mutation=False):
    expected = {'RAILWAY_PROJECT_ID': PROJECT, 'RAILWAY_ENVIRONMENT_ID': ENVIRONMENT,
                'RAILWAY_SERVICE_ID': SERVICE, 'RAILWAY_GIT_COMMIT_SHA': expected_revision}
    if not re.fullmatch(r'[a-f0-9]{40}', expected_revision) or any(os.environ.get(k) != v for k, v in expected.items()):
        raise OperatorStop('Exact provider runtime identity mismatch')
    if server.ENVIRONMENT != 'production' or not server.READING_PASS_V2_ENABLED:
        raise OperatorStop('Production Reading Pass context unavailable')
    if mutation and (not containment_enabled() or not hasattr(server.reading_pass_service, '_acceptance_budget')):
        raise OperatorStop('Cap-capable contained runtime required')


async def baseline_startup_noop(server, *, session=None):
    """Sufficient no-op conditions for unchanged baseline startup; read-only.

    This reads only index metadata and the exact existing bootstrap plan's
    pointer identities, never manuscripts, wallet fields or a user directory.
    """
    if server.ENABLE_STARTUP_DB_MAINTENANCE:
        raise OperatorStop('Baseline general maintenance is enabled; rollback not qualified')
    plan_path = Path(server.__file__).parent / 'data' / 'approved_reader_bootstrap.json'
    plan = json.loads(plan_path.read_text())
    entries = plan.get('titles')
    if plan.get('schema') != 'earnalism.approved-reader-bootstrap.v1' or plan.get('bootstrap_only') is not True or plan.get('territory') != 'IN' or plan.get('target_characters') != 3200 or not isinstance(entries, list) or not entries:
        raise OperatorStop('Exact baseline initialization plan unavailable')
    slugs = [entry.get('slug') for entry in entries if isinstance(entry, dict)]
    if len(slugs) != len(entries) or any(not isinstance(slug, str) or not slug for slug in slugs) or len(set(slugs)) != len(slugs):
        raise OperatorStop('Ambiguous baseline initialization plan')
    required = {
        'reader_content_segments': [([('book_slug', 1), ('page_index', 1), ('segmentation_version', 1)], None)],
        'reader_segment_manifests': [([('book_slug', 1), ('segmentation_version', 1)], None), ([('book_slug', 1)], {'status': 'active'})],
        'reader_segment_activation_state': [([('book_slug', 1)], None)],
        'reader_segment_activation_operations': [([('operation_id', 1)], None)],
    }
    for name, constraints in required.items():
        indexes = await server.db[name].index_information()
        for keys, partial in constraints:
            if not any(spec.get('unique') is True and list(spec.get('key', [])) == keys and spec.get('partialFilterExpression') == partial for spec in indexes.values()):
                raise OperatorStop('Missing baseline initialization index; no create/repair attempted')
    for slug in slugs:
        pointer = await server.db.reader_segment_activation_state.find_one({'book_slug': slug}, {'_id': 1}, session=session)
        active = await server.db.reader_segment_manifests.find_one({'book_slug': slug, 'status': 'active'}, {'_id': 1}, session=session)
        if not pointer and not active:
            # Even if source/rights would currently HOLD, do not infer future
            # no-op from that. Require the baseline's explicit preserve branch.
            raise OperatorStop('Baseline could initialize an absent pointer; stop')
    return {'baseline_startup': 'NO_PUBLICATION_WRITE_PRECONDITIONS_OBSERVED',
            'planned_titles': len(slugs), 'indexes_verified': True,
            'limitation': 'Read-only observation; recheck immediately before rollback, no concurrent publication changes'}


def _checked_budget(record, user_id):
    fixed = {'schema': 'reader-acceptance-budget.v1', 'user_id': user_id,
             'content_type': 'text', 'content_id': BOOK, 'test_id': TEST_ID,
             'manifest_version': MANIFEST, 'segmentation_version': SEGMENTATION,
             'maximum_seconds': MAXIMUM}
    if not isinstance(record, dict) or any(record.get(k) != v for k, v in fixed.items()) or type(record.get('consumed_seconds')) is not int or not 0 <= record['consumed_seconds'] <= MAXIMUM or record.get('status') not in ('enabled', 'disabled') or not isinstance(record.get('expires_at'), datetime):
        raise OperatorStop('Retained budget differs from exact approved scope')
    return record


async def budget_operation(server, *, action, user_id, expected_consumed=None, session=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', user_id) or hashlib.sha256(user_id.encode()).hexdigest() != ACCOUNT_SELECTOR_SHA256:
        raise OperatorStop('Exact internal account ID required')
    user = await server.db.users.find_one({'id': user_id, 'role': 'user'},
        {'_id': 0, 'id': 1, 'role': 1, 'status': 1, 'reader_acceptance_budget': 1, 'active_reading_session': 1}, session=session)
    if not user:
        raise OperatorStop('Exact normal account unavailable')
    record = user.get('reader_acceptance_budget')
    if action == 'status':
        return {'budget': _checked_budget(record, user_id), 'account_status': user.get('status')}
    active = await server.db.reading_pass_sessions.find_one({'user_id': user_id, 'status': {'$in': ['active', 'paused']}}, {'_id': 0, 'id': 1}, session=session)
    if active or user.get('active_reading_session'):
        raise OperatorStop('Active/unsettled session exists; no close/debit performed by operator')
    query = {'id': user_id, 'role': 'user', 'status': 'active'}
    if action == 'enable':
        if record is not None or 'reader_acceptance_budget' in user or user.get('status') != 'active':
            raise OperatorStop('Budget already retained or account unavailable; never reset/replace')
        active_manifest = await server.db.reader_segment_manifests.find_one(
            {'book_slug': BOOK, 'status': 'active', 'version': MANIFEST, 'segmentation_version': SEGMENTATION}, {'_id': 0, 'version': 1}, session=session)
        pointer = await server.db.reader_segment_activation_state.find_one({'book_slug': BOOK},
            {'_id': 0, 'active_segmentation_version': 1, 'generation': 1}, session=session)
        if not active_manifest or (pointer and (pointer.get('active_segmentation_version') != SEGMENTATION or type(pointer.get('generation')) is not int or pointer['generation'] != 0)):
            raise OperatorStop('Exact retained edition/generation mismatch')
        query['reader_acceptance_budget'] = {'$exists': False}
        record = dict(schema='reader-acceptance-budget.v1', user_id=user_id, content_type='text', content_id=BOOK,
            test_id=TEST_ID, manifest_version=MANIFEST, segmentation_version=SEGMENTATION,
            maximum_seconds=MAXIMUM, consumed_seconds=0, status='enabled',
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=EXPIRY_SECONDS))
        change = {'reader_acceptance_budget': record}
    else:
        record = _checked_budget(record, user_id)
        if type(expected_consumed) is not int or record['consumed_seconds'] != expected_consumed:
            raise OperatorStop('Exact observed consumption CAS required')
        if record['status'] == 'disabled' and (action == 'disable' or (action == 'rollback-guard' and user.get('status') == 'blocked')):
            return {'status': 'ALREADY_SATISFIED', 'consumed_seconds': expected_consumed}
        if user.get('status') != 'active':
            raise OperatorStop('Account status changed')
        query.update({f'reader_acceptance_budget.{k}': v for k, v in record.items()})
        change = {'reader_acceptance_budget.status': 'disabled'}
        if action == 'rollback-guard':
            change['status'] = 'blocked'
        elif action != 'disable':
            raise OperatorStop('Unsupported operation')
    updated = await server.db.users.update_one(query, {'$set': change}, session=session)
    if updated.modified_count != 1:
        raise OperatorStop('Account/budget CAS changed; no retry')
    return {'status': action.upper(), 'test_id': TEST_ID,
            'consumed_seconds': record['consumed_seconds'], 'maximum_seconds': MAXIMUM,
            'expires_at': record['expires_at'], 'account_blocked': action == 'rollback-guard'}


async def execute(server, args):
    verify_runtime(server, args.expected_revision, mutation=args.action not in ('preflight', 'status'))
    if args.action == 'preflight':
        return await baseline_startup_noop(server)
    if args.action == 'status':
        return await budget_operation(server, action='status', user_id=args.user_id)
    # Re-establish baseline safety before enable or the conditional rollback
    # guard. No indexes or publication state are installed by this caller.
    if args.action in ('enable', 'rollback-guard'):
        await baseline_startup_noop(server)
    mongo_session = await server.client.start_session()
    async with mongo_session:
        mongo_session.start_transaction()
        try:
            result = await budget_operation(server, action=args.action, user_id=args.user_id,
                expected_consumed=args.expected_consumed, session=mongo_session)
        except Exception:
            await mongo_session.abort_transaction()
            raise
        try:
            await mongo_session.commit_transaction()  # ONCE, no automatic retry
        except Exception as exc:
            raise CommitOutcomeUnknown('COMMIT_OUTCOME_UNKNOWN; use status read; do not repeat mutation') from exc
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', required=True, choices=['preflight', 'status', 'enable', 'disable', 'rollback-guard'])
    parser.add_argument('--expected-revision', required=True)
    parser.add_argument('--user-id', default='')
    parser.add_argument('--expected-consumed', type=int)
    parser.add_argument('--via-railway', action='store_true')
    parser.add_argument('--identity-file')
    args = parser.parse_args()
    if args.via_railway:
        if not args.identity_file:
            parser.error('Explicit already-authorized identity file required; no personal SSH scan or key creation')
        forwarded = ['--action', args.action, '--expected-revision', args.expected_revision]
        if args.user_id: forwarded += ['--user-id', args.user_id]
        if args.expected_consumed is not None: forwarded += ['--expected-consumed', str(args.expected_consumed)]
        encoded = base64.b64encode(Path(__file__).read_bytes()).decode('ascii')
        remote = shlex.join(['python', '-c', f"import base64;exec(compile(base64.b64decode('{encoded}'),'<reviewed-acceptance-operator>','exec'))", *forwarded])
        try:
            return subprocess.run(['railway', 'ssh', '--project', PROJECT, '--environment', ENVIRONMENT,
                '--service', SERVICE, '--identity-file', args.identity_file, remote], check=False, timeout=60).returncode
        except subprocess.TimeoutExpired:
            print(json.dumps({'status': 'REMOTE_OUTCOME_UNKNOWN', 'next': 'Scoped status read; no mutation retry'}))
            return 42
    try:
        try:
            import server
        except ImportError:
            from backend import server
        result = asyncio.run(execute(server, args))
        print(json.dumps(result, default=lambda x: x.isoformat() if isinstance(x, datetime) else str(x)))
        return 0
    except CommitOutcomeUnknown:
        print(json.dumps({'status': 'COMMIT_OUTCOME_UNKNOWN', 'next': 'Scoped status read only; do not repeat mutation'}))
        return 42
    except Exception:
        # Never print exception text/trace containing connection strings or
        # private runtime state. Unknown commit is preserved as an explicit state.
        print(json.dumps({'status': 'STOP_OR_UNKNOWN', 'next': 'Inspect scoped status/preflight; no mutation retry'}))
        return 42


if __name__ == '__main__':
    sys.exit(main())
