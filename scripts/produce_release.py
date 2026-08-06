#!/usr/bin/env python3
"""Deterministic release coordinator with two human gates.

This command evaluates a title manifest. Rights, content, artifact, staging,
browser, and production checks are automated inputs and fail closed. The only
human inputs are the reader-render approval and the audiobook model/profile
approval. It never infers legal permission, quality, or deployment success.

The command is provider-free by design: generation and deployment adapters must
write their explicit PASS results into the title manifest before promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


AUTOMATED_CHECKS = (
    "rights",
    "manuscript",
    "reader_artifacts",
    "audio_artifacts",
    "synchronization",
    "checksums",
    "staging",
    "browser",
    "production",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def is_http_url(value: Any) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def pass_result(detail: str) -> dict[str, Any]:
    return {"status": "PASS", "detail": detail}


def block_result(detail: str) -> dict[str, Any]:
    return {"status": "BLOCKED", "detail": detail}


def check_file(root: Path, value: Any, expected_sha256: Any, label: str) -> dict[str, Any]:
    if not value:
        return block_result(f"{label} path is missing")
    path = (root / str(value)).resolve() if not Path(str(value)).is_absolute() else Path(str(value))
    if not path.is_file():
        return block_result(f"{label} does not exist: {path}")
    actual = sha256_file(path)
    expected = str(expected_sha256 or "").lower()
    if len(expected) != 64 or actual != expected:
        return block_result(f"{label} checksum mismatch")
    return pass_result(f"{label} present and checksum verified")


def check_rights(manifest: dict[str, Any]) -> dict[str, Any]:
    rights = manifest.get("rights") or {}
    missing = [
        field
        for field in ("source_url", "source_license", "commercial_use", "territories", "source_sha256")
        if not rights.get(field)
    ]
    if missing:
        return block_result("explicit rights fields missing: " + ", ".join(missing))
    if not is_http_url(rights.get("source_url")):
        return block_result("rights source_url is not an http(s) URL")
    if str(rights.get("commercial_use")).upper() != "APPROVED":
        return block_result("commercial_use must be explicitly APPROVED")
    if not isinstance(rights.get("territories"), list) or not rights["territories"]:
        return block_result("at least one approved territory is required")
    if len(str(rights.get("source_sha256"))) != 64:
        return block_result("source_sha256 must be a SHA-256 digest")
    return pass_result("explicit source and commercial-use rights verified")


def check_human_gate(path: Path | None, slug: str, gate_name: str, expected: dict[str, Any]) -> dict[str, Any]:
    if path is None:
        return {"status": "PENDING", "detail": f"{gate_name} approval packet not supplied"}
    try:
        approval = load_json(path)
    except ValueError as exc:
        return block_result(str(exc))
    if str(approval.get("status", "")).upper() != "APPROVED":
        return block_result(f"{gate_name} approval is not APPROVED")
    if approval.get("slug") != slug:
        return block_result(f"{gate_name} approval slug does not match title")
    for key, value in expected.items():
        if approval.get(key) != value:
            return block_result(f"{gate_name} approval does not match {key}")
    return pass_result(f"{gate_name} approval explicitly recorded")


def evaluate(manifest: dict[str, Any], root: Path, reader_approval: Path | None, audio_approval: Path | None) -> dict[str, Any]:
    slug = str(manifest.get("slug") or "").strip()
    if not slug:
        raise ValueError("manifest.slug is required")
    manuscript = manifest.get("manuscript") or {}
    reader = manifest.get("reader") or {}
    audio = manifest.get("audio") or {}
    automated: dict[str, dict[str, Any]] = {"rights": check_rights(manifest)}
    automated["manuscript"] = check_file(root, manuscript.get("path"), manuscript.get("sha256"), "manuscript")
    automated["reader_artifacts"] = check_file(root, reader.get("preview_path"), reader.get("preview_sha256"), "reader preview")

    for name in AUTOMATED_CHECKS[3:]:
        supplied = (manifest.get("automated_checks") or {}).get(name) or {}
        automated[name] = (
            pass_result(f"{name} check passed")
            if str(supplied.get("status", "")).upper() == "PASS"
            else block_result(f"{name} requires an explicit automated PASS")
        )

    reader_gate = check_human_gate(
        reader_approval,
        slug,
        "reader render",
        {"manuscript_sha256": manuscript.get("sha256"), "preview_sha256": reader.get("preview_sha256")},
    )
    audio_gate = check_human_gate(
        audio_approval,
        slug,
        "audiobook profile",
        {"profile_sha256": audio.get("profile_sha256"), "model": audio.get("model"), "voice": audio.get("voice")},
    )
    automated_pass = all(item["status"] == "PASS" for item in automated.values())
    human_pass = reader_gate["status"] == "PASS" and audio_gate["status"] == "PASS"
    return {
        "slug": slug,
        "human_gates": {"reader_render": reader_gate, "audiobook_profile": audio_gate},
        "automated_checks": automated,
        "release_status": "LIVE" if automated_pass and human_pass else "BLOCKED",
        "next_action": "production verified" if automated_pass and human_pass else "resolve the first BLOCKED or PENDING check",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reader-approval", type=Path)
    parser.add_argument("--audio-profile-approval", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--state-file", type=Path, help="Optional status output; no evidence is written by default")
    args = parser.parse_args(argv)
    try:
        report = evaluate(load_json(args.manifest), args.root.resolve(), args.reader_approval, args.audio_profile_approval)
    except ValueError as exc:
        print(json.dumps({"release_status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    print(rendered)
    if args.state_file:
        args.state_file.parent.mkdir(parents=True, exist_ok=True)
        args.state_file.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["release_status"] == "LIVE" else 1


if __name__ == "__main__":
    sys.exit(main())
