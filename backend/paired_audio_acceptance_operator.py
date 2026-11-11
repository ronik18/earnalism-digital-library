"""One-shot controller operation; importing this module performs no I/O.

No CLI, HTTP route, client factory, capture, deployment, balance write, metadata
repair, retirement or retry is provided. The existing protected controller must
supply its already-admitted server and exact qualified source bindings.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import re

from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
try:
    from . import paired_audio_acceptance_budget as policy
    from .domain.reading_pass import ensure_utc
except ImportError:
    import paired_audio_acceptance_budget as policy
    from domain.reading_pass import ensure_utc

PROJECT = 'a8533934-35c4-463e-9f43-577a9ac391ee'
ENVIRONMENT = '580b250c-80ee-48ad-bfbe-fa4e31a6b378'
SERVICE = '5af42e7e-f518-4f6a-b602-d9950866501f'
RECEIPTS = 'paired_audio_acceptance_installations'
SOURCE_FILES = ('server.py', 'reading_pass_service.py',
                'paired_audio_acceptance_budget.py', 'paired_audio_acceptance_operator.py')
MARKER = 'paired_audio_acceptance_installation'


class InstallationHold(ValueError):
    pass


class CommitOutcomeUnknown(InstallationHold):
    pass


def need(condition, message):
    if not condition:
        raise InstallationHold(message)


def verify_runtime(server, *, expected_revision, expected_files):
    """Expected values must come from the controller's qualified candidate."""
    need(isinstance(expected_revision, str) and re.fullmatch('[a-f0-9]{40}', expected_revision),
         'Exact qualified merged revision required')
    expected = dict(RAILWAY_PROJECT_ID=PROJECT, RAILWAY_ENVIRONMENT_ID=ENVIRONMENT,
                    RAILWAY_SERVICE_ID=SERVICE, RAILWAY_GIT_COMMIT_SHA=expected_revision)
    need(all(os.environ.get(k) == v for k, v in expected.items()), 'Serving source/provider mismatch')
    need(server.ENVIRONMENT == 'production' and server.READING_PASS_V2_ENABLED is True,
         'Production ReadingPass context required')
    root = Path(__file__).resolve().parent
    need(Path(server.__file__).resolve() == root/'server.py', 'Existing controller server required')
    need(isinstance(expected_files, dict) and set(expected_files) == set(SOURCE_FILES),
         'Complete qualified runtime source bindings required')
    need(all(isinstance(h, str) and re.fullmatch('[a-f0-9]{64}', h)
             and sha256((root/name).read_bytes()).hexdigest() == h
             for name, h in expected_files.items()), 'Runtime artifact mismatch')


async def install_in_transaction(server, *, user_id, auth_session_id, now,
                                 expected_revision, expected_files, session):
    """Called only by install(); writes the new cap/receipt, never old evidence."""
    need(session is not None and session.in_transaction, 'Existing controller transaction required')
    budget = policy.build_budget(user_id, now, auth_session_id=auth_session_id)
    db = server.db
    need(not await db[RECEIPTS].find_one({'_id': policy.APPROVAL_ID}, session=session),
         'Approval already retained; no second installation')
    user = await db.users.find_one({'id': user_id, 'role': 'user'},
        {'id': 1, 'status': 1, 'reader_acceptance_budget': 1, MARKER: 1,
         'active_reading_session': 1, 'active_user_session_id': 1}, session=session)
    need(user and user.get('status') == 'active' and 'reader_acceptance_budget' not in user
         and MARKER not in user and not user.get('active_reading_session')
         and user.get('active_user_session_id') == auth_session_id,
         'Missing member, conflicting cap/receipt or authentication changed')
    auth = await db.user_sessions.find_one({'id': auth_session_id, 'user_id': user_id},
        {'status': 1, 'idle_expires_at': 1, 'absolute_expires_at': 1}, session=session)
    need(auth and auth.get('status') == 'active'
         and all(isinstance(auth.get(k), datetime) and ensure_utc(auth[k]) > now
                 for k in ('idle_expires_at', 'absolute_expires_at')),
         'Current authenticated member session required')
    need(not await db.reading_pass_sessions.find_one(
        {'user_id': user_id, 'status': {'$in': ['active', 'paused']}}, session=session),
        'Unsettled session exists; no automatic cleanup')
    need(not await db.reading_pass_sessions.find_one(
        {'user_id': user_id, 'acceptance_test_id': policy.TEST_ID}, session=session),
        'Attempt already retained; no restart')
    for collection in ('native_audio_review_grants', 'sredni_initial_review_grants'):
        need(not await db[collection].find_one({'user_id': user_id, 'state': 'OPEN'}, session=session),
             'Conflicting native grant; preserve it unchanged')
    # Pure existing release validation, no network call or release selection write.
    need(server._is_controlled_public_slug(policy.SLUG), 'Controlled public title required')
    artifact = server._controlled_artifact_doc(policy.SLUG, include_content=False)
    if artifact and server._can_expose_audiobook_package_canary(artifact, policy.SLUG):
        book = artifact
    else:
        book = await db.books.find_one(
            server._controlled_public_book_query({'slug': policy.SLUG}),
            server._READER_AUDIO_BOOK_PROJECTION, session=session)
        book = server._reader_audio_truth_doc(book, policy.SLUG)
        need(book and server.can_expose_audio({**book, 'slug': policy.SLUG}),
             'Exact released book unavailable')
    package = server._validated_audiobook_package(book, policy.SLUG,
        raw_package=server._book_audiobook_release_packages(book).get(policy.DESCRIPTOR),
        expected_release_descriptor_sha256=policy.DESCRIPTOR)
    need(policy.package_scope(policy.SLUG, package)
         and server._has_release_eligible_audiobook_package_evidence(
             book, policy.SLUG, policy.DESCRIPTOR, package), 'Released package evidence changed')
    receipt = dict(_id=policy.APPROVAL_ID, user_id=user_id, auth_session_id=auth_session_id,
        test_id=policy.TEST_ID, schema='paired-audio-acceptance-installation.v1',
        source_revision=expected_revision, source_files=dict(expected_files),
        created_at=now, maximum_seconds=40, maximum_sessions=1,
        capture_claims_added=0, status='INSTALLED')
    # Built-in Mongo _id uniqueness is the durable one-shot fence. No upsert.
    await db[RECEIPTS].insert_one(receipt, session=session)
    result = await db.users.update_one(
        {'id': user_id, 'role': 'user', 'status': 'active',
         'active_user_session_id': auth_session_id,
         'reader_acceptance_budget': {'$exists': False}, MARKER: {'$exists': False}},
        {'$set': {'reader_acceptance_budget': budget, MARKER: policy.APPROVAL_ID}}, session=session)
    need(result.modified_count == 1, 'Installation CAS changed; abort without retry')
    return dict(status='INSTALLED', approval_id=policy.APPROVAL_ID,
                source_revision=expected_revision, maximum_seconds=40,
                maximum_sessions=1, expires_at=budget['expires_at'])


async def install(server, *, user_id, auth_session_id, expected_revision, expected_files):
    """ONE transaction and ONE commit attempt; never replay an unknown outcome."""
    verify_runtime(server, expected_revision=expected_revision, expected_files=expected_files)
    expected_files = dict(expected_files)
    now = datetime.now(timezone.utc)
    session = await server.client.start_session()
    async with session:
        session.start_transaction(read_concern=ReadConcern('snapshot'),
                                  write_concern=WriteConcern('majority'))
        try:
            result = await install_in_transaction(server, user_id=user_id,
                auth_session_id=auth_session_id, now=now, expected_revision=expected_revision,
                expected_files=expected_files, session=session)
        except BaseException:
            await session.abort_transaction()
            raise
        try:
            await session.commit_transaction()
        except BaseException as exc:
            raise CommitOutcomeUnknown('Outcome unknown: HOLD, reconcile existing evidence; do not reinstall') from exc
    return result
