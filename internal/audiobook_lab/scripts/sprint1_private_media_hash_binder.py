#!/usr/bin/env python3
"""Hash-bind one explicitly selected retained private B2 media object.

Preflight is the default and performs no network calls. Execution requires an
exact preflight plan digest, an explicit authorization environment variable,
and complete private-audio B2 credentials. The script never uploads, publishes,
changes catalog/release state, or reads/writes the paid TTS lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO


DEFAULT_INVENTORY = Path(
    "internal/audiobook_lab/storage_containment/b2_live_audio_cleanup_inventory.json"
)
DEFAULT_EVIDENCE_DIR = Path("internal/audiobook_lab/sprint1_publication/title_runs")
APPROVAL_ENV = "EARNALISM_APPROVE_PRIVATE_MEDIA_HASH_BINDING"
PRIVATE_STORAGE_ENV = {
    "endpoint": ("B2_PRIVATE_AUDIO_S3_ENDPOINT", "B2_PRIVATE_QA_S3_ENDPOINT"),
    "region": ("B2_PRIVATE_AUDIO_REGION", "B2_PRIVATE_QA_REGION"),
    "bucket": ("B2_PRIVATE_AUDIO_BUCKET", "B2_PRIVATE_QA_BUCKET"),
    "access_key_id": (
        "B2_PRIVATE_AUDIO_ACCESS_KEY_ID",
        "B2_PRIVATE_QA_ACCESS_KEY_ID",
    ),
    "secret_access_key": (
        "B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY",
        "B2_PRIVATE_QA_SECRET_ACCESS_KEY",
    ),
}
SHA256_HEX_LENGTH = 64
READ_CHUNK_BYTES = 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(READ_CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )
    os.replace(temporary, path)


def is_sha256(value: str) -> bool:
    return len(value) == SHA256_HEX_LENGTH and all(
        character in "0123456789abcdef" for character in value
    )


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_private_output_dir(repo_root: Path, output_dir: Path) -> list[str]:
    blockers: list[str] = []
    if not output_dir.is_absolute():
        blockers.append("Private output directory must be an absolute path")
        return blockers
    resolved_root = repo_root.resolve()
    resolved_output = output_dir.resolve()
    if is_relative_to(resolved_output, resolved_root):
        blockers.append(
            "Private media output must be outside the repository, including "
            "frontend/public and frontend/build"
        )
    return blockers


def load_candidate(
    evidence: dict[str, Any],
    slug: str,
    candidate_name: str,
    expected_audio_sha256: str,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    if evidence.get("slug") != slug:
        blockers.append("Release evidence slug does not exactly match requested slug")
    candidate = evidence.get(candidate_name)
    if not isinstance(candidate, dict):
        blockers.append(
            f"Release evidence has no top-level candidate object named {candidate_name!r}"
        )
        return {}, blockers
    evidence_hash = str(candidate.get("audio_sha256") or "").strip().lower()
    expected_hash = expected_audio_sha256.strip().lower()
    if not is_sha256(expected_hash):
        blockers.append("--expected-audio-sha256 must be a lowercase SHA-256 digest")
    if not is_sha256(evidence_hash):
        blockers.append(f"{candidate_name}.audio_sha256 is missing or invalid")
    elif expected_hash != evidence_hash:
        blockers.append(
            "Command-line expected audio SHA-256 does not exactly match release evidence"
        )
    source_hash = str(candidate.get("source_sha256") or "").strip().lower()
    if not is_sha256(source_hash):
        blockers.append(f"{candidate_name}.source_sha256 is missing or invalid")
    return candidate, blockers


def select_inventory_object(
    inventory: dict[str, Any],
    slug: str,
    object_key: str,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    rows = inventory.get("object_versions")
    if not isinstance(rows, list):
        return {}, ["Retained-object inventory has no object_versions array"]
    exact = [
        item
        for item in rows
        if isinstance(item, dict) and str(item.get("key") or "") == object_key
    ]
    if len(exact) != 1:
        return {}, [
            f"Explicit object key must match exactly one inventory row; matched {len(exact)}"
        ]
    row = exact[0]
    if row.get("store") != "private_audio":
        blockers.append("Selected object is not in the private_audio store")
    if row.get("classification") != "PRESERVE_REFERENCED_NONLIVE":
        blockers.append(
            "Selected object is not classified PRESERVE_REFERENCED_NONLIVE"
        )
    if row.get("is_latest") is not True or row.get("delete_marker") is not False:
        blockers.append("Selected object is not the current retained object version")
    if f"/{slug}/" not in object_key:
        blockers.append("Selected object key is not path-bound to the requested slug")
    if not str(row.get("bucket") or "").strip():
        blockers.append("Selected inventory row has no bucket")
    if not str(row.get("version_id") or "").strip():
        blockers.append("Selected inventory row has no immutable version_id")
    if int(row.get("size_bytes") or 0) <= 0:
        blockers.append("Selected inventory row has no positive size_bytes")
    return row, blockers


def build_plan(
    *,
    repo_root: Path,
    inventory_path: Path,
    evidence_path: Path,
    slug: str,
    candidate_name: str,
    object_key: str,
    expected_audio_sha256: str,
    private_output_dir: Path,
) -> dict[str, Any]:
    blockers = validate_private_output_dir(repo_root, private_output_dir)
    inventory_raw = inventory_path.read_bytes()
    evidence_raw = evidence_path.read_bytes()
    inventory = json.loads(inventory_raw)
    evidence = json.loads(evidence_raw)
    if not isinstance(inventory, dict):
        raise ValueError(f"Expected JSON object: {inventory_path}")
    if not isinstance(evidence, dict):
        raise ValueError(f"Expected JSON object: {evidence_path}")
    candidate, candidate_blockers = load_candidate(
        evidence,
        slug,
        candidate_name,
        expected_audio_sha256,
    )
    row, inventory_blockers = select_inventory_object(inventory, slug, object_key)
    blockers.extend(candidate_blockers)
    blockers.extend(inventory_blockers)

    expected_hash = str(candidate.get("audio_sha256") or "").strip().lower()
    source_hash = str(candidate.get("source_sha256") or "").strip().lower()
    binding = {
        "slug": slug,
        "title": str(evidence.get("title") or ""),
        "author": str(evidence.get("author") or ""),
        "candidate_name": candidate_name,
        "candidate_status": str(candidate.get("status") or ""),
        "expected_audio_sha256": expected_hash,
        "source_sha256": source_hash,
        "inventory_sha256": sha256_bytes(inventory_raw),
        "release_evidence_sha256": sha256_bytes(evidence_raw),
        "store": str(row.get("store") or ""),
        "bucket": str(row.get("bucket") or ""),
        "key": str(row.get("key") or object_key),
        "version_id": str(row.get("version_id") or ""),
        "inventory_size_bytes": int(row.get("size_bytes") or 0),
        "private_output_dir": str(private_output_dir.resolve()),
    }
    plan_sha256 = sha256_bytes(json_bytes(binding))
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "mode": "PREFLIGHT",
        "status": (
            "READY_FOR_AUTHORIZED_PRIVATE_DOWNLOAD"
            if not blockers
            else "BLOCKED_PREFLIGHT"
        ),
        "binding": binding,
        "plan_sha256": plan_sha256,
        "blockers": sorted(set(blockers)),
        "network_call_performed": False,
        "download_performed": False,
        "upload_performed": False,
        "publication_performed": False,
        "release_gate_mutated": False,
        "paid_tts_lock_read_or_mutated": False,
    }


def env_first(*names: str) -> str:
    return next(
        (
            os.environ.get(name, "").strip()
            for name in names
            if os.environ.get(name, "").strip()
        ),
        "",
    )


def private_storage_config() -> tuple[dict[str, str], list[str]]:
    config = {
        field: env_first(*names)
        for field, names in PRIVATE_STORAGE_ENV.items()
    }
    missing = [
        "/".join(PRIVATE_STORAGE_ENV[field])
        for field, value in config.items()
        if not value
    ]
    return config, missing


def private_s3_client(config: dict[str, str]):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=config["endpoint"].rstrip("/"),
        region_name=config["region"],
        aws_access_key_id=config["access_key_id"],
        aws_secret_access_key=config["secret_access_key"],
        config=Config(
            s3={"addressing_style": "path"},
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


def stream_object_to_file(body: BinaryIO, output: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = body.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        output.write(chunk)
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def download_and_bind(
    plan: dict[str, Any],
    client: Any,
) -> dict[str, Any]:
    binding = plan["binding"]
    output_dir = Path(binding["private_output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    suffix = Path(binding["key"]).suffix.lower()
    if not suffix or len(suffix) > 10:
        suffix = ".bin"
    bound_path = output_dir / (
        f"{binding['slug']}--{binding['candidate_name']}--"
        f"{binding['expected_audio_sha256']}{suffix}"
    )
    temporary = output_dir / f".{bound_path.name}.{os.getpid()}.download"
    actual_hash = ""
    actual_size = 0
    error = ""
    try:
        response = client.get_object(
            Bucket=binding["bucket"],
            Key=binding["key"],
            VersionId=binding["version_id"],
        )
        body = response["Body"]
        try:
            with temporary.open("wb") as handle:
                os.chmod(temporary, 0o600)
                actual_hash, actual_size = stream_object_to_file(body, handle)
        finally:
            body.close()
        hash_match = actual_hash == binding["expected_audio_sha256"]
        size_match = actual_size == binding["inventory_size_bytes"]
        if hash_match and size_match:
            os.replace(temporary, bound_path)
            os.chmod(bound_path, 0o600)
        else:
            temporary.unlink(missing_ok=True)
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        hash_match = False
        size_match = False
        error = f"{type(exc).__name__}: {exc}"

    blockers: list[str] = []
    if error:
        blockers.append(f"PRIVATE_OBJECT_DOWNLOAD_FAILED: {error}")
    else:
        if not hash_match:
            blockers.append("DOWNLOADED_AUDIO_SHA256_MISMATCH")
        if not size_match:
            blockers.append("DOWNLOADED_AUDIO_SIZE_MISMATCH")
    bound = not blockers
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "mode": "EXECUTE",
        "status": "BOUND_EXACT_PRIVATE_CANDIDATE" if bound else "BLOCKED_UNBOUND",
        "plan_sha256": plan["plan_sha256"],
        "binding": binding,
        "actual_audio_sha256": actual_hash,
        "actual_size_bytes": actual_size,
        "hash_match": hash_match,
        "size_match": size_match,
        "bound_private_path": str(bound_path) if bound else "",
        "blockers": blockers,
        "network_call_performed": True,
        "download_performed": not bool(error),
        "upload_performed": False,
        "publication_performed": False,
        "release_gate_mutated": False,
        "paid_tts_lock_read_or_mutated": False,
    }


def exact_execute_command(
    *,
    script_path: Path,
    args: argparse.Namespace,
    plan_sha256: str,
) -> str:
    environment = [
        f"{APPROVAL_ENV}=true",
        'B2_PRIVATE_AUDIO_S3_ENDPOINT="${B2_PRIVATE_AUDIO_S3_ENDPOINT:?required}"',
        'B2_PRIVATE_AUDIO_REGION="${B2_PRIVATE_AUDIO_REGION:?required}"',
        'B2_PRIVATE_AUDIO_BUCKET="${B2_PRIVATE_AUDIO_BUCKET:?required}"',
        'B2_PRIVATE_AUDIO_ACCESS_KEY_ID="${B2_PRIVATE_AUDIO_ACCESS_KEY_ID:?required}"',
        'B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY="${B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY:?required}"',
    ]
    command = [
        "PYTHONDONTWRITEBYTECODE=1",
        *environment,
        "python3",
        shlex.quote(str(script_path.resolve())),
        "--mode",
        "execute",
        "--repo-root",
        shlex.quote(str(args.repo_root.resolve())),
        "--inventory",
        shlex.quote(str(args.inventory.resolve())),
        "--release-evidence",
        shlex.quote(str(args.release_evidence.resolve())),
        "--slug",
        shlex.quote(args.slug),
        "--candidate",
        shlex.quote(args.candidate),
        "--object-key",
        shlex.quote(args.object_key),
        "--expected-audio-sha256",
        shlex.quote(args.expected_audio_sha256),
        "--private-output-dir",
        shlex.quote(str(args.private_output_dir.resolve())),
        "--report",
        shlex.quote(str(args.report.resolve())),
        "--expected-plan-sha256",
        shlex.quote(plan_sha256),
    ]
    return " ".join(command)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "execute"), default="preflight")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--release-evidence", type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--object-key", required=True)
    parser.add_argument("--expected-audio-sha256", required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--expected-plan-sha256", default="")
    args = parser.parse_args(argv)
    args.repo_root = args.repo_root.resolve()
    if not args.inventory.is_absolute():
        args.inventory = args.repo_root / args.inventory
    if args.release_evidence is None:
        args.release_evidence = (
            args.repo_root
            / DEFAULT_EVIDENCE_DIR
            / f"{args.slug}_release_gate_evidence.json"
        )
    elif not args.release_evidence.is_absolute():
        args.release_evidence = args.repo_root / args.release_evidence
    if args.report is None:
        args.report = (
            args.repo_root
            / DEFAULT_EVIDENCE_DIR
            / f"{args.slug}_{args.candidate}_private_media_binding.json"
        )
    elif not args.report.is_absolute():
        args.report = args.repo_root / args.report
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        plan = build_plan(
            repo_root=args.repo_root,
            inventory_path=args.inventory,
            evidence_path=args.release_evidence,
            slug=args.slug,
            candidate_name=args.candidate,
            object_key=args.object_key,
            expected_audio_sha256=args.expected_audio_sha256,
            private_output_dir=args.private_output_dir,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED_PREFLIGHT",
                    "error": f"{type(exc).__name__}: {exc}",
                    "network_call_performed": False,
                },
                sort_keys=True,
            )
        )
        return 2

    plan["next_exact_command"] = exact_execute_command(
        script_path=Path(__file__),
        args=args,
        plan_sha256=plan["plan_sha256"],
    )
    if args.mode == "preflight":
        atomic_write_json(args.report, plan)
        print(
            json.dumps(
                {
                    "status": plan["status"],
                    "plan_sha256": plan["plan_sha256"],
                    "blockers": plan["blockers"],
                    "network_call_performed": False,
                    "next_exact_command": plan["next_exact_command"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0 if not plan["blockers"] else 2

    execution_blockers = list(plan["blockers"])
    if os.environ.get(APPROVAL_ENV) != "true":
        execution_blockers.append(f"{APPROVAL_ENV}=true is required")
    if args.expected_plan_sha256 != plan["plan_sha256"]:
        execution_blockers.append(
            "--expected-plan-sha256 does not match the fresh preflight plan"
        )
    config, missing = private_storage_config()
    if missing:
        execution_blockers.append(
            "Missing private B2 configuration: " + ", ".join(missing)
        )
    if config.get("bucket") and config["bucket"] != plan["binding"]["bucket"]:
        execution_blockers.append(
            "Configured private B2 bucket does not match selected inventory bucket"
        )
    if execution_blockers:
        result = {
            **plan,
            "generated_at": utc_now(),
            "mode": "EXECUTE",
            "status": "BLOCKED_BEFORE_NETWORK",
            "blockers": sorted(set(execution_blockers)),
            "network_call_performed": False,
        }
        atomic_write_json(args.report, result)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "blockers": result["blockers"],
                    "network_call_performed": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2

    result = download_and_bind(plan, private_s3_client(config))
    result["next_exact_command"] = ""
    atomic_write_json(args.report, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "hash_match": result["hash_match"],
                "size_match": result["size_match"],
                "bound_private_path": result["bound_private_path"],
                "blockers": result["blockers"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "BOUND_EXACT_PRIVATE_CANDIDATE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
