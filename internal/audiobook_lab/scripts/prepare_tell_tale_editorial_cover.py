#!/usr/bin/env python3
"""Prepare a private, rights-bound Tell-Tale Heart editorial cover pair.

This tool composes deterministic typography over the verified Odilon Redon
public-domain source artwork. It writes only to a private cover-candidate
package and never uploads, canonicalizes, or changes reader/audio release truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SLUG = "the-tell-tale-heart"
TARGET_SIZE = (1600, 2400)
SOURCE_SHA256 = "075f2c285d2f546076e8f1f50f03da43184f4c51d47746fbabc2358f9d37ed56"
DEFAULT_PACKAGE = (
    ROOT
    / "internal"
    / "audiobook_lab"
    / "sprint1_publication"
    / "cover_candidates"
    / SLUG
)
DEFAULT_SOURCE = DEFAULT_PACKAGE / "source_art" / "odilon-redon-the-tell-tale-heart-1883.jpeg"
DEFAULT_RIGHTS = DEFAULT_PACKAGE / "source_rights_evidence.json"
CATALOG_PATHS = (
    ROOT / "data" / "controlled_publications" / SLUG / "public_book.json",
    ROOT / "backend" / "data" / "controlled_publications" / SLUG / "public_book.json",
)
FONT_CANDIDATES = {
    "regular": (
        Path("/System/Library/Fonts/Supplemental/Georgia.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
    ),
    "bold": (
        Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    ),
}
IVORY = (249, 235, 199, 255)
GOLD = (214, 176, 96, 235)
BURGUNDY = (44, 13, 22, 225)
SAFE_MARGIN = 120


class CoverCandidateError(RuntimeError):
    """Raised when a private cover candidate cannot be prepared safely."""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_catalog_truth() -> tuple[dict[str, Any], dict[str, str]]:
    records = [read_json(path) for path in CATALOG_PATHS]
    truth = records[0]
    if truth.get("slug") != SLUG:
        raise CoverCandidateError(f"unexpected canonical slug: {truth.get('slug')}")
    for record in records[1:]:
        for field in ("slug", "title", "author", "short_description"):
            if record.get(field) != truth.get(field):
                raise CoverCandidateError(f"controlled mirrors disagree on {field}")
    title = str(truth.get("title") or "").strip()
    author = str(truth.get("author") or "").strip()
    description = str(truth.get("short_description") or "").strip()
    if not title or not author or not description:
        raise CoverCandidateError("canonical title, author, and short description are required")
    return truth, {str(path.relative_to(ROOT)): sha256_file(path) for path in CATALOG_PATHS}


def select_font(size: int, *, bold: bool = False) -> tuple[ImageFont.FreeTypeFont, Path]:
    key = "bold" if bold else "regular"
    for candidate in FONT_CANDIDATES[key]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size), candidate
    raise CoverCandidateError(f"no deterministic {key} serif font is available")


def text_width(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=face)
    return int(box[2] - box[0])


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    face: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
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
    return lines


def fit_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    max_width: int,
    max_lines: int,
    max_size: int,
    min_size: int,
    bold: bool,
) -> tuple[ImageFont.FreeTypeFont, Path, list[str]]:
    for size in range(max_size, min_size - 1, -4):
        face, font_path = select_font(size, bold=bold)
        lines = wrap_text(draw, text, face, max_width)
        if len(lines) <= max_lines:
            return face, font_path, lines
    raise CoverCandidateError(f"text does not fit configured geometry: {text}")


def line_height(draw: ImageDraw.ImageDraw, face: ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), "Ag", font=face)
    return int(box[3] - box[1])


def draw_centered_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    name: str,
    y: int,
    max_width: int,
    max_lines: int,
    max_size: int,
    min_size: int,
    bold: bool,
    fill: tuple[int, int, int, int],
    line_gap: int,
) -> tuple[dict[str, Any], Path]:
    face, font_path, lines = fit_lines(
        draw,
        text,
        max_width=max_width,
        max_lines=max_lines,
        max_size=max_size,
        min_size=min_size,
        bold=bold,
    )
    height = line_height(draw, face)
    top = y
    max_rendered_width = 0
    for line in lines:
        width = text_width(draw, line, face)
        max_rendered_width = max(max_rendered_width, width)
        draw.text(((TARGET_SIZE[0] - width) / 2, y), line, font=face, fill=fill)
        y += height + line_gap
    bottom = y - line_gap
    left = (TARGET_SIZE[0] - max_rendered_width) // 2
    return (
        {
            "name": name,
            "text": text,
            "lines": lines,
            "font_size": face.size,
            "box": [left, top, TARGET_SIZE[0] - left, bottom],
        },
        font_path,
    )


def cover_crop(source: Image.Image, *, mirror: bool = False) -> tuple[Image.Image, dict[str, Any]]:
    image = ImageOps.exif_transpose(source).convert("RGB")
    if mirror:
        image = ImageOps.mirror(image)
    source_width, source_height = image.size
    target_ratio = TARGET_SIZE[0] / TARGET_SIZE[1]
    crop_width = round(source_height * target_ratio)
    left = max(0, (source_width - crop_width) // 2)
    crop_box = (left, 0, min(source_width, left + crop_width), source_height)
    image = image.crop(crop_box).resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    return image, {
        "source_size": [source_width, source_height],
        "crop_box": list(crop_box),
        "target_size": list(TARGET_SIZE),
        "mirrored": mirror,
        "resampling": "LANCZOS",
    }


def add_vertical_shade(
    image: Image.Image,
    *,
    top_alpha: int,
    bottom_alpha: int,
    color: tuple[int, int, int],
) -> Image.Image:
    shade = Image.new("RGBA", TARGET_SIZE, (*color, 0))
    alpha = Image.new("L", (1, TARGET_SIZE[1]))
    alpha.putdata(
        [
            round(top_alpha + (bottom_alpha - top_alpha) * (y / (TARGET_SIZE[1] - 1)))
            for y in range(TARGET_SIZE[1])
        ]
    )
    alpha = alpha.resize(TARGET_SIZE, Image.Resampling.NEAREST)
    shade.putalpha(alpha)
    return Image.alpha_composite(image.convert("RGBA"), shade)


def draw_frame(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle(
        (52, 52, TARGET_SIZE[0] - 52, TARGET_SIZE[1] - 52),
        radius=32,
        outline=(40, 16, 20, 220),
        width=18,
    )
    draw.rounded_rectangle(
        (72, 72, TARGET_SIZE[0] - 72, TARGET_SIZE[1] - 72),
        radius=24,
        outline=GOLD,
        width=5,
    )
    draw.rounded_rectangle(
        (92, 92, TARGET_SIZE[0] - 92, TARGET_SIZE[1] - 92),
        radius=18,
        outline=(247, 224, 165, 145),
        width=2,
    )


def render_front(
    source: Image.Image,
    *,
    title: str,
    author: str,
) -> tuple[Image.Image, dict[str, Any]]:
    base, crop = cover_crop(source)
    base = ImageEnhance.Contrast(base).enhance(1.08)
    base = ImageEnhance.Color(base).enhance(0.82)
    image = add_vertical_shade(
        base,
        top_alpha=205,
        bottom_alpha=55,
        color=(30, 7, 13),
    )
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((136, 132, 1464, 746), radius=40, fill=BURGUNDY, outline=GOLD, width=3)
    title_box, title_font = draw_centered_block(
        draw,
        title,
        name="title",
        y=236,
        max_width=1160,
        max_lines=2,
        max_size=154,
        min_size=104,
        bold=True,
        fill=IVORY,
        line_gap=20,
    )
    author_y = max(542, title_box["box"][3] + 48)
    author_box, author_font = draw_centered_block(
        draw,
        author,
        name="author",
        y=author_y,
        max_width=1040,
        max_lines=1,
        max_size=68,
        min_size=48,
        bold=False,
        fill=(238, 205, 141, 255),
        line_gap=0,
    )
    draw_frame(draw)
    return image.convert("RGB"), {
        "crop": crop,
        "text_boxes": [title_box, author_box],
        "fonts": {
            "title": str(title_font),
            "author": str(author_font),
        },
        "treatment": {
            "source_art_only": True,
            "contrast": 1.08,
            "color": 0.82,
            "vertical_shade": {"top_alpha": 205, "bottom_alpha": 55, "color": [30, 7, 13]},
        },
    }


def render_back(
    source: Image.Image,
    *,
    title: str,
    author: str,
    description: str,
) -> tuple[Image.Image, dict[str, Any]]:
    base, crop = cover_crop(source, mirror=True)
    base = base.filter(ImageFilter.GaussianBlur(radius=1.4))
    base = ImageEnhance.Contrast(base).enhance(0.88)
    base = ImageEnhance.Color(base).enhance(0.58)
    image = add_vertical_shade(
        base,
        top_alpha=155,
        bottom_alpha=195,
        color=(29, 8, 14),
    )
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((150, 188, 1450, 2160), radius=48, fill=(38, 12, 18, 212), outline=GOLD, width=3)
    title_box, title_font = draw_centered_block(
        draw,
        title,
        name="title",
        y=318,
        max_width=1080,
        max_lines=2,
        max_size=118,
        min_size=84,
        bold=True,
        fill=IVORY,
        line_gap=18,
    )
    author_y = max(640, title_box["box"][3] + 48)
    author_box, author_font = draw_centered_block(
        draw,
        author,
        name="author",
        y=author_y,
        max_width=980,
        max_lines=1,
        max_size=58,
        min_size=44,
        bold=False,
        fill=(238, 205, 141, 255),
        line_gap=0,
    )
    description_y = max(1030, author_box["box"][3] + 150)
    description_box, description_font = draw_centered_block(
        draw,
        description,
        name="canonical_short_description",
        y=description_y,
        max_width=1040,
        max_lines=6,
        max_size=52,
        min_size=40,
        bold=False,
        fill=(244, 228, 194, 245),
        line_gap=22,
    )
    draw_frame(draw)
    return image.convert("RGB"), {
        "crop": crop,
        "text_boxes": [title_box, author_box, description_box],
        "fonts": {
            "title": str(title_font),
            "author": str(author_font),
            "description": str(description_font),
        },
        "treatment": {
            "source_art_only": True,
            "gaussian_blur_radius": 1.4,
            "contrast": 0.88,
            "color": 0.58,
            "vertical_shade": {"top_alpha": 155, "bottom_alpha": 195, "color": [29, 8, 14]},
        },
    }


def boxes_intersect(left: list[int], right: list[int]) -> bool:
    return not (
        left[2] <= right[0]
        or right[2] <= left[0]
        or left[3] <= right[1]
        or right[3] <= left[1]
    )


def validate_geometry(side: str, boxes: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for item in boxes:
        x0, y0, x1, y1 = item["box"]
        if not (
            SAFE_MARGIN <= x0 < x1 <= TARGET_SIZE[0] - SAFE_MARGIN
            and SAFE_MARGIN <= y0 < y1 <= TARGET_SIZE[1] - SAFE_MARGIN
        ):
            errors.append(f"{side}:{item['name']} escapes safe margins")
    for index, left in enumerate(boxes):
        for right in boxes[index + 1 :]:
            if boxes_intersect(left["box"], right["box"]):
                errors.append(f"{side}:{left['name']} overlaps {right['name']}")
    return errors


def save_jpeg(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        path,
        "JPEG",
        quality=91,
        optimize=True,
        progressive=False,
        subsampling=0,
        dpi=(300, 300),
    )


def validate_cover_file(path: Path) -> dict[str, Any]:
    from backend.config.book_cover import validate_book_cover

    body = path.read_bytes()
    return validate_book_cover(body, "image/jpeg", 4 * 1024 * 1024)


def package_relative_or_root(path: Path, package_dir: Path) -> str:
    try:
        return str(path.relative_to(package_dir))
    except ValueError:
        return manifest_path_relative(path)


def prepare_package(
    package_dir: Path,
    source_art: Path,
    rights_evidence_path: Path,
    *,
    generated_at: str,
) -> dict[str, Any]:
    catalog, catalog_hashes_before = load_catalog_truth()
    rights = read_json(rights_evidence_path)
    if rights.get("status") != "VERIFIED_PUBLIC_DOMAIN_SOURCE_ART":
        raise CoverCandidateError("source rights status is not verified public domain")
    if rights.get("review", {}).get("canonical_promotion_authorized") is not False:
        raise CoverCandidateError("source evidence must prohibit automatic canonical promotion")
    if sha256_file(source_art) != SOURCE_SHA256:
        raise CoverCandidateError("source-art SHA-256 does not match the verified file")
    if rights.get("source", {}).get("sha256") != SOURCE_SHA256:
        raise CoverCandidateError("rights evidence does not bind the verified source-art hash")

    with Image.open(source_art) as source:
        source.load()
        if list(source.size) != [
            int(rights["source"]["width"]),
            int(rights["source"]["height"]),
        ]:
            raise CoverCandidateError("source-art dimensions do not match rights evidence")
        front, front_recipe = render_front(
            source,
            title=catalog["title"],
            author=catalog["author"],
        )
        back, back_recipe = render_back(
            source,
            title=catalog["title"],
            author=catalog["author"],
            description=catalog["short_description"],
        )

    front_path = package_dir / f"{SLUG}-front-editorial-candidate-v1.jpg"
    back_path = package_dir / f"{SLUG}-back-editorial-candidate-v1.jpg"
    save_jpeg(front, front_path)
    save_jpeg(back, back_path)

    geometry_errors = [
        *validate_geometry("front", front_recipe["text_boxes"]),
        *validate_geometry("back", back_recipe["text_boxes"]),
    ]
    front_validation = validate_cover_file(front_path)
    back_validation = validate_cover_file(back_path)
    if geometry_errors:
        raise CoverCandidateError("; ".join(geometry_errors))
    if [front_validation["width"], front_validation["height"]] != list(TARGET_SIZE):
        raise CoverCandidateError("front output dimensions are invalid")
    if [back_validation["width"], back_validation["height"]] != list(TARGET_SIZE):
        raise CoverCandidateError("back output dimensions are invalid")

    catalog_hashes_after = {
        str(path.relative_to(ROOT)): sha256_file(path) for path in CATALOG_PATHS
    }
    if catalog_hashes_before != catalog_hashes_after:
        raise CoverCandidateError("controlled catalog changed during private cover preparation")

    composition_recipe = {
        "schema_version": "earnalism.deterministic_cover_composition.v1",
        "slug": SLUG,
        "title": catalog["title"],
        "author": catalog["author"],
        "canonical_short_description": catalog["short_description"],
        "source_art_sha256": SOURCE_SHA256,
        "output_size": list(TARGET_SIZE),
        "generation_mode": "deterministic_pillow_composition_over_verified_public_domain_art",
        "ai_generated_imagery": False,
        "placeholder_art": False,
        "front": front_recipe,
        "back": back_recipe,
    }
    write_json(package_dir / "composition_recipe.json", composition_recipe)

    visual_validation = {
        "schema_version": "earnalism.private_cover_visual_validation.v1",
        "status": "PASS_PENDING_EDITORIAL_REVIEW",
        "generated_at": generated_at,
        "checks": {
            "source_art_hash_bound": True,
            "source_rights_verified": True,
            "exact_catalog_title": True,
            "exact_catalog_author": True,
            "exact_catalog_short_description": True,
            "front_dimensions_1600x2400": True,
            "back_dimensions_1600x2400": True,
            "front_under_admin_upload_limit": front_validation["bytes"] < 4 * 1024 * 1024,
            "back_under_admin_upload_limit": back_validation["bytes"] < 4 * 1024 * 1024,
            "text_inside_safe_margins": True,
            "text_box_overlap_count": 0,
            "public_catalog_unchanged": True,
            "audio_release_truth_unchanged": True,
        },
        "geometry_errors": geometry_errors,
        "front_validation": front_validation,
        "back_validation": back_validation,
        "manual_checks_required": [
            "Owner/editorial approval of visual direction",
            "Normal-zoom legibility review",
            "Private admin candidate preview review",
        ],
    }
    write_json(package_dir / "visual_validation.json", visual_validation)

    manifest = {
        "schema_version": "earnalism.private_cover_candidate.v1",
        "status": "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED",
        "generated_at": generated_at,
        "slug": SLUG,
        "title": catalog["title"],
        "author": catalog["author"],
        "generation_mode": composition_recipe["generation_mode"],
        "source_art": {
            "path": package_relative_or_root(source_art, package_dir),
            "sha256": SOURCE_SHA256,
            "rights_evidence": package_relative_or_root(rights_evidence_path, package_dir),
            "record_url": rights["source"]["record_url"],
            "rights_mark": rights["rights"]["mark"],
        },
        "front": {
            "path": manifest_path_relative(front_path),
            "sha256": sha256_file(front_path),
            **front_validation,
        },
        "back": {
            "path": manifest_path_relative(back_path),
            "sha256": sha256_file(back_path),
            **back_validation,
        },
        "catalog_hashes": catalog_hashes_after,
        "review": {
            "admin_upload_status": "NOT_UPLOADED",
            "canonical_promotion_status": "NOT_PROMOTED",
            "owner_editorial_review_required": True,
        },
        "constraints": {
            "private_only": True,
            "public_catalog_mutated": False,
            "reader_state_mutated": False,
            "audiobook_release_state_mutated": False,
            "ai_generated_imagery": False,
            "placeholder_art": False,
        },
    }
    write_json(package_dir / "candidate_manifest.json", manifest)

    review_packet = f"""# The Tell-Tale Heart private editorial cover candidate

## Decision

This is a private, pending-review front/back candidate for **{catalog['title']}** by **{catalog['author']}**. It is not canonical, has not been exposed publicly, and cannot change reader or audiobook release truth.

## Source and rights

- Source artwork: Odilon Redon, *The Tell-Tale Heart* (1883), charcoal on brown paper.
- Rights status: Public Domain Mark 1.0, bound to `source_rights_evidence.json`.
- Exact source SHA-256: `{SOURCE_SHA256}`.
- Composition: deterministic Pillow crop, tonal treatment, borders, and catalog text overlay.
- AI-generated imagery: no.
- Placeholder art: no.

## Technical checks

- Front: 1600 × 2400 JPEG, `{manifest['front']['sha256']}`, {manifest['front']['bytes']} bytes.
- Back: 1600 × 2400 JPEG, `{manifest['back']['sha256']}`, {manifest['back']['bytes']} bytes.
- Exact canonical title/author and canonical short description used.
- Geometry validation: zero text-box overlaps; all text remains inside the 120 px safe margin.
- Both files pass the backend cover validator and remain below the 4 MiB admin limit.
- Both controlled-publication mirrors remained byte-for-byte unchanged.

## Pending review

Owner/editorial review must approve the finished pair before private admin upload. An authenticated upload must remain `ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW`; canonical promotion is a separate, hash-bound decision.

## Next exact command

```bash
python3 -m json.tool {manifest_path_relative(package_dir / 'candidate_manifest.json')} >/dev/null
```
"""
    (package_dir / "review_packet.md").write_text(review_packet, encoding="utf-8")
    return manifest


def manifest_path_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--source-art", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--rights-evidence", type=Path, default=DEFAULT_RIGHTS)
    parser.add_argument("--generated-at", default="")
    args = parser.parse_args()
    manifest = prepare_package(
        args.package_dir.resolve(),
        args.source_art.resolve(),
        args.rights_evidence.resolve(),
        generated_at=args.generated_at or utc_now(),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
