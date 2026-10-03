#!/usr/bin/env python3
"""Deterministic, inactive-only cover derivative for bn-035.

This renderer reads existing repository metadata, uses repository-owned font
assets with RAQM shaping, and never performs network or publication actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features
from fontTools.ttLib import TTFont


CANVAS = (1600, 2400)
REPO = Path("/tmp/earnalism-post509-ledger")
PUBLIC_BOOK = REPO / "data/controlled_publications/bn-035/public_book.json"
EXPECTED_PUBLIC_BOOK_SHA256 = "5356ea9d89eb2539798a05d37106db47a8b19d4a027f81e0e1b2c80f7beae7e2"
BN_SERIF = REPO / "frontend/src/assets/fonts/noto-serif-bengali-600.ttf"
BN_SANS = REPO / "frontend/src/assets/fonts/noto-sans-bengali-500.ttf"
EN_SERIF = REPO / "frontend/src/assets/fonts/eb-garamond-400.ttf"
EXPECTED = {
    "title": "বড়দিদি",
    "author": "শরৎচন্দ্র চট্টোপাধ্যায়",
    "short_description": "বড় বোনের নিঃস্বার্থ ভালোবাসা ও ত্যাগের অসাধারণ কাহিনি।",
    "about_author": "শরৎচন্দ্র চট্টোপাধ্যায় (১৮৭৬–১৯৩৮) বাংলা সাহিত্যের সবচেয়ে জনপ্রিয় কথাসাহিত্যিক।",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_metadata() -> dict:
    if sha256(PUBLIC_BOOK) != EXPECTED_PUBLIC_BOOK_SHA256:
        raise RuntimeError("public_book.json changed from reviewed preimage")
    payload = json.loads(PUBLIC_BOOK.read_text(encoding="utf-8"))
    for key, expected in EXPECTED.items():
        if payload.get(key) != expected:
            raise RuntimeError(f"metadata mismatch for {key}")
    return payload


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size, layout_engine=ImageFont.Layout.RAQM)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        box = draw.textbbox((0, 0), trial, font=face, direction="ltr", language="bn")
        if box[2] - box[0] <= max_width:
            current = trial
        else:
            if not current:
                raise RuntimeError(f"single token exceeds safe width: {word}")
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def center_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    y: int,
    face: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    *,
    language: str,
    spacing: int,
) -> tuple[int, tuple[int, int, int, int]]:
    boxes: list[tuple[int, int, int, int]] = []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=face, direction="ltr", language=language)
        width = box[2] - box[0]
        height = box[3] - box[1]
        x = (CANVAS[0] - width) // 2
        draw.text((x, y), line, font=face, fill=fill, direction="ltr", language=language)
        boxes.append((x, y, x + width, y + height))
        y += height + spacing
    return y, (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def background() -> Image.Image:
    width, height = CANVAS
    image = Image.new("RGBA", CANVAS, "#d8c9aa")
    pixels = image.load()
    for y in range(height):
        vertical = y / (height - 1)
        for x in range(width):
            horizontal = abs(x - width / 2) / (width / 2)
            shade = int(17 * vertical + 15 * horizontal * horizontal)
            pixels[x, y] = (max(160, 224 - shade), max(145, 211 - shade), max(120, 181 - shade), 255)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((92, 86, 1508, 2314), radius=70, fill=(67, 20, 31, 255), outline=(211, 173, 87, 255), width=8)
    draw.rounded_rectangle((136, 130, 1464, 2270), radius=52, outline=(243, 219, 161, 160), width=3)
    return image


def draw_shelter_motif(draw: ImageDraw.ImageDraw, *, top: int) -> tuple[int, int, int, int]:
    # A deterministic graphical motif kept wholly outside the text zones.
    gold = (216, 179, 91, 255)
    dim = (216, 179, 91, 95)
    bounds = (365, top, 1235, top + 610)
    draw.arc((365, top, 1235, top + 850), 195, 345, fill=gold, width=24)
    draw.arc((470, top + 100, 1130, top + 740), 195, 345, fill=dim, width=14)
    draw.ellipse((690, top + 210, 910, top + 430), fill=(216, 179, 91, 210))
    draw.polygon(
        [(800, top + 170), (940, top + 430), (800, top + 590), (660, top + 430)],
        fill=(216, 179, 91, 58),
        outline=(216, 179, 91, 180),
    )
    draw.line((445, top + 600, 1155, top + 600), fill=gold, width=8)
    return bounds


def render_front(metadata: dict, out_path: Path) -> dict:
    image = background()
    draw = ImageDraw.Draw(image, "RGBA")
    en_small = font(EN_SERIF, 42)
    bn_title = font(BN_SERIF, 174)
    bn_author = font(BN_SANS, 70)

    _, library_box = center_lines(draw, ["THE EARNALISM LIBRARY"], 238, en_small, (244, 216, 148, 255), language="en", spacing=0)
    draw.line((340, 330, 1260, 330), fill=(216, 179, 91, 190), width=4)
    motif_box = draw_shelter_motif(draw, top=430)

    _, title_box = center_lines(draw, [metadata["title"]], 1190, bn_title, (255, 240, 199, 255), language="bn", spacing=0)
    _, author_box = center_lines(draw, [metadata["author"]], 1450, bn_author, (239, 211, 157, 255), language="bn", spacing=0)
    draw.line((390, 1618, 1210, 1618), fill=(216, 179, 91, 150), width=4)
    draw.ellipse((770, 1685, 830, 1745), outline=(216, 179, 91, 230), width=7)
    draw.ellipse((788, 1703, 812, 1727), fill=(216, 179, 91, 230))
    _, imprint_box = center_lines(draw, ["Earnalism — A Reo Enterprise Venture"], 2150, en_small, (244, 222, 171, 255), language="en", spacing=0)

    for text_box in (library_box, title_box, author_box, imprint_box):
        if not (text_box[3] < motif_box[1] or text_box[1] > motif_box[3]):
            raise RuntimeError(f"motif intersects typography: {text_box}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out_path, format="PNG", compress_level=9, optimize=False)
    return {
        "text_boxes": {"library": library_box, "title": title_box, "author": author_box, "imprint": imprint_box},
        "ornament_box": motif_box,
    }


def render_back(metadata: dict, out_path: Path) -> dict:
    image = background()
    draw = ImageDraw.Draw(image, "RGBA")
    en_small = font(EN_SERIF, 42)
    bn_title = font(BN_SERIF, 138)
    bn_blurb = font(BN_SERIF, 68)
    bn_about = font(BN_SANS, 50)

    _, label_box = center_lines(draw, ["BACK COVER"], 226, en_small, (244, 216, 148, 255), language="en", spacing=0)
    _, title_box = center_lines(draw, [metadata["title"]], 382, bn_title, (255, 240, 199, 255), language="bn", spacing=0)
    draw.line((320, 610, 1280, 610), fill=(216, 179, 91, 190), width=4)

    blurb_lines = wrap(draw, metadata["short_description"], bn_blurb, 1050)
    _, blurb_box = center_lines(draw, blurb_lines, 745, bn_blurb, (248, 226, 179, 255), language="bn", spacing=38)
    about_lines = wrap(draw, metadata["about_author"], bn_about, 1030)
    _, about_box = center_lines(draw, about_lines, 1115, bn_about, (226, 199, 148, 255), language="bn", spacing=26)

    motif_box = draw_shelter_motif(draw, top=1510)
    _, imprint_box = center_lines(draw, ["Earnalism — A Reo Enterprise Venture"], 2150, en_small, (244, 222, 171, 255), language="en", spacing=0)

    for text_box in (label_box, title_box, blurb_box, about_box, imprint_box):
        if not (text_box[3] < motif_box[1] or text_box[1] > motif_box[3]):
            raise RuntimeError(f"motif intersects typography: {text_box}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out_path, format="PNG", compress_level=9, optimize=False)
    return {
        "text_boxes": {"label": label_box, "title": title_box, "short_description": blurb_box, "about_author": about_box, "imprint": imprint_box},
        "ornament_box": motif_box,
        "short_description_lines": blurb_lines,
        "about_author_lines": about_lines,
    }


def cmap_check(path: Path, strings: list[str]) -> dict:
    tt = TTFont(path)
    cmap = {codepoint for table in tt["cmap"].tables for codepoint in table.cmap}
    missing = sorted({char for text in strings for char in text if not char.isspace() and ord(char) not in cmap})
    return {"font": str(path), "sha256": sha256(path), "missing_codepoints": [f"U+{ord(char):04X}" for char in missing]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not all(features.check(name) for name in ("raqm", "harfbuzz", "fribidi", "freetype2")):
        raise RuntimeError("required shaping stack unavailable")
    metadata = load_metadata()
    for value in EXPECTED.values():
        if unicodedata.normalize("NFC", value) != value:
            raise RuntimeError("metadata must remain NFC-normalized")
        if "\u25cc" in value:
            raise RuntimeError("input contains a dotted-circle glyph")

    front = args.output / "bn-035-front-inactive.png"
    back = args.output / "bn-035-back-inactive.png"
    layout = {"front": render_front(metadata, front), "back": render_back(metadata, back)}
    checks = {
        "scope": "INACTIVE_DERIVATIVE_ONLY_NO_APPROVAL_OR_ACTIVATION_CLAIM",
        "source_public_book": str(PUBLIC_BOOK),
        "source_public_book_sha256": sha256(PUBLIC_BOOK),
        "metadata": {key: metadata[key] for key in EXPECTED},
        "metadata_nfc": True,
        "input_contains_dotted_circle": False,
        "forbidden_status_badge_present": False,
        "raqm": features.check("raqm"),
        "harfbuzz": features.check("harfbuzz"),
        "fribidi": features.check("fribidi"),
        "freetype2": features.check("freetype2"),
        "fonts": [
            cmap_check(BN_SERIF, list(EXPECTED.values())),
            cmap_check(BN_SANS, list(EXPECTED.values())),
        ],
        "outputs": {
            "front": {"path": str(front), "sha256": sha256(front), "bytes": front.stat().st_size, "dimensions": list(Image.open(front).size)},
            "back": {"path": str(back), "sha256": sha256(back), "bytes": back.stat().st_size, "dimensions": list(Image.open(back).size)},
        },
        "layout": layout,
    }
    (args.output / "render-checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
