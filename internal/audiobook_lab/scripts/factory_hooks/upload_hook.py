#!/usr/bin/env python3
"""Upload approved release-factory audiobook artifacts and verify checksums."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from common import (
    finish,
    has_cloudinary_credentials,
    iso_now,
    parser,
    read_json,
    rel,
    sha256_file,
    upload_cloudinary,
    validation_pass,
    verify_remote_checksum,
    write_json,
)


ARTIFACT_KEYS = {
    "mp3": "final_audio_path",
    "timestamps": "timestamps",
    "vtt": "vtt",
    "chapters": "chapters",
    "meta": "meta",
}


def has_b2_credentials() -> bool:
    return bool(
        os.environ.get("B2_ACCESS_KEY_ID")
        and os.environ.get("B2_SECRET_ACCESS_KEY")
        and os.environ.get("B2_BUCKET")
        and os.environ.get("B2_S3_ENDPOINT")
        and os.environ.get("B2_REGION")
    )


def b2_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        region_name=os.environ["B2_REGION"],
        endpoint_url=os.environ["B2_S3_ENDPOINT"].rstrip("/"),
        aws_access_key_id=os.environ["B2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["B2_SECRET_ACCESS_KEY"],
        config=Config(s3={"addressing_style": "path"}),
    )


def content_type_for_key(key: str) -> str:
    return {
        "mp3": "audio/mpeg",
        "timestamps": "application/json",
        "vtt": "text/vtt",
        "chapters": "application/json",
        "meta": "application/json",
    }.get(key, "application/octet-stream")


def upload_b2(path: Path, *, key: str) -> dict[str, Any]:
    bucket = os.environ["B2_BUCKET"]
    endpoint = os.environ["B2_S3_ENDPOINT"].rstrip("/")
    client = b2_client()
    client.upload_file(
        str(path),
        bucket,
        key,
        ExtraArgs={
            "ContentType": content_type_for_key(key.rsplit(".", 1)[-1] if "." in key else key),
            "CacheControl": "private, max-age=600, stale-while-revalidate=3600" if key.endswith(".mp3") else "private, max-age=3600, stale-while-revalidate=86400",
        },
    )
    return {"secure_url": f"{endpoint}/{bucket}/{key}", "bucket": bucket, "key": key}


def verify_b2_checksum(*, key: str, local_path: Path) -> dict[str, Any]:
    bucket = os.environ["B2_BUCKET"]
    client = b2_client()
    head = client.head_object(Bucket=bucket, Key=key)
    digest = hashlib.sha256()
    obj = client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"]
    try:
        for chunk in iter(lambda: body.read(1024 * 1024), b""):
            digest.update(chunk)
    finally:
        body.close()
    local_hash = sha256_file(local_path)
    remote_hash = digest.hexdigest()
    return {
        "url": f"{os.environ['B2_S3_ENDPOINT'].rstrip('/')}/{bucket}/{key}",
        "status": 200,
        "resolves": True,
        "local_sha256": local_hash,
        "remote_sha256": remote_hash,
        "match": bool(local_hash and remote_hash and local_hash == remote_hash),
        "local_size": local_path.stat().st_size if local_path.exists() else 0,
        "remote_size": int(head.get("ContentLength") or 0),
        "content_type": head.get("ContentType", ""),
    }


def resolve_path(value: str, run_dir: Path) -> Path:
    path = Path(value or "")
    if path.is_absolute():
        return path
    direct = run_dir / path
    if direct.exists():
        return direct
    return Path(__file__).resolve().parents[4] / path


def stage_artifacts(run_dir: Path) -> tuple[dict[str, Path], list[str]]:
    blockers: list[str] = []
    tts = read_json(run_dir / "tts_hook_result.json", {})
    sync = read_json(run_dir / "asr_sync_hook_result.json", {})
    qa = read_json(run_dir / "auto_premium_qa.json", {})
    if qa.get("auto_approval_decision") is not True:
        blockers.append("Pre-upload auto_premium_qa.json is missing or not approved.")
    values = {
        "mp3": tts.get("final_audio_path")
        or (tts.get("artifacts") or {}).get("final_audio_path")
        or (tts.get("updated_fields") or {}).get("final_audio_path"),
        "timestamps": (sync.get("artifacts") or {}).get("timestamps"),
        "vtt": (sync.get("artifacts") or {}).get("vtt"),
        "chapters": (sync.get("artifacts") or {}).get("chapters"),
        "meta": (sync.get("artifacts") or {}).get("meta"),
    }
    paths: dict[str, Path] = {}
    for key, value in values.items():
        if not value:
            blockers.append(f"{key} artifact path is missing.")
            continue
        path = resolve_path(str(value), run_dir)
        if not path.exists() or path.stat().st_size <= 0:
            blockers.append(f"{key} artifact is missing or empty: {value}")
            continue
        paths[key] = path
    return paths, blockers


def main() -> int:
    args = parser().parse_args()
    started = iso_now()
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run or args.slug == "__hook_validation__":
        return validation_pass(
            args,
            "upload",
            started,
            {
                "cloudinary_credentials_detected": has_cloudinary_credentials(),
                "b2_credentials_detected": has_b2_credentials(),
                "storage_backend": "b2_s3" if has_b2_credentials() else "cloudinary_raw" if has_cloudinary_credentials() else "missing",
            },
        )

    paths, blockers = stage_artifacts(run_dir)
    if blockers:
        return finish(
            args,
            "upload",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="upload/checksum",
            blockers=blockers,
            retryable=True,
            artifacts={key: rel(path) for key, path in paths.items()},
        )
    if not has_b2_credentials() and not has_cloudinary_credentials():
        return finish(
            args,
            "upload",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="upload/checksum",
            blockers=["B2/S3 or Cloudinary credentials are required for the factory upload backend."],
            retryable=True,
            metrics={"storage_backend": "missing"},
        )

    uploads: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    urls: dict[str, str] = {}
    storage_backend = "b2_s3" if has_b2_credentials() else "cloudinary_raw"
    for key, path in paths.items():
        if storage_backend == "b2_s3":
            suffix = {"mp3": "mp3", "timestamps": "json", "vtt": "vtt", "chapters": "json", "meta": "json"}[key]
            object_key = f"earnalism/audiobooks/{args.slug}/{args.slug}_{key}_{sha256_file(path)[:12]}.{suffix}"
            upload = upload_b2(path, key=object_key)
            url = upload.get("secure_url") or ""
            check = verify_b2_checksum(key=object_key, local_path=path)
        else:
            upload = upload_cloudinary(
                path,
                folder=f"earnalism/audiobooks/{args.slug}",
                resource_type="raw",
                public_id=f"{args.slug}_{key}_{sha256_file(path)[:12]}",
            )
            url = upload.get("secure_url") or ""
            check = verify_remote_checksum(url, path)
        uploads[key] = upload
        checks[key] = check
        urls[key] = url

    failed = [key for key, check in checks.items() if not check.get("resolves") or not check.get("match") or not check.get("local_size")]
    manifest = {
        "slug": args.slug,
        "uploaded_at": iso_now(),
        "storage_backend": storage_backend,
        "urls": urls,
        "uploads": uploads,
        "checksums": checks,
        "status": "PASS" if not failed else "BLOCKED",
    }
    manifest_path = run_dir / "upload_manifest.json"
    write_json(manifest_path, manifest)
    if failed:
        return finish(
            args,
            "upload",
            started,
            status="BLOCKED",
            ready_for_next_stage=False,
            blocker_category="upload/checksum",
            blockers=[f"Remote checksum/URL verification failed for: {', '.join(failed)}"],
            retryable=True,
            artifacts={"upload_manifest": rel(manifest_path), "urls": urls},
            metrics={"checksums": checks},
        )

    return finish(
        args,
        "upload",
        started,
        status="PASS",
        ready_for_next_stage=True,
        blocker_category="none",
        blockers=[],
        retryable=False,
        artifacts={"upload_manifest": rel(manifest_path), "urls": urls},
        metrics={"checksums": checks, "storage_backend": storage_backend},
        updated_fields={
            "upload_status": "UPLOADED",
            "final_audio_url": urls["mp3"],
            "sidecar_urls": {key: urls[key] for key in ("timestamps", "vtt", "chapters", "meta")},
            "remote_checksums": checks,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
