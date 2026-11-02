"""Private exact-scope admission and complete server-record legacy reconciliation.

Pure/local validation does not confer approval. The operator supplies an externally
reviewed expected authority-file hash; referenced original owner, independent member,
execution and serving-source receipts must be actual observations, never generated
by this module. No network, credentials, account writes or positive default budget.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = 'earnalism.native_audio_review_authority.v1'
ORIGINAL_OWNER_RECEIPT_SHA256 = '5826f4bc1272a7e4f0d882990b81f704598fb37ed9536eb374091b991af6fd1d'
ORIGINAL_QUESTION_ID = 'call_d2bb41f54c2347a1a6a6f9bf12c8f314'
ORIGINAL_QUESTION = ('Please sign in privately at the Earnalism login page opened in Chrome, using your intended existing member account with Reading Pass credit. Then confirm that this is the account for the prepared Selfish Giant check: about 31 active audio seconds, capped at 120 seconds of existing credit, no purchases. I’ll wait for the other release to finish before testing. Do not send credentials in chat.')
ORIGINAL_ANSWER = 'Signed in—use this account for the bounded check'
HISTORICAL_SOURCE = '47c9eba3b121bbbbf7d21974dee6e70937f0d75912f2a0946efb267f93be8195'
HISTORICAL_RUNTIME = '28f3da2e95f9bb7c010fbb705bd463f69682161296fa6a2d2c28b2d1678a6b00'
SHA = re.compile(r'^[0-9a-f]{64}$')
# Conservative window begins at the retained prepared sign-in handoff, before
# the owner confirmed that intended account. Callers cannot move it past usage.
ORIGINAL_WINDOW_START = datetime(2026, 10, 31, 18, 49, 58, 42193, tzinfo=timezone.utc)
MAX_ROWS = 1000
class AdmissionStop(ValueError):
    """Code-only errors: never print input, identities, database errors or secrets."""


def need(value, code):
    if not value:
        raise AdmissionStop(code)


def utc(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise AdmissionStop('INVALID_UTC_TIME') from None
        need(value.tzinfo is not None, 'EXPLICIT_UTC_TIME_REQUIRED')
    need(isinstance(value, datetime), 'SERVER_TIME_REQUIRED')
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def normalized(value):
    if isinstance(value, datetime):
        return {'utc': utc(value).isoformat()}
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(normalized(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def identity_hash(value):
    need(isinstance(value, str) and 1 <= len(value) <= 256, 'PRIVATE_IDENTITY_REQUIRED')
    return hashlib.sha256(value.encode()).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'DUPLICATE_JSON_FIELD')
        result[key] = value
    return result


def private_json(path, expected_sha256):
    """Read a bounded owner-only regular file without following final symlinks."""
    need(isinstance(expected_sha256, str) and SHA.fullmatch(expected_sha256), 'EXPECTED_FILE_HASH_REQUIRED')
    fd = os.open(Path(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
             and stat.S_IMODE(before.st_mode) == 0o600 and 0 < before.st_size <= 1024 * 1024,
             'PRIVATE_0600_REGULAR_FILE_REQUIRED')
        raw = b''
        while len(raw) <= 1024 * 1024:
            block = os.read(fd, 65536)
            if not block:
                break
            raw += block
        after = os.fstat(fd)
        need((before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns)
             and len(raw) == before.st_size and hashlib.sha256(raw).hexdigest() == expected_sha256,
             'PRIVATE_EVIDENCE_HASH_CHANGED')
        result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(AdmissionStop('NONFINITE_JSON')))
        need(isinstance(result, dict), 'EVIDENCE_OBJECT_REQUIRED')
        return result
    finally:
        os.close(fd)


def qualify_original_owner(owner,expected_sha256):
    # Exact direct human reply; the prepared sign-in UI receipt is not approval.
    need(expected_sha256 == ORIGINAL_OWNER_RECEIPT_SHA256
         and owner.get('schema') == 'earnalism.owner_original120_verbatim_reply.v1'
         and owner.get('question_id') == ORIGINAL_QUESTION_ID
         and owner.get('question') == ORIGINAL_QUESTION and owner.get('answer') == ORIGINAL_ANSWER
         and owner.get('maximum_cumulative_existing_credit_seconds') == 120
         and owner.get('new_credit_or_purchase_authority') is False
         and owner.get('remaining_allowance') is None, 'ORIGINAL_OWNER_REPLY_REQUIRED')
    return True


def qualify_journal(ref):
    need(isinstance(ref,dict) and set(ref)=={'path','device','inode'},'BOUND_PRIVATE_JOURNAL_REQUIRED')
    path=Path(ref['path'])
    need(path.is_absolute() and path.resolve(strict=True)==path,'EXACT_PRIVATE_JOURNAL_PATH_REQUIRED')
    info=path.lstat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700
         and type(ref['device']) is int and type(ref['inode']) is int
         and (info.st_dev,info.st_ino)==(ref['device'],ref['inode']),'PRIVATE_JOURNAL_IDENTITY_CHANGED_NO_REPLAY')
    return path


def parse_authority(path, expected_sha256, *, now, allow_expired=False):
    """Resolve actual hash-bound receipts. Missing/unknown claims always HOLD.

    The expected top-level hash is selected externally after owner/integration
    review, not trusted from inside the file. This parser never manufactures a
    missing approval or an independently observed member binding.
    """
    b = private_json(path, expected_sha256)
    need(b.get('schema') == SCHEMA and b.get('action') in {'provision', 'close', 'prepare-namespace'}, 'EXACT_AUTHORITY_SCHEMA_REQUIRED')
    need(isinstance(b.get('operation_id'), str) and re.fullmatch(r'[A-Za-z0-9_-]{16,128}', b['operation_id']), 'OPERATION_ID_REQUIRED')
    need(b.get('country') == 'IN' and b.get('slug') == 'the-selfish-giant'
         and b.get('descriptor_sha256') == 'd2dbc302427a535e5a3e89dfb82f0b9b880729ea6c56837fd9d9f18ea1077258'
         and b.get('package_version') == 'sha256-288896c0fa472ce2a13c76d022b717805c21a8620b0bdb0662055685bd365fa2', 'EXACT_BOOK_PACKAGE_SCOPE_REQUIRED')
    uh, ah = identity_hash(b.get('user_id')), identity_hash(b.get('auth_session_id'))
    receipts = {}
    for key in ('owner', 'identity', 'execution', 'legacy', 'source', 'intent'):
        ref = b.get(key)
        need(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'HASH_BOUND_RECEIPTS_REQUIRED')
        receipts[key] = private_json(ref['path'], ref['sha256'])
    owner = receipts['owner']
    qualify_original_owner(owner,b['owner']['sha256'])
    now = utc(now)
    expires = utc(b.get('expires_at'))
    need(utc(b.get('created_at')) <= expires and 0 < (expires - utc(b['created_at'])).total_seconds() <= 900,
         'BOUNDED_OPERATION_CLOCK_REQUIRED')
    if not allow_expired:
        need(utc(b['created_at']) <= now < expires, 'AUTHORITY_EXPIRED_OR_FUTURE')
    for key, schema in (('identity', 'earnalism.native_audio_review_member_binding.v1'),
                        ('execution', 'earnalism.native_audio_review_execution.v1')):
        r = receipts[key]
        need(r.get('schema') == schema and r.get('user_id_sha256') == uh
             and r.get('auth_session_id_sha256') == ah and r.get('owner_receipt_sha256') == b['owner']['sha256'],
             'INDEPENDENT_MEMBER_OR_EXECUTION_BINDING_REQUIRED')
        need(0 < (utc(r.get('expires_at')) - utc(r.get('observed_at'))).total_seconds() <= 900, 'RECEIPT_CLOCK_INVALID')
        if not allow_expired:
            need(utc(r['observed_at']) <= now < utc(r['expires_at']) and utc(r['expires_at']) >= expires,
                 'MEMBER_OR_EXECUTION_EVIDENCE_EXPIRED')
    need(receipts['identity'].get('source') == 'OWNER_SELECTED_AUTHENTICATED_NORMAL_MEMBER', 'INDEPENDENT_NORMAL_MEMBER_OBSERVATION_REQUIRED')
    execution = receipts['execution']
    need(execution.get('decision') == 'ACCEPTED_EXACT_SCOPED_METADATA_OPERATION'
         and execution.get('action') == b['action'] and execution.get('operation_id') == b['operation_id']
         and execution.get('original_ceiling_seconds') == 120
         and all(execution.get(k) == b[k] for k in ('slug', 'country', 'descriptor_sha256', 'package_version')),
         'EXACT_EXECUTION_AUTHORITY_REQUIRED')
    source = receipts['source']
    need(source.get('schema') == 'earnalism.native_audio_review_serving_source.v1'
         and source.get('status') == 'QUALIFIED_EXACT_SERVING_SOURCE'
         and all(isinstance(source.get(k), str) and SHA.fullmatch(source[k]) for k in
                 ('runtime_source_sha256', 'source_files_sha256'))
         and isinstance(source.get('merged_main_commit'), str) and re.fullmatch(r'[0-9a-f]{40}', source['merged_main_commit'])
         and all(source.get(k) == b[k] for k in ('slug', 'descriptor_sha256', 'package_version')),
         'EXACT_QUALIFIED_SERVING_SOURCE_REQUIRED')
    need(0 < (utc(source.get('expires_at')) - utc(source.get('observed_at'))).total_seconds() <= 900, 'SERVING_SOURCE_CLOCK_INVALID')
    if not allow_expired:
        need(utc(source['observed_at']) <= now < utc(source['expires_at']) and utc(source['expires_at']) >= expires, 'SERVING_SOURCE_OBSERVATION_EXPIRED')
    legacy = receipts['legacy']
    need(legacy.get('schema') == 'earnalism.native_audio_review_legacy_scope.v1'
         and legacy.get('user_id_sha256') == uh and legacy.get('owner_receipt_sha256') == b['owner']['sha256']
         and legacy.get('historical_metering_source_sha256') == HISTORICAL_SOURCE
         and legacy.get('historical_runtime_source_sha256') == HISTORICAL_RUNTIME,
         'ORIGINAL_LEGACY_SOURCE_SCOPE_REQUIRED')
    ids = legacy.get('original_session_ids')
    need(isinstance(ids, list) and 0 < len(ids) <= MAX_ROWS and len(set(ids)) == len(ids)
         and all(isinstance(i, str) and 1 <= len(i) <= 128 for i in ids), 'COMPLETE_ORIGINAL_SESSION_IDENTIFIERS_REQUIRED')
    need(utc(legacy.get('original_started_at')) == ORIGINAL_WINDOW_START
         and ORIGINAL_WINDOW_START <= utc(legacy.get('observed_at')) <= now,
         'LEGACY_SCOPE_CLOCK_REQUIRED')
    need(isinstance(legacy.get('projection_sha256'), str) and SHA.fullmatch(legacy['projection_sha256']), 'ACTUAL_LEGACY_PROJECTION_REQUIRED')
    qualify_journal(b.get('journal'))
    need(receipts['execution'].get('journal')==b['journal'],'EXECUTION_JOURNAL_BINDING_REQUIRED')
    intent = receipts['intent']
    need(intent.get('schema') == 'earnalism.native_audio_review_intent.v1'
         and intent.get('operation_id') == b['operation_id'] and intent.get('action') == b['action']
         and intent.get('journal')==b['journal']
         and intent.get('execution_receipt_sha256') == b['execution']['sha256']
         and intent.get('expected_state_sha256') == b.get('expected_state_sha256'), 'EXACT_DURABLE_INTENT_REQUIRED')
    need(isinstance(b.get('expected_state_sha256'), str) and SHA.fullmatch(b['expected_state_sha256']), 'EXPECTED_SCOPED_STATE_REQUIRED')
    if b['action'] == 'close':
        need(isinstance(b.get('grant_id'), str) and b['grant_id'].startswith('selfish-'), 'EXACT_CLOSE_GRANT_REQUIRED')
    return b, receipts


def micros(delta):
    return max(0, (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds)


def reconcile_legacy(*, user_id, ids, original_started_at, observed_at, sessions, heartbeats, ledger, transactions):
    """Exact complete server intervals; conservative upper bound, never WPM/credits.

    Coverage is selected by the operator from ALL own unscoped audio starts for
    either title since the original approval, including zero-debit rows. A complete
    heartbeat version chain and genuine immutable terminal settlement are required.
    Last-interval expiry is retained in the last response, not reconstructed from
    the terminal row's overwritten lease expiry. Unknowns HOLD.
    """
    for rows in (sessions, heartbeats, ledger, transactions):
        need(isinstance(rows, list) and len(rows) <= MAX_ROWS, 'LEGACY_HISTORY_NOT_BOUNDED')
    need(set(ids) == {r.get('id') for r in sessions} and len(sessions) == len(ids), 'COMPLETE_ORIGINAL_SESSION_COVERAGE_REQUIRED')
    all_ids = set(ids)
    need(all(r.get('session_id') in all_ids and r.get('user_id') == user_id for rows in (heartbeats, ledger, transactions) for r in rows), 'LEGACY_CROSS_MEMBER_OR_SESSION_RECORD')
    need(len({r.get('id') for r in ledger}) == len(ledger)
         and len({r.get('idempotency_key') for r in ledger}) == len(ledger), 'DUPLICATE_LEGACY_LEDGER')
    linked = {r.get('id'): r for r in transactions}
    need(len(linked) == len(transactions) and set(linked) == {r.get('source_transaction_id') for r in ledger}, 'EXACT_LEGACY_WALLET_LINKS_REQUIRED')
    total_credit = 0
    for row in ledger:
        amount = row.get('debit'); t = linked[row['source_transaction_id']]
        need(type(amount) is int and amount > 0 and row.get('credit') == 0 and row.get('signed_seconds') == -amount
             and row.get('event_type') == 'TIME_DEBIT' and t.get('seconds') == -amount
             and t.get('session_id') == row['session_id'] and t.get('type') == 'consume'
             and t.get('actor') == 'reading-pass-v2', 'LEGACY_FINANCIAL_CHAIN_MISMATCH')
        total_credit += amount
    total_time = 0
    for row in sessions:
        sid = row['id']; created = utc(row.get('created_at')); settled = utc(row.get('settlement_at'))
        need(row.get('user_id') == user_id and row.get('content_type') == 'audio'
             and row.get('content_id') in {'the-selfish-giant', 'the-open-window'}
             and row.get('status') in {'ended', 'expired', 'exhausted', 'transferred', 'revoked'}
             and row.get('billing_active') is False and 'active_lock' not in row
             and utc(original_started_at) <= created <= settled <= utc(observed_at)
             and utc(row.get('last_billed_at')) == settled
             and utc(row.get('lease_expires_at')) == settled,
             'ORIGINAL_SESSION_NOT_IMMUTABLY_SETTLED')
        version = row.get('lease_version')
        need(type(version) is int and 1 <= version <= MAX_ROWS, 'LEGACY_LEASE_VERSION_REQUIRED')
        hb = sorted([r for r in heartbeats if r['session_id'] == sid], key=lambda r: r.get('lease_version', -1))
        need([r.get('lease_version') for r in hb] == list(range(1, version)), 'COMPLETE_ZERO_DEBIT_HEARTBEAT_CHAIN_REQUIRED')
        need(len({r.get('idempotency_key') for r in hb}) == len(hb)
             and len({r.get('sequence') for r in hb}) == len(hb), 'LEGACY_HEARTBEAT_IDEMPOTENCY_REQUIRED')
        debits = {r['idempotency_key']: r['debit'] for r in ledger if r['session_id'] == sid}
        expected_keys = set(); previous = created; expiry = created; billable = False; last_sequence = 0
        for h in hb:
            at = utc(h.get('created_at')); response = h.get('response')
            need(previous <= at <= settled and isinstance(response, dict)
                 and response.get('session_id') == sid and response.get('content_type') == 'audio'
                 and response.get('content_id') == row['content_id'] and response.get('lease_version') == h['lease_version'] + 1
                 and type(h.get('sequence')) is int and h['sequence'] > last_sequence
                 and type(h.get('active')) is bool and isinstance(h.get('playback_state'), str)
                 and response.get('status') in {'Running', 'Connecting', 'Paused', 'Exhausted'}, 'LEGACY_HEARTBEAT_STATE_UNKNOWN')
            if billable:
                total_time += min(micros(min(at, expiry) - previous), 20000000)
            amount = response.get('deducted_seconds')
            need(type(amount) is int and amount >= 0, 'LEGACY_RESPONSE_DEBIT_REQUIRED')
            key = f"heartbeat:{sid}:{h['sequence']}"
            need(debits.get(key, 0) == amount, 'LEGACY_HEARTBEAT_LEDGER_MISMATCH')
            if amount:
                expected_keys.add(key)
            expiry = utc(response.get('lease_expires_at'))
            need(at <= expiry <= at + timedelta(seconds=20), 'LEGACY_LEASE_HORIZON_UNKNOWN')
            billable = h['active'] and h['playback_state'].lower() == 'playing' and response['status'] == 'Running'
            if billable:
                need(type(response.get('balance_seconds')) is int and response['balance_seconds'] > 0, 'LEGACY_RUNNING_BALANCE_UNKNOWN')
            previous, last_sequence = at, h['sequence']
        if billable:
            total_time += min(micros(min(settled, expiry) - previous), 20000000)
        need(utc(row.get('lease_issued_at')) == previous and row.get('last_sequence', 0) == last_sequence, 'FINAL_LEGACY_LEASE_CHAIN_CHANGED')
        terminal = f"terminal:{sid}:{version}:{row['status']}"
        if terminal in debits:
            expected_keys.add(terminal)
        need(set(debits) == expected_keys and type(row.get('seconds_consumed')) is int
             and row['seconds_consumed'] == sum(debits.values()), 'COMPLETE_LEGACY_TERMINAL_LEDGER_REQUIRED')
    need(51 <= total_credit <= 120 and 0 <= total_time <= 120000000, 'ORIGINAL_120_BOUND_EXHAUSTED_OR_USAGE_FLOOR_MISSING')
    projection = dict(sessions=sorted(sessions, key=lambda r: r['id']), heartbeats=sorted(heartbeats, key=lambda r: r['id']),
                      ledger=sorted(ledger, key=lambda r: r['id']), transactions=sorted(transactions, key=lambda r: r['id']))
    return {'lineage_status': 'CONSERVATIVE_PROVEN_BOUND', 'legacy_credit_bound_seconds': total_credit,
            'legacy_time_bound_microseconds': total_time, 'projection_sha256': digest(projection)}
