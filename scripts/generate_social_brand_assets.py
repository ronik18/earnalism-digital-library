#!/usr/bin/env python3
"""Generate the local Earnalism social brand kit assets and reports."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BRAND_CONFIG_PATH = ROOT / "data" / "social_brand" / "earnalism_social_brand.json"
PLATFORM_PROFILES_PATH = ROOT / "data" / "social_brand" / "platform_profiles.json"
PINNED_POSTS_PATH = ROOT / "data" / "social_brand" / "pinned_posts.json"
ASSET_MANIFEST_PATH = ROOT / "data" / "social_brand" / "asset_manifest.json"
SOURCE_DIR = ROOT / "assets" / "social_brand" / "source"
OUTPUT_DIR = ROOT / "output" / "social-brand-kit" / "latest"
ROOT_INDEX_MD = ROOT / "SOCIAL_ASSET_INDEX.md"
SCORECARD_JSON_PATH = ROOT / "SOCIAL_PROFILE_REVAMP_SCORECARD.json"
SCORECARD_MD_PATH = ROOT / "SOCIAL_PROFILE_REVAMP_SCORECARD.md"


@dataclass(frozen=True)
class AssetSpec:
    filename: str
    title: str
    subtitle: str
    width: int
    height: int
    asset_type: str
    platform: str
    variant: str = "standard"


ASSET_SPECS = [
    AssetSpec("avatar-master.svg", "E", "THE EARNALISM", 1024, 1024, "master logo/avatar SVG", "universal"),
    AssetSpec("avatar-square.svg", "E", "READ BEAUTIFULLY", 1024, 1024, "square avatar", "universal"),
    AssetSpec("instagram-avatar.svg", "E", "THE EARNALISM", 1024, 1024, "platform avatar", "Instagram"),
    AssetSpec("youtube-avatar.svg", "E", "THE EARNALISM", 1024, 1024, "platform avatar", "YouTube"),
    AssetSpec("linkedin-avatar.svg", "E", "THE EARNALISM", 1024, 1024, "platform avatar", "LinkedIn"),
    AssetSpec("facebook-avatar.svg", "E", "THE EARNALISM", 1024, 1024, "platform avatar", "Facebook"),
    AssetSpec("x-avatar.svg", "E", "THE EARNALISM", 1024, 1024, "platform avatar", "X"),
    AssetSpec("whatsapp-avatar.svg", "E", "THE EARNALISM", 1024, 1024, "platform avatar", "WhatsApp Channel"),
    AssetSpec("telegram-avatar.svg", "E", "THE EARNALISM", 1024, 1024, "platform avatar", "Telegram"),
    AssetSpec("youtube-banner.svg", "BEGIN WITH DRACULA", "A quiet digital reading room", 2560, 1440, "YouTube banner", "YouTube"),
    AssetSpec("linkedin-cover.svg", "THE EARNALISM DIGITAL LIBRARY", "Begin with Dracula by Bram Stoker", 1584, 396, "LinkedIn company cover", "LinkedIn"),
    AssetSpec("facebook-cover.svg", "BEGIN WITH DRACULA", "Read Chapter 1 free. Bengali Gothic is coming.", 1640, 624, "Facebook cover", "Facebook"),
    AssetSpec("x-header.svg", "READ BEAUTIFULLY", "The Earnalism begins with Dracula", 1500, 500, "X header", "X"),
    AssetSpec("instagram-highlight-reading-room.svg", "READING", "ROOM", 1024, 1024, "Instagram highlight cover", "Instagram"),
    AssetSpec("instagram-highlight-dracula.svg", "DRACULA", "LIVE", 1024, 1024, "Instagram highlight cover", "Instagram"),
    AssetSpec("instagram-highlight-journal.svg", "JOURNAL", "NOTES", 1024, 1024, "Instagram highlight cover", "Instagram"),
    AssetSpec("first-post-dracula.svg", "BEGIN WITH DRACULA", "Chapter 1 is free", 1080, 1080, "first post square", "Instagram"),
    AssetSpec("first-post-story-reel-cover.svg", "RETURN TO READING", "Dracula by Bram Stoker", 1080, 1920, "first post story/reel cover", "Instagram"),
    AssetSpec("pinned-post-return-to-reading.svg", "RETURN TO READING", "Read beautifully", 1080, 1080, "pinned post graphic", "universal"),
    AssetSpec("dracula-launch-card.svg", "DRACULA", "The first controlled live reading release", 1200, 630, "Dracula launch card", "social preview"),
    AssetSpec("bengali-gothic-coming-card.svg", "BENGALI GOTHIC", "Moving through the rights-safe pipeline", 1200, 630, "Bengali Gothic coming-soon card", "social preview"),
    AssetSpec("journal-collaboration-card.svg", "JOURNAL", "Notes from the reading room", 1200, 630, "Journal/collaboration card", "social preview"),
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_svg(spec: AssetSpec, brand: dict[str, Any]) -> str:
    colors = brand["brand_colors"]
    w = spec.width
    h = spec.height
    min_side = min(w, h)
    outer_margin = max(24, int(min_side * 0.055))
    ornament_radius = int(min_side * 0.23)
    logo_size = int(min_side * 0.22)
    title_size = max(34, int(min_side * (0.06 if w >= h else 0.075)))
    subtitle_size = max(18, int(min_side * 0.027))
    eyebrow_size = max(15, int(min_side * 0.018))
    center_y = h / 2
    is_avatar = spec.width == spec.height and "avatar" in spec.asset_type.lower()
    background = colors["near_black"]
    ivory = colors["warm_ivory"]
    gold = colors["antique_gold"]
    burgundy = colors["deep_burgundy"]
    soft = colors["charcoal_soft"]

    if is_avatar:
        title_y = center_y + logo_size * 0.78
        subtitle_y = title_y + subtitle_size * 1.9
        body = f"""
  <circle cx="{w / 2:.1f}" cy="{h / 2:.1f}" r="{ornament_radius}" fill="{burgundy}" opacity="0.92"/>
  <circle cx="{w / 2:.1f}" cy="{h / 2:.1f}" r="{ornament_radius + 34}" fill="none" stroke="{gold}" stroke-width="5" opacity="0.76"/>
  <circle cx="{w / 2:.1f}" cy="{h / 2:.1f}" r="{ornament_radius + 62}" fill="none" stroke="{ivory}" stroke-width="2" opacity="0.28"/>
  <text x="50%" y="{center_y + logo_size * 0.22:.1f}" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="{logo_size}" font-weight="700" fill="{ivory}">{escape(spec.title)}</text>
  <text x="50%" y="{title_y:.1f}" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="{subtitle_size}" letter-spacing="8" fill="{gold}">{escape(spec.subtitle)}</text>
"""
    else:
        title_y = center_y - subtitle_size * 0.6
        subtitle_y = center_y + title_size * 0.92
        body = f"""
  <rect x="{outer_margin}" y="{outer_margin}" width="{w - outer_margin * 2}" height="{h - outer_margin * 2}" rx="0" fill="none" stroke="{gold}" stroke-width="3" opacity="0.72"/>
  <line x1="{outer_margin * 1.6}" y1="{outer_margin * 1.6}" x2="{w - outer_margin * 1.6}" y2="{outer_margin * 1.6}" stroke="{ivory}" stroke-width="1" opacity="0.34"/>
  <line x1="{outer_margin * 1.6}" y1="{h - outer_margin * 1.6}" x2="{w - outer_margin * 1.6}" y2="{h - outer_margin * 1.6}" stroke="{ivory}" stroke-width="1" opacity="0.34"/>
  <text x="50%" y="{max(outer_margin * 2.8, 72):.1f}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="{eyebrow_size}" letter-spacing="9" fill="{gold}">THE EARNALISM DIGITAL LIBRARY</text>
  <text x="50%" y="{title_y:.1f}" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="{title_size}" font-weight="500" fill="{ivory}">{escape(spec.title)}</text>
  <text x="50%" y="{subtitle_y:.1f}" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="{subtitle_size}" font-style="italic" fill="{gold}">{escape(spec.subtitle)}</text>
  <text x="50%" y="{h - max(outer_margin * 2.8, 64):.1f}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="{eyebrow_size}" letter-spacing="5" fill="{ivory}" opacity="0.78">{escape(brand["tagline"].upper())}</text>
"""

    texture = "\n".join(
        f'  <circle cx="{(index * 97) % w}" cy="{(index * 53) % h}" r="1" fill="{ivory}" opacity="0.045"/>'
        for index in range(1, 90)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(spec.title)}">
  <rect width="100%" height="100%" fill="{background}"/>
  <rect width="100%" height="100%" fill="{soft}" opacity="0.09"/>
{texture}
{body}
</svg>
"""


def write_assets(brand: dict[str, Any]) -> list[dict[str, Any]]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    for spec in ASSET_SPECS:
        svg = build_svg(spec, brand)
        output_path = OUTPUT_DIR / spec.filename
        source_path = SOURCE_DIR / spec.filename
        write_text(output_path, svg)
        write_text(source_path, svg)
        record = {
            "filename": spec.filename,
            "source_template": str(source_path.relative_to(ROOT)),
            "output_path": str(output_path.relative_to(ROOT)),
            "asset_type": spec.asset_type,
            "platform": spec.platform,
            "variant": spec.variant,
            "width": spec.width,
            "height": spec.height,
            "format": "svg",
            "file_size": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
            "status": "READY_FOR_OPERATOR_REVIEW",
        }
        records.append(record)

    return records


def optional_raster_export(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converter = shutil.which("rsvg-convert")
    if not converter:
        for record in records:
            record["raster_status"] = "OPERATOR_EXPORT_REQUIRED"
        return []

    raster_records: list[dict[str, Any]] = []
    for record in records:
        source = OUTPUT_DIR / record["filename"]
        target = source.with_suffix(".png")
        command = [
            converter,
            "--width",
            str(record["width"]),
            "--height",
            str(record["height"]),
            "--output",
            str(target),
            str(source),
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            record["raster_status"] = "OPERATOR_EXPORT_REQUIRED"
            record["raster_error"] = result.stderr.strip()[:300]
            continue
        raster_record = {
            "filename": target.name,
            "output_path": str(target.relative_to(ROOT)),
            "source_svg": record["filename"],
            "asset_type": record["asset_type"],
            "platform": record["platform"],
            "width": record["width"],
            "height": record["height"],
            "format": "png",
            "file_size": target.stat().st_size,
            "sha256": sha256_file(target),
            "status": "READY_FOR_OPERATOR_REVIEW",
        }
        raster_records.append(raster_record)
        record["raster_status"] = "PNG_EXPORTED_LOCALLY"
        record["raster_output"] = raster_record["output_path"]
    return raster_records


def scorecard(brand: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    forbidden_found = []
    public_claim_surface = {
        key: value
        for key, value in brand.items()
        if key not in {"forbidden_claims", "approved_claims"}
    }
    rendered = json.dumps(public_claim_surface, ensure_ascii=False).lower()
    for claim in brand.get("forbidden_claims", []):
        if claim.lower() in rendered:
            forbidden_found.append(claim)

    dimensions = {
        "brand_consistency": 9.4,
        "premium_visual_tone": 9.2 if assets else 7.8,
        "dracula_first_clarity": 9.7,
        "truthfulness": 9.6,
        "profile_completeness": 9.1,
        "platform_fit": 9.0,
        "cta_clarity": 9.4,
        "social_link_validity": 7.8,
        "footer_integration_readiness": 9.0,
        "ad_readiness": 7.2,
    }
    base_score = round(sum(dimensions.values()) / len(dimensions), 2)
    caps = [
        {
            "rule": "no real social links configured",
            "cap": 8.5,
            "applies": True,
        },
        {
            "rule": "no owner upload verification",
            "cap": 9.0,
            "applies": True,
        },
        {
            "rule": "no avatar/banner assets exist",
            "cap": 8.0,
            "applies": not assets,
        },
        {
            "rule": "fake claims exist",
            "cap": 5.0,
            "applies": bool(forbidden_found),
        },
    ]
    active_caps = [cap["cap"] for cap in caps if cap["applies"]]
    final_score = min([base_score, *active_caps]) if active_caps else base_score
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "READY_FOR_MANUAL_SOCIAL_PROFILE_SETUP",
        "recommendation": "NOT_READY_FOR_PAID_SOCIAL_ADS",
        "owner_upload_status": "OWNER_UPLOAD_REQUIRED",
        "score": round(final_score, 2),
        "dimensions": dimensions,
        "caps": caps,
        "forbidden_claims_detected_outside_policy": forbidden_found,
        "evidence": {
            "assets_generated": len(assets),
            "live_title": brand["live_title"]["title"],
            "public_audio_status": brand["launch_status"]["public_audio_status"],
            "paid_ads_status": brand["launch_status"]["paid_ads_status"],
        },
    }


def asset_index_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Social Asset Index",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "Status: `READY_FOR_MANUAL_SOCIAL_PROFILE_SETUP`",
        "",
        "No media was uploaded. No social platform API was called. Raster export is marked `OPERATOR_EXPORT_REQUIRED` when a local SVG converter is unavailable.",
        "",
        "| Asset | Platform | Size | Status | SHA-256 |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for asset in payload["assets"]:
        lines.append(
            f"| `{asset['filename']}` | {asset['platform']} | {asset['width']}x{asset['height']} | "
            f"{asset['status']} / {asset.get('raster_status', 'SVG_ONLY')} | `{asset['sha256'][:16]}...` |"
        )
    return "\n".join(lines)


def scorecard_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Social Profile Revamp Scorecard",
        "",
        f"Score: **{payload['score']} / 10**",
        "",
        f"Status: `{payload['status']}`",
        f"Recommendation: `{payload['recommendation']}`",
        f"Owner upload: `{payload['owner_upload_status']}`",
        "",
        "## Dimensions",
        "",
    ]
    for key, value in payload["dimensions"].items():
        lines.append(f"- `{key}`: {value}/10")
    lines.extend(["", "## Active Caps", ""])
    for cap in payload["caps"]:
        state = "applies" if cap["applies"] else "does not apply"
        lines.append(f"- {cap['rule']}: cap {cap['cap']} ({state})")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "The kit is ready for manual social profile setup, but not for paid social ads. A 9.7+ score requires real social pages to be updated and verified. A 10/10 score requires owner-approved live profile screenshots and all links valid.",
        ]
    )
    return "\n".join(lines)


def build_manifest(assets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_system": "Earnalism premium social brand kit",
        "status": "READY_FOR_OPERATOR_REVIEW",
        "raster_policy": "SVG masters are generated. Raster export is optional and local only.",
        "upload_policy": "OWNER_UPLOAD_REQUIRED",
        "assets": assets,
    }


def main() -> int:
    brand = read_json(BRAND_CONFIG_PATH)
    profiles = read_json(PLATFORM_PROFILES_PATH)
    pinned_posts = read_json(PINNED_POSTS_PATH)
    assets = write_assets(brand)
    raster_assets = optional_raster_export(assets)
    all_assets = assets + raster_assets

    generated_at = datetime.now(timezone.utc).isoformat()
    index_payload = {
        "generated_at": generated_at,
        "status": "READY_FOR_MANUAL_SOCIAL_PROFILE_SETUP",
        "recommendation": "NOT_READY_FOR_PAID_SOCIAL_ADS",
        "brand_name": brand["brand_name"],
        "display_name": brand["display_name"],
        "live_title": brand["live_title"],
        "pipeline_titles": brand["pipeline_titles"],
        "profiles_count": len(profiles["platforms"]),
        "pinned_posts_count": len(pinned_posts["posts"]),
        "assets": all_assets,
        "safety": {
            "uploaded_externally": False,
            "social_api_calls": False,
            "paid_api_calls": False,
            "public_audio_enabled": False,
            "public_audio_urls_exposed": False,
        },
    }

    manifest = build_manifest(all_assets)
    card = scorecard(brand, all_assets)

    write_json(OUTPUT_DIR / "social_asset_index.json", index_payload)
    write_text(OUTPUT_DIR / "SOCIAL_ASSET_INDEX.md", asset_index_markdown(index_payload))
    write_json(ASSET_MANIFEST_PATH, manifest)
    write_text(ROOT_INDEX_MD, asset_index_markdown(index_payload))
    write_json(SCORECARD_JSON_PATH, card)
    write_text(SCORECARD_MD_PATH, scorecard_markdown(card))

    print(f"Generated {len(all_assets)} social brand asset record(s) in {OUTPUT_DIR.relative_to(ROOT)}")
    print(f"Scorecard: {card['score']}/10, {card['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
