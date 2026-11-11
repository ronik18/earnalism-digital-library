"""Prepared synthetic tests; no production or provider access."""
import asyncio
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import pytest
from backend import paired_audio_acceptance_budget as policy
from backend.domain.reading_pass import ReadingPassError
from backend.tests import test_open_window_audio_acceptance_budget as legacy

def fixture(monkeypatch):
    clock, db, client, service = legacy.fixture(monkeypatch)
    monkeypatch.setattr(policy, "MEMBER_SHA256", sha256(b"user-1").hexdigest())
    db.users.rows[0]["reader_acceptance_budget"] = policy.build_budget(
        "user-1", clock[0], auth_session_id="auth-1")
    return clock, db, client, service

def test_cumulative_40_including_delayed_cleanup_and_terminal_replay(monkeypatch):
    async def run():
        clock, db, _, service = fixture(monkeypatch)
        lease = await legacy.start(service)
        await legacy.renew(service, lease, 1)
        for sequence in (2, 3):
            clock[0] += timedelta(seconds=20)
            await legacy.renew(service, lease, sequence)
        clock[0] += timedelta(hours=1)
        await legacy.end(service, lease)
        await legacy.end(service, lease)
        legacy.assert_accounting(db, 40)
        assert db.users.rows[0]["reader_acceptance_budget"]["sessions_started"] == 1
        with pytest.raises(ReadingPassError):
            await legacy.start(service)
    asyncio.run(run())

def test_zero_debit_start_is_consumed_and_transfer_is_denied(monkeypatch):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        with pytest.raises(ReadingPassError):
            await legacy.start(service, transfer=True)
        await legacy.end(service, await legacy.start(service))
        with pytest.raises(ReadingPassError):
            await legacy.start(service)
        legacy.assert_accounting(db, 0)
        assert len(db.reading_pass_sessions.rows) == 1
    asyncio.run(run())

@pytest.mark.parametrize("field,value", [
    ("maximum_seconds",41), ("maximum_seconds",True), ("maximum_sessions",2),
    ("sessions_started",True), ("sessions_started",2), ("consumed_seconds",-1),
    ("consumed_seconds",41), ("user_id","other"), ("auth_session_id","other"),
    ("approval_id","other"), ("package_version","other"),
    ("release_descriptor_sha256","other"), ("catalogue_uuid","other"),
    ("test_id","other"), ("status","disabled")])
def test_malformed_or_changed_authority_denies_without_writes(monkeypatch,field,value):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        db.users.rows[0]["reader_acceptance_budget"][field] = value
        before = deepcopy(db.users.rows)
        with pytest.raises(ReadingPassError):
            await legacy.start(service)
        assert db.users.rows == before
        assert not db.reading_pass_sessions.rows and not db.wallet_ledger.rows
    asyncio.run(run())

def test_wrong_package_text_and_other_title_cannot_bypass_cap(monkeypatch):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        for overrides in ({"scope":{}}, {"content_type":"text"}, {"content_id":"other"}):
            with pytest.raises(ReadingPassError):
                await legacy.start(service, **overrides)
        assert db.users.rows[0]["reader_acceptance_budget"]["sessions_started"] == 0
    asyncio.run(run())

def test_concurrent_last_second_terminal_and_renew_share_remaining_cap(monkeypatch):
    async def run():
        clock, db, _, service = fixture(monkeypatch)
        # Synthetic prior committed debits; not an installation technique.
        db.users.rows[0]["reader_acceptance_budget"]["consumed_seconds"] = 39
        db.users.rows[0]["reading_seconds_balance"] = db.users.rows[0]["wallet_seconds"] = 961
        lease = await legacy.start(service)
        await legacy.renew(service, lease, 1)
        clock[0] += timedelta(seconds=5)
        await asyncio.gather(legacy.renew(service,lease,2),legacy.end(service,lease),return_exceptions=True)
        assert db.users.rows[0]["reader_acceptance_budget"]["consumed_seconds"] == 40
        assert db.users.rows[0]["wallet_seconds"] == 960
        assert sum(row["debit"] for row in db.wallet_ledger.rows) == 1
    asyncio.run(run())


@pytest.mark.parametrize("change", ["future", "extended-expiry", "stale-start", "stale-debit"])
def test_clock_and_snapshot_cas_cannot_expand_authority(monkeypatch,change):
    async def run():
        clock, db, _, service = fixture(monkeypatch)
        budget = db.users.rows[0]["reader_acceptance_budget"]
        if change == "future":
            budget["created_at"] += timedelta(seconds=1)
            budget["expires_at"] += timedelta(seconds=1)
        elif change == "extended-expiry":
            budget["expires_at"] += timedelta(seconds=1)
        else:
            snapshot = deepcopy(budget)
            budget["sessions_started"] = 1
            if change == "stale-start":
                with pytest.raises(ReadingPassError):
                    await service._reserve_audio_acceptance_start("user-1",snapshot,None)
            else:
                with pytest.raises(ReadingPassError):
                    await service._debit_account("user-1",1,snapshot,None)
            assert db.users.rows[0]["wallet_seconds"] == 1000
            return
        with pytest.raises(ReadingPassError):
            await legacy.start(service)
        assert not db.reading_pass_sessions.rows
    asyncio.run(run())

@pytest.mark.parametrize("change", ["missing", "wrong-binding", "wrong-ordinal", "wrong-auth", "wrong-package"])
def test_bound_lease_cannot_fall_back_to_ordinary_access(monkeypatch,change):
    async def run():
        _, db, _, service = fixture(monkeypatch)
        lease = await legacy.start(service)
        row = db.reading_pass_sessions.rows[0]
        if change == "missing":
            del db.users.rows[0]["reader_acceptance_budget"]
        elif change == "wrong-binding": row["acceptance_test_id"] = "other"
        elif change == "wrong-ordinal": row["acceptance_session_ordinal"] = 2
        elif change == "wrong-auth": row["auth_session_id"] = "other"
        else: row["scope"]["package_version"] = "other"
        with pytest.raises(ReadingPassError):
            await service.authorize(user_id="user-1",auth_session_id="auth-1",
                session_id=lease["session_id"],lease_token=lease["lease_token"],
                content_type="audio",content_id=policy.SLUG)
        assert db.users.rows[0]["wallet_seconds"] == 1000
    asyncio.run(run())

@pytest.mark.parametrize("selected", [False, True])
def test_protected_media_revalidates_exact_public_package(monkeypatch,selected):
    from unittest.mock import AsyncMock
    async def run():
        _, _, _, service = fixture(monkeypatch)
        lease = await legacy.start(service)
        package = dict(package_version=policy.PACKAGE,
            release_descriptor_sha256=policy.DESCRIPTOR,duration_ms=491436)
        namespace = dict(_reading_pass_lease_headers=lambda request:(lease["session_id"],lease["lease_token"]),
            sredni_profile=legacy.sredni_profile,sredni_review=legacy.sredni_review,
            reading_pass_service=service,audio_acceptance_budget=legacy.policy,
            paired_audio_acceptance_budget=policy,
            _reader_audio_package_book_for_slug=AsyncMock(return_value={"slug":policy.SLUG}),
            _selected_audiobook_package=lambda *a:(package if selected else None,"",""),
            ReadingPassError=ReadingPassError,_reading_pass_http_error=lambda error:error)
        authorize = legacy.server_function("_authorize_reading_pass_audio",namespace)
        principal = dict(id="user-1",session_id="auth-1",role="user")
        if selected:
            assert (await authorize(None,principal,policy.SLUG))["acceptance_session_ordinal"] == 1
        else:
            with pytest.raises(ReadingPassError):
                await authorize(None,principal,policy.SLUG)
    asyncio.run(run())
