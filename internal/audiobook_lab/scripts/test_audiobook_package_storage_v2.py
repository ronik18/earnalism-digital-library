#!/usr/bin/env python3
"""Offline tests for immutable package-v2 B2 storage tooling."""

from __future__ import annotations

import io
import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
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
        public: bool = False,
        default_retention_days: int = 365,
    ) -> None:
        self.versioning = versioning
        self.lock_mode = lock_mode
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


class FakeNativeLifecycleReader:
    def __init__(self, rules: object = None, error: Exception | None = None) -> None:
        self.rules = [] if rules is None else rules
        self.error = error
        self.read_calls = 0

    def read(self):
        self.read_calls += 1
        if self.error is not None:
            raise self.error
        return self.rules


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
            FakeNativeLifecycleReader(),
        )

        self.assertTrue(report["passed"])
        self.assertEqual(upload_client.method_calls, ["head_bucket"])
        self.assertIn(
            "get_object_lock_configuration",
            retention_admin_client.method_calls,
        )
        self.assertNotIn(
            "get_bucket_lifecycle_configuration",
            retention_admin_client.method_calls,
        )
        self.assertEqual(
            report["checks"]["production_lifecycle_source"],
            "B2_NATIVE_API_V4_B2_LIST_BUCKETS",
        )
        self.assertEqual(
            report["profiles_used"],
            {
                "object_io": "upload",
                "retention_preflight": "retention_admin",
            },
        )

    def test_native_lifecycle_reader_lists_only_the_exact_bucket(self) -> None:
        production = config("prod")
        authorization = {
            "accountId": production.account_id,
            "authorizationToken": "opaque-token",
            "apiInfo": {
                "storageApi": {
                    "apiUrl": "https://api001.backblazeb2.com",
                    "allowed": {
                        "capabilities": ["listBuckets"],
                        "buckets": [
                            {
                                "id": "opaque-bucket-id",
                                "name": production.bucket,
                            }
                        ],
                    },
                }
            },
        }
        bucket_list = {
            "buckets": [
                {
                    "accountId": production.account_id,
                    "bucketId": "opaque-bucket-id",
                    "bucketName": production.bucket,
                    "lifecycleRules": [
                        {
                            "fileNamePrefix": "qa/",
                            "daysFromUploadingToHiding": 1,
                            "daysFromHidingToDeleting": 7,
                        }
                    ],
                }
            ]
        }
        with mock.patch.object(
            storage,
            "_native_json_request",
            side_effect=[authorization, bucket_list],
        ) as request:
            rules = storage.create_native_lifecycle_reader(production).read()

        self.assertEqual(len(rules), 1)
        self.assertEqual(request.call_count, 2)
        list_request = request.call_args_list[1].args[0]
        self.assertEqual(list_request.get_method(), "POST")
        self.assertEqual(
            json.loads(list_request.data.decode("utf-8")),
            {
                "accountId": production.account_id,
                "bucketName": production.bucket,
            },
        )

    def test_native_lifecycle_reader_rejects_returned_bucket_id_mismatch(self) -> None:
        production = config("prod")
        authorization = {
            "accountId": production.account_id,
            "authorizationToken": "opaque-token",
            "apiInfo": {
                "storageApi": {
                    "apiUrl": "https://api001.backblazeb2.com",
                    "allowed": {
                        "capabilities": ["listBuckets"],
                        "buckets": [
                            {
                                "id": "authorized-bucket-id",
                                "name": production.bucket,
                            }
                        ],
                    },
                }
            },
        }
        returned = {
            "buckets": [
                {
                    "accountId": production.account_id,
                    "bucketId": "different-bucket-id",
                    "bucketName": production.bucket,
                    "lifecycleRules": [],
                }
            ]
        }
        with mock.patch.object(
            storage,
            "_native_json_request",
            side_effect=[authorization, returned],
        ):
            with self.assertRaisesRegex(
                storage.StorageSafetyError,
                "NATIVE_LIFECYCLE_RESPONSE_INVALID.*exact_bucket_missing",
            ):
                storage.create_native_lifecycle_reader(production).read()

    def test_native_lifecycle_reader_rejects_missing_returned_bucket_id(self) -> None:
        production = config("prod")
        authorization = {
            "accountId": production.account_id,
            "authorizationToken": "opaque-token",
            "apiInfo": {
                "storageApi": {
                    "apiUrl": "https://api001.backblazeb2.com",
                    "allowed": {
                        "capabilities": ["listBuckets"],
                        "buckets": [
                            {
                                "id": "authorized-bucket-id",
                                "name": production.bucket,
                            }
                        ],
                    },
                }
            },
        }
        returned = {
            "buckets": [
                {
                    "accountId": production.account_id,
                    "bucketName": production.bucket,
                    "lifecycleRules": [],
                }
            ]
        }
        with mock.patch.object(
            storage,
            "_native_json_request",
            side_effect=[authorization, returned],
        ):
            with self.assertRaisesRegex(
                storage.StorageSafetyError,
                "NATIVE_LIFECYCLE_RESPONSE_INVALID.*exact_bucket_missing",
            ):
                storage.create_native_lifecycle_reader(production).read()

    def test_native_json_request_refuses_redirect_before_credentials_move(self) -> None:
        requests_seen: list[tuple[str, str | None]] = []

        class RedirectServer(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests_seen.append(
                    (self.path, self.headers.get("Authorization"))
                )
                self.send_response(302)
                self.send_header(
                    "Location",
                    self.path.replace("/source", "/sink"),
                )
                self.end_headers()

            def log_message(self, format, *args):
                return

        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            RedirectServer,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for label, authorization in (
                ("basic", "Basic FAKE_APPLICATION_KEY_FOR_TEST"),
                ("bearer", "FAKE_BEARER_AUTHORIZATION_TOKEN_FOR_TEST"),
            ):
                original_path = f"/{label}/source"
                redirect_path = f"/{label}/sink"
                request = storage.urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}{original_path}",
                    headers={"Authorization": authorization},
                )
                with self.subTest(authorization=label):
                    with self.assertRaisesRegex(
                        storage.StorageSafetyError,
                        "NATIVE_LIFECYCLE_REDIRECT_BLOCKED.*HTTP_302",
                    ) as raised:
                        storage._native_json_request(
                            request,
                            "redirect_probe",
                        )

                    self.assertNotIn(
                        redirect_path,
                        [path for path, _ in requests_seen],
                    )
                    self.assertNotIn(redirect_path, str(raised.exception))
                    self.assertNotIn(authorization, str(raised.exception))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.assertEqual(
            requests_seen,
            [
                ("/basic/source", "Basic FAKE_APPLICATION_KEY_FOR_TEST"),
                ("/bearer/source", "FAKE_BEARER_AUTHORIZATION_TOKEN_FOR_TEST"),
            ],
        )

    def test_native_lifecycle_reader_requires_list_buckets_capability(self) -> None:
        production = config("prod")
        authorization = {
            "accountId": production.account_id,
            "authorizationToken": "opaque-token",
            "apiInfo": {
                "storageApi": {
                    "apiUrl": "https://api001.backblazeb2.com",
                    "allowed": {
                        "capabilities": ["readBuckets"],
                        "buckets": [
                            {
                                "id": "opaque-bucket-id",
                                "name": production.bucket,
                            }
                        ],
                    },
                }
            },
        }
        with mock.patch.object(
            storage,
            "_native_json_request",
            return_value=authorization,
        ):
            with self.assertRaisesRegex(
                storage.StorageSafetyError,
                "NATIVE_LIFECYCLE_CAPABILITY_MISSING",
            ):
                storage.create_native_lifecycle_reader(production).read()

    def test_native_lifecycle_reader_requires_exact_bucket_scope(self) -> None:
        production = config("prod")
        authorization = {
            "accountId": production.account_id,
            "authorizationToken": "opaque-token",
            "apiInfo": {
                "storageApi": {
                    "apiUrl": "https://api001.backblazeb2.com",
                    "allowed": {
                        "capabilities": ["listBuckets"],
                        "buckets": [],
                    },
                }
            },
        }
        with mock.patch.object(
            storage,
            "_native_json_request",
            return_value=authorization,
        ):
            with self.assertRaisesRegex(
                storage.StorageSafetyError,
                "NATIVE_LIFECYCLE_BUCKET_SCOPE_MISMATCH",
            ):
                storage.create_native_lifecycle_reader(production).read()

    def test_native_lifecycle_reader_repr_does_not_expose_credentials(self) -> None:
        production = config("prod")
        representation = repr(
            storage.create_native_lifecycle_reader(production)
        )
        self.assertNotIn(
            production.retention_admin_credentials.access_key_id,
            representation,
        )
        self.assertNotIn(
            production.retention_admin_credentials.secret_access_key,
            representation,
        )

    def test_preflight_rejects_malformed_native_lifecycle_response(self) -> None:
        with self.assertRaisesRegex(
            storage.StorageSafetyError,
            "NATIVE_LIFECYCLE_RESPONSE_INVALID",
        ):
            storage.preflight_store(
                FakeS3(),
                config("prod"),
                retention_admin_client=FakeS3(),
                native_lifecycle_reader=FakeNativeLifecycleReader(
                    [
                        {
                            "fileNamePrefix": "v1/prod/",
                            "daysFromUploadingToHiding": None,
                            "daysFromHidingToDeleting": "thirty",
                        }
                    ]
                ),
            )

    def test_preflight_rejects_malformed_unfinished_upload_lifecycle_field(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            storage.StorageSafetyError,
            "NATIVE_LIFECYCLE_RESPONSE_INVALID.*"
            "daysFromStartingToCancelingUnfinishedLargeFiles_invalid",
        ):
            storage.preflight_store(
                FakeS3(),
                config("prod"),
                retention_admin_client=FakeS3(),
                native_lifecycle_reader=FakeNativeLifecycleReader(
                    [
                        {
                            "fileNamePrefix": "qa/",
                            "daysFromUploadingToHiding": None,
                            "daysFromHidingToDeleting": None,
                            "daysFromStartingToCancelingUnfinishedLargeFiles": 0,
                        }
                    ]
                ),
            )

    def test_native_lifecycle_failure_prevents_any_object_write(self) -> None:
        upload_client = FakeS3()
        with self.assertRaisesRegex(
            storage.StorageSafetyError,
            "NATIVE_LIFECYCLE_API_FAILED",
        ):
            storage.upload_plan(
                upload_client,
                config("prod"),
                self._plan(),
                retention_days=30,
                retention_admin_client=FakeS3(default_retention_days=30),
                native_lifecycle_reader=FakeNativeLifecycleReader(
                    error=storage.StorageSafetyError(
                        "NATIVE_LIFECYCLE_API_FAILED",
                        "list_buckets:HTTP_501",
                    )
                ),
            )
        self.assertEqual(upload_client.put_calls, [])
        self.assertNotIn("put_object", upload_client.method_calls)

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
        reader = FakeNativeLifecycleReader(
            [
                {
                    "fileNamePrefix": "v1/prod/",
                    "daysFromUploadingToHiding": 1,
                    "daysFromHidingToDeleting": 30,
                }
            ]
        )
        report = storage.preflight_store(
            FakeS3(),
            config("prod"),
            retention_admin_client=FakeS3(),
            native_lifecycle_reader=reader,
        )
        self.assertFalse(report["passed"])
        self.assertIn("PRODUCTION_LIFECYCLE_DELETION_CONFIGURED", report["blockers"])

    def test_preflight_rejects_lifecycle_rule_that_hides_live_objects(self) -> None:
        reader = FakeNativeLifecycleReader(
            [
                {
                    "fileNamePrefix": "v1/prod/",
                    "daysFromUploadingToHiding": 30,
                    "daysFromHidingToDeleting": None,
                }
            ]
        )
        report = storage.preflight_store(
            FakeS3(),
            config("prod"),
            retention_admin_client=FakeS3(),
            native_lifecycle_reader=reader,
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
            native_lifecycle_reader=FakeNativeLifecycleReader(),
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
            native_lifecycle_reader=FakeNativeLifecycleReader(),
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
            native_lifecycle_reader=FakeNativeLifecycleReader(),
        )
        self.assertEqual(len(client.put_calls), 2)
        self.assertTrue(all(item["action"] == "ALREADY_PRESENT_VERIFIED" for item in second["objects"]))

    def test_bucket_default_retention_fails_preflight_before_upload(self) -> None:
        upload_client = FakeS3(default_retention_days=30)
        retention_admin = FakeS3(default_retention_days=30)

        with self.assertRaisesRegex(
            storage.StorageSafetyError,
            "GOVERNANCE_DEFAULT_RETENTION_BELOW_REQUIRED",
        ):
            storage.upload_plan(
                upload_client,
                config("prod"),
                self._plan(),
                retention_days=90,
                retention_admin_client=retention_admin,
                native_lifecycle_reader=FakeNativeLifecycleReader(),
            )

        self.assertEqual(upload_client.put_calls, [])
        self.assertEqual(
            retention_admin.method_calls,
            [
                "get_bucket_versioning",
                "get_object_lock_configuration",
                "get_public_access_block",
                "get_bucket_policy_status",
                "get_bucket_acl",
            ],
        )

    def test_thirty_day_default_preflights_and_uploads_for_thirty_days(self) -> None:
        upload_client = FakeS3(default_retention_days=30)
        retention_admin = FakeS3(default_retention_days=30)
        report = storage.preflight_store(
            upload_client,
            config("prod"),
            retention_admin,
            FakeNativeLifecycleReader(),
            minimum_default_retention_days=30,
        )

        self.assertTrue(report["passed"])
        self.assertEqual(
            report["checks"]["object_lock"],
            {
                "enabled": True,
                "default_mode": "GOVERNANCE",
                "default_retention_days_floor": 30,
                "minimum_required_retention_days": 30,
                "retention_requirement_satisfied": True,
            },
        )
        receipt = storage.upload_plan(
            upload_client,
            config("prod"),
            self._plan(),
            retention_days=30,
            retention_admin_client=retention_admin,
            native_lifecycle_reader=FakeNativeLifecycleReader(),
        )
        self.assertTrue(receipt["passed"])
        self.assertEqual(len(upload_client.put_calls), 2)

    def test_replication_uses_primary_receipt_and_verifies_both_stores(self) -> None:
        primary = FakeS3(default_retention_days=30)
        replica = FakeS3(default_retention_days=30)
        primary_retention = FakeS3(default_retention_days=30)
        replica_retention = FakeS3(default_retention_days=30)
        plan = self._plan()
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        primary_receipt = storage.upload_plan(
            primary,
            config("prod"),
            plan,
            retention_days=30,
            now=now,
            retention_admin_client=primary_retention,
            native_lifecycle_reader=FakeNativeLifecycleReader(),
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
            prod_native_lifecycle_reader=FakeNativeLifecycleReader(),
            dr_native_lifecycle_reader=FakeNativeLifecycleReader(),
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
        primary = FakeS3(default_retention_days=30)
        replica = FakeS3(default_retention_days=30)
        primary_retention = FakeS3(default_retention_days=30)
        replica_retention = FakeS3(default_retention_days=30)
        with mock.patch.dict(os.environ, self._release_env(), clear=True):
            def client_for_store(store_config, profile_name):
                return {
                    ("prod", "upload"): primary,
                    ("prod", "retention_admin"): primary_retention,
                    ("dr", "upload"): replica,
                    ("dr", "retention_admin"): replica_retention,
                }[(store_config.role, profile_name)]

            with mock.patch.object(
                storage,
                "create_s3_client",
                side_effect=client_for_store,
            ), mock.patch.object(
                storage,
                "create_native_lifecycle_reader",
                side_effect=lambda _: FakeNativeLifecycleReader(),
            ):
                output = io.StringIO()
                with mock.patch("sys.stdout", new=output):
                    code = storage.main(["preflight", "--retention-days", "30"])
            self.assertEqual(code, 0)
            preflight = json.loads(output.getvalue())
            self.assertTrue(preflight["passed"])
            self.assertTrue(
                all(
                    store["checks"]["object_lock"][
                        "retention_requirement_satisfied"
                    ]
                    for store in preflight["stores"]
                )
            )
            self.assertEqual(primary.put_calls, [])
            self.assertEqual(replica.put_calls, [])

            with mock.patch.object(
                storage,
                "create_s3_client",
                side_effect=client_for_store,
            ), mock.patch.object(
                storage,
                "create_native_lifecycle_reader",
                side_effect=lambda _: FakeNativeLifecycleReader(),
            ):
                with mock.patch("sys.stdout", new=io.StringIO()):
                    code = storage.main(["upload", "--plan", str(self.plan_path), "--retention-days", "30"])
            self.assertEqual(code, 0)
            primary_path = self.root / "primary_receipt.json"
            self.assertTrue(primary_path.is_file())
            primary_raw = json.loads(primary_path.read_text(encoding="utf-8"))
            self.assertEqual(primary_raw["receipt_role"], "primary")

            with mock.patch.object(
                storage,
                "create_s3_client",
                side_effect=client_for_store,
            ), mock.patch.object(
                storage,
                "create_native_lifecycle_reader",
                side_effect=lambda _: FakeNativeLifecycleReader(),
            ):
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

            with mock.patch.object(
                storage,
                "create_s3_client",
                side_effect=client_for_store,
            ), mock.patch.object(
                storage,
                "create_native_lifecycle_reader",
                side_effect=lambda _: FakeNativeLifecycleReader(),
            ):
                with mock.patch("sys.stdout", new=io.StringIO()):
                    code = storage.main(
                        [
                            "verify",
                            "--plan",
                            str(self.plan_path),
                            "--store",
                            "prod",
                            "--minimum-remaining-retention-days",
                            "29",
                        ]
                    )
            self.assertEqual(code, 0)

    def test_verify_rejects_receipt_not_bound_to_plan(self) -> None:
        client = FakeS3()
        plan = self._plan()
        receipt = storage.upload_plan(
            client,
            config("prod"),
            plan,
            retention_days=30,
            retention_admin_client=FakeS3(),
            native_lifecycle_reader=FakeNativeLifecycleReader(),
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
            native_lifecycle_reader=FakeNativeLifecycleReader(),
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
