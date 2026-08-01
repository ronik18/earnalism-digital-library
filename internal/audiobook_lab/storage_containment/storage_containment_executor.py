#!/usr/bin/env python3
"""Hash-bound retention-first storage containment executor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import boto3
import cloudinary
import cloudinary.uploader
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError, RequestException
from urllib3.util.retry import Retry
from botocore.config import Config
from botocore.exceptions import ClientError
from boto3.exceptions import S3UploadFailedError


EXPECTED_INVENTORY_SHA256 = (
    "21c9f5c85c56be3779822b90fb31c178db8131f7f39f7d2bdae1d00a5f61b23c"
)
EXPECTED_TARGET_COUNT = 606
FULL_OWNER_TOKEN_REQUIRED = (
    "AUTHORIZE_P0_REMOTE_STORAGE_CONTAINMENT_FOR_UNAPPROVED_AUDIO_OBJECTS."
)
SCOPED_OWNER_TOKEN_REQUIRED = (
    "AUTHORIZE_SPRINT1_SCOPED_STORAGE_CONTAINMENT_AND_DEFER_NONSPRINT_REMOTE_CONTAINMENT."
)
DEFERRED_SPRINT1_SLUGS = {"great-expectations", "jane-eyre"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_inventory(path: Path) -> dict:
    actual = sha256_file(path)
    if actual != EXPECTED_INVENTORY_SHA256:
        raise RuntimeError(
            f"INVENTORY_SHA_MISMATCH expected={EXPECTED_INVENTORY_SHA256} actual={actual}"
        )
    reviewed = os.getenv("REVIEWED_INVENTORY_SHA256")
    if reviewed and reviewed != EXPECTED_INVENTORY_SHA256:
        raise RuntimeError("REVIEWED_INVENTORY_SHA256 does not match the frozen inventory")
    return json.loads(path.read_text())


def reviewed_targets(inventory: dict) -> list[dict]:
    rows = inventory["objects"] + inventory["supporting_assets"]
    return [
        row
        for row in rows
        if row.get("direct_url_bypasses_release_gate")
        and row.get("recommended_action") == "MOVE_TO_PRIVATE_QA_BUCKET"
    ]


def row_slugs(row: dict) -> set[str]:
    slugs = {row.get("slug", "")}
    slugs.update(row.get("associated_slugs") or [])
    return {slug for slug in slugs if slug}


def canonical_active_sprint1_slugs(inventory_path: Path) -> set[str]:
    repo_root = inventory_path.resolve().parents[3]
    publication_root = repo_root / "internal/audiobook_lab/sprint1_publication"
    publication = json.loads(
        (publication_root / "sprint1_publication_matrix.json").read_text()
    )
    final = json.loads(
        (publication_root / "sprint1_final_yes_yes_matrix.json").read_text()
    )
    publication_slugs = {
        row["slug"]
        for row in publication.get("titles", [])
        if row.get("sprint1_audio_target") is True
    }
    final_slugs = {row["slug"] for row in final.get("titles", [])}
    if publication_slugs != final_slugs:
        raise RuntimeError("Sprint1 source matrices disagree on the active slug set")
    if publication_slugs & DEFERRED_SPRINT1_SLUGS:
        raise RuntimeError("Canonical active Sprint1 set includes a deferred title")
    if len(publication_slugs) != 32:
        raise RuntimeError(
            f"ACTIVE_SPRINT1_COUNT_MISMATCH expected=32 actual={len(publication_slugs)}"
        )
    return publication_slugs


def load_scoped_target_ids(
    path: Path, inventory: dict, inventory_path: Path
) -> list[str]:
    document = json.loads(path.read_text())
    if document.get("inventory_sha256") != EXPECTED_INVENTORY_SHA256:
        raise RuntimeError("Scoped target list inventory SHA does not match frozen inventory")
    if document.get("owner_decision") != SCOPED_OWNER_TOKEN_REQUIRED:
        raise RuntimeError("Scoped target list owner decision mismatch")

    active_rows = document.get("active_slugs") or []
    active_slugs = {
        row.get("slug") if isinstance(row, dict) else row
        for row in active_rows
    }
    active_slugs.discard(None)
    if not active_slugs:
        raise RuntimeError("Scoped target list has no active Sprint1 slugs")
    canonical_slugs = canonical_active_sprint1_slugs(inventory_path)
    if active_slugs != canonical_slugs:
        raise RuntimeError("Scoped target list active slugs differ from source matrices")
    deferred_overlap = active_slugs & DEFERRED_SPRINT1_SLUGS
    if deferred_overlap:
        raise RuntimeError(
            "Scoped target list includes deferred slugs: "
            + ",".join(sorted(deferred_overlap))
        )

    selected_rows = document.get("targets") or []
    selected_ids = [row.get("object_id") for row in selected_rows]
    if not selected_ids or any(not object_id for object_id in selected_ids):
        raise RuntimeError("Scoped target list contains an empty target object_id")
    if len(selected_ids) != len(set(selected_ids)):
        raise RuntimeError("Scoped target list contains duplicate object IDs")

    expected_count = document.get("summary", {}).get("executable_target_count")
    if expected_count != len(selected_ids):
        raise RuntimeError(
            f"SCOPED_TARGET_COUNT_MISMATCH expected={expected_count} "
            f"actual={len(selected_ids)}"
        )

    reviewed_by_id = {row["object_id"]: row for row in reviewed_targets(inventory)}
    for selected in selected_rows:
        object_id = selected["object_id"]
        reviewed = reviewed_by_id.get(object_id)
        if not reviewed:
            raise RuntimeError(f"Scoped target is not a reviewed target: {object_id}")
        if reviewed.get("is_current_approved_asset") or selected.get(
            "approved_current_asset"
        ):
            raise RuntimeError(f"Scoped target is a current approved asset: {object_id}")
        if not row_slugs(reviewed).intersection(active_slugs):
            raise RuntimeError(f"Scoped target is outside active Sprint1: {object_id}")
        if row_slugs(reviewed).intersection(DEFERRED_SPRINT1_SLUGS):
            raise RuntimeError(f"Scoped target intersects a deferred title: {object_id}")

    return selected_ids


def select_targets(
    inventory: dict,
    inventory_path: Path,
    target_slug: str,
    target_list_path: str,
) -> list[dict]:
    targets = reviewed_targets(inventory)
    if target_slug and target_list_path:
        raise RuntimeError("target-slug and target-list are mutually exclusive")
    if target_list_path:
        selected_ids = load_scoped_target_ids(
            Path(target_list_path), inventory, inventory_path
        )
        by_id = {row["object_id"]: row for row in targets}
        return [by_id[object_id] for object_id in selected_ids]
    if target_slug:
        targets = [row for row in targets if row.get("slug") == target_slug]
    if target_slug and not targets:
        raise RuntimeError(f"No reviewed containment targets for slug: {target_slug}")
    if not target_slug and len(targets) != EXPECTED_TARGET_COUNT:
        raise RuntimeError(
            f"TARGET_COUNT_MISMATCH expected={EXPECTED_TARGET_COUNT} actual={len(targets)}"
        )
    return targets


def dry_run_summary(inventory: dict, targets: list[dict], args) -> dict:
    protected = [
        row
        for row in inventory["objects"] + inventory["supporting_assets"]
        if row.get("is_current_approved_asset")
    ]
    providers: dict[str, dict] = {}
    for row in targets:
        provider = row["storage_provider"]
        stats = providers.setdefault(provider, {"count": 0, "known_bytes": 0})
        stats["count"] += 1
        stats["known_bytes"] += row.get("byte_size") or 0
    return {
        "mode": "DRY_RUN_ONLY",
        "mutation_performed": False,
        "inventory_sha256": EXPECTED_INVENTORY_SHA256,
        "selection_mode": "SCOPED_TARGET_LIST" if args.target_list else (
            "TARGET_SLUG" if args.target_slug else "FULL_REVIEWED_INVENTORY"
        ),
        "target_slug": args.target_slug or None,
        "target_list": args.target_list or None,
        "shard_count": args.shard_count,
        "shard_index": args.shard_index,
        "target_count": len(targets),
        "known_bytes": sum(row.get("byte_size") or 0 for row in targets),
        "unknown_size_count": sum(row.get("byte_size") is None for row in targets),
        "providers": providers,
        "protected_current_approved_package_objects": len(protected),
        "protected_current_approved_mp3_objects": sum(
            row.get("is_current_approved_asset") for row in inventory["objects"]
        ),
    }


def create_s3_client(prefix: str):
    return boto3.client(
        "s3",
        endpoint_url=require_env(f"{prefix}_S3_ENDPOINT"),
        aws_access_key_id=require_env(f"{prefix}_ACCESS_KEY_ID"),
        aws_secret_access_key=require_env(f"{prefix}_SECRET_ACCESS_KEY"),
        region_name=require_env(f"{prefix}_REGION"),
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


def configure_cloudinary() -> None:
    if os.getenv("CLOUDINARY_URL"):
        cloudinary.config(secure=True)
        return
    cloudinary.config(
        cloud_name=require_env("CLOUDINARY_CLOUD_NAME"),
        api_key=require_env("CLOUDINARY_API_KEY"),
        api_secret=require_env("CLOUDINARY_API_SECRET"),
        secure=True,
    )


def public_probe(session: requests.Session, url: str) -> int:
    response = session.get(
        url,
        headers={"Range": "bytes=0-0"},
        allow_redirects=True,
        stream=True,
        timeout=(20, 60),
    )
    status = response.status_code
    response.close()
    return status


def configure_requests_session() -> requests.Session:
    session = configure_requests_session()
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def cloudinary_public_id_url(row: dict) -> str | None:
    locator = row.get("storage_locator") or {}
    cloud_name = locator.get("cloud_name")
    public_id = locator.get("public_id")
    resource_type = locator.get("resource_type") or "image"
    if not (cloud_name and public_id):
        return None
    return f"https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/{public_id}"


def download_object(session: requests.Session, url: str, destination: Path) -> tuple[int, str]:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        if destination.exists():
            destination.unlink()
        digest = hashlib.sha256()
        byte_count = 0
        try:
            with session.get(url, allow_redirects=True, stream=True, timeout=(20, 180)) as response:
                response.raise_for_status()
                with destination.open("wb") as output:
                    for block in response.iter_content(chunk_size=1024 * 1024):
                        if not block:
                            continue
                        output.write(block)
                        digest.update(block)
                        byte_count += len(block)
            return byte_count, digest.hexdigest()
        except (ChunkedEncodingError, RequestException) as exc:
            last_error = exc
            time.sleep(attempt * 2)
            continue
    raise RuntimeError(f"Download failed for {url}: {last_error}") from last_error


def private_head(client, bucket: str, key: str) -> dict | None:
    try:
        result = client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    return {
        "byte_size": int(result["ContentLength"]),
        "metadata": result.get("Metadata") or {},
        "etag": str(result.get("ETag") or "").strip('"'),
    }


def upload_private(
    client,
    bucket: str,
    key: str,
    local_path: Path,
    row: dict,
    sha256: str,
    byte_size: int,
) -> dict:
    extra = {
        "Metadata": {
            "source-sha256": sha256,
            "source-object-id": row["object_id"],
            "source-provider": row["storage_provider"].lower(),
        }
    }
    if row.get("content_type"):
        extra["ContentType"] = row["content_type"]
    try:
        client.upload_file(str(local_path), bucket, key, ExtraArgs=extra)
    except (ClientError, S3UploadFailedError) as exc:
        message = str(exc)
        code = ""
        if isinstance(exc, ClientError):
            code = str(exc.response.get("Error", {}).get("Code", ""))
            message = str(exc.response.get("Error", {}).get("Message", message))
        if code == "AccessDenied" and "CreateMultipartUpload" in message:
            with local_path.open("rb") as stream:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=stream,
                    Metadata=extra.get("Metadata", {}),
                    ContentType=extra.get("ContentType"),
                )
        else:
            # fallback for S3Transfer wrapped AccessDenied from multipart initiation
            if isinstance(exc, S3UploadFailedError) and "CreateMultipartUpload" in message:
                with local_path.open("rb") as stream:
                    client.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=stream,
                        Metadata=extra.get("Metadata", {}),
                        ContentType=extra.get("ContentType"),
                    )
            else:
                raise
    retained = private_head(client, bucket, key)
    if not retained:
        raise RuntimeError(f"Private copy missing after upload: {row['object_id']}")
    if retained["byte_size"] != byte_size:
        raise RuntimeError(
            f"Private copy size mismatch for {row['object_id']}: "
            f"{retained['byte_size']} != {byte_size}"
        )
    if retained["metadata"].get("source-sha256") != sha256:
        raise RuntimeError(f"Private copy SHA metadata mismatch: {row['object_id']}")
    return retained


def destroy_cloudinary(row: dict) -> dict:
    locator = row["storage_locator"]
    last_result = None
    for attempt in range(1, 4):
        last_result = cloudinary.uploader.destroy(
            locator["public_id"],
            resource_type=locator["resource_type"],
            type=locator.get("delivery_type", "upload"),
            invalidate=True,
        )
        if last_result.get("result") in {"ok", "not found"}:
            return last_result
        if attempt < 3:
            time.sleep(attempt * 3)
    raise RuntimeError(f"Cloudinary destroy failed for {row['object_id']}: {last_result}")


def destroy_b2_source(source_client, row: dict) -> None:
    locator = row["storage_locator"]
    source_client.delete_object(Bucket=locator["bucket"], Key=locator["key"])


def await_inaccessible(session: requests.Session, url: str) -> int:
    delays = (0, 2, 5, 10, 20, 30)
    status = 0
    for delay in delays:
        if delay:
            time.sleep(delay)
        status = public_probe(session, url)
        if status in {403, 404}:
            return status
    raise RuntimeError(f"Public URL still reachable after containment: HTTP {status}")


def append_log(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as output:
        output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def execute(inventory: dict, targets: list[dict], args) -> dict:
    if os.getenv("ALLOW_REMOTE_MUTATION") != "true":
        raise RuntimeError("ALLOW_REMOTE_MUTATION must equal true")
    required_owner_token = (
        SCOPED_OWNER_TOKEN_REQUIRED if args.target_list else FULL_OWNER_TOKEN_REQUIRED
    )
    if os.getenv("OWNER_APPROVAL_TOKEN") != required_owner_token:
        raise RuntimeError("Owner approval token mismatch")
    if os.getenv("B2_PRIVATE_QA_BUCKET_CONFIRMED_PRIVATE") != "true":
        raise RuntimeError("Private QA bucket is not explicitly confirmed private")

    destination_bucket = require_env("B2_PRIVATE_QA_BUCKET")
    destination_client = create_s3_client("B2")
    needs_b2_source = any(row["storage_provider"] == "B2" for row in targets)
    source_client = create_s3_client("B2_SOURCE") if needs_b2_source else None
    destination_client.head_bucket(Bucket=destination_bucket)
    configure_cloudinary()

    log_path = Path(args.mutation_log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("")
    session = requests.Session()
    run_id = f"storage-containment-{uuid.uuid4().hex[:12]}"
    summary = {
        "run_id": run_id,
        "started_at": utc_now(),
        "selection_mode": "SCOPED_TARGET_LIST" if args.target_list else (
            "TARGET_SLUG" if args.target_slug else "FULL_REVIEWED_INVENTORY"
        ),
        "target_slug": args.target_slug or None,
        "target_list": args.target_list or None,
        "shard_count": args.shard_count,
        "shard_index": args.shard_index,
        "target_count": len(targets),
        "retained_private": 0,
        "newly_contained": 0,
        "already_contained": 0,
        "failed": 0,
        "providers": {},
        "mutation_log": str(log_path),
    }

    with tempfile.TemporaryDirectory(prefix="earnalism-storage-containment-") as temp:
        work = Path(temp)
        for index, row in enumerate(targets, 1):
            provider = row["storage_provider"]
            summary["providers"].setdefault(
                provider,
                {"targets": 0, "newly_contained": 0, "already_contained": 0},
            )
            summary["providers"][provider]["targets"] += 1
            filename = Path(unquote(urlparse(row["direct_url"]).path)).name or "object.bin"
            private_key = (
                f"storage-containment/{row['slug']}/{row['object_id']}/{filename}"
            )
            base_record = {
                "run_id": run_id,
                "timestamp": utc_now(),
                "index": index,
                "target_count": len(targets),
                "object_id": row["object_id"],
                "slug": row["slug"],
                "provider": provider,
                "original_url": row["direct_url"],
                "private_bucket": destination_bucket,
                "private_key": private_key,
            }
            try:
                pre_status = public_probe(session, row["direct_url"])
                if pre_status in {403, 404}:
                    retained = private_head(destination_client, destination_bucket, private_key)
                    if not retained:
                        fallback_url = cloudinary_public_id_url(row)
                        if not fallback_url:
                            raise RuntimeError(
                                "Original is inaccessible but reviewed private retention copy is missing"
                            )
                        fallback_status = public_probe(session, fallback_url)
                        if fallback_status not in {200, 206}:
                            raise RuntimeError(
                                "Original is inaccessible but reviewed private retention copy is missing"
                            )

                        local_path = work / f"{row['object_id']}-{filename}"
                        byte_size, sha256 = download_object(
                            session, fallback_url, local_path
                        )
                        expected_size = row.get("byte_size")
                        if expected_size is not None and byte_size != expected_size:
                            raise RuntimeError(
                                f"Downloaded size mismatch: {byte_size} != {expected_size}"
                            )
                        upload_private(
                            destination_client,
                            destination_bucket,
                            private_key,
                            local_path,
                            row,
                            sha256,
                            byte_size,
                        )
                        summary["retained_private"] += 1
                        summary["newly_contained"] += 1
                        summary["providers"][provider]["newly_contained"] += 1

                        if provider == "Cloudinary":
                            destroy_cloudinary(row)
                        elif provider == "B2":
                            if source_client is None:
                                raise RuntimeError("B2 source client was not initialized")
                            destroy_b2_source(source_client, row)
                        else:
                            raise RuntimeError(f"Unsupported provider: {provider}")

                        post_status = await_inaccessible(session, fallback_url)
                        append_log(
                            log_path,
                            {
                                **base_record,
                                "result": "CONTAINED_PRIVATE_COPY_VERIFIED",
                                "pre_http_status": pre_status,
                                "post_http_status": post_status,
                                "byte_size": byte_size,
                                "sha256": sha256,
                            },
                        )
                        local_path.unlink(missing_ok=True)
                        print(
                            json.dumps(
                                {
                                    "progress": f"{index}/{len(targets)}",
                                    "object_id": row["object_id"],
                                    "slug": row["slug"],
                                    "provider": provider,
                                    "result": "CONTAINED",
                                    "post_http_status": post_status,
                                },
                                separators=(",", ":"),
                            ),
                            flush=True,
                        )
                        continue

                        
                    summary["retained_private"] += 1
                    summary["already_contained"] += 1
                    summary["providers"][provider]["already_contained"] += 1
                    append_log(
                        log_path,
                        {
                            **base_record,
                            "result": "ALREADY_CONTAINED_PRIVATE_COPY_VERIFIED",
                            "pre_http_status": pre_status,
                            "post_http_status": pre_status,
                            "byte_size": retained["byte_size"],
                            "sha256": retained["metadata"].get("source-sha256", ""),
                        },
                    )
                    continue
                if pre_status not in {200, 206}:
                    raise RuntimeError(f"Unexpected pre-containment HTTP status: {pre_status}")

                local_path = work / f"{row['object_id']}-{filename}"
                byte_size, sha256 = download_object(
                    session, row["direct_url"], local_path
                )
                expected_size = row.get("byte_size")
                if expected_size is not None and byte_size != expected_size:
                    raise RuntimeError(
                        f"Downloaded size mismatch: {byte_size} != {expected_size}"
                    )
                upload_private(
                    destination_client,
                    destination_bucket,
                    private_key,
                    local_path,
                    row,
                    sha256,
                    byte_size,
                )
                summary["retained_private"] += 1

                if provider == "Cloudinary":
                    destroy_cloudinary(row)
                elif provider == "B2":
                    if source_client is None:
                        raise RuntimeError("B2 source client was not initialized")
                    destroy_b2_source(source_client, row)
                else:
                    raise RuntimeError(f"Unsupported provider: {provider}")

                post_status = await_inaccessible(session, row["direct_url"])
                summary["newly_contained"] += 1
                summary["providers"][provider]["newly_contained"] += 1
                append_log(
                    log_path,
                    {
                        **base_record,
                        "result": "CONTAINED_PRIVATE_COPY_VERIFIED",
                        "pre_http_status": pre_status,
                        "post_http_status": post_status,
                        "byte_size": byte_size,
                        "sha256": sha256,
                    },
                )
                local_path.unlink(missing_ok=True)
                print(
                    json.dumps(
                        {
                            "progress": f"{index}/{len(targets)}",
                            "object_id": row["object_id"],
                            "slug": row["slug"],
                            "provider": provider,
                            "result": "CONTAINED",
                            "post_http_status": post_status,
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )
            except Exception as exc:
                summary["failed"] += 1
                append_log(
                    log_path,
                    {
                        **base_record,
                        "result": "FAILED",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
                raise

    summary["completed_at"] = utc_now()
    return summary


def parse_args():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute-reviewed", action="store_true")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--target-slug", default="")
    parser.add_argument("--target-list", default="")
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--mutation-log", default="/tmp/earnalism-storage-containment.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory_path = Path(args.inventory)
    inventory = load_inventory(inventory_path)
    targets = select_targets(
        inventory, inventory_path, args.target_slug, args.target_list
    )
    if args.shard_count < 1:
        raise RuntimeError("shard-count must be at least 1")
    if not 0 <= args.shard_index < args.shard_count:
        raise RuntimeError("shard-index must be in [0, shard-count)")
    if args.target_slug and args.shard_count != 1:
        raise RuntimeError("Canary target-slug execution cannot be sharded")
    targets = targets[args.shard_index :: args.shard_count]
    if args.dry_run:
        print(json.dumps(dry_run_summary(inventory, targets, args), indent=2))
        return 0
    summary = execute(inventory, targets, args)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        raise
