"""A6 proof that PDF scope is non-customer and binaries bypass the v2 cache."""

from __future__ import annotations

import asyncio
import csv
import importlib
import io
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.responses import FileResponse, StreamingResponse

from test_safe_json_cache_migration import _restore_redis, _with_fake_redis


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_pdf_scope")
os.environ.setdefault("JWT_SECRET", "pdf-scope-synthetic")
server = importlib.import_module("backend.server")
codec = importlib.import_module("backend.cache.codec")
policy = importlib.import_module("backend.cache.policy")
cache_keys = importlib.import_module("backend.cache.keys")


def _doc(name: str) -> Path:
    return ROOT / "docs" / "architecture" / "cache-media" / name


def test_pdf_inventory_is_complete_non_ambiguous_and_non_customer():
    inventory = json.loads(_doc("a6-pdf-inventory.json").read_text(encoding="utf-8"))
    classification = json.loads(_doc("a6-pdf-product-classification.json").read_text(encoding="utf-8"))
    assert inventory["unclassified_item_count"] == 0
    assert inventory["ambiguous_customer_facing_item_count"] == 0
    assert inventory["tracked_pdf_file_count"] == 0
    assert classification["classification"] == "EXISTING_INTERNAL_OR_REPORT_PDF_ONLY"
    assert classification["active_customer_pdf_route_count"] == 0
    assert classification["active_customer_pdf_upload_route_count"] == 0
    assert classification["active_customer_pdf_viewer_count"] == 0
    assert classification["active_customer_pdf_model_field_count"] == 0


def test_openapi_and_frontend_have_no_customer_pdf_delivery_surface():
    paths = server.app.openapi()["paths"]
    assert not [path for path in paths if "pdf" in path.lower()]
    frontend = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (ROOT / "frontend" / "src").rglob("*")
        if path.is_file()
    ).lower()
    forbidden = ("react-pdf", "pdfjs", "application/pdf", "<iframe", "<embed", "<object")
    assert not [marker for marker in forbidden if marker in frontend]


def test_pdf_binary_and_stream_like_values_bypass_redis_without_leaking(tmp_path, caplog):
    fake, prior = _with_fake_redis()
    pdf_path = tmp_path / "private-sentinel.pdf"
    pdf_path.write_bytes(b"%PDF-1.7 synthetic")

    def byte_generator():
        yield b"%PDF-1.7 generator"

    async def async_byte_generator():
        yield b"%PDF-1.7 async-generator"

    handle = pdf_path.open("rb")
    buffered = io.BufferedReader(io.BytesIO(b"%PDF-1.7 buffered"))
    values = [
        b"%PDF-1.7 bytes",
        bytearray(b"%PDF-1.7 bytearray"),
        memoryview(b"%PDF-1.7 memoryview"),
        "data:application/pdf;base64,JVBERi0xLjc=",
        handle,
        buffered,
        byte_generator(),
        async_byte_generator(),
        StreamingResponse(iter([b"%PDF-1.7 stream"]), media_type="application/pdf"),
        FileResponse(pdf_path, media_type="application/pdf"),
        {"nested": {"body": b"%PDF-1.7 nested"}},
        {"attachment": "data:application/pdf;base64,JVBERi0xLjc="},
    ]
    try:
        for index, value in enumerate(values):
            asyncio.run(server._redis_cache_set("reader-content", f"pdf-{index}", value, 20))
            assert server._v2_cache_key("reader-content", f"pdf-{index}") not in fake.entries
        assert "private-sentinel.pdf" not in caplog.text
        assert b"%PDF-1.7 bytes" not in caplog.text.encode()
    finally:
        handle.close()
        buffered.close()
        _restore_redis(prior)


def test_safe_pdf_metadata_is_serializable_when_it_contains_no_binary_or_uri():
    metadata = {"filename": "owner-review.pdf", "content_type": "application/pdf", "page_count": 2}
    assert codec.redis_cache_payload_is_media(metadata) is False
    assert codec.decode_v2(codec.encode_v2(metadata, compress_min_bytes=99_999)) == metadata


@pytest.mark.parametrize(
    "value",
    [
        "data:application/pdf;base64,JVBERi0=",
        "data:application/pdf,%25PDF",
        "DATA:APPLICATION/PDF;base64,JVBERi0=",
        " \tdata:application/pdf;charset=utf-8;base64,JVBERi0=",
        "data:application/pdf;name=report.pdf,",
        "data:application/pdf",
        {"nested": ["data:application/pdf;base64,JVBERi0="]},
        {"data:application/pdf;base64,JVBERi0=": "metadata"},
        "data:audio/mpeg;base64,SUQz",
        "data:image/png;base64,iVBORw0KGgo=",
        "data:video/mp4;base64,AAAA",
        "data:application/octet-stream;base64,AA==",
        "data:text/plain,not-approved-for-cache",
        "data:image/svg+xml,%3Csvg%3E",
        "data:font/woff2;base64,AA==",
        "data:unknown/type,opaque",
    ],
)
def test_all_data_uri_forms_are_rejected_recursively(value):
    assert codec.redis_cache_payload_is_media(value) is True
    with pytest.raises(codec.CacheCodecError, match="binary or media"):
        codec.canonical_json_bytes(value)


def test_data_uri_in_normalized_model_is_rejected():
    class SyntheticModel:
        def model_dump(self, *, mode):
            assert mode == "json"
            return {"attachment": "data:application/pdf;base64,JVBERi0="}

    assert codec.redis_cache_payload_is_media(SyntheticModel()) is True


def test_safe_pdf_metadata_and_ordinary_data_text_remain_cacheable():
    value = {
        "content_type": "application/pdf",
        "filename": "report.pdf",
        "page_count": 22,
        "sha256": "a" * 64,
        "object_id": "object-1",
        "note": "The documentation uses data: as a label in prose.",
        "base64_looking": "JVBERi0xLjc=",
    }
    assert codec.redis_cache_payload_is_media(value) is False
    assert codec.decode_v2(codec.encode_v2(value, compress_min_bytes=99_999)) == value


def _metric_count(policy_id, operation, result):
    return sum(
        event["count"]
        for event in importlib.import_module("backend.cache.metrics").snapshot_v2()["events"]
        if event["policy_id"] == policy_id
        and event["operation"] == operation
        and event["result"] == result
        and event["bucket"] == "count"
    )


def test_every_active_policy_bypasses_pdf_data_uri_once_without_logging(caplog):
    fake, prior = _with_fake_redis()
    sentinel = "A6_PDF_DATA_URI_SENTINEL"
    try:
        for namespace, registered in policy.ACTIVE_CACHE_POLICIES.items():
            policy_id = registered.policy_id
            before = _metric_count(policy_id, "write", "binary_or_media")
            asyncio.run(server._redis_cache_set(namespace, f"pdf-uri-{namespace}", f"data:application/pdf;base64,{sentinel}", 20))
            assert server._v2_cache_key(namespace, f"pdf-uri-{namespace}") not in fake.entries
            assert _metric_count(policy_id, "write", "binary_or_media") == before + 1
        assert sentinel not in caplog.text
    finally:
        _restore_redis(prior)


def test_stale_v2_data_uri_is_exact_key_cleaned_and_source_replaced(caplog):
    fake, prior = _with_fake_redis()
    sentinel = "A6_STALE_PDF_DATA_URI_SENTINEL"
    v2_key = server._v2_cache_key("reader-content", "stale-pdf")
    unrelated_key = server._v2_cache_key("reader-content", "unrelated")
    legacy_key = cache_keys.cache_digest_key(server.REDIS_KEY_PREFIX, "reader-content", "stale-pdf")
    stale_raw = json.dumps(f"data:application/pdf;base64,{sentinel}").encode("utf-8")
    try:
        fake.entries[v2_key] = (20, codec.encode_v2_canonical(stale_raw, compress_min_bytes=99_999))
        fake.entries[unrelated_key] = (20, codec.encode_v2({"unrelated": True}, compress_min_bytes=99_999))
        fake.entries[legacy_key] = (20, b"legacy-entry-is-never-read")
        calls = []

        async def loader():
            calls.append("source")
            return {"source": "truth"}

        result = asyncio.run(server._redis_cache_aside("reader-content", "stale-pdf", 20, loader))
        assert result == {"source": "truth"}
        assert calls == ["source"]
        assert fake.deleted == [v2_key]
        assert unrelated_key in fake.entries
        assert legacy_key in fake.entries
        assert codec.decode_v2(fake.entries[v2_key][1]) == {"source": "truth"}
        assert sentinel not in caplog.text
    finally:
        _restore_redis(prior)


def test_pdf_policy_rows_are_documented_but_no_pdf_policy_is_active():
    matrix = json.loads(_doc("cache-policy-matrix.json").read_text(encoding="utf-8"))
    rows = {row["use_case"]: row for row in matrix["rows"]}
    for use_case in ("complete customer PDF binary", "PDF Range fragment", "rendered/generated report PDF"):
        assert rows[use_case]["decision"] == "DO_NOT_CACHE"
        assert rows[use_case]["maximum_serialized_bytes"] == 0
    assert rows["future PDF metadata"]["decision"] == "CONDITIONAL"
    assert "pdf" not in " ".join(policy.ACTIVE_CACHE_POLICIES)
    assert len(policy.ACTIVE_CACHE_POLICIES) == 6


def test_pdf_policy_json_markdown_csv_and_future_contract_remain_consistent():
    matrix = json.loads(_doc("cache-policy-matrix.json").read_text(encoding="utf-8"))
    markdown = _doc("cache-policy-matrix.md").read_text(encoding="utf-8")
    with _doc("cache-policy-matrix.csv").open(encoding="utf-8", newline="") as handle:
        csv_rows = {row["use_case"]: row for row in csv.DictReader(handle)}
    expected = {"complete customer PDF binary", "PDF Range fragment", "rendered/generated report PDF", "future PDF metadata"}
    assert expected <= {row["use_case"] for row in matrix["rows"]}
    assert expected <= set(csv_rows)
    assert all(use_case in markdown for use_case in expected)
    contract = json.loads(_doc("future-customer-pdf-delivery-contract.json").read_text(encoding="utf-8"))
    assert contract["implementation_status"] == "DESIGN_BOUNDARY_ONLY"
    assert contract["pdf_metadata_cache_activated"] is False
