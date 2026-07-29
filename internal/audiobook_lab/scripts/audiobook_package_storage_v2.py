#!/usr/bin/env python3
"""Fail-closed storage operations for immutable Earnalism audiobook packages.

This tool deliberately does not alter controlled-publication truth or release
gates.  It accepts a local, hash-bound storage plan and can:

* preflight independent private production and disaster-recovery B2 stores;
* upload exact package assets with Governance Object Lock retention;
* verify every object through a complete download and SHA-256 comparison;
* replicate production bytes to an independent DR store; and
* report the current plus two prior package generations without deleting them.

The expected plan is an internal build artifact, not a public package manifest:

{
  "schema_version": "audiobook_package_upload_plan.v2",
  "slug": "a-ghost-story",
  "release_descriptor_sha256": "<64 lowercase hex>",
  "immutable_prefix": "v1/prod/sprint1/a-ghost-story/releases/<hash>/",
  "assets": [{
    "asset_id": "chapter-01-segment-01-audio",
    "local_path": "/private/path/segment.mp3",
    "key": "v1/prod/sprint1/a-ghost-story/releases/<hash>/delivery/chapter-01.mp3",
    "sha256": "<64 lowercase hex>",
    "size_bytes": 1234,
    "mime_type": "audio/mpeg"
  }]
}

Every key must be inside the builder-emitted immutable release-descriptor
prefix. Version IDs are produced by storage before the final package version
can be derived. Masters, segment assets, sidecars, and release-manifest objects
are all supported; the tool does not infer purpose from filenames. Credentials
and secret values are never included in reports or exception output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO, Mapping, Optional, Sequence
from urllib.parse import urlparse


PLAN_SCHEMA = "audiobook_package_upload_plan.v2"
RECEIPT_SCHEMA = "audiobook_package_storage_receipt.v1"
PRODUCTION_PREFIX = "v1/prod/sprint1/"
LIFECYCLE_PROTECTED_PREFIX = "v1/prod/"
DEFAULT_RETENTION_DAYS = 365
PRODUCTION_RELEASE_STATUSES = frozenset(
    {
        "RELEASE_CANDIDATE",
        "FINAL_MANIFEST_ONLY",
    }
)
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,119}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

ENV_PREFIXES = {
    "prod": "B2_AUDIOBOOK_PROD_",
    "dr": "B2_AUDIOBOOK_DR_",
}
IDENTITY_ENV_SUFFIXES = {
    "endpoint": "S3_ENDPOINT",
    "region": "REGION",
    "bucket": "BUCKET",
    "account_id": "ACCOUNT_ID",
}
CREDENTIAL_PROFILE_ENV_SUFFIXES = {
    "upload": {
        "access_key_id": "UPLOAD_ACCESS_KEY_ID",
        "secret_access_key": "UPLOAD_SECRET_ACCESS_KEY",
    },
    "retention_admin": {
        "access_key_id": "RETENTION_ADMIN_ACCESS_KEY_ID",
        "secret_access_key": "RETENTION_ADMIN_SECRET_ACCESS_KEY",
    },
}
PRIVATE_QA_ENV = {
    "endpoint": "B2_PRIVATE_QA_S3_ENDPOINT",
    "region": "B2_PRIVATE_QA_REGION",
    "bucket": "B2_PRIVATE_QA_BUCKET",
    "account_id": "B2_PRIVATE_QA_ACCOUNT_ID",
    "access_key_id": "B2_PRIVATE_QA_ACCESS_KEY_ID",
    "secret_access_key": "B2_PRIVATE_QA_SECRET_ACCESS_KEY",
}
PUBLIC_GRANTEE_URIS = {
    "http://acs.amazonaws.com/groups/global/AllUsers",
    "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
}
UNSUPPORTED_CODES = {
    "AccessDenied",
    "InvalidRequest",
    "MethodNotAllowed",
    "NotImplemented",
    "UnsupportedOperation",
    "XNotImplemented",
}
MISSING_CODES = {"404", "NoSuchKey", "NotFound"}
NO_LIFECYCLE_CODES = {"NoSuchLifecycleConfiguration", "NoSuchLifecycle"}


class StorageSafetyError(RuntimeError):
    """An expected, safe-to-report storage invariant failure."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CredentialProfile:
    name: str
    access_key_id: str = field(repr=False)
    secret_access_key: str = field(repr=False)

    def __post_init__(self) -> None:
        if self.name not in {"upload", "retention_admin", "private_qa_legacy"}:
            raise StorageSafetyError("UNKNOWN_CREDENTIAL_PROFILE", self.name)
        if not self.access_key_id or not self.secret_access_key:
            raise StorageSafetyError("INCOMPLETE_CREDENTIAL_PROFILE", self.name)

    def safe_summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "configured": True,
        }


@dataclass(frozen=True)
class StorageConfig:
    role: str
    endpoint: str
    region: str
    bucket: str
    account_id: str = field(repr=False)
    upload_credentials: CredentialProfile = field(repr=False)
    retention_admin_credentials: Optional[CredentialProfile] = field(
        default=None,
        repr=False,
    )
    release_eligible: bool = True
    environment_prefix: str = ""

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise StorageSafetyError("INVALID_STORAGE_ENDPOINT", self.role)
        if not all(
            (
                self.region,
                self.bucket,
                self.upload_credentials,
            )
        ) or (self.release_eligible and not self.account_id):
            raise StorageSafetyError("INCOMPLETE_STORAGE_CONFIG", self.role)
        if self.release_eligible:
            if self.upload_credentials.name != "upload":
                raise StorageSafetyError("UPLOAD_PROFILE_REQUIRED", self.role)
            if (
                self.retention_admin_credentials is None
                or self.retention_admin_credentials.name != "retention_admin"
            ):
                raise StorageSafetyError("RETENTION_ADMIN_PROFILE_REQUIRED", self.role)
            if (
                self.upload_credentials.access_key_id
                == self.retention_admin_credentials.access_key_id
            ):
                raise StorageSafetyError(
                    "CREDENTIAL_PROFILES_NOT_SEPARATE",
                    self.role,
                )
        elif self.upload_credentials.name != "private_qa_legacy":
            raise StorageSafetyError("PRIVATE_QA_LEGACY_PROFILE_REQUIRED", self.role)

    def credential_profile(self, profile_name: str) -> CredentialProfile:
        if profile_name == "upload":
            return self.upload_credentials
        if profile_name == "retention_admin" and self.retention_admin_credentials:
            return self.retention_admin_credentials
        raise StorageSafetyError("CREDENTIAL_PROFILE_NOT_CONFIGURED", profile_name)

    def safe_summary(self) -> dict[str, Any]:
        parsed = urlparse(self.endpoint)
        return {
            "role": self.role,
            "endpoint_host": parsed.hostname or "",
            "region": self.region,
            "bucket": self.bucket,
            "account_identity_declared": bool(self.account_id),
            "account_fingerprint": (
                hashlib.sha256(self.account_id.encode("utf-8")).hexdigest()[:16]
                if self.account_id
                else ""
            ),
            "credential_profiles": {
                "object_io": self.upload_credentials.safe_summary(),
                "retention_preflight": (
                    self.retention_admin_credentials.safe_summary()
                    if self.retention_admin_credentials
                    else {"name": "not_configured", "configured": False}
                ),
            },
            "release_eligible": self.release_eligible,
            "environment_prefix": self.environment_prefix,
        }


@dataclass(frozen=True)
class PlanObject:
    asset_id: str
    local_path: Path
    key: str
    sha256: str
    size_bytes: int
    mime_type: str


@dataclass(frozen=True)
class StoragePlan:
    schema_version: str
    slug: str
    release_descriptor_sha256: str
    immutable_prefix: str
    release_status: str
    objects: tuple[PlanObject, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_values(names: Mapping[str, str]) -> tuple[dict[str, str], list[str]]:
    values = {field_name: os.environ.get(env_name, "").strip() for field_name, env_name in names.items()}
    missing = [field_name for field_name, value in values.items() if not value]
    return values, missing


def config_from_env(role: str, allow_private_qa_staging: bool = False) -> StorageConfig:
    """Load one store without sharing runtime, upload, or admin authority."""

    if role not in ENV_PREFIXES:
        raise StorageSafetyError("UNKNOWN_STORE_ROLE", role)
    prefix = ENV_PREFIXES[role]
    identity_names = {
        field_name: prefix + suffix
        for field_name, suffix in IDENTITY_ENV_SUFFIXES.items()
    }
    identity_values, identity_missing = _env_values(identity_names)
    identity_present_count = len(identity_values) - len(identity_missing)
    if identity_missing and identity_present_count:
        raise StorageSafetyError(
            "PARTIAL_STORAGE_CONFIGURATION",
            f"{role} is missing identity fields: {','.join(sorted(identity_missing))}",
        )
    if identity_missing and role == "prod" and allow_private_qa_staging:
        qa_values, qa_missing = _env_values(PRIVATE_QA_ENV)
        required_qa_missing = [field for field in qa_missing if field != "account_id"]
        if required_qa_missing:
            raise StorageSafetyError(
                "PRIVATE_QA_STAGING_CONFIGURATION_MISSING",
                f"missing fields: {','.join(sorted(required_qa_missing))}",
            )
        return StorageConfig(
            role="private_qa_staging",
            release_eligible=False,
            environment_prefix="B2_PRIVATE_QA_",
            endpoint=qa_values["endpoint"],
            region=qa_values["region"],
            bucket=qa_values["bucket"],
            account_id=qa_values["account_id"],
            upload_credentials=CredentialProfile(
                name="private_qa_legacy",
                access_key_id=qa_values["access_key_id"],
                secret_access_key=qa_values["secret_access_key"],
            ),
        )
    if identity_missing:
        raise StorageSafetyError("STORAGE_CONFIGURATION_MISSING", role)

    profiles: dict[str, CredentialProfile] = {}
    for profile_name, suffixes in CREDENTIAL_PROFILE_ENV_SUFFIXES.items():
        names = {
            field_name: prefix + suffix
            for field_name, suffix in suffixes.items()
        }
        values, missing = _env_values(names)
        if missing:
            code = (
                "UPLOAD_PROFILE_CONFIGURATION_MISSING"
                if profile_name == "upload"
                else "RETENTION_ADMIN_PROFILE_CONFIGURATION_MISSING"
            )
            raise StorageSafetyError(
                code,
                f"{role} is missing fields: {','.join(sorted(missing))}",
            )
        profiles[profile_name] = CredentialProfile(
            name=profile_name,
            access_key_id=values["access_key_id"],
            secret_access_key=values["secret_access_key"],
        )
    return StorageConfig(
        role=role,
        release_eligible=True,
        environment_prefix=prefix,
        endpoint=identity_values["endpoint"],
        region=identity_values["region"],
        bucket=identity_values["bucket"],
        account_id=identity_values["account_id"],
        upload_credentials=profiles["upload"],
        retention_admin_credentials=profiles["retention_admin"],
    )


def validate_independent_stores(prod: StorageConfig, dr: StorageConfig) -> None:
    """Require distinct account credentials, region, endpoint, and bucket."""

    failures: list[str] = []
    if prod.account_id == dr.account_id:
        failures.append("account")
    if (
        prod.upload_credentials.access_key_id
        == dr.upload_credentials.access_key_id
    ):
        failures.append("upload_credentials")
    if (
        prod.retention_admin_credentials
        and dr.retention_admin_credentials
        and prod.retention_admin_credentials.access_key_id
        == dr.retention_admin_credentials.access_key_id
    ):
        failures.append("retention_admin_credentials")
    if prod.region.lower() == dr.region.lower():
        failures.append("region")
    if prod.bucket.lower() == dr.bucket.lower():
        failures.append("bucket")
    prod_host = (urlparse(prod.endpoint).hostname or "").lower()
    dr_host = (urlparse(dr.endpoint).hostname or "").lower()
    if prod_host == dr_host:
        failures.append("endpoint")
    if not prod.release_eligible or not dr.release_eligible:
        failures.append("release_eligibility")
    if failures:
        raise StorageSafetyError("STORES_NOT_INDEPENDENT", ",".join(failures))


def create_s3_client(config: StorageConfig, profile_name: str) -> Any:
    """Create a path-style S3 client. Import boto3 only for real execution."""

    import boto3
    from botocore.config import Config

    credentials = config.credential_profile(profile_name)
    return boto3.client(
        "s3",
        endpoint_url=config.endpoint,
        region_name=config.region,
        aws_access_key_id=credentials.access_key_id,
        aws_secret_access_key=credentials.secret_access_key,
        config=Config(
            s3={"addressing_style": "path"},
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


def _error_code(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict) and error.get("Code"):
            return str(error["Code"])
        metadata = response.get("ResponseMetadata")
        if isinstance(metadata, dict) and metadata.get("HTTPStatusCode"):
            return str(metadata["HTTPStatusCode"])
    return type(exc).__name__


def _safe_cloud_call(client: Any, method: str, **kwargs: Any) -> Any:
    try:
        return getattr(client, method)(**kwargs)
    except StorageSafetyError:
        raise
    except Exception as exc:
        raise StorageSafetyError("CLOUD_OPERATION_FAILED", f"{method}:{_error_code(exc)}") from None


def _optional_evidence_call(client: Any, method: str, **kwargs: Any) -> tuple[str, Any]:
    if not hasattr(client, method):
        return "UNAVAILABLE", None
    try:
        return "AVAILABLE", getattr(client, method)(**kwargs)
    except Exception as exc:
        code = _error_code(exc)
        if code in UNSUPPORTED_CODES:
            return f"UNAVAILABLE_{code}", None
        raise StorageSafetyError("CLOUD_OPERATION_FAILED", f"{method}:{code}") from None


def _lifecycle_prefix(rule: Mapping[str, Any]) -> str:
    if isinstance(rule.get("Filter"), dict):
        rule_filter = rule["Filter"]
        if isinstance(rule_filter.get("And"), dict):
            return str(rule_filter["And"].get("Prefix") or "")
        return str(rule_filter.get("Prefix") or "")
    return str(rule.get("Prefix") or "")


def _prefixes_overlap(left: str, right: str) -> bool:
    left = left.lstrip("/")
    right = right.lstrip("/")
    return not left or not right or left.startswith(right) or right.startswith(left)


def _lifecycle_has_deletion(rule: Mapping[str, Any]) -> bool:
    expiration = rule.get("Expiration")
    if isinstance(expiration, dict) and any(
        key in expiration for key in ("Date", "Days", "ExpiredObjectDeleteMarker")
    ):
        return True
    noncurrent = rule.get("NoncurrentVersionExpiration")
    return isinstance(noncurrent, dict) and any(key in noncurrent for key in ("NoncurrentDays", "NewerNoncurrentVersions"))


def preflight_store(
    upload_client: Any,
    config: StorageConfig,
    retention_admin_client: Any = None,
) -> dict[str, Any]:
    """Validate production invariants or the reduced private-QA contract."""

    if config.release_eligible and retention_admin_client is None:
        raise StorageSafetyError("RETENTION_ADMIN_CLIENT_REQUIRED", config.role)
    bucket_admin_client = (
        retention_admin_client if config.release_eligible else upload_client
    )
    blockers: list[str] = []
    checks: dict[str, Any] = {}
    _safe_cloud_call(upload_client, "head_bucket", Bucket=config.bucket)
    checks["bucket_access"] = "PASS"

    versioning = _safe_cloud_call(
        bucket_admin_client,
        "get_bucket_versioning",
        Bucket=config.bucket,
    )
    checks["versioning"] = str(versioning.get("Status") or "DISABLED")
    if versioning.get("Status") != "Enabled":
        blockers.append("BUCKET_VERSIONING_NOT_ENABLED")

    if config.release_eligible:
        lock_config = _safe_cloud_call(
            bucket_admin_client,
            "get_object_lock_configuration",
            Bucket=config.bucket,
        )
        object_lock = lock_config.get("ObjectLockConfiguration") or {}
        retention = ((object_lock.get("Rule") or {}).get("DefaultRetention") or {})
        lock_mode = str(retention.get("Mode") or "")
        lock_period = int(retention.get("Days") or 0) + int(retention.get("Years") or 0) * 365
        checks["object_lock"] = {
            "enabled": object_lock.get("ObjectLockEnabled") == "Enabled",
            "default_mode": lock_mode,
            "default_retention_days_floor": lock_period,
        }
        if object_lock.get("ObjectLockEnabled") != "Enabled":
            blockers.append("OBJECT_LOCK_NOT_ENABLED")
        if lock_mode != "GOVERNANCE" or lock_period < 1:
            blockers.append("GOVERNANCE_DEFAULT_RETENTION_NOT_CONFIGURED")
    else:
        checks["object_lock"] = {
            "status": "NOT_REQUIRED_FOR_PRIVATE_QA_STAGING",
            "release_eligible": False,
        }

    private_evidence: list[dict[str, Any]] = []
    private_positive = False
    public_detected = False

    status, response = _optional_evidence_call(
        bucket_admin_client,
        "get_public_access_block",
        Bucket=config.bucket,
    )
    if status == "AVAILABLE":
        public_block = response.get("PublicAccessBlockConfiguration") or {}
        values = {
            key: bool(public_block.get(key))
            for key in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
        }
        private_evidence.append({"source": "public_access_block", "status": values})
        private_positive = all(values.values())
    else:
        private_evidence.append({"source": "public_access_block", "status": status})

    status, response = _optional_evidence_call(
        bucket_admin_client,
        "get_bucket_policy_status",
        Bucket=config.bucket,
    )
    if status == "AVAILABLE":
        is_public = bool((response.get("PolicyStatus") or {}).get("IsPublic"))
        private_evidence.append({"source": "bucket_policy_status", "is_public": is_public})
        public_detected = public_detected or is_public
        private_positive = private_positive or not is_public
    else:
        private_evidence.append({"source": "bucket_policy_status", "status": status})

    status, response = _optional_evidence_call(
        bucket_admin_client,
        "get_bucket_acl",
        Bucket=config.bucket,
    )
    if status == "AVAILABLE":
        public_grants = [
            grant
            for grant in response.get("Grants", [])
            if str((grant.get("Grantee") or {}).get("URI") or "") in PUBLIC_GRANTEE_URIS
        ]
        private_evidence.append({"source": "bucket_acl", "public_grant_count": len(public_grants)})
        public_detected = public_detected or bool(public_grants)
        private_positive = private_positive or not public_grants
    else:
        private_evidence.append({"source": "bucket_acl", "status": status})

    checks["private_bucket_evidence"] = private_evidence
    if public_detected:
        blockers.append("BUCKET_IS_PUBLIC")
    elif not private_positive:
        blockers.append("PRIVATE_BUCKET_EVIDENCE_UNAVAILABLE")

    if config.release_eligible:
        try:
            lifecycle = getattr(
                bucket_admin_client,
                "get_bucket_lifecycle_configuration",
            )(Bucket=config.bucket)
        except Exception as exc:
            code = _error_code(exc)
            if code in NO_LIFECYCLE_CODES:
                lifecycle = {"Rules": []}
            else:
                raise StorageSafetyError(
                    "CLOUD_OPERATION_FAILED",
                    f"get_bucket_lifecycle_configuration:{code}",
                ) from None
        deleting_rules = []
        for rule in lifecycle.get("Rules", []):
            if (
                str(rule.get("Status") or "") == "Enabled"
                and _prefixes_overlap(_lifecycle_prefix(rule), LIFECYCLE_PROTECTED_PREFIX)
                and _lifecycle_has_deletion(rule)
            ):
                deleting_rules.append(str(rule.get("ID") or "unnamed"))
        checks["production_lifecycle_deletion_rules"] = deleting_rules
        if deleting_rules:
            blockers.append("PRODUCTION_LIFECYCLE_DELETION_CONFIGURED")
    else:
        checks["production_lifecycle_deletion_rules"] = (
            "NOT_APPLICABLE_TO_PRIVATE_QA_STAGING"
        )

    return {
        "store": config.safe_summary(),
        "profiles_used": {
            "object_io": config.upload_credentials.name,
            "retention_preflight": (
                config.retention_admin_credentials.name
                if config.retention_admin_credentials
                else "not_configured"
            ),
        },
        "checks": checks,
        "blockers": blockers,
        "passed": not blockers,
        "release_eligible": config.release_eligible and not blockers,
    }


def _validate_hash(value: Any, field_name: str) -> str:
    text = str(value or "")
    if not SHA256_RE.fullmatch(text):
        raise StorageSafetyError("INVALID_PLAN", f"{field_name} must be lowercase SHA-256")
    return text


def hash_local_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def immutable_release_prefix(slug: str, release_descriptor_sha256: str) -> str:
    """Mirror backend.audiobook_packages without requiring backend imports."""

    if not SLUG_RE.fullmatch(slug):
        raise StorageSafetyError("INVALID_PLAN", "invalid slug")
    descriptor = _validate_hash(
        release_descriptor_sha256,
        "release_descriptor_sha256",
    )
    return f"{PRODUCTION_PREFIX}{slug}/releases/{descriptor}/"


def require_production_plan_status(
    config: StorageConfig,
    plan: StoragePlan,
) -> None:
    if (
        config.release_eligible
        and plan.release_status not in PRODUCTION_RELEASE_STATUSES
    ):
        raise StorageSafetyError(
            "PRODUCTION_PLAN_STATUS_NOT_ALLOWED",
            plan.release_status,
        )


def load_storage_plan(path: Path, verify_local_files: bool = True) -> StoragePlan:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageSafetyError("INVALID_PLAN", type(exc).__name__) from None
    if not isinstance(raw, dict):
        raise StorageSafetyError("INVALID_PLAN", "root must be an object")
    if raw.get("schema_version") != PLAN_SCHEMA:
        raise StorageSafetyError("INVALID_PLAN", "unexpected schema_version")
    slug = str(raw.get("slug") or "")
    if not SLUG_RE.fullmatch(slug):
        raise StorageSafetyError("INVALID_PLAN", "invalid slug")
    release_descriptor_sha256 = _validate_hash(
        raw.get("release_descriptor_sha256"),
        "release_descriptor_sha256",
    )
    expected_prefix = immutable_release_prefix(slug, release_descriptor_sha256)
    immutable_prefix = str(raw.get("immutable_prefix") or "")
    if immutable_prefix != expected_prefix:
        raise StorageSafetyError("INVALID_PLAN", "immutable_prefix is not canonical")
    release_status = str(raw.get("release_status") or "")
    if not release_status or len(release_status) > 80:
        raise StorageSafetyError("INVALID_PLAN", "release_status is required")
    raw_objects = raw.get("assets")
    if not isinstance(raw_objects, list) or not raw_objects:
        raise StorageSafetyError("INVALID_PLAN", "assets must be a non-empty array")

    objects: list[PlanObject] = []
    seen_keys: set[str] = set()
    for index, item in enumerate(raw_objects):
        if not isinstance(item, dict):
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}] must be an object")
        asset_id = str(item.get("asset_id") or "")
        if not IDENTIFIER_RE.fullmatch(asset_id):
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}].asset_id is invalid")
        local_path_text = str(item.get("local_path") or "")
        if not local_path_text:
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}].local_path is required")
        local_path = Path(local_path_text).expanduser()
        if not local_path.is_absolute():
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}].local_path must be absolute")
        expected_sha = _validate_hash(item.get("sha256"), f"objects[{index}].sha256")
        try:
            expected_size = int(item.get("size_bytes"))
        except (TypeError, ValueError):
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}].size_bytes is invalid") from None
        if expected_size < 1:
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}].size_bytes must be positive")
        mime_type = str(item.get("mime_type") or "").strip()
        if not mime_type or len(mime_type) > 120 or "\n" in mime_type or "\r" in mime_type:
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}].mime_type is invalid")
        key = str(item.get("key") or "")
        if (
            not key.startswith(immutable_prefix)
            or key.endswith("/")
            or key.startswith("/")
            or "\\" in key
            or any(part in {"", ".", ".."} for part in key.split("/"))
            or len(key) > 1024
        ):
            raise StorageSafetyError("INVALID_PLAN", f"objects[{index}].key is outside immutable package prefix")
        if key in seen_keys:
            raise StorageSafetyError("INVALID_PLAN", f"duplicate key for objects[{index}]")
        seen_keys.add(key)
        if verify_local_files:
            if not local_path.is_file():
                raise StorageSafetyError("LOCAL_ASSET_MISSING", f"objects[{index}]")
            actual_sha, actual_size = hash_local_file(local_path)
            if actual_sha != expected_sha or actual_size != expected_size:
                raise StorageSafetyError("LOCAL_ASSET_HASH_OR_SIZE_MISMATCH", f"objects[{index}]")
        objects.append(
            PlanObject(
                asset_id=asset_id,
                local_path=local_path,
                key=key,
                sha256=expected_sha,
                size_bytes=expected_size,
                mime_type=mime_type,
            )
        )
    return StoragePlan(
        schema_version=PLAN_SCHEMA,
        slug=slug,
        release_descriptor_sha256=release_descriptor_sha256,
        immutable_prefix=immutable_prefix,
        release_status=release_status,
        objects=tuple(objects),
    )


def load_storage_receipt(
    path: Path,
    plan: StoragePlan,
    expected_role: str,
    expected_store: Optional[StorageConfig] = None,
) -> dict[str, dict[str, Any]]:
    """Validate a receipt and return exact asset records keyed by asset ID."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StorageSafetyError("INVALID_STORAGE_RECEIPT", type(exc).__name__) from None
    if not isinstance(raw, dict) or raw.get("receipt_schema") != RECEIPT_SCHEMA:
        raise StorageSafetyError("INVALID_STORAGE_RECEIPT", "unexpected receipt schema")
    if raw.get("receipt_role") != expected_role:
        raise StorageSafetyError("INVALID_STORAGE_RECEIPT", "unexpected receipt role")
    if expected_store is not None:
        safe_store = expected_store.safe_summary()
        receipt_store = raw.get("store")
        if not isinstance(receipt_store, dict) or any(
            receipt_store.get(field_name) != safe_store.get(field_name)
            for field_name in (
                "role",
                "endpoint_host",
                "region",
                "bucket",
                "account_fingerprint",
                "release_eligible",
            )
        ):
            raise StorageSafetyError("INVALID_STORAGE_RECEIPT", "store identity mismatch")
    for field_name, expected in (
        ("slug", plan.slug),
        ("release_descriptor_sha256", plan.release_descriptor_sha256),
        ("immutable_prefix", plan.immutable_prefix),
        ("release_status", plan.release_status),
    ):
        if raw.get(field_name) != expected:
            raise StorageSafetyError("INVALID_STORAGE_RECEIPT", f"{field_name} mismatch")
    raw_objects = raw.get("objects")
    if not isinstance(raw_objects, list):
        raise StorageSafetyError("INVALID_STORAGE_RECEIPT", "objects must be an array")
    expected_assets = {asset.asset_id: asset for asset in plan.objects}
    records: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(raw_objects):
        if not isinstance(record, dict):
            raise StorageSafetyError("INVALID_STORAGE_RECEIPT", f"objects[{index}] is invalid")
        asset_id = str(record.get("asset_id") or "")
        asset = expected_assets.get(asset_id)
        if asset is None or asset_id in records:
            raise StorageSafetyError("INVALID_STORAGE_RECEIPT", f"objects[{index}].asset_id mismatch")
        try:
            receipt_size = int(record.get("size_bytes") or -1)
        except (TypeError, ValueError):
            receipt_size = -1
        if (
            record.get("key") != asset.key
            or record.get("sha256") != asset.sha256
            or receipt_size != asset.size_bytes
            or record.get("mime_type") != asset.mime_type
            or not record.get("version_id")
            or record.get("full_download_verified") is not True
            or (
                expected_store is not None
                and (
                    record.get("store") != expected_store.role
                    or record.get("bucket") != expected_store.bucket
                )
            )
        ):
            raise StorageSafetyError("INVALID_STORAGE_RECEIPT", f"objects[{index}] identity mismatch")
        records[asset_id] = record
    if set(records) != set(expected_assets):
        raise StorageSafetyError("INVALID_STORAGE_RECEIPT", "receipt does not cover the exact plan")
    return records


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _hash_remote_body(body: Any) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = body.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    finally:
        close = getattr(body, "close", None)
        if callable(close):
            close()
    return digest.hexdigest(), size


def _head_or_none(client: Any, bucket: str, key: str) -> Optional[dict[str, Any]]:
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        if _error_code(exc) in MISSING_CODES:
            return None
        raise StorageSafetyError("CLOUD_OPERATION_FAILED", f"head_object:{_error_code(exc)}") from None


def _metadata_matches(head: Mapping[str, Any], asset: PlanObject, plan: StoragePlan) -> bool:
    metadata = {str(key).lower(): str(value) for key, value in (head.get("Metadata") or {}).items()}
    return (
        int(head.get("ContentLength") or -1) == asset.size_bytes
        and str(head.get("ContentType") or "") == asset.mime_type
        and metadata.get("sha256") == asset.sha256
        and metadata.get("size-bytes") == str(asset.size_bytes)
        and metadata.get("release-descriptor-sha256") == plan.release_descriptor_sha256
        and metadata.get("asset-id") == asset.asset_id
    )


def _retention_passes(head: Mapping[str, Any], minimum_retain_until: datetime) -> bool:
    retain_until = _parse_datetime(head.get("ObjectLockRetainUntilDate"))
    return (
        str(head.get("ObjectLockMode") or "") == "GOVERNANCE"
        and retain_until is not None
        and retain_until >= minimum_retain_until
    )


def verify_remote_object(
    client: Any,
    config: StorageConfig,
    plan: StoragePlan,
    asset: PlanObject,
    minimum_retain_until: datetime,
    version_id: str = "",
) -> dict[str, Any]:
    head_kwargs: dict[str, Any] = {"Bucket": config.bucket, "Key": asset.key}
    if version_id:
        head_kwargs["VersionId"] = version_id
    head = _safe_cloud_call(client, "head_object", **head_kwargs)
    resolved_version_id = str(head.get("VersionId") or version_id or "")
    if not resolved_version_id:
        raise StorageSafetyError("REMOTE_VERSION_ID_MISSING", asset.key)
    if not _metadata_matches(head, asset, plan):
        raise StorageSafetyError("REMOTE_METADATA_MISMATCH", asset.key)
    if config.release_eligible and not _retention_passes(head, minimum_retain_until):
        raise StorageSafetyError("REMOTE_RETENTION_MISMATCH", asset.key)
    get_kwargs = dict(head_kwargs)
    get_kwargs["VersionId"] = resolved_version_id
    response = _safe_cloud_call(client, "get_object", **get_kwargs)
    downloaded_sha, downloaded_size = _hash_remote_body(response["Body"])
    if downloaded_sha != asset.sha256 or downloaded_size != asset.size_bytes:
        raise StorageSafetyError("REMOTE_FULL_DOWNLOAD_MISMATCH", asset.key)
    return {
        "key": asset.key,
        "asset_id": asset.asset_id,
        "store": config.role,
        "bucket": config.bucket,
        "sha256": downloaded_sha,
        "size_bytes": downloaded_size,
        "mime_type": asset.mime_type,
        "version_id": resolved_version_id,
        "object_lock_mode": str(head.get("ObjectLockMode") or ""),
        "retain_until": (
            (_parse_datetime(head.get("ObjectLockRetainUntilDate")) or minimum_retain_until).isoformat()
            if config.release_eligible
            else ""
        ),
        "full_download_verified": True,
    }


def _put_asset(
    client: Any,
    config: StorageConfig,
    plan: StoragePlan,
    asset: PlanObject,
    body: BinaryIO,
) -> str:
    kwargs = {
        "Bucket": config.bucket,
        "Key": asset.key,
        "Body": body,
        "ContentLength": asset.size_bytes,
        "ContentType": asset.mime_type,
        "CacheControl": "private, max-age=31536000, immutable",
        "Metadata": {
            "sha256": asset.sha256,
            "size-bytes": str(asset.size_bytes),
            "release-descriptor-sha256": plan.release_descriptor_sha256,
            "asset-id": asset.asset_id,
        },
    }
    response = _safe_cloud_call(client, "put_object", **kwargs)
    version_id = str(response.get("VersionId") or "")
    if not version_id:
        raise StorageSafetyError("UPLOAD_VERSION_ID_MISSING", asset.key)
    return version_id


def upload_plan(
    upload_client: Any,
    config: StorageConfig,
    plan: StoragePlan,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: Optional[datetime] = None,
    retention_admin_client: Any = None,
) -> dict[str, Any]:
    if retention_days < 1:
        raise StorageSafetyError("INVALID_RETENTION_DAYS", str(retention_days))
    require_production_plan_status(config, plan)
    preflight = preflight_store(
        upload_client,
        config,
        retention_admin_client,
    )
    if not preflight["passed"]:
        raise StorageSafetyError("STORE_PREFLIGHT_FAILED", ",".join(preflight["blockers"]))
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    retain_until = started + timedelta(days=retention_days)
    records = []
    for asset in plan.objects:
        existing = _head_or_none(upload_client, config.bucket, asset.key)
        if existing is not None:
            if not _metadata_matches(existing, asset, plan):
                raise StorageSafetyError("IMMUTABLE_KEY_ALREADY_EXISTS_WITH_DIFFERENT_METADATA", asset.key)
            record = verify_remote_object(
                upload_client,
                config,
                plan,
                asset,
                minimum_retain_until=retain_until,
                version_id=str(existing.get("VersionId") or ""),
            )
            record["action"] = "ALREADY_PRESENT_VERIFIED"
            records.append(record)
            continue
        with asset.local_path.open("rb") as body:
            version_id = _put_asset(
                upload_client,
                config,
                plan,
                asset,
                body,
            )
        record = verify_remote_object(
            upload_client,
            config,
            plan,
            asset,
            minimum_retain_until=retain_until,
            version_id=version_id,
        )
        record["action"] = "UPLOADED_AND_VERIFIED"
        records.append(record)
    return {
        "operation": "upload",
        "receipt_schema": RECEIPT_SCHEMA,
        "receipt_role": "primary" if config.release_eligible else "private_qa_staging",
        "generated_at": utc_now(),
        "store": config.safe_summary(),
        "profiles_used": preflight["profiles_used"],
        "release_eligible": config.release_eligible,
        "slug": plan.slug,
        "release_descriptor_sha256": plan.release_descriptor_sha256,
        "immutable_prefix": plan.immutable_prefix,
        "release_status": plan.release_status,
        "retention_days": retention_days,
        "objects": records,
        "passed": len(records) == len(plan.objects),
    }


def verify_plan(
    upload_client: Any,
    config: StorageConfig,
    plan: StoragePlan,
    receipt_records: Mapping[str, Mapping[str, Any]],
    retention_days: int = 0,
    now: Optional[datetime] = None,
    retention_admin_client: Any = None,
) -> dict[str, Any]:
    if retention_days < 0:
        raise StorageSafetyError("INVALID_RETENTION_DAYS", str(retention_days))
    require_production_plan_status(config, plan)
    preflight = preflight_store(
        upload_client,
        config,
        retention_admin_client,
    )
    if not preflight["passed"]:
        raise StorageSafetyError("STORE_PREFLIGHT_FAILED", ",".join(preflight["blockers"]))
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    minimum = started + timedelta(days=retention_days)
    if set(receipt_records) != {asset.asset_id for asset in plan.objects}:
        raise StorageSafetyError("INVALID_STORAGE_RECEIPT", "receipt does not cover the exact plan")
    records = []
    for asset in plan.objects:
        receipt = receipt_records[asset.asset_id]
        record = verify_remote_object(
            upload_client,
            config,
            plan,
            asset,
            minimum_retain_until=minimum,
            version_id=str(receipt.get("version_id") or ""),
        )
        if (
            record["key"] != receipt.get("key")
            or record["sha256"] != receipt.get("sha256")
            or record["size_bytes"] != receipt.get("size_bytes")
        ):
            raise StorageSafetyError("REMOTE_OBJECT_NO_LONGER_MATCHES_RECEIPT", asset.key)
        record["receipt_verified"] = True
        records.append(record)
    return {
        "operation": "verify",
        "generated_at": utc_now(),
        "store": config.safe_summary(),
        "profiles_used": preflight["profiles_used"],
        "release_eligible": config.release_eligible,
        "slug": plan.slug,
        "release_descriptor_sha256": plan.release_descriptor_sha256,
        "immutable_prefix": plan.immutable_prefix,
        "release_status": plan.release_status,
        "objects": records,
        "passed": len(records) == len(plan.objects),
    }


def replicate_plan(
    prod_upload_client: Any,
    prod_config: StorageConfig,
    dr_upload_client: Any,
    dr_config: StorageConfig,
    plan: StoragePlan,
    primary_receipt_records: Mapping[str, Mapping[str, Any]],
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: Optional[datetime] = None,
    prod_retention_admin_client: Any = None,
    dr_retention_admin_client: Any = None,
) -> dict[str, Any]:
    validate_independent_stores(prod_config, dr_config)
    require_production_plan_status(prod_config, plan)
    require_production_plan_status(dr_config, plan)
    prod_preflight = preflight_store(
        prod_upload_client,
        prod_config,
        prod_retention_admin_client,
    )
    dr_preflight = preflight_store(
        dr_upload_client,
        dr_config,
        dr_retention_admin_client,
    )
    blockers = prod_preflight["blockers"] + dr_preflight["blockers"]
    if blockers:
        raise StorageSafetyError("STORE_PREFLIGHT_FAILED", ",".join(blockers))
    if retention_days < 1:
        raise StorageSafetyError("INVALID_RETENTION_DAYS", str(retention_days))
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    retain_until = started + timedelta(days=retention_days)
    records = []
    if set(primary_receipt_records) != {asset.asset_id for asset in plan.objects}:
        raise StorageSafetyError("INVALID_STORAGE_RECEIPT", "primary receipt does not cover exact plan")
    for asset in plan.objects:
        primary_receipt = primary_receipt_records[asset.asset_id]
        prod_record = verify_remote_object(
            prod_upload_client,
            prod_config,
            plan,
            asset,
            minimum_retain_until=started,
            version_id=str(primary_receipt.get("version_id") or ""),
        )
        existing = _head_or_none(
            dr_upload_client,
            dr_config.bucket,
            asset.key,
        )
        if existing is not None:
            if not _metadata_matches(existing, asset, plan):
                raise StorageSafetyError("IMMUTABLE_KEY_ALREADY_EXISTS_WITH_DIFFERENT_METADATA", asset.key)
            dr_record = verify_remote_object(
                dr_upload_client,
                dr_config,
                plan,
                asset,
                minimum_retain_until=retain_until,
                version_id=str(existing.get("VersionId") or ""),
            )
            action = "DR_ALREADY_PRESENT_VERIFIED"
        else:
            source_response = _safe_cloud_call(
                prod_upload_client,
                "get_object",
                Bucket=prod_config.bucket,
                Key=asset.key,
                VersionId=prod_record["version_id"],
            )
            with tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024, mode="w+b") as spool:
                digest = hashlib.sha256()
                size = 0
                source_body = source_response["Body"]
                try:
                    while True:
                        chunk = source_body.read(1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                        size += len(chunk)
                        spool.write(chunk)
                finally:
                    close = getattr(source_body, "close", None)
                    if callable(close):
                        close()
                if digest.hexdigest() != asset.sha256 or size != asset.size_bytes:
                    raise StorageSafetyError("PRODUCTION_SOURCE_CHANGED_DURING_REPLICATION", asset.key)
                spool.seek(0)
                version_id = _put_asset(
                    dr_upload_client,
                    dr_config,
                    plan,
                    asset,
                    spool,
                )
            dr_record = verify_remote_object(
                dr_upload_client,
                dr_config,
                plan,
                asset,
                minimum_retain_until=retain_until,
                version_id=version_id,
            )
            action = "REPLICATED_AND_VERIFIED"
        records.append(
            {
                "asset_id": asset.asset_id,
                "store": dr_config.role,
                "bucket": dr_config.bucket,
                "key": asset.key,
                "sha256": asset.sha256,
                "size_bytes": asset.size_bytes,
                "mime_type": asset.mime_type,
                "version_id": dr_record["version_id"],
                "primary_version_id": prod_record["version_id"],
                "object_lock_mode": dr_record["object_lock_mode"],
                "retain_until": dr_record["retain_until"],
                "action": action,
                "full_download_verified": True,
                "primary_receipt_verified": True,
            }
        )
    return {
        "operation": "replicate",
        "receipt_schema": RECEIPT_SCHEMA,
        "receipt_role": "replica",
        "generated_at": utc_now(),
        "production_store": prod_config.safe_summary(),
        "dr_store": dr_config.safe_summary(),
        "store": dr_config.safe_summary(),
        "profiles_used": {
            "production": prod_preflight["profiles_used"],
            "disaster_recovery": dr_preflight["profiles_used"],
        },
        "slug": plan.slug,
        "release_descriptor_sha256": plan.release_descriptor_sha256,
        "immutable_prefix": plan.immutable_prefix,
        "release_status": plan.release_status,
        "retention_days": retention_days,
        "objects": records,
        "passed": len(records) == len(plan.objects),
    }


def _iso_datetime(value: Any) -> str:
    parsed = _parse_datetime(value)
    return parsed.isoformat() if parsed else ""


def audit_retention(
    upload_client: Any,
    config: StorageConfig,
    slug: str,
    current_release_descriptor_sha256: str,
    retain_versions: int = 3,
    retention_admin_client: Any = None,
) -> dict[str, Any]:
    """Report retained generations. This function intentionally cannot delete."""

    if not SLUG_RE.fullmatch(slug):
        raise StorageSafetyError("INVALID_SLUG", slug)
    if not SHA256_RE.fullmatch(current_release_descriptor_sha256):
        raise StorageSafetyError(
            "INVALID_RELEASE_DESCRIPTOR_SHA256",
            current_release_descriptor_sha256,
        )
    if retain_versions < 3:
        raise StorageSafetyError("RETENTION_REPORT_MUST_KEEP_CURRENT_PLUS_TWO", str(retain_versions))
    preflight = preflight_store(
        upload_client,
        config,
        retention_admin_client,
    )
    if not preflight["passed"]:
        raise StorageSafetyError("STORE_PREFLIGHT_FAILED", ",".join(preflight["blockers"]))
    prefix = f"{PRODUCTION_PREFIX}{slug}/releases/"
    versions_by_release: dict[str, list[dict[str, Any]]] = {}
    key_marker = ""
    version_marker = ""
    while True:
        kwargs: dict[str, Any] = {"Bucket": config.bucket, "Prefix": prefix}
        if key_marker:
            kwargs["KeyMarker"] = key_marker
        if version_marker:
            kwargs["VersionIdMarker"] = version_marker
        page = _safe_cloud_call(upload_client, "list_object_versions", **kwargs)
        for item in page.get("Versions", []):
            key = str(item.get("Key") or "")
            parts = key.split("/")
            if len(parts) < 7 or "/".join(parts[:5]) + "/" != prefix:
                continue
            release_descriptor_sha256 = parts[5]
            if not SHA256_RE.fullmatch(release_descriptor_sha256):
                continue
            versions_by_release.setdefault(release_descriptor_sha256, []).append(
                {
                    "key": key,
                    "version_id": str(item.get("VersionId") or ""),
                    "is_latest": bool(item.get("IsLatest")),
                    "size_bytes": int(item.get("Size") or 0),
                    "last_modified": _iso_datetime(item.get("LastModified")),
                }
            )
        if not page.get("IsTruncated"):
            break
        key_marker = str(page.get("NextKeyMarker") or "")
        version_marker = str(page.get("NextVersionIdMarker") or "")
        if not key_marker:
            raise StorageSafetyError("TRUNCATED_VERSION_LIST_WITHOUT_MARKER")

    if current_release_descriptor_sha256 not in versions_by_release:
        raise StorageSafetyError(
            "CURRENT_RELEASE_DESCRIPTOR_NOT_FOUND",
            current_release_descriptor_sha256,
        )
    package_summaries = []
    for release_descriptor_sha256, records in versions_by_release.items():
        current_records = [record for record in records if record["is_latest"]]
        package_summaries.append(
            {
                "release_descriptor_sha256": release_descriptor_sha256,
                "is_current": release_descriptor_sha256 == current_release_descriptor_sha256,
                "latest_object_count": len(current_records),
                "physical_version_count": len(records),
                "latest_size_bytes": sum(record["size_bytes"] for record in current_records),
                "latest_modified": max((record["last_modified"] for record in records), default=""),
                "all_version_ids_present": all(bool(record["version_id"]) for record in records),
            }
        )
    package_summaries.sort(
        key=lambda item: (
            item["release_descriptor_sha256"] != current_release_descriptor_sha256,
            str(item["latest_modified"]),
        ),
        reverse=False,
    )
    current = next(
        item
        for item in package_summaries
        if item["release_descriptor_sha256"] == current_release_descriptor_sha256
    )
    prior = sorted(
        (
            item
            for item in package_summaries
            if item["release_descriptor_sha256"] != current_release_descriptor_sha256
        ),
        key=lambda item: str(item["latest_modified"]),
        reverse=True,
    )
    retained = [current] + prior[: retain_versions - 1]
    older = prior[retain_versions - 1 :]
    retained_checks_pass = True
    audit_time = datetime.now(timezone.utc)
    for summary in retained:
        records = versions_by_release[summary["release_descriptor_sha256"]]
        current_records = [record for record in records if record["is_latest"]]
        modes: list[str] = []
        retain_until_values: list[datetime] = []
        sha_metadata_present = True
        for record in current_records:
            head = _safe_cloud_call(
                upload_client,
                "head_object",
                Bucket=config.bucket,
                Key=record["key"],
                VersionId=record["version_id"],
            )
            modes.append(str(head.get("ObjectLockMode") or ""))
            retain_until = _parse_datetime(head.get("ObjectLockRetainUntilDate"))
            if retain_until is not None:
                retain_until_values.append(retain_until)
            metadata = {str(key).lower(): str(value) for key, value in (head.get("Metadata") or {}).items()}
            sha_metadata_present = sha_metadata_present and bool(SHA256_RE.fullmatch(metadata.get("sha256", "")))
        governance_locked = bool(current_records) and all(mode == "GOVERNANCE" for mode in modes)
        retention_active = (
            len(retain_until_values) == len(current_records)
            and bool(retain_until_values)
            and min(retain_until_values) > audit_time
        )
        summary["governance_locked"] = governance_locked
        summary["retention_active"] = retention_active
        summary["earliest_retain_until"] = (
            min(retain_until_values).isoformat() if retain_until_values else ""
        )
        summary["sha256_metadata_present"] = sha_metadata_present
        retained_checks_pass = (
            retained_checks_pass
            and governance_locked
            and retention_active
            and sha_metadata_present
            and summary["all_version_ids_present"]
        )
    return {
        "operation": "audit",
        "generated_at": utc_now(),
        "store": config.safe_summary(),
        "profiles_used": preflight["profiles_used"],
        "slug": slug,
        "current_release_descriptor_sha256": current_release_descriptor_sha256,
        "retention_policy": "CURRENT_PLUS_TWO_OR_MORE",
        "minimum_retained_release_generations": retain_versions,
        "retained_release_generations": retained,
        "older_release_generations_observed": older,
        "delete_actions": [],
        "deletion_supported": False,
        "passed": (
            len(retained) >= min(retain_versions, len(package_summaries))
            and retained_checks_pass
        ),
    }


def safe_failure(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, StorageSafetyError):
        return {
            "passed": False,
            "error": exc.code,
            "detail": exc.detail,
        }
    return {
        "passed": False,
        "error": "UNEXPECTED_ERROR",
        "detail": type(exc).__name__,
    }


def _write_report(report: Mapping[str, Any], path: Optional[str]) -> None:
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path:
        report_path = Path(path).expanduser()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)


def _write_receipt(receipt: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)


def _preflight_command(args: argparse.Namespace) -> dict[str, Any]:
    prod = config_from_env("prod", args.allow_private_qa_staging)
    prod_upload_client = create_s3_client(prod, "upload")
    prod_retention_client = (
        create_s3_client(prod, "retention_admin")
        if prod.release_eligible
        else None
    )
    prod_report = preflight_store(
        prod_upload_client,
        prod,
        prod_retention_client,
    )
    if not prod.release_eligible:
        return {
            "operation": "preflight",
            "generated_at": utc_now(),
            "mode": "PRIVATE_QA_STAGING_ONLY",
            "release_eligible": False,
            "stores": [prod_report],
            "passed": prod_report["passed"],
        }
    dr = config_from_env("dr")
    validate_independent_stores(prod, dr)
    dr_report = preflight_store(
        create_s3_client(dr, "upload"),
        dr,
        create_s3_client(dr, "retention_admin"),
    )
    passed = prod_report["passed"] and dr_report["passed"]
    return {
        "operation": "preflight",
        "generated_at": utc_now(),
        "mode": "PRODUCTION_AND_DR",
        "release_eligible": passed,
        "stores": [prod_report, dr_report],
        "passed": passed,
    }


def _upload_command(args: argparse.Namespace) -> dict[str, Any]:
    plan_path = Path(args.plan).expanduser()
    plan = load_storage_plan(plan_path)
    config = config_from_env("prod", args.allow_private_qa_staging)
    receipt = upload_plan(
        create_s3_client(config, "upload"),
        config,
        plan,
        args.retention_days,
        retention_admin_client=(
            create_s3_client(config, "retention_admin")
            if config.release_eligible
            else None
        ),
    )
    receipt_path = Path(args.receipt).expanduser() if args.receipt else plan_path.parent / "primary_receipt.json"
    _write_receipt(receipt, receipt_path)
    report = dict(receipt)
    report["receipt_path"] = str(receipt_path.resolve())
    return report


def _verify_command(args: argparse.Namespace) -> dict[str, Any]:
    plan_path = Path(args.plan).expanduser()
    plan = load_storage_plan(plan_path, verify_local_files=False)
    config = config_from_env(
        args.store,
        args.allow_private_qa_staging and args.store == "prod",
    )
    default_name = "primary_receipt.json" if args.store == "prod" else "replica_receipt.json"
    receipt_path = Path(args.receipt).expanduser() if args.receipt else plan_path.parent / default_name
    expected_role = (
        "private_qa_staging"
        if config.role == "private_qa_staging"
        else ("primary" if args.store == "prod" else "replica")
    )
    receipt_records = load_storage_receipt(receipt_path, plan, expected_role, config)
    report = verify_plan(
        create_s3_client(config, "upload"),
        config,
        plan,
        receipt_records,
        args.minimum_remaining_retention_days,
        retention_admin_client=(
            create_s3_client(config, "retention_admin")
            if config.release_eligible
            else None
        ),
    )
    report["receipt_path"] = str(receipt_path.resolve())
    report["receipt_role"] = expected_role
    return report


def _replicate_command(args: argparse.Namespace) -> dict[str, Any]:
    plan_path = Path(args.plan).expanduser()
    plan = load_storage_plan(plan_path, verify_local_files=False)
    prod = config_from_env("prod")
    dr = config_from_env("dr")
    validate_independent_stores(prod, dr)
    primary_path = (
        Path(args.primary_receipt).expanduser()
        if args.primary_receipt
        else plan_path.parent / "primary_receipt.json"
    )
    primary_records = load_storage_receipt(primary_path, plan, "primary", prod)
    receipt = replicate_plan(
        create_s3_client(prod, "upload"),
        prod,
        create_s3_client(dr, "upload"),
        dr,
        plan,
        primary_records,
        args.retention_days,
        prod_retention_admin_client=create_s3_client(
            prod,
            "retention_admin",
        ),
        dr_retention_admin_client=create_s3_client(
            dr,
            "retention_admin",
        ),
    )
    replica_path = (
        Path(args.replica_receipt).expanduser()
        if args.replica_receipt
        else plan_path.parent / "replica_receipt.json"
    )
    _write_receipt(receipt, replica_path)
    report = dict(receipt)
    report["primary_receipt_path"] = str(primary_path.resolve())
    report["receipt_path"] = str(replica_path.resolve())
    return report


def _audit_command(args: argparse.Namespace) -> dict[str, Any]:
    config = config_from_env(
        args.store,
        args.allow_private_qa_staging and args.store == "prod",
    )
    return audit_retention(
        create_s3_client(config, "upload"),
        config,
        args.slug,
        args.current_release_descriptor_sha256,
        args.retain_versions,
        retention_admin_client=(
            create_s3_client(config, "retention_admin")
            if config.release_eligible
            else None
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight, upload, verify, replicate, and audit immutable audiobook package-v2 objects."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Validate production and DR bucket invariants.")
    preflight.add_argument("--allow-private-qa-staging", action="store_true")
    preflight.add_argument("--report")
    preflight.set_defaults(handler=_preflight_command)

    upload = subparsers.add_parser("upload", help="Upload and full-download-verify a local storage plan.")
    upload.add_argument("--plan", required=True)
    upload.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    upload.add_argument("--allow-private-qa-staging", action="store_true")
    upload.add_argument("--receipt", help="Defaults to primary_receipt.json beside the plan.")
    upload.add_argument("--report")
    upload.set_defaults(handler=_upload_command)

    verify = subparsers.add_parser("verify", help="Full-download-verify an exact remote package plan.")
    verify.add_argument("--plan", required=True)
    verify.add_argument("--store", choices=("prod", "dr"), default="prod")
    verify.add_argument("--minimum-remaining-retention-days", type=int, default=0)
    verify.add_argument("--allow-private-qa-staging", action="store_true")
    verify.add_argument("--receipt", help="Defaults to primary_receipt.json or replica_receipt.json.")
    verify.add_argument("--report")
    verify.set_defaults(handler=_verify_command)

    replicate = subparsers.add_parser("replicate", help="Replicate verified production bytes to independent DR.")
    replicate.add_argument("--plan", required=True)
    replicate.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    replicate.add_argument("--primary-receipt", help="Defaults to primary_receipt.json beside the plan.")
    replicate.add_argument("--replica-receipt", help="Defaults to replica_receipt.json beside the plan.")
    replicate.add_argument("--report")
    replicate.set_defaults(handler=_replicate_command)

    audit = subparsers.add_parser("audit", help="Report current + 2 retained release generations; never delete.")
    audit.add_argument("--slug", required=True)
    audit.add_argument("--current-release-descriptor-sha256", required=True)
    audit.add_argument("--store", choices=("prod", "dr"), default="prod")
    audit.add_argument("--retain-versions", type=int, default=3)
    audit.add_argument("--allow-private-qa-staging", action="store_true")
    audit.add_argument("--report")
    audit.set_defaults(handler=_audit_command)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = args.handler(args)
    except Exception as exc:
        report = safe_failure(exc)
    _write_report(report, getattr(args, "report", None))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
