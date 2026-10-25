"""Bounded recovery candidate; no CLI or automatic provider invocation.

An independently launched supervisor must own restart authority. The installer
never starts it and cannot arm recovery by supplying a receipt alone.
"""
from dataclasses import dataclass
import asyncio
import json
import os
from pathlib import Path
import time
from .open_window_audio_cap_installer import InstallerStop


@dataclass
class RecoveryState:
    deployment_id: str
    revision: str
    deadline: float
    restart_reserved: bool = False
    restart_acknowledged: bool = False
    healthy: bool = False


def reserve_restart(path, deployment_id, revision):
    """Exclusive durable reservation. Existing/uncertain records are never reset."""
    path = Path(path)
    fd = None
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            fd = None
            json.dump(dict(deployment_id=deployment_id, revision=revision,
                status="RESTART_RESERVED_OUTCOME_NOT_YET_KNOWN"), handle)
            handle.flush()
            os.fsync(handle.fileno())
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    except Exception:
        if fd is not None:
            os.close(fd)
        raise InstallerStop("RESTART_RESERVATION_UNVERIFIED_NO_RETRY") from None


async def recover_once(state, *, now, persist_reservation, provider, interlock=None):
    """One durable reservation before a single restart attempt, never a retry.

    provider is a separately reviewed supervisor adapter, not a caller's status
    Boolean. Unknown restart outcome still consumes the reservation. Recovery
    does not depend on whether the installer reports success or loses contact.
    """
    if now < state.deadline:
        raise InstallerStop("RECOVERY_DEADLINE_NOT_REACHED")
    if state.restart_reserved:
        raise InstallerStop("RECOVERY_ATTEMPT_ALREADY_RESERVED")
    if interlock is None:
        raise InstallerStop("INSTALLER_QUIESCENCE_INTERLOCK_REQUIRED")
    # Majority-acknowledged closure serializes against the install transaction.
    # Even a suspended installer or unknown commit cannot write behind closure.
    try:
        if await interlock.close() is not True:
            raise ValueError()
    except Exception:
        raise InstallerStop("INTERLOCK_CLOSE_UNVERIFIED_NO_RESTART") from None
    # Persist must implement exclusive create/fsync, not overwrite old state.
    state.restart_reserved = True
    try:
        await persist_reservation(state.deployment_id, state.revision)
    except Exception:
        raise InstallerStop("RESTART_RESERVATION_UNVERIFIED_NO_RETRY") from None
    try:
        before = await provider.observe(state.deployment_id)
        if (before.get("revision") != state.revision
            or before.get("automatic_deployments_off") is not True
            or before.get("other_deployments") is not False):
            raise InstallerStop("RECOVERY_TARGET_CHANGED")
        if before.get("stopped") is True:
            if await provider.restart(state.deployment_id) is not True:
                raise InstallerStop("RESTART_OUTCOME_UNVERIFIED")
            state.restart_acknowledged = True
        elif before.get("running") is not True:
            raise InstallerStop("RECOVERY_STATE_UNVERIFIED")
        after = (await provider.wait_for_health(state.deployment_id)
                 if hasattr(provider, "wait_for_health") else await provider.observe(state.deployment_id))
        state.healthy = (after.get("revision") == state.revision
            and after.get("running") is True and after.get("health_pass") is True
            and after.get("automatic_deployments_off") is True
            and after.get("other_deployments") is False)
        if not state.healthy:
            raise InstallerStop("RECOVERY_HEALTH_UNVERIFIED_NO_RETRY")
        return {"status": "EXACT_DEPLOYMENT_RESTORED", "restart_attempts": int(state.restart_acknowledged)}
    except InstallerStop:
        raise
    except Exception:
        raise InstallerStop("RECOVERY_OUTCOME_UNVERIFIED_NO_RETRY") from None


async def supervise(state, *, installer_pid, reservation_path, provider,
                    interlock=None, readiness_path=None,
                    clock=time.monotonic, sleep=asyncio.sleep):
    """Independent owner-started process; never launched by the installer.

    A caller must start this in a new process/session and verify readiness before
    stopping traffic. Waiting is independent of installer success, crash or exit.
    """
    if os.getpid() == installer_pid or not 0 < state.deadline-clock() <= 300:
        raise InstallerStop("INDEPENDENT_BOUNDED_SUPERVISOR_REQUIRED")
    if (interlock is None or readiness_path is None or interlock.plan.revision != state.revision
            or interlock.plan.deployment_id != state.deployment_id):
        raise InstallerStop("EXACT_INTERLOCK_BINDING_REQUIRED")
    from .domain.reading_pass import ensure_utc
    from .open_window_audio_cap_installer import _now
    if abs((ensure_utc(interlock.plan.restore_at)-_now()).total_seconds() - (state.deadline-clock())) > 1:
        raise InstallerStop("SUPERVISOR_DEADLINE_BINDING_MISMATCH")
    from .open_window_audio_cap_interlock import serve_readiness
    server = await serve_readiness(readiness_path, interlock, installer_pid)
    try:
        while clock() < state.deadline:
            await sleep(min(0.25, state.deadline-clock()))
        async def persist(deployment, revision):
            reserve_restart(reservation_path, deployment, revision)
        return await recover_once(state, now=clock(), persist_reservation=persist,
            provider=provider, interlock=interlock)
    finally:
        server.close()
        await server.wait_closed()
        # Preserve the socket path as stopped-attempt evidence; never reuse it.


class RailwayRecoveryProvider:
    """Prepared exact-target adapter. Instantiation does not contact Railway.

    Only the separately authorized supervisor may invoke restart. No rebuild,
    redeploy, variable write, old-secret restoration or database operation.
    """
    def __init__(self, deployment_id, revision, health_deadline):
        import re
        if (not re.fullmatch(r"[0-9a-f-]{36}", deployment_id)
                or not re.fullmatch(r"[0-9a-f]{40}", revision)
                or not 0 < health_deadline-time.monotonic() <= 300):
            raise InstallerStop("RECOVERY_TARGET_INVALID")
        self.deployment_id, self.revision = deployment_id, revision
        self.health_deadline = health_deadline

    async def observe(self, deployment_id):
        from . import open_window_audio_cap_live as live
        from . import open_window_audio_cap_installer as installer
        if deployment_id != self.deployment_id:
            raise InstallerStop("RECOVERY_TARGET_CHANGED")
        query = ('query { deployment(id:"' + deployment_id +
            '"){id deploymentStopped meta instances{status}} serviceInstance(environmentId:"' +
            installer.ENVIRONMENT + '",serviceId:"' + installer.SERVICE +
            '"){activeDeployments{id} latestDeployment{id status}}'
            ' serviceInstanceAutoDeployStatus(projectId:"' + installer.PROJECT +
            '",environmentId:"' + installer.ENVIRONMENT + '",serviceId:"' + installer.SERVICE +
            '"){enabled} }')
        try:
            response = json.loads(await live._command("railway", "api", query, "--compact"))
            if response.get("errors"):
                raise ValueError()
            d = response["data"]; dep = d["deployment"]; service = d["serviceInstance"]
            instances = dep["instances"]
            result = dict(revision=dep["meta"].get("commitHash"),
                automatic_deployments_off=d["serviceInstanceAutoDeployStatus"]["enabled"] is False,
                other_deployments=(service["latestDeployment"]["id"] != deployment_id or
                    service["latestDeployment"]["status"] in {"BUILDING", "DEPLOYING", "QUEUED", "INITIALIZING", "WAITING"} or
                    any(x["id"] != deployment_id for x in service["activeDeployments"])),
                stopped=dep["deploymentStopped"] is True and bool(instances) and
                    all(x["status"] in {"EXITED", "REMOVED"} for x in instances),
                running=dep["deploymentStopped"] is False and bool(instances) and
                    all(x["status"] == "RUNNING" for x in instances), health_pass=False)
            if result["running"]:
                result["health_pass"] = all(status == b"200" for status in await asyncio.gather(*[
                    live._command("curl", "--silent", "--output", "/dev/null", "--write-out",
                        "%{http_code}", "--max-time", "3", "--max-redirs", "0", url)
                    for url in ("https://api.theearnalism.com/healthz",
                                "https://theearnalism.com/api/reading-pass/config")]))
            return result
        except InstallerStop:
            raise
        except Exception:
            raise InstallerStop("RECOVERY_OBSERVATION_UNVERIFIED") from None

    async def restart(self, deployment_id):
        from .open_window_audio_cap_live import _command
        if deployment_id != self.deployment_id:
            raise InstallerStop("RECOVERY_TARGET_CHANGED")
        try:
            response = json.loads(await _command("railway", "api",
                'mutation {deploymentRestart(id:"' + deployment_id + '")}', "--compact"))
            return not response.get("errors") and response["data"]["deploymentRestart"] is True
        except Exception:
            raise InstallerStop("RESTART_OUTCOME_UNVERIFIED_NO_RETRY") from None

    async def wait_for_health(self, deployment_id):
        # Read-only polling; no second restart or other recovery mutation.
        while time.monotonic() < self.health_deadline:
            result = await self.observe(deployment_id)
            if (result["revision"] != self.revision or result["other_deployments"]
                    or not result["automatic_deployments_off"] or result["health_pass"]):
                return result
            await asyncio.sleep(min(1, max(0, self.health_deadline-time.monotonic())))
        raise InstallerStop("RECOVERY_HEALTH_DEADLINE_UNVERIFIED_NO_RETRY")
