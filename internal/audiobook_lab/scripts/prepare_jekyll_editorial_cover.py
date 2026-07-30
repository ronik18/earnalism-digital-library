#!/usr/bin/env python3
"""Prepare a private, rights-bound Jekyll and Hyde editorial cover pair.

The tool composes exact controlled-catalog typography over two verified
Charles Raymond Macauley public-domain illustrations from the 1904 edition.
It writes only a private review packet. It cannot upload, canonicalize, change
reader/audio release truth, or authorize unrestricted worldwide distribution.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
COMMON_SCRIPT = Path(__file__).with_name("prepare_tell_tale_editorial_cover.py")
COMMON_SPEC = importlib.util.spec_from_file_location(
    "prepare_tell_tale_editorial_cover_common",
    COMMON_SCRIPT,
)
if not COMMON_SPEC or not COMMON_SPEC.loader:
    raise RuntimeError("could not load deterministic cover composition helpers")
COMMON = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(COMMON)

SLUG = "jekyll-and-hyde"
TARGET_SIZE = (1600, 2400)
THUMBNAIL_SIZE = (320, 480)
FEATURE_SIZE = (800, 1200)
THUMBNAIL_BUDGET_BYTES = 80 * 1024
FEATURE_BUDGET_BYTES = 180 * 1024
FRONT_SOURCE_SHA256 = "1848b89196669aeb7c0ea097d4821dc20cab09cca968d9bd854f85e68413f374"
BACK_SOURCE_SHA256 = "e48ba094dde8140e7894d6f9963b9674f395a6de98dcaf3766d1eb452e4628be"
DEFAULT_PACKAGE = (
    ROOT
    / "internal"
    / "audiobook_lab"
    / "sprint1_publication"
    / "cover_candidates"
    / SLUG
)
DEFAULT_FRONT_SOURCE = (
    DEFAULT_PACKAGE / "source_art" / "macauley-jekyll-ch2-drawing1-1904.jpg"
)
DEFAULT_BACK_SOURCE = (
    DEFAULT_PACKAGE / "source_art" / "macauley-jekyll-ch10-drawing2-1904.jpg"
)
DEFAULT_RIGHTS = DEFAULT_PACKAGE / "source_rights_evidence.json"
CATALOG_PATHS = (
    ROOT / "data" / "controlled_publications" / SLUG / "public_book.json",
    ROOT / "backend" / "data" / "controlled_publications" / SLUG / "public_book.json",
)
IVORY = (247, 236, 211, 255)
MUTED_GOLD = (202, 168, 100, 255)
DEEP_PLUM = (31, 12, 21, 232)
FRAME_GOLD = (190, 146, 76, 226)
SAFE_MARGIN = 112
MASTER_UPLOAD_LIMIT_BYTES = 4 * 1024 * 1024


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
            raise CoverCandidateError(f"unexpected canonical slug: {record.get('slug')}")
    for record in records[1:]:
        for field in ("slug", "title", "author", "short_description", "description"):
            if record.get(field) != truth.get(field):
                raise CoverCandidateError(f"controlled mirrors disagree on {field}")

    title = str(truth.get("title") or "").strip()
    author = str(truth.get("author") or "").strip()
    short_description = str(truth.get("short_description") or "").strip()
    description = str(truth.get("description") or "").strip()
    if not title or not author or not short_description:
        raise CoverCandidateError(
            "canonical title, author, and short description are required"
        )
    if description and description != short_description:
        raise CoverCandidateError(
            "an approved distinct editorial back-copy field was not found"
        )
    return truth, {
        repo_relative(path): sha256_file(path)
        for path in CATALOG_PATHS
    }


def font_evidence(fonts: dict[str, str]) -> dict[str, dict[str, str]]:
    evidence: dict[str, dict[str, str]] = {}
    for role, raw_path in fonts.items():
        path = Path(raw_path)
        evidence[role] = {
            "resolved_path": str(path),
            "sha256": sha256_file(path),
        }
    return evidence


def cover_crop(source: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    image = ImageOps.exif_transpose(source).convert("RGB")
    source_width, source_height = image.size
    target_ratio = TARGET_SIZE[0] / TARGET_SIZE[1]
    source_ratio = source_width / source_height
    if source_ratio > target_ratio:
        crop_width = round(source_height * target_ratio)
        left = (source_width - crop_width) // 2
        crop_box = (left, 0, left + crop_width, source_height)
    else:
        crop_height = round(source_width / target_ratio)
        top = (source_height - crop_height) // 2
        crop_box = (0, top, source_width, top + crop_height)
    image = image.crop(crop_box).resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    return image, {
        "source_size": [source_width, source_height],
        "crop_box": list(crop_box),
        "target_size": list(TARGET_SIZE),
        "resampling": "LANCZOS",
    }


def duotone(
    source: Image.Image,
    *,
    black: str,
    white: str,
    contrast: float,
) -> Image.Image:
    gray = ImageOps.grayscale(source)
    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    return ImageOps.colorize(gray, black=black, white=white).convert("RGBA")


def draw_frame(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle(
        (48, 48, TARGET_SIZE[0] - 48, TARGET_SIZE[1] - 48),
        radius=28,
        outline=(28, 12, 17, 230),
        width=18,
    )
    draw.rounded_rectangle(
        (70, 70, TARGET_SIZE[0] - 70, TARGET_SIZE[1] - 70),
        radius=22,
        outline=FRAME_GOLD,
        width=5,
    )
    draw.rounded_rectangle(
        (89, 89, TARGET_SIZE[0] - 89, TARGET_SIZE[1] - 89),
        radius=16,
        outline=(244, 227, 188, 125),
        width=2,
    )


def render_front(
    source: Image.Image,
    *,
    title: str,
    author: str,
) -> tuple[Image.Image, dict[str, Any]]:
    base, crop = cover_crop(source)
    image = duotone(
        base,
        black="#110d12",
        white="#d8c9aa",
        contrast=1.16,
    )
    image = COMMON.add_vertical_shade(
        image.convert("RGB"),
        top_alpha=92,
        bottom_alpha=72,
        color=(20, 7, 12),
    )
    draw = ImageDraw.Draw(image, "RGBA")
    title_panel = [126, 122, 1474, 910]
    draw.rounded_rectangle(
        title_panel,
        radius=42,
        fill=DEEP_PLUM,
        outline=FRAME_GOLD,
        width=4,
    )
    title_box, title_font = COMMON.draw_centered_block(
        draw,
        title,
        name="title",
        y=212,
        max_width=1130,
        max_lines=3,
        max_size=126,
        min_size=82,
        bold=True,
        fill=IVORY,
        line_gap=13,
    )
    author_y = max(714, title_box["box"][3] + 48)
    author_box, author_font = COMMON.draw_centered_block(
        draw,
        author,
        name="author",
        y=author_y,
        max_width=1040,
        max_lines=1,
        max_size=58,
        min_size=44,
        bold=False,
        fill=MUTED_GOLD,
        line_gap=0,
    )
    draw_frame(draw)
    return image.convert("RGB"), {
        "crop": crop,
        "content_panel": title_panel,
        "text_panels": {
            "title": title_panel,
            "author": title_panel,
        },
        "text_boxes": [title_box, author_box],
        "fonts": {
            "title": str(title_font),
            "author": str(author_font),
        },
        "treatment": {
            "source_art_only": True,
            "duotone_black": "#110d12",
            "duotone_white": "#d8c9aa",
            "contrast": 1.16,
            "vertical_shade": {
                "top_alpha": 92,
                "bottom_alpha": 72,
                "color": [20, 7, 12],
            },
        },
    }


def render_back(
    source: Image.Image,
    *,
    title: str,
    author: str,
    description: str,
) -> tuple[Image.Image, dict[str, Any]]:
    base, crop = cover_crop(source)
    base = base.filter(ImageFilter.GaussianBlur(radius=0.65))
    base = ImageEnhance.Contrast(base).enhance(0.94)
    image = duotone(
        base,
        black="#0f1110",
        white="#b9ad8c",
        contrast=1.0,
    )
    image = COMMON.add_vertical_shade(
        image.convert("RGB"),
        top_alpha=115,
        bottom_alpha=155,
        color=(18, 8, 13),
    )
    draw = ImageDraw.Draw(image, "RGBA")
    title_panel = [132, 146, 1468, 920]
    draw.rounded_rectangle(
        title_panel,
        radius=48,
        fill=(31, 12, 21, 220),
        outline=FRAME_GOLD,
        width=4,
    )
    description_panel = [132, 1590, 1468, 2228]
    draw.rounded_rectangle(
        description_panel,
        radius=48,
        fill=(31, 12, 21, 220),
        outline=FRAME_GOLD,
        width=4,
    )
    title_box, title_font = COMMON.draw_centered_block(
        draw,
        title,
        name="title",
        y=276,
        max_width=1080,
        max_lines=3,
        max_size=104,
        min_size=70,
        bold=True,
        fill=IVORY,
        line_gap=13,
    )
    author_y = max(780, title_box["box"][3] + 48)
    author_box, author_font = COMMON.draw_centered_block(
        draw,
        author,
        name="author",
        y=author_y,
        max_width=990,
        max_lines=1,
        max_size=54,
        min_size=42,
        bold=False,
        fill=MUTED_GOLD,
        line_gap=0,
    )
    description_y = 1720
    description_box, description_font = COMMON.draw_centered_block(
        draw,
        description,
        name="canonical_short_description",
        y=description_y,
        max_width=1040,
        max_lines=6,
        max_size=50,
        min_size=38,
        bold=False,
        fill=(243, 229, 201, 248),
        line_gap=24,
    )
    draw_frame(draw)
    return image.convert("RGB"), {
        "crop": crop,
        "content_panels": {
            "title_and_author": title_panel,
            "description": description_panel,
        },
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
            "source_art_only": True,
            "gaussian_blur_radius": 0.65,
            "pre_duotone_contrast": 0.94,
            "duotone_black": "#0f1110",
            "duotone_white": "#b9ad8c",
            "vertical_shade": {
                "top_alpha": 115,
                "bottom_alpha": 155,
                "color": [18, 8, 13],
            },
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


def srgb_luminance(rgb: tuple[int, int, int]) -> float:
    values = []
    for channel in rgb:
        value = channel / 255
        values.append(
            value / 12.92
            if value <= 0.04045
            else ((value + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast_ratio(foreground: tuple[int, int, int], background: tuple[int, int, int]) -> float:
    lighter = max(srgb_luminance(foreground), srgb_luminance(background))
    darker = min(srgb_luminance(foreground), srgb_luminance(background))
    return round((lighter + 0.05) / (darker + 0.05), 3)


def small_card_metrics(recipe: dict[str, Any]) -> dict[str, Any]:
    scale = THUMBNAIL_SIZE[0] / TARGET_SIZE[0]
    text_metrics = {
        item["name"]: {
            "source_font_px": item["font_size"],
            "thumbnail_font_px": round(item["font_size"] * scale, 2),
            "line_count": len(item["lines"]),
        }
        for item in recipe["text_boxes"]
    }
    title_px = text_metrics["title"]["thumbnail_font_px"]
    author_px = text_metrics["author"]["thumbnail_font_px"]
    return {
        "thumbnail_scale": scale,
        "text": text_metrics,
        "title_minimum_16px_pass": title_px >= 16,
        "author_minimum_9px_pass": author_px >= 9,
        "ivory_on_panel_contrast_ratio": contrast_ratio(
            IVORY[:3],
            DEEP_PLUM[:3],
        ),
        "wcag_large_text_contrast_pass": contrast_ratio(
            IVORY[:3],
            DEEP_PLUM[:3],
        )
        >= 3,
    }


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
        resized.save(
            buffer,
            "WEBP",
            quality=quality,
            method=6,
            lossless=False,
        )
        candidate = buffer.getvalue()
        if len(candidate) <= budget_bytes:
            selected = candidate
            selected_quality = quality
            break
    if selected is None:
        raise CoverCandidateError(
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


def validate_source(
    source_path: Path,
    evidence: dict[str, Any],
    *,
    expected_sha256: str,
) -> None:
    if evidence.get("sha256") != expected_sha256:
        raise CoverCandidateError("rights evidence has an unexpected source SHA-256")
    if sha256_file(source_path) != expected_sha256:
        raise CoverCandidateError("source-art SHA-256 does not match verified evidence")
    if source_path.stat().st_size != int(evidence["size_bytes"]):
        raise CoverCandidateError("source-art size does not match verified evidence")
    with Image.open(source_path) as image:
        image.load()
        if list(image.size) != [int(evidence["width"]), int(evidence["height"])]:
            raise CoverCandidateError(
                "source-art dimensions do not match verified evidence"
            )
        if image.format != "JPEG":
            raise CoverCandidateError("source-art format is not JPEG")


def derivative_record(
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


def prepare_package(
    package_dir: Path,
    front_source: Path,
    back_source: Path,
    rights_evidence_path: Path,
    *,
    generated_at: str,
) -> dict[str, Any]:
    catalog, catalog_hashes_before = load_catalog_truth()
    rights = read_json(rights_evidence_path)
    if rights.get("status") != "VERIFIED_PUBLIC_DOMAIN_SOURCE_ART_FOR_PRIVATE_COMPOSITION":
        raise CoverCandidateError("source rights status is not private-composition verified")
    review = rights.get("review", {})
    if review.get("private_candidate_composition_allowed") is not True:
        raise CoverCandidateError("source evidence does not authorize private composition")
    if review.get("canonical_promotion_authorized") is not False:
        raise CoverCandidateError("source evidence must prohibit canonical promotion")
    if review.get("public_upload_authorized") is not False:
        raise CoverCandidateError("source evidence must prohibit public upload")
    if rights.get("rights", {}).get("global_unrestricted_assertion") is not False:
        raise CoverCandidateError("source evidence must retain territorial caveat")

    front_evidence = rights["sources"]["front"]
    back_evidence = rights["sources"]["back"]
    validate_source(
        front_source,
        front_evidence,
        expected_sha256=FRONT_SOURCE_SHA256,
    )
    validate_source(
        back_source,
        back_evidence,
        expected_sha256=BACK_SOURCE_SHA256,
    )

    with Image.open(front_source) as source:
        source.load()
        front, front_recipe = render_front(
            source,
            title=catalog["title"],
            author=catalog["author"],
        )
    with Image.open(back_source) as source:
        source.load()
        back, back_recipe = render_back(
            source,
            title=catalog["title"],
            author=catalog["author"],
            description=catalog["short_description"],
        )

    front_path = package_dir / f"{SLUG}-front-editorial-candidate-v2.jpg"
    back_path = package_dir / f"{SLUG}-back-editorial-candidate-v2.jpg"
    save_master_jpeg(front, front_path)
    save_master_jpeg(back, back_path)

    derivative_dir = package_dir / "derivatives"
    derivative_specs = {
        "front_thumbnail": (
            front,
            derivative_dir / f"{SLUG}-front-thumbnail-v2.webp",
            THUMBNAIL_SIZE,
            THUMBNAIL_BUDGET_BYTES,
        ),
        "front_feature": (
            front,
            derivative_dir / f"{SLUG}-front-feature-v2.webp",
            FEATURE_SIZE,
            FEATURE_BUDGET_BYTES,
        ),
        "back_thumbnail": (
            back,
            derivative_dir / f"{SLUG}-back-thumbnail-v2.webp",
            THUMBNAIL_SIZE,
            THUMBNAIL_BUDGET_BYTES,
        ),
        "back_feature": (
            back,
            derivative_dir / f"{SLUG}-back-feature-v2.webp",
            FEATURE_SIZE,
            FEATURE_BUDGET_BYTES,
        ),
    }
    derivative_encodings: dict[str, dict[str, Any]] = {}
    for name, (image, path, size, budget) in derivative_specs.items():
        derivative_encodings[name] = save_webp_with_budget(
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
        raise CoverCandidateError("; ".join(geometry_errors))

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
    if [front_validation["width"], front_validation["height"]] != list(TARGET_SIZE):
        raise CoverCandidateError("front output dimensions are invalid")
    if [back_validation["width"], back_validation["height"]] != list(TARGET_SIZE):
        raise CoverCandidateError("back output dimensions are invalid")

    derivative_validations: dict[str, dict[str, Any]] = {}
    for name, (_, path, size, budget) in derivative_specs.items():
        validation = validate_cover_file(
            path,
            content_type="image/webp",
            max_bytes=budget,
        )
        if [validation["width"], validation["height"]] != list(size):
            raise CoverCandidateError(f"{name} output dimensions are invalid")
        derivative_validations[name] = derivative_record(
            path,
            package_dir=package_dir,
            validation=validation,
            encoding=derivative_encodings[name],
        )

    front_card = small_card_metrics(front_recipe)
    back_card = small_card_metrics(back_recipe)
    for side, metrics in (("front", front_card), ("back", back_card)):
        if not metrics["title_minimum_16px_pass"]:
            raise CoverCandidateError(f"{side} title is too small at thumbnail size")
        if not metrics["author_minimum_9px_pass"]:
            raise CoverCandidateError(f"{side} author is too small at thumbnail size")
        if not metrics["wcag_large_text_contrast_pass"]:
            raise CoverCandidateError(f"{side} text contrast is insufficient")

    catalog_hashes_after = {
        repo_relative(path): sha256_file(path)
        for path in CATALOG_PATHS
    }
    if catalog_hashes_before != catalog_hashes_after:
        raise CoverCandidateError("controlled catalog changed during private preparation")

    all_fonts = {
        "front_title": front_recipe["fonts"]["title"],
        "front_author": front_recipe["fonts"]["author"],
        "back_title": back_recipe["fonts"]["title"],
        "back_author": back_recipe["fonts"]["author"],
        "back_description": back_recipe["fonts"]["description"],
    }
    composition_recipe = {
        "schema_version": "earnalism.deterministic_cover_composition.v2",
        "slug": SLUG,
        "title": catalog["title"],
        "author": catalog["author"],
        "canonical_back_copy": catalog["short_description"],
        "approved_distinct_editorial_back_copy_found": False,
        "source_art_sha256": {
            "front": FRONT_SOURCE_SHA256,
            "back": BACK_SOURCE_SHA256,
        },
        "output_size": list(TARGET_SIZE),
        "generation_mode": "deterministic_pillow_composition_over_verified_public_domain_art",
        "ai_generated_imagery": False,
        "placeholder_art": False,
        "script": {
            "path": repo_relative(Path(__file__)),
            "sha256": sha256_file(Path(__file__)),
            "shared_helper_path": repo_relative(COMMON_SCRIPT),
            "shared_helper_sha256": sha256_file(COMMON_SCRIPT),
        },
        "fonts": font_evidence(all_fonts),
        "front": front_recipe,
        "back": back_recipe,
        "derivatives": {
            "thumbnail": {
                "size": list(THUMBNAIL_SIZE),
                "budget_bytes": THUMBNAIL_BUDGET_BYTES,
            },
            "feature": {
                "size": list(FEATURE_SIZE),
                "budget_bytes": FEATURE_BUDGET_BYTES,
            },
            "resampling": "LANCZOS",
            "format": "WEBP",
        },
    }
    write_json(package_dir / "composition_recipe.json", composition_recipe)

    rights_hash = sha256_file(rights_evidence_path)
    manifest = {
        "schema_version": "earnalism.private_cover_candidate.v2",
        "status": "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED",
        "generated_at": generated_at,
        "slug": SLUG,
        "title": catalog["title"],
        "author": catalog["author"],
        "canonical_back_copy": catalog["short_description"],
        "generation_mode": composition_recipe["generation_mode"],
        "source_art": {
            "front": {
                "path": package_relative(front_source, package_dir),
                "sha256": FRONT_SOURCE_SHA256,
                "record_url": front_evidence["record_url"],
                "rights_mark": rights["rights"]["mark"],
            },
            "back": {
                "path": package_relative(back_source, package_dir),
                "sha256": BACK_SOURCE_SHA256,
                "record_url": back_evidence["record_url"],
                "rights_mark": rights["rights"]["mark"],
            },
            "rights_evidence": package_relative(rights_evidence_path, package_dir),
            "rights_evidence_sha256": rights_hash,
            "global_unrestricted_assertion": False,
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
        "superseded_private_ai_assets": {
            "status": "SUPERSEDED_PRIVATE_AI_ART_NOT_AUTHORIZED_FOR_CANONICAL_USE",
            "front": {
                "path": f"{SLUG}-front-art-v1.png",
                "sha256": "ba3dca9fba29a741d74b0ac94e8b9db97fcaf52a09776b208361044346d4dfba",
            },
            "back": {
                "path": f"{SLUG}-back-art-v1.png",
                "sha256": "92326eb8eba9678adf6af8a06cc820a4ef9500ef68e3dec3b8783cf1af7dbace",
            },
        },
        "review": {
            "manual_visual_review_status": "PENDING",
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

    visual_validation = {
        "schema_version": "earnalism.private_cover_visual_validation.v2",
        "status": "AUTOMATED_PASS_MANUAL_EDITORIAL_REVIEW_PENDING",
        "generated_at": generated_at,
        "checks": {
            "source_art_hashes_bound": True,
            "source_rights_verified_for_private_composition": True,
            "territorial_rights_caveat_retained": True,
            "exact_catalog_title": True,
            "exact_catalog_author": True,
            "exact_canonical_back_copy": True,
            "distinct_editorial_back_copy_invented": False,
            "front_dimensions_1600x2400": True,
            "back_dimensions_1600x2400": True,
            "front_under_admin_upload_limit": True,
            "back_under_admin_upload_limit": True,
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
            "small_card_title_legibility_floor": (
                front_card["title_minimum_16px_pass"]
                and back_card["title_minimum_16px_pass"]
            ),
            "small_card_author_legibility_floor": (
                front_card["author_minimum_9px_pass"]
                and back_card["author_minimum_9px_pass"]
            ),
            "public_catalog_unchanged": True,
            "audio_release_truth_unchanged": True,
        },
        "geometry_errors": geometry_errors,
        "front_validation": front_validation,
        "back_validation": back_validation,
        "derivative_validations": derivative_validations,
        "small_card_metrics": {
            "front": front_card,
            "back": back_card,
        },
        "manual_checks_required": [
            "Visual inspection of front and back master outputs",
            "Visual inspection of front and back thumbnail outputs",
            "Owner/editorial approval of visual direction and canonical copy treatment",
            "Territorial rights review before any canonical promotion",
            "Private admin candidate preview review before any public decision",
        ],
    }
    write_json(package_dir / "visual_validation.json", visual_validation)

    review_packet = f"""# Jekyll and Hyde private editorial cover candidate

## Decision

This is a private, pending-review front/back candidate for **{catalog['title']}** by **{catalog['author']}**. It is not canonical, has not been uploaded, and cannot change reader or audiobook release truth.

## Source and rights

- Front source: Charles Raymond Macauley, Chapter 2 Drawing 1, Scott-Thaw 1904 edition.
- Back source: Charles Raymond Macauley, Chapter 10 Drawing 2, Scott-Thaw 1904 edition.
- Rights evidence: Public Domain Mark 1.0 source records, exact URLs and hashes in `source_rights_evidence.json`.
- Front source SHA-256: `{FRONT_SOURCE_SHA256}`.
- Back source SHA-256: `{BACK_SOURCE_SHA256}`.
- The Commons longer-term-jurisdiction caveat is retained. This packet does not claim unrestricted worldwide rights.
- Composition: deterministic Pillow crop, duotone treatment, borders, panels, and controlled-catalog text overlay.
- AI-generated imagery: no.
- Placeholder art: no.

## Exact catalog copy

- Title: `{catalog['title']}`
- Author: `{catalog['author']}`
- Back copy: `{catalog['short_description']}`

No distinct approved editorial back-copy field exists, so no new marketing copy was invented.

## Technical checks

- Front master: 1600 × 2400 JPEG, `{manifest['front']['sha256']}`, {manifest['front']['bytes']} bytes.
- Back master: 1600 × 2400 JPEG, `{manifest['back']['sha256']}`, {manifest['back']['bytes']} bytes.
- Thumbnail derivatives: 320 × 480 WebP, each at or below 80 KiB.
- Feature derivatives: 800 × 1200 WebP, each at or below 180 KiB.
- Geometry validation: zero text-box overlaps; every text box remains inside both the safe margin and its content panel.
- Small-card type floors and deterministic foreground/panel contrast checks pass.
- Both controlled-publication mirrors remained byte-for-byte unchanged.

## Pending review

Automated preparation does not approve this cover. Visual inspection and owner/editorial review remain mandatory. Any later private admin upload must remain `ADMIN_UPLOADED_PENDING_CANONICAL_REVIEW`; canonical promotion requires a separate hash-bound decision and territorial-rights confirmation.

## Next exact command

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q internal/audiobook_lab/scripts/test_prepare_jekyll_editorial_cover.py
```
"""
    (package_dir / "review_packet.md").write_text(
        review_packet,
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--front-source", type=Path, default=DEFAULT_FRONT_SOURCE)
    parser.add_argument("--back-source", type=Path, default=DEFAULT_BACK_SOURCE)
    parser.add_argument("--rights-evidence", type=Path, default=DEFAULT_RIGHTS)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args()
    manifest = prepare_package(
        args.package_dir.resolve(),
        args.front_source.resolve(),
        args.back_source.resolve(),
        args.rights_evidence.resolve(),
        generated_at=args.generated_at,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
