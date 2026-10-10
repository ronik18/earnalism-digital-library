"""Actual transactions/indexes; explicit disposable loopback replica set only."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend import reading_pass_service as module
from backend.domain.reading_pass import ReadingPassError
from backend.tests.test_reading_pass_text_admission_mongo_integration import _isolated_database, _seed_retained_content
from backend import server

pytestmark = pytest.mark.skipif(
    __import__('os').environ.get('READER_SEGMENT_MONGO_INTEGRATION') != '1',
    reason='requires explicit disposable loopback replica set',
)


class Fixture:
    async def seed(self, db, monkeypatch):
        self.db = db
        self.now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        self.origin = self.now
        monkeypatch.setattr(module, '_now', lambda: self.now)
        self.manifest = await _seed_retained_content(db, 'preparation-fixture')
        await db.users.insert_one({'id': 'fixture-user', 'role': 'user', 'status': 'active', 'reading_seconds_balance': 120, 'wallet_seconds': 120})
        self.service = server.reading_pass_service
        self.lease = await self.service.start_session(user_id='fixture-user', auth_session_id='fixture-auth', device_id='fixture-device', device_label='Disposable', content_type='text', content_id='preparation-fixture',
            scope={'segmentation_version': self.manifest['segmentation_version'], 'manifest_version': self.manifest['version'], 'authority_activation_generation': 1}, prepare_text=True)
        return self

    def at(self, seconds):
        self.now = self.origin + timedelta(seconds=seconds)

    def request(self, phase, version=1, sequence=1, key='fixture-renew-0001'):
        return dict(user_id='fixture-user', auth_session_id='fixture-auth', session_id=self.lease['session_id'], lease_token=self.lease['lease_token'], lease_version=version, sequence=sequence, idempotency_key=key, active=phase == 'readable', text_phase=phase)

    async def document(self):
        return await self.db.reading_pass_sessions.find_one({'id': self.lease['session_id']})

    async def assert_balance(self, debit):
        user = await self.db.users.find_one({'id': 'fixture-user'})
        rows = await self.db.wallet_ledger.find({}).to_list(None)
        assert sum(row['debit'] for row in rows) == debit
        assert user['reading_seconds_balance'] == user['wallet_seconds'] == 120 - debit
        assert len({row['idempotency_key'] for row in rows}) == len(rows)

    async def end(self):
        return await self.service.end_session(user_id='fixture-user', auth_session_id='fixture-auth', session_id=self.lease['session_id'])

    async def revoke(self):
        return await self.service.revoke_text_publication(book_slug='preparation-fixture', expected_activation_generation=1,
            expected_segmentation_version=self.manifest['segmentation_version'], expected_manifest_version=self.manifest['version'],
            operation_id='fixture-revoke-0001', reason='Disposable qualification', actor_id='fixture-admin')


def test_duplicate_overlapping_preparation_and_stale_versions(monkeypatch):
    async def run():
        async with _isolated_database() as db:
            f = await Fixture().seed(db, monkeypatch)
            f.at(10)
            request = f.request('preparing')
            await asyncio.gather(*(f.service.renew_lease(**request) for _ in range(8)), return_exceptions=True)
            # Retry the exact persisted intent, never a fabricated fresh sequence.
            result = await f.service.renew_lease(**request)
            assert result['duplicate'] and result['deducted_seconds'] == 0
            assert await db.reading_pass_heartbeats.count_documents({}) == 1
            doc = await f.document()
            assert doc['lease_version'] == 2 and doc['text_phase'] == 'preparing'
            assert doc['preparation_deadline'] == f.origin.replace(tzinfo=None) + timedelta(seconds=20)
            stale = await f.service.renew_lease(**f.request('readable', key='stale-distinct-key'))
            assert stale['status'] == 'Stale'
            with pytest.raises(ReadingPassError, match='different renewal intent'):
                await f.service.renew_lease(**{**request, 'active': True, 'text_phase': 'readable'})
            await f.assert_balance(0)
    asyncio.run(run())


@pytest.mark.parametrize('round_id', range(3))
def test_preparation_readable_and_inactive_races(monkeypatch, round_id):
    async def run():
        async with _isolated_database() as db:
            f = await Fixture().seed(db, monkeypatch)
            f.at(16.112)
            await asyncio.gather(f.service.renew_lease(**f.request('preparing', key='prepare-race-key')),
                f.service.renew_lease(**f.request('readable', key='readable-race-key')), return_exceptions=True)
            await f.assert_balance(0)
            doc = await f.document()
            assert doc['lease_version'] == 2 and doc['text_phase'] in {'preparing', 'readable'}
            if doc['text_phase'] != 'readable':
                await f.service.renew_lease(**f.request('readable', doc['lease_version'], doc['last_sequence'] + 1, 'finish-readable-key'))
            f.at(21.112)
            doc = await f.document()
            version, sequence = doc['lease_version'], doc['last_sequence'] + 1
            await asyncio.gather(f.service.renew_lease(**f.request('readable', version, sequence, 'active-race-key')),
                f.service.renew_lease(**f.request('inactive', version, sequence, 'inactive-race-key')), return_exceptions=True)
            doc = await f.document()
            assert doc['lease_version'] == version + 1
            if doc['status'] != 'paused':
                await f.service.renew_lease(**f.request('inactive', doc['lease_version'], doc['last_sequence'] + 1, 'finish-inactive-key'))
            assert (await f.document())['status'] == 'paused'
            await f.assert_balance(5)
    asyncio.run(run())


@pytest.mark.parametrize('terminal', ['end', 'expire', 'revoke'])
def test_terminal_racing_readable_cannot_resurrect_or_backbill(monkeypatch, terminal):
    async def run():
        async with _isolated_database() as db:
            f = await Fixture().seed(db, monkeypatch)
            f.at(21 if terminal == 'expire' else 16.112)
            request = f.request('readable')
            terminal_call = f.end() if terminal == 'end' else f.revoke() if terminal == 'revoke' else f.service.renew_lease(**f.request('preparing', key='timeout-other-key'))
            await asyncio.gather(f.service.renew_lease(**request), terminal_call, return_exceptions=True)
            # Finish a retryable terminal operation, then prove renewal cannot
            # resurrect durable ended/expired/revoked state.
            if terminal == 'end':
                await f.end()
            elif terminal == 'revoke':
                await f.revoke()
            else:
                with pytest.raises(ReadingPassError):
                    await f.service.renew_lease(**request)
            doc = await f.document()
            assert doc['status'] in {'ended', 'expired', 'revoked'}
            await f.assert_balance(0)
            with pytest.raises(ReadingPassError):
                await f.service.authorize(user_id='fixture-user', auth_session_id='fixture-auth', session_id=f.lease['session_id'], lease_token=f.lease['lease_token'], content_type='text', content_id='preparation-fixture')
            outcome = await asyncio.gather(f.service.renew_lease(**request), return_exceptions=True)
            assert isinstance(outcome[0], ReadingPassError) or outcome[0]['status'] == 'Stale'
            assert (await f.document())['status'] == doc['status']
            await f.assert_balance(0)
    asyncio.run(run())


def test_end_revoke_and_inactive_settle_same_balance_once(monkeypatch):
    async def run():
        async with _isolated_database() as db:
            f = await Fixture().seed(db, monkeypatch)
            f.at(16.112)
            await f.service.renew_lease(**f.request('readable'))
            f.at(26.112)
            await asyncio.gather(f.end(), f.revoke(), f.service.renew_lease(**f.request('inactive', 2, 2, 'settlement-race-key')), return_exceptions=True)
            await f.revoke()
            await f.end()
            await f.assert_balance(10)
            assert (await f.document())['status'] in {'ended', 'revoked'}
            assert await db.wallet_ledger.count_documents({}) == 1
    asyncio.run(run())


def test_concurrent_legacy_session_settlements_do_not_lose_balance_updates(monkeypatch):
    async def run():
        async with _isolated_database() as db:
            f = await Fixture().seed(db, monkeypatch)
            f.at(16.112)
            await f.service.renew_lease(**f.request('readable'))
            # Deliberate historical-overlap fixture, not a second ordinary
            # start. The production unique active_lock prevents new overlap.
            legacy = await f.document()
            legacy.pop('_id'); legacy.pop('active_lock', None)
            legacy['id'] = 'synthetic-legacy-overlap'
            await db.reading_pass_sessions.insert_one(legacy)
            f.at(26.112)
            end_legacy = dict(user_id='fixture-user', auth_session_id='fixture-auth', session_id=legacy['id'])
            results = await asyncio.gather(f.end(), f.service.end_session(**end_legacy), return_exceptions=True)
            assert any(isinstance(value, dict) for value in results)
            await f.end(); await f.service.end_session(**end_legacy)
            await f.assert_balance(20)
            assert await db.wallet_ledger.count_documents({}) == 2
            assert await db.reading_pass_sessions.count_documents({'status': 'ended'}) == 2
    asyncio.run(run())
