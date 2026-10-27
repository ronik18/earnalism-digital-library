"""Disabled protected installer candidate. No CLI, connections or credentials.

The only executable adapter is restricted to disposable loopback UAT databases.
Production enablement, the exact merged revision and a provider-backed traffic
fence remain separate approval gates. No existing authority is ever overwritten.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

try:
    from . import audio_acceptance_budget as policy
    from .domain.reading_pass import ensure_utc
except ImportError:
    import audio_acceptance_budget as policy
    from domain.reading_pass import ensure_utc

INSTALLATION_ID = "open-window-audio-cap-install-v1"
BASE_WITHOUT_ENFORCEMENT = "0596e6ab11d26acffe93a79b6165801c0e9d2037"
PROJECT = "a8533934-35c4-463e-9f43-577a9ac391ee"
ENVIRONMENT = "580b250c-80ee-48ad-bfbe-fa4e31a6b378"
SERVICE = "5af42e7e-f518-4f6a-b602-d9950866501f"
ENFORCEMENT_PINS = {
    "backend/audio_acceptance_budget.py": "61c9bacc041dc1342db3398abd4db3790f481e769f40fe522181e7fd8d4653c9",
    "backend/reading_pass_service.py": "f28f6af29ee961dd7ed5a1590d31052245cae59868f4b77a54306a1fe5d4c4a8",
    "backend/server.py": "a1c36360f518f292638bd875a17281388b42dcf8d3dd15109073205bcf6544b3",
}


class InstallerStop(ValueError):
    """Sanitized stop code only; never include account/driver data."""


class OutcomeUnknown(InstallerStop):
    pass


@dataclass(frozen=True)
class Approval:
    revision: str
    deployment_id: str
    private_account_selector_sha256: str
    installer_sha256: str
    valid_until: datetime


def _now():
    return datetime.now(timezone.utc)


def _hash(value):
    def encode(item):
        if isinstance(item, datetime):
            return ensure_utc(item).isoformat()
        raise TypeError("Unsupported authority value")
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=encode).encode()).hexdigest()


def load_private_identity(path):
    """Owner-private account-ID file only; no token/password/key inputs."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        raise InstallerStop("PRIVATE_IDENTITY_FILE_REQUIRED") from None
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 512):
            raise InstallerStop("PRIVATE_IDENTITY_FILE_REQUIRED")
        try:
            value = json.load(handle)
        except (ValueError, UnicodeError):
            raise InstallerStop("PRIVATE_IDENTITY_INVALID") from None
    if (not isinstance(value, dict) or set(value) != {"user_id"}
            or not isinstance(value["user_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value["user_id"])):
        raise InstallerStop("PRIVATE_IDENTITY_INVALID")
    return value["user_id"]


def verify_runtime(server, approval, user_id, environ):
    if (not re.fullmatch(r"[0-9a-f]{40}", approval.revision)
            or approval.revision == BASE_WITHOUT_ENFORCEMENT
            or not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", approval.deployment_id)
            or not re.fullmatch(r"[0-9a-f]{64}", approval.installer_sha256)
            or not re.fullmatch(r"[0-9a-f]{64}", approval.private_account_selector_sha256)
            or not isinstance(approval.valid_until, datetime)
            or ensure_utc(approval.valid_until) <= _now()):
        raise InstallerStop("APPROVAL_OR_ENFORCEMENT_REVISION_UNQUALIFIED")
    if not hmac.compare_digest(hashlib.sha256(user_id.encode()).hexdigest(),
                               approval.private_account_selector_sha256):
        raise InstallerStop("PRIVATE_ACCOUNT_MISMATCH")
    expected = dict(RAILWAY_PROJECT_ID=PROJECT, RAILWAY_ENVIRONMENT_ID=ENVIRONMENT,
                    RAILWAY_SERVICE_ID=SERVICE, RAILWAY_GIT_COMMIT_SHA=approval.revision,
                    RAILWAY_DEPLOYMENT_ID=approval.deployment_id)
    if (any(environ.get(k) != v for k, v in expected.items())
            or server.ENVIRONMENT != "production" or server.READING_PASS_V2_ENABLED is not True
            or not hasattr(server.reading_pass_service, "_reserve_audio_acceptance_start")):
        raise InstallerStop("EXACT_RUNTIME_MISMATCH")
    root = Path(server.__file__).resolve().parent.parent
    try:
        pins_match = all(hashlib.sha256((root / p).read_bytes()).hexdigest() == digest
                         for p, digest in ENFORCEMENT_PINS.items())
    except OSError:
        raise InstallerStop("ENFORCEMENT_SOURCE_UNAVAILABLE") from None
    if not pins_match:
        raise InstallerStop("ENFORCEMENT_SOURCE_MISMATCH")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != approval.installer_sha256:
        raise InstallerStop("INSTALLER_SOURCE_MISMATCH")


def verify_fence(proof, approval):
    """Validate freshness/binding, not the provider fact itself.

    A separately qualified provider procedure must hold the traffic fence from
    before this proof through committed readback. A Boolean alone is not proof.
    """
    if (not isinstance(proof, dict) or proof.get("writers_quiesced") is not True
            or proof.get("automatic_deployments_off") is not True
            or proof.get("revision") != approval.revision
            or proof.get("deployment_id") != approval.deployment_id
            or not isinstance(proof.get("observed_at"), datetime)
            or not isinstance(proof.get("valid_until"), datetime)):
        raise InstallerStop("QUALIFIED_TRAFFIC_FENCE_REQUIRED")
    age = (_now() - ensure_utc(proof["observed_at"])).total_seconds()
    span = (ensure_utc(proof["valid_until"]) - ensure_utc(proof["observed_at"])).total_seconds()
    if not 0 <= age <= 30 or not 0 < span <= 300 or _now() >= ensure_utc(proof["valid_until"]):
        raise InstallerStop("TRAFFIC_FENCE_EXPIRED")


async def _assert_settled(db, user_id, session):
    cursor = db.reading_pass_sessions.find({"user_id": user_id},
        {"_id": 0, "status": 1, "active_lock": 1, "billing_active": 1, "settlement_at": 1},
        session=session).limit(1001)
    rows = await cursor.to_list(1001)
    if len(rows) > 1000 or any(
        r.get("status") not in {"ended", "expired", "exhausted", "transferred", "revoked"}
        or "active_lock" in r or r.get("billing_active") is not False
        or not isinstance(r.get("settlement_at"), datetime) for r in rows
    ):
        raise InstallerStop("ACTIVE_OR_UNSETTLED_SESSION")


def _validate_retained(record, receipt, approval, user_id):
    if not record or not receipt:
        raise InstallerStop("RECEIPT_OR_AUTHORITY_MISSING")
    try:
        policy.validate_budget(record, dict(user_id=user_id, content_type="audio",
            content_id=policy.SLUG, scope=policy.PACKAGE_SCOPE), starting=True, now=_now())
    except Exception:
        raise InstallerStop("RETAINED_AUTHORITY_MISMATCH") from None
    initial = {**record, "consumed_seconds": 0, "sessions_started": 0}
    expected = dict(user_id=user_id, revision=approval.revision,
                    deployment_id=approval.deployment_id, source_pins=ENFORCEMENT_PINS,
                    installer_sha256=approval.installer_sha256,
                    initial_budget_sha256=_hash(initial))
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise InstallerStop("INSTALLATION_RECEIPT_MISMATCH")


async def _operation(server, approval, user_id, fence, session, environ, interlock=None):
    db = server.db
    if interlock is not None:
        await interlock.claim(session)
    user = await db.users.find_one({"id": user_id, "role": "user"},
        {"_id": 0, "status": 1, "reading_seconds_balance": 1, "wallet_seconds": 1,
         "reader_acceptance_budget": 1, "active_reading_session": 1}, session=session)
    if not user or user.get("status") != "active":
        raise InstallerStop("EXACT_NORMAL_ACCOUNT_UNAVAILABLE")
    receipt = await db.reading_pass_acceptance_installations.find_one(
        {"_id": INSTALLATION_ID}, session=session)
    if receipt:
        _validate_retained(user.get("reader_acceptance_budget"), receipt, approval, user_id)
        return False  # Idempotent observation; never reset counters or expiry.
    if "reader_acceptance_budget" in user or "active_reading_session" in user:
        raise InstallerStop("EXISTING_AUTHORITY_OR_SESSION_MARKER")
    await _assert_settled(db, user_id, session)
    balance, mirror = user.get("reading_seconds_balance"), user.get("wallet_seconds")
    if type(balance) is not int or type(mirror) is not int or balance != mirror or balance < 600:
        raise InstallerStop("EXISTING_BALANCE_UNQUALIFIED")
    verify_fence(await fence(), approval)
    verify_runtime(server, approval, user_id, environ)
    record = policy.build_budget(user_id, _now())
    query = dict(id=user_id, role="user", status="active", reading_seconds_balance=balance,
                 wallet_seconds=mirror, reader_acceptance_budget={"$exists": False},
                 active_reading_session={"$exists": False})
    result = await db.users.update_one(query, {"$set": {"reader_acceptance_budget": record}}, session=session)
    if result.modified_count != 1:
        raise InstallerStop("ACCOUNT_CAS_CHANGED_NO_RETRY")
    await db.reading_pass_acceptance_installations.insert_one(dict(_id=INSTALLATION_ID,
        user_id=user_id, revision=approval.revision, deployment_id=approval.deployment_id,
        source_pins=ENFORCEMENT_PINS, installer_sha256=approval.installer_sha256,
        initial_budget_sha256=_hash(record)), session=session)
    await db.reading_pass_audit.insert_one(dict(_id=INSTALLATION_ID,
        event="audio_acceptance_budget_installed", user_id=user_id, test_id=policy.TEST_ID,
        maximum_seconds=600, maximum_sessions=2, created_at=record["created_at"]), session=session)
    verify_fence(await fence(), approval)
    verify_runtime(server, approval, user_id, environ)
    return True


async def _readback(server, approval, user_id):
    user = await server.db.users.find_one({"id": user_id, "role": "user"},
        {"_id": 0, "reader_acceptance_budget": 1}) or {}
    receipt = await server.db.reading_pass_acceptance_installations.find_one({"_id": INSTALLATION_ID})
    record = user.get("reader_acceptance_budget")
    _validate_retained(record, receipt, approval, user_id)
    audit = await server.db.reading_pass_audit.find_one({"_id": INSTALLATION_ID})
    expected_audit = dict(event="audio_acceptance_budget_installed", user_id=user_id,
        test_id=policy.TEST_ID, maximum_seconds=600, maximum_sessions=2,
        created_at=record["created_at"])
    if not audit or any(audit.get(k) != v for k, v in expected_audit.items()):
        raise InstallerStop("INSTALLATION_AUDIT_MISMATCH")
    # Do not serialize the private account, selector, receipt or balance.
    return dict(maximum_seconds=600, maximum_sessions=2,
                consumed_seconds=record["consumed_seconds"], sessions_started=record["sessions_started"],
                expires_at=ensure_utc(record["expires_at"]).isoformat())


async def _execute(server, approval, user_id, fence, environ, *, interlock=None):
    verify_runtime(server, approval, user_id, environ)
    verify_fence(await fence(), approval)
    mongo_session = await server.client.start_session()
    async with mongo_session:
        mongo_session.start_transaction(read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern("majority", wtimeout=5000), max_commit_time_ms=5000)
        try:
            installed = await _operation(server, approval, user_id, fence, mongo_session, environ, interlock)
        except Exception:
            try:
                await mongo_session.abort_transaction()
            except Exception:
                raise OutcomeUnknown("ABORT_OUTCOME_UNVERIFIED_DO_NOT_RETRY") from None
            raise InstallerStop("INSTALLATION_STOPPED_NO_RETRY") from None
        try:
            await mongo_session.commit_transaction()  # exactly one attempt
        except Exception:
            raise OutcomeUnknown("COMMIT_OUTCOME_UNVERIFIED_DO_NOT_RETRY") from None
    try:
        result = await _readback(server, approval, user_id)
        if installed and (result["consumed_seconds"] or result["sessions_started"]):
            raise InstallerStop("POST_INSTALL_ACTIVITY")
    except Exception:
        raise OutcomeUnknown("COMMITTED_READBACK_UNVERIFIED_DO_NOT_RETRY") from None
    return dict(status="INSTALLED_VERIFIED" if installed else "EXISTING_MATCHED_READ_ONLY", **result)


async def execute_production(*args, installation_authorized=False, **kwargs):
    """Explicit owner-operated entry, never called by the serving application.

    No credentials, DB connection acquisition, provider mutation or session API.
    The live launcher performs source, private target and provider verification.
    Merely importing or testing this module cannot authorize installation.
    """
    if installation_authorized is not True:
        raise InstallerStop("PRODUCTION_ENTRY_NOT_ENABLED")
    from .open_window_audio_cap_live import run_protected
    return await run_protected(*args, **kwargs)


async def execute_synthetic(server, approval, user_id, fence, environ, *, interlock=None):
    """Only local disposable fixture execution is currently enabled."""
    if (not re.fullmatch(r"acceptance_operator_synthetic_[0-9a-f]{32}", server.db.name)
            or not server.client.nodes
            or any(host != "127.0.0.1" or not 27018 <= port <= 27099 for host, port in server.client.nodes)):
        raise InstallerStop("DISPOSABLE_LOOPBACK_FIXTURE_REQUIRED")
    hello = await server.client.admin.command("hello")
    if hello.get("setName") != "earnalism-uat-rs0" or hello.get("isWritablePrimary") is not True:
        raise InstallerStop("DISPOSABLE_REPLICA_SET_REQUIRED")
    return await _execute(server, approval, user_id, fence, environ, interlock=interlock)
