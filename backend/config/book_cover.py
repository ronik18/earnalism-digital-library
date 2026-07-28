"""Validation and persistence helpers for owner-managed book-cover uploads."""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Any

from PIL import Image, UnidentifiedImageError


ALLOWED_BOOK_COVER_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
MIN_BOOK_COVER_WIDTH = 300
MIN_BOOK_COVER_HEIGHT = 400
MAX_BOOK_COVER_DIMENSION = 8000
MIN_BOOK_COVER_ASPECT_RATIO = 0.5
MAX_BOOK_COVER_ASPECT_RATIO = 0.9
BOOK_COVER_KINDS = {"front", "back"}


def canonical_cover_kind(value: str) -> str:
    kind = str(value or "").strip().lower()
    if kind not in BOOK_COVER_KINDS:
        raise ValueError("Cover kind must be front or back.")
    return kind


def validate_book_cover(body: bytes, content_type: str, max_bytes: int) -> dict[str, Any]:
    """Validate raster cover bytes before any remote upload occurs."""
    declared_type = str(content_type or "").split(";", 1)[0].strip().lower()
    if declared_type not in ALLOWED_BOOK_COVER_TYPES:
        raise ValueError("Unsupported image type. Use JPG, PNG, or WebP.")
    if not body:
        raise ValueError("Cover file is empty.")
    if len(body) > max_bytes:
        raise ValueError(f"Cover must be under {max_bytes} bytes.")

    try:
        with Image.open(BytesIO(body)) as image:
            image.verify()
        with Image.open(BytesIO(body)) as image:
            width, height = image.size
            actual_format = image.format or ""
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Cover file is not a readable image.") from exc

    expected_format = ALLOWED_BOOK_COVER_TYPES[declared_type]
    if actual_format != expected_format:
        raise ValueError("Cover content does not match its declared file type.")
    if width < MIN_BOOK_COVER_WIDTH or height < MIN_BOOK_COVER_HEIGHT:
        raise ValueError(
            f"Cover must be at least {MIN_BOOK_COVER_WIDTH}×{MIN_BOOK_COVER_HEIGHT}px."
        )
    if max(width, height) > MAX_BOOK_COVER_DIMENSION:
        raise ValueError(
            f"Cover dimensions must not exceed {MAX_BOOK_COVER_DIMENSION}px."
        )
    aspect_ratio = width / height
    if not MIN_BOOK_COVER_ASPECT_RATIO <= aspect_ratio <= MAX_BOOK_COVER_ASPECT_RATIO:
        raise ValueError("Cover must use a portrait book-cover aspect ratio.")

    return {
        "width": width,
        "height": height,
        "format": actual_format,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "aspect_ratio": round(aspect_ratio, 4),
    }


def build_cover_update_fields(
    kind: str,
    upload_result: dict[str, Any],
    validation: dict[str, Any],
    *,
    updated_at: str,
    updated_by: str,
) -> dict[str, Any]:
    """Return a cover-only database patch; reader/audio fields are never accepted."""
    cover_kind = canonical_cover_kind(kind)
    prefix = "back_cover" if cover_kind == "back" else "cover"
    url_field = "back_cover_url" if cover_kind == "back" else "cover_url"
    image_url_field = (
        "back_cover_image_url" if cover_kind == "back" else "cover_image_url"
    )
    thumbnail_field = (
        "back_cover_thumbnail_url" if cover_kind == "back" else "thumbnail_url"
    )
    blur_field = (
        "back_cover_blur_placeholder" if cover_kind == "back" else "blur_placeholder"
    )
    dominant_color_field = (
        "back_cover_dominant_color" if cover_kind == "back" else "dominant_color"
    )

    return {
        url_field: upload_result["cover_url"],
        image_url_field: upload_result["cover_url"],
        thumbnail_field: upload_result["thumbnail_url"],
        blur_field: upload_result["blur_placeholder"],
        dominant_color_field: upload_result["dominant_color"],
        f"{prefix}_width": int(validation["width"]),
        f"{prefix}_height": int(validation["height"]),
        f"{prefix}_sha256": str(validation["sha256"]),
        f"{prefix}_processing_status": "ready",
        f"{prefix}_processing_error": "",
        f"{prefix}_audit_status": "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW",
        f"{prefix}_updated_at": updated_at,
        f"{prefix}_updated_by": updated_by,
    }
