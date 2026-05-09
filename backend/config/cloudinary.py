import os

import cloudinary
import cloudinary.api
import cloudinary.uploader
from cloudinary.utils import cloudinary_url


def init_cloudinary() -> None:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )


def upload_image(file_bytes, folder: str = "earnalism", public_id=None, resource_type: str = "image") -> dict:
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        public_id=public_id,
        resource_type=resource_type,
        overwrite=True,
        format="auto",
        quality="auto:best",
        colors=True,
        responsive_breakpoints={
            "create_derived": True,
            "bytes_step": 20000,
            "min_width": 320,
            "max_width": 1200,
            "max_images": 5,
        },
    )

    breakpoints = []
    rb = result.get("responsive_breakpoints") or []
    if rb and rb[0].get("breakpoints"):
        breakpoints = rb[0]["breakpoints"]
    srcset = ", ".join(f"{b['secure_url']} {b['width']}w" for b in breakpoints) if breakpoints else ""

    colors = result.get("colors") or []
    dominant_color = colors[0][0] if colors and isinstance(colors[0], (list, tuple)) and colors[0] else "#1A1010"

    return {
        "url": result.get("secure_url") or result.get("url"),
        "public_id": result.get("public_id"),
        "width": result.get("width"),
        "height": result.get("height"),
        "dominant_color": dominant_color,
        "srcset": srcset,
        "format": result.get("format"),
    }


def delete_image(public_id: str) -> bool:
    result = cloudinary.uploader.destroy(public_id)
    return result.get("result") == "ok"


def get_optimized_url(public_id: str, width: int = None, height: int = None, crop: str = "fill") -> str:
    transformation = {"quality": "auto:best", "fetch_format": "auto"}
    if width:
        transformation["width"] = width
    if height:
        transformation["height"] = height
    if width or height:
        transformation["crop"] = crop
    url, _ = cloudinary_url(public_id, **transformation)
    return url
