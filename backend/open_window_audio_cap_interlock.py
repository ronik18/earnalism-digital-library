"""One DB gate and owner-local readiness socket. No CLI or automatic I/O.

Installer claim and installation share a transaction. Recovery closes that same
document with majority acknowledgement before restart. Whichever write wins,
an installer cannot subsequently commit behind a verified closed gate.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from . import open_window_audio_cap_installer as installer
from .domain.reading_pass import ensure_utc


@dataclass(frozen=True)
class Plan:
    revision: str
    deployment_id: str
    run_id: str
    restore_at: datetime
    supervisor_sha256: str
    database_name: str
    private_nodes_sha256: str

    def validate(self):
        if (not re.fullmatch(r"[0-9a-f]{40}", self.revision)
            or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", self.deployment_id)
            or not re.fullmatch(r"[0-9a-f]{32}", self.run_id)
            or not re.fullmatch(r"[0-9a-f]{64}", self.supervisor_sha256)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", self.database_name)
            or not re.fullmatch(r"[0-9a-f]{64}", self.private_nodes_sha256)
            or not isinstance(self.restore_at, datetime)):
            raise installer.InstallerStop("INTERLOCK_PLAN_INVALID")

    @property
    def digest(self):
        self.validate()
        return installer._hash(self.__dict__)


class Gate:
    def __init__(self, db, client, plan):
        plan.validate()
        if (db.client is not client or client.options.retry_writes is not False
                or db.name != plan.database_name or not client.nodes
                or installer._hash(sorted([list(x) for x in client.nodes])) != plan.private_nodes_sha256):
            raise installer.InstallerStop("INTERLOCK_PRIVATE_CLIENT_NO_RETRIES_REQUIRED")
        self.db, self.client, self.plan = db, client, plan
        self.collection = db.get_collection("reading_pass_acceptance_installations").with_options(
            read_concern=ReadConcern("majority"), write_concern=WriteConcern("majority", wtimeout=5000))
        self.key = installer.INSTALLATION_ID + ":interlock:" + plan.run_id

    async def prepare(self):
        """One separately authorized control-record creation; never automatic."""
        try:
            await self.collection.insert_one(dict(_id=self.key, plan_sha256=self.plan.digest, state="OPEN"))
            await self.require_open()
        except Exception:
            raise installer.OutcomeUnknown("INTERLOCK_SETUP_UNVERIFIED_NO_RETRY") from None

    async def require_open(self):
        try:
            row = await self.collection.find_one({"_id": self.key, "plan_sha256": self.plan.digest})
            if not row or row.get("state") != "OPEN":
                raise ValueError()
        except Exception:
            raise installer.InstallerStop("INTERLOCK_NOT_OPEN") from None

    async def claim(self, session):
        # This write MUST use the same transaction as the account/receipt/audit.
        if session is None or session.in_transaction is not True:
            raise installer.InstallerStop("INSTALLATION_TRANSACTION_REQUIRED")
        result = await self.collection.update_one(
            {"_id": self.key, "plan_sha256": self.plan.digest, "state": "OPEN"},
            {"$set": {"state": "INSTALLED"}}, session=session)
        if result.modified_count != 1:
            raise installer.InstallerStop("INTERLOCK_CLOSED_NO_INSTALLATION")

    async def close(self):
        """One CAS, no retry. A committed close excludes every late claim."""
        try:
            result = await self.collection.update_one(
                {"_id": self.key, "plan_sha256": self.plan.digest, "state": {"$in": ["OPEN", "INSTALLED"]}},
                {"$set": {"state": "CLOSED"}})
            if result.modified_count != 1:
                raise ValueError()
            row = await self.collection.find_one({"_id": self.key, "plan_sha256": self.plan.digest})
            if not row or row.get("state") != "CLOSED":
                raise ValueError()
            return True
        except Exception:
            raise installer.OutcomeUnknown("INTERLOCK_CLOSE_UNVERIFIED_NO_RESTART") from None


def _private_parent(path):
    parent = Path(path).parent
    info = parent.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise installer.InstallerStop("PRIVATE_READINESS_DIRECTORY_REQUIRED")


async def serve_readiness(path, gate, installer_pid):
    """Call only in the independent supervisor, before traffic is stopped."""
    _private_parent(path)
    if installer_pid == os.getpid() or Path(path).exists() or Path(path).is_symlink():
        raise installer.InstallerStop("INDEPENDENT_READINESS_REQUIRED")
    from . import open_window_audio_cap_recovery as recovery
    if hashlib.sha256(Path(recovery.__file__).read_bytes()).hexdigest() != gate.plan.supervisor_sha256:
        raise installer.InstallerStop("SUPERVISOR_SOURCE_MISMATCH")
    await gate.require_open()  # Authenticated DB access, not a supplied ready Boolean.
    async def answer(reader, writer):
        try:
            raw = await asyncio.wait_for(reader.readuntil(b"\n"), 2)
            request = json.loads(raw)
            await gate.require_open()
            remaining = (ensure_utc(gate.plan.restore_at)-installer._now()).total_seconds()
            if (not 0 < remaining <= 300 or request.get("plan") != gate.plan.digest
                    or not re.fullmatch(r"[0-9a-f]{32}", request.get("challenge", ""))):
                raise ValueError()
            response = dict(plan=gate.plan.digest, challenge=request["challenge"],
                supervisor_pid=os.getpid(), installer_pid=installer_pid, state="READY")
            writer.write(json.dumps(response).encode()+b"\n")
            await writer.drain()
        except Exception:
            pass  # No private driver details on socket or logs.
        finally:
            writer.close()
            await writer.wait_closed()
    server = await asyncio.start_unix_server(answer, path=str(path), limit=4096)
    os.chmod(path, 0o600)
    return server


async def require_ready(path, plan, installer_pid=None):
    """Fresh challenge to a private socket; never trust a saved receipt alone."""
    writer = None
    try:
        _private_parent(path)
        info = Path(path).lstat()
        if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError()
        pid = os.getpid() if installer_pid is None else installer_pid
        reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(str(path), limit=4096), 2)
        challenge = secrets.token_hex(16)
        writer.write(json.dumps(dict(plan=plan.digest, challenge=challenge)).encode()+b"\n")
        await writer.drain()
        result = json.loads(await asyncio.wait_for(reader.readuntil(b"\n"), 2))
        if (result.get("challenge") != challenge or result.get("plan") != plan.digest
            or result.get("installer_pid") != pid or result.get("state") != "READY"
            or type(result.get("supervisor_pid")) is not int or result["supervisor_pid"] == pid):
            raise ValueError()
        return True
    except Exception:
        raise installer.InstallerStop("LIVE_SUPERVISOR_NOT_READY") from None
    finally:
        if writer:
            writer.close()
            await writer.wait_closed()
