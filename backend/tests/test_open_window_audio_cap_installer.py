"""New installer delta only. Synthetic fixtures; live entry remains disabled."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from backend import open_window_audio_cap_installer as installer
from backend.domain.reading_pass import ReadingPassConfig
from backend.reading_pass_service import ReadingPassService

ACCOUNT = "synthetic-owner-1"
NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)
REPO = Path(__file__).resolve().parents[2]


def context(monkeypatch, db=None, client=None):
    monkeypatch.setattr(installer, "_now", lambda: NOW)
    approval = installer.Approval(revision="a" * 40,
        deployment_id="00000000-0000-4000-8000-000000000001",
        private_account_selector_sha256=hashlib.sha256(ACCOUNT.encode()).hexdigest(),
        installer_sha256=hashlib.sha256(Path(installer.__file__).read_bytes()).hexdigest(),
        valid_until=NOW + timedelta(minutes=5))
    env = dict(RAILWAY_PROJECT_ID=installer.PROJECT, RAILWAY_ENVIRONMENT_ID=installer.ENVIRONMENT,
        RAILWAY_SERVICE_ID=installer.SERVICE, RAILWAY_GIT_COMMIT_SHA=approval.revision,
        RAILWAY_DEPLOYMENT_ID=approval.deployment_id)
    service = ReadingPassService(db=db, client=client, config=ReadingPassConfig(), token_secret="synthetic")
    server = SimpleNamespace(__file__=str(REPO / "backend/server.py"), ENVIRONMENT="production",
        READING_PASS_V2_ENABLED=True, reading_pass_service=service, db=db, client=client)
    proof = dict(writers_quiesced=True, automatic_deployments_off=True, revision=approval.revision,
        deployment_id=approval.deployment_id, observed_at=NOW, valid_until=NOW + timedelta(minutes=2))
    async def fence(): return deepcopy(proof)
    return server, approval, env, proof, fence


def test_production_entry_cannot_execute():
    with pytest.raises(installer.InstallerStop, match="PRODUCTION_ENTRY_NOT_ENABLED"):
        asyncio.run(installer.execute_production())


@pytest.mark.parametrize("kind", ["remote", "wrong-namespace"])
def test_synthetic_adapter_rejects_other_targets_before_database_read(kind):
    name = "acceptance_operator_synthetic_" + "a" * 32 if kind == "remote" else "not_disposable"
    nodes = {("never-contact.invalid", 27018)} if kind == "remote" else {("127.0.0.1", 27018)}
    # No admin or collection methods exist: reaching either would fail the test.
    server = SimpleNamespace(db=SimpleNamespace(name=name), client=SimpleNamespace(nodes=nodes))
    with pytest.raises(installer.InstallerStop, match="DISPOSABLE_LOOPBACK_FIXTURE_REQUIRED"):
        asyncio.run(installer.execute_synthetic(server, None, ACCOUNT, None, {}))


@pytest.mark.parametrize("change", ["base-revision", "runtime-revision", "deployment", "account",
    "source-pin", "installer-pin", "approval-expired", "flag"])
def test_exact_runtime_and_private_account_fail_closed(monkeypatch, change):
    server, approval, env, _, _ = context(monkeypatch)
    account = ACCOUNT
    if change == "base-revision": approval = replace(approval, revision=installer.BASE_WITHOUT_ENFORCEMENT)
    elif change == "runtime-revision": env["RAILWAY_GIT_COMMIT_SHA"] = "b" * 40
    elif change == "deployment": env["RAILWAY_DEPLOYMENT_ID"] = "other"
    elif change == "account": account = "another-synthetic-owner"
    elif change == "source-pin": monkeypatch.setattr(installer, "ENFORCEMENT_PINS", {"backend/server.py": "0" * 64})
    elif change == "installer-pin": approval = replace(approval, installer_sha256="0" * 64)
    elif change == "approval-expired": approval = replace(approval, valid_until=NOW)
    else: server.READING_PASS_V2_ENABLED = False
    with pytest.raises(installer.InstallerStop): installer.verify_runtime(server, approval, account, env)


@pytest.mark.parametrize("change", ["not-quiesced", "auto-deploy-on", "wrong-revision", "stale", "future", "too-long"])
def test_fence_is_exact_and_fresh(monkeypatch, change):
    _, approval, _, proof, _ = context(monkeypatch)
    if change == "not-quiesced": proof["writers_quiesced"] = False
    elif change == "auto-deploy-on": proof["automatic_deployments_off"] = False
    elif change == "wrong-revision": proof["revision"] = "b" * 40
    elif change == "stale": proof["observed_at"] -= timedelta(seconds=31)
    elif change == "future": proof["observed_at"] += timedelta(seconds=1)
    else: proof["valid_until"] += timedelta(minutes=10)
    with pytest.raises(installer.InstallerStop): installer.verify_fence(proof, approval)


def test_private_identity_loader_is_owner_only_and_not_a_secret_input(tmp_path):
    p = tmp_path / "synthetic-identity.json"
    p.write_text(json.dumps({"user_id": ACCOUNT})); p.chmod(0o600)
    assert installer.load_private_identity(p) == ACCOUNT
    link = tmp_path / "link"; link.symlink_to(p)
    with pytest.raises(installer.InstallerStop): installer.load_private_identity(link)
    p.chmod(0o644)
    with pytest.raises(installer.InstallerStop): installer.load_private_identity(p)
    p.chmod(0o600); p.write_text(json.dumps({"user_id": ACCOUNT, "password": "DUMMY_NOT_A_SECRET"}))
    with pytest.raises(installer.InstallerStop): installer.load_private_identity(p)


pytestmark_mongo = pytest.mark.skipif(os.environ.get("READER_SEGMENT_MONGO_INTEGRATION") != "1",
    reason="requires authenticated disposable loopback fixture")


@pytestmark_mongo
@pytest.mark.parametrize("scenario", ["install-replay", "existing-budget", "active", "unsettled",
    "low-balance", "mirror-mismatch", "duplicate-install", "fence-lost", "changed-readback",
    "commit-unknown", "readback-unknown", "audit-missing", "audit-changed"])
def test_installer_delta_real_mongo(monkeypatch, scenario):
    from scripts.uat_mongo_fixture import isolated_database
    async def run():
        async with isolated_database("acceptance_operator_synthetic_") as (client, db):
            await db.users.insert_one(dict(id=ACCOUNT, role="user", status="active",
                reading_seconds_balance=1000, wallet_seconds=1000))
            server, approval, env, proof, fence = context(monkeypatch, db, client)
            if scenario == "existing-budget":
                await db.users.update_one({"id": ACCOUNT}, {"$set": {"reader_acceptance_budget": {"retained": True}}})
            elif scenario == "active":
                await db.reading_pass_sessions.insert_one(dict(user_id=ACCOUNT, status="active", active_lock=ACCOUNT))
            elif scenario == "unsettled":
                await db.reading_pass_sessions.insert_one(dict(user_id=ACCOUNT, status="ended", billing_active=False))
            elif scenario == "low-balance":
                await db.users.update_one({"id": ACCOUNT}, {"$set": {"reading_seconds_balance": 599, "wallet_seconds": 599}})
            elif scenario == "mirror-mismatch":
                await db.users.update_one({"id": ACCOUNT}, {"$set": {"wallet_seconds": 999}})
            elif scenario == "fence-lost":
                calls = [0]
                async def fence():
                    calls[0] += 1
                    return {**proof, "writers_quiesced": calls[0] < 3}
            before = await db.users.find_one({"id": ACCOUNT})
            if scenario in {"existing-budget", "active", "unsettled", "low-balance", "mirror-mismatch", "fence-lost"}:
                with pytest.raises(installer.InstallerStop):
                    await installer.execute_synthetic(server, approval, ACCOUNT, fence, env)
                assert await db.users.find_one({"id": ACCOUNT}) == before
                assert await db.reading_pass_acceptance_installations.count_documents({}) == 0
                assert await db.reading_pass_audit.count_documents({}) == 0
                return
            if scenario in {"commit-unknown", "readback-unknown"}:
                commit_calls = [0]
                if scenario == "commit-unknown":
                    class ClientProxy:
                        nodes = client.nodes
                        admin = client.admin
                        async def start_session(self):
                            session = await client.start_session()
                            original = session.commit_transaction
                            async def uncertain_commit():
                                commit_calls[0] += 1
                                await original()
                                raise RuntimeError("DUMMY_PRIVATE_DRIVER_DETAILS")
                            session.commit_transaction = uncertain_commit
                            return session
                    server.client = ClientProxy()
                else:
                    async def uncertain_readback(*args):
                        raise RuntimeError("DUMMY_PRIVATE_DRIVER_DETAILS")
                    monkeypatch.setattr(installer, "_readback", uncertain_readback)
                with pytest.raises(installer.OutcomeUnknown) as stopped:
                    await installer.execute_synthetic(server, approval, ACCOUNT, fence, env)
                assert "DUMMY_PRIVATE" not in str(stopped.value) and ACCOUNT not in str(stopped.value)
                if scenario == "commit-unknown": assert commit_calls == [1]
                assert await db.reading_pass_acceptance_installations.count_documents({}) == 1
                assert await db.reading_pass_audit.count_documents({}) == 1
                assert (await db.users.find_one({"id": ACCOUNT}))["reader_acceptance_budget"]["sessions_started"] == 0
                assert await db.reading_pass_sessions.count_documents({}) == 0
                assert await db.wallet_ledger.count_documents({}) == 0
                return
            if scenario == "duplicate-install":
                results = await asyncio.gather(*[installer.execute_synthetic(server, approval, ACCOUNT, fence, env)
                                                for _ in range(2)], return_exceptions=True)
                assert any(isinstance(x, dict) for x in results)
            else:
                result = await installer.execute_synthetic(server, approval, ACCOUNT, fence, env)
                assert result["status"] == "INSTALLED_VERIFIED"
                assert ACCOUNT not in json.dumps(result) and "balance" not in json.dumps(result)
            if scenario in {"audit-missing", "audit-changed"}:
                if scenario == "audit-missing":
                    await db.reading_pass_audit.delete_one({"_id": installer.INSTALLATION_ID})
                else:
                    await db.reading_pass_audit.update_one({"_id": installer.INSTALLATION_ID},
                        {"$set": {"maximum_seconds": 601}})
                with pytest.raises(installer.OutcomeUnknown, match="COMMITTED_READBACK_UNVERIFIED"):
                    await installer.execute_synthetic(server, approval, ACCOUNT, fence, env)
                assert (await db.users.find_one({"id": ACCOUNT}))["reader_acceptance_budget"]["consumed_seconds"] == 0
                return
            if scenario == "changed-readback":
                await db.users.update_one({"id": ACCOUNT}, {"$set": {"reader_acceptance_budget.maximum_seconds": 601}})
                with pytest.raises(installer.InstallerStop):
                    await installer.execute_synthetic(server, approval, ACCOUNT, fence, env)
                assert (await db.users.find_one({"id": ACCOUNT}))["reader_acceptance_budget"]["maximum_seconds"] == 601
            else:
                # Observe advanced counters without resetting them or granting balance.
                await db.users.update_one({"id": ACCOUNT}, {"$set": {
                    "reader_acceptance_budget.consumed_seconds": 3, "reader_acceptance_budget.sessions_started": 1}})
                result = await installer.execute_synthetic(server, approval, ACCOUNT, fence, env)
                assert result["status"] == "EXISTING_MATCHED_READ_ONLY"
                assert result["consumed_seconds"] == 3 and result["sessions_started"] == 1
            user = await db.users.find_one({"id": ACCOUNT})
            assert user["reading_seconds_balance"] == user["wallet_seconds"] == 1000
            assert await db.reading_pass_acceptance_installations.count_documents({}) == 1
            assert await db.reading_pass_audit.count_documents({}) == 1
            assert await db.reading_pass_sessions.count_documents({}) == 0
            assert await db.wallet_ledger.count_documents({}) == 0
            assert await db.wallet_transactions.count_documents({}) == 0
    asyncio.run(run())
