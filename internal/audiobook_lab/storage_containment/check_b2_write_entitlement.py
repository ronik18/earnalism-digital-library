#!/usr/bin/env python3
from __future__ import annotations

import os
import uuid
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def require_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise SystemExit(f"missing env: {name}")
    return value


def make_client(prefix: str):
    return boto3.client(
        "s3",
        endpoint_url=require_env(f"{prefix}_S3_ENDPOINT"),
        aws_access_key_id=require_env(f"{prefix}_ACCESS_KEY_ID"),
        aws_secret_access_key=require_env(f"{prefix}_SECRET_ACCESS_KEY"),
        region_name=require_env(f"{prefix}_REGION"),
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def check() -> int:
    bucket = require_env("B2_PRIVATE_QA_BUCKET")
    client = make_client("B2")

    try:
        client.head_bucket(Bucket=bucket)
        print("head_bucket=OK")
    except ClientError as exc:
        print(f"head_bucket=FAIL {exc.response.get('Error', {}).get('Code')} {exc.response.get('Error', {}).get('Message')}")
        return 2

    key = f"storage-containment/_preflight/{uuid.uuid4()}.bin"
    body = b"preflight"
    try:
        client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/octet-stream")
        print("put_object=OK")
    except ClientError as exc:
        err = exc.response.get("Error", {})
        print(f"put_object=FAIL {err.get('Code')} {err.get('Message')}")
        return 3

    try:
        client.delete_object(Bucket=bucket, Key=key)
        print("delete_object=OK")
    except ClientError as exc:
        err = exc.response.get("Error", {})
        print(f"delete_object=FAIL {err.get('Code')} {err.get('Message')}")
        return 4

    mpu_key = f"storage-containment/_preflight/{uuid.uuid4()}.bin"
    upload_id = None
    try:
        resp = client.create_multipart_upload(Bucket=bucket, Key=mpu_key)
        upload_id = resp["UploadId"]
        print("create_multipart_upload=OK")
    except ClientError as exc:
        err = exc.response.get("Error", {})
        print(f"create_multipart_upload=FAIL {err.get('Code')} {err.get('Message')}")
        return 5
    finally:
        if upload_id:
            try:
                client.abort_multipart_upload(Bucket=bucket, Key=mpu_key, UploadId=upload_id)
                print("abort_multipart_upload=OK")
            except ClientError:
                print("abort_multipart_upload=FAIL")

    return 0


if __name__ == "__main__":
    raise SystemExit(check())
