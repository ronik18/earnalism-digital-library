#!/usr/bin/env python3
"""Explicitly move selected books to a non-public draft state."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("slugs", nargs="+", choices=["bn-058", "bn-070"]); args = p.parse_args()
    url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not url: raise SystemExit("BLOCKED: Mongo URL missing")
    from pymongo import MongoClient
    from backend.publication_workflow_adapter import canonical_update, canonical_audit_event
    c = MongoClient(url, serverSelectionTimeoutMS=15000, uuidRepresentation="standard"); c.admin.command("ping")
    db = c[os.environ.get("MONGODB_DB_NAME") or os.environ.get("DB_NAME") or url.rsplit("/",1)[-1].split("?",1)[0] or "earnalism"]
    col = db[os.environ.get("MONGODB_BOOKS_COLLECTION", "books")]
    now = datetime.now(timezone.utc).isoformat(); changed = 0
    for slug in args.slugs:
        before = col.find_one({"slug": slug}, {"_id": 0})
        if not before: raise SystemExit(f"BLOCKED: missing Mongo record: {slug}")
        marker = hashlib.sha256(json.dumps({"slug": slug, "event": "BOOK_EXPLICITLY_DEFERRED_TO_DRAFT"}, sort_keys=True).encode()).hexdigest()
        workflow = canonical_update(before)
        workflow["publication"] = {"state": "DRAFT", "published_at": "", "publication_version": "", "reader_exposed": False, "audio_exposed": False}
        update = {"$set": {"publication_workflow": workflow, "is_published": False, "isPublic": False, "isLive": False, "showInPublicLibrary": False, "allowPublicReading": False, "publication_status": "DRAFT", "publicationStatus": "draft", "readerStatus": "draft", "audio_enabled": False, "audiobook_enabled": False, "generate_audiobook": False}, "$addToSet": {"publication_workflow_audit": {**canonical_audit_event(slug, workflow, "BOOK_EXPLICITLY_DEFERRED_TO_DRAFT"), "event_id": marker}}}
        result = col.update_one({"slug": slug}, update)
        changed += int(result.modified_count)
        after = col.find_one({"slug": slug}, {"_id": 0}) or {}
        if after.get("is_published") is not False or after.get("isPublic") is not False or after.get("isLive") is not False: raise SystemExit(f"BLOCKED: draft verification failed: {slug}")
        print(f"drafted={slug} modified={result.modified_count}")
    print(f"changed={changed}"); return 0
if __name__ == "__main__": raise SystemExit(main())
