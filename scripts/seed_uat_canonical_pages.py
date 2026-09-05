#!/usr/bin/env python3
"""Activate deterministic local canonical pages for the UAT fixture edition."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API = os.environ["UAT_API_BASE_URL"].rstrip("/")
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def request(path: str, payload: dict, token: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8")
    try:
        with urlopen(Request(f"{API}{path}", data=body, headers=headers), timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise SystemExit(f"UAT canonical-page seed request failed: HTTP {error.code}: {detail}") from error


def main() -> None:
    if not API.startswith("http://127.0.0.1:") or not API.endswith("/api"):
        raise SystemExit("UAT_API_BASE_URL must be a local /api URL")
    login = request("/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    token = login.get("token", "")
    if not token:
        raise SystemExit("UAT canonical-page seed could not obtain an admin token")
    try:
        with urlopen(Request(f"{API}/books"), timeout=30) as response:
            books = json.loads(response.read().decode("utf-8"))
    except (HTTPError, json.JSONDecodeError) as error:
        raise SystemExit("UAT canonical-page seed could not enumerate local books") from error
    slugs = sorted(str(book.get("slug") or "") for book in books if isinstance(book, dict) and book.get("reader_enabled") is True)
    if not slugs:
        raise SystemExit("UAT canonical-page seed found no reader-approved local titles")
    for slug in slugs:
        result = request(
            f"/admin/reading-pass/books/{slug}/segments",
            {
                "segmentation_version": "canonical-page-preview-v1",
                "target_characters": 3200,
                "activate": True,
                "dry_run": False,
            },
            token,
        )
        if not result.get("activated") or int(result.get("total_pages", 0) or 0) < 4:
            raise SystemExit(f"UAT canonical-page seed did not activate a protected page boundary for {slug}")
    print(f"canonical pages active for {len(slugs)} reader-approved titles")


if __name__ == "__main__":
    main()
