"""Local socket readiness and real Mongo transaction ordering; no production."""
import asyncio
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import pytest

from backend import open_window_audio_cap_interlock as locks
from backend import open_window_audio_cap_installer as installer
from backend import open_window_audio_cap_recovery as recovery
from backend.tests.test_open_window_audio_cap_installer import context, NOW, ACCOUNT


def plan(a, db=None, client=None):
    return locks.Plan(a.revision, a.deployment_id, "c" * 32, NOW + timedelta(seconds=180),
        hashlib.sha256(Path(recovery.__file__).read_bytes()).hexdigest(),
        db.name if db is not None else "synthetic",
        installer._hash(sorted([list(x) for x in client.nodes])) if client is not None else "1"*64)


@pytest.mark.parametrize("kind", ["stale-socket", "wrong-plan", "closed-gate", "bad-permissions", "same-process", "wrong-source"])
def test_readiness_is_live_bound_private_and_open(monkeypatch, kind):
    _, a, _, _, _ = context(monkeypatch)
    p = plan(a)
    if kind == "wrong-source": p = replace(p, supervisor_sha256="0"*64)
    class Gate:
        plan = p
        async def require_open(self):
            if kind == "closed-gate": raise installer.InstallerStop("INTERLOCK_NOT_OPEN")
    async def run():
        folder = Path(tempfile.mkdtemp(prefix="ow-ready-", dir="/tmp")); socket = folder/"r.sock"
        server = None
        try:
            pid = os.getpid() if kind == "same-process" else os.getpid()+100000
            if kind in {"same-process", "closed-gate", "wrong-source"}:
                with pytest.raises(installer.InstallerStop): await locks.serve_readiness(socket, Gate(), pid)
                return
            server = await locks.serve_readiness(socket, Gate(), pid)
            if kind == "stale-socket":
                server.close(); await server.wait_closed()
            elif kind == "bad-permissions": socket.chmod(0o666)
            other = replace(p, run_id="d"*32) if kind == "wrong-plan" else p
            with pytest.raises(installer.InstallerStop, match="LIVE_SUPERVISOR_NOT_READY"):
                await locks.require_ready(socket, other, pid)
        finally:
            if server: server.close(); await server.wait_closed()
            shutil.rmtree(folder)
    asyncio.run(run())


def test_fresh_readiness_roundtrip_and_gate_loss(monkeypatch):
    _, a, _, _, _ = context(monkeypatch)
    p = plan(a)
    class Gate:
        plan = p
        closed = False
        async def require_open(self):
            if self.closed: raise installer.InstallerStop("INTERLOCK_NOT_OPEN")
    async def run():
        folder = Path(tempfile.mkdtemp(prefix="ow-ready-", dir="/tmp")); socket = folder/"r.sock"
        gate = Gate(); pid = os.getpid()+100000
        server = await locks.serve_readiness(socket, gate, pid)
        try:
            assert await locks.require_ready(socket, p, pid) is True
            gate.closed = True
            with pytest.raises(installer.InstallerStop): await locks.require_ready(socket, p, pid)
        finally:
            server.close(); await server.wait_closed(); shutil.rmtree(folder)
    asyncio.run(run())


def test_automatic_write_retry_client_is_refused(monkeypatch):
    _, a, _, _, _ = context(monkeypatch)
    client = SimpleNamespace(options=SimpleNamespace(retry_writes=True))
    with pytest.raises(installer.InstallerStop, match="NO_RETRIES_REQUIRED"):
        locks.Gate(SimpleNamespace(client=client), client, plan(a))


@pytest.mark.parametrize("field", ["database", "nodes"])
def test_supervisor_cannot_close_a_different_database(monkeypatch, field):
    _, a, _, _, _ = context(monkeypatch)
    client = SimpleNamespace(options=SimpleNamespace(retry_writes=False), nodes={("127.0.0.1",27018)})
    db = SimpleNamespace(name="synthetic", client=client)
    p = plan(a, db, client)
    p = replace(p, database_name="another") if field == "database" else replace(p, private_nodes_sha256="0"*64)
    with pytest.raises(installer.InstallerStop): locks.Gate(db, client, p)


def test_supervisor_cannot_move_the_reviewed_restore_deadline(monkeypatch):
    _, a, _, _, _ = context(monkeypatch)
    async def run():
        with pytest.raises(installer.InstallerStop, match="DEADLINE_BINDING"):
            await recovery.supervise(recovery.RecoveryState(a.deployment_id,a.revision,200),
                installer_pid=os.getpid()+100000,reservation_path="unused",provider=object(),
                interlock=SimpleNamespace(plan=plan(a)),readiness_path="unused",clock=lambda:100)
    asyncio.run(run())


def test_claim_requires_same_active_transaction():
    gate = object.__new__(locks.Gate)
    for session in (None, SimpleNamespace(in_transaction=False)):
        with pytest.raises(installer.InstallerStop, match="TRANSACTION_REQUIRED"):
            asyncio.run(gate.claim(session))


def test_live_handshake_with_actual_independent_process():
    import subprocess
    import sys
    import time
    from datetime import datetime, timezone
    folder = Path(tempfile.mkdtemp(prefix="ow-ready-", dir="/tmp")); socket = folder/"r.sock"
    p = locks.Plan("a"*40, "00000000-0000-4000-8000-000000000001", "e"*32,
        datetime.now(timezone.utc)+timedelta(seconds=30),
        hashlib.sha256(Path(recovery.__file__).read_bytes()).hexdigest(), "synthetic", "1"*64)
    child = '''import asyncio,json,sys
from datetime import datetime
from backend.open_window_audio_cap_interlock import Plan,serve_readiness
data=json.loads(sys.argv[1]);data["restore_at"]=datetime.fromisoformat(data["restore_at"])
class DummyGate:
    plan=Plan(**data)
    async def require_open(self): pass
async def run():
    server=await serve_readiness(sys.argv[2],DummyGate(),int(sys.argv[3]))
    try: await asyncio.sleep(10)
    finally: server.close();await server.wait_closed()
asyncio.run(run())
'''
    encoded = {**p.__dict__, "restore_at": p.restore_at.isoformat()}
    process = subprocess.Popen([sys.executable, "-c", child, json.dumps(encoded), str(socket), str(os.getpid())],
        cwd=Path(__file__).resolve().parents[2], start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic()+5
        while not socket.exists() and time.monotonic() < deadline: time.sleep(0.025)
        assert asyncio.run(locks.require_ready(socket, p)) is True
        process.terminate(); process.wait(timeout=3)
        with pytest.raises(installer.InstallerStop, match="NOT_READY"):
            asyncio.run(locks.require_ready(socket, p))
    finally:
        if process.poll() is None: process.kill();process.wait()
        shutil.rmtree(folder)


def test_replayed_readiness_response_is_refused(monkeypatch):
    _, a, _, _, _ = context(monkeypatch)
    p = plan(a)
    async def run():
        folder = Path(tempfile.mkdtemp(prefix="ow-ready-", dir="/tmp")); socket = folder/"r.sock"
        async def stale(reader, writer):
            await reader.readline()
            writer.write(json.dumps(dict(plan=p.digest, challenge="0"*32,
                installer_pid=os.getpid(), supervisor_pid=os.getpid()+100000, state="READY")).encode()+b"\n")
            await writer.drain();writer.close();await writer.wait_closed()
        server = await asyncio.start_unix_server(stale, path=str(socket));socket.chmod(0o600)
        try:
            with pytest.raises(installer.InstallerStop): await locks.require_ready(socket, p)
        finally:
            server.close();await server.wait_closed();shutil.rmtree(folder)
    asyncio.run(run())


@pytest.mark.parametrize("result", [False, "error"])
def test_no_restart_without_confirmed_gate_closure(result):
    class Gate:
        async def close(self):
            if result == "error": raise RuntimeError("DUMMY_PRIVATE_DRIVER_DETAILS")
            return False
    async def run():
        with pytest.raises(installer.InstallerStop, match="NO_RESTART") as e:
            await recovery.recover_once(recovery.RecoveryState("synthetic", "a", 1), now=1,
                persist_reservation=None, provider=object(), interlock=Gate())
        assert "DUMMY_PRIVATE" not in str(e.value)
    asyncio.run(run())


mongo = pytest.mark.skipif(os.environ.get("READER_SEGMENT_MONGO_INTEGRATION") != "1",
    reason="requires authenticated disposable loopback Mongo")


@mongo
@pytest.mark.parametrize("scenario", ["close-first", "commit-first", "stale-snapshot", "abort-first", "close-response-lost", "commit-response-lost", "duplicate-setup"])
def test_real_mongo_gate_serializes_install_and_recovery(monkeypatch, scenario):
    from scripts.uat_mongo_fixture import isolated_database
    from pymongo.read_concern import ReadConcern
    from pymongo.write_concern import WriteConcern
    async def run():
        async with isolated_database("acceptance_operator_synthetic_", retryWrites=False) as (client, db):
            await db.users.insert_one(dict(id=ACCOUNT, role="user", status="active",
                reading_seconds_balance=1000, wallet_seconds=1000))
            server, a, env, proof, fence = context(monkeypatch, db, client)
            gate = locks.Gate(db, client, plan(a, db, client)); await gate.prepare()
            if scenario == "duplicate-setup":
                original = await gate.collection.find_one({"_id":gate.key})
                with pytest.raises(installer.OutcomeUnknown): await gate.prepare()
                assert await gate.collection.find_one({"_id":gate.key}) == original
                assert await gate.close() is True
            elif scenario == "close-first":
                assert await gate.close() is True
                with pytest.raises(installer.InstallerStop):
                    await installer.execute_synthetic(server, a, ACCOUNT, fence, env, interlock=gate)
            elif scenario in {"stale-snapshot", "abort-first"}:
                async with await client.start_session() as session:
                    session.start_transaction(read_concern=ReadConcern("snapshot"), write_concern=WriteConcern("majority"))
                    await db.users.find_one({"id": ACCOUNT}, session=session)
                    if scenario == "stale-snapshot":
                        await gate.close()
                        with pytest.raises(Exception): await gate.claim(session)
                        await session.abort_transaction()
                    else:
                        await gate.claim(session)
                        await session.abort_transaction()
                        assert await gate.close() is True
            elif scenario == "close-response-lost":
                collection = gate.collection
                class LostReply:
                    async def update_one(self, *args, **kwargs):
                        await collection.update_one(*args, **kwargs)
                        raise RuntimeError("DUMMY_PRIVATE_DRIVER_DETAILS")
                gate.collection = LostReply()
                with pytest.raises(installer.OutcomeUnknown): await gate.close()
                gate.collection = collection
                assert (await collection.find_one({"_id": gate.key}))["state"] == "CLOSED"
                # No installation can occur even though the closing response was lost.
                with pytest.raises(installer.InstallerStop):
                    await installer.execute_synthetic(server, a, ACCOUNT, fence, env, interlock=gate)
            elif scenario == "commit-response-lost":
                calls = [0]
                class ClientProxy:
                    nodes = client.nodes
                    admin = client.admin
                    async def start_session(self):
                        session = await client.start_session(); commit = session.commit_transaction
                        async def lost():
                            calls[0] += 1; await commit(); raise RuntimeError("DUMMY_PRIVATE_COMMIT")
                        session.commit_transaction = lost
                        return session
                server.client = ClientProxy()
                with pytest.raises(installer.OutcomeUnknown):
                    await installer.execute_synthetic(server, a, ACCOUNT, fence, env, interlock=gate)
                assert calls == [1]
                assert await gate.close() is True
            else:
                reached = asyncio.Event(); release = asyncio.Event(); count = [0]
                async def paused_fence():
                    count[0] += 1
                    if count[0] == 3:
                        reached.set(); await release.wait()
                    return proof
                install = asyncio.create_task(installer.execute_synthetic(server, a, ACCOUNT, paused_fence, env, interlock=gate))
                await asyncio.wait_for(reached.wait(), 3)
                close = asyncio.create_task(gate.close())
                await asyncio.sleep(0.05)
                assert not close.done()  # Recovery waits behind the install transaction.
                release.set()
                assert (await install)["status"] == "INSTALLED_VERIFIED"
                assert await close is True
            row = await gate.collection.find_one({"_id": gate.key})
            assert row["state"] == "CLOSED"
            user = await db.users.find_one({"id": ACCOUNT})
            installed = scenario in {"commit-first", "commit-response-lost"}
            assert ("reader_acceptance_budget" in user) == installed
            assert user["reading_seconds_balance"] == user["wallet_seconds"] == 1000
            assert await db.reading_pass_audit.count_documents({}) == int(installed)
            assert await db.reading_pass_sessions.count_documents({}) == 0
            assert await db.wallet_ledger.count_documents({}) == 0
            with pytest.raises(installer.InstallerStop):
                await installer.execute_synthetic(server, a, ACCOUNT, fence, env, interlock=gate)
    asyncio.run(run())
