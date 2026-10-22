#!/usr/bin/env python3
"""Bootstrap a fresh, authenticated loopback UAT replica; never use app URLs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shlex
from uuid import uuid4


DATABASE = "earnalism_uat"
REPLICA_SET = "earnalism-uat-rs0"


def validate_target(environment: dict) -> int:
    if environment.get("ENVIRONMENT") != "uat":
        raise ValueError("UAT environment required")
    if environment.get("DB_NAME", DATABASE) != DATABASE:
        raise ValueError("isolated UAT database required")
    if any(environment.get(key, "127.0.0.1") != "127.0.0.1"
           for key in ("UAT_BACKEND_HOST", "UAT_FRONTEND_HOST")):
        raise ValueError("loopback hosts required")
    port = int(environment["UAT_MONGODB_PORT"])
    if not 27018 <= port <= 27099:
        raise ValueError("isolated UAT MongoDB port required")
    return port


def prepare(environment: dict, output: Path) -> dict:
    from pymongo import MongoClient
    from pymongo.errors import OperationFailure

    port = validate_target(environment)
    target = f"mongodb://127.0.0.1:{port}/?directConnection=true"
    options = dict(serverSelectionTimeoutMS=3000, connectTimeoutMS=3000,
                   socketTimeoutMS=5000)
    # No caller-supplied URI, database, principal, marker or production policy
    # participates in fixture provisioning. Require access control before writes.
    with MongoClient(target, **options) as anonymous:
        hello = anonymous.admin.command("hello")
        if hello.get("setName") != REPLICA_SET or not hello.get("isWritablePrimary"):
            raise ValueError("isolated UAT primary required")
        try:
            anonymous[DATABASE].books.find_one({}, {"_id": 1})
        except OperationFailure as error:
            if error.code != 13:
                raise
        else:
            raise ValueError("UAT MongoDB must enforce authentication")
        setup_user = "uat_setup_" + secrets.token_hex(8)
        setup_password = secrets.token_hex(32)
        # Only the localhost exception on a new disposable instance permits this.
        anonymous.admin.command("createUser", setup_user, pwd=setup_password,
                                roles=[{"role": "root", "db": "admin"}])

    principal = "uat_app_" + secrets.token_hex(8)
    password = secrets.token_hex(32)
    with MongoClient(target, username=setup_user, password=setup_password,
                     authSource="admin", **options) as setup:
        setup.admin.command("createUser", principal, pwd=password,
                            roles=[{"role": "readWrite", "db": DATABASE}])

    markers = [{"uuid": str(uuid4()), "slug": f"uat-startup-guard-{letter}",
                "version": "uat-fixture-v1", "segmentation_version": "uat-fixture-blocks-v1",
                "generation": 0} for letter in ("a", "b")]
    uri = (f"mongodb://{principal}:{password}@127.0.0.1:{port}/{DATABASE}"
           f"?authSource=admin&replicaSet={REPLICA_SET}")
    with MongoClient(uri, **options) as app:
        db = app[DATABASE]
        for marker in markers:
            db.books.insert_one({"id": marker["uuid"], "slug": marker["slug"],
                                 "is_published": False, "status": "draft",
                                 "has_audiobook": False})
            db.reader_segment_manifests.insert_one({
                "book_slug": marker["slug"], "status": "active",
                "version": marker["version"],
                "segmentation_version": marker["segmentation_version"]})

    policy = {"database": DATABASE, "principal": principal,
              "authentication_database": "admin", "markers": markers}
    values = {"UAT_MONGODB_URI": uri, "MONGODB_URL": uri, "DB_NAME": DATABASE,
              "EARNALISM_STARTUP_DATA_GUARD_JSON": json.dumps(policy, separators=(",", ":"))}
    # The setup identity is for the test runner only. Keep it in the disposable
    # Mongo runtime (not uploaded evidence), and remove it during launcher cleanup.
    setup_path = output.with_name("startup-guard-setup.json")
    with open(setup_path, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        json.dump({"port": port, "principal": setup_user, "password": setup_password}, handle)
    values["UAT_MONGO_SETUP_FILE"] = str(setup_path.resolve())
    # Never print connection strings. The backend receives only restricted app
    # credentials; the launcher removes UAT_MONGO_SETUP_FILE from its environment.
    with open(output, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        handle.write("".join(f"export {key}={shlex.quote(value)}\n" for key, value in values.items()))
    return policy


def main() -> None:
    try:
        output = Path(os.environ["UAT_MONGO_FIXTURE_DIR"]) / "startup-guard.env"
        prepare(dict(os.environ), output)
    except Exception:
        raise SystemExit("isolated UAT guard fixture preparation failed") from None
    print("uat-startup-guard-fixture=PREPARED; authenticated loopback only")


if __name__ == "__main__":
    main()
