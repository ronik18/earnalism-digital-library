#!/usr/bin/env python3
"""Render a local five-second Earnalism logo reveal video.

The renderer is deterministic and uses only local assets, Pillow, and ffmpeg.
It writes temporary PNG frames to output/branding/tmp and removes them after a
successful encode.
"""

from __future__ import annotations

import argparse
import math
import random
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
except ImportError as exc:  # pragma: no cover - exercised manually.
    raise SystemExit(
        "Pillow is required for logo reveal rendering. Install with: "
        "python3 -m pip install -r requirements.txt"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGO = ROOT / "assets" / "branding" / "earnalism-logo.png"
DEFAULT_OUTPUT = ROOT / "output" / "branding" / "earnalism-logo-reveal-5s.mp4"
DEFAULT_TMP = ROOT / "output" / "branding" / "tmp"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_SECONDS = 5
FRAME_COUNT = FPS * DURATION_SECONDS

IVORY = (253, 250, 244)
WARM_IVORY = (247, 240, 225)
ANTIQUE_GOLD = (204, 151, 57)
SOFT_AMBER = (235, 171, 68)
DEEP_BROWN = (58, 31, 22)
BURGUNDY = (72, 18, 28)


@dataclass(frozen=True)
class Particle:
    angle: float
    radius: float
    size: float
    speed: float
    phase: float
    kind: str
    color: tuple[int, int, int]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def ease_out_cubic(value: float) -> float:
    value = clamp(value)
    return 1 - (1 - value) ** 3


def ease_in_out_cubic(value: float) -> float:
    value = clamp(value)
    if value < 0.5:
        return 4 * value * value * value
    return 1 - ((-2 * value + 2) ** 3) / 2


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit(
            "ffmpeg is required to render output/branding/earnalism-logo-reveal-5s.mp4. "
            "Install it first, for example: brew install ffmpeg"
        )
    return ffmpeg


def load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    spacing: int = 0,
) -> None:
    if spacing <= 0:
        width, _ = text_size(draw, text, font)
        draw.text((center_x - width / 2, y), text, font=font, fill=fill)
        return

    glyph_widths = [text_size(draw, char, font)[0] for char in text]
    total_width = sum(glyph_widths) + spacing * max(0, len(text) - 1)
    x = center_x - total_width / 2
    for char, glyph_width in zip(text, glyph_widths):
        draw.text((x, y), char, font=font, fill=fill)
        x += glyph_width + spacing


def make_background() -> Image.Image:
    low_w, low_h = 480, 270
    image = Image.new("RGB", (low_w, low_h), IVORY)
    pixels = image.load()
    for y in range(low_h):
        for x in range(low_w):
            nx = (x / low_w - 0.5) * 2
            ny = (y / low_h - 0.5) * 2
            center = max(0.0, 1.0 - math.sqrt((nx * 0.9) ** 2 + (ny * 1.08) ** 2))
            corner = clamp(math.sqrt(nx * nx + ny * ny) / 1.35)
            glow = center ** 1.7
            vignette = corner ** 2.1
            color = tuple(
                int(
                    IVORY[channel] * (1 - glow)
                    + WARM_IVORY[channel] * glow
                    - 14 * vignette
                    + (8 if channel == 0 else 4 if channel == 1 else 0) * glow
                )
                for channel in range(3)
            )
            pixels[x, y] = tuple(max(0, min(255, value)) for value in color)
    return image.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC).convert("RGBA")


def make_particles() -> list[Particle]:
    rng = random.Random(1847)
    colors = [ANTIQUE_GOLD, SOFT_AMBER, (169, 91, 30), (243, 204, 121), (112, 47, 24)]
    particles: list[Particle] = []
    for index in range(155):
        particles.append(
            Particle(
                angle=rng.uniform(0, math.tau),
                radius=rng.uniform(90, 520),
                size=rng.uniform(2.0, 9.0) if index % 5 else rng.uniform(10.0, 22.0),
                speed=rng.uniform(0.35, 1.85),
                phase=rng.uniform(0, math.tau),
                kind="page" if index % 7 == 0 else "spark",
                color=rng.choice(colors),
            )
        )
    return particles


def draw_rotated_quad(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    width: float,
    height: float,
    angle: float,
    fill: tuple[int, int, int, int],
) -> None:
    points = [(-width / 2, -height / 2), (width / 2, -height / 2), (width / 2, height / 2), (-width / 2, height / 2)]
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    rotated = [(x + px * cos_a - py * sin_a, y + px * sin_a + py * cos_a) for px, py in points]
    draw.polygon(rotated, fill=fill)


def draw_particles(image: Image.Image, particles: list[Particle], seconds: float) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    center_x, center_y = WIDTH * 0.5, HEIGHT * 0.42

    reveal = ease_out_cubic((seconds - 0.8) / 1.4)
    early_alpha = clamp(seconds / 0.8)
    settle = clamp((seconds - 3.0) / 1.4)
    hold_fade = 1 - 0.65 * settle

    for particle in particles:
        if seconds < 0.1:
            continue
        theta = particle.angle + particle.speed * seconds + (1 - reveal) * 2.7
        radius = particle.radius * (1.0 - 0.38 * reveal) + 16 * math.sin(seconds * 1.7 + particle.phase)
        drift = 1 - reveal
        x = lerp(-260 + 180 * math.cos(particle.phase), center_x, reveal) + math.cos(theta) * radius
        y = lerp(HEIGHT * 0.48 + 80 * math.sin(particle.phase), center_y, reveal) + math.sin(theta) * radius * 0.68
        x += math.sin(seconds * 0.35 + particle.phase) * 22 * drift
        alpha = int(185 * early_alpha * hold_fade * (0.45 + 0.55 * math.sin(particle.phase + 1.8) ** 2))
        if alpha <= 2:
            continue

        fill = (*particle.color, alpha)
        if particle.kind == "page":
            draw_rotated_quad(draw, x, y, particle.size * 1.7, particle.size * 0.72, theta + 0.7, fill)
        else:
            size = particle.size
            draw.ellipse((x - size / 2, y - size / 2, x + size / 2, y + size / 2), fill=fill)

    layer = layer.filter(ImageFilter.GaussianBlur(radius=0.18))
    image.alpha_composite(layer)


def make_logo_lockup(logo_path: Path) -> Image.Image:
    if not logo_path.exists():
        raise SystemExit(f"Missing logo asset: {logo_path}")

    emblem = Image.open(logo_path).convert("RGBA")
    emblem.thumbnail((320, 320), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (980, 680), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    brand_font = load_font(
        [
            "/System/Library/Fonts/Supplemental/Didot.ttc",
            "/System/Library/Fonts/Supplemental/Baskerville.ttc",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
        ],
        104,
    )
    tagline_font = load_font(
        [
            "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
            "/System/Library/Fonts/Supplemental/Baskerville.ttc",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
        ],
        34,
    )
    subline_font = load_font(
        [
            "/System/Library/Fonts/Avenir Next.ttc",
            "/System/Library/Fonts/Avenir.ttc",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
        ],
        25,
    )

    center_x = canvas.width // 2
    emblem_x = center_x - emblem.width // 2
    canvas.alpha_composite(emblem, (emblem_x, 24))

    draw_centered_text(draw, center_x, 363, "Earnalism", brand_font, (*DEEP_BROWN, 245))
    draw_centered_text(draw, center_x, 484, "Where Learning Becomes Earning", tagline_font, (*ANTIQUE_GOLD, 235))
    draw_centered_text(draw, center_x, 548, "A REO ENTERPRISE VENTURE", subline_font, (*DEEP_BROWN, 225), spacing=7)

    bbox = canvas.getbbox()
    if not bbox:
        return canvas
    return canvas.crop((bbox[0] - 20, bbox[1] - 20, bbox[2] + 20, bbox[3] + 24))


def tint_logo(logo: Image.Image, seconds: float) -> Image.Image:
    shimmer = clamp((seconds - 2.2) / 1.0) * (1 - 0.35 * clamp((seconds - 3.8) / 1.2))
    if shimmer <= 0.02:
        return logo
    enhanced = ImageEnhance.Contrast(logo).enhance(1.0 + 0.05 * shimmer)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.0 + 0.12 * shimmer)
    return enhanced


def draw_logo(image: Image.Image, logo: Image.Image, seconds: float) -> None:
    progress = ease_out_cubic((seconds - 2.2) / 1.0)
    if progress <= 0:
        return

    hold_push = 1 + 0.012 * ease_in_out_cubic(clamp((seconds - 3.2) / 1.0))
    scale = (0.86 + 0.14 * progress) * hold_push
    alpha = int(255 * progress)
    logo_frame = tint_logo(logo, seconds).resize(
        (int(logo.width * scale), int(logo.height * scale)),
        Image.Resampling.LANCZOS,
    )
    if alpha < 255:
        alpha_channel = logo_frame.getchannel("A").point(lambda value: int(value * alpha / 255))
        logo_frame.putalpha(alpha_channel)

    x = (WIDTH - logo_frame.width) // 2
    y = int(HEIGHT * 0.49 - logo_frame.height / 2)

    shadow = Image.new("RGBA", logo_frame.size, (0, 0, 0, 0))
    shadow.putalpha(logo_frame.getchannel("A").filter(ImageFilter.GaussianBlur(18)))
    shadow_tint = Image.new("RGBA", logo_frame.size, (82, 48, 20, int(42 * progress)))
    shadow_tint.putalpha(shadow.getchannel("A").point(lambda value: min(value, int(42 * progress))))
    image.alpha_composite(shadow_tint, (x + 4, y + 18))
    image.alpha_composite(logo_frame, (x, y))


def draw_glow_and_sweep(image: Image.Image, seconds: float) -> None:
    glow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer, "RGBA")

    ambient = int(42 * clamp(seconds / 0.8))
    draw.ellipse(
        (WIDTH * 0.24, HEIGHT * 0.12, WIDTH * 0.76, HEIGHT * 0.9),
        fill=(224, 165, 65, ambient),
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(70))
    image.alpha_composite(glow_layer)

    underline_progress = clamp((seconds - 3.2) / 1.0)
    if underline_progress > 0:
        underline = Image.new("RGBA", image.size, (0, 0, 0, 0))
        udraw = ImageDraw.Draw(underline, "RGBA")
        width = 660 * ease_out_cubic(underline_progress)
        y = int(HEIGHT * 0.71)
        udraw.rounded_rectangle(
            (WIDTH / 2 - width / 2, y, WIDTH / 2 + width / 2, y + 5),
            radius=3,
            fill=(204, 151, 57, int(105 * (1 - 0.15 * clamp((seconds - 4.2) / 0.8)))),
        )
        underline = underline.filter(ImageFilter.GaussianBlur(4))
        image.alpha_composite(underline)

    sweep_progress = clamp((seconds - 3.35) / 0.72)
    if 0 < sweep_progress < 1:
        sweep = Image.new("RGBA", image.size, (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(sweep, "RGBA")
        x = lerp(WIDTH * 0.28, WIDTH * 0.72, ease_in_out_cubic(sweep_progress))
        sdraw.polygon(
            [(x - 38, 240), (x + 58, 240), (x - 112, 735), (x - 206, 735)],
            fill=(255, 228, 154, 54),
        )
        sweep = sweep.filter(ImageFilter.GaussianBlur(18))
        image.alpha_composite(sweep)


def draw_frame(background: Image.Image, logo: Image.Image, particles: list[Particle], frame_index: int) -> Image.Image:
    seconds = frame_index / FPS
    fade_in = clamp(seconds / 0.8)
    image = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))

    bg = background.copy()
    bg_alpha = bg.getchannel("A").point(lambda value: int(value * fade_in))
    bg.putalpha(bg_alpha)
    image.alpha_composite(bg)

    draw_glow_and_sweep(image, seconds)
    draw_particles(image, particles, seconds)
    draw_logo(image, logo, seconds)

    return image.convert("RGB")


def render_frames(logo_path: Path, tmp_dir: Path) -> None:
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    background = make_background()
    logo = make_logo_lockup(logo_path)
    particles = make_particles()

    for frame_index in range(FRAME_COUNT):
        frame = draw_frame(background, logo, particles, frame_index)
        frame.save(tmp_dir / f"frame_{frame_index:04d}.png", optimize=True)


def encode_video(ffmpeg: str, tmp_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(tmp_dir / "frame_%04d.png"),
        "-t",
        str(DURATION_SECONDS),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(FPS),
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the Earnalism 5-second logo reveal MP4.")
    parser.add_argument("--logo", type=Path, default=DEFAULT_LOGO, help="Path to the Earnalism logo PNG.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output MP4 path.")
    parser.add_argument("--tmp-dir", type=Path, default=DEFAULT_TMP, help="Temporary frame directory.")
    parser.add_argument("--keep-frames", action="store_true", help="Keep temporary frames for visual debugging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logo_path = args.logo if args.logo.is_absolute() else ROOT / args.logo
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    tmp_dir = args.tmp_dir if args.tmp_dir.is_absolute() else ROOT / args.tmp_dir

    ffmpeg = require_ffmpeg()
    render_frames(logo_path, tmp_dir)
    encode_video(ffmpeg, tmp_dir, output_path)

    if not args.keep_frames:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"Rendered {output_path}")
    print(f"Duration: {DURATION_SECONDS}s | Resolution: {WIDTH}x{HEIGHT} | FPS: {FPS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
