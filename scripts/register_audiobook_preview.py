#!/usr/bin/env python3
"""Validate or activate a generated Reading Pass audiobook preview via admin API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", required=True)
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--version-id", required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "earnalism.audiobook-preview.v1":
        parser.error("--manifest must use earnalism.audiobook-preview.v1")
    slug = str(manifest.get("book_slug") or "").strip()
    if not slug:
        parser.error("preview manifest is missing book_slug")
    preview_sha = str(manifest.get("preview_sha256") or "").strip().lower()
    payload = {
        "version": args.version or f"sha256-{preview_sha}",
        "duration_seconds": float(manifest["duration_seconds"]),
        "sha256": preview_sha,
        "source_sha256": str(manifest["source_sha256"]).strip().lower(),
        "bytes": int(manifest["preview_bytes"]),
        "store": args.store,
        "bucket": args.bucket,
        "key": args.key,
        "version_id": args.version_id,
        "activate": bool(args.activate),
    }
    url = f"{args.api_base.rstrip('/')}/admin/reading-pass/audiobooks/{slug}/preview"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {args.admin_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Preview registration failed ({exc.code}): {detail}") from exc
    except URLError as exc:
        raise SystemExit(f"Preview registration failed: {exc.reason}") from exc
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
