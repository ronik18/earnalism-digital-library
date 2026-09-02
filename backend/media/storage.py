"""Current explicit-store URL matching and synchronous B2 operation wrappers."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, Mapping, Optional
from urllib.parse import unquote, urlparse


REQUIRED_STORE_FIELDS = ("endpoint", "region", "bucket", "access_key_id", "secret_access_key")


def storage_for_url(url: str, stores: Iterable[Mapping[str, str]]) -> Optional[Mapping[str, str]]:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"}:
        return None
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    for store in stores:
        endpoint_host = urlparse(str(store["endpoint"])).netloc
        path_style = bool(endpoint_host and parsed.netloc == endpoint_host and path_parts and path_parts[0] == store["bucket"])
        virtual_hosted = bool(endpoint_host and parsed.netloc == f"{store['bucket']}.{endpoint_host}" and path_parts)
        if path_style or virtual_hosted:
            return store
    return None


def is_configured(storage: Optional[Mapping[str, str]] = None, stores: Iterable[Mapping[str, str]] = ()) -> bool:
    if storage is not None:
        return all(storage.get(field) for field in REQUIRED_STORE_FIELDS)
    return any(store.get("name") == "primary" for store in stores)


def key_from_url(url: str, storage: Optional[Mapping[str, str]], *, fallback_bucket: str, fallback_endpoint: str) -> str:
    parsed = urlparse(url or "")
    path_parts = [unquote(part) for part in parsed.path.split("/") if part]
    if not path_parts:
        return ""
    selected = storage or {}
    bucket = str(selected.get("bucket") or fallback_bucket)
    endpoint_host = urlparse(str(selected.get("endpoint") or fallback_endpoint)).netloc
    if endpoint_host and parsed.netloc == f"{bucket}.{endpoint_host}":
        return "/".join(path_parts)
    if bucket and path_parts[0] == bucket:
        return "/".join(path_parts[1:])
    return ""


def storage_error_http_status(exc: BaseException) -> int:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return 0
    metadata = response.get("ResponseMetadata")
    try:
        return int((metadata or {}).get("HTTPStatusCode") or 0)
    except (TypeError, ValueError):
        return 0


async def head_object(s3: Any, *, bucket: str, key: str, version_id: str = "") -> dict:
    kwargs = {"Bucket": bucket, "Key": key}
    if version_id:
        kwargs["VersionId"] = version_id
    return await asyncio.to_thread(s3.head_object, **kwargs)


async def get_object(s3: Any, *, bucket: str, key: str, byte_range: Optional[str], version_id: str = "") -> dict:
    kwargs = {"Bucket": bucket, "Key": key}
    if byte_range:
        kwargs["Range"] = byte_range
    if version_id:
        kwargs["VersionId"] = version_id
    return await asyncio.to_thread(s3.get_object, **kwargs)
