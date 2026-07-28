from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from backend.config.book_cover import (
    build_cover_update_fields,
    canonical_cover_kind,
    validate_book_cover,
)


ROOT = Path(__file__).resolve().parents[2]
SERVER_SOURCE = (ROOT / "backend/server.py").read_text(encoding="utf-8")


def image_bytes(image_format: str = "PNG", size: tuple[int, int] = (1200, 1800)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "#6B1020").save(buffer, format=image_format)
    return buffer.getvalue()


def upload_result() -> dict:
    return {
        "cover_url": "https://res.cloudinary.com/demo/image/upload/cover.png",
        "thumbnail_url": "https://res.cloudinary.com/demo/image/upload/w_300/cover.png",
        "blur_placeholder": "https://res.cloudinary.com/demo/image/upload/e_blur/cover.png",
        "dominant_color": "#6B1020",
    }


def test_book_cover_validator_accepts_portrait_png_and_binds_sha256():
    body = image_bytes()
    result = validate_book_cover(body, "image/png", 4 * 1024 * 1024)

    assert result["format"] == "PNG"
    assert result["width"] == 1200
    assert result["height"] == 1800
    assert len(result["sha256"]) == 64
    assert result["bytes"] == len(body)


def test_book_cover_validator_rejects_spoofed_small_and_landscape_files():
    with pytest.raises(ValueError, match="does not match"):
        validate_book_cover(image_bytes(), "image/webp", 4 * 1024 * 1024)
    with pytest.raises(ValueError, match="at least"):
        validate_book_cover(image_bytes(size=(200, 300)), "image/png", 4 * 1024 * 1024)
    with pytest.raises(ValueError, match="portrait"):
        validate_book_cover(image_bytes(size=(1200, 800)), "image/png", 4 * 1024 * 1024)


def test_cover_update_fields_are_side_specific_and_cannot_mutate_release_truth():
    validation = validate_book_cover(image_bytes(), "image/png", 4 * 1024 * 1024)
    fields = build_cover_update_fields(
        "back",
        upload_result(),
        validation,
        updated_at="2026-07-28T00:00:00+00:00",
        updated_by="owner@example.com",
    )

    assert fields["back_cover_image_url"] == upload_result()["cover_url"]
    assert fields["back_cover_audit_status"] == "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW"
    assert fields["back_cover_width"] == 1200
    assert fields["back_cover_height"] == 1800
    forbidden = {
        "reader_enabled",
        "is_published",
        "audiobook_enabled",
        "audio_enabled",
        "audiobook_release_gate",
        "audio_qa_status",
        "audio_url",
    }
    assert forbidden.isdisjoint(fields)


def test_cover_kind_is_fail_closed():
    assert canonical_cover_kind("front") == "front"
    assert canonical_cover_kind(" BACK ") == "back"
    with pytest.raises(ValueError, match="front or back"):
        canonical_cover_kind("spine")


def test_admin_cover_routes_are_authenticated_bounded_and_not_generation_gated():
    cover_route = SERVER_SOURCE.split('@api.post("/admin/books/{slug}/cover")', 1)[1].split(
        '@api.post("/admin/books/{slug}/chapters/{chapter_id}/upload")',
        1,
    )[0]
    status_route = SERVER_SOURCE.split('@api.get("/admin/books/cover-status")', 1)[1].split(
        '@api.get("/admin/books/{slug}")',
        1,
    )[0]

    assert "Depends(require_admin)" in cover_route
    assert "confirm_expensive_job" in cover_route
    assert "ENABLE_ADMIN_COVER_UPLOADS" in cover_route
    assert "ENABLE_COVER_GENERATION" not in cover_route
    assert "validate_book_cover" in cover_route
    assert "admin_upload_audit.insert_one" in cover_route
    assert "Depends(require_admin)" in status_route
    assert "load_controlled_artifact_book" in status_route


def test_persisted_sprint1_inventory_matches_the_32_title_contract():
    report = json.loads(
        (
            ROOT
            / "internal/earnalism_intelligence/catalog_truth/sprint1_missing_cover_inventory_20260728.json"
        ).read_text(encoding="utf-8")
    )

    assert report["summary"] == {
        "sprint1_titles_checked": 32,
        "valid_cover_pairs": 20,
        "missing_both": 11,
        "missing_front_only": 0,
        "missing_back_only": 0,
        "broken_populated_urls": 0,
        "title_mismatched_pairs": 1,
        "titles_needing_remediation": 12,
    }
    assert len(report["books"]) == 12
    assert {book["slug"] for book in report["books"]} >= {
        "pather-panchali",
        "devdas",
        "a-ghost-story",
    }
    assert report["release_truth_unchanged"] is True
