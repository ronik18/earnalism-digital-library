#!/usr/bin/env python3
"""Create canonical Reading Pass pages through the authenticated admin API.

Dry-run is the default.  No direct database writes are performed by this
operator tool, keeping ingestion and audit behavior inside the application.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def _json_request(url: str, *, token: str = "", method: str = "GET", body: dict | None = None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.environ.get("EARNALISM_API_BASE", "http://127.0.0.1:8000/api"))
    parser.add_argument("--admin-token", default=os.environ.get("EARNALISM_ADMIN_TOKEN", ""))
    parser.add_argument("--slug", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--segmentation-version", default="canonical-html-blocks-v1")
    parser.add_argument("--target-characters", type=int, default=3200)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()

    if (args.apply or args.activate) and not args.admin_token:
        parser.error("--admin-token or EARNALISM_ADMIN_TOKEN is required for writes")
    if args.activate and not args.apply:
        parser.error("--activate requires --apply")

    slugs = list(dict.fromkeys(args.slug))
    if args.all:
        books = _json_request(f"{args.api_base.rstrip('/')}/books")
        slugs.extend(str(book.get("slug") or "") for book in books if book.get("slug"))
        slugs = list(dict.fromkeys(slugs))
    if not slugs:
        parser.error("provide --slug or --all")

    failures = []
    results = []
    for slug in slugs:
        body = {
            "segmentation_version": args.segmentation_version,
            "target_characters": args.target_characters,
            "dry_run": not args.apply,
            "activate": bool(args.activate),
        }
        try:
            result = _json_request(
                f"{args.api_base.rstrip('/')}/admin/reading-pass/books/{slug}/segments",
                token=args.admin_token,
                method="POST",
                body=body,
            )
            results.append(result)
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
            failures.append({"slug": slug, "reason": str(exc)})

    print(json.dumps({"results": results, "failures": failures}, indent=2, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
