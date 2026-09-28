"""Fail-closed scope policy for hosted implementation tasks."""

from __future__ import annotations

import re

PROTECTED_PREFIXES = (".github/", "internal/", ".env", "secrets/")
ALWAYS_SENSITIVE = (
    "payment", "razorpay", "billing", "entitlement", "customer", "user-data",
    "secret", "token", "credential", "deploy", "database", "migration",
)
CATALOGUE_MARKERS = ("catalogue", "catalog", "publication", "publish", "controlled_publications")


def authorized_scope(path: str, brief: str = "", acceptance: str = "") -> bool:
    """Return whether a generic task may retain a change to *path*.

    Ordinary application source (including frontend/backend product files) is
    allowed. Security, deployment, data, and release-control surfaces remain
    denied unless the task explicitly authorizes catalogue work; even then the
    always-sensitive list remains denied.
    """
    normalized = path.replace("\\", "/").lower()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith(PROTECTED_PREFIXES):
        return False
    if any(marker in normalized for marker in ALWAYS_SENSITIVE):
        return False
    if any(marker in normalized for marker in CATALOGUE_MARKERS):
        context = f"{brief} {acceptance}".lower()
        return bool(re.search(r"\b(authori[sz]ed|explicit(?:ly)?|approved)\b[^.\n]*\b(catalog|publication)", context))
    return True


def forbidden_paths(paths: list[str], brief: str = "", acceptance: str = "") -> list[str]:
    return sorted(path for path in paths if not authorized_scope(path, brief, acceptance))
