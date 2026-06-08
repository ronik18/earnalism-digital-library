#!/usr/bin/env python3
"""Generate original typographic Bengali covers and upload them to Earnalism."""

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
DEFAULT_STATUS = ROOT / "output/bengali_draft_publish_readiness_latest.json"
DEFAULT_OUTPUT = ROOT / "output/generated_bengali_covers"

FONT_CANDIDATES = [
    "/System/Library/Fonts/KohinoorBangla.ttc",
    "/System/Library/Fonts/Supplemental/Bangla MN.ttc",
    "/System/Library/Fonts/Supplemental/Bangla Sangam MN.ttc",
    "/System/Library/Fonts/Kohinoor.ttc",
]

CATEGORY_LABELS = {
    "literary-fiction": "Literary Fiction",
    "young-readers": "Young Readers",
    "adventure": "Adventure",
    "gothic-fiction": "Gothic Fiction",
    "history-strategy": "History & Strategy",
    "bengali-classics": "Bengali Classics",
}

PALETTES = [
    ("#4c1d25", "#f7f0e6", "#c9964a", "#241819"),
    ("#183c3d", "#f4efe7", "#a85f3f", "#152124"),
    ("#28334a", "#f7f2e8", "#b88a44", "#171b24"),
    ("#4d3226", "#f5eddf", "#8f6a3f", "#1f1915"),
    ("#284229", "#f6f0e5", "#b06c4c", "#151d17"),
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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("\u200c", "").replace("\u200d", "")
    text = text.replace("পোস্ট্মাস্টার", "পোস্টমাস্টার")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def manifest_books(paths: list[Path]) -> dict[str, dict[str, Any]]:
    books: dict[str, dict[str, Any]] = {}
    by_title: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.exists():
            continue
        data = load_json(path)
        rows = data.get("books", data) if isinstance(data, dict) else data
        for row in rows:
            if not isinstance(row, dict):
                continue
            slug = str(row.get("slug") or "").strip()
            if slug:
                books[slug] = row
            title_key = display_text(row.get("title")).casefold()
            if title_key:
                by_title[title_key] = row
    books["__by_title__"] = by_title
    return books


def book_for_status_row(books: dict[str, dict[str, Any]], row: dict[str, Any]) -> dict[str, Any] | None:
    slug = str(row.get("slug") or "").strip()
    book = books.get(slug)
    if book:
        return book
    by_title = books.get("__by_title__", {})
    return by_title.get(display_text(row.get("title")).casefold())


def font_path() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("No Bengali-capable font found on this machine.")


def font(size: int, path: str) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def text_width(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=face)
    return int(box[2] - box[0])


def wrap_text(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = re.split(r"\s+", (text or "").strip())
    lines: list[str] = []
    current = ""
    for word in words:
        probe = f"{current} {word}".strip()
        if current and text_width(draw, probe, face) > max_width:
            lines.append(current)
            current = word
        else:
            current = probe
    if current:
        lines.append(current)
    return lines or [""]


def fit_lines(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_size: int, min_size: int, path: str) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(max_size, min_size - 1, -4):
        face = font(size, path)
        lines = wrap_text(draw, text, face, max_width)
        if lines and all(text_width(draw, line, face) <= max_width for line in lines) and len(lines) <= 4:
            return face, lines
    face = font(min_size, path)
    return face, wrap_text(draw, text, face, max_width)


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
        box = draw.textbbox((0, 0), line, font=face)
        line_width = box[2] - box[0]
        line_height = box[3] - box[1]
        draw.text(((width - line_width) / 2, y), line, fill=fill, font=face)
        y += line_height + spacing
    return y


def generate_cover(book: dict[str, Any], output_dir: Path, kind: str, font_file: str) -> Path:
    slug = str(book["slug"])
    title = display_text(book.get("title") or slug)
    author = display_text(book.get("author") or "Earnalism")
    category = CATEGORY_LABELS.get(str(book.get("category_slug") or ""), "Bengali Library")
    palette = PALETTES[sum(ord(ch) for ch in slug) % len(PALETTES)]
    ink, paper, accent, dark = palette
    image = Image.new("RGB", (1200, 1800), paper)
    draw = ImageDraw.Draw(image)

    margin = 96
    draw.rectangle((42, 42, 1158, 1758), outline=accent, width=4)
    draw.rectangle((66, 66, 1134, 1734), outline=ink, width=2)

    small = font(34, font_file)
    micro = font(25, font_file)
    author_font = font(48, font_file)
    title_font, title_lines = fit_lines(draw, title, 940, 112, 64, font_file)

    if kind == "front":
        draw.text((margin, 120), "Earnalism Digital Library", fill=accent, font=micro)
        draw.line((margin, 180, 1110, 180), fill=accent, width=3)
        y = 485
        y = draw_centered_lines(draw, title_lines, title_font, y, ink, 1200, 20)
        y += 58
        author_lines = wrap_text(draw, author, author_font, 880)
        draw_centered_lines(draw, author_lines, author_font, y, dark, 1200, 10)
        draw.line((310, 1320, 890, 1320), fill=accent, width=3)
        label = f"{category} / Bengali"
        label_width = text_width(draw, label, small)
        draw.text(((1200 - label_width) / 2, 1375), label, fill=ink, font=small)
        draw.text((margin, 1620), "A clean reader-ready edition", fill=dark, font=micro)
    else:
        draw.text((margin, 140), "Earnalism", fill=accent, font=small)
        draw.line((margin, 205, 1110, 205), fill=accent, width=3)
        back_title_font, back_title_lines = fit_lines(draw, title, 920, 72, 48, font_file)
        y = 390
        y = draw_centered_lines(draw, back_title_lines, back_title_font, y, ink, 1200, 18)
        y += 55
        author_lines = wrap_text(draw, author, font(42, font_file), 860)
        draw_centered_lines(draw, author_lines, font(42, font_file), y, dark, 1200, 10)
        body = [
            "Prepared for quiet, focused digital reading.",
            "Source provenance and rights evidence are retained internally.",
            "Reader-facing text is kept free from repository boilerplate.",
        ]
        y = 965
        for line in body:
            body_width = text_width(draw, line, micro)
            draw.text(((1200 - body_width) / 2, y), line, fill=dark, font=micro)
            y += 62
        draw.line((310, 1395, 890, 1395), fill=accent, width=3)
        label = CATEGORY_LABELS.get(str(book.get("category_slug") or ""), "Bengali Library")
        label_width = text_width(draw, label, small)
        draw.text(((1200 - label_width) / 2, 1455), label, fill=ink, font=small)

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{slug}_{kind}.png"
    image.save(path, "PNG", optimize=True)
    return path


def login(session: requests.Session, api_url: str) -> None:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL/ADMIN_PASSWORD are required.")
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
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--manifest", action="append", type=Path, default=[])
    parser.add_argument("--api-url", default=os.environ.get("EARNALISM_API_URL", DEFAULT_API_URL))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--env-file", action="append", type=Path, default=[ROOT / ".secrets/earnalism-import.env"])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Generate local covers without uploading.")
    parser.add_argument("--reuse-local", action="store_true", help="Upload existing local cover PNGs when present.")
    args = parser.parse_args()

    for env_file in args.env_file:
        load_env_file(env_file)

    api_url = normalize_api_url(args.api_url)
    manifest_paths = args.manifest or [
        ROOT / "book_import_manifest.json",
        ROOT / "output/source_repair/20260602T192021Z/source_repaired_404_manifest.json",
        ROOT / "output/bengali_source_repair/20260603T084835Z/bengali_source_repaired_upload_manifest.json",
    ]
    books = manifest_books([path.expanduser().resolve() for path in manifest_paths])
    status_rows = load_json(args.status.expanduser().resolve())
    font_file = font_path()

    session = requests.Session()
    if not args.dry_run:
        login(session, api_url)

    results: list[dict[str, Any]] = []
    for row in status_rows:
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        if not args.force and row.get("front") and row.get("back"):
            continue
        book = book_for_status_row(books, row)
        if not book:
            results.append({"slug": slug, "status": "skipped", "reason": "not found in cover metadata manifests"})
            continue
        book = {
            **book,
            "slug": slug,
            "title": row.get("title") or book.get("title"),
            "author": row.get("author") or book.get("author"),
            "category_slug": row.get("category_slug") or book.get("category_slug") or book.get("categoryslug") or "bengali-classics",
        }
        item: dict[str, Any] = {"slug": slug, "title": book.get("title"), "uploads": {}}
        for kind in ("front", "back"):
            if not args.force and row.get(kind):
                continue
            image_path = args.output_dir / f"{slug}_{kind}.png"
            if args.reuse_local and image_path.exists():
                print(f"{slug}: reusing local {kind} cover at {image_path}", flush=True)
            else:
                image_path = generate_cover(book, args.output_dir, kind, font_file)
                print(f"{slug}: generated {kind} cover at {image_path}", flush=True)
            if args.dry_run:
                item["uploads"][kind] = {"ok": True, "local_path": str(image_path), "uploaded": False}
                continue
            try:
                item["uploads"][kind] = upload_cover(session, api_url, slug, kind, image_path)
                print(f"{slug}: uploaded {kind} cover", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep processing the batch
                item["uploads"][kind] = {"ok": False, "error": str(exc), "local_path": str(image_path)}
                print(f"{slug}: failed {kind} cover upload: {exc}", flush=True)
        item["status"] = "uploaded"
        results.append(item)

    report_path = args.output_dir / "cover_upload_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"api_url": api_url, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated/uploaded cover report: {report_path}")
    print(f"Processed: {len(results)}")
    print(f"Uploaded attempts: {sum(len(item.get('uploads', {})) for item in results)}")
    return 0 if all(not upload.get("error") for item in results for upload in item.get("uploads", {}).values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
