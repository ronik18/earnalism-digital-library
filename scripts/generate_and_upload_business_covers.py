#!/usr/bin/env python3
"""Generate neutral Earnalism business covers and upload them to admin drafts."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_URL = "https://api.theearnalism.com"
DEFAULT_MANIFEST = ROOT / "book_import_manifests" / "business_entrepreneurship_public_domain_20260609.json"
DEFAULT_OUTPUT = ROOT / "output" / "generated_business_covers"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

PALETTES = [
    ("#20302f", "#f6f0e6", "#b98b47", "#5b2632", "#d8c6a3"),
    ("#2b2c40", "#f7f1e8", "#bc9254", "#1f6f6b", "#dbc6a0"),
    ("#352a2b", "#f5eee4", "#aa7d47", "#3d6f67", "#d6bd91"),
    ("#243244", "#f4efe6", "#c2944b", "#612b3b", "#dac59d"),
    ("#2f3527", "#f7f0e5", "#b88548", "#5a2b38", "#d8c19a"),
]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_api_url(value: str) -> str:
    value = (value or DEFAULT_API_URL).rstrip("/")
    return value if value.endswith("/api") else f"{value}/api"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("books", data) if isinstance(data, dict) else data
    return [row for row in rows if isinstance(row, dict)]


def display_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def font_path() -> str | None:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def font(size: int, path: str | None) -> ImageFont.ImageFont:
    if path:
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=face)
    return int(box[2] - box[0])


def text_height(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=face)
    return int(box[3] - box[1])


def wrap_text(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont, max_width: int) -> list[str]:
    tokens = re.split(r"\s+", display_text(text))
    lines: list[str] = []
    current = ""
    for token in tokens:
        probe = f"{current} {token}".strip()
        if current and text_width(draw, probe, face) > max_width:
            lines.append(current)
            current = token
        else:
            current = probe
    if current:
        lines.append(current)
    return lines or [""]


def fit_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    max_lines: int,
    max_size: int,
    min_size: int,
    path: str | None,
) -> tuple[ImageFont.ImageFont, list[str]]:
    for size in range(max_size, min_size - 1, -4):
        face = font(size, path)
        lines = wrap_text(draw, text, face, max_width)
        if len(lines) <= max_lines and all(text_width(draw, line, face) <= max_width for line in lines):
            return face, lines
    face = font(min_size, path)
    return face, wrap_text(draw, text, face, max_width)[:max_lines]


def draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    face: ImageFont.ImageFont,
    y: int,
    fill: str,
    width: int,
    spacing: int,
) -> int:
    for line in lines:
        line_width = text_width(draw, line, face)
        draw.text(((width - line_width) / 2, y), line, fill=fill, font=face)
        y += text_height(draw, line, face) + spacing
    return y


def palette_for(slug: str) -> tuple[str, str, str, str, str]:
    return PALETTES[sum(ord(ch) for ch in slug) % len(PALETTES)]


def draw_rule(draw: ImageDraw.ImageDraw, y: int, accent: str, width: int = 1200) -> None:
    draw.line((180, y, width - 180, y), fill=accent, width=4)


def generate_cover(book: dict[str, Any], output_dir: Path, kind: str, font_file: str | None) -> Path:
    slug = display_text(book.get("slug")) or "business-book"
    title = display_text(book.get("title")) or slug.replace("-", " ").title()
    subtitle = display_text(book.get("subtitle"))
    author = display_text(book.get("author")) or "Earnalism"
    ink, paper, accent, secondary, muted = palette_for(slug)

    image = Image.new("RGB", (1200, 1800), paper)
    draw = ImageDraw.Draw(image)
    margin = 84

    draw.rectangle((42, 42, 1158, 1758), outline=accent, width=5)
    draw.rectangle((68, 68, 1132, 1732), outline=ink, width=2)
    draw.rectangle((94, 94, 1106, 1706), outline=muted, width=1)

    small = font(30, font_file)
    micro = font(23, font_file)
    author_font = font(46, font_file)
    category_font = font(32, font_file)
    title_font, title_lines = fit_lines(draw, title, 930, 4, 110, 58, font_file)

    if kind == "front":
        draw.text((margin, 122), "Earnalism Digital Library", fill=secondary, font=micro)
        label = "Business & Entrepreneurship"
        label_width = text_width(draw, label, category_font)
        draw.text(((1200 - label_width) / 2, 315), label, fill=accent, font=category_font)
        draw_rule(draw, 388, accent)

        y = 535
        y = draw_centered_lines(draw, title_lines, title_font, y, ink, 1200, 22)
        if subtitle:
            subtitle_font, subtitle_lines = fit_lines(draw, subtitle, 840, 2, 48, 32, font_file)
            y += 34
            y = draw_centered_lines(draw, subtitle_lines, subtitle_font, y, secondary, 1200, 12)
        y += 76
        author_lines = wrap_text(draw, author, author_font, 880)
        draw_centered_lines(draw, author_lines, author_font, y, ink, 1200, 12)

        draw_rule(draw, 1294, accent)
        footer = "Clean public-domain reader edition"
        footer_width = text_width(draw, footer, small)
        draw.text(((1200 - footer_width) / 2, 1374), footer, fill=secondary, font=small)
    else:
        draw.text((margin, 128), "Earnalism", fill=secondary, font=small)
        draw_rule(draw, 210, accent)
        back_title_font, back_title_lines = fit_lines(draw, title, 900, 3, 70, 42, font_file)
        y = 405
        y = draw_centered_lines(draw, back_title_lines, back_title_font, y, ink, 1200, 18)
        y += 48
        author_lines = wrap_text(draw, author, author_font, 860)
        draw_centered_lines(draw, author_lines, author_font, y, secondary, 1200, 10)

        body_font = font(34, font_file)
        body_lines = [
            "Prepared for focused digital reading.",
            "A clean public-domain reader edition.",
            "Business & Entrepreneurship",
        ]
        y = 945
        for line in body_lines:
            line_width = text_width(draw, line, body_font)
            draw.text(((1200 - line_width) / 2, y), line, fill=ink, font=body_font)
            y += 74
        draw_rule(draw, 1378, accent)
        label = "Business & Entrepreneurship"
        label_width = text_width(draw, label, category_font)
        draw.text(((1200 - label_width) / 2, 1454), label, fill=accent, font=category_font)

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{slug}_{kind}.png"
    image.save(path, "PNG", optimize=True)
    return path


def login(session: requests.Session, api_url: str) -> None:
    token = os.environ.get("EARNALISM_ADMIN_TOKEN", "").strip()
    if not token:
        email = os.environ.get("ADMIN_EMAIL", "").strip()
        password = os.environ.get("ADMIN_PASSWORD", "").strip()
        if not email or not password:
            raise RuntimeError("Set EARNALISM_ADMIN_TOKEN or ADMIN_EMAIL + ADMIN_PASSWORD.")
        response = session.post(f"{api_url}/auth/login", json={"email": email, "password": password}, timeout=30)
        response.raise_for_status()
        token = response.json()["token"]
    session.headers.update({"Authorization": f"Bearer {token}"})


def upload_cover(session: requests.Session, api_url: str, slug: str, kind: str, path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        response = session.post(
            f"{api_url}/admin/books/{slug}/cover",
            params={"kind": kind},
            files={"file": (path.name, handle, "image/png")},
            timeout=180,
        )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", DEFAULT_API_URL))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--env-file", action="append", type=Path, default=[ROOT / ".secrets" / "earnalism-import.env"])
    parser.add_argument("--slug", action="append", default=[], help="Restrict to one or more manifest slugs.")
    parser.add_argument("--dry-run", action="store_true", help="Generate local covers without uploading.")
    parser.add_argument("--reuse-local", action="store_true", help="Reuse existing local PNGs when present.")
    args = parser.parse_args()

    for env_file in args.env_file:
        load_env_file(env_file.expanduser().resolve())

    manifest = args.manifest.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    selected_slugs = {slug.strip() for slug in args.slug if slug.strip()}
    books = [
        book
        for book in load_manifest(manifest)
        if not selected_slugs or str(book.get("slug") or "").strip() in selected_slugs
    ]
    if not books:
        raise RuntimeError("No manifest books selected for cover generation.")

    api_url = normalize_api_url(args.api_url)
    font_file = font_path()
    session = requests.Session()
    if not args.dry_run:
        login(session, api_url)

    results: list[dict[str, Any]] = []
    for book in books:
        slug = display_text(book.get("slug"))
        item: dict[str, Any] = {"slug": slug, "title": book.get("title"), "uploads": {}}
        for kind in ("front", "back"):
            image_path = output_dir / f"{slug}_{kind}.png"
            if args.reuse_local and image_path.exists():
                print(f"{slug}: reusing local {kind} cover at {image_path}", flush=True)
            else:
                image_path = generate_cover(book, output_dir, kind, font_file)
                print(f"{slug}: generated {kind} cover at {image_path}", flush=True)
            if args.dry_run:
                item["uploads"][kind] = {"ok": True, "uploaded": False, "local_path": str(image_path)}
                continue
            try:
                item["uploads"][kind] = upload_cover(session, api_url, slug, kind, image_path)
                item["uploads"][kind]["local_path"] = str(image_path)
                print(f"{slug}: uploaded {kind} cover", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep the batch report complete
                item["uploads"][kind] = {"ok": False, "error": str(exc), "local_path": str(image_path)}
                print(f"{slug}: failed {kind} cover upload: {exc}", flush=True)
        results.append(item)

    report = {
        "manifest": str(manifest),
        "api_url": api_url,
        "dry_run": args.dry_run,
        "results": results,
    }
    report_path = output_dir / "business_cover_upload_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cover report: {report_path}")
    failures = [
        upload
        for item in results
        for upload in item.get("uploads", {}).values()
        if upload.get("ok") is False or upload.get("error")
    ]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
