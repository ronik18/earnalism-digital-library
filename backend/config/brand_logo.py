"""Validation rules for owner-managed brand logo uploads."""

from io import BytesIO

from PIL import Image, UnidentifiedImageError


ALLOWED_BRAND_LOGO_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
MIN_BRAND_LOGO_DIMENSION = 32
MAX_BRAND_LOGO_DIMENSION = 4096


def validate_brand_logo(body: bytes, content_type: str, max_bytes: int) -> dict:
    """Validate a raster logo without persisting or exposing its contents."""
    if content_type not in ALLOWED_BRAND_LOGO_TYPES:
        raise ValueError("Unsupported logo type. Export a transparent PNG or WebP from Canva.")
    if not body:
        raise ValueError("Logo file is empty.")
    if len(body) > max_bytes:
        raise ValueError(f"Logo must be under {max_bytes} bytes.")

    try:
        with Image.open(BytesIO(body)) as image:
            image.verify()
        with Image.open(BytesIO(body)) as image:
            width, height = image.size
            actual_format = image.format or ""
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Logo file is not a readable image.") from exc

    expected_format = ALLOWED_BRAND_LOGO_TYPES[content_type]
    if actual_format != expected_format:
        raise ValueError("Logo content does not match its declared file type.")
    if min(width, height) < MIN_BRAND_LOGO_DIMENSION:
        raise ValueError(f"Logo must be at least {MIN_BRAND_LOGO_DIMENSION}×{MIN_BRAND_LOGO_DIMENSION}px.")
    if max(width, height) > MAX_BRAND_LOGO_DIMENSION:
        raise ValueError(f"Logo dimensions must not exceed {MAX_BRAND_LOGO_DIMENSION}px.")

    return {
        "width": width,
        "height": height,
        "format": actual_format,
        "bytes": len(body),
    }
