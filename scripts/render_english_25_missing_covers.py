#!/usr/bin/env python3
"""Render deterministic, rights-safe graphical covers for the 25-title batch.

The artwork is generated from vector primitives and deterministic typography;
it does not download or embed third-party art. Existing approved covers are
never replaced. The output is an 800x1200 WebP front/back pair under the
frontend's same-origin book asset path plus a checksum-bound audit report.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = ROOT / "scripts" / "prepare_english_25_title_batch.py"
ASSET_ROOT = ROOT / "frontend" / "public" / "assets" / "books"
AUDIT_PATH = (
    ROOT
    / "internal"
    / "earnalism_intelligence"
    / "english_25_title_generated_cover_audit.json"
)
WIDTH, HEIGHT = 800, 1200


@dataclass(frozen=True)
class Theme:
    name: str
    top: tuple[int, int, int]
    bottom: tuple[int, int, int]
    accent: tuple[int, int, int]
    symbol: str


THEMES = {
    "the-most-dangerous-game": Theme("island hunt", (12, 24, 27), (45, 14, 17), (211, 164, 91), "island"),
    "the-stolen-white-elephant": Theme("royal elephant", (31, 22, 48), (75, 46, 33), (232, 197, 116), "elephant"),
    "a-horseman-in-the-sky": Theme("cliff and rider", (22, 38, 55), (77, 45, 38), (218, 176, 104), "horse"),
    "the-happy-prince": Theme("gilded statue and swallow", (14, 39, 65), (55, 31, 69), (240, 199, 87), "swallow"),
    "a-mystery-of-heroism": Theme("smoke and water", (45, 42, 41), (88, 36, 25), (221, 182, 116), "medal"),
    "the-open-boat": Theme("open sea", (10, 49, 66), (18, 24, 42), (203, 177, 113), "boat"),
    "a-white-heron": Theme("moonlit pine and heron", (17, 49, 45), (46, 65, 49), (226, 212, 157), "heron"),
    "the-pit-and-the-pendulum": Theme("stone chamber", (31, 26, 36), (72, 24, 28), (204, 154, 88), "pendulum"),
    "an-occurrence-at-owl-creek-bridge": Theme("bridge and river", (27, 45, 52), (70, 43, 35), (215, 180, 112), "bridge"),
    "love-of-life": Theme("northern trail", (25, 45, 54), (71, 73, 65), (228, 204, 145), "trail"),
    "a-scandal-in-bohemia": Theme("sealed letter", (41, 25, 52), (78, 33, 44), (226, 183, 102), "letter"),
    "the-lady-with-the-dog": Theme("seaside promenade", (25, 51, 61), (75, 45, 49), (220, 183, 122), "dog"),
    "the-bishop": Theme("cathedral candle", (35, 29, 47), (69, 39, 31), (231, 195, 122), "cathedral"),
    "the-enchanted-april": Theme("Italian garden", (35, 62, 54), (105, 67, 64), (237, 204, 138), "villa"),
    "the-metamorphosis": Theme("threshold and shadow", (31, 33, 38), (69, 46, 35), (195, 160, 105), "door"),
    "the-canterville-ghost": Theme("English manor", (30, 36, 55), (71, 41, 61), (215, 182, 112), "manor"),
    "the-man-who-would-be-king": Theme("mountain crown", (30, 45, 50), (78, 55, 36), (225, 184, 100), "crown"),
    "the-fall-of-the-house-of-usher": Theme("house and tarn", (24, 31, 41), (61, 31, 39), (202, 164, 105), "usher"),
    "picture-of-dorian-gray": Theme("portrait and gilt frame", (29, 35, 44), (65, 33, 47), (218, 180, 105), "portrait"),
}


def load_plans():
    spec = importlib.util.spec_from_file_location("english_25_prepare_for_covers", PREPARE_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError("Unable to load the 25-title plan")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.TITLE_PLANS


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def font(size: int, *, italic: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont:
    families = []
    if bold:
        families.extend(
            [
                "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            ]
        )
    elif italic:
        families.extend(
            [
                "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
            ]
        )
    else:
        families.extend(
            [
                "/System/Library/Fonts/Supplemental/Georgia.ttf",
                "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            ]
        )
    for candidate in families:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    raise FileNotFoundError("No supported serif font is installed")


def gradient(theme: Theme) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        vignette = 1.0 - 0.06 * math.sin(math.pi * ratio)
        color = tuple(
            int((theme.top[index] * (1 - ratio) + theme.bottom[index] * ratio) * vignette)
            for index in range(3)
        )
        for x in range(WIDTH):
            edge = abs(x - WIDTH / 2) / (WIDTH / 2)
            shade = 1.0 - 0.14 * edge * edge
            pixels[x, y] = tuple(int(channel * shade) for channel in color)
    return image


def decorative_field(image: Image.Image, theme: Theme, seed: int) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    accent = (*theme.accent, 110)
    for index in range(22):
        x = 60 + ((seed >> (index % 16)) + index * 83) % 680
        y = 160 + ((seed >> ((index + 5) % 16)) + index * 137) % 830
        radius = 1 + (index % 3)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=accent)
    draw.rounded_rectangle((35, 35, 765, 1165), radius=18, outline=(*theme.accent, 170), width=2)
    draw.rounded_rectangle((49, 49, 751, 1151), radius=14, outline=(*theme.accent, 65), width=1)
    draw.line((110, 142, 690, 142), fill=(*theme.accent, 120), width=2)
    draw.line((110, 1018, 690, 1018), fill=(*theme.accent, 120), width=2)


def draw_symbol(image: Image.Image, theme: Theme) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    gold = (*theme.accent, 220)
    haze = Image.new("RGBA", image.size, (0, 0, 0, 0))
    haze_draw = ImageDraw.Draw(haze, "RGBA")
    haze_draw.ellipse((160, 310, 640, 790), fill=(*theme.accent, 18), outline=(*theme.accent, 55), width=3)
    image.paste(haze.filter(ImageFilter.GaussianBlur(18)), (0, 0), haze)

    symbol = theme.symbol
    if symbol == "island":
        draw.arc((220, 370, 580, 730), 205, 338, fill=gold, width=5)
        draw.polygon([(290, 670), (405, 530), (520, 670)], outline=gold)
        draw.ellipse((500, 380, 565, 445), outline=gold, width=3)
    elif symbol == "elephant":
        draw.ellipse((235, 470, 540, 690), outline=gold, width=5)
        draw.ellipse((485, 500, 610, 625), outline=gold, width=4)
        draw.arc((520, 560, 655, 760), 75, 210, fill=gold, width=5)
        for x in (295, 445):
            draw.line((x, 650, x - 10, 745), fill=gold, width=7)
        draw.arc((450, 395, 620, 540), 200, 330, fill=gold, width=4)
    elif symbol == "horse":
        draw.polygon([(205, 690), (400, 410), (610, 690)], outline=gold)
        draw.line((390, 470, 490, 575), fill=gold, width=6)
        draw.ellipse((465, 535, 535, 590), outline=gold, width=4)
        draw.line((490, 590, 455, 675), fill=gold, width=5)
        draw.line((495, 590, 535, 675), fill=gold, width=5)
    elif symbol == "swallow":
        draw.line((400, 390, 400, 705), fill=gold, width=8)
        draw.ellipse((325, 345, 475, 490), outline=gold, width=4)
        draw.arc((210, 475, 405, 650), 210, 350, fill=gold, width=5)
        draw.arc((395, 475, 590, 650), 190, 330, fill=gold, width=5)
    elif symbol == "medal":
        draw.ellipse((295, 430, 505, 640), outline=gold, width=6)
        draw.polygon([(330, 620), (365, 770), (420, 645), (475, 770), (485, 620)], outline=gold)
        draw.line((400, 480, 400, 595), fill=gold, width=5)
        draw.line((345, 538, 455, 538), fill=gold, width=5)
    elif symbol == "boat":
        for offset in (0, 40, 80):
            draw.arc((160, 610 + offset, 640, 760 + offset), 200, 340, fill=gold, width=4)
        draw.polygon([(290, 595), (510, 595), (465, 665), (330, 665)], outline=gold)
        draw.line((400, 420, 400, 595), fill=gold, width=5)
        draw.polygon([(405, 430), (505, 555), (405, 555)], outline=gold)
    elif symbol == "heron":
        draw.line((300, 725, 515, 390), fill=gold, width=5)
        draw.arc((305, 490, 500, 760), 115, 295, fill=gold, width=6)
        draw.arc((440, 405, 560, 535), 125, 295, fill=gold, width=5)
        draw.line((510, 425, 630, 395), fill=gold, width=4)
        draw.line((375, 690, 350, 790), fill=gold, width=4)
        draw.line((405, 690, 430, 790), fill=gold, width=4)
    elif symbol == "pendulum":
        draw.line((400, 350, 400, 650), fill=gold, width=5)
        draw.polygon([(400, 650), (340, 760), (460, 760)], outline=gold)
        draw.arc((205, 360, 595, 790), 210, 330, fill=gold, width=4)
    elif symbol == "bridge":
        draw.line((155, 650, 645, 650), fill=gold, width=7)
        draw.arc((230, 500, 570, 770), 190, 350, fill=gold, width=5)
        for x in (215, 310, 400, 490, 585):
            draw.line((x, 550, x, 650), fill=gold, width=3)
        draw.arc((120, 660, 680, 800), 195, 345, fill=gold, width=3)
    elif symbol == "trail":
        draw.polygon([(140, 720), (330, 420), (430, 620), (550, 380), (680, 720)], outline=gold)
        draw.line((405, 760, 420, 710, 385, 670, 425, 620, 395, 580), fill=gold, width=5)
        draw.ellipse((330, 680, 350, 700), fill=gold)
        draw.ellipse((455, 600, 475, 620), fill=gold)
    elif symbol == "letter":
        draw.rectangle((220, 455, 580, 720), outline=gold, width=5)
        draw.line((220, 455, 400, 610, 580, 455), fill=gold, width=4)
        draw.ellipse((355, 565, 445, 655), outline=gold, width=4)
        draw.arc((310, 350, 490, 500), 205, 335, fill=gold, width=4)
    elif symbol == "dog":
        draw.arc((155, 630, 645, 790), 195, 345, fill=gold, width=4)
        draw.ellipse((325, 480, 490, 650), outline=gold, width=5)
        draw.polygon([(335, 515), (285, 445), (370, 480)], outline=gold)
        draw.line((360, 640, 350, 735), fill=gold, width=5)
        draw.line((450, 640, 470, 735), fill=gold, width=5)
        draw.arc((470, 520, 585, 665), 205, 340, fill=gold, width=5)
    elif symbol == "cathedral":
        draw.polygon([(240, 730), (240, 500), (400, 355), (560, 500), (560, 730)], outline=gold)
        draw.arc((340, 530, 460, 730), 180, 360, fill=gold, width=5)
        draw.line((400, 365, 400, 690), fill=gold, width=3)
        draw.line((360, 440, 440, 440), fill=gold, width=3)
    elif symbol == "villa":
        draw.rectangle((215, 520, 585, 730), outline=gold, width=5)
        draw.polygon([(180, 520), (400, 375), (620, 520)], outline=gold)
        for x in (285, 400, 515):
            draw.arc((x - 40, 565, x + 40, 720), 180, 360, fill=gold, width=4)
        for x, y in ((180, 680), (625, 650), (590, 760), (220, 760)):
            draw.ellipse((x - 28, y - 28, x + 28, y + 28), outline=gold, width=3)
    elif symbol == "door":
        draw.rectangle((275, 370, 525, 760), outline=gold, width=6)
        draw.line((400, 370, 400, 760), fill=gold, width=3)
        draw.ellipse((455, 560, 468, 573), fill=gold)
        draw.ellipse((345, 500, 455, 660), outline=(*theme.accent, 100), width=4)
    elif symbol == "manor":
        draw.rectangle((210, 520, 590, 730), outline=gold, width=5)
        draw.polygon([(175, 520), (400, 370), (625, 520)], outline=gold)
        for x in (280, 400, 520):
            draw.rectangle((x - 32, 565, x + 32, 660), outline=gold, width=3)
        draw.arc((305, 615, 495, 780), 180, 360, fill=gold, width=4)
    elif symbol == "crown":
        draw.polygon([(210, 680), (250, 470), (355, 595), (400, 420), (455, 595), (560, 470), (590, 680)], outline=gold)
        draw.line((230, 680, 575, 680), fill=gold, width=7)
        draw.polygon([(145, 760), (330, 500), (430, 675), (590, 430), (670, 760)], outline=(*theme.accent, 100))
    elif symbol == "usher":
        draw.rectangle((225, 500, 575, 710), outline=gold, width=5)
        draw.polygon([(190, 500), (400, 350), (610, 500)], outline=gold)
        draw.line((400, 350, 405, 810), fill=gold, width=3)
        draw.line((190, 760, 610, 760), fill=gold, width=3)
        draw.arc((170, 710, 630, 875), 195, 345, fill=gold, width=3)
    elif symbol == "portrait":
        draw.rounded_rectangle((235, 360, 565, 790), radius=12, outline=gold, width=7)
        draw.rounded_rectangle((260, 385, 540, 765), radius=8, outline=(*theme.accent, 125), width=3)
        draw.ellipse((330, 445, 470, 595), outline=gold, width=4)
        draw.arc((300, 565, 500, 735), 195, 345, fill=gold, width=5)
        draw.line((285, 405, 515, 745), fill=(*theme.accent, 80), width=2)
        draw.line((515, 405, 285, 745), fill=(*theme.accent, 80), width=2)


def fit_title(draw: ImageDraw.ImageDraw, title: str, max_width: int) -> tuple[list[str], ImageFont.FreeTypeFont]:
    for size in range(56, 35, -2):
        title_font = font(size, bold=True)
        words = title.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if draw.textbbox((0, 0), candidate, font=title_font)[2] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= 4:
            return lines, title_font
    return textwrap.wrap(title, width=22), font(36, bold=True)


def render_front(public: dict[str, Any], theme: Theme) -> Image.Image:
    image = gradient(theme)
    decorative_field(image, theme, int(hashlib.sha256(public["slug"].encode()).hexdigest()[:8], 16))
    draw_symbol(image, theme)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text((400, 92), "E A R N A L I S M   C L A S S I C S", anchor="mm", font=font(16), fill=(*theme.accent, 235))
    lines, title_font = fit_title(draw, str(public["title"]), 650)
    line_height = title_font.size + 8
    top = 190 - (len(lines) - 1) * line_height / 2
    for index, line in enumerate(lines):
        draw.text((400, top + index * line_height), line, anchor="mm", font=title_font, fill=(250, 244, 226, 255))
    author = str(public.get("author") or "").upper()
    draw.text((400, 1060), author, anchor="mm", font=font(24), fill=(*theme.accent, 245))
    return image


def wrap_pixels(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_back(public: dict[str, Any], theme: Theme) -> Image.Image:
    image = gradient(theme)
    decorative_field(image, theme, int(hashlib.sha256((public["slug"] + "back").encode()).hexdigest()[:8], 16))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text((400, 115), "A TIMELESS VOICE, BEAUTIFULLY RESTORED", anchor="mm", font=font(18), fill=(*theme.accent, 240))
    draw.line((170, 158, 630, 158), fill=(*theme.accent, 135), width=2)
    description = str(public.get("short_description") or public.get("description") or "").strip()
    face = font(31)
    lines = wrap_pixels(draw, description, face, 590)
    y = 260
    for line in lines[:12]:
        draw.text((400, y), line, anchor="mm", font=face, fill=(247, 240, 221, 245))
        y += 48
    draw.ellipse((335, 820, 465, 950), outline=(*theme.accent, 190), width=3)
    draw.text((400, 885), "E", anchor="mm", font=font(54, italic=True), fill=(*theme.accent, 235))
    draw.text((400, 1018), "READ WITHIN THE EARNALISM DIGITAL LIBRARY", anchor="mm", font=font(15), fill=(234, 224, 203, 210))
    draw.text((400, 1070), str(public.get("author") or ""), anchor="mm", font=font(22, italic=True), fill=(*theme.accent, 235))
    return image


def save_webp(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "WEBP", quality=78, method=6)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rows = []
    for plan in load_plans():
        public_path = ROOT / "data" / "controlled_publications" / plan.slug / "public_book.json"
        public = read_json(public_path)
        has_cover = bool(public.get("cover_image_url") or public.get("cover_url"))
        if has_cover:
            continue
        theme = THEMES.get(plan.slug)
        if theme is None:
            raise ValueError(f"Missing graphical theme for {plan.slug}")
        front_path = ASSET_ROOT / plan.slug / "front-cover.webp"
        back_path = ASSET_ROOT / plan.slug / "back-cover.webp"
        if args.write:
            save_webp(render_front(public, theme), front_path)
            save_webp(render_back(public, theme), back_path)
        rows.append(
            {
                "slug": plan.slug,
                "title": public.get("title"),
                "author": public.get("author"),
                "theme": theme.name,
                "art_source": "deterministic_vector_primitives_no_external_art",
                "title_author_overlay": "deterministic",
                "front_path": front_path.relative_to(ROOT).as_posix(),
                "back_path": back_path.relative_to(ROOT).as_posix(),
                "front_url": f"https://theearnalism.com/assets/books/{plan.slug}/front-cover.webp",
                "back_url": f"https://theearnalism.com/assets/books/{plan.slug}/back-cover.webp",
                "dimensions": [WIDTH, HEIGHT],
                "front_sha256": sha256_file(front_path) if front_path.is_file() else "",
                "back_sha256": sha256_file(back_path) if back_path.is_file() else "",
                "front_bytes": front_path.stat().st_size if front_path.is_file() else 0,
                "back_bytes": back_path.stat().st_size if back_path.is_file() else 0,
            }
        )
    merged_rows = rows
    if args.write and AUDIT_PATH.is_file():
        existing = read_json(AUDIT_PATH)
        by_slug = {
            str(row.get("slug")): row
            for row in existing.get("rows", [])
            if isinstance(row, dict) and row.get("slug")
        }
        by_slug.update({row["slug"]: row for row in rows})
        merged_rows = [by_slug[slug] for slug in sorted(by_slug)]
    report = {
        "schema": "earnalism-generated-cover-audit-v1",
        "status": "GENERATED_AWAITING_VISUAL_SMOKE" if args.write else "DRY_RUN",
        "cover_count": len(merged_rows),
        "performance_budget_bytes": 180 * 1024,
        "no_unlicensed_external_art": True,
        "visual_smoke": "PENDING" if args.write else "NOT_RUN",
        "visual_smoke_scope": "New or changed covers require visual review; prior checksum-bound rows are preserved.",
        "rows": merged_rows,
    }
    if args.write:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
