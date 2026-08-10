from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend" / "public"


def test_installable_app_icons_are_focused_rgba_assets_with_any_purpose():
    manifest = json.loads((PUBLIC / "site.webmanifest").read_text(encoding="utf-8"))
    icons = {icon["sizes"]: icon for icon in manifest["icons"]}

    assert {"192x192", "512x512"} <= icons.keys()
    for size in ("192x192", "512x512"):
        icon = icons[size]
        assert icon["purpose"] == "any"
        relative = icon["src"].split("?", 1)[0].lstrip("/")
        asset = PUBLIC / relative
        data = asset.read_bytes()
        assert asset.exists()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert data[25] == 6  # PNG color type 6: truecolor with alpha.


def test_html_references_cache_busted_focused_icon_derivatives():
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")

    assert "favicon.png?v=20260810-focused" in html
    assert "earnalism-app-icon-192.png?v=20260810-focused" in html
    assert "apple-touch-icon.png?v=20260810-focused" in html
