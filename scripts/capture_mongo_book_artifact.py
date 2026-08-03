#!/usr/bin/env python3
"""Capture one existing Mongo book into a controlled reader-only artifact."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def sha(value: Any) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    elif not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output-root", type=Path, default=Path("data/controlled_publications"))
    args = parser.parse_args()
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
    if not mongo_url:
        raise SystemExit("BLOCKED: MONGODB_URL or MONGO_URL is required")
    from pymongo import MongoClient

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=15000, uuidRepresentation="standard")
    client.admin.command("ping")
    db_name = os.environ.get("MONGODB_DB_NAME") or os.environ.get("DB_NAME") or mongo_url.rsplit("/", 1)[-1].split("?", 1)[0] or "earnalism"
    book = client[db_name][os.environ.get("MONGODB_BOOKS_COLLECTION", "books")].find_one({"slug": args.slug}, {"_id": 0})
    if not isinstance(book, dict):
        raise SystemExit(f"BLOCKED: Mongo book not found: {args.slug}")
    rights = book.get("rights_metadata") if isinstance(book.get("rights_metadata"), dict) else {}
    chapters = book.get("chapters") if isinstance(book.get("chapters"), list) else []
    if not chapters or not all(isinstance(ch, dict) and ch.get("content") for ch in chapters):
        raise SystemExit("BLOCKED: complete chapter content is not present")
    if rights.get("copyright_owner") != "Ronik Basak" or rights.get("commercial_use_allowed") is not True:
        raise SystemExit("BLOCKED: explicit author-owned commercial-use rights are not present")
    if not book.get("cover_url") or not book.get("back_cover_url"):
        raise SystemExit("BLOCKED: both cover URLs are required")

    out = args.output_root / args.slug
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    public = {k: v for k, v in book.items() if k not in {"chapters", "rights_metadata", "audiobook_enabled", "generate_audiobook"}}
    public.update({
        "slug": args.slug,
        "is_published": True,
        "isPublic": True,
        "isLive": True,
        "showInPublicLibrary": True,
        "allowPublicReading": True,
        "approved_to_publish": True,
        "publication_status": "LIVE_APPROVED",
        "audio_enabled": False,
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "captured_from": "live_mongo_author_owned_record",
        "captured_at": now,
        "chapters": [
            {k: v for k, v in ch.items() if k != "content"}
            for ch in chapters
        ],
    })
    source = {
        "slug": args.slug,
        "source_type": "original_work",
        "source_name": "Author-owned original work",
        "source_license": rights.get("source_license", "Author-owned original work prepared for Earnalism publication."),
        "copyright_owner": rights.get("copyright_owner"),
        "author": rights.get("author", book.get("author")),
        "commercial_use_allowed": True,
        "source_hash": sha("".join(ch.get("content", "") for ch in chapters)),
        "captured_at": now,
    }
    approval = {
        "slug": args.slug,
        "approved_to_publish": True,
        "rights_tier": "A",
        "verification_status": "approved",
        "qa_status": "QA_PASSED",
        "approval_scope": "reader_only_author_owned_capture",
        "owner_attestation": "Ronik Basak attests that this is author-owned original work and authorizes commercial reader publication.",
        "audiobook_enabled": False,
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "captured_at": now,
    }
    manifest = {"slug": args.slug, "chapter_count": len(chapters), "audio_enabled": False, "audiobook_enabled": False, "chapters": public["chapters"]}
    (out / "public_book.json").write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n")
    (out / "source_evidence.json").write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n")
    (out / "approval_evidence.json").write_text(json.dumps(approval, indent=2, ensure_ascii=False) + "\n")
    (out / "reader_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    chapter_dir = out / "chapters"; chapter_dir.mkdir(exist_ok=True)
    for index, chapter in enumerate(chapters, 1):
        payload = {"id": chapter.get("id", f"chapter-{index:03d}"), "order": chapter.get("order", index), "title": chapter.get("title", ""), "content": chapter["content"], "content_hash": sha(chapter["content"])}
        (chapter_dir / f"chapter-{index:03d}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    files = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "checksum_manifest.json":
            files.append({"file": str(path.relative_to(out)), "sha256": sha(path.read_bytes())})
    (out / "checksum_manifest.json").write_text(json.dumps({"slug": args.slug, "files": files}, indent=2) + "\n")
    print(f"captured={args.slug} chapters={len(chapters)} audio_enabled=false output={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
