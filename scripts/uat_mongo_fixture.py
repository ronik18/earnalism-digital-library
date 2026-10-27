"""Exact per-test MongoDB grants on the disposable authenticated UAT instance."""

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import secrets
import stat
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


PREFIXES = {"rpseg_it_", "rpadmit_it_", "acceptance_cap_synthetic_",
            "acceptance_operator_synthetic_", "inspection_timeout_it_"}


def validate_app_uri(environment):
    if environment.get("ENVIRONMENT", "uat") not in {"uat", "test"}:
        raise ValueError("isolated UAT environment required")
    uri = urlparse(environment.get("MONGODB_URL", ""))
    query = parse_qs(uri.query)
    if (uri.scheme != "mongodb" or uri.hostname != "127.0.0.1"
            or not uri.port or not 27018 <= uri.port <= 27099
            or uri.path != "/earnalism_uat" or "," in uri.netloc
            or not re.fullmatch(r"uat_app_[0-9a-f]{16}", uri.username or "")
            or not re.fullmatch(r"[0-9a-f]{64}", uri.password or "")
            or query != {"authSource": ["admin"], "replicaSet": ["earnalism-uat-rs0"]}):
        raise ValueError("authenticated loopback UAT fixture required")
    return uri


def setup_configuration(environment):
    uri = validate_app_uri(environment)
    path = Path(environment["UAT_MONGO_SETUP_FILE"])
    if not path.is_absolute():
        raise ValueError("private UAT setup file required")
    # Do not follow links or accept shared/world-readable credential files.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError("private UAT setup file required")
        config = json.load(handle)
    if (set(config) != {"port", "principal", "password"} or config["port"] != uri.port
            or not re.fullmatch(r"uat_setup_[0-9a-f]{16}", config["principal"])
            or not re.fullmatch(r"[0-9a-f]{64}", config["password"])):
        raise ValueError("matching disposable UAT setup required")
    return config


CLIENT_DEADLINES_MS = {
    "serverSelectionTimeoutMS": 3000,
    "connectTimeoutMS": 3000,
    "socketTimeoutMS": 30000,
    "waitQueueTimeoutMS": 3000,
}


def bounded_client_options(options):
    """Allow shorter test deadlines, never disabled or extended socket waits."""
    for key, limit in CLIENT_DEADLINES_MS.items():
        value = options.get(key, limit)
        if type(value) is not int or not 0 < value <= limit:
            raise ValueError("bounded disposable MongoDB client deadline required")
    return {**CLIENT_DEADLINES_MS, **options}


@asynccontextmanager
async def isolated_database(prefix, **client_options):
    from motor.motor_asyncio import AsyncIOMotorClient

    if prefix not in PREFIXES:
        raise ValueError("registered UAT namespace prefix required")
    config = setup_configuration(os.environ)
    namespace = prefix + uuid4().hex
    principal, password = "uat_case_" + secrets.token_hex(8), secrets.token_hex(32)
    target = f"mongodb://127.0.0.1:{config['port']}/?replicaSet=earnalism-uat-rs0"
    setup = AsyncIOMotorClient(target, username=config["principal"], password=config["password"],
                               authSource="admin", **bounded_client_options({}))
    client = None
    created = False
    try:
        hello = await setup.admin.command("hello")
        if hello.get("setName") != "earnalism-uat-rs0" or not hello.get("isWritablePrimary"):
            raise ValueError("isolated UAT primary required")
        await setup.admin.command("createUser", principal, pwd=password,
                                  roles=[{"role": "readWrite", "db": namespace}])
        created = True
        client = AsyncIOMotorClient(target, username=principal, password=password, authSource="admin",
                                     **bounded_client_options(client_options))
        yield client, client[namespace]
    finally:
        try:
            if created:
                # Setup cleans even when a test has closed its restricted client.
                try:
                    await setup.drop_database(namespace)
                finally:
                    await setup.admin.command("dropUser", principal)
        finally:
            if client is not None:
                client.close()
            setup.close()
