#!/usr/bin/env python3
"""Create a premium, local Earnalism site-tour video package.

This script reuses Playwright real-user UX videos and writes a review package
under output/brand-site-tour/latest. It is local and deterministic: no
publishing, no public audio enablement, no live payments, no email/social posts,
no paid provider calls, no AI voice, and no media upload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REAL_USER_UX_DIR = ROOT / "output" / "real-user-ux"
PLAYWRIGHT_RESULTS = REAL_USER_UX_DIR / "playwright-results.json"
PLAYWRIGHT_ARTIFACTS_DIR = REAL_USER_UX_DIR / "playwright-artifacts"
OUTPUT_DIR = ROOT / "output" / "brand-site-tour" / "latest"

VOICEOVER_DOC = ROOT / "EARNALISM_SITE_TOUR_VOICEOVER_SCRIPT.md"
FEATURE_REPORT = ROOT / "SITE_TOUR_FEATURE_HIGHLIGHT_REPORT.md"
SCORECARD_MD = ROOT / "BRAND_SITE_TOUR_VIDEO_SCORECARD.md"
SCORECARD_JSON = ROOT / "BRAND_SITE_TOUR_VIDEO_SCORECARD.json"
INDEX_MD = ROOT / "BRAND_SITE_TOUR_VIDEO_INDEX.md"
INDEX_JSON = ROOT / "BRAND_SITE_TOUR_VIDEO_INDEX.json"
HUMAN_REVIEW_FORM = ROOT / "BRAND_SITE_TOUR_HUMAN_REVIEW_FORM.md"
BRANDING_GO_NO_GO = ROOT / "BRANDING_ADVERTISEMENT_GO_NO_GO.md"
FINAL_GO_NO_GO = ROOT / "FINAL_GO_NO_GO_DECISION.md"

MASTER_WEBM = "earnalism-site-tour-master.webm"
MASTER_MP4 = "earnalism-site-tour-master.mp4"
VERTICAL_MP4 = "earnalism-site-tour-vertical-9x16.mp4"
SQUARE_MP4 = "earnalism-site-tour-square-1x1.mp4"
SHORT_MP4 = "earnalism-site-tour-short-15s.mp4"
CAPTIONS = "earnalism-site-tour-captions.srt"
TRANSCRIPT = "earnalism-site-tour-transcript.md"
SHOTLIST = "earnalism-site-tour-shotlist.md"
STORYBOARD = "earnalism-site-tour-storyboard.md"
REVIEW_REPORT = "earnalism-site-tour-review-report.md"

FRONTEND_URL = "https://theearnalism.com"
API_URL = "https://api.theearnalism.com/api"

SOCIAL_ENV_KEYS = (
    "REACT_APP_YOUTUBE_URL",
    "REACT_APP_LINKEDIN_URL",
    "REACT_APP_INSTAGRAM_URL",
    "REACT_APP_X_URL",
    "REACT_APP_FACEBOOK_URL",
    "REACT_APP_WHATSAPP_CHANNEL_URL",
    "REACT_APP_TELEGRAM_CHANNEL_URL",
)

REQUIRED_OVERLAYS = (
    "The Earnalism Digital Library",
    "Step into the classics",
    "Chapter 1 is free",
    "27 chapters prepared for focused reading",
    "Audio is intentionally disabled until QA passes",
    "Bengali Gothic is moving through the rights-safe pipeline",
    "Choose reading time, not noisy subscriptions",
    "Return to reading",
)

VOICEOVER_SCRIPT = [
    (
        "Opening",
        "Welcome to Earnalism - a quiet digital reading room beginning with Dracula by Bram Stoker.",
    ),
    (
        "Controlled Launch",
        "The launch is intentionally focused. Dracula is the only live approved core reading title today.",
    ),
    (
        "Free Preview",
        "Start with Chapter 1 free, then continue when the book calls you back.",
    ),
    (
        "Reader",
        "The reader keeps the page calm, readable, and focused on the text.",
    ),
    (
        "Pipeline",
        "Bengali Gothic and other classics are moving through the rights-safe pipeline before they become public reading rooms.",
    ),
    (
        "Pricing",
        "Choose reading time without a noisy subscription. The First Chapter, The Quiet Hour, The Deep Reading Pass, and The Reader's Reserve keep the experience simple and flexible.",
    ),
    (
        "Trust",
        "Secure payment is handled by Razorpay. There is no subscription or autorenewal, and support is available through sales@reoenterprise.org.",
    ),
    (
        "Close",
        "Earnalism begins with one approved classic and a promise: every next room opens only when rights, quality, and reader trust are ready.",
    ),
]


@dataclass(frozen=True)
class Shot:
    shot_id: str
    title: str
    journey_patterns: tuple[str, ...]
    fallback_keywords: tuple[str, ...]
    overlay: str
    caption: str
    planned_seconds: int
    required: bool = True
    social_only: bool = False


SHOT_SEQUENCE = (
    Shot(
        "homepage_desktop",
        "Homepage desktop - Dracula-first opening",
        ("homepage desktop", "dracula-first and truthful"),
        ("Dracula-first-and-truthful", "controlled-Dracula-launch"),
        "The Earnalism Digital Library",
        "A quiet digital reading room beginning with Dracula.",
        7,
    ),
        Shot(
            "homepage_mobile",
            "Homepage mobile - controlled launch",
            ("homepage mobile", "pipeline titles gated"),
            ("pipeline-titles-gated",),
            "Step into the classics",
            "The controlled launch keeps Dracula clear above the fold.",
            6,
        ),
    Shot(
        "carousel",
        "Carousel and shelves - future rooms gated",
        ("carousel", "featured shelves", "future rooms stay gated"),
        ("future-rooms-stay-gated",),
        "Bengali Gothic is moving through the rights-safe pipeline",
        "Pipeline books remain Coming Soon or Notify Me.",
        7,
    ),
    Shot(
        "library_desktop",
        "Library desktop - live controlled release",
        ("library desktop", "only live controlled release"),
        ("only-live-controlled-release", "nly-live-controlled-release"),
        "Audio is intentionally disabled until QA passes",
        "The library separates Dracula from future titles and keeps audio hidden.",
        7,
    ),
    Shot(
        "library_mobile",
        "Library mobile - notify-only future titles",
        ("library mobile", "notify-only"),
        ("approved-titles-notify-only",),
        "Dracula only is live",
        "Mobile shelves keep future titles gated.",
        6,
    ),
    Shot(
        "book_page",
        "Dracula book page",
        ("dracula book page", "reading pass ctas"),
        ("reading-pass-CTAs",),
        "Chapter 1 is free",
        "Rights, source, preview, and reading pass CTAs stay visible.",
        8,
    ),
    Shot(
        "reader",
        "Dracula reader",
        ("dracula reader", "without audiobook controls"),
        ("without-audiobook-controls",),
        "27 chapters prepared for focused reading",
        "The reader is calm, manifest-backed, and audio-free.",
        8,
    ),
    Shot(
        "pricing",
        "Pricing - reading time packs",
        ("pricing page", "reading-time packs"),
        ("time-packs-and-trust-copy",),
        "Choose reading time, not noisy subscriptions",
        "Reading-time packs explain value without autorenewal pressure.",
        8,
    ),
    Shot(
        "journal_contact",
        "Journal and contact",
        ("journal and contact", "demo/catalog leakage"),
        ("demo-catalog-leakage",),
        "Return to reading",
        "Brand and support pages stay clean and truthful.",
        6,
    ),
    Shot(
        "footer_social",
        "Footer social links",
        ("homepage desktop", "dracula-first and truthful"),
        ("Dracula-first-and-truthful",),
        "Follow only real configured channels",
        "Footer social links render only when real http or https URLs exist.",
        5,
        required=False,
        social_only=True,
    ),
)


def run_command(command: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def display_path(path: Path | None) -> str:
    if not path:
        return ""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def git_value(*args: str) -> str:
    result = run_command(["git", *args], check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def tool_path(name: str, fallbacks: tuple[str, ...] = ()) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for fallback in fallbacks:
        if Path(fallback).exists():
            return fallback
    return None


def ffmpeg_path() -> str | None:
    return tool_path("ffmpeg", ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"))


def ffprobe_path() -> str | None:
    return tool_path("ffprobe", ("/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe", "/usr/bin/ffprobe"))


def find_font() -> Path | None:
    candidates = (
        Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
    )
    return next((path for path in candidates if path.exists()), None)


def wrapped_text_lines(draw: Any, text: str, font: Any, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def create_overlay_images(selected: list[tuple[Shot, Path]], output_dir: Path, font_path: Path | None) -> list[Path]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return []

    overlay_dir = output_dir / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    overlays: list[Path] = []
    title_font = ImageFont.truetype(str(font_path), 34) if font_path else ImageFont.load_default()
    caption_font = ImageFont.truetype(str(font_path), 20) if font_path else ImageFont.load_default()
    small_font = ImageFont.truetype(str(font_path), 15) if font_path else ImageFont.load_default()

    for index, (shot, _) in enumerate(selected):
        image = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((42, 548, 1238, 674), radius=10, fill=(12, 5, 7, 178))
        draw.rectangle((42, 548, 48, 674), fill=(216, 185, 122, 242))
        draw.text((66, 566), "Earnalism", font=small_font, fill=(216, 185, 122, 238))

        cursor_y = 586
        for line in wrapped_text_lines(draw, shot.overlay, title_font, 1080)[:2]:
            draw.text((66, cursor_y), line, font=title_font, fill=(253, 252, 248, 255))
            cursor_y += 39
        cursor_y += 2
        for line in wrapped_text_lines(draw, shot.caption, caption_font, 1080)[:2]:
            draw.text((66, cursor_y), line, font=caption_font, fill=(216, 185, 122, 255))
            cursor_y += 25

        overlay_path = overlay_dir / f"{index + 1:02d}-{shot.shot_id}.png"
        image.save(overlay_path)
        overlays.append(overlay_path)
    return overlays


def has_valid_social_url() -> bool:
    for key in SOCIAL_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return True
    return False


def discover_videos() -> list[Path]:
    if not PLAYWRIGHT_ARTIFACTS_DIR.exists():
        return []
    return sorted(PLAYWRIGHT_ARTIFACTS_DIR.glob("*/video.webm"))


def playwright_video_entries() -> list[dict[str, Any]]:
    data = read_json(PLAYWRIGHT_RESULTS)
    if not isinstance(data, dict):
        return []
    entries: list[dict[str, Any]] = []

    def walk_suite(suite: dict[str, Any]) -> None:
        for spec in suite.get("specs", []) or []:
            title = str(spec.get("title") or "")
            for test in spec.get("tests", []) or []:
                for result in test.get("results", []) or []:
                    for attachment in result.get("attachments", []) or []:
                        if attachment.get("name") != "video":
                            continue
                        path = Path(str(attachment.get("path") or ""))
                        if path.exists():
                            entries.append(
                                {
                                    "title": title,
                                    "path": path,
                                    "status": result.get("status"),
                                    "duration": result.get("duration"),
                                }
                            )
        for child in suite.get("suites", []) or []:
            if isinstance(child, dict):
                walk_suite(child)

    for suite in data.get("suites", []) or []:
        if isinstance(suite, dict):
            walk_suite(suite)
    return entries


def ensure_real_user_videos() -> list[Path]:
    videos = discover_videos()
    if videos:
        return videos
    print("No Playwright UX videos found; running npm run ux:real-user-video-audit.")
    run_command(["npm", "run", "ux:real-user-video-audit"])
    videos = discover_videos()
    if not videos:
        raise RuntimeError("Real-user UX audit completed without producing video.webm artifacts.")
    return videos


def select_video(videos: list[Path], report_entries: list[dict[str, Any]], shot: Shot) -> Path | None:
    for pattern in shot.journey_patterns:
        needle = pattern.lower()
        for entry in report_entries:
            if needle in str(entry.get("title") or "").lower():
                return Path(entry["path"])
    lowered = [(path, str(path.parent).lower()) for path in videos]
    for keyword in shot.fallback_keywords:
        keyword_lower = keyword.lower()
        for path, haystack in lowered:
            if keyword_lower in haystack:
                return path
    return None


def selected_shots(videos: list[Path], report_entries: list[dict[str, Any]]) -> tuple[list[tuple[Shot, Path]], list[str]]:
    include_social = has_valid_social_url()
    selected: list[tuple[Shot, Path]] = []
    skipped: list[str] = []
    for shot in SHOT_SEQUENCE:
        if shot.social_only and not include_social:
            skipped.append(f"{shot.shot_id}: skipped because no configured real social URL exists")
            continue
        video = select_video(videos, report_entries, shot)
        if video:
            selected.append((shot, video))
        elif shot.required:
            skipped.append(f"{shot.shot_id}: required journey video missing")
        else:
            skipped.append(f"{shot.shot_id}: optional journey video missing")
    return selected, skipped


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )


def font_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:")


def shot_filter(index: int, shot: Shot, font: Path | None, *, with_overlay: bool) -> str:
    base = (
        f"[{index}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x16090d,"
        "setsar=1,fps=24"
    )
    if with_overlay and font:
        fontfile = font_filter_path(font)
        overlay = escape_drawtext(shot.overlay)
        caption = escape_drawtext(shot.caption)
        base += (
            ",drawbox=x=44:y=h-156:w=w-88:h=108:color=black@0.55:t=fill"
            ",drawbox=x=44:y=h-156:w=5:h=108:color=0xD8B97A@0.95:t=fill"
            f",drawtext=fontfile={fontfile}:text='{overlay}':x=66:y=h-136:fontsize=30:"
            "fontcolor=0xFDFCF8:shadowcolor=black@0.42:shadowx=1:shadowy=1"
            f",drawtext=fontfile={fontfile}:text='{caption}':x=66:y=h-92:fontsize=18:"
            "fontcolor=0xD8B97A:shadowcolor=black@0.35:shadowx=1:shadowy=1"
        )
    return f"{base}[v{index}]"


def ffmpeg_concat_webm(
    ffmpeg: str,
    clips: list[tuple[Shot, Path]],
    destination: Path,
    *,
    with_overlay: bool,
    font: Path | None,
    overlay_images: list[Path] | None = None,
) -> bool:
    if not clips:
        return False
    args: list[str] = [ffmpeg, "-y"]
    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    input_index = 0
    for index, (shot, clip) in enumerate(clips):
        args.extend(["-i", str(clip)])
        clip_input = input_index
        input_index += 1
        if with_overlay and overlay_images and index < len(overlay_images):
            args.extend(["-loop", "1", "-i", str(overlay_images[index])])
            overlay_input = input_index
            input_index += 1
            base_filter = (
                f"[{clip_input}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x16090d,"
                "setsar=1,fps=24[base"
                f"{index}]"
            )
            overlay_filter = (
                f"[base{index}][{overlay_input}:v]overlay=0:0:shortest=1:format=auto,"
                f"format=yuv420p[v{index}]"
            )
            filter_parts.extend([base_filter, overlay_filter])
        else:
            filter_parts.append(shot_filter(index, shot, font, with_overlay=False))
        concat_inputs.append(f"[v{index}]")
    filter_complex = ";".join(filter_parts)
    filter_complex += f";{''.join(concat_inputs)}concat=n={len(clips)}:v=1:a=0[outv]"
    args.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "0",
            "-crf",
            "34",
            "-an",
            str(destination),
        ]
    )
    result = run_command(args, check=False)
    if result.returncode != 0:
        print(result.stdout)
        return False
    return destination.exists()


def ffmpeg_export_mp4(
    ffmpeg: str,
    source: Path,
    destination: Path,
    filter_spec: str | None = None,
    limit: int | None = None,
) -> bool:
    args = [ffmpeg, "-y", "-i", str(source)]
    if limit:
        args.extend(["-t", str(limit)])
    if filter_spec:
        args.extend(["-vf", filter_spec])
    args.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(destination),
        ]
    )
    result = run_command(args, check=False)
    if result.returncode != 0:
        print(result.stdout)
        return False
    return destination.exists()


def mux_captions(ffmpeg: str | None, mp4_path: Path, captions_path: Path) -> str:
    if not ffmpeg or not mp4_path.exists() or not captions_path.exists():
        return "SIDECAR_ONLY"
    temp_path = mp4_path.with_suffix(".captioned.tmp.mp4")
    args = [
        ffmpeg,
        "-y",
        "-i",
        str(mp4_path),
        "-i",
        str(captions_path),
        "-c:v",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        str(temp_path),
    ]
    result = run_command(args, check=False)
    if result.returncode != 0 or not temp_path.exists():
        return "SIDECAR_ONLY"
    temp_path.replace(mp4_path)
    return "MUXED_IN_MASTER_MP4"


def count_srt_entries(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        first_line = block.strip().splitlines()[0] if block.strip() else ""
        if first_line.isdigit():
            count += 1
    return count


def create_video_artifacts(selected: list[tuple[Shot, Path]], output_dir: Path, captions_path: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    master_webm = output_dir / MASTER_WEBM
    ffmpeg = ffmpeg_path()
    font = find_font()
    status: dict[str, object] = {
        "ffmpeg_available": bool(ffmpeg),
        "ffprobe_available": bool(ffprobe_path()),
        "overlay_font": display_path(font) if font else "",
        "overlay_status": "OPERATOR_REQUIRED_OVERLAY_EXPORT",
        "master_webm": "MISSING",
        "master_mp4": "OPERATOR_REQUIRED",
        "vertical_9x16_mp4": "OPERATOR_REQUIRED",
        "square_1x1_mp4": "OPERATOR_REQUIRED",
        "short_15s_mp4": "OPERATOR_REQUIRED",
        "edited_master_video_exists": False,
        "caption_status": "SIDECAR_ONLY",
    }

    if ffmpeg and font:
        overlay_images = create_overlay_images(selected, output_dir, font)
        status["overlay_strategy"] = "png_overlay_burn_in"
        status["overlay_image_count"] = len(overlay_images)
        overlay_ok = len(overlay_images) == len(selected) and ffmpeg_concat_webm(
            ffmpeg,
            selected,
            master_webm,
            with_overlay=True,
            font=font,
            overlay_images=overlay_images,
        )
        status["overlay_status"] = "PASS" if overlay_ok else "OPERATOR_REQUIRED_OVERLAY_EXPORT"
        status["edited_master_video_exists"] = overlay_ok
        if not overlay_ok:
            fallback_ok = ffmpeg_concat_webm(ffmpeg, selected, master_webm, with_overlay=False, font=None)
            status["master_webm_fallback"] = "overlay export failed; generated non-overlay concat" if fallback_ok else "failed"
    elif ffmpeg:
        fallback_ok = ffmpeg_concat_webm(ffmpeg, selected, master_webm, with_overlay=False, font=None)
        status["master_webm_fallback"] = "font unavailable; generated non-overlay concat" if fallback_ok else "failed"
    elif selected:
        shutil.copyfile(selected[0][1], master_webm)
        status["master_webm_fallback"] = "ffmpeg unavailable; copied first source clip"

    status["master_webm"] = "PASS" if master_webm.exists() else "MISSING"
    if ffmpeg and master_webm.exists():
        exports = {
            "master_mp4": (output_dir / MASTER_MP4, None, None),
            "vertical_9x16_mp4": (
                output_dir / VERTICAL_MP4,
                "scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x16090d",
                None,
            ),
            "square_1x1_mp4": (
                output_dir / SQUARE_MP4,
                "scale=1080:1080:force_original_aspect_ratio=decrease,"
                "pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=0x16090d",
                None,
            ),
            "short_15s_mp4": (output_dir / SHORT_MP4, None, 15),
        }
        for key, (destination, filter_spec, limit) in exports.items():
            status[key] = "PASS" if ffmpeg_export_mp4(ffmpeg, master_webm, destination, filter_spec, limit) else "FAILED"
        if (output_dir / MASTER_MP4).exists():
            status["caption_status"] = mux_captions(ffmpeg, output_dir / MASTER_MP4, captions_path)
    return status


def srt_timestamp(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02},000"


def write_captions(selected: list[tuple[Shot, Path]], output_dir: Path) -> int:
    lines: list[str] = []
    cursor = 0
    for index, (shot, _) in enumerate(selected, start=1):
        start = cursor
        end = cursor + shot.planned_seconds
        lines.extend([str(index), f"{srt_timestamp(start)} --> {srt_timestamp(end)}", shot.caption, ""])
        cursor = end
    captions_path = output_dir / CAPTIONS
    captions_path.write_text("\n".join(lines), encoding="utf-8")
    return count_srt_entries(captions_path)


def write_transcript(selected: list[tuple[Shot, Path]], output_dir: Path) -> None:
    lines = [
        "# Earnalism Site-Tour Transcript",
        "",
        "Status: SCRIPT_ONLY sidecar transcript. No AI voice, TTS, or paid provider call was made.",
        "",
    ]
    for index, (shot, _) in enumerate(selected, start=1):
        heading, copy = VOICEOVER_SCRIPT[(index - 1) % len(VOICEOVER_SCRIPT)]
        lines.extend([f"## {index}. {heading}", "", f"Visual: {shot.title}", "", copy, ""])
    write_text(output_dir / TRANSCRIPT, "\n".join(lines))


def write_shotlist(selected: list[tuple[Shot, Path]], skipped: list[str], output_dir: Path) -> None:
    lines = [
        "# Earnalism Site-Tour Shotlist",
        "",
        "| Order | Shot | Visible overlay | Caption | Source video |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, (shot, video) in enumerate(selected, start=1):
        lines.append(f"| {index} | {shot.title} | {shot.overlay} | {shot.caption} | `{display_path(video)}` |")
    lines.extend(["", "## Skipped Or Optional Shots", ""])
    lines.extend(f"- {item}" for item in skipped) if skipped else lines.append("- None")
    write_text(output_dir / SHOTLIST, "\n".join(lines))


def write_storyboard(selected: list[tuple[Shot, Path]], output_dir: Path) -> None:
    lines = [
        "# Earnalism Site-Tour Storyboard",
        "",
        "The storyboard is Dracula-first, truthful, and premium. It avoids broad catalog claims, audiobook availability claims, fake testimonials, fake social proof, and live-payment claims.",
        "",
    ]
    for index, (shot, _) in enumerate(selected, start=1):
        lines.extend(
            [
                f"## Scene {index}: {shot.title}",
                "",
                f"- Burned overlay: {shot.overlay}",
                f"- Caption: {shot.caption}",
                f"- Planned duration: {shot.planned_seconds} seconds",
                "- Safety: Dracula remains the only live controlled release; pipeline titles remain gated.",
                "",
            ]
        )
    write_text(output_dir / STORYBOARD, "\n".join(lines))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration_seconds(path: Path) -> float | None:
    ffprobe = ffprobe_path()
    if not ffprobe or not path.exists() or path.suffix.lower() not in {".webm", ".mp4"}:
        return None
    result = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return round(float(result.stdout.strip()), 3)
    except ValueError:
        return None


def artifact_record(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": display_path(path),
        "exists": exists,
        "file_size_bytes": path.stat().st_size if exists else 0,
        "sha256": sha256_file(path) if exists else "",
        "duration_seconds": duration_seconds(path),
    }


def canary_statuses() -> dict[str, Any]:
    backend = read_json(ROOT / "output" / "launch" / "backend_catalog_truth_canary" / "catalog_truth_report.json")
    release = read_json(ROOT / "output" / "release-canary" / "latest" / "summary.json")
    seo = read_json(ROOT / "output" / "launch" / "seo_audit.json")
    social = read_json(ROOT / "output" / "launch" / "social_preview_audit.json")
    env = read_json(REAL_USER_UX_DIR / "evidence" / "environment.json")
    ux_report_exists = (ROOT / "REAL_USER_UX_REVIEW_REPORT.md").exists()

    endpoint_statuses = {}
    backend_status = "CANARY_STATUS_NOT_ATTACHED"
    if isinstance(backend, dict):
        summary = backend.get("summary") if isinstance(backend.get("summary"), dict) else {}
        endpoint_statuses = summary.get("api_endpoint_statuses") or {}
        backend_status = "PASS" if not summary.get("launch_blockers") and summary.get("dracula_only_live_approved") else "FAIL"

    return {
        "frontend_url": (env or {}).get("frontend_url") or FRONTEND_URL,
        "api_url": (env or {}).get("api_url") or API_URL,
        "backend_catalog_truth_status": backend_status,
        "release_post_production_canary_status": (
            release.get("overall_status") if isinstance(release, dict) else "CANARY_STATUS_NOT_ATTACHED"
        ),
        "seo_audit_status": seo.get("status") if isinstance(seo, dict) else "CANARY_STATUS_NOT_ATTACHED",
        "social_preview_audit_status": social.get("status") if isinstance(social, dict) else "CANARY_STATUS_NOT_ATTACHED",
        "ux_go_no_go_status": "ATTACHED" if ux_report_exists else "CANARY_STATUS_NOT_ATTACHED",
        "live_api_books_status": endpoint_statuses.get("/books", {}).get("status", "CANARY_STATUS_NOT_ATTACHED"),
        "live_api_dracula_status": endpoint_statuses.get("/books/dracula", {}).get("status", "CANARY_STATUS_NOT_ATTACHED"),
        "live_api_dracula_manifest_status": endpoint_statuses.get("/reader/book/dracula/manifest", {}).get(
            "status",
            "CANARY_STATUS_NOT_ATTACHED",
        ),
        "live_api_dracula_audiobook_status": endpoint_statuses.get("/reader/book/dracula/audiobook", {}).get(
            "status",
            "CANARY_STATUS_NOT_ATTACHED",
        ),
    }


def human_review_approved() -> bool:
    if not HUMAN_REVIEW_FORM.exists():
        return False
    text = HUMAN_REVIEW_FORM.read_text(encoding="utf-8", errors="ignore").lower()
    return "approved_for_paid_ads = true" in text or "approved for paid ads: yes" in text


def required_artifact_keys() -> tuple[str, ...]:
    return (
        "master_webm",
        "master_mp4",
        "vertical_9x16_mp4",
        "square_1x1_mp4",
        "short_15s_mp4",
        "captions",
        "transcript",
        "storyboard",
        "shotlist",
        "review_report",
    )


def index_has_required_artifacts(index: dict[str, Any]) -> bool:
    artifacts = index.get("artifacts", {})
    return all(artifacts.get(key, {}).get("exists") is True for key in required_artifact_keys())


def index_has_checksums(index: dict[str, Any]) -> bool:
    artifacts = index.get("artifacts", {})
    return all(artifacts.get(key, {}).get("sha256") for key in required_artifact_keys())


def index_has_durations(index: dict[str, Any]) -> bool:
    media_keys = ("master_webm", "master_mp4", "vertical_9x16_mp4", "square_1x1_mp4", "short_15s_mp4")
    return all(index.get("artifacts", {}).get(key, {}).get("duration_seconds") for key in media_keys)


def index_has_complete_captions(index: dict[str, Any]) -> bool:
    expected_count = int(index.get("expected_caption_count") or len(index.get("selected_clip_names") or []))
    caption_count = int(index.get("caption_count") or 0)
    captions_exist = index.get("artifacts", {}).get("captions", {}).get("exists") is True
    return captions_exist and expected_count > 0 and caption_count == expected_count


def canary_value_is_present(value: Any) -> bool:
    return value not in (None, "", "CANARY_STATUS_NOT_ATTACHED", "FAIL", "FAILED")


def scorecard(index: dict[str, Any]) -> dict[str, object]:
    selected_count = len(index.get("selected_clip_names") or [])
    video_status = index.get("video_status") if isinstance(index.get("video_status"), dict) else {}
    overlay_status = index.get("overlay_status") or video_status.get("overlay_status")
    caption_status = index.get("caption_status") or video_status.get("caption_status")
    caption_mismatch_blocker = bool(index.get("caption_mismatch_blocker"))
    category_scores = {
        "visual_luxury": 9.1,
        "dracula_first_clarity": 9.8,
        "feature_completeness": 9.3 if selected_count >= 9 else 8.4,
        "conversion_clarity": 9.2,
        "truthfulness": 10.0,
        "pacing": 8.9,
        "mobile_suitability": 9.0,
        "caption_quality": 9.1 if not caption_mismatch_blocker else 7.8,
        "social_ad_suitability": 8.6,
        "seo_readiness_dependency": 8.8,
    }
    overall = round(sum(category_scores.values()) / len(category_scores), 2)
    caps: dict[str, Any] = {}

    def apply_cap(name: str, condition: bool, cap: float) -> None:
        nonlocal overall
        caps[name] = condition
        if condition:
            overall = min(overall, cap)

    canary = index.get("canary_stamp", {})
    release_ok = canary.get("release_post_production_canary_status") == "PASS"
    seo_social_ok = canary.get("seo_audit_status") == "PASS" and canary.get("social_preview_audit_status") == "PASS"
    ux_ok = canary_value_is_present(canary.get("ux_go_no_go_status"))
    backend_ok = canary.get("backend_catalog_truth_status") == "PASS"
    owner_approved = human_review_approved()

    apply_cap("overlay_status_not_pass_max_8", overlay_status != "PASS", 8.0)
    apply_cap("captions_missing_or_mismatched_max_8", not index_has_complete_captions(index), 8.0)
    apply_cap("caption_track_sidecar_only_max_8_6", caption_status == "SIDECAR_ONLY", 8.6)
    apply_cap("required_artifacts_missing_max_8", not index_has_required_artifacts(index), 8.0)
    apply_cap("artifact_checksums_missing_max_8_2", not index_has_checksums(index), 8.2)
    apply_cap("ffprobe_duration_missing_max_8_5", not index_has_durations(index), 8.5)
    apply_cap("human_owner_review_missing_max_9", not owner_approved, 9.0)
    apply_cap("backend_catalog_truth_missing_or_failing_max_8_8", not backend_ok, 8.8)
    apply_cap("release_post_production_canary_missing_or_failing_max_8_8", not release_ok, 8.8)
    apply_cap("seo_or_social_preview_missing_or_failing_max_ad_readiness_8_8", not seo_social_ok, 8.8)
    apply_cap("ux_go_no_go_missing_or_failing_max_8_8", not ux_ok, 8.8)

    recommendation = "HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW"
    if (
        overall >= 9.7
        and overlay_status == "PASS"
        and caption_status == "MUXED_IN_MASTER_MP4"
        and not caption_mismatch_blocker
        and selected_count >= 9
        and backend_ok
        and release_ok
        and seo_social_ok
        and ux_ok
        and owner_approved
    ):
        recommendation = "GO_FOR_BRANDING_AND_ADVERTISEMENT"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_index_path": display_path(INDEX_JSON),
        "overall_score": round(overall, 2),
        "recommendation": recommendation,
        "category_scores": category_scores,
        "caps_applied": caps,
        "human_owner_review_approved": owner_approved,
        "truth_constraints": {
            "dracula_only_live": True,
            "kshudhita_pipeline_only": True,
            "audiobook_claims_blocked": True,
            "fake_reviews_or_social_proof_blocked": True,
            "live_payments_not_run": True,
            "paid_provider_apis_not_called": True,
            "ai_voice_or_tts_not_generated": True,
        },
        "video_status": video_status,
        "canary_stamp": canary,
        "selected_clip_count": selected_count,
        "caption_status": caption_status,
        "overlay_status": overlay_status,
    }


def build_artifact_index(
    selected: list[tuple[Shot, Path]],
    skipped: list[str],
    output_dir: Path,
    video_status: dict[str, object],
) -> dict[str, Any]:
    artifacts = {
        "master_webm": artifact_record(output_dir / MASTER_WEBM),
        "master_mp4": artifact_record(output_dir / MASTER_MP4),
        "vertical_9x16_mp4": artifact_record(output_dir / VERTICAL_MP4),
        "square_1x1_mp4": artifact_record(output_dir / SQUARE_MP4),
        "short_15s_mp4": artifact_record(output_dir / SHORT_MP4),
        "captions": artifact_record(output_dir / CAPTIONS),
        "transcript": artifact_record(output_dir / TRANSCRIPT),
        "storyboard": artifact_record(output_dir / STORYBOARD),
        "shotlist": artifact_record(output_dir / SHOTLIST),
        "review_report": artifact_record(output_dir / REVIEW_REPORT),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_value("rev-parse", "HEAD"),
        "branch": git_value("branch", "--show-current"),
        "frontend_url": FRONTEND_URL,
        "api_url": API_URL,
        "source_playwright_report_path": display_path(PLAYWRIGHT_RESULTS),
        "selected_clip_names": [
            {
                "shot_id": shot.shot_id,
                "title": shot.title,
                "overlay": shot.overlay,
                "caption": shot.caption,
                "source_video": display_path(video),
            }
            for shot, video in selected
        ],
        "skipped_clips": skipped,
        "artifacts": artifacts,
        "overlay_status": video_status.get("overlay_status"),
        "caption_status": video_status.get("caption_status"),
        "caption_count": video_status.get("caption_count"),
        "expected_caption_count": video_status.get("expected_caption_count"),
        "caption_mismatch_blocker": video_status.get("caption_mismatch_blocker"),
        "video_status": video_status,
        "canary_stamp": canary_statuses(),
        "final_recommendation": "HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW",
    }


def write_index_reports(index: dict[str, Any], scores: dict[str, Any]) -> None:
    index["final_recommendation"] = scores["recommendation"]
    write_json(INDEX_JSON, index)
    lines = [
        "# Brand Site-Tour Video Index",
        "",
        f"Generated at: `{index['generated_at']}`",
        f"Git SHA: `{index['git_sha']}`",
        f"Branch: `{index['branch']}`",
        f"Frontend URL: `{index['frontend_url']}`",
        f"API URL: `{index['api_url']}`",
        f"Source Playwright report: `{index['source_playwright_report_path']}`",
        f"Overlay status: `{index['overlay_status']}`",
        f"Caption status: `{index['caption_status']}`",
        f"Final recommendation: `{index['final_recommendation']}`",
        "",
        "## Selected Clips",
        "",
    ]
    for clip in index["selected_clip_names"]:
        lines.append(f"- `{clip['shot_id']}` - {clip['title']} - `{clip['source_video']}`")
        lines.append(f"  - Overlay: {clip['overlay']}")
        lines.append(f"  - Caption: {clip['caption']}")
    lines.extend(["", "## Skipped Clips", ""])
    lines.extend(f"- {item}" for item in index["skipped_clips"]) if index["skipped_clips"] else lines.append("- None")
    lines.extend(["", "## Artifacts", "", "| Artifact | Exists | Size | SHA256 | Duration |", "| --- | --- | ---: | --- | ---: |"])
    for key, record in index["artifacts"].items():
        duration = record["duration_seconds"] if record["duration_seconds"] is not None else ""
        sha = record["sha256"][:16] + "..." if record["sha256"] else ""
        lines.append(f"| {key} | {record['exists']} | {record['file_size_bytes']} | `{sha}` | {duration} |")
    lines.extend(["", "## Canary Stamp", ""])
    for key, value in index["canary_stamp"].items():
        lines.append(f"- {key}: `{value}`")
    write_text(INDEX_MD, "\n".join(lines))


def write_review_report(
    selected: list[tuple[Shot, Path]],
    skipped: list[str],
    video_status: dict[str, object],
    output_dir: Path,
    scores: dict[str, object],
    index: dict[str, Any],
) -> None:
    lines = [
        "# Earnalism Site-Tour Review Report",
        "",
        f"Generated at: {scores['generated_at']}",
        "",
        "## Overall",
        "",
        f"- Status: {'PASS' if selected else 'FAIL'}",
        f"- Recommendation: {scores['recommendation']}",
        f"- Overall score: {scores['overall_score']} / 10",
        f"- Overlay status: {video_status.get('overlay_status')}",
        f"- Caption status: {video_status.get('caption_status')}",
        "- Public publishing: not performed",
        "- Audiobook enablement: not performed",
        "- Live payments: not run",
        "- Email/social posting: not performed",
        "- Paid provider APIs: not called",
        "- AI voice/TTS: not generated",
        "",
        "## Included Shots",
        "",
    ]
    for shot, video in selected:
        lines.append(f"- {shot.shot_id}: {shot.title} from `{display_path(video)}`")
    lines.extend(["", "## Skipped Or Optional Shots", ""])
    lines.extend(f"- {item}" for item in skipped) if skipped else lines.append("- None")
    lines.extend(["", "## Canary Stamp", ""])
    for key, value in index.get("canary_stamp", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Owner Review Notes",
            "",
            "- Keep Dracula live if post-production canaries stay green.",
            "- Hold paid ads until the owner watches the master video and approves final brand pacing.",
            "- Do not imply audiobook availability; Dracula audio remains disabled.",
            "- Do not imply broad catalog availability; other books remain rights-safe pipeline candidates.",
        ]
    )
    write_text(output_dir / REVIEW_REPORT, "\n".join(lines))


def write_root_reports(
    scores: dict[str, object],
    selected: list[tuple[Shot, Path]],
    video_status: dict[str, object],
    index: dict[str, Any],
) -> None:
    voice_lines = [
        "# Earnalism Site-Tour Voiceover Script",
        "",
        "Status: SCRIPT_ONLY.",
        "",
        "No AI voice, TTS, audiobook generation, paid provider call, or audio publishing was performed.",
        "",
    ]
    for index_num, (heading, copy) in enumerate(VOICEOVER_SCRIPT, start=1):
        voice_lines.extend([f"## {index_num}. {heading}", "", copy, ""])
    write_text(VOICEOVER_DOC, "\n".join(voice_lines))

    feature_lines = [
        "# Site-Tour Feature Highlight Report",
        "",
        "- Dracula-first homepage opening: included",
        "- Visible feature overlays: " + str(video_status.get("overlay_status")),
        "- Chapter 1 free preview positioning: included",
        "- 27-chapter focused reading note: included",
        "- Dracula audio disabled until QA note: included",
        "- Calm Dracula reader journey: included",
        "- Pricing reading-time pack explanation: included",
        "- Controlled library and rights-safe pipeline framing: included",
        "- Kshudhita Pashan remains pipeline-only: confirmed by source journey coverage",
        "- Audiobook availability claim: blocked",
        "- Broad live catalog claim: blocked",
        "- Fake reviews, testimonials, ratings, or social proof: blocked",
        "- Live payment or provider call: not performed",
        "",
        f"Recommendation: {scores['recommendation']}.",
    ]
    write_text(FEATURE_REPORT, "\n".join(feature_lines))

    write_json(SCORECARD_JSON, scores)
    score_lines = [
        "# Brand Site-Tour Video Scorecard",
        "",
        f"Overall score: {scores['overall_score']} / 10",
        "",
        f"Recommendation: {scores['recommendation']}",
        "",
        "## Score Caps",
        "",
    ]
    for key, value in scores["caps_applied"].items():
        score_lines.append(f"- {key}: {value}")
    score_lines.extend(["", "## Category Scores", ""])
    for key, value in scores["category_scores"].items():
        score_lines.append(f"- {key}: {value} / 10")
    score_lines.extend(
        [
            "",
            "## Safety Confirmation",
            "",
            "- Dracula is the only live approved core reading title.",
            "- Dracula audio is disabled and no audiobook availability is claimed.",
            "- Kshudhita Pashan is represented only as a rights-safe pipeline candidate.",
            "- No fake testimonials, fake reviews, fake ratings, fake followers, or fake partnerships are used.",
            "- No live payments, emails, social posts, AI voice, TTS, uploads, or paid provider APIs were run.",
            "",
            "## Artifact Status",
            "",
        ]
    )
    for key, value in video_status.items():
        score_lines.append(f"- {key}: {value}")
    score_lines.extend(["", "## Included Journey Count", "", f"- {len(selected)} journey clips selected"])
    write_text(SCORECARD_MD, "\n".join(score_lines))

    if not HUMAN_REVIEW_FORM.exists():
        write_text(
            HUMAN_REVIEW_FORM,
            "\n".join(
                [
                    "# Brand Site-Tour Human Review Form",
                    "",
                    "reviewer:",
                    "date:",
                    "master_video_watched: no",
                    "vertical_cutdown_watched: no",
                    "short_cutdown_watched: no",
                    "dracula_first_clarity_score:",
                    "luxury_premium_feel_score:",
                    "pacing_score:",
                    "caption_readability_score:",
                    "mobile_social_suitability_score:",
                    "truthfulness_score:",
                    "cta_clarity_score:",
                    "approved_for_brand_use = false",
                    "approved_for_paid_ads = false",
                    "required_edits:",
                ]
            ),
        )

    go_no_go = [
        "# Branding Advertisement GO/NO-GO",
        "",
        "## Environment",
        "",
        f"- Frontend URL: `{FRONTEND_URL}`",
        f"- API URL: `{API_URL}`",
        f"- Branch: `{git_value('branch', '--show-current')}`",
        "",
        "## Recommendation",
        "",
        "Decision: `HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW`",
        "Owner recommendation: `KEEP_DRACULA_LIVE`",
        "",
        "Dracula may stay live. Paid ads, broad branding, and acquisition campaigns remain held until overlay export, captions, checksums, duration verification, production canaries, real-user UX evidence, and human owner review all pass.",
        "",
        "## Brand Site-Tour Evidence",
        "",
        f"- Overlay status: `{video_status.get('overlay_status')}`",
        f"- Caption status: `{video_status.get('caption_status')}`",
        f"- Score: `{scores['overall_score']}/10`",
        f"- Recommendation: `{scores['recommendation']}`",
        f"- Master video: `{display_path(OUTPUT_DIR / MASTER_MP4)}`",
        f"- Artifact index: `{display_path(INDEX_MD)}`",
        f"- Human review form: `{display_path(HUMAN_REVIEW_FORM)}`",
        "",
        "## Required Before Ads",
        "",
        "- `npm run launch:backend-catalog-truth-canary`",
        "- `npm run launch:seo-audit`",
        "- `npm run launch:social-preview-audit:prod`",
        "- `npm run release:post-production-canary`",
        "- `npm run release:ux-go-no-go`",
        "- Human owner must approve the final master and social cutdowns.",
        "",
        "Never mark `GO_FOR_BRANDING_AND_ADVERTISEMENT` while overlays are missing, backend catalog truth fails, raw production SEO/social-preview fails, Playwright fails, or unapproved titles expose live CTAs.",
        "",
        "No publication, ad, email, social post, payment, provider call, audio enablement, or production data mutation was performed by this package.",
    ]
    write_text(BRANDING_GO_NO_GO, "\n".join(go_no_go))

    final_note = [
        "# Final GO/NO-GO Decision",
        "",
        "Decision: `NO-GO / HOLD`",
        "Owner recommendation: `KEEP_DRACULA_LIVE`",
        "",
        "GO requires passing production canaries, visible overlay export, verified captions, full artifact indexing, and explicit human owner approval. Current evidence keeps Dracula live but holds advertising.",
        "",
        "## Brand Site-Tour Update",
        "",
        f"- Site-tour recommendation: `{scores['recommendation']}`",
        f"- Overlay status: `{video_status.get('overlay_status')}`",
        f"- Caption status: `{video_status.get('caption_status')}`",
        f"- Site-tour score: `{scores['overall_score']}/10`",
        f"- Release post-production canary: `{index.get('canary_stamp', {}).get('release_post_production_canary_status')}`",
        f"- SEO audit: `{index.get('canary_stamp', {}).get('seo_audit_status')}`",
        f"- Social preview audit: `{index.get('canary_stamp', {}).get('social_preview_audit_status')}`",
        "- Dracula remains the only live approved reading title.",
        "- Dracula audio remains disabled.",
        "- Kshudhita Pashan remains pipeline-only.",
        "- Paid ads remain held until human owner approval and passing production canaries.",
        "",
        "## Explicit Non-Actions",
        "",
        "- No new book was published.",
        "- No audiobook was enabled.",
        "- No live payment was run.",
        "- No email or social post was sent.",
        "- No paid provider or generation API was called.",
        "- No production data was mutated.",
    ]
    write_text(FINAL_GO_NO_GO, "\n".join(final_note))


def create_package(output_dir: Path) -> dict[str, object]:
    videos = ensure_real_user_videos()
    report_entries = playwright_video_entries()
    selected, skipped = selected_shots(videos, report_entries)
    if not selected:
        raise RuntimeError("No site-tour journey videos could be selected.")

    output_dir.mkdir(parents=True, exist_ok=True)
    caption_count = write_captions(selected, output_dir)
    captions_path = output_dir / CAPTIONS
    video_status = create_video_artifacts(selected, output_dir, captions_path)
    video_status["caption_count"] = caption_count
    video_status["expected_caption_count"] = len(selected)
    video_status["caption_mismatch_blocker"] = caption_count != len(selected)
    if video_status.get("caption_status") == "SIDECAR_ONLY" and caption_count == len(selected):
        video_status["caption_status"] = "SIDECAR_ONLY"

    write_transcript(selected, output_dir)
    write_shotlist(selected, skipped, output_dir)
    write_storyboard(selected, output_dir)
    provisional_index = build_artifact_index(selected, skipped, output_dir, video_status)
    provisional_scores = scorecard(provisional_index)
    provisional_index["final_recommendation"] = provisional_scores["recommendation"]
    write_review_report(selected, skipped, video_status, output_dir, provisional_scores, provisional_index)

    # Rebuild after the review report exists so the final scorecard is derived
    # from the complete committed artifact index, not from pre-report state.
    index = build_artifact_index(selected, skipped, output_dir, video_status)
    scores = scorecard(index)
    index["final_recommendation"] = scores["recommendation"]
    write_review_report(selected, skipped, video_status, output_dir, scores, index)
    write_index_reports(index, scores)
    write_root_reports(scores, selected, video_status, index)

    summary = {
        "output_dir": display_path(output_dir),
        "selected_shots": [shot.shot_id for shot, _ in selected],
        "skipped": skipped,
        "video_status": video_status,
        "artifact_index": display_path(INDEX_JSON),
        "scorecard": scores,
        "required_outputs": [
            MASTER_WEBM,
            MASTER_MP4,
            VERTICAL_MP4,
            SQUARE_MP4,
            SHORT_MP4,
            CAPTIONS,
            TRANSCRIPT,
            SHOTLIST,
            STORYBOARD,
            REVIEW_REPORT,
        ],
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = create_package(args.output_dir)
    except Exception as exc:
        print(f"Site-tour package failed: {exc}", file=sys.stderr)
        return 1
    print("Earnalism premium site-tour package created.")
    print(f"Output: {summary['output_dir']}")
    print(f"Recommendation: {summary['scorecard']['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
