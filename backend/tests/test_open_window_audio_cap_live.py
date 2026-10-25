"""Provider wiring and recovery tests use synthetic metadata; no live calls."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
import hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest

from backend import open_window_audio_cap_installer as installer
from backend import open_window_audio_cap_live as live
from backend import open_window_audio_cap_recovery as recovery
from backend import open_window_audio_cap_interlock as interlocks
from backend.tests.test_open_window_audio_cap_installer import context, NOW, ACCOUNT


def fixture(monkeypatch):
    _, a, _, _, _ = context(monkeypatch)
    receipt = dict(deployment_id=a.deployment_id, revision=a.revision,
        restore_at=NOW + timedelta(minutes=3), separate_process=True,
        external_writers_excluded=True, restart_attempt_limit=1,
        reading_pass_v2_enabled=True, startup_guard_pass=True, baseline_health_pass=True)
    approval = live.LiveApproval(installation=a,
        launcher_sha256=hashlib.sha256(Path(live.__file__).read_bytes()).hexdigest(),
        private_nodes_sha256=installer._hash([["127.0.0.1", 27018]]),
        fence_started_at=NOW, restore_at=receipt["restore_at"],
        recovery_receipt_sha256=installer._hash(receipt))
    snapshot = dict(serviceInstance=dict(activeDeployments=[],
        latestDeployment=dict(id=a.deployment_id, status="SUCCESS")),
        deployment=dict(id=a.deployment_id, status="SUCCESS", deploymentStopped=True,
            meta=dict(commitHash=a.revision), instances=[dict(status="EXITED")]),
        serviceInstanceAutoDeployStatus=dict(enabled=False), environmentStagedChanges=dict(patch=None))
    return approval, receipt, snapshot


@pytest.mark.parametrize("change", ["running", "wrong-source", "other-deployment", "auto-on",
    "staged", "empty-instances", "latest-building", "expired", "almost-expired", "long-window", "missing"])
def test_provider_fence_refuses_unqualified_state(monkeypatch, change):
    a, _, s = fixture(monkeypatch)
    if change == "running": s["deployment"]["instances"][0]["status"] = "RUNNING"
    elif change == "wrong-source": s["deployment"]["meta"]["commitHash"] = "b" * 40
    elif change == "other-deployment": s["serviceInstance"]["activeDeployments"] = [dict(id="other", deploymentStopped=True)]
    elif change == "auto-on": s["serviceInstanceAutoDeployStatus"]["enabled"] = True
    elif change == "staged": s["environmentStagedChanges"]["patch"] = {"changed": True}
    elif change == "empty-instances": s["deployment"]["instances"] = []
    elif change == "latest-building": s["serviceInstance"]["latestDeployment"]["status"] = "BUILDING"
    elif change == "expired": a = replace(a, restore_at=NOW)
    elif change == "almost-expired": a = replace(a, restore_at=NOW + timedelta(seconds=29))
    elif change == "long-window": a = replace(a, restore_at=NOW + timedelta(seconds=301))
    else: del s["deployment"]
    with pytest.raises(installer.InstallerStop): live.validate_snapshot(s, a, NOW)


def test_fence_refresh_cannot_extend_original_deadline(monkeypatch):
    a, _, s = fixture(monkeypatch)
    first = live.validate_snapshot(s, a, NOW)
    later = live.validate_snapshot(s, a, NOW + timedelta(seconds=60))
    assert first["valid_until"] == later["valid_until"] == a.restore_at


@pytest.mark.parametrize("change", ["different", "wrong-revision", "no-independent-process", "unexcluded-writers"])
def test_recovery_receipt_fails_closed(monkeypatch, change):
    a, receipt, _ = fixture(monkeypatch)
    if change == "different": receipt["extra"] = True
    elif change == "wrong-revision": receipt["revision"] = "b" * 40
    elif change == "no-independent-process": receipt["separate_process"] = False
    else: receipt["external_writers_excluded"] = False
    with pytest.raises(installer.InstallerStop): live.verify_recovery_receipt(receipt, a)


def test_provider_query_contains_no_mutation_or_variable_values(monkeypatch):
    a, _, snapshot = fixture(monkeypatch)
    calls = []
    async def command(*argv):
        import json
        calls.append(argv)
        return json.dumps(dict(data=snapshot)).encode()
    monkeypatch.setattr(live, "_command", command)
    assert asyncio.run(live.railway_snapshot(a)) == snapshot
    query = calls[0][2]
    assert query.startswith("query {") and "mutation" not in query
    assert "decryptVariables:false" in query and "variables(" not in query


def test_live_entry_reads_actual_source_and_binds_private_target_before_db(monkeypatch, tmp_path):
    a, receipt, snapshot = fixture(monkeypatch)
    identity = tmp_path / "identity.json"
    identity.write_text('{"user_id":"' + ACCOUNT + '"}'); identity.chmod(0o600)
    calls = []
    async def command(*argv):
        calls.append(argv)
        return (a.installation.revision + "\n").encode() if argv[-2:] == ("rev-parse", "HEAD") else b""
    async def observe(_): return deepcopy(snapshot)
    async def routes(): return None
    async def execute(server, approval, user_id, fence, env, *, interlock):
        assert user_id == ACCOUNT
        assert env["RAILWAY_GIT_COMMIT_SHA"] == a.installation.revision
        assert (await fence())["writers_quiesced"] is True
        return dict(status="DUMMY_INSTALLATION_NOT_A_DATABASE_CALL")
    monkeypatch.setattr(live, "_command", command)
    monkeypatch.setattr(live, "railway_snapshot", observe)
    monkeypatch.setattr(live, "verify_unreachable_routes", routes)
    monkeypatch.setattr(installer, "_execute", execute)
    client = SimpleNamespace(nodes={("127.0.0.1", 27018)})
    db = SimpleNamespace(name="earnalism", client=client)
    plan = interlocks.Plan(a.installation.revision, a.installation.deployment_id,
        "c" * 32, a.restore_at, hashlib.sha256(Path(recovery.__file__).read_bytes()).hexdigest(),
        db.name, a.private_nodes_sha256)
    a = replace(a, interlock_plan_sha256=plan.digest)
    gate = object.__new__(interlocks.Gate)
    gate.client, gate.db, gate.plan = client, db, plan
    async def ready(*_): return True
    monkeypatch.setattr(interlocks, "require_ready", ready)
    result = asyncio.run(installer.execute_production(installation_authorized=True,
        approval=a, identity_path=identity, client=client, db=db, recovery_receipt=receipt,
        interlock=gate, readiness_path="dummy-private-socket"))
    assert result["status"].startswith("DUMMY")
    assert any("status" in x for x in calls)
    # Wrong target fails before invoking even the harmless fake DB operation.
    db.name = "other"
    with pytest.raises(installer.InstallerStop, match="PRIVATE_DATABASE_MISMATCH"):
        asyncio.run(installer.execute_production(installation_authorized=True,
            approval=a, identity_path=identity, client=client, db=db, recovery_receipt=receipt,
            interlock=gate, readiness_path="dummy-private-socket"))


@pytest.mark.parametrize("scenario", ["healthy", "restart-unknown", "wrong-source", "unhealthy", "already-running", "reservation-failed"])
def test_recovery_reserves_before_one_attempt_and_never_retries(scenario):
    calls = []
    class Gate:
        async def close(self):
            calls.append("closed")
            return True
    class Provider:
        async def observe(self, deployment):
            return dict(revision="b" if scenario == "wrong-source" else "a",
                automatic_deployments_off=True, other_deployments=False,
                stopped=scenario != "already-running" and "restart" not in calls,
                running=scenario == "already-running" or "restart" in calls,
                health_pass=scenario != "unhealthy")
        async def restart(self, deployment):
            assert calls[:2] == ["closed", "reserved"]
            calls.append("restart")
            if scenario == "restart-unknown": raise RuntimeError("DUMMY_PRIVATE_ERROR")
            return True
    async def reserve(*_):
        calls.append("reserved")
        if scenario == "reservation-failed": raise installer.InstallerStop("RESERVATION_UNVERIFIED")
    state = recovery.RecoveryState("synthetic-deployment", "a", 100)
    async def run():
        if scenario in {"healthy", "already-running"}:
            result = await recovery.recover_once(state, now=100, persist_reservation=reserve, provider=Provider(), interlock=Gate())
            assert result["status"] == "EXACT_DEPLOYMENT_RESTORED"
        else:
            with pytest.raises(installer.InstallerStop) as e:
                await recovery.recover_once(state, now=100, persist_reservation=reserve, provider=Provider(), interlock=Gate())
            assert "DUMMY_PRIVATE" not in str(e.value)
        if state.restart_reserved:
            with pytest.raises(installer.InstallerStop, match="ALREADY_RESERVED"):
                await recovery.recover_once(state, now=101, persist_reservation=reserve, provider=Provider(), interlock=Gate())
        assert calls.count("restart") <= 1
    asyncio.run(run())


def test_recovery_never_starts_before_deadline():
    state = recovery.RecoveryState("synthetic", "a", 100)
    with pytest.raises(installer.InstallerStop, match="NOT_REACHED"):
        asyncio.run(recovery.recover_once(state, now=99, persist_reservation=None, provider=None))


def test_restart_reservation_is_durable_exclusive_and_survives_new_state(tmp_path):
    import json
    import stat
    path = tmp_path / "restart.json"
    recovery.reserve_restart(path, "synthetic", "a" * 40)
    before = path.read_bytes()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(before)["status"] == "RESTART_RESERVED_OUTCOME_NOT_YET_KNOWN"
    with pytest.raises(installer.InstallerStop, match="NO_RETRY"):
        recovery.reserve_restart(path, "synthetic", "a" * 40)
    assert path.read_bytes() == before
    link = tmp_path / "link"; link.symlink_to(path)
    with pytest.raises(installer.InstallerStop): recovery.reserve_restart(link, "synthetic", "a" * 40)
    assert path.read_bytes() == before


@pytest.mark.parametrize("status", [b"200", b"401", b"404", b"000", b"302", b"502", b"503"])
def test_route_fence_requires_positive_gateway_failure(monkeypatch, status):
    calls = []
    async def command(*argv):
        calls.append(argv)
        return status
    monkeypatch.setattr(live, "_command", command)
    if status in (b"502", b"503"):
        asyncio.run(live.verify_unreachable_routes())
        assert len(calls) == 3
    else:
        with pytest.raises(installer.InstallerStop): asyncio.run(live.verify_unreachable_routes())


def test_recovery_adapter_can_only_restart_its_exact_target(monkeypatch):
    import json
    import time
    a, _, _ = fixture(monkeypatch)
    calls = []
    async def command(*argv):
        calls.append(argv)
        return json.dumps({"data": {"deploymentRestart": True}}).encode()
    monkeypatch.setattr(live, "_command", command)
    provider = recovery.RailwayRecoveryProvider(a.installation.deployment_id,
        a.installation.revision, time.monotonic()+30)
    assert asyncio.run(provider.restart(a.installation.deployment_id)) is True
    assert calls[0][2] == 'mutation {deploymentRestart(id:"' + a.installation.deployment_id + '")}'
    with pytest.raises(installer.InstallerStop): asyncio.run(provider.restart("other"))
    assert len(calls) == 1


def test_independent_supervisor_survives_coordinator_exit(tmp_path):
    import json
    import subprocess
    import sys
    import time
    root = Path(__file__).resolve().parents[2]
    outcome = tmp_path / "outcome.json"
    reservation = tmp_path / "reservation.json"
    child = '''import asyncio,json,os,sys,time,tempfile,hashlib,shutil
from datetime import datetime,timedelta,timezone
from pathlib import Path
from backend.open_window_audio_cap_recovery import RecoveryState,supervise
from backend.open_window_audio_cap_interlock import Plan
from backend import open_window_audio_cap_recovery as recovery
deployment="00000000-0000-4000-8000-000000000001"
class DummyGate:
    plan=Plan("a"*40,deployment,"c"*32,datetime.now(timezone.utc)+timedelta(seconds=0.5),
        hashlib.sha256(Path(recovery.__file__).read_bytes()).hexdigest(),"synthetic","1"*64)
    async def require_open(self): pass
    async def close(self): return True
class DummyProvider:
    restarted=False
    async def observe(self,_):
        return dict(revision="a"*40,automatic_deployments_off=True,other_deployments=False,
            stopped=not self.restarted,running=self.restarted,health_pass=self.restarted)
    async def restart(self,_):
        self.restarted=True
        return True
private_dir=tempfile.mkdtemp(prefix="ow-r-",dir="/tmp")
result=asyncio.run(supervise(RecoveryState(deployment,"a"*40,time.monotonic()+0.5),
    installer_pid=int(sys.argv[1]),reservation_path=sys.argv[2],provider=DummyProvider(),
    interlock=DummyGate(),readiness_path=Path(private_dir)/"r.sock"))
shutil.rmtree(private_dir)
Path(sys.argv[3]).write_text(json.dumps(result))
'''
    coordinator = '''import subprocess,sys,os
subprocess.Popen([sys.executable,"-c",sys.argv[1],str(os.getpid()),sys.argv[2],sys.argv[3]],
    start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
'''
    parent = subprocess.run([sys.executable, "-c", coordinator, child, str(reservation), str(outcome)],
        cwd=root, capture_output=True, timeout=5)
    assert parent.returncode == 0
    deadline = time.monotonic()+5
    while not outcome.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert json.loads(outcome.read_text())["status"] == "EXACT_DEPLOYMENT_RESTORED"
    assert json.loads(reservation.read_text())["status"] == "RESTART_RESERVED_OUTCOME_NOT_YET_KNOWN"
