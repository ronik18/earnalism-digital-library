"""In-memory synthetic controller tests. No DB client or network is created."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from backend import paired_audio_acceptance_operator as operator
from backend import paired_audio_acceptance_budget as policy
from backend.tests.test_reading_pass_service_concurrency import Database


class Session:
    def __init__(self, client):
        self.client = client
        self.in_transaction = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def start_transaction(self, **options):
        assert options['read_concern'].level == 'snapshot'
        assert options['write_concern'].document == {'w': 'majority'}
        self.snapshot = {key: deepcopy(value.rows) for key, value in vars(self.client.db).items()}
        self.in_transaction = True

    async def abort_transaction(self):
        self.client.aborts += 1
        for key in list(vars(self.client.db)):
            if key not in self.snapshot:
                delattr(self.client.db, key)
            else:
                getattr(self.client.db, key).rows = deepcopy(self.snapshot[key])
        self.in_transaction = False

    async def commit_transaction(self):
        self.client.commits += 1
        self.in_transaction = False
        if self.client.unknown_commit:
            raise RuntimeError('synthetic lost commit acknowledgement')


class Client:
    def __init__(self, db):
        self.db = db
        self.starts = self.commits = self.aborts = 0
        self.unknown_commit = False

    async def start_session(self):
        self.starts += 1
        return Session(self)


def fixture(monkeypatch):
    db = Database(balance=1000)
    now = datetime.now(timezone.utc)
    db.user_sessions.rows.append(dict(id='auth-1', user_id='user-1', status='active',
        idle_expires_at=now+timedelta(hours=1), absolute_expires_at=now+timedelta(hours=1)))
    monkeypatch.setattr(policy, 'MEMBER_SHA256', sha256(b'user-1').hexdigest())
    package = dict(package_version=policy.PACKAGE,
                   release_descriptor_sha256=policy.DESCRIPTOR, duration_ms=491436)
    server = SimpleNamespace(db=db, client=Client(db),
        __file__=str(Path(operator.__file__).with_name('server.py')),
        ENVIRONMENT='production', READING_PASS_V2_ENABLED=True,
        _is_controlled_public_slug=lambda slug: slug == policy.SLUG,
        _controlled_artifact_doc=lambda *a, **k: {'slug': policy.SLUG},
        _can_expose_audiobook_package_canary=lambda *a: True,
        _book_audiobook_release_packages=lambda book: {policy.DESCRIPTOR:package},
        _validated_audiobook_package=lambda *a, **k: package,
        _has_release_eligible_audiobook_package_evidence=lambda *a: True)
    expected = {name:sha256(Path(operator.__file__).with_name(name).read_bytes()).hexdigest()
                for name in operator.SOURCE_FILES}
    for key, value in dict(RAILWAY_PROJECT_ID=operator.PROJECT,
        RAILWAY_ENVIRONMENT_ID=operator.ENVIRONMENT, RAILWAY_SERVICE_ID=operator.SERVICE,
        RAILWAY_GIT_COMMIT_SHA='a'*40).items():
        monkeypatch.setenv(key, value)
    args = dict(user_id='user-1', auth_session_id='auth-1', expected_revision='a'*40,
                expected_files=expected)
    return db, server, args


def test_once_only_without_historical_or_financial_mutation(monkeypatch):
    async def run():
        db, server, args = fixture(monkeypatch)
        db['native_audio_review_workflows'].rows.append(dict(_id='old', used_credit_seconds=51))
        db['capture_journal'].rows.append(dict(_id='old', consumed=6))
        historical = deepcopy(db.native_audio_review_workflows.rows), deepcopy(db.capture_journal.rows)
        result = await operator.install(server, **args)
        assert result['maximum_seconds'] == 40 and result['maximum_sessions'] == 1
        assert db.users.rows[0]['wallet_seconds'] == db.users.rows[0]['reading_seconds_balance'] == 1000
        assert db.users.rows[0]['reader_acceptance_budget']['consumed_seconds'] == 0
        assert db.users.rows[0][operator.MARKER] == policy.APPROVAL_ID
        assert len(db[operator.RECEIPTS].rows) == 1
        with pytest.raises(operator.InstallationHold):
            await operator.install(server, **args)
        assert server.client.commits == 1
        assert historical == (db.native_audio_review_workflows.rows, db.capture_journal.rows)
        assert not db.wallet_ledger.rows and not db.wallet_transactions.rows
    asyncio.run(run())


@pytest.mark.parametrize('conflict', ['cap', 'null-cap', 'marker', 'active', 'paused',
    'old-attempt', 'native', 'sredni', 'expired-auth', 'different-auth', 'wrong-package'])
def test_conflicts_abort_without_install_or_counter_changes(monkeypatch, conflict):
    async def run():
        db, server, args = fixture(monkeypatch)
        if conflict == 'cap': db.users.rows[0]['reader_acceptance_budget'] = dict(consumed_seconds=51, status='disabled')
        elif conflict == 'null-cap': db.users.rows[0]['reader_acceptance_budget'] = None
        elif conflict == 'marker': db.users.rows[0][operator.MARKER] = policy.APPROVAL_ID
        elif conflict in ('active','paused'): db.reading_pass_sessions.rows.append(dict(user_id='user-1',status=conflict))
        elif conflict == 'old-attempt': db.reading_pass_sessions.rows.append(dict(user_id='user-1',acceptance_test_id=policy.TEST_ID,status='ended'))
        elif conflict in ('native','sredni'):
            name = 'native_audio_review_grants' if conflict == 'native' else 'sredni_initial_review_grants'
            db[name].rows.append(dict(user_id='user-1',state='OPEN'))
        elif conflict == 'expired-auth': db.user_sessions.rows[0]['idle_expires_at'] = datetime(2020,1,1,tzinfo=timezone.utc)
        elif conflict == 'different-auth': args['auth_session_id'] = 'other'
        else: server._validated_audiobook_package = lambda *a, **k: None
        before = deepcopy(db.users.rows)
        with pytest.raises(operator.InstallationHold):
            await operator.install(server, **args)
        assert db.users.rows == before and not db[operator.RECEIPTS].rows
        assert server.client.commits == 0 and server.client.aborts == 1
    asyncio.run(run())


def test_unknown_commit_is_never_replayed(monkeypatch):
    async def run():
        db, server, args = fixture(monkeypatch)
        server.client.unknown_commit = True
        with pytest.raises(operator.CommitOutcomeUnknown):
            await operator.install(server, **args)
        assert server.client.starts == server.client.commits == 1
        assert server.client.aborts == 0
        assert len(db[operator.RECEIPTS].rows) == 1
        assert db.users.rows[0]['reader_acceptance_budget']['sessions_started'] == 0
    asyncio.run(run())


def test_failed_account_cas_rolls_back_inserted_receipt(monkeypatch):
    async def run():
        db, server, args = fixture(monkeypatch)
        async def changed(*_args, **_kwargs):
            return SimpleNamespace(modified_count=0)
        monkeypatch.setattr(db.users,'update_one',changed)
        with pytest.raises(operator.InstallationHold):
            await operator.install(server, **args)
        assert not db[operator.RECEIPTS].rows
        assert 'reader_acceptance_budget' not in db.users.rows[0]
        assert server.client.aborts == 1 and server.client.commits == 0
    asyncio.run(run())


@pytest.mark.parametrize('mismatch', ['source','provider','artifact','incomplete'])
def test_provenance_failure_holds_before_opening_transaction(monkeypatch,mismatch):
    async def run():
        _, server, args = fixture(monkeypatch)
        if mismatch == 'source': args['expected_revision'] = 'b'*40
        elif mismatch == 'provider': monkeypatch.setenv('RAILWAY_SERVICE_ID','other')
        elif mismatch == 'artifact': args['expected_files']['server.py'] = '0'*64
        else: del args['expected_files']['server.py']
        with pytest.raises(operator.InstallationHold):
            await operator.install(server, **args)
        assert server.client.starts == 0
    asyncio.run(run())


def test_uncapped_start_fence_cannot_use_preinstallation_snapshot(monkeypatch):
    async def run():
        db, server, args = fixture(monkeypatch)
        # A stale pre-installation read cannot admit an uncapped session.
        await operator.install(server, **args)
        from backend.domain.reading_pass import ReadingPassError
        with pytest.raises(ReadingPassError):
            await policy.fence_start(db,'user-1',None,mongo_session=object())
        budget = deepcopy(db.users.rows[0]['reader_acceptance_budget'])
        await policy.fence_start(db,'user-1',budget,mongo_session=object())
        assert db.users.rows[0]['paired_audio_acceptance_admission_revision'] == 1
        assert db.users.rows[0]['reader_acceptance_budget'] == budget
    asyncio.run(run())


def test_other_members_do_not_acquire_new_fence_writes(monkeypatch):
    async def run():
        db, _, _ = fixture(monkeypatch)
        before = deepcopy(db.users.rows)
        await policy.fence_start(db,'unrelated-user',None,mongo_session=object())
        assert db.users.rows == before
    asyncio.run(run())
