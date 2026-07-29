#!/usr/bin/env python3
"""Offline tests for immutable package-v2 B2 storage tooling."""

from __future__ import annotations

import io
import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audiobook_package_storage_v2 as storage


class FakeCloudError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(
        self,
        *,
        versioning: str = "Enabled",
        lock_mode: str = "GOVERNANCE",
        lifecycle_rules: list[dict] | None = None,
        public: bool = False,
        default_retention_days: int = 365,
    ) -> None:
        self.versioning = versioning
        self.lock_mode = lock_mode
        self.lifecycle_rules = lifecycle_rules or []
        self.public = public
        self.default_retention_days = default_retention_days
        self.objects: dict[tuple[str, str], dict] = {}
        self.latest: dict[str, str] = {}
        self.counter = 0
        self.put_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.method_calls: list[str] = []

    def head_bucket(self, **kwargs):
        self.method_calls.append("head_bucket")
        return {}

    def get_bucket_versioning(self, **kwargs):
        self.method_calls.append("get_bucket_versioning")
        return {"Status": self.versioning}

    def get_object_lock_configuration(self, **kwargs):
        self.method_calls.append("get_object_lock_configuration")
        return {
            "ObjectLockConfiguration": {
                "ObjectLockEnabled": "Enabled",
                "Rule": {
                    "DefaultRetention": {
                        "Mode": self.lock_mode,
                        "Days": self.default_retention_days,
                    }
                },
            }
        }

    def get_public_access_block(self, **kwargs):
        self.method_calls.append("get_public_access_block")
        private = not self.public
        return {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": private,
                "IgnorePublicAcls": private,
                "BlockPublicPolicy": private,
                "RestrictPublicBuckets": private,
            }
        }

    def get_bucket_policy_status(self, **kwargs):
        self.method_calls.append("get_bucket_policy_status")
        return {"PolicyStatus": {"IsPublic": self.public}}

    def get_bucket_acl(self, **kwargs):
        self.method_calls.append("get_bucket_acl")
        if self.public:
            return {
                "Grants": [
                    {
                        "Grantee": {
                            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
                        }
                    }
                ]
            }
        return {"Grants": []}

    def get_bucket_lifecycle_configuration(self, **kwargs):
        self.method_calls.append("get_bucket_lifecycle_configuration")
        return {"Rules": self.lifecycle_rules}

    def head_object(self, *, Bucket, Key, VersionId=None):
        self.method_calls.append("head_object")
        version_id = VersionId or self.latest.get(Key)
        if not version_id or (Key, version_id) not in self.objects:
            raise FakeCloudError("NoSuchKey")
        record = self.objects[(Key, version_id)]
        return {
            "VersionId": version_id,
            "ContentLength": len(record["body"]),
            "ContentType": record["content_type"],
            "Metadata": dict(record["metadata"]),
            "ObjectLockMode": record["lock_mode"],
            "ObjectLockRetainUntilDate": record["retain_until"],
        }

    def put_object(self, **kwargs):
        self.method_calls.append("put_object")
        self.counter += 1
        version_id = f"version-{self.counter}"
        body = kwargs["Body"].read()
        record = {
            "body": body,
            "metadata": dict(kwargs["Metadata"]),
            "content_type": kwargs["ContentType"],
            "lock_mode": self.lock_mode,
            "retain_until": (
                datetime.now(timezone.utc)
                + timedelta(days=self.default_retention_days)
                if self.lock_mode
                else None
            ),
            "last_modified": datetime.now(timezone.utc) + timedelta(seconds=self.counter),
        }
        key = kwargs["Key"]
        self.objects[(key, version_id)] = record
        self.latest[key] = version_id
        self.put_calls.append(dict(kwargs, Body=b"<stream>"))
        return {"VersionId": version_id}

    def get_object(self, *, Bucket, Key, VersionId=None):
        self.method_calls.append("get_object")
        version_id = VersionId or self.latest.get(Key)
        if not version_id or (Key, version_id) not in self.objects:
            raise FakeCloudError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[(Key, version_id)]["body"])}

    def list_object_versions(self, **kwargs):
        self.method_calls.append("list_object_versions")
        prefix = kwargs.get("Prefix", "")
        versions = []
        for (key, version_id), record in self.objects.items():
            if key.startswith(prefix):
                versions.append(
                    {
                        "Key": key,
                        "VersionId": version_id,
                        "IsLatest": self.latest.get(key) == version_id,
                        "Size": len(record["body"]),
                        "LastModified": record["last_modified"],
                    }
                )
        return {"Versions": versions, "IsTruncated": False}


def config(role: str, *, release_eligible: bool = True) -> storage.StorageConfig:
    index = "1" if role == "prod" else "2"
    return storage.StorageConfig(
        role=role,
        endpoint=f"https://s3.region-{index}.example.invalid",
        region=f"region-{index}",
        bucket=f"private-bucket-{index}",
        account_id=f"account-{index}",
        upload_credentials=storage.CredentialProfile(
            name="upload",
            access_key_id=f"upload-key-{index}",
            secret_access_key=f"upload-secret-{index}",
        ),
        retention_admin_credentials=storage.CredentialProfile(
            name="retention_admin",
            access_key_id=f"retention-key-{index}",
            secret_access_key=f"retention-secret-{index}",
        ),
        release_eligible=release_eligible,
        environment_prefix=f"B2_AUDIOBOOK_{role.upper()}_",
    )


class StorageToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.audio = self.root / "master.mp3"
        self.audio.write_bytes(b"exact master bytes")
        self.manifest = self.root / "release-manifest.json"
        self.manifest.write_text('{"release":"exact"}\n', encoding="utf-8")
        self.release_descriptor_sha256 = "a" * 64
        self.immutable_prefix = (
            "v1/prod/sprint1/muchiram-gurer-jibanchorit/releases/"
            f"{self.release_descriptor_sha256}/"
        )
        self.plan_path = self.root / "upload-plan.json"
        self.plan_raw = {
            "schema_version": storage.PLAN_SCHEMA,
            "slug": "muchiram-gurer-jibanchorit",
            "release_descriptor_sha256": self.release_descriptor_sha256,
            "immutable_prefix": self.immutable_prefix,
            "release_status": "RELEASE_CANDIDATE",
            "assets": [
                self._object("master-audio", self.audio, "masters/master.mp3", "audio/mpeg"),
                self._object(
                    "release-manifest",
                    self.manifest,
                    "release/release-manifest.json",
                    "application/json",
                ),
            ],
        }
        self.plan_path.write_text(json.dumps(self.plan_raw), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _object(self, asset_id: str, path: Path, suffix: str, mime_type: str) -> dict:
        digest, size = storage.hash_local_file(path)
        return {
            "asset_id": asset_id,
            "local_path": str(path),
            "key": f"{self.immutable_prefix}{suffix}",
            "sha256": digest,
            "size_bytes": size,
            "mime_type": mime_type,
        }

    def _plan(self, verify_local_files: bool = True) -> storage.StoragePlan:
        return storage.load_storage_plan(self.plan_path, verify_local_files=verify_local_files)

    def _set_release_status(self, release_status: str) -> storage.StoragePlan:
        raw = dict(self.plan_raw)
        raw["release_status"] = release_status
        self.plan_path.write_text(json.dumps(raw), encoding="utf-8")
        return self._plan()

    def _release_env(self) -> dict[str, str]:
        return {
            "B2_AUDIOBOOK_PROD_S3_ENDPOINT": config("prod").endpoint,
            "B2_AUDIOBOOK_PROD_REGION": config("prod").region,
            "B2_AUDIOBOOK_PROD_BUCKET": config("prod").bucket,
            "B2_AUDIOBOOK_PROD_ACCOUNT_ID": config("prod").account_id,
            "B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID": config("prod").upload_credentials.access_key_id,
            "B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY": config("prod").upload_credentials.secret_access_key,
            "B2_AUDIOBOOK_PROD_RETENTION_ADMIN_ACCESS_KEY_ID": config("prod").retention_admin_credentials.access_key_id,
            "B2_AUDIOBOOK_PROD_RETENTION_ADMIN_SECRET_ACCESS_KEY": config("prod").retention_admin_credentials.secret_access_key,
            "B2_AUDIOBOOK_DR_S3_ENDPOINT": config("dr").endpoint,
            "B2_AUDIOBOOK_DR_REGION": config("dr").region,
            "B2_AUDIOBOOK_DR_BUCKET": config("dr").bucket,
            "B2_AUDIOBOOK_DR_ACCOUNT_ID": config("dr").account_id,
            "B2_AUDIOBOOK_DR_UPLOAD_ACCESS_KEY_ID": config("dr").upload_credentials.access_key_id,
            "B2_AUDIOBOOK_DR_UPLOAD_SECRET_ACCESS_KEY": config("dr").upload_credentials.secret_access_key,
            "B2_AUDIOBOOK_DR_RETENTION_ADMIN_ACCESS_KEY_ID": config("dr").retention_admin_credentials.access_key_id,
            "B2_AUDIOBOOK_DR_RETENTION_ADMIN_SECRET_ACCESS_KEY": config("dr").retention_admin_credentials.secret_access_key,
        }

    def test_environment_has_no_implicit_legacy_fallback_and_redacts_secrets(self) -> None:
        legacy_only = {
            "B2_S3_ENDPOINT": "https://legacy.invalid",
            "B2_BUCKET": "legacy",
            "B2_ACCESS_KEY_ID": "legacy-id",
            "B2_SECRET_ACCESS_KEY": "legacy-secret",
        }
        with mock.patch.dict(os.environ, legacy_only, clear=True):
            with self.assertRaisesRegex(storage.StorageSafetyError, "STORAGE_CONFIGURATION_MISSING"):
                storage.config_from_env("prod")

        qa = {
            "B2_PRIVATE_QA_S3_ENDPOINT": "https://qa.invalid",
            "B2_PRIVATE_QA_REGION": "qa-region",
            "B2_PRIVATE_QA_BUCKET": "qa-private",
            "B2_PRIVATE_QA_ACCOUNT_ID": "qa-account",
            "B2_PRIVATE_QA_ACCESS_KEY_ID": "qa-id",
            "B2_PRIVATE_QA_SECRET_ACCESS_KEY": "most-secret-value",
        }
        with mock.patch.dict(os.environ, qa, clear=True):
            staged = storage.config_from_env("prod", allow_private_qa_staging=True)
        self.assertFalse(staged.release_eligible)
        self.assertNotIn("most-secret-value", repr(staged))
        self.assertNotIn("qa-id", json.dumps(staged.safe_summary()))

        qa_without_account = {key: value for key, value in qa.items() if key != "B2_PRIVATE_QA_ACCOUNT_ID"}
        with mock.patch.dict(os.environ, qa_without_account, clear=True):
            staged_without_account = storage.config_from_env(
                "prod",
                allow_private_qa_staging=True,
            )
        self.assertFalse(staged_without_account.release_eligible)
        self.assertEqual(staged_without_account.account_id, "")

    def test_production_requires_distinct_upload_and_retention_admin_profiles(self) -> None:
        full = {
            key: value
            for key, value in self._release_env().items()
            if key.startswith("B2_AUDIOBOOK_PROD_")
        }
        identity = {
            key: value
            for key, value in full.items()
            if not any(
                token in key
                for token in ("UPLOAD_", "RETENTION_ADMIN_")
            )
        }
        shared_or_runtime = {
            **identity,
            "B2_AUDIOBOOK_PROD_ACCESS_KEY_ID": "shared-key",
            "B2_AUDIOBOOK_PROD_SECRET_ACCESS_KEY": "shared-secret",
            "B2_AUDIOBOOK_PROD_RUNTIME_ACCESS_KEY_ID": "runtime-key",
            "B2_AUDIOBOOK_PROD_RUNTIME_SECRET_ACCESS_KEY": "runtime-secret",
        }
        with mock.patch.dict(os.environ, shared_or_runtime, clear=True):
            with self.assertRaisesRegex(
                storage.StorageSafetyError,
                "UPLOAD_PROFILE_CONFIGURATION_MISSING",
            ):
                storage.config_from_env("prod")

        upload_only = {
            **identity,
            "B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID": "upload-key",
            "B2_AUDIOBOOK_PROD_UPLOAD_SECRET_ACCESS_KEY": "upload-secret",
        }
        with mock.patch.dict(os.environ, upload_only, clear=True):
            with self.assertRaisesRegex(
                storage.StorageSafetyError,
                "RETENTION_ADMIN_PROFILE_CONFIGURATION_MISSING",
            ):
                storage.config_from_env("prod")

        same_key = dict(full)
        same_key["B2_AUDIOBOOK_PROD_RETENTION_ADMIN_ACCESS_KEY_ID"] = (
            same_key["B2_AUDIOBOOK_PROD_UPLOAD_ACCESS_KEY_ID"]
        )
        with mock.patch.dict(os.environ, same_key, clear=True):
            with self.assertRaisesRegex(
                storage.StorageSafetyError,
                "CREDENTIAL_PROFILES_NOT_SEPARATE",
            ):
                storage.config_from_env("prod")

        with mock.patch.dict(os.environ, full, clear=True):
            production = storage.config_from_env("prod")
        summary = production.safe_summary()
        encoded = json.dumps(summary)
        self.assertEqual(
            summary["credential_profiles"]["object_io"]["name"],
            "upload",
        )
        self.assertEqual(
            summary["credential_profiles"]["retention_preflight"]["name"],
            "retention_admin",
        )
        for secret in (
            production.upload_credentials.access_key_id,
            production.upload_credentials.secret_access_key,
            production.retention_admin_credentials.access_key_id,
            production.retention_admin_credentials.secret_access_key,
        ):
            self.assertNotIn(secret, encoded)
            self.assertNotIn(secret, repr(production))

    def test_bucket_preflight_uses_retention_admin_not_upload_profile(self) -> None:
        upload_client = FakeS3()
        retention_admin_client = FakeS3()

        report = storage.preflight_store(
            upload_client,
            config("prod"),
            retention_admin_client,
        )

        self.assertTrue(report["passed"])
        self.assertEqual(upload_client.method_calls, ["head_bucket"])
        self.assertIn(
            "get_object_lock_configuration",
            retention_admin_client.method_calls,
        )
        self.assertIn(
            "get_bucket_lifecycle_configuration",
            retention_admin_client.method_calls,
        )
        self.assertEqual(
            report["profiles_used"],
            {
                "object_io": "upload",
                "retention_preflight": "retention_admin",
            },
        )

    def test_independence_requires_account_region_endpoint_and_bucket(self) -> None:
        prod = config("prod")
        same_region = storage.StorageConfig(
            role="dr",
            endpoint="https://different.example.invalid",
            region=prod.region,
            bucket="different-bucket",
            account_id="different-account",
            upload_credentials=storage.CredentialProfile(
                "upload",
                "different-upload-key",
                "different-upload-secret",
            ),
            retention_admin_credentials=storage.CredentialProfile(
                "retention_admin",
                "different-retention-key",
                "different-retention-secret",
            ),
        )
        with self.assertRaisesRegex(storage.StorageSafetyError, "STORES_NOT_INDEPENDENT"):
            storage.validate_independent_stores(prod, same_region)
        storage.validate_independent_stores(prod, config("dr"))

    def test_private_qa_staging_skips_production_retention_but_remains_ineligible(self) -> None:
        qa_config = storage.StorageConfig(
            role="private_qa_staging",
            endpoint="https://qa.example.invalid",
            region="qa-region",
            bucket="qa-private",
            account_id="",
            upload_credentials=storage.CredentialProfile(
                "private_qa_legacy",
                "qa-id",
                "qa-secret",
            ),
            release_eligible=False,
            environment_prefix="B2_PRIVATE_QA_",
        )
        cloud = FakeS3(lock_mode="")
        private_plan = self._set_release_status("PRIVATE_STAGING_ONLY")
        receipt = storage.upload_plan(
            cloud,
            qa_config,
            private_plan,
            retention_days=1,
        )

        self.assertTrue(receipt["passed"])
        self.assertFalse(receipt["release_eligible"])
        self.assertEqual(receipt["receipt_role"], "private_qa_staging")
        self.assertEqual(
            receipt["profiles_used"],
            {
                "object_io": "private_qa_legacy",
                "retention_preflight": "not_configured",
            },
        )
        self.assertTrue(all(not row["object_lock_mode"] for row in receipt["objects"]))
        self.assertTrue(all("ObjectLockMode" not in call for call in cloud.put_calls))

    def test_private_staging_plan_cannot_be_uploaded_with_production_credentials(self) -> None:
        plan = self._set_release_status("PRIVATE_STAGING_ONLY")
        upload_client = FakeS3()

        with self.assertRaisesRegex(
            storage.StorageSafetyError,
            "PRODUCTION_PLAN_STATUS_NOT_ALLOWED",
        ):
            storage.upload_plan(
                upload_client,
                config("prod"),
                plan,
                retention_admin_client=FakeS3(),
            )

        self.assertEqual(upload_client.put_calls, [])

    def test_plan_accepts_master_and_release_manifest_exact_keys(self) -> None:
        plan = self._plan()
        self.assertEqual([item.asset_id for item in plan.objects], ["master-audio", "release-manifest"])
        self.assertTrue(plan.objects[0].key.endswith("/masters/master.mp3"))
        broken = dict(self.plan_raw)
        broken["assets"] = [dict(self.plan_raw["assets"][0], key="outside/master.mp3")]
        self.plan_path.write_text(json.dumps(broken), encoding="utf-8")
        with self.assertRaisesRegex(storage.StorageSafetyError, "immutable package prefix"):
            self._plan()

    def test_preflight_rejects_deleting_lifecycle_rule(self) -> None:
        client = FakeS3(
            lifecycle_rules=[
                {
                    "ID": "expire-production",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "v1/prod/"},
                    "Expiration": {"Days": 30},
                }
            ]
        )
        report = storage.preflight_store(
            FakeS3(),
            config("prod"),
            retention_admin_client=client,
        )
        self.assertFalse(report["passed"])
        self.assertIn("PRODUCTION_LIFECYCLE_DELETION_CONFIGURED", report["blockers"])

    def test_upload_writes_locked_versions_and_receipt_can_verify(self) -> None:
        client = FakeS3()
        plan = self._plan()
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        retention_admin = FakeS3()
        receipt = storage.upload_plan(
            client,
            config("prod"),
            plan,
            retention_days=90,
            now=now,
            retention_admin_client=retention_admin,
        )
        self.assertEqual(receipt["receipt_schema"], storage.RECEIPT_SCHEMA)
        self.assertEqual(receipt["receipt_role"], "primary")
        self.assertEqual(len(client.put_calls), 2)
        self.assertTrue(
            all(
                "ObjectLockMode" not in call
                and "ObjectLockRetainUntilDate" not in call
                for call in client.put_calls
            )
        )
        self.assertTrue(
            all(
                item["object_lock_mode"] == "GOVERNANCE"
                and item["retain_until"]
                for item in receipt["objects"]
            )
        )
        self.assertTrue(all(item["full_download_verified"] for item in receipt["objects"]))
        self.assertEqual(
            receipt["profiles_used"],
            {
                "object_io": "upload",
                "retention_preflight": "retention_admin",
            },
        )
        self.assertNotIn("put_object", retention_admin.method_calls)
        self.assertNotIn("get_object", retention_admin.method_calls)
        self.assertNotIn("get_object_lock_configuration", client.method_calls)
        receipt_text = json.dumps(receipt)
        self.assertNotIn(
            config("prod").upload_credentials.secret_access_key,
            receipt_text,
        )
        self.assertNotIn(
            config("prod").retention_admin_credentials.secret_access_key,
            receipt_text,
        )

        receipt_path = self.root / "primary_receipt.json"
        storage._write_receipt(receipt, receipt_path)
        records = storage.load_storage_receipt(receipt_path, plan, "primary")
        verified = storage.verify_plan(
            client,
            config("prod"),
            plan,
            records,
            now=now,
            retention_admin_client=retention_admin,
        )
        self.assertTrue(verified["passed"])
        self.assertTrue(all(item["receipt_verified"] for item in verified["objects"]))

        second = storage.upload_plan(
            client,
            config("prod"),
            plan,
            retention_days=90,
            now=now,
            retention_admin_client=retention_admin,
        )
        self.assertEqual(len(client.put_calls), 2)
        self.assertTrue(all(item["action"] == "ALREADY_PRESENT_VERIFIED" for item in second["objects"]))

    def test_bucket_default_retention_is_verified_fail_closed_after_upload(self) -> None:
        upload_client = FakeS3(default_retention_days=30)
        retention_admin = FakeS3(default_retention_days=30)

        with self.assertRaisesRegex(
            storage.StorageSafetyError,
            "REMOTE_RETENTION_MISMATCH",
        ):
            storage.upload_plan(
                upload_client,
                config("prod"),
                self._plan(),
                retention_days=90,
                retention_admin_client=retention_admin,
            )

        self.assertEqual(len(upload_client.put_calls), 1)
        self.assertNotIn("ObjectLockMode", upload_client.put_calls[0])
        self.assertNotIn(
            "ObjectLockRetainUntilDate",
            upload_client.put_calls[0],
        )

    def test_replication_uses_primary_receipt_and_verifies_both_stores(self) -> None:
        primary = FakeS3()
        replica = FakeS3()
        primary_retention = FakeS3()
        replica_retention = FakeS3()
        plan = self._plan()
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        primary_receipt = storage.upload_plan(
            primary,
            config("prod"),
            plan,
            retention_days=30,
            now=now,
            retention_admin_client=primary_retention,
        )
        primary_records = {item["asset_id"]: item for item in primary_receipt["objects"]}
        replica_receipt = storage.replicate_plan(
            primary,
            config("prod"),
            replica,
            config("dr"),
            plan,
            primary_records,
            retention_days=30,
            now=now,
            prod_retention_admin_client=primary_retention,
            dr_retention_admin_client=replica_retention,
        )
        self.assertEqual(replica_receipt["receipt_role"], "replica")
        self.assertEqual(len(replica.put_calls), 2)
        self.assertTrue(all(item["full_download_verified"] for item in replica_receipt["objects"]))
        for item in replica_receipt["objects"]:
            asset = next(asset for asset in plan.objects if asset.asset_id == item["asset_id"])
            self.assertEqual(
                primary.objects[(asset.key, item["primary_version_id"])]["body"],
                replica.objects[(asset.key, item["version_id"])]["body"],
            )

    def test_cli_persists_primary_and_replica_receipts(self) -> None:
        primary = FakeS3()
        replica = FakeS3()
        primary_retention = FakeS3()
        replica_retention = FakeS3()
        with mock.patch.dict(os.environ, self._release_env(), clear=True):
            def client_for_store(store_config, profile_name):
                return {
                    ("prod", "upload"): primary,
                    ("prod", "retention_admin"): primary_retention,
                    ("dr", "upload"): replica,
                    ("dr", "retention_admin"): replica_retention,
                }[(store_config.role, profile_name)]

            with mock.patch.object(storage, "create_s3_client", side_effect=client_for_store):
                with mock.patch("sys.stdout", new=io.StringIO()):
                    code = storage.main(["upload", "--plan", str(self.plan_path), "--retention-days", "30"])
            self.assertEqual(code, 0)
            primary_path = self.root / "primary_receipt.json"
            self.assertTrue(primary_path.is_file())
            primary_raw = json.loads(primary_path.read_text(encoding="utf-8"))
            self.assertEqual(primary_raw["receipt_role"], "primary")

            with mock.patch.object(storage, "create_s3_client", side_effect=client_for_store):
                with mock.patch("sys.stdout", new=io.StringIO()):
                    code = storage.main(["replicate", "--plan", str(self.plan_path), "--retention-days", "30"])
            self.assertEqual(code, 0)
            replica_path = self.root / "replica_receipt.json"
            self.assertTrue(replica_path.is_file())
            replica_raw = json.loads(replica_path.read_text(encoding="utf-8"))
            self.assertEqual(replica_raw["receipt_role"], "replica")
            self.assertEqual(
                {item["asset_id"] for item in replica_raw["objects"]},
                {"master-audio", "release-manifest"},
            )

    def test_verify_rejects_receipt_not_bound_to_plan(self) -> None:
        client = FakeS3()
        plan = self._plan()
        receipt = storage.upload_plan(
            client,
            config("prod"),
            plan,
            retention_days=30,
            retention_admin_client=FakeS3(),
        )
        receipt["objects"][0]["sha256"] = "0" * 64
        receipt_path = self.root / "primary_receipt.json"
        storage._write_receipt(receipt, receipt_path)
        with self.assertRaisesRegex(storage.StorageSafetyError, "INVALID_STORAGE_RECEIPT"):
            storage.load_storage_receipt(receipt_path, plan, "primary")

    def test_audit_reports_current_plus_two_and_has_no_delete_path(self) -> None:
        client = FakeS3()
        release_descriptors = [char * 64 for char in ("a", "c", "d", "e")]
        for index, release_descriptor in enumerate(release_descriptors):
            key = (
                "v1/prod/sprint1/muchiram-gurer-jibanchorit/releases/"
                f"{release_descriptor}/masters/master.mp3"
            )
            body = f"version-{index}".encode()
            client.put_object(
                Bucket=config("prod").bucket,
                Key=key,
                Body=io.BytesIO(body),
                ContentLength=len(body),
                ContentType="audio/mpeg",
                CacheControl="private",
                Metadata={"sha256": hashlib.sha256(body).hexdigest()},
            )
        report = storage.audit_retention(
            client,
            config("prod"),
            "muchiram-gurer-jibanchorit",
            release_descriptors[0],
            retention_admin_client=FakeS3(),
        )
        self.assertEqual(len(report["retained_release_generations"]), 3)
        self.assertEqual(
            report["retained_release_generations"][0]["release_descriptor_sha256"],
            release_descriptors[0],
        )
        self.assertEqual(report["delete_actions"], [])
        self.assertFalse(report["deletion_supported"])
        self.assertTrue(report["passed"])
        self.assertTrue(all(item["governance_locked"] for item in report["retained_release_generations"]))
        self.assertEqual(client.delete_calls, [])


if __name__ == "__main__":
    unittest.main()
