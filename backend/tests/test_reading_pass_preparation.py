"""Synthetic server-clock qualification; no external service or production data."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.domain.reading_pass import ReadingPassConfig, ReadingPassError
from backend.reading_pass_service import ReadingPassService
from backend.tests.test_reading_pass_service_concurrency import Database, Client, _revoke_fixture


class Fixture:
    def __init__(self, monkeypatch):
        self.now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        self.origin = self.now
        monkeypatch.setattr("backend.reading_pass_service._now", lambda: self.now)
        self.db = Database(balance=120)
        self.db.reader_segment_activation_state.rows.append({"book_slug": "book-1", "active_segmentation_version": "fixture-v1", "generation": 1})
        self.db.reader_segment_manifests.rows.append({"book_slug": "book-1", "segmentation_version": "fixture-v1", "version": "fixture-manifest-v1", "status": "active"})
        self.service = ReadingPassService(db=self.db, client=Client(), config=ReadingPassConfig(), token_secret="synthetic-secret")
        self.scope = {"canonical_page_index": 75, "segmentation_version": "fixture-v1", "manifest_version": "fixture-manifest-v1", "authority_activation_generation": 1}

    def at(self, seconds):
        self.now = self.origin + timedelta(seconds=seconds)

    async def start(self, **kwargs):
        self.lease = await self.service.start_session(user_id="user-1", auth_session_id="auth-1", device_id="fixture-device", device_label="Synthetic", content_type="text", content_id="book-1", scope=self.scope, prepare_text=True, **kwargs)
        self.sequence = 0
        return self.lease

    async def renew(self, phase, **extra):
        self.sequence += 1
        self.request = dict(user_id="user-1", auth_session_id="auth-1", session_id=self.lease["session_id"], lease_token=self.lease["lease_token"], lease_version=self.lease["lease_version"], sequence=self.sequence, idempotency_key=f"fixture-heartbeat-{self.sequence}", active=phase == "readable", text_phase=phase)
        self.request.update(extra)
        self.lease = await self.service.renew_lease(**self.request)
        return self.lease

    async def end(self):
        return await self.service.end_session(user_id="user-1", auth_session_id="auth-1", session_id=self.lease["session_id"])


def test_preparation_then_readability_and_inactivity_are_server_timed(monkeypatch):
    async def run():
        f = Fixture(monkeypatch)
        start = await f.start()
        assert start["text_phase"] == "preparing" and start["deducted_seconds"] == 0
        f.at(10)
        preparing = await f.renew("preparing")
        assert preparing["status"] == "Running" and preparing["balance_seconds"] == 120 and preparing["deducted_seconds"] == 0
        assert preparing["preparation_expires_at"] == start["preparation_expires_at"]
        f.at(16.112)
        visible = await f.renew("readable")
        assert visible["balance_seconds"] == 120 and visible["deducted_seconds"] == 0
        f.at(26.112)
        reading = await f.renew("readable")
        assert reading["deducted_seconds"] == 10 and reading["balance_seconds"] == 110
        f.at(29.112)
        paused = await f.renew("inactive")
        assert paused["status"] == "Paused" and paused["deducted_seconds"] == 3 and paused["balance_seconds"] == 107
        f.at(30)
        resumed = await f.renew("preparing")
        assert resumed["status"] == "Running" and resumed["deducted_seconds"] == 0
        f.at(31)
        assert (await f.renew("readable"))["deducted_seconds"] == 0
        assert sum(row["debit"] for row in f.db.wallet_ledger.rows) == 13
    asyncio.run(run())


@pytest.mark.parametrize("terminal", ["end", "inactive", "timeout", "revoked", "denied"])
def test_preparation_terminal_paths_never_bill(monkeypatch, terminal):
    async def run():
        f = Fixture(monkeypatch)
        await f.start()
        f.at(16)
        if terminal == "end":
            assert (await f.end())["deducted_seconds"] == 0
        elif terminal == "inactive":
            assert (await f.renew("inactive"))["status"] == "Paused"
        elif terminal == "timeout":
            f.at(20)
            with pytest.raises(ReadingPassError, match="preparation window expired"):
                await f.renew("preparing")
            assert f.db.reading_pass_sessions.rows[0]["ended_reason"] == "preparation_timeout"
        elif terminal == "revoked":
            await _revoke_fixture(f.service)
            with pytest.raises(ReadingPassError) as error:
                await f.renew("preparing")
            # The revocation operation already terminates matching sessions.
            assert error.value.code == "LEASE_EXPIRED"
            assert f.db.reading_pass_sessions.rows[0]["status"] == "revoked"
        else:
            with pytest.raises(ReadingPassError) as error:
                await f.renew("preparing", text_authority="denied")
            assert error.value.code == "CONTENT_AUTHORITY_UNAVAILABLE"
        assert f.db.users.rows[0]["reading_seconds_balance"] == 120
        assert f.db.wallet_ledger.rows == []
    asyncio.run(run())


def test_restart_cannot_reset_unearned_preparation_deadline(monkeypatch):
    async def run():
        f = Fixture(monkeypatch)
        original = await f.start()
        f.at(15)
        await f.end()
        restarted = await f.start()
        assert restarted["preparation_expires_at"] == original["preparation_expires_at"]
        assert restarted["lease_expires_at"] == original["preparation_expires_at"]
        f.at(20)
        await f.end()
        with pytest.raises(ReadingPassError) as error:
            await f.start()
        assert error.value.code == "PREPARATION_EXPIRED"
        assert f.db.wallet_ledger.rows == []
        f.at(141)
        retry = await f.start()
        assert retry["text_phase"] == "preparing" and retry["deducted_seconds"] == 0
        assert retry["preparation_expires_at"] != original["preparation_expires_at"]
    asyncio.run(run())


def test_preparation_idempotency_binds_phase_and_does_not_renew_deadline(monkeypatch):
    async def run():
        f = Fixture(monkeypatch)
        await f.start()
        f.at(10)
        first = await f.renew("preparing")
        f.at(16)
        duplicate = await f.service.renew_lease(**f.request)
        assert duplicate["duplicate"] and duplicate["lease_version"] == first["lease_version"]
        assert duplicate["preparation_expires_at"] == first["preparation_expires_at"]
        with pytest.raises(ReadingPassError) as error:
            await f.service.renew_lease(**{**f.request, "active": False, "text_phase": "inactive"})
        assert error.value.code == "HEARTBEAT_INTENT_CONFLICT"
        assert len(f.db.reading_pass_heartbeats.rows) == 1 and f.db.wallet_ledger.rows == []
    asyncio.run(run())


def test_readable_session_cannot_relabel_billable_time_as_preparation(monkeypatch):
    async def run():
        f = Fixture(monkeypatch)
        await f.start()
        f.at(1)
        await f.renew("readable")
        f.at(10)
        with pytest.raises(ReadingPassError) as error:
            await f.renew("preparing")
        assert error.value.status_code == 409
        assert f.db.reading_pass_sessions.rows[0]["billing_active"] is True
    asyncio.run(run())


@pytest.mark.parametrize("active,phase", [(True, "preparing"), (True, "inactive"), (False, "readable"), (False, "unknown")])
def test_malformed_lifecycle_cannot_change_authority_or_billing(monkeypatch, active, phase):
    async def run():
        f = Fixture(monkeypatch)
        await f.start()
        with pytest.raises(ReadingPassError) as error:
            await f.renew(phase, active=active)
        assert error.value.status_code == 400
        assert len(f.db.reading_pass_heartbeats.rows) == 0
        assert f.db.users.rows[0]["reading_seconds_balance"] == 120
    asyncio.run(run())


def test_expiry_cannot_authorize_chunks_or_bill_even_after_reconnect_grace(monkeypatch):
    async def run():
        f = Fixture(monkeypatch)
        lease = await f.start()
        f.at(40)
        with pytest.raises(ReadingPassError) as denied:
            await f.service.authorize(user_id="user-1", auth_session_id="auth-1", session_id=lease["session_id"], lease_token=lease["lease_token"], content_type="text", content_id="book-1")
        assert denied.value.code == "LEASE_EXPIRED"
        with pytest.raises(ReadingPassError) as expired:
            await f.renew("preparing")
        assert expired.value.code == "PREPARATION_EXPIRED"
        assert f.db.reading_pass_sessions.rows[0]["ended_reason"] == "preparation_timeout"
        assert f.db.wallet_ledger.rows == []
    asyncio.run(run())


def test_audio_playing_and_buffering_contract_is_unchanged(monkeypatch):
    async def run():
        f = Fixture(monkeypatch)
        lease = await f.service.start_session(user_id="user-1", auth_session_id="auth-1", device_id="audio-fixture", device_label="Synthetic", content_type="audio", content_id="audio-fixture", scope={}, prepare_text=True)
        assert "text_phase" not in lease
        f.at(10)
        request = dict(user_id="user-1", auth_session_id="auth-1", session_id=lease["session_id"], lease_token=lease["lease_token"], lease_version=1, sequence=1, idempotency_key="audio-buffer-001", active=False, playback_state="buffering")
        buffered = await f.service.renew_lease(**request)
        assert buffered["status"] == "Connecting" and buffered["deducted_seconds"] == 0
        f.at(15)
        request.update(lease_version=2, sequence=2, idempotency_key="audio-playing-002", active=True, playback_state="playing")
        playing = await f.service.renew_lease(**request)
        assert playing["status"] == "Running" and playing["deducted_seconds"] == 0
        f.at(25)
        request.update(lease_version=3, sequence=3, idempotency_key="audio-playing-003")
        assert (await f.service.renew_lease(**request))["deducted_seconds"] == 10
        with pytest.raises(ReadingPassError):
            await f.service.renew_lease(**{**request, "text_phase": "preparing", "active": False})
    asyncio.run(run())


def test_simultaneous_preparation_receipts_transition_once(monkeypatch):
    async def run():
        f = Fixture(monkeypatch)
        lease = await f.start()
        f.at(10)
        request = dict(user_id="user-1", auth_session_id="auth-1", session_id=lease["session_id"], lease_token=lease["lease_token"], lease_version=1, sequence=1, idempotency_key="preparation-concurrent-001", active=False, text_phase="preparing")
        results = await asyncio.gather(*(f.service.renew_lease(**request) for _ in range(100)))
        assert all(row["deducted_seconds"] == 0 and row["lease_version"] == 2 for row in results)
        assert sum(bool(row.get("duplicate")) for row in results) == 99
        assert len(f.db.reading_pass_heartbeats.rows) == 1
        assert f.db.wallet_ledger.rows == []
    asyncio.run(run())
