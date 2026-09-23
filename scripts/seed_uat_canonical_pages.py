#!/usr/bin/env python3
"""Prepare then version-promote deterministic local canonical UAT pages."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reading_pass_segment_matrix import build_matrix


API = ""
ADMIN_EMAIL = ""
ADMIN_PASSWORD = ""


def controlled_reader_release_slugs() -> list[str]:
    """Return the parity-checked local Reader release allowlist.

    The local UAT seeder normally creates immutable segments and promotes an
    active version.  That is useful only when the checked-in release contract
    deliberately permits public Reader titles.  A fully held release must not
    create local publication state merely to make a regression harness pass.
    Require both frontend and backend copies of the controlled-launch contract
    to agree before taking this local-only path.  Do not enumerate ``/api/books``:
    once a public Reader release is enabled, that endpoint correctly requires a
    Vercel-signed proxy assertion and a direct local UAT request must not
    emulate or bypass that production boundary.
    """
    contracts = []
    for relative in ("data/controlled_launch.json", "backend/data/controlled_launch.json"):
        path = ROOT / relative
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"UAT canonical-page seed could not read {relative}") from error
        if not isinstance(value, dict):
            raise SystemExit(f"UAT canonical-page seed found malformed {relative}")
        contracts.append(value)
    if contracts[0] != contracts[1]:
        raise SystemExit("UAT canonical-page seed found divergent controlled-launch contracts")
    contract = contracts[0]
    enabled = contract.get("public_reader_exposure_enabled")
    slugs = contract.get("live_approved_slugs")
    if enabled is False and slugs == []:
        return []
    if enabled is not True or not isinstance(slugs, list):
        raise SystemExit("UAT canonical-page seed found malformed controlled Reader release state")
    normalized = [str(slug).strip().lower() for slug in slugs]
    if not normalized or any(not slug for slug in normalized) or len(set(normalized)) != len(normalized):
        raise SystemExit("UAT canonical-page seed found malformed controlled Reader allowlist")
    return sorted(normalized)


def public_reader_release_is_held() -> bool:
    """Compatibility helper for the all-title public Reader hold contract."""
    return controlled_reader_release_slugs() == []


def request(path: str, payload: dict | None = None, token: str = "") -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    try:
        with urlopen(Request(f"{API}{path}", data=body, headers=headers), timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise SystemExit(f"UAT canonical-page seed request failed: HTTP {error.code}: {detail}") from error


def main() -> None:
    global API, ADMIN_EMAIL, ADMIN_PASSWORD
    API = os.environ.get("UAT_API_BASE_URL", "").rstrip("/")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    if not API.startswith("http://127.0.0.1:") or not API.endswith("/api"):
        raise SystemExit("UAT_API_BASE_URL must be a local /api URL")
    slugs = controlled_reader_release_slugs()
    if not slugs:
        print("canonical pages NOT_APPLICABLE_PUBLIC_RELEASE_HOLD; no admin login or publication mutation attempted")
        return
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        raise SystemExit("UAT canonical-page seed requires local admin credentials when Reader exposure is enabled")
    login = request("/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    token = login.get("token", "")
    if not token:
        raise SystemExit("UAT canonical-page seed could not obtain an admin token")
    matrix = build_matrix(slugs)
    if matrix["result"] != "PASS":
        raise SystemExit("UAT canonical-page matrix has unresolved release truth")
    for row in matrix["rows"]:
        slug = row["slug"]
        target = row["selected_target_characters"]
        result = request(
            f"/admin/reading-pass/books/{slug}/segments",
            {
                "segmentation_version": row["selected_segmentation_version"],
                "target_characters": target,
                "activate": False,
                "dry_run": False,
            },
            token,
        )
        if not result.get("prepared") or int(result.get("total_pages", 0) or 0) < 4:
            raise SystemExit(f"UAT canonical-page seed did not prepare a protected page boundary for {slug}")
        try:
            active = request(f"/admin/reading-pass/books/{slug}/segments/active", token=token)
        except SystemExit as error:
            if "HTTP 404" not in str(error):
                raise
            active = None
        if active:
            promoted = request(
                f"/admin/reading-pass/books/{slug}/segments/promote",
                {
                    "target_segmentation_version": row["selected_segmentation_version"],
                    "expected_active_segmentation_version": active["segmentation_version"],
                    "expected_activation_generation": active["activation_generation"],
                    "operation_id": f"uat-seed-{slug}-{uuid.uuid4()}",
                },
                token,
            )
        else:
            promoted = request(
                f"/admin/reading-pass/books/{slug}/segments/bootstrap",
                {
                    "target_segmentation_version": row["selected_segmentation_version"],
                    "operation_id": f"uat-seed-bootstrap-{slug}-{uuid.uuid4()}",
                },
                token,
            )
        if not promoted.get("activated"):
            raise SystemExit(f"UAT canonical-page seed did not promote a protected page boundary for {slug}")
    print(f"canonical pages active for {len(slugs)} reader-approved titles")


if __name__ == "__main__":
    main()
