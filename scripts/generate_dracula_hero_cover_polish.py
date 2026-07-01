#!/usr/bin/env python3
"""Generate the homepage-only polished Dracula hero cover derivative.

The source cover remains preserved for provenance and SEO. This derivative is
used only inside the 3D homepage hero book object, where the cover must read as
a premium hardback at a glance.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend/public/assets/books/dracula/dracula-front-cover.webp"
OUTPUT = ROOT / "frontend/public/assets/books/dracula/dracula-front-cover-hero-polished.webp"


def scale_box(box: tuple[float, float, float, float], scale: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = (round(value * scale) for value in box)
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def scale_points(points: list[tuple[float, float]], scale: int) -> list[tuple[int, int]]:
    return [(round(x * scale), round(y * scale)) for x, y in points]


def soften_path_artifacts(image: Image.Image) -> Image.Image:
    """Quiet the red trail on the path without removing title or rose accents."""

    result = image.convert("RGBA")
    pixels = result.load()
    width, height = result.size

    x_min = int(width * 0.45)
    x_max = int(width * 0.78)
    y_min = int(height * 0.59)
    y_max = int(height * 0.80)

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            red, green, blue, alpha = pixels[x, y]
            red_dominant = red > 62 and red > green * 1.28 and red > blue * 1.12
            if not red_dominant:
                continue
            # Keep a natural, very subdued rose/blood-red trace rather than
            # removing the accent entirely.
            pixels[x, y] = (
                int(red * 0.58 + 34),
                int(green * 0.72 + 22),
                int(blue * 0.72 + 20),
                alpha,
            )

    return result


def ornamental_border_overlay(size: tuple[int, int]) -> Image.Image:
    width, height = size
    scale = 3
    overlay = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    gold = (224, 185, 101, 185)
    gold_soft = (255, 225, 157, 132)
    gold_shadow = (77, 46, 18, 150)
    rose = (118, 22, 26, 92)
    edge_matte = (2, 2, 2, 76)

    def rr(box, fill, outline=None, radius=0, width_px=1):
        draw.rounded_rectangle(
            scale_box(box, scale),
            radius=round(radius * scale),
            fill=fill,
            outline=outline,
            width=round(width_px * scale),
        )

    def line(points, fill, width_px=1):
        draw.line(scale_points(points, scale), fill=fill, width=round(width_px * scale), joint="curve")

    def arc(box, start, end, fill, width_px=1):
        draw.arc(scale_box(box, scale), start=start, end=end, fill=fill, width=round(width_px * scale))

    # Subtly calm the old uneven edge artwork, then redraw a disciplined frame.
    rr((22, 22, width - 22, height - 22), fill=None, outline=edge_matte, radius=24, width_px=18)
    rr((34, 34, width - 34, height - 34), fill=None, outline=gold_shadow, radius=20, width_px=3)
    rr((38, 38, width - 38, height - 38), fill=None, outline=gold, radius=18, width_px=2)
    rr((54, 55, width - 54, height - 55), fill=None, outline=gold_soft, radius=13, width_px=1)
    rr((67, 70, width - 67, height - 70), fill=None, outline=(132, 91, 41, 108), radius=10, width_px=1)

    def corner(origin_x: int, origin_y: int, sx: int, sy: int) -> None:
        x0 = origin_x
        y0 = origin_y
        line([(x0, y0 + sy * 78), (x0, y0 + sy * 24), (x0 + sx * 78, y0 + sy * 24)], gold, 1.25)
        line([(x0 + sx * 12, y0 + sy * 96), (x0 + sx * 12, y0 + sy * 42), (x0 + sx * 96, y0 + sy * 42)], gold_shadow, 1.0)
        arc((x0 + sx * 23, y0 + sy * 23, x0 + sx * 116, y0 + sy * 116), 180 if sx > 0 else 270, 270 if sx > 0 else 360, gold_soft, 1.2)
        arc((x0 + sx * 38, y0 + sy * 38, x0 + sx * 136, y0 + sy * 136), 182 if sx > 0 else 272, 264 if sx > 0 else 354, gold, 1.0)
        leaf_x = x0 + sx * 86
        leaf_y = y0 + sy * 52
        draw.ellipse(scale_box((leaf_x - 6, leaf_y - 3, leaf_x + 8, leaf_y + 5), scale), fill=gold_soft)
        draw.ellipse(scale_box((x0 + sx * 52 - 5, y0 + sy * 85 - 4, x0 + sx * 52 + 7, y0 + sy * 85 + 5), scale), fill=rose)

    corner(43, 43, 1, 1)
    corner(width - 43, 43, -1, 1)
    corner(43, height - 43, 1, -1)
    corner(width - 43, height - 43, -1, -1)

    center_x = width / 2
    for y, sy in ((55, 1), (height - 57, -1)):
        line([(center_x - 95, y), (center_x - 28, y)], gold, 1.0)
        line([(center_x + 28, y), (center_x + 95, y)], gold, 1.0)
        line([(center_x, y + sy * 3), (center_x - 18, y + sy * 21), (center_x, y + sy * 38), (center_x + 18, y + sy * 21), (center_x, y + sy * 3)], gold_soft, 1.0)
        draw.ellipse(scale_box((center_x - 7, y + sy * 13 - 4, center_x + 7, y + sy * 13 + 10), scale), fill=gold)

    return overlay.resize(size, Image.Resampling.LANCZOS)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    image = Image.open(SOURCE).convert("RGBA")
    image = soften_path_artifacts(image)
    image = ImageEnhance.Contrast(image).enhance(1.035)
    image = ImageEnhance.Sharpness(image).enhance(1.04)
    image = Image.alpha_composite(image, ornamental_border_overlay(image.size))
    image = image.convert("RGB")
    image.save(OUTPUT, "WEBP", quality=90, method=6)
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
