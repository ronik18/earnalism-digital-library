#!/usr/bin/env python3
"""Seed only rights-safe, non-production fixture identities into the CI Mongo database."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from pymongo import MongoClient


def main() -> None:
    uri = os.environ.get("MONGO_URL", "")
    parsed = urlparse(uri)
    if parsed.hostname != "127.0.0.1" or "earnalism_p0" not in uri:
        raise SystemExit("P0 fixture seeding requires the job-local earnalism_p0 database")
    now = datetime.now(timezone.utc).isoformat()
    db = MongoClient(uri, serverSelectionTimeoutMS=5000).get_database()
    fixtures = [
        {"slug": "dracula", "title": "Dracula", "author": "Bram Stoker", "rights": "public-domain", "availability": "approved"},
        {"slug": "a-ghost-story", "title": "A Ghost Story", "author": "Mark Twain", "rights": "public-domain", "availability": "approved"},
        {"slug": "p0-unavailable-fixture", "title": "Unavailable CI Fixture", "rights": "test-only", "availability": "unavailable"},
    ]
    db.p0_ephemeral_catalog.delete_many({})
    db.p0_ephemeral_catalog.insert_many([{**fixture, "seeded_at": now} for fixture in fixtures])
    db.p0_ephemeral_accounts.delete_many({})
    db.p0_ephemeral_accounts.insert_one({"id": "p0-entitled-reader", "reading_pass_seconds": 1800, "entitlement": "active", "seeded_at": now})
    print("P0 fixture seed: PASS (two public-domain titles, unavailable title, entitled account; job-local only)")


if __name__ == "__main__":
    main()
