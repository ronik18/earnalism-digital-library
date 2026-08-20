#!/usr/bin/env python3
"""Initialize and verify the launcher-owned local MongoDB replica set."""

from __future__ import annotations

import os
import time

from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError


REPLICA_SET = "earnalism-uat-rs0"
PORT = int(os.environ["UAT_MONGODB_PORT"])


def main() -> None:
    # Bootstrap without a replica-set topology.  Before replSetInitiate there
    # is no set name for PyMongo to discover, so using the final backend URI
    # here would wait for a primary that cannot exist yet.
    client = MongoClient(
        f"mongodb://127.0.0.1:{PORT}/?directConnection=true",
        serverSelectionTimeoutMS=1_500,
        connectTimeoutMS=1_500,
    )
    deadline = time.monotonic() + 45
    initiated = False
    while time.monotonic() < deadline:
        try:
            hello = client.admin.command("hello")
            if hello.get("isWritablePrimary"):
                print(f"mongodb replica set PRIMARY on 127.0.0.1:{PORT}")
                return
            if not hello.get("setName") and not initiated:
                try:
                    client.admin.command(
                        "replSetInitiate",
                        {"_id": REPLICA_SET, "members": [{"_id": 0, "host": f"127.0.0.1:{PORT}"}]},
                    )
                except OperationFailure as error:
                    if error.code not in {23, 93}:  # already initialized / not yet ready
                        raise
                initiated = True
        except (OperationFailure, ServerSelectionTimeoutError):
            # A just-started server either has not accepted connections yet or
            # is still transitioning through replica-set initiation.
            pass
        time.sleep(0.5)
    raise SystemExit("local MongoDB replica set did not reach PRIMARY within 45 seconds")


if __name__ == "__main__":
    main()
