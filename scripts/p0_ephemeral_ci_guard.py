#!/usr/bin/env python3
"""Fail closed unless the P0 staging job is completely job-local and test-only."""
from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlparse


def reject(message: str) -> None:
    print(f"P0 ephemeral staging guard: {message}", file=sys.stderr)
    raise SystemExit(2)


def loopback_url(name: str) -> None:
    value = os.environ.get(name, "")
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        reject(f"{name} must be a loopback http URL")


def main() -> None:
    for name in ("P0_FRONTEND_URL", "P0_API_URL"):
        loopback_url(name)
    mongo = os.environ.get("MONGO_URL", "")
    redis = os.environ.get("REDIS_URL", "")
    if not re.match(r"^mongodb://127\.0\.0\.1:27018/", mongo):
        reject("MONGO_URL must name the job-local replica set")
    if not re.match(r"^redis://127\.0\.0\.1:6379(?:/|$)", redis):
        reject("REDIS_URL must name the job-local Redis service")
    payment_key = os.environ.get("RAZORPAY_KEY_ID", "")
    if not re.match(r"^rzp_test_", payment_key) or "live" in payment_key.lower():
        reject("RAZORPAY_KEY_ID must be generated test-only material")
    for name, value in os.environ.items():
        if "URL" in name or "HOST" in name:
            if any(token in value.lower() for token in ("theearnalism.com", "railway.app", "vercel.app")):
                reject(f"{name} names a non-job-local host")
    print("P0 ephemeral staging guard: PASS (loopback frontend/API, job-local Mongo/Redis, test payment key)")
    print("P0 ephemeral staging resources: mongodb=replica-set redis=service payment=test-key")


if __name__ == "__main__":
    main()
