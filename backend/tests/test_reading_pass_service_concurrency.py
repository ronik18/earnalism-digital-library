import asyncio
import copy
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.domain.reading_pass import ReadingPassConfig
from backend.reading_pass_service import ReadingPassService


def _get(document, path):
    value = document
    for part in path.split('.'):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _matches(document, query):
    for key, expected in query.items():
        actual = _get(document, key)
        if isinstance(expected, dict):
            if '$in' in expected and actual not in expected['$in']:
                return False
            if '$ne' in expected and actual == expected['$ne']:
                return False
            if '$gte' in expected and not (actual is not None and actual >= expected['$gte']):
                return False
        elif actual != expected:
            return False
    return True


def _set(document, path, value):
    target = document
    parts = path.split('.')
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = copy.deepcopy(value)


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, *_args):
        return self

    async def to_list(self, _limit):
        return copy.deepcopy(self.rows)


class Collection:
    def __init__(self, rows=None):
        self.rows = copy.deepcopy(rows or [])

    async def find_one(self, query, projection=None, **_kwargs):
        row = next((row for row in self.rows if _matches(row, query)), None)
        return copy.deepcopy(row) if row else None

    async def insert_one(self, document, **_kwargs):
        if 'idempotency_key' in document and any(
            row.get('session_id') == document.get('session_id')
            and row.get('idempotency_key') == document.get('idempotency_key')
            for row in self.rows
        ):
            raise AssertionError('duplicate idempotency row')
        self.rows.append(copy.deepcopy(document))
        return SimpleNamespace(inserted_id=document.get('id'))

    async def update_one(self, query, update, upsert=False, **_kwargs):
        row = next((row for row in self.rows if _matches(row, query)), None)
        if row is None and upsert:
            row = {key: copy.deepcopy(value) for key, value in query.items() if not isinstance(value, dict)}
            self.rows.append(row)
        if row is None:
            return SimpleNamespace(modified_count=0, matched_count=0, upserted_id=None)
        changed = False
        for key, value in update.get('$set', {}).items():
            if _get(row, key) != value:
                _set(row, key, value)
                changed = True
        for key, value in update.get('$setOnInsert', {}).items():
            if _get(row, key) is None:
                _set(row, key, value)
                changed = True
        for key, value in update.get('$inc', {}).items():
            _set(row, key, int(_get(row, key) or 0) + int(value))
            changed = True
        for key in update.get('$unset', {}):
            if key in row:
                row.pop(key, None)
                changed = True
        return SimpleNamespace(modified_count=int(changed), matched_count=1, upserted_id=row.get('id') if upsert else None)

    async def update_many(self, query, update, **kwargs):
        modified = 0
        for row in list(self.rows):
            if _matches(row, query):
                result = await self.update_one({'id': row.get('id')}, update, **kwargs)
                modified += result.modified_count
        return SimpleNamespace(modified_count=modified)

    def find(self, query, projection=None, **_kwargs):
        return Cursor([row for row in self.rows if _matches(row, query)])


class Database:
    def __init__(self, balance=120):
        self.users = Collection([{
            'id': 'user-1', 'role': 'user', 'status': 'active',
            'reading_seconds_balance': balance, 'wallet_seconds': balance,
            'active_user_session_id': 'auth-1',
        }])
        for name in (
            'reading_pass_sessions', 'reading_pass_devices', 'reading_pass_audit',
            'reading_pass_heartbeats', 'reading_pass_positions', 'wallet_transactions',
            'wallet_ledger', 'topup_intents', 'user_sessions',
        ):
            setattr(self, name, Collection())


class Transaction:
    def __init__(self, lock):
        self.lock = lock

    async def __aenter__(self):
        await self.lock.acquire()
        return self

    async def __aexit__(self, *_args):
        self.lock.release()


class Session:
    def __init__(self, lock):
        self.lock = lock

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def start_transaction(self):
        return Transaction(self.lock)


class Client:
    def __init__(self):
        self.lock = asyncio.Lock()

    async def start_session(self):
        return Session(self.lock)


class LabeledTransactionError(Exception):
    def __init__(self, label):
        super().__init__(label)
        self.label = label

    def has_error_label(self, label):
        return label == self.label


class ExplicitCommitSession:
    def __init__(self):
        self.in_transaction = False
        self.commit_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def start_transaction(self):
        self.in_transaction = True

    async def abort_transaction(self):
        self.in_transaction = False

    async def commit_transaction(self):
        self.commit_calls += 1
        if self.commit_calls == 1:
            raise LabeledTransactionError('UnknownTransactionCommitResult')
        self.in_transaction = False


class ExplicitCommitClient:
    def __init__(self):
        self.session = ExplicitCommitSession()

    async def start_session(self):
        return self.session


async def _start(service):
    return await service.start_session(
        user_id='user-1', auth_session_id='auth-1', device_id='device-0001',
        device_label='Fixture', content_type='text', content_id='book-1',
        scope={'canonical_page_index': 4},
    )


def test_unknown_commit_retries_commit_without_replaying_balance_operation():
    async def scenario():
        database = Database(balance=120)
        client = ExplicitCommitClient()
        service = ReadingPassService(db=database, client=client, config=ReadingPassConfig(), token_secret='secret')
        operation_calls = 0

        async def operation(_session):
            nonlocal operation_calls
            operation_calls += 1
            return {'ok': True}

        result = await service._transaction(operation)
        assert result == {'ok': True}
        assert operation_calls == 1
        assert client.session.commit_calls == 2

    asyncio.run(scenario())


def test_one_hundred_simultaneous_renewals_debit_once(monkeypatch):
    async def scenario():
        database = Database(balance=120)
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        started = await _start(service)
        session = database.reading_pass_sessions.rows[0]
        session['last_billed_at'] = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session['lease_expires_at'] = datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc)

        monkeypatch.setattr('backend.reading_pass_service.datetime', FrozenDateTime)
        results = await asyncio.gather(*[
            service.renew_lease(
                user_id='user-1', auth_session_id='auth-1', session_id=started['session_id'],
                lease_token=started['lease_token'], lease_version=1, sequence=1,
                idempotency_key=f'renew-{index:03d}', active=True,
            )
            for index in range(100)
        ])
        user = database.users.rows[0]
        assert user['reading_seconds_balance'] == 110
        assert len(database.wallet_ledger.rows) == 1
        assert sum(row['deducted_seconds'] for row in results) == 10
        assert user['reading_seconds_balance'] >= 0

    asyncio.run(scenario())


def test_ten_duplicate_payment_callbacks_create_one_credit():
    async def scenario():
        database = Database(balance=0)
        intent = {
            'id': 'intent-1', 'user_id': 'user-1', 'minutes': 30,
            'pack_id': '30m', 'status': 'created',
        }
        database.topup_intents.rows.append(copy.deepcopy(intent))
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        await asyncio.gather(*[
            service.credit_verified_payment(intent=intent, payment_id='pay-1', source='webhook')
            for _ in range(10)
        ])
        assert database.users.rows[0]['reading_seconds_balance'] == 1800
        assert len(database.wallet_ledger.rows) == 1
        assert database.wallet_ledger.rows[0]['event_type'] == 'PASS_CREDIT'

    asyncio.run(scenario())


def test_active_lock_is_released_when_session_ends():
    async def scenario():
        database = Database(balance=120)
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        started = await _start(service)
        assert database.reading_pass_sessions.rows[0]['active_lock'] == 'user-1'
        ended = await service.end_session(
            user_id='user-1', auth_session_id='auth-1', session_id=started['session_id']
        )
        assert ended['ended'] is True
        assert 'active_lock' not in database.reading_pass_sessions.rows[0]

    asyncio.run(scenario())


def test_end_session_settles_final_server_timed_interval(monkeypatch):
    async def scenario():
        database = Database(balance=120)
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        started = await _start(service)
        session = database.reading_pass_sessions.rows[0]
        session['last_billed_at'] = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session['lease_expires_at'] = datetime(2026, 1, 1, 0, 0, 20, tzinfo=timezone.utc)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 1, 0, 0, 7, tzinfo=timezone.utc)

        monkeypatch.setattr('backend.reading_pass_service.datetime', FrozenDateTime)
        ended = await service.end_session(
            user_id='user-1', auth_session_id='auth-1', session_id=started['session_id']
        )
        assert ended['deducted_seconds'] == 7
        assert ended['balance_seconds'] == 113
        assert database.users.rows[0]['reading_seconds_balance'] == 113
        assert database.wallet_ledger.rows[-1]['idempotency_key'].endswith(':ended')

    asyncio.run(scenario())


def test_transfer_settles_old_session_before_issuing_new_lease(monkeypatch):
    async def scenario():
        database = Database(balance=120)
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        await _start(service)
        old = database.reading_pass_sessions.rows[0]
        old['last_billed_at'] = datetime(2026, 1, 1, tzinfo=timezone.utc)
        old['lease_expires_at'] = datetime(2026, 1, 1, 0, 0, 20, tzinfo=timezone.utc)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 1, 0, 0, 6, tzinfo=timezone.utc)

        monkeypatch.setattr('backend.reading_pass_service.datetime', FrozenDateTime)
        replacement = await service.start_session(
            user_id='user-1', auth_session_id='auth-2', device_id='device-0002',
            device_label='Replacement', content_type='text', content_id='book-1',
            scope={'canonical_page_index': 4}, transfer=True,
        )
        assert old['status'] == 'transferred'
        assert old['seconds_consumed'] == 6
        assert database.users.rows[0]['reading_seconds_balance'] == 114
        assert replacement['balance_seconds'] == 114

    asyncio.run(scenario())


def test_expired_session_is_settled_and_does_not_block_new_start(monkeypatch):
    async def scenario():
        database = Database(balance=120)
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        await _start(service)
        old = database.reading_pass_sessions.rows[0]
        old['last_billed_at'] = datetime(2026, 1, 1, tzinfo=timezone.utc)
        old['lease_expires_at'] = datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 1, 0, 0, 30, tzinfo=timezone.utc)

        monkeypatch.setattr('backend.reading_pass_service.datetime', FrozenDateTime)
        replacement = await service.start_session(
            user_id='user-1', auth_session_id='auth-2', device_id='device-0002',
            device_label='Replacement', content_type='text', content_id='book-1',
            scope={'canonical_page_index': 4},
        )
        assert old['status'] == 'expired'
        assert old['seconds_consumed'] == 10
        assert database.users.rows[0]['reading_seconds_balance'] == 110
        assert replacement['balance_seconds'] == 110

    asyncio.run(scenario())


def test_media_cookie_credential_is_bound_to_active_login_and_exact_content():
    async def scenario():
        database = Database(balance=120)
        now = datetime.now(timezone.utc)
        database.user_sessions.rows.append({
            'id': 'auth-1', 'user_id': 'user-1', 'status': 'active',
            'idle_expires_at': datetime(2099, 1, 1, tzinfo=timezone.utc),
            'absolute_expires_at': datetime(2099, 1, 1, tzinfo=timezone.utc),
            'created_at': now,
        })
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        started = await service.start_session(
            user_id='user-1', auth_session_id='auth-1', device_id='device-0001',
            device_label='Fixture', content_type='audio', content_id='book-1',
            scope={'media_position_seconds': 180},
        )
        authorized = await service.authorize_media_credential(
            session_id=started['session_id'], lease_token=started['lease_token'],
            content_type='audio', content_id='book-1',
        )
        assert authorized['user_id'] == 'user-1'

    asyncio.run(scenario())


def test_device_revoke_settles_active_interval_atomically(monkeypatch):
    async def scenario():
        database = Database(balance=120)
        database.user_sessions.rows.append({
            'id': 'auth-1', 'user_id': 'user-1', 'status': 'active',
        })
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        await _start(service)
        session = database.reading_pass_sessions.rows[0]
        session['last_billed_at'] = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session['lease_expires_at'] = datetime(2026, 1, 1, 0, 0, 20, tzinfo=timezone.utc)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)

        monkeypatch.setattr('backend.reading_pass_service.datetime', FrozenDateTime)
        revoked = await service.revoke_auth_session(user_id='user-1', auth_session_id='auth-1')
        assert revoked['deducted_seconds'] == 5
        assert database.users.rows[0]['reading_seconds_balance'] == 115
        assert database.reading_pass_sessions.rows[0]['status'] == 'revoked'
        assert database.user_sessions.rows[0]['status'] == 'revoked'

    asyncio.run(scenario())


def test_pause_heartbeat_settles_the_preceding_active_interval(monkeypatch):
    async def scenario():
        database = Database(balance=120)
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        started = await _start(service)
        session = database.reading_pass_sessions.rows[0]
        session['last_billed_at'] = datetime(2026, 1, 1, tzinfo=timezone.utc)
        session['lease_expires_at'] = datetime(2026, 1, 1, 0, 0, 20, tzinfo=timezone.utc)

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc)

        monkeypatch.setattr('backend.reading_pass_service.datetime', FrozenDateTime)
        renewed = await service.renew_lease(
            user_id='user-1', auth_session_id='auth-1', session_id=started['session_id'],
            lease_token=started['lease_token'], lease_version=1, sequence=1,
            idempotency_key='pause-1', active=False,
        )
        assert renewed['deducted_seconds'] == 10
        assert renewed['status'] == 'Paused'
        assert database.users.rows[0]['reading_seconds_balance'] == 110
        assert 'active_lock' in database.reading_pass_sessions.rows[0]

    asyncio.run(scenario())


def test_position_sync_whitelists_shape_and_rejects_invalid_values():
    async def scenario():
        database = Database(balance=120)
        service = ReadingPassService(db=database, client=Client(), config=ReadingPassConfig(), token_secret='secret')
        text = await service.save_position(
            user_id='user-1', content_type='text', content_id='book-1',
            position={'canonical_page_index': 4, 'chapter_id': 'chapter-2', 'access': 'forged'},
            version=0,
        )
        assert text['position'] == {'canonical_page_index': 4, 'chapter_id': 'chapter-2'}
        audio = await service.save_position(
            user_id='user-1', content_type='audio', content_id='book-1',
            position={'media_position_seconds': 181.23456, 'lease': 'forged'},
            version=0,
        )
        assert audio['position'] == {'media_position_seconds': 181.235}

    asyncio.run(scenario())
