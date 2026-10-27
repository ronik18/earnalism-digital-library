"""Owner-operated, stopped-service installer adapter; no executable CLI.

Importing this module performs no I/O. Railway access is query-only through the
existing CLI session. Credentials and an authenticated DB client are supplied
privately by the owner, never acquired or serialized by this adapter.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from . import open_window_audio_cap_installer as installer
from .domain.reading_pass import ReadingPassConfig, ensure_utc
from .reading_pass_service import ReadingPassService


@dataclass(frozen=True)
class LiveApproval:
    installation: installer.Approval
    launcher_sha256: str
    private_nodes_sha256: str
    fence_started_at: datetime
    restore_at: datetime
    # Receipt is a private reviewed input, not evidence manufactured by this module.
    recovery_receipt_sha256: str
    interlock_plan_sha256: str = ""


async def _command(*argv):
    """Capture provider output privately; errors never carry command output."""
    proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
        await proc.communicate()
        raise installer.InstallerStop("READ_ONLY_COMMAND_UNVERIFIED") from None
    if proc.returncode or len(stdout) > 131072:
        raise installer.InstallerStop("READ_ONLY_COMMAND_UNVERIFIED")
    return stdout


async def railway_snapshot(approval):
    """No provider mutation is present in this source."""
    a = approval.installation
    # Validate interpolation before invoking the CLI, including approval expiry.
    import re
    if not re.fullmatch(r"[0-9a-f-]{36}", a.deployment_id):
        raise installer.InstallerStop("INVALID_DEPLOYMENT")
    query = ('query { serviceInstance(environmentId:"' + installer.ENVIRONMENT +
        '",serviceId:"' + installer.SERVICE + '"){activeDeployments{id deploymentStopped}'
        ' latestDeployment{id status}} deployment(id:"' + a.deployment_id +
        '"){id status deploymentStopped meta instances{status}}'
        ' serviceInstanceAutoDeployStatus(projectId:"' + installer.PROJECT +
        '",environmentId:"' + installer.ENVIRONMENT + '",serviceId:"' + installer.SERVICE +
        '"){enabled} environmentStagedChanges(environmentId:"' + installer.ENVIRONMENT +
        '"){patch(decryptVariables:false)} }')
    try:
        value = json.loads(await _command("railway", "api", query, "--compact"))
        if value.get("errors"):
            raise ValueError()
        return value["data"]
    except (ValueError, KeyError, TypeError):
        raise installer.InstallerStop("PROVIDER_READ_UNVERIFIED") from None


async def verify_unreachable_routes():
    """Positive gateway failures required; a timeout is not proof of fencing."""
    for url in ("https://api.theearnalism.com/healthz",
                "https://api.theearnalism.com/api/reading-pass/config",
                "https://theearnalism.com/api/reading-pass/config"):
        status = await _command("curl", "--silent", "--output", "/dev/null",
            "--write-out", "%{http_code}", "--max-time", "3", "--max-redirs", "0", url)
        if status not in (b"502", b"503"):
            raise installer.InstallerStop("SERVING_ROUTE_STILL_REACHABLE_OR_UNVERIFIED")


def validate_snapshot(value, approval, now):
    """Prove the exact serving deployment is stopped, not merely SUCCESS."""
    try:
        a = approval.installation
        service, deployment = value["serviceInstance"], value["deployment"]
        active = service["activeDeployments"]
        if (service["latestDeployment"]["id"] != a.deployment_id
            or service["latestDeployment"]["status"] != "SUCCESS"
            or deployment["id"] != a.deployment_id or deployment["status"] != "SUCCESS"
            or deployment["meta"].get("commitHash") != a.revision
            or deployment["deploymentStopped"] is not True
            or not isinstance(active, list)
            or any(x["id"] != a.deployment_id or x["deploymentStopped"] is not True for x in active)
            or not deployment["instances"]
            or any(x["status"] not in {"EXITED", "REMOVED"} for x in deployment["instances"])
            or value["serviceInstanceAutoDeployStatus"]["enabled"] is not False
            or value["environmentStagedChanges"]["patch"]):
            raise ValueError()
        start, end = ensure_utc(approval.fence_started_at), ensure_utc(approval.restore_at)
        # Never renew the outage deadline when refreshing a provider observation.
        if not 0 < (end-start).total_seconds() <= 300 or not start <= now < end:
            raise ValueError()
        if (end-now).total_seconds() < 30:
            raise ValueError()
        return dict(writers_quiesced=True, automatic_deployments_off=True,
            revision=a.revision, deployment_id=a.deployment_id,
            observed_at=now, valid_until=end)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise installer.InstallerStop("STOPPED_SERVICE_FENCE_UNVERIFIED") from None


def verify_recovery_receipt(receipt, approval):
    """Require a separate, reviewed recovery supervisor's exact private receipt.

    This validates binding only. Production supervisor liveness and all-writer
    coverage require an independently qualified procedure, not a JSON assertion.
    """
    try:
        if (installer._hash(receipt) != approval.recovery_receipt_sha256
            or receipt["deployment_id"] != approval.installation.deployment_id
            or receipt["revision"] != approval.installation.revision
            or receipt["restore_at"] != approval.restore_at
            or receipt["separate_process"] is not True
            or receipt["external_writers_excluded"] is not True
            or receipt["reading_pass_v2_enabled"] is not True
            or receipt["startup_guard_pass"] is not True
            or receipt["baseline_health_pass"] is not True
            or type(receipt["restart_attempt_limit"]) is not int
            or receipt["restart_attempt_limit"] != 1):
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise installer.InstallerStop("INDEPENDENT_RECOVERY_NOT_QUALIFIED") from None


async def run_protected(*, approval, identity_path, client, db, recovery_receipt,
                        interlock, readiness_path):
    """Prepared private entry. Caller must hold separate installation approval.

    Runs independently of stopped service processes. Does not import server.py
    (which loads configuration and owns the serving runtime). No paid API calls.
    """
    try:
        root = Path(__file__).resolve().parents[1]
        if (hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != approval.launcher_sha256
            or (await _command("git", "-C", str(root), "rev-parse", "HEAD")).decode().strip()
                != approval.installation.revision
            or await _command("git", "-C", str(root), "status", "--porcelain")
            or db.name != "earnalism" or db.client is not client or not client.nodes
            or installer._hash(sorted([list(x) for x in client.nodes])) != approval.private_nodes_sha256):
            raise installer.InstallerStop("REVIEWED_SOURCE_OR_PRIVATE_DATABASE_MISMATCH")
        verify_recovery_receipt(recovery_receipt, approval)
        from .open_window_audio_cap_interlock import Gate, require_ready
        if (not isinstance(interlock, Gate) or interlock.client is not client
            or interlock.db is not db or interlock.plan.digest != approval.interlock_plan_sha256
            or interlock.plan.database_name != db.name
            or interlock.plan.private_nodes_sha256 != approval.private_nodes_sha256
            or interlock.plan.revision != approval.installation.revision
            or interlock.plan.deployment_id != approval.installation.deployment_id
            or interlock.plan.restore_at != approval.restore_at):
            raise installer.InstallerStop("EXACT_INTERLOCK_BINDING_REQUIRED")
        await require_ready(readiness_path, interlock.plan)
        user_id = installer.load_private_identity(identity_path)
        async def fence():
            observed_at = installer._now()
            snapshot = await railway_snapshot(approval)
            proof = validate_snapshot(snapshot, approval, observed_at)
            await verify_unreachable_routes()
            installer.verify_fence(proof, approval.installation)
            return proof
        await fence()  # Before any DB command; all serving instances must be stopped.
        env = dict(RAILWAY_PROJECT_ID=installer.PROJECT, RAILWAY_ENVIRONMENT_ID=installer.ENVIRONMENT,
            RAILWAY_SERVICE_ID=installer.SERVICE, RAILWAY_GIT_COMMIT_SHA=approval.installation.revision,
            RAILWAY_DEPLOYMENT_ID=approval.installation.deployment_id)
        # Remote runtime identity above is provider-attested; never caller-injected env.
        server = SimpleNamespace(__file__=str(root / "backend/server.py"), ENVIRONMENT="production",
            READING_PASS_V2_ENABLED=recovery_receipt["reading_pass_v2_enabled"], client=client, db=db,
            reading_pass_service=ReadingPassService(db=db, client=client,
                config=ReadingPassConfig(), token_secret="unused-installer-no-session-api"))
        result = await installer._execute(server, approval.installation, user_id, fence, env,
            interlock=interlock)
        await fence()  # Retain fencing through committed readback.
        return result
    except installer.InstallerStop:
        raise
    except Exception:
        # Caller must reconcile even if failure followed a commit. Never retry.
        raise installer.OutcomeUnknown("PROTECTED_ENTRY_UNVERIFIED_DO_NOT_RETRY") from None
