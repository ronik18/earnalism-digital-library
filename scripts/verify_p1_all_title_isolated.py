#!/usr/bin/env python3
"""Exercise the flag-true all-title Reading Pass contract on loopback only.

The report is deliberately metadata-only: it never writes protected text,
tokens, user state, or Redis values to disk.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from redis import Redis


API = os.environ["UAT_API_BASE_URL"].rstrip("/")
REDIS_URL = os.environ["REDIS_URL"]
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def call(method: str, path: str, payload: dict | None = None, token: str = "", headers: dict | None = None):
    request_headers = {"Accept": "application/json", **(headers or {})}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    try:
        with urlopen(Request(f"{API}{path}", data=data, headers=request_headers, method=method), timeout=30) as response:
            return response.status, dict(response.headers.items()), json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raw = error.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"detail": raw[:200]}
        return error.code, dict(error.headers.items()), body


def code(body: dict) -> str:
    detail = body.get("detail", body) if isinstance(body, dict) else {}
    return str(detail.get("code", "")) if isinstance(detail, dict) else ""


def header(headers: dict, name: str) -> str:
    return next((str(value) for key, value in headers.items() if key.lower() == name.lower()), "")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def signup(label: str) -> tuple[str, str]:
    email = f"p1-{label}-{uuid.uuid4().hex[:12]}@example.com"
    status, _, body = call("POST", "/users/signup", {"name": f"P1 {label}", "email": email, "password": "P1-local-only-password"})
    require(status == 200, f"signup {label}: {status}: {body}")
    return str(body["user"]["id"]), str(body["token"])


def cache_inventory(redis: Redis, protected_samples: list[str]) -> dict:
    rows = []
    protected_hits = 0
    for key in redis.scan_iter(count=200):
        raw = redis.get(key) if redis.type(key) == b"string" else b""
        protected_hits += sum(1 for sample in protected_samples if sample.encode("utf-8") in raw)
        rows.append({"key": key.decode("utf-8", "replace"), "type": redis.type(key).decode(), "ttl": redis.ttl(key), "size": len(raw)})
    require(protected_hits == 0, "protected canonical content found in shared Redis")
    return {"key_count": len(rows), "protected_payload_hits": protected_hits, "keys": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(API.startswith("http://127.0.0.1:") and API.endswith("/api"), "P1 validation requires loopback API")
    require(os.environ.get("READING_PASS_V2_ENABLED", "").lower() == "true", "P1 validation requires flag true")
    redis = Redis.from_url(REDIS_URL, socket_connect_timeout=3)
    require(redis.ping() is True, "isolated Redis is unreachable")

    status, _, config = call("GET", "/reading-pass/config")
    require(status == 200 and config.get("enabled") is True and config.get("public_audio_seconds") == 0, "unexpected v2 config")
    status, _, login = call("POST", "/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    require(status == 200, "admin login failed")
    admin = str(login["token"])
    status, _, books = call("GET", "/books")
    require(status == 200, "public book inventory unavailable")
    approved = sorted(
        (book for book in books if book.get("reader_enabled") is True),
        key=lambda book: str(book.get("slug") or ""),
    )
    require(approved, "no reader-approved titles")

    positive_id, positive = signup("positive")
    _, zero = signup("zero")
    blocked_id, blocked = signup("blocked")
    status, _, _ = call("POST", f"/admin/users/{positive_id}/wallet/adjust", {"minutes": 30, "reason": "P1 isolated validation"}, admin)
    require(status == 200, "positive wallet setup failed")
    status, _, _ = call("PATCH", f"/admin/users/{blocked_id}/status", {"status": "blocked"}, admin)
    require(status == 200, "blocked user setup failed")

    cold_before = cache_inventory(redis, [])
    protected_samples: list[str] = []
    active = None
    rows = []
    for book in approved:
        slug, book_id = str(book["slug"]), str(book["id"])
        status, headers, manifest = call("GET", f"/reading-pass/books/{slug}/manifest")
        require(status == 200 and manifest.get("book_slug") == slug and int(manifest.get("total_pages", 0)) >= 4, f"manifest identity/page count failed: {slug}")
        require("public" in header(headers, "Cache-Control").lower(), f"manifest cache header failed: {slug}")
        public_hashes = []
        for page in (1, 2, 3):
            page_status, page_headers, body = call("GET", f"/reading-pass/books/{slug}/pages/{page}")
            require(page_status == 200 and body.get("book_slug") == slug and body.get("page_index") == page and body.get("is_preview") is True, f"public page failed: {slug}/{page}")
            require("public" in header(page_headers, "Cache-Control").lower(), f"public cache header failed: {slug}/{page}")
            public_hashes.append(str(body.get("content_sha256", "")))
        denied, _, denied_body = call("GET", f"/reading-pass/books/{slug}/pages/4")
        require(denied == 401 and code(denied_body) == "AUTH_REQUIRED", f"anonymous page 4 failed: {slug}: status={denied} code={code(denied_body)}")
        denied, _, denied_body = call("GET", f"/reading-pass/books/{slug}/pages/4", token=zero)
        require(denied == 403 and code(denied_body) == "PASS_REQUIRED", f"zero-balance page 4 failed: {slug}")
        denied, _, denied_body = call("GET", f"/reading-pass/books/{slug}/pages/4", token=blocked)
        require(denied == 403 and code(denied_body) == "CONTENT_NOT_AUTHORIZED", f"blocked page 4 failed: {slug}")
        session_payload = {"device_id": "p1-isolated-browser", "device_label": "P1 isolated browser", "content_type": "text", "content_id": slug, "canonical_page_index": 4}
        endpoint = "/reading-pass/sessions/start" if active is None else "/reading-pass/sessions/transfer"
        status, _, active = call("POST", endpoint, session_payload, positive)
        require(status == 200 and active.get("session_id") and active.get("lease_token"), f"positive entitlement failed: {slug}")
        lease_headers = {"X-Reading-Pass-Session": str(active["session_id"]), "X-Reading-Pass-Lease": str(active["lease_token"])}
        status, page_headers, body = call("GET", f"/reading-pass/books/{slug}/pages/4", token=positive, headers=lease_headers)
        require(status == 200 and body.get("book_slug") == slug and body.get("page_index") == 4 and body.get("is_preview") is False, f"protected page failed: {slug}")
        require("private" in header(page_headers, "Cache-Control").lower() and "no-store" in header(page_headers, "Cache-Control").lower(), f"protected cache header failed: {slug}")
        protected_samples.append(str(body.get("content", "")))
        rows.append({"slug": slug, "book_id": book_id, "manifest_version": manifest.get("version"), "total_pages": manifest.get("total_pages"), "public_page_hashes": public_hashes, "protected_page_sha256": body.get("content_sha256")})

    warm_after = cache_inventory(redis, [sample for sample in protected_samples if sample])
    require(active is not None, "no positive entitlement session")
    status, _, body = call("GET", f"/reading-pass/books/{rows[0]['slug']}/pages/4", token=zero, headers={"X-Reading-Pass-Session": str(active["session_id"]), "X-Reading-Pass-Lease": str(active["lease_token"])})
    require(status == 403, "cross-user authorization unexpectedly succeeded")
    status, _, _ = call("POST", "/reading-pass/sessions/end", {"session_id": active["session_id"], "reason": "p1_validation_complete"}, positive)
    require(status == 200, "positive session cleanup failed")
    report = {"schema_version": "earnalism.p1-all-title-isolated.v1", "result": "PASS", "generated_at": int(time.time()), "reader_approved_titles": len(rows), "titles": rows, "cold_cache": cold_before, "warm_cache": warm_after, "public_audio_seconds": config["public_audio_seconds"], "production_mutations": False}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "reader_approved_titles": len(rows), "cold_cache_keys": cold_before["key_count"], "warm_cache_keys": warm_after["key_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
