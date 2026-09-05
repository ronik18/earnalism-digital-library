#!/usr/bin/env python3
"""Reject any P1 UAT runtime that could reach a production dependency."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def local_url(name: str, expected_db: str = "") -> None:
    value = os.environ.get(name, "")
    parsed = urlparse(value)
    if parsed.hostname != "127.0.0.1":
        raise SystemExit(f"{name} must resolve to loopback")
    if expected_db and parsed.path.lstrip("/").split("/", 1)[0] != expected_db:
        raise SystemExit(f"{name} must use the isolated {expected_db} database")


def main() -> None:
    if os.environ.get("ENVIRONMENT") != "uat" or os.environ.get("READING_PASS_V2_ENABLED", "").lower() != "true":
        raise SystemExit("P1 UAT requires ENVIRONMENT=uat and READING_PASS_V2_ENABLED=true")
    local_url("MONGODB_URL", "earnalism_uat")
    local_url("REDIS_URL")
    for name in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET", "STRIPE_SECRET_KEY", "STRIPE_PUBLIC_KEY", "STRIPE_WEBHOOK_SECRET"):
        if os.environ.get(name):
            raise SystemExit(f"{name} must be empty in P1 UAT")
    if not os.environ.get("READING_PASS_TOKEN_SECRET"):
        raise SystemExit("P1 UAT requires a local Reading Pass token secret")
    print("p1-isolated-preflight=PASS")


if __name__ == "__main__":
    main()
