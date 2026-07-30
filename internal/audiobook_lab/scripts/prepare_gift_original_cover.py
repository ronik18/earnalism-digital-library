#!/usr/bin/env python3
"""Prepare an original, deterministic Gift of the Magi cover pair.

The artwork is composed entirely from programmatic shapes and exact controlled
catalog copy. It uses no third-party illustration, generated-image model,
placeholder art, or reader-facing engineering language. The command writes a
private review packet only; authenticated upload and checksum-bound canonical
promotion remain separate operations.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
COMMON_SCRIPT = Path(__file__).with_name("prepare_tell_tale_editorial_cover.py")
COMMON_SPEC = importlib.util.spec_from_file_location(
    "prepare_gift_original_cover_common",
    COMMON_SCRIPT,
)
if not COMMON_SPEC or not COMMON_SPEC.loader:
    raise RuntimeError("could not load deterministic cover helpers")
COMMON = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(COMMON)

SLUG = "the-gift-of-the-magi"
TARGET_SIZE = (1600, 2400)
THUMBNAIL_SIZE = (320, 480)
FEATURE_SIZE = (800, 1200)
THUMBNAIL_BUDGET_BYTES = 80 * 1024
FEATURE_BUDGET_BYTES = 180 * 1024
MASTER_UPLOAD_LIMIT_BYTES = 4 * 1024 * 1024
SAFE_MARGIN = 112
DEFAULT_PACKAGE = (
    ROOT
    / "internal"
    / "audiobook_lab"
    / "sprint1_publication"
    / "cover_candidates"
    / SLUG
    / "original_v1"
)
CATALOG_PATHS = (
    ROOT / "data" / "controlled_publications" / SLUG / "public_book.json",
    ROOT / "backend" / "data" / "controlled_publications" / SLUG / "public_book.json",
)

IVORY = (250, 239, 214, 255)
SOFT_IVORY = (238, 221, 183, 255)
GOLD = (215, 174, 91, 255)
PALE_GOLD = (240, 210, 145, 255)
OXBLOOD = (73, 16, 29, 255)
DEEP_PINE = (7, 34, 31, 255)
NIGHT = (12, 9, 16, 255)
PANEL = (27, 10, 18, 238)


class GiftCoverError(RuntimeError):
    """Raised when the original cover cannot be prepared safely."""


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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def save_master_jpeg(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        path,
        "JPEG",
        quality=89,
        optimize=True,
        progressive=True,
        subsampling=1,
        dpi=(300, 300),
    )


def save_webp_with_budget(
    image: Image.Image,
    path: Path,
    *,
    size: tuple[int, int],
    budget_bytes: int,
) -> dict[str, Any]:
    resized = image.resize(size, Image.Resampling.LANCZOS)
    selected: bytes | None = None
    selected_quality = 0
    for quality in range(84, 39, -2):
        buffer = BytesIO()
        resized.save(buffer, "WEBP", quality=quality, method=6, lossless=False)
        candidate = buffer.getvalue()
        if len(candidate) <= budget_bytes:
            selected = candidate
            selected_quality = quality
            break
    if selected is None:
        raise GiftCoverError(
            f"{path.name} cannot meet the {budget_bytes}-byte performance budget"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(selected)
    return {
        "quality": selected_quality,
        "budget_bytes": budget_bytes,
        "budget_pass": len(selected) <= budget_bytes,
    }


def validate_cover_file(
    path: Path,
    *,
    content_type: str,
    max_bytes: int,
) -> dict[str, Any]:
    from backend.config.book_cover import validate_book_cover

    return validate_book_cover(path.read_bytes(), content_type, max_bytes)


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def package_relative(path: Path, package_dir: Path) -> str:
    try:
        return str(path.relative_to(package_dir))
    except ValueError:
        return repo_relative(path)


def load_catalog_truth() -> tuple[dict[str, Any], dict[str, str]]:
    records = [read_json(path) for path in CATALOG_PATHS]
    truth = records[0]
    for record in records:
        if record.get("slug") != SLUG:
            raise GiftCoverError(f"unexpected canonical slug: {record.get('slug')}")
    for record in records[1:]:
        for field in ("slug", "title", "author", "short_description"):
            if record.get(field) != truth.get(field):
                raise GiftCoverError(f"controlled mirrors disagree on {field}")

    title = str(truth.get("title") or "").strip()
    author = str(truth.get("author") or "").strip()
    description = str(truth.get("short_description") or "").strip()
    if title != "The Gift of the Magi" or author != "O. Henry":
        raise GiftCoverError("canonical title or author does not match the expected work")
    if not description:
        raise GiftCoverError("canonical short description is required")
    prohibited = (
        "release",
        "gate",
        "controlled",
        "qa_passed",
        "approved",
        "internal",
    )
    normalized = description.lower()
    if any(term in normalized for term in prohibited):
        raise GiftCoverError("canonical short description contains internal language")
    return truth, {
        repo_relative(path): sha256_file(path)
        for path in CATALOG_PATHS
    }


def _blend(left: int, right: int, amount: float) -> int:
    return round(left + (right - left) * amount)


def vertical_gradient(
    top: tuple[int, int, int],
    middle: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    strip = Image.new("RGB", (1, TARGET_SIZE[1]), top)
    pixels = strip.load()
    for y in range(TARGET_SIZE[1]):
        position = y / (TARGET_SIZE[1] - 1)
        if position <= 0.52:
            amount = position / 0.52
            source, target = top, middle
        else:
            amount = (position - 0.52) / 0.48
            source, target = middle, bottom
        pixels[0, y] = tuple(
            _blend(source[index], target[index], amount)
            for index in range(3)
        )
    return strip.resize(TARGET_SIZE)


def draw_frame(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle(
        (48, 48, TARGET_SIZE[0] - 48, TARGET_SIZE[1] - 48),
        radius=30,
        outline=(9, 5, 9, 245),
        width=18,
    )
    draw.rounded_rectangle(
        (70, 70, TARGET_SIZE[0] - 70, TARGET_SIZE[1] - 70),
        radius=24,
        outline=(198, 150, 70, 238),
        width=6,
    )
    draw.rounded_rectangle(
        (92, 92, TARGET_SIZE[0] - 92, TARGET_SIZE[1] - 92),
        radius=18,
        outline=(246, 224, 177, 135),
        width=2,
    )
    for box, start, end in (
        ((58, 58, 290, 290), 180, 270),
        ((1310, 58, 1542, 290), 270, 360),
        ((58, 2110, 290, 2342), 90, 180),
        ((1310, 2110, 1542, 2342), 0, 90),
    ):
        draw.arc(box, start, end, fill=(232, 196, 125, 150), width=4)


def draw_star_field(draw: ImageDraw.ImageDraw, *, top: int, bottom: int) -> None:
    for index in range(78):
        x = 126 + ((index * 137) % 1348)
        y = top + ((index * 223) % max(1, bottom - top))
        radius = 2 + (index % 4)
        alpha = 38 + (index % 5) * 15
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(245, 220, 158, alpha),
        )


def draw_ribbon(draw: ImageDraw.ImageDraw, *, center_y: int) -> None:
    left_points: list[tuple[int, int]] = []
    right_points: list[tuple[int, int]] = []
    for step in range(91):
        amount = step / 90
        x = 250 + round(amount * 1100)
        wave = math.sin(amount * math.pi * 2)
        left_points.append((x, center_y + round(wave * 205)))
        right_points.append((x, center_y - round(wave * 205)))
    draw.line(left_points, fill=(225, 177, 88, 105), width=48, joint="curve")
    draw.line(left_points, fill=(247, 215, 147, 205), width=8, joint="curve")
    draw.line(right_points, fill=(128, 21, 38, 180), width=52, joint="curve")
    draw.line(right_points, fill=(242, 198, 121, 128), width=5, joint="curve")
    draw.ellipse(
        (758, center_y - 42, 842, center_y + 42),
        fill=(22, 10, 14, 245),
        outline=GOLD,
        width=5,
    )


def draw_watch(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[int, int],
    radius: int,
) -> None:
    cx, cy = center
    for inset, width, color in (
        (0, 14, (235, 201, 125, 235)),
        (26, 5, (128, 83, 31, 255)),
        (48, 3, (238, 216, 167, 180)),
    ):
        draw.ellipse(
            (cx - radius + inset, cy - radius + inset, cx + radius - inset, cy + radius - inset),
            fill=(20, 29, 27, 232) if inset == 48 else None,
            outline=color,
            width=width,
        )
    draw.rounded_rectangle(
        (cx - 48, cy - radius - 78, cx + 48, cy - radius + 30),
        radius=30,
        outline=(233, 197, 119, 235),
        width=10,
    )
    for hour in range(12):
        angle = math.radians(hour * 30 - 90)
        outer_x = cx + math.cos(angle) * (radius - 67)
        outer_y = cy + math.sin(angle) * (radius - 67)
        inner_x = cx + math.cos(angle) * (radius - (92 if hour % 3 else 112))
        inner_y = cy + math.sin(angle) * (radius - (92 if hour % 3 else 112))
        draw.line(
            (inner_x, inner_y, outer_x, outer_y),
            fill=(235, 205, 138, 220),
            width=7 if hour % 3 else 11,
        )
    draw.line((cx, cy, cx - radius * 0.24, cy - radius * 0.36), fill=PALE_GOLD, width=14)
    draw.line((cx, cy, cx + radius * 0.37, cy - radius * 0.12), fill=PALE_GOLD, width=10)
    draw.ellipse((cx - 17, cy - 17, cx + 17, cy + 17), fill=GOLD)

    chain_points = []
    for step in range(55):
        angle = math.radians(210 + step * 4.2)
        chain_points.append(
            (
                cx + math.cos(angle) * (radius + 100 + step * 4),
                cy + math.sin(angle) * (radius + 100 + step * 2),
            )
        )
    draw.line(chain_points, fill=(222, 180, 91, 190), width=14, joint="curve")
    for x, y in chain_points[::5]:
        draw.ellipse((x - 13, y - 8, x + 13, y + 8), outline=PALE_GOLD, width=3)


def draw_comb(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[int, int],
    width: int,
    height: int,
    rotation_hint: int,
) -> None:
    cx, cy = center
    left = cx - width // 2
    right = cx + width // 2
    top = cy - height // 2
    bottom = cy + height // 2
    draw.rounded_rectangle(
        (left, top, right, top + 104),
        radius=48,
        fill=(105, 18, 36, 230),
        outline=(231, 190, 105, 240),
        width=8,
    )
    for index in range(9):
        x = left + 48 + index * ((width - 96) / 8)
        draw.ellipse((x - 14, top + 30, x + 14, top + 58), fill=PALE_GOLD)
    tooth_count = 17
    for index in range(tooth_count):
        x = left + 24 + index * ((width - 48) / (tooth_count - 1))
        offset = abs(index - (tooth_count - 1) / 2) * 7
        draw.line(
            (x, top + 93, x + rotation_hint, bottom - offset),
            fill=(225, 190, 117, 235),
            width=7,
        )


def draw_gift_symbolism(draw: ImageDraw.ImageDraw, *, compact: bool) -> None:
    if compact:
        draw_ribbon(draw, center_y=1260)
        draw_watch(draw, center=(590, 1190), radius=245)
        draw_comb(draw, center=(1035, 1170), width=430, height=420, rotation_hint=12)
        return
    draw_ribbon(draw, center_y=1645)
    draw_watch(draw, center=(570, 1570), radius=300)
    draw_comb(draw, center=(1050, 1510), width=500, height=540, rotation_hint=14)
    draw_comb(draw, center=(1040, 1760), width=455, height=430, rotation_hint=-8)


def render_front(title: str, author: str) -> tuple[Image.Image, dict[str, Any]]:
    image = vertical_gradient((5, 28, 26), (70, 13, 27), (13, 8, 17)).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    draw_star_field(draw, top=760, bottom=2260)

    title_panel = [126, 126, 1474, 820]
    draw.rounded_rectangle(title_panel, radius=46, fill=PANEL, outline=GOLD, width=4)
    title_box, title_font = COMMON.draw_centered_block(
        draw,
        title,
        name="title",
        y=215,
        max_width=1120,
        max_lines=3,
        max_size=142,
        min_size=92,
        bold=True,
        fill=IVORY,
        line_gap=14,
    )
    author_y = max(670, title_box["box"][3] + 54)
    author_box, author_font = COMMON.draw_centered_block(
        draw,
        author,
        name="author",
        y=author_y,
        max_width=1000,
        max_lines=1,
        max_size=60,
        min_size=46,
        bold=False,
        fill=GOLD,
        line_gap=0,
    )

    draw.rounded_rectangle(
        (152, 900, 1448, 2225),
        radius=620,
        fill=(6, 26, 25, 186),
        outline=(211, 166, 78, 158),
        width=5,
    )
    for inset in range(0, 190, 38):
        draw.arc(
            (170 + inset, 915 + inset, 1430 - inset, 2210 - inset),
            205,
            336,
            fill=(240, 207, 141, 55),
            width=3,
        )
    draw_gift_symbolism(draw, compact=False)
    draw_frame(draw)
    return image.convert("RGB"), {
        "text_panels": {"title": title_panel, "author": title_panel},
        "text_boxes": [title_box, author_box],
        "fonts": {"title": str(title_font), "author": str(author_font)},
        "treatment": {
            "original_programmatic_art": True,
            "external_image_assets": [],
            "generated_image_model": None,
            "symbolism": [
                "gold pocket watch and chain",
                "jeweled hair combs",
                "interwoven gift ribbons",
            ],
        },
    }


def render_back(
    title: str,
    author: str,
    description: str,
) -> tuple[Image.Image, dict[str, Any]]:
    image = vertical_gradient((61, 12, 25), (6, 36, 32), (11, 8, 15)).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    draw_star_field(draw, top=810, bottom=1500)

    title_panel = [126, 126, 1474, 830]
    draw.rounded_rectangle(title_panel, radius=46, fill=PANEL, outline=GOLD, width=4)
    title_box, title_font = COMMON.draw_centered_block(
        draw,
        title,
        name="title",
        y=230,
        max_width=1080,
        max_lines=3,
        max_size=108,
        min_size=76,
        bold=True,
        fill=IVORY,
        line_gap=13,
    )
    author_y = max(690, title_box["box"][3] + 48)
    author_box, author_font = COMMON.draw_centered_block(
        draw,
        author,
        name="author",
        y=author_y,
        max_width=980,
        max_lines=1,
        max_size=54,
        min_size=42,
        bold=False,
        fill=GOLD,
        line_gap=0,
    )

    draw.rounded_rectangle(
        (205, 885, 1395, 1545),
        radius=320,
        fill=(8, 29, 27, 185),
        outline=(211, 166, 78, 150),
        width=4,
    )
    draw_gift_symbolism(draw, compact=True)

    description_panel = [132, 1630, 1468, 2248]
    draw.rounded_rectangle(
        description_panel,
        radius=48,
        fill=PANEL,
        outline=GOLD,
        width=4,
    )
    description_box, description_font = COMMON.draw_centered_block(
        draw,
        description,
        name="canonical_short_description",
        y=1790,
        max_width=1050,
        max_lines=5,
        max_size=52,
        min_size=40,
        bold=False,
        fill=SOFT_IVORY,
        line_gap=26,
    )
    draw_frame(draw)
    return image.convert("RGB"), {
        "text_panels": {
            "title": title_panel,
            "author": title_panel,
            "canonical_short_description": description_panel,
        },
        "text_boxes": [title_box, author_box, description_box],
        "fonts": {
            "title": str(title_font),
            "author": str(author_font),
            "description": str(description_font),
        },
        "treatment": {
            "original_programmatic_art": True,
            "external_image_assets": [],
            "generated_image_model": None,
            "reader_facing_back_copy_source": "controlled_catalog.short_description",
        },
    }


def boxes_intersect(left: list[int], right: list[int]) -> bool:
    return not (
        left[2] <= right[0]
        or right[2] <= left[0]
        or left[3] <= right[1]
        or right[3] <= left[1]
    )


def validate_geometry(side: str, recipe: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    boxes = recipe["text_boxes"]
    for item in boxes:
        x0, y0, x1, y1 = item["box"]
        if not (
            SAFE_MARGIN <= x0 < x1 <= TARGET_SIZE[0] - SAFE_MARGIN
            and SAFE_MARGIN <= y0 < y1 <= TARGET_SIZE[1] - SAFE_MARGIN
        ):
            errors.append(f"{side}:{item['name']} escapes safe margins")
        panel = recipe["text_panels"][item["name"]]
        if not (
            panel[0] <= x0 < x1 <= panel[2]
            and panel[1] <= y0 < y1 <= panel[3]
        ):
            errors.append(f"{side}:{item['name']} escapes content panel")
    for index, left in enumerate(boxes):
        for right in boxes[index + 1 :]:
            if boxes_intersect(left["box"], right["box"]):
                errors.append(f"{side}:{left['name']} overlaps {right['name']}")
    return errors


def _derivative_record(
    path: Path,
    *,
    package_dir: Path,
    validation: dict[str, Any],
    encoding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "path": package_relative(path, package_dir),
        "sha256": sha256_file(path),
        **validation,
        **encoding,
    }


def prepare_package(package_dir: Path, *, generated_at: str) -> dict[str, Any]:
    catalog, catalog_hashes_before = load_catalog_truth()
    title = catalog["title"]
    author = catalog["author"]
    description = catalog["short_description"]
    front, front_recipe = render_front(title, author)
    back, back_recipe = render_back(title, author, description)

    front_path = package_dir / f"{SLUG}-front-original-v1.jpg"
    back_path = package_dir / f"{SLUG}-back-original-v1.jpg"
    save_master_jpeg(front, front_path)
    save_master_jpeg(back, back_path)

    derivative_dir = package_dir / "derivatives"
    derivative_specs = {
        "front_thumbnail": (
            front,
            derivative_dir / f"{SLUG}-front-thumbnail-original-v1.webp",
            THUMBNAIL_SIZE,
            THUMBNAIL_BUDGET_BYTES,
        ),
        "front_feature": (
            front,
            derivative_dir / f"{SLUG}-front-feature-original-v1.webp",
            FEATURE_SIZE,
            FEATURE_BUDGET_BYTES,
        ),
        "back_thumbnail": (
            back,
            derivative_dir / f"{SLUG}-back-thumbnail-original-v1.webp",
            THUMBNAIL_SIZE,
            THUMBNAIL_BUDGET_BYTES,
        ),
        "back_feature": (
            back,
            derivative_dir / f"{SLUG}-back-feature-original-v1.webp",
            FEATURE_SIZE,
            FEATURE_BUDGET_BYTES,
        ),
    }
    encodings: dict[str, dict[str, Any]] = {}
    for name, (image, path, size, budget) in derivative_specs.items():
        encodings[name] = save_webp_with_budget(
            image,
            path,
            size=size,
            budget_bytes=budget,
        )

    geometry_errors = [
        *validate_geometry("front", front_recipe),
        *validate_geometry("back", back_recipe),
    ]
    if geometry_errors:
        raise GiftCoverError("; ".join(geometry_errors))

    front_validation = validate_cover_file(
        front_path,
        content_type="image/jpeg",
        max_bytes=MASTER_UPLOAD_LIMIT_BYTES,
    )
    back_validation = validate_cover_file(
        back_path,
        content_type="image/jpeg",
        max_bytes=MASTER_UPLOAD_LIMIT_BYTES,
    )
    derivative_validations: dict[str, dict[str, Any]] = {}
    for name, (_, path, size, budget) in derivative_specs.items():
        validation = validate_cover_file(
            path,
            content_type="image/webp",
            max_bytes=budget,
        )
        if [validation["width"], validation["height"]] != list(size):
            raise GiftCoverError(f"{name} output dimensions are invalid")
        derivative_validations[name] = _derivative_record(
            path,
            package_dir=package_dir,
            validation=validation,
            encoding=encodings[name],
        )

    catalog_hashes_after = {
        repo_relative(path): sha256_file(path)
        for path in CATALOG_PATHS
    }
    if catalog_hashes_before != catalog_hashes_after:
        raise GiftCoverError("controlled catalog changed during private preparation")

    manifest = {
        "schema_version": "earnalism.private_cover_candidate.v3",
        "status": "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED",
        "generated_at": generated_at,
        "slug": SLUG,
        "title": title,
        "author": author,
        "generation_mode": "deterministic_original_programmatic_graphical_composition",
        "rights": {
            "status": "ORIGINAL_COMPOSITION_NO_THIRD_PARTY_ART",
            "external_image_assets": [],
            "generated_image_model": None,
            "territorial_restriction": None,
            "commercial_use_blocker": None,
        },
        "copy": {
            "title": title,
            "title_source": "controlled_catalog.title",
            "title_sha256": sha256_text(title),
            "author": author,
            "author_source": "controlled_catalog.author",
            "author_sha256": sha256_text(author),
            "back_description": description,
            "back_description_source": "controlled_catalog.short_description",
            "back_description_sha256": sha256_text(description),
            "reader_facing_internal_language_rendered": False,
        },
        "front": {
            "path": package_relative(front_path, package_dir),
            "sha256": sha256_file(front_path),
            **front_validation,
            "thumbnail": derivative_validations["front_thumbnail"],
            "feature": derivative_validations["front_feature"],
        },
        "back": {
            "path": package_relative(back_path, package_dir),
            "sha256": sha256_file(back_path),
            **back_validation,
            "thumbnail": derivative_validations["back_thumbnail"],
            "feature": derivative_validations["back_feature"],
        },
        "catalog_hashes": catalog_hashes_after,
        "review": {
            "manual_visual_review_status": "PENDING",
            "copy_proofread_status": "PENDING",
            "ocr_status": "PENDING",
            "owner_editorial_review_required": True,
            "admin_upload_status": "NOT_UPLOADED",
            "canonical_promotion_status": "NOT_PROMOTED",
        },
        "constraints": {
            "private_only": True,
            "public_catalog_mutated": False,
            "reader_state_mutated": False,
            "audiobook_release_state_mutated": False,
            "ai_generated_imagery": False,
            "placeholder_art": False,
            "public_upload_authorized": False,
            "canonical_promotion_authorized": False,
        },
    }
    write_json(package_dir / "candidate_manifest.json", manifest)
    write_json(
        package_dir / "composition_recipe.json",
        {
            "schema_version": "earnalism.deterministic_cover_composition.v3",
            "slug": SLUG,
            "title": title,
            "author": author,
            "back_description": description,
            "output_size": list(TARGET_SIZE),
            "generation_mode": manifest["generation_mode"],
            "external_image_assets": [],
            "generated_image_model": None,
            "front": front_recipe,
            "back": back_recipe,
            "script": {
                "path": repo_relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
                "helper_path": repo_relative(COMMON_SCRIPT),
                "helper_sha256": sha256_file(COMMON_SCRIPT),
            },
        },
    )
    write_json(
        package_dir / "visual_validation.json",
        {
            "schema_version": "earnalism.private_cover_visual_validation.v3",
            "status": "AUTOMATED_PASS_MANUAL_EDITORIAL_REVIEW_PENDING",
            "generated_at": generated_at,
            "checks": {
                "original_programmatic_art": True,
                "third_party_image_asset_count": 0,
                "generated_image_model_used": False,
                "territorial_rights_blocker": False,
                "exact_catalog_title": True,
                "exact_catalog_author": True,
                "exact_catalog_back_description": True,
                "reader_facing_internal_language_rendered": False,
                "front_dimensions_1600x2400": (
                    [front_validation["width"], front_validation["height"]]
                    == list(TARGET_SIZE)
                ),
                "back_dimensions_1600x2400": (
                    [back_validation["width"], back_validation["height"]]
                    == list(TARGET_SIZE)
                ),
                "text_inside_safe_margins": True,
                "text_inside_content_panels": True,
                "text_box_overlap_count": 0,
                "thumbnail_derivatives_under_80_kib": all(
                    derivative_validations[name]["bytes"] <= THUMBNAIL_BUDGET_BYTES
                    for name in ("front_thumbnail", "back_thumbnail")
                ),
                "feature_derivatives_under_180_kib": all(
                    derivative_validations[name]["bytes"] <= FEATURE_BUDGET_BYTES
                    for name in ("front_feature", "back_feature")
                ),
                "public_catalog_unchanged": True,
                "audio_release_truth_unchanged": True,
            },
            "geometry_errors": geometry_errors,
            "front_validation": front_validation,
            "back_validation": back_validation,
            "derivative_validations": derivative_validations,
            "copy_contract": manifest["copy"],
            "manual_checks_required": [
                "Visual inspection of both masters and thumbnails",
                "OCR and proofreading against the exact copy contract",
                "Owner/editorial approval of the exact hash-bound pair",
                "Authenticated admin upload as pending canonical review",
                "Separate exact-checksum canonical promotion",
            ],
        },
    )
    (package_dir / "review_packet.md").write_text(
        f"""# The Gift of the Magi original graphical cover candidate

This private candidate uses only deterministic programmatic shapes and exact
controlled-catalog title, author, and back-description text. It contains no
third-party illustration, generated image-model output, placeholder art, or
reader-facing engineering language.

- Front SHA-256: `{manifest['front']['sha256']}`
- Back SHA-256: `{manifest['back']['sha256']}`
- Dimensions: `1600 × 2400`
- Back copy: `{description}`
- Public upload: not yet authorized
- Canonical promotion: not yet authorized
- Reader/audio release truth: unchanged
""",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args()
    manifest = prepare_package(
        args.package_dir.resolve(),
        generated_at=args.generated_at,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
