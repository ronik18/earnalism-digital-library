from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WORK_DIR = Path(__file__).resolve().parent
SOURCE_DIR = Path("/workspace/scratch/181ef0a25f05/next-pair-a")
ORIGINAL_FRONT = SOURCE_DIR / "the-art-of-money-getting-front.png"
ORIGINAL_BACK = SOURCE_DIR / "the-art-of-money-getting-back.png"
PRESERVED_FRONT = WORK_DIR / "original-front.png"
PRESERVED_BACK = WORK_DIR / "original-back.png"
SERIF = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
SERIF_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf")

MAROON = (66, 22, 30, 255)
GOLD = (223, 183, 92, 255)
CREAM = (246, 231, 189, 255)

SOURCE_EXCERPT_LINES = [
    "In the United States, where we have more land",
    "than people, it is not at all difficult for persons",
    "in good health to make money.",
    "",
    "In this comparatively new field there are so many",
    "avenues of success open, so many vocations which",
    "are not crowded, that any person of either sex",
    "who is willing, at least for the time being, to",
    "engage in any respectable occupation that offers,",
    "may find lucrative employment.",
]
SOURCE_EXCERPT = " ".join(line for line in SOURCE_EXCERPT_LINES if line)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def centered_text(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0]
    draw.text(((1600 - width) / 2, y), text, font=font, fill=fill)


def render_front(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(str(SERIF), 105)
    author = ImageFont.truetype(str(SERIF), 58)

    draw.rounded_rectangle(
        (210, 700, 1390, 1265), radius=46, fill=MAROON, outline=GOLD, width=6
    )
    centered_text(draw, 780, "The Art of", title, CREAM)
    centered_text(draw, 925, "Money Getting", title, CREAM)
    draw.line((480, 1080, 1120, 1080), fill=GOLD, width=3)
    centered_text(draw, 1110, "P. T. Barnum", author, CREAM)

    # Remove the internal release-status pill without replacing it with a claim.
    draw.rounded_rectangle((180, 1830, 1420, 2140), radius=30, fill=MAROON)
    image.save(destination, format="PNG", optimize=False, compress_level=9)


def render_back(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image)
    kicker = ImageFont.truetype(str(SERIF), 44)
    title = ImageFont.truetype(str(SERIF), 102)
    body = ImageFont.truetype(str(SERIF), 48)
    author = ImageFont.truetype(str(SERIF), 62)

    draw.rounded_rectangle((95, 70, 1505, 2160), radius=52, fill=MAROON)
    draw.rounded_rectangle((125, 70, 1475, 2160), radius=52, outline=GOLD, width=6)
    centered_text(draw, 120, "BACK COVER", kicker, GOLD)
    centered_text(draw, 245, "The Art of", title, CREAM)
    centered_text(draw, 380, "Money Getting", title, CREAM)
    draw.line((300, 555, 1300, 555), fill=GOLD, width=3)

    y = 620
    for line in SOURCE_EXCERPT_LINES:
        if line:
            centered_text(draw, y, line, body, CREAM)
        y += 75

    draw.line((500, 1500, 1100, 1500), fill=GOLD, width=3)
    centered_text(draw, 1540, "P. T. Barnum", author, CREAM)
    image.save(destination, format="PNG", optimize=False, compress_level=9)


def render_pair(suffix: str) -> tuple[Path, Path]:
    front = WORK_DIR / f"inactive-front-{suffix}.png"
    back = WORK_DIR / f"inactive-back-{suffix}.png"
    render_front(PRESERVED_FRONT, front)
    render_back(PRESERVED_BACK, back)
    return front, back


def main() -> None:
    shutil.copyfile(ORIGINAL_FRONT, PRESERVED_FRONT)
    shutil.copyfile(ORIGINAL_BACK, PRESERVED_BACK)

    expected_originals = {
        "front": "0c1d69427d4fb59f6a844abda7caf06113476d5fe548afcf0293c5ba12a53616",
        "back": "96877955ed3ef8a0a9d86353a76584c881b513d6ea50ba09443e028adf66b5be",
    }
    actual_originals = {
        "front": sha256(PRESERVED_FRONT),
        "back": sha256(PRESERVED_BACK),
    }
    if actual_originals != expected_originals:
        raise SystemExit(f"original hash mismatch: {actual_originals}")

    front_run1, back_run1 = render_pair("run1")
    front_run2, back_run2 = render_pair("run2")
    deterministic = (
        front_run1.read_bytes() == front_run2.read_bytes()
        and back_run1.read_bytes() == back_run2.read_bytes()
    )
    if not deterministic:
        raise SystemExit("double render mismatch")

    receipt = {
        "schema": "earnalism.inactive-cover-derivative-receipt.v1",
        "slug": "the-art-of-money-getting",
        "state": "INACTIVE_SCRATCH_CANDIDATE_NOT_APPROVED_OR_PROMOTED",
        "method": "deterministic local Pillow mask-and-typeset derivative; no image generation, network, or paid call",
        "originals": {
            "front": {
                "path": str(PRESERVED_FRONT),
                "url": "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1783273638/earnalism/covers/front/the-art-of-money-getting_front_1600x2400.png",
                "sha256": actual_originals["front"],
                "dimensions": [1600, 2400],
                "bytes": PRESERVED_FRONT.stat().st_size,
            },
            "back": {
                "path": str(PRESERVED_BACK),
                "url": "https://res.cloudinary.com/dzlrhlfpu/image/upload/v1783273639/earnalism/covers/back/the-art-of-money-getting_back_1600x2400.png",
                "sha256": actual_originals["back"],
                "dimensions": [1600, 2400],
                "bytes": PRESERVED_BACK.stat().st_size,
            },
        },
        "repairs": [
            "Removed internal LIVE CONTROLLED RELEASE badge without adding a release claim.",
            "Placed title and author on an opaque panel so decorative coins cannot cross text.",
            "Replaced truncated/occluded back copy with a complete exact excerpt already present in the controlled chapter source.",
        ],
        "source_excerpt": SOURCE_EXCERPT,
        "font_files": {
            "serif": {"path": str(SERIF), "sha256": sha256(SERIF)},
            "serif_bold": {"path": str(SERIF_BOLD), "sha256": sha256(SERIF_BOLD)},
        },
        "renders": {
            "front_run1": {"path": str(front_run1), "sha256": sha256(front_run1), "bytes": front_run1.stat().st_size},
            "front_run2": {"path": str(front_run2), "sha256": sha256(front_run2), "bytes": front_run2.stat().st_size},
            "back_run1": {"path": str(back_run1), "sha256": sha256(back_run1), "bytes": back_run1.stat().st_size},
            "back_run2": {"path": str(back_run2), "sha256": sha256(back_run2), "bytes": back_run2.stat().st_size},
        },
        "double_render_byte_identity": "PASS",
        "cover_display_approved": False,
        "publication_approved": False,
        "production_activation_authorized": False,
        "next_gate": "Two independent visual/source reviews, then genuine cover-display and publication acceptance before any repository or runtime mutation.",
    }
    (WORK_DIR / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
