"""Default-local, exact Selfish metadata operator. Never run by application startup.

No-argument/check-local mode reads no environment, credentials or database. Runtime
modes require an externally pinned actual authority packet, exact private connection
profile and an existing qualified metadata namespace. No normal session settlement,
wallet/carry/user-cap changes, key setup or production playback is performed here.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

from . import native_audio_review_authority as proof


def local_source_sha256():
    root = Path(__file__).parent
    names = ('native_audio_review_authority.py', 'native_audio_review_operator.py',
             'native_audio_review_operator_cli.py', 'native_audio_review_scope.py',
             'native_audiobook_replacement.py', 'reading_pass_service.py', 'server.py')
    return proof.digest([{ 'path': n, 'sha256': hashlib.sha256((root / n).read_bytes()).hexdigest()} for n in names])


def seal(directory, name, value):
    directory = Path(directory)
    st = directory.lstat()
    proof.need(stat.S_ISDIR(st.st_mode) and not directory.is_symlink() and st.st_uid == os.getuid()
               and stat.S_IMODE(st.st_mode) == 0o700, 'PRIVATE_EXISTING_JOURNAL_DIRECTORY_REQUIRED')
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        # Never unlink a possibly written pre-call intent or overwrite a result.
        raise proof.AdmissionStop('PRIVATE_JOURNAL_OUTCOME_UNKNOWN_NO_REPLAY') from None


async def runtime(a, bundle, receipts):
    # These imports/connection-file reads occur ONLY under an explicit runtime
    # mode, after real externally hash-pinned evidence has been parsed locally.
    from motor.motor_asyncio import AsyncIOMotorClient
    from . import native_audio_review_operator as operator
    from .catalog_truth import load_controlled_artifact_book
    execution = receipts['execution']
    proof.need(a.journal is not None and str(a.journal)==bundle['journal']['path'], 'RUNTIME_JOURNAL_NOT_APPROVED')
    proof.qualify_journal(bundle['journal'])
    proof.need(a.mongo_profile and a.database and a.journal, 'EXPLICIT_RUNTIME_INPUTS_REQUIRED')
    proof.need(proof.identity_hash(a.database) == execution.get('database_name_sha256'), 'DATABASE_TARGET_NOT_APPROVED')
    profile = proof.private_json(a.mongo_profile, execution.get('mongo_profile_sha256'))
    proof.need(set(profile) == {'uri'} and isinstance(profile['uri'], str)
               and profile['uri'].startswith(('mongodb://', 'mongodb+srv://')), 'PRIVATE_MONGO_PROFILE_REQUIRED')
    client = AsyncIOMotorClient(profile['uri'], retryWrites=False, retryReads=False, tz_aware=True,
                               serverSelectionTimeoutMS=5000, connectTimeoutMS=5000,
                               socketTimeoutMS=10000, maxPoolSize=2)
    try:
        db = client[a.database]
        admitted = operator.admit_authority(a.authority, a.authority_sha256,
            now=datetime.now(timezone.utc), allow_expired=a.status)
        if a.status:
            if admitted.action=='prepare-namespace':
                await operator.member(db,admitted,require_no_user_cap=False,require_current_auth=False)
                return await operator.namespace_status(db)
            return await operator.status(db, client, admitted)
        proof.need(a.execute or a.prepare_namespace, 'EXPLICIT_EXECUTE_REQUIRED')
        proof.need((admitted.action=='prepare-namespace') is a.prepare_namespace, 'RUNTIME_ACTION_MISMATCH')
        book = load_controlled_artifact_book('the-selfish-giant', include_content=False)
        proof.need(isinstance(book, dict), 'QUALIFIED_CONTROLLED_BOOK_REQUIRED')
        # The exclusive durable marker survives ANY failure. A second --execute
        # for the same operation is denied even if no DB result can be observed.
        seal(a.journal, admitted.operation_id + '.attempt.json', {
            'schema': 'earnalism.native_audio_review_runtime_attempt.v1',
            'operation_id': admitted.operation_id, 'authority_sha256': a.authority_sha256,
            'action': admitted.action, 'status': 'INTENT_DURABLE_OUTCOME_NOT_YET_KNOWN',
            'started_at': datetime.now(timezone.utc).isoformat()})
        if a.prepare_namespace:
            result=await operator.prepare_namespace_one_shot(db=db,client=client,admitted=admitted,book=book)
        else:
            result = await operator.execute_one_shot(db=db, client=client, admitted=admitted, book=book)
        seal(a.journal, admitted.operation_id + '.result.json', result)
        return result
    finally:
        client.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--check-local', action='store_true')
    modes.add_argument('--status', action='store_true')
    modes.add_argument('--execute', action='store_true')
    modes.add_argument('--prepare-namespace', action='store_true')
    p.add_argument('--authority', type=Path)
    p.add_argument('--authority-sha256')
    p.add_argument('--mongo-profile', type=Path)
    p.add_argument('--database')
    p.add_argument('--journal', type=Path)
    a = p.parse_args(argv)
    try:
        if not a.authority:
            proof.need(not a.execute and not a.prepare_namespace and not a.status, 'REAL_AUTHORITY_REQUIRED')
            print(json.dumps({'status': 'LOCAL_ONLY_REAL_AUTHORITY_AND_LEGACY_DATA_REQUIRED',
                              'actual_remaining_seconds': None, 'database_access': False}))
            return 2
        bundle, receipts = proof.parse_authority(a.authority, a.authority_sha256,
            now=datetime.now(timezone.utc), allow_expired=a.status)
        if a.execute or a.prepare_namespace or a.status:
            proof.need(a.journal is not None and str(a.journal)==bundle['journal']['path'], 'RUNTIME_JOURNAL_NOT_APPROVED')
        proof.need(receipts['source']['source_files_sha256'] == local_source_sha256(), 'LOCAL_SOURCE_DIFFERS_FROM_APPROVED_SERVING_SOURCE')
        if not a.execute and not a.prepare_namespace and not a.status:
            print(json.dumps({'status': 'LOCAL_RECEIPTS_PARSED_CURRENT_DB_AND_HISTORY_UNVERIFIED',
                              'authority_sha256': a.authority_sha256,
                              'actual_remaining_seconds': None, 'database_access': False}))
            return 0
        result = asyncio.run(asyncio.wait_for(runtime(a, bundle, receipts), timeout=50))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (proof.AdmissionStop, FileExistsError) as error:
        code = str(error) if isinstance(error, proof.AdmissionStop) else 'DURABLE_ATTEMPT_EXISTS_STATUS_ONLY_NO_REPLAY'
        print(json.dumps({'status': 'HOLD', 'code': code, 'actual_remaining_seconds': None, 'replay_permitted': False}))
        return 2
    except Exception:
        # Includes Mongo/URI/credential/JSON/runtime timeout details; never print
        # raw exception text, tracebacks, source receipt bodies or identities.
        print(json.dumps({'status': 'HOLD', 'code': 'VALIDATION_OR_RUNTIME_OUTCOME_UNVERIFIED_STATUS_ONLY_NO_REPLAY',
                          'actual_remaining_seconds': None, 'replay_permitted': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
