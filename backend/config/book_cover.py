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
HEX_SHA256 = frozenset("0123456789abcdef")


def canonical_cover_kind(value: str) -> str:
    kind = str(value or "").strip().lower()
    if kind not in BOOK_COVER_KINDS:
        raise ValueError("Cover kind must be front or back.")
    return kind


def content_addressed_cover_candidate_asset_id(slug: str, sha256: str) -> str:
    """Return the immutable per-byte identity used for private cover intake."""
    normalized_slug = str(slug or "").strip().lower()
    digest = str(sha256 or "").strip().lower()
    if not normalized_slug or "/" in normalized_slug or normalized_slug in {".", ".."}:
        raise ValueError("Invalid controlled publication slug.")
    if len(digest) != 64 or set(digest) > HEX_SHA256:
        raise ValueError("Cover candidate SHA-256 is missing or invalid.")
    return f"candidate_controlled-{normalized_slug}-{digest}"


def content_addressed_cover_candidate_public_id(
    slug: str,
    kind: str,
    sha256: str,
) -> str:
    """Return the exact Cloudinary public ID for one immutable candidate."""
    cover_kind = canonical_cover_kind(kind)
    prefix = "back_cover" if cover_kind == "back" else "cover"
    asset_id = content_addressed_cover_candidate_asset_id(slug, sha256)
    return f"earnalism/covers/{cover_kind}/{prefix}_{asset_id}"


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


def build_private_cover_candidate(
    slug: str,
    kind: str,
    upload_result: dict[str, Any],
    validation: dict[str, Any],
    *,
    updated_at: str,
    updated_by: str,
) -> dict[str, Any]:
    """Return a private review candidate that cannot double as public book data."""
    cover_kind = canonical_cover_kind(kind)
    public_id = str(upload_result.get("cloudinary_public_id") or "").strip()
    version = str(upload_result.get("cloudinary_version") or "").strip()
    image_format = str(upload_result.get("cloudinary_format") or "").strip().lower()
    resource_type = str(
        upload_result.get("cloudinary_resource_type") or "image"
    ).strip().lower()
    return {
        "slug": str(slug or "").strip().lower(),
        "kind": cover_kind,
        "candidate_url": upload_result["cover_url"],
        "immutable_candidate_url": upload_result["cover_url"],
        "candidate_thumbnail_url": upload_result["thumbnail_url"],
        "candidate_blur_placeholder": upload_result["blur_placeholder"],
        "candidate_dominant_color": upload_result["dominant_color"],
        "candidate_srcset": upload_result.get("srcset", ""),
        "cloudinary_public_id": public_id,
        "cloudinary_version": version,
        "cloudinary_version_id": str(
            upload_result.get("cloudinary_version_id") or ""
        ).strip(),
        "cloudinary_resource_type": resource_type,
        "cloudinary_format": image_format,
        "cloudinary_bytes": int(upload_result.get("cloudinary_bytes") or 0),
        "width": int(validation["width"]),
        "height": int(validation["height"]),
        "input_format": str(validation["format"]),
        "input_size_bytes": int(validation["bytes"]),
        "sha256": str(validation["sha256"]),
        "processing_status": "ready",
        "processing_error": "",
        "audit_status": "ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW",
        "updated_at": updated_at,
        "updated_by": updated_by,
    }
