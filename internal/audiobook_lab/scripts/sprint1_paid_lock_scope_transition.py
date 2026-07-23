#!/usr/bin/env python3
"""Authorize one audited Sprint 1 paid-audio title scope on an idle lock.

This command changes only the persistent allow-listed slug. Paid work must
still acquire and restore the lock through ``sprint1_paid_stage_runner.py``.
It never starts a provider call, uploads media, changes release truth, or
publishes a title.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[3]
CURATION_PATH = ROOT / "backend/data/home_hero_curation.json"


class ScopeTransitionError(RuntimeError):
    """Raised when an idle paid lock cannot be safely re-scoped."""


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScopeTransitionError(f"Unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ScopeTransitionError(f"Expected JSON object: {path}")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(path)


def bool_env(name: str, env: dict[str, str]) -> bool:
    return env.get(name, "").strip().lower() in {"1", "true", "yes"}


def canonical_sprint1_bengali(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    rows = payload.get("books")
    if not isinstance(rows, list):
        active_slugs = payload.get("sprint1_active_slugs")
        if not isinstance(active_slugs, list):
            raise ScopeTransitionError("Canonical curation file has no Sprint 1 active slug list")
        rows = []
        controlled_roots = (
            path.parent / "controlled_publications",
            ROOT / "backend/data/controlled_publications",
            ROOT / "data/controlled_publications",
        )
        for slug_value in active_slugs:
            slug = str(slug_value or "").strip()
            for controlled_root in controlled_roots:
                public_book_path = controlled_root / slug / "public_book.json"
                if public_book_path.is_file():
                    rows.append(read_json(public_book_path))
                    break
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        chapters = row.get("chapters") if isinstance(row.get("chapters"), list) else []
        chapter_language = str(chapters[0].get("language_hint") or "") if chapters else ""
        language = str(row.get("language") or chapter_language).lower()
        if language not in {"ben", "bn", "bengali"}:
            continue
        slug = str(row.get("slug") or "").strip()
        if "reader_enabled" not in row:
            row = {**row, "reader_enabled": row.get("allowPublicReading") is True}
        if slug:
            result[slug] = row
    return result


def validate_transition(
    lock: dict[str, Any],
    *,
    expected_current_slug: str,
    next_slug: str,
    canonical_books: dict[str, dict[str, Any]],
    env: dict[str, str],
) -> dict[str, float]:
    if not bool_env("EARNALISM_APPROVE_PAID_TTS_SCOPE_TRANSITION", env):
        raise ScopeTransitionError("EARNALISM_APPROVE_PAID_TTS_SCOPE_TRANSITION=true is required")
    if not bool_env("EARNALISM_STOP_ON_BUDGET_EXCEEDED", env):
        raise ScopeTransitionError("EARNALISM_STOP_ON_BUDGET_EXCEEDED=true is required")
    if lock.get("status") != "active":
        raise ScopeTransitionError("paid_tts.lock status must be active")
    if lock.get("current_holder") != "none":
        raise ScopeTransitionError("paid_tts.lock is currently held")
    if lock.get("allowed_next_holders") != []:
        raise ScopeTransitionError("paid_tts.lock has a scheduled holder")
    if lock.get("allowed_slugs") != [expected_current_slug]:
        raise ScopeTransitionError(
            f"paid_tts.lock current slug mismatch: expected {expected_current_slug}"
        )
    book = canonical_books.get(next_slug)
    if not book:
        raise ScopeTransitionError(f"Next slug is not a canonical Sprint 1 Bengali title: {next_slug}")
    if book.get("reader_enabled") is not True:
        raise ScopeTransitionError(f"Next slug is not reader-enabled: {next_slug}")
    try:
        campaign_cap = float(env["SPRINT1_TOTAL_AUDIO_BUDGET_USD"])
        per_title_cap = float(env["SPRINT1_MAX_USD_PER_TITLE"])
    except (KeyError, ValueError) as exc:
        raise ScopeTransitionError("Sprint 1 campaign and per-title budget caps are required") from exc
    if campaign_cap <= 0 or per_title_cap <= 0:
        raise ScopeTransitionError("Sprint 1 budget caps must be positive")
    lock_cap = float(lock.get("budget_cap_usd") or 0)
    if campaign_cap > lock_cap:
        raise ScopeTransitionError("Requested campaign cap exceeds the existing paid lock cap")
    if per_title_cap > campaign_cap:
        raise ScopeTransitionError("Per-title cap exceeds the campaign cap")
    return {"campaign_cap_usd": campaign_cap, "per_title_cap_usd": per_title_cap}


def transition(args: argparse.Namespace, env: dict[str, str] | None = None) -> dict[str, Any]:
    process_env = dict(os.environ if env is None else env)
    before = args.lock_path.read_bytes()
    lock = json.loads(before.decode("utf-8"))
    books = canonical_sprint1_bengali(args.curation_path)
    budget = validate_transition(
        lock,
        expected_current_slug=args.expected_current_slug,
        next_slug=args.next_slug,
        canonical_books=books,
        env=process_env,
    )
    book = books[args.next_slug]
    changed_at = iso_now()
    updated = {
        **lock,
        "current_holder": "none",
        "allowed_next_holders": [],
        "approved_scope": args.scope,
        "allowed_slugs": [args.next_slug],
        "requested_slug": args.next_slug,
        "budget_cap_usd": budget["campaign_cap_usd"],
        "per_title_budget_cap_usd": budget["per_title_cap_usd"],
        "scope_transition": {
            "from_slug": args.expected_current_slug,
            "to_slug": args.next_slug,
            "canonical_title": book.get("title"),
            "canonical_author": book.get("author"),
            "owner_authorization": "SPRINT1_BENGALI_END_TO_END_GO_LIVE",
            "changed_at": changed_at,
            "provider_call_performed": False,
            "publication_performed": False,
        },
        "updated_at": changed_at,
    }
    atomic_write_json(args.lock_path, updated)
    after = args.lock_path.read_bytes()
    report = {
        "status": "PASS",
        "changed_at": changed_at,
        "lock_path": str(args.lock_path),
        "from_slug": args.expected_current_slug,
        "to_slug": args.next_slug,
        "canonical_title": book.get("title"),
        "canonical_author": book.get("author"),
        "budget": budget,
        "lock_sha256_before": sha256_bytes(before),
        "lock_sha256_after": sha256_bytes(after),
        "provider_call_performed": False,
        "publication_performed": False,
    }
    atomic_write_json(args.report, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--curation-path", type=Path, default=CURATION_PATH)
    parser.add_argument("--expected-current-slug", required=True)
    parser.add_argument("--next-slug", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = transition(args)
    except (OSError, json.JSONDecodeError, ScopeTransitionError) as exc:
        print(json.dumps({"status": "BLOCKED", "blocker": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
