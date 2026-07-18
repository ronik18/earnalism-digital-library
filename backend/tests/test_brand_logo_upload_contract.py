from io import BytesIO

import pytest
from PIL import Image

from backend.config.brand_logo import validate_brand_logo


def image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (256, 96), (255, 255, 255, 0)).save(buffer, format=image_format)
    return buffer.getvalue()


def test_brand_logo_accepts_canva_png_and_returns_dimensions():
    result = validate_brand_logo(image_bytes("PNG"), "image/png", 4 * 1024 * 1024)

    assert result["format"] == "PNG"
    assert result["width"] == 256
    assert result["height"] == 96


def test_brand_logo_rejects_svg_and_content_type_mismatch():
    with pytest.raises(ValueError, match="transparent PNG or WebP"):
        validate_brand_logo(b"<svg></svg>", "image/svg+xml", 4 * 1024 * 1024)
    with pytest.raises(ValueError, match="does not match"):
        validate_brand_logo(image_bytes("PNG"), "image/webp", 4 * 1024 * 1024)


def test_brand_logo_rejects_tiny_images_and_oversized_payloads():
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "white").save(buffer, format="PNG")
    with pytest.raises(ValueError, match="at least"):
        validate_brand_logo(buffer.getvalue(), "image/png", 4 * 1024 * 1024)
    with pytest.raises(ValueError, match="under"):
        validate_brand_logo(image_bytes("PNG"), "image/png", 10)
