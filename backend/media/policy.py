"""Current audiobook content-type and browser-cache policy."""

from __future__ import annotations


def audio_asset_content_type(asset_key: str, fallback: str = "") -> str:
    if fallback and fallback != "application/octet-stream":
        return fallback
    return {
        "mp3": "audio/mpeg",
        "timestamps": "application/json",
        "vtt": "text/vtt",
        "chapters": "application/json",
        "meta": "application/json",
        "metadata": "application/json",
        "manifest": "application/json",
    }.get(asset_key, "application/octet-stream")


def audio_asset_cache_control(asset_key: str) -> str:
    if asset_key == "mp3":
        return "private, max-age=600, stale-while-revalidate=3600"
    return "private, max-age=3600, stale-while-revalidate=86400"
