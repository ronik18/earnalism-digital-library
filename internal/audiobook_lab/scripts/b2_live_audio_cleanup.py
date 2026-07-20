#!/usr/bin/env python3
"""Inventory and safely remove unused Earnalism audiobook objects from B2.

The script fails closed.  It derives the live allowlist from controlled catalog
truth, preserves the latest version of any non-live object still referenced by
repository evidence, and requires an exact plan digest for version-level
deletion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse


DEFAULT_PREFIX = "earnalism/audiobooks/"
MEDIA_SUFFIXES = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav", ".webm"}
SIDECAR_SUFFIXES = {".json", ".vtt"}
TEXT_SUFFIXES = {
    ".css", ".csv", ".html", ".js", ".json", ".jsonl", ".jsx", ".md", ".mjs",
    ".py", ".sh", ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
}
REFERENCE_ROOTS = (
    "backend/data/controlled_publications",
    "data/controlled_publications",
    "internal/audiobook_lab",
    "internal/earnalism_intelligence",
    "frontend/src",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(json_bytes(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def env_first(*names: str) -> str:
    return next((os.environ.get(name, "").strip() for name in names if os.environ.get(name, "").strip()), "")


def storage_configs() -> list[dict[str, str]]:
    raw = [
        {
            "name": "primary",
            "endpoint": env_first("B2_S3_ENDPOINT", "B2_ENDPOINT").rstrip("/"),
            "region": env_first("B2_REGION"),
            "bucket": env_first("B2_BUCKET", "B2_BUCKET_NAME"),
            "access_key_id": env_first("B2_ACCESS_KEY_ID", "B2_KEY_ID"),
            "secret_access_key": env_first("B2_SECRET_ACCESS_KEY", "B2_APP_KEY"),
        },
        {
            "name": "private_audio",
            "endpoint": env_first("B2_PRIVATE_AUDIO_S3_ENDPOINT", "B2_PRIVATE_QA_S3_ENDPOINT").rstrip("/"),
            "region": env_first("B2_PRIVATE_AUDIO_REGION", "B2_PRIVATE_QA_REGION"),
            "bucket": env_first("B2_PRIVATE_AUDIO_BUCKET", "B2_PRIVATE_QA_BUCKET"),
            "access_key_id": env_first("B2_PRIVATE_AUDIO_ACCESS_KEY_ID", "B2_PRIVATE_QA_ACCESS_KEY_ID"),
            "secret_access_key": env_first("B2_PRIVATE_AUDIO_SECRET_ACCESS_KEY", "B2_PRIVATE_QA_SECRET_ACCESS_KEY"),
        },
    ]
    required = ("endpoint", "region", "bucket", "access_key_id", "secret_access_key")
    configured: list[dict[str, str]] = []
    identities: set[tuple[str, str]] = set()
    for store in raw:
        if not all(store[field] for field in required):
            continue
        identity = (store["endpoint"], store["bucket"])
        if identity in identities:
            continue
        identities.add(identity)
        configured.append(store)
    return configured


def s3_client(store: dict[str, str]):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=store["endpoint"],
        region_name=store["region"],
        aws_access_key_id=store["access_key_id"],
        aws_secret_access_key=store["secret_access_key"],
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5, "mode": "standard"}),
    )


def store_for_url(url: str, stores: list[dict[str, str]]) -> tuple[Optional[dict[str, str]], str]:
    parsed = urlparse(url)
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    for store in stores:
        endpoint_host = urlparse(store["endpoint"]).netloc
        if parsed.netloc == endpoint_host and path_parts and path_parts[0] == store["bucket"]:
            return store, "/".join(path_parts[1:])
        if parsed.netloc == f"{store['bucket']}.{endpoint_host}" and path_parts:
            return store, "/".join(path_parts)
    return None, ""


def load_live_assets(repo_root: Path, stores: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    sys.path.insert(0, str(repo_root))
    from backend.catalog_truth import can_expose_audio, load_controlled_artifact_book

    assets: list[dict[str, Any]] = []
    blockers: list[str] = []
    controlled = repo_root / "backend/data/controlled_publications"
    for path in sorted(controlled.glob("*/public_book.json")):
        slug = path.parent.name
        book = load_controlled_artifact_book(slug, artifact_dir=path.parent)
        if not book:
            continue
        if not can_expose_audio(book):
            continue
        slug = str(book.get("slug") or slug)
        nested = book.get("audiobook") if isinstance(book.get("audiobook"), dict) else {}
        nested_assets = nested.get("assets") if isinstance(nested.get("assets"), dict) else {}
        top_assets = book.get("audiobook_assets") if isinstance(book.get("audiobook_assets"), dict) else {}
        urls = {**nested_assets, **top_assets}
        expected_hashes = nested.get("asset_sha256") if isinstance(nested.get("asset_sha256"), dict) else {}
        if not urls:
            blockers.append(f"{slug}: release-approved audio has no asset URLs")
            continue
        for asset_name, raw_url in sorted(urls.items()):
            url = str(raw_url or "").strip()
            store, key = store_for_url(url, stores)
            if not store or not key:
                blockers.append(f"{slug}/{asset_name}: live URL does not resolve to a configured B2 store")
                continue
            assets.append(
                {
                    "slug": slug,
                    "title": str(book.get("title") or ""),
                    "author": str(book.get("author") or ""),
                    "asset": str(asset_name),
                    "store": store["name"],
                    "bucket": store["bucket"],
                    "key": key,
                    "expected_sha256": str(expected_hashes.get(asset_name) or ""),
                }
            )
    return assets, blockers


def list_versions(client: Any, bucket: str) -> tuple[list[dict[str, Any]], bool, str]:
    records: list[dict[str, Any]] = []
    key_marker = ""
    version_marker = ""
    try:
        while True:
            kwargs: dict[str, Any] = {"Bucket": bucket}
            if key_marker:
                kwargs["KeyMarker"] = key_marker
            if version_marker:
                kwargs["VersionIdMarker"] = version_marker
            page = client.list_object_versions(**kwargs)
            for item in page.get("Versions", []):
                records.append(
                    {
                        "key": item["Key"],
                        "version_id": str(item.get("VersionId") or ""),
                        "is_latest": bool(item.get("IsLatest")),
                        "delete_marker": False,
                        "size_bytes": int(item.get("Size") or 0),
                        "etag": str(item.get("ETag") or "").strip('"'),
                        "last_modified": item.get("LastModified").isoformat() if item.get("LastModified") else "",
                    }
                )
            for item in page.get("DeleteMarkers", []):
                records.append(
                    {
                        "key": item["Key"],
                        "version_id": str(item.get("VersionId") or ""),
                        "is_latest": bool(item.get("IsLatest")),
                        "delete_marker": True,
                        "size_bytes": 0,
                        "etag": "",
                        "last_modified": item.get("LastModified").isoformat() if item.get("LastModified") else "",
                    }
                )
            if not page.get("IsTruncated"):
                break
            key_marker = str(page.get("NextKeyMarker") or "")
            version_marker = str(page.get("NextVersionIdMarker") or "")
            if not key_marker:
                raise RuntimeError("B2 returned a truncated version listing without NextKeyMarker")
        return records, True, ""
    except Exception as exc:
        return [], False, f"{type(exc).__name__}: {exc}"


def reference_map(repo_root: Path, object_keys: set[str]) -> dict[str, list[str]]:
    found: dict[str, set[str]] = defaultdict(set)
    if not object_keys:
        return {}
    chunks = [sorted(object_keys)[index:index + 80] for index in range(0, len(object_keys), 80)]
    patterns = [re.compile("|".join(re.escape(key) for key in chunk)) for chunk in chunks]
    for relative_root in REFERENCE_ROOTS:
        root = repo_root / relative_root
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 20 * 1024 * 1024:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern in patterns:
                for match in pattern.finditer(text):
                    found[match.group(0)].add(str(path.relative_to(repo_root)))
    return {key: sorted(paths) for key, paths in found.items()}


def is_audiobook_scoped(key: str) -> bool:
    lowered = key.lower()
    suffix = Path(lowered).suffix
    package_sidecar = suffix in SIDECAR_SUFFIXES and lowered.startswith(
        ("storage-containment/", "earnalism/audiobooks-polished/")
    )
    return lowered.startswith(DEFAULT_PREFIX) or suffix in MEDIA_SUFFIXES or "audiobook" in lowered or package_sidecar


def hash_remote_object(client: Any, bucket: str, key: str) -> tuple[str, int]:
    response = client.get_object(Bucket=bucket, Key=key)
    digest = hashlib.sha256()
    size = 0
    body = response["Body"]
    try:
        while True:
            chunk = body.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    finally:
        body.close()
    return digest.hexdigest(), size


def build_inventory(repo_root: Path, anonymous_public_stores: set[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    stores = storage_configs()
    blockers: list[str] = []
    if not stores:
        blockers.append("No complete B2 storage configuration is available")
    live_assets, live_blockers = load_live_assets(repo_root, stores)
    blockers.extend(live_blockers)
    if not live_assets:
        blockers.append("Catalog truth produced an empty live-audio allowlist")
    live_by_identity = {(item["bucket"], item["key"]): item for item in live_assets}
    store_runtime: dict[str, tuple[dict[str, str], Any]] = {}
    versions: list[dict[str, Any]] = []
    version_support: dict[str, bool] = {}
    for store in stores:
        client = s3_client(store)
        store_runtime[store["name"]] = (store, client)
        listed, supported, error = list_versions(client, store["bucket"])
        version_support[store["name"]] = supported
        if not supported:
            blockers.append(f"{store['name']}: version-level inventory failed: {error}")
            continue
        for item in listed:
            item.update({"store": store["name"], "bucket": store["bucket"]})
            versions.append(item)

    refs = reference_map(repo_root, {item["key"] for item in versions})
    classified: list[dict[str, Any]] = []
    current_live: dict[tuple[str, str], dict[str, Any]] = {}
    for item in versions:
        identity = (item["bucket"], item["key"])
        row = dict(item)
        row["reference_files"] = refs.get(item["key"], [])
        if identity in live_by_identity:
            row["live_slug"] = live_by_identity[identity]["slug"]
            row["live_asset"] = live_by_identity[identity]["asset"]
            if item["is_latest"] and not item["delete_marker"]:
                row["classification"] = "KEEP_LIVE"
                current_live[identity] = row
            elif item["is_latest"] and item["delete_marker"]:
                row["classification"] = "BLOCKED_LIVE_DELETE_MARKER"
                blockers.append(f"Live key is hidden by a current delete marker: {item['bucket']}/{item['key']}")
            else:
                row["classification"] = "DELETE_CANDIDATE_STALE_VERSION"
        elif not is_audiobook_scoped(item["key"]):
            row["classification"] = "PRESERVE_OUT_OF_SCOPE"
        elif item["store"] in anonymous_public_stores:
            row["classification"] = "DELETE_CANDIDATE_NONLIVE_PUBLIC_ORIGIN"
        elif item["is_latest"] and not item["delete_marker"] and row["reference_files"]:
            row["classification"] = "PRESERVE_REFERENCED_NONLIVE"
        else:
            row["classification"] = "DELETE_CANDIDATE_UNUSED_AUDIOBOOK"
        classified.append(row)

    verified_live: list[dict[str, Any]] = []
    for identity, asset in sorted(live_by_identity.items()):
        current = current_live.get(identity)
        if not current:
            blockers.append(f"Live B2 object missing from current version inventory: {identity[0]}/{identity[1]}")
            continue
        store, client = store_runtime[asset["store"]]
        try:
            actual_hash, actual_size = hash_remote_object(client, store["bucket"], asset["key"])
        except Exception as exc:
            blockers.append(f"Live B2 object could not be hashed: {identity[0]}/{identity[1]}: {type(exc).__name__}")
            continue
        expected = asset.get("expected_sha256") or ""
        hash_match = not expected or expected == actual_hash
        if not hash_match:
            blockers.append(f"Live B2 checksum mismatch: {identity[0]}/{identity[1]}")
        verified_live.append(
            {
                **asset,
                "version_id": current["version_id"],
                "size_bytes": actual_size,
                "sha256": actual_hash,
                "expected_sha256": expected,
                "checksum_status": "MATCH" if expected else "DISCOVERED_AND_BOUND_BY_CURRENT_LIVE_KEY",
            }
        )

    delete_rows = [
        row for row in classified
        if row["classification"].startswith("DELETE_CANDIDATE_")
    ]
    delete_plan = [
        {
            "store": row["store"],
            "bucket": row["bucket"],
            "key": row["key"],
            "version_id": row["version_id"],
            "delete_marker": row["delete_marker"],
            "size_bytes": row["size_bytes"],
            "classification": row["classification"],
        }
        for row in sorted(delete_rows, key=lambda value: (value["store"], value["key"], value["version_id"]))
    ]
    plan_sha256 = sha256_json(
        {
            "delete_plan": delete_plan,
            "live_versions": [
                {"bucket": item["bucket"], "key": item["key"], "version_id": item["version_id"], "sha256": item["sha256"]}
                for item in verified_live
            ],
        }
    )
    counts: dict[str, int] = defaultdict(int)
    for row in classified:
        counts[row["classification"]] += 1
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "mode": "INVENTORY",
        "scope": "configured B2 buckets; deletion limited to versioned audiobook-scoped objects",
        "truth_source": "backend/data/controlled_publications + backend.catalog_truth.can_expose_audio",
        "configured_stores": [{"name": store["name"], "bucket": store["bucket"], "region": store["region"]} for store in stores],
        "anonymous_public_stores": sorted(anonymous_public_stores),
        "version_inventory_supported": version_support,
        "live_title_count": len({item["slug"] for item in live_assets}),
        "live_asset_count": len(live_assets),
        "live_assets": verified_live,
        "classification_counts": dict(sorted(counts.items())),
        "object_versions": sorted(classified, key=lambda value: (value["store"], value["key"], value["version_id"])),
        "delete_plan": delete_plan,
        "delete_plan_sha256": plan_sha256,
        "delete_candidate_version_count": len(delete_plan),
        "delete_candidate_bytes": sum(item["size_bytes"] for item in delete_plan),
        "blockers": sorted(set(blockers)),
        "deletion_authorized_by_inventory": not blockers and bool(delete_plan) and all(version_support.values()),
    }
    runtime = {name: client for name, (_, client) in store_runtime.items()}
    return report, runtime


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# B2 Live Audio Cleanup Inventory",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"- Live titles: **{report['live_title_count']}**",
        f"- Live assets retained: **{report['live_asset_count']}**",
        f"- Deletion candidates: **{report['delete_candidate_version_count']} versions**",
        f"- Candidate bytes: **{report['delete_candidate_bytes']}**",
        f"- Plan SHA-256: `{report['delete_plan_sha256']}`",
        f"- Deletion authorized by inventory: **{str(report['deletion_authorized_by_inventory']).lower()}**",
        "",
        "## Live allowlist",
        "",
    ]
    for item in report["live_assets"]:
        lines.append(
            f"- `{item['slug']}` / `{item['asset']}` — `{item['bucket']}/{item['key']}` "
            f"({item['size_bytes']} bytes, SHA-256 `{item['sha256']}`)"
        )
    lines.extend(["", "## Classification counts", ""])
    for name, count in report["classification_counts"].items():
        lines.append(f"- `{name}`: {count}")
    lines.extend(["", "## Blockers", ""])
    if report["blockers"]:
        lines.extend(f"- {blocker}" for blocker in report["blockers"])
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def execute_deletion(report: dict[str, Any], runtime: dict[str, Any], expected_plan: str) -> dict[str, Any]:
    if os.environ.get("EARNALISM_APPROVE_B2_LIVE_ONLY_CLEANUP") != "true":
        raise RuntimeError("EARNALISM_APPROVE_B2_LIVE_ONLY_CLEANUP=true is required")
    if report["blockers"] or not report["deletion_authorized_by_inventory"]:
        raise RuntimeError("Inventory does not authorize deletion")
    if expected_plan != report["delete_plan_sha256"]:
        raise RuntimeError("Expected plan SHA-256 does not match the fresh inventory")
    deleted: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item in report["delete_plan"]:
        try:
            runtime[item["store"]].delete_object(
                Bucket=item["bucket"], Key=item["key"], VersionId=item["version_id"]
            )
            deleted.append(item)
        except Exception as exc:
            errors.append(
                {"bucket": item["bucket"], "key": item["key"], "version_id": item["version_id"], "error": f"{type(exc).__name__}: {exc}"}
            )
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "mode": "EXECUTE",
        "plan_sha256": report["delete_plan_sha256"],
        "deleted_version_count": len(deleted),
        "deleted_bytes": sum(item["size_bytes"] for item in deleted),
        "deleted": deleted,
        "errors": errors,
        "status": "PASS" if not errors and len(deleted) == len(report["delete_plan"]) else "PARTIAL_OR_FAILED",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--mode", choices=("inventory", "execute"), default="inventory")
    parser.add_argument("--expected-plan-sha256", default="")
    parser.add_argument(
        "--anonymous-public-store",
        action="append",
        default=[],
        help="Configured store name whose origin was independently verified as anonymously reachable",
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--execution-report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    report_path = args.report or repo_root / "internal/audiobook_lab/storage_containment/b2_live_audio_cleanup_inventory.json"
    markdown_path = args.markdown or repo_root / "internal/audiobook_lab/storage_containment/b2_live_audio_cleanup_inventory.md"
    execution_path = args.execution_report or repo_root / "internal/audiobook_lab/storage_containment/b2_live_audio_cleanup_execution.json"
    public_stores = set(args.anonymous_public_store)
    configured_names = {store["name"] for store in storage_configs()}
    unknown_public_stores = sorted(public_stores - configured_names)
    if unknown_public_stores:
        raise RuntimeError(f"Unknown anonymous-public store names: {', '.join(unknown_public_stores)}")
    report, runtime = build_inventory(repo_root, public_stores)
    write_json(report_path, report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown_report(report), encoding="utf-8")
    if args.mode == "inventory":
        print(json.dumps({
            "status": "PASS" if not report["blockers"] else "BLOCKED",
            "live_titles": report["live_title_count"],
            "live_assets": report["live_asset_count"],
            "delete_candidates": report["delete_candidate_version_count"],
            "delete_candidate_bytes": report["delete_candidate_bytes"],
            "delete_plan_sha256": report["delete_plan_sha256"],
            "blocker_count": len(report["blockers"]),
        }, sort_keys=True))
        return 0 if not report["blockers"] else 2
    result = execute_deletion(report, runtime, args.expected_plan_sha256)
    write_json(execution_path, result)
    print(json.dumps({
        "status": result["status"],
        "deleted_versions": result["deleted_version_count"],
        "deleted_bytes": result["deleted_bytes"],
        "error_count": len(result["errors"]),
    }, sort_keys=True))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
