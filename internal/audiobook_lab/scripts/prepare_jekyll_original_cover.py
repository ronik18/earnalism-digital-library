#!/usr/bin/env python3
"""Prepare an original, deterministic Jekyll and Hyde cover pair.

The artwork is drawn entirely from programmatic shapes and controlled-catalog
text. It uses no third-party illustration, generated image model, placeholder
art, or reader-facing engineering copy. The command writes a private review
packet only; upload and canonical promotion remain separate authenticated
operations.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
LEGACY_SCRIPT = Path(__file__).with_name("prepare_jekyll_editorial_cover.py")
LEGACY_SPEC = importlib.util.spec_from_file_location(
    "prepare_jekyll_editorial_cover_legacy",
    LEGACY_SCRIPT,
)
if not LEGACY_SPEC or not LEGACY_SPEC.loader:
    raise RuntimeError("could not load deterministic cover helpers")
LEGACY = importlib.util.module_from_spec(LEGACY_SPEC)
LEGACY_SPEC.loader.exec_module(LEGACY)

SLUG = "jekyll-and-hyde"
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
    / "original_v3"
)

IVORY = (248, 238, 214, 255)
MUTED_GOLD = (205, 166, 91, 255)
FRAME_GOLD = (190, 145, 72, 230)
INK = (10, 13, 15, 255)
OXBLOOD = (61, 16, 29, 255)
DEEP_TEAL = (11, 47, 49, 255)
PANEL = (25, 10, 17, 238)


class OriginalCoverError(RuntimeError):
    """Raised when the original cover cannot be prepared safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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


def _blend(left: int, right: int, amount: float) -> int:
    return round(left + (right - left) * amount)


def vertical_gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    strip = Image.new("RGB", (1, TARGET_SIZE[1]), top)
    pixels = strip.load()
    for y in range(TARGET_SIZE[1]):
        amount = y / (TARGET_SIZE[1] - 1)
        color = tuple(_blend(top[index], bottom[index], amount) for index in range(3))
        pixels[0, y] = color
    return strip.resize(TARGET_SIZE)


def draw_frame(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle(
        (48, 48, TARGET_SIZE[0] - 48, TARGET_SIZE[1] - 48),
        radius=30,
        outline=(8, 5, 8, 245),
        width=18,
    )
    draw.rounded_rectangle(
        (70, 70, TARGET_SIZE[0] - 70, TARGET_SIZE[1] - 70),
        radius=24,
        outline=FRAME_GOLD,
        width=6,
    )
    draw.rounded_rectangle(
        (91, 91, TARGET_SIZE[0] - 91, TARGET_SIZE[1] - 91),
        radius=18,
        outline=(246, 224, 177, 135),
        width=2,
    )


def draw_arch(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    width = x1 - x0
    draw.rounded_rectangle(box, radius=width // 2, fill=(8, 13, 15, 245))
    draw.rounded_rectangle(box, radius=width // 2, outline=FRAME_GOLD, width=10)
    draw.rounded_rectangle(
        (x0 + 28, y0 + 28, x1 - 28, y1 - 28),
        radius=(width - 56) // 2,
        outline=(244, 224, 181, 105),
        width=3,
    )
    center = (x0 + x1) // 2
    draw.polygon(
        [(x0 + 38, y0 + 38), (center, y0 + 38), (center, y1 - 38), (x0 + 38, y1 - 38)],
        fill=(36, 69, 67, 215),
    )
    draw.polygon(
        [(center, y0 + 38), (x1 - 38, y0 + 38), (x1 - 38, y1 - 38), (center, y1 - 38)],
        fill=(76, 20, 35, 218),
    )
    draw.line((center, y0 + 40, center, y1 - 40), fill=MUTED_GOLD, width=5)


def draw_dual_silhouette(
    draw: ImageDraw.ImageDraw,
    *,
    center_x: int,
    head_y: int,
    scale: float,
) -> None:
    head_radius = round(150 * scale)
    left_head = (center_x - head_radius * 2, head_y, center_x, head_y + head_radius * 2)
    right_head = (center_x, head_y, center_x + head_radius * 2, head_y + head_radius * 2)
    draw.pieslice(left_head, 90, 270, fill=(231, 218, 189, 235))
    draw.pieslice(right_head, 270, 90, fill=(5, 8, 10, 245))

    shoulder_y = head_y + round(295 * scale)
    bottom_y = shoulder_y + round(390 * scale)
    shoulder_width = round(335 * scale)
    neck = round(72 * scale)
    draw.polygon(
        [
            (center_x - neck, shoulder_y - round(90 * scale)),
            (center_x - shoulder_width, shoulder_y + round(80 * scale)),
            (center_x - shoulder_width, bottom_y),
            (center_x, bottom_y),
            (center_x, shoulder_y - round(105 * scale)),
        ],
        fill=(222, 208, 179, 232),
    )
    draw.polygon(
        [
            (center_x, shoulder_y - round(105 * scale)),
            (center_x + shoulder_width, shoulder_y + round(80 * scale)),
            (center_x + shoulder_width, bottom_y),
            (center_x, bottom_y),
        ],
        fill=(4, 7, 9, 247),
    )
    eye_y = head_y + round(135 * scale)
    draw.ellipse(
        (
            center_x - round(97 * scale),
            eye_y,
            center_x - round(69 * scale),
            eye_y + round(18 * scale),
        ),
        fill=(31, 18, 17, 230),
    )
    draw.ellipse(
        (
            center_x + round(66 * scale),
            eye_y - round(4 * scale),
            center_x + round(105 * scale),
            eye_y + round(24 * scale),
        ),
        fill=(214, 156, 61, 255),
    )


def draw_molecular_flourish(draw: ImageDraw.ImageDraw) -> None:
    points = [(250, 2080), (405, 1995), (540, 2100), (690, 2008), (845, 2110)]
    draw.line(points, fill=(200, 158, 78, 165), width=4)
    for index, (x, y) in enumerate(points):
        radius = 16 if index in (0, len(points) - 1) else 12
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            outline=(235, 205, 139, 190),
            width=4,
        )
    draw.arc((990, 1940, 1360, 2240), 190, 350, fill=(200, 158, 78, 150), width=5)
    draw.arc((1035, 1985, 1310, 2205), 10, 170, fill=(235, 205, 139, 115), width=3)


def render_front(title: str, author: str) -> tuple[Image.Image, dict[str, Any]]:
    image = vertical_gradient((10, 24, 25), (39, 9, 21)).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    for index in range(19):
        inset = 118 + index * 29
        alpha = max(8, 35 - index)
        draw.arc(
            (inset, 680 + index * 8, 1600 - inset, 2220 - index * 5),
            195,
            345,
            fill=(213, 170, 88, alpha),
            width=2,
        )

    title_panel = [126, 126, 1474, 865]
    draw.rounded_rectangle(title_panel, radius=44, fill=PANEL, outline=FRAME_GOLD, width=4)
    title_box, title_font = LEGACY.COMMON.draw_centered_block(
        draw,
        title,
        name="title",
        y=208,
        max_width=1130,
        max_lines=3,
        max_size=126,
        min_size=82,
        bold=True,
        fill=IVORY,
        line_gap=13,
    )
    author_y = max(704, title_box["box"][3] + 44)
    author_box, author_font = LEGACY.COMMON.draw_centered_block(
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

    arch = (350, 925, 1250, 2190)
    draw_arch(draw, arch)
    draw_dual_silhouette(draw, center_x=800, head_y=1150, scale=0.92)
    draw_molecular_flourish(draw)
    draw_frame(draw)
    return image.convert("RGB"), {
        "content_panel": title_panel,
        "text_panels": {"title": title_panel, "author": title_panel},
        "text_boxes": [title_box, author_box],
        "fonts": {"title": str(title_font), "author": str(author_font)},
        "treatment": {
            "original_programmatic_art": True,
            "external_image_assets": [],
            "generated_image_model": None,
            "symbolism": ["divided doorway", "dual silhouette", "molecular flourish"],
        },
    }


def render_back(title: str, author: str) -> tuple[Image.Image, dict[str, Any]]:
    image = vertical_gradient((31, 9, 18), (7, 31, 32)).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    for index in range(16):
        x = 170 + index * 84
        draw.line(
            (x, 815, 1600 - x // 3, 2115),
            fill=(205, 166, 91, 16 + index),
            width=2,
        )

    title_panel = [132, 150, 1468, 900]
    draw.rounded_rectangle(title_panel, radius=48, fill=PANEL, outline=FRAME_GOLD, width=4)
    title_box, title_font = LEGACY.COMMON.draw_centered_block(
        draw,
        title,
        name="title",
        y=270,
        max_width=1080,
        max_lines=3,
        max_size=104,
        min_size=70,
        bold=True,
        fill=IVORY,
        line_gap=13,
    )
    author_y = max(765, title_box["box"][3] + 44)
    author_box, author_font = LEGACY.COMMON.draw_centered_block(
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

    draw_arch(draw, (425, 1010, 1175, 2115))
    draw_dual_silhouette(draw, center_x=800, head_y=1240, scale=0.76)
    draw.line((330, 2240, 1270, 2240), fill=FRAME_GOLD, width=4)
    draw.ellipse((786, 2226, 814, 2254), fill=MUTED_GOLD)
    draw_frame(draw)
    return image.convert("RGB"), {
        "content_panel": title_panel,
        "text_panels": {"title": title_panel, "author": title_panel},
        "text_boxes": [title_box, author_box],
        "fonts": {"title": str(title_font), "author": str(author_font)},
        "treatment": {
            "original_programmatic_art": True,
            "external_image_assets": [],
            "generated_image_model": None,
            "reader_facing_back_copy_rendered": False,
        },
    }


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
            if LEGACY.boxes_intersect(left["box"], right["box"]):
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
    catalog, catalog_hashes_before = LEGACY.load_catalog_truth()
    front, front_recipe = render_front(catalog["title"], catalog["author"])
    back, back_recipe = render_back(catalog["title"], catalog["author"])

    front_path = package_dir / f"{SLUG}-front-original-v3.jpg"
    back_path = package_dir / f"{SLUG}-back-original-v3.jpg"
    LEGACY.save_master_jpeg(front, front_path)
    LEGACY.save_master_jpeg(back, back_path)

    derivative_dir = package_dir / "derivatives"
    derivative_specs = {
        "front_thumbnail": (
            front,
            derivative_dir / f"{SLUG}-front-thumbnail-original-v3.webp",
            THUMBNAIL_SIZE,
            THUMBNAIL_BUDGET_BYTES,
        ),
        "front_feature": (
            front,
            derivative_dir / f"{SLUG}-front-feature-original-v3.webp",
            FEATURE_SIZE,
            FEATURE_BUDGET_BYTES,
        ),
        "back_thumbnail": (
            back,
            derivative_dir / f"{SLUG}-back-thumbnail-original-v3.webp",
            THUMBNAIL_SIZE,
            THUMBNAIL_BUDGET_BYTES,
        ),
        "back_feature": (
            back,
            derivative_dir / f"{SLUG}-back-feature-original-v3.webp",
            FEATURE_SIZE,
            FEATURE_BUDGET_BYTES,
        ),
    }
    encodings: dict[str, dict[str, Any]] = {}
    for name, (image, path, size, budget) in derivative_specs.items():
        encodings[name] = LEGACY.save_webp_with_budget(
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
        raise OriginalCoverError("; ".join(geometry_errors))

    front_validation = LEGACY.validate_cover_file(
        front_path,
        content_type="image/jpeg",
        max_bytes=MASTER_UPLOAD_LIMIT_BYTES,
    )
    back_validation = LEGACY.validate_cover_file(
        back_path,
        content_type="image/jpeg",
        max_bytes=MASTER_UPLOAD_LIMIT_BYTES,
    )
    derivative_validations: dict[str, dict[str, Any]] = {}
    for name, (_, path, size, budget) in derivative_specs.items():
        validation = LEGACY.validate_cover_file(
            path,
            content_type="image/webp",
            max_bytes=budget,
        )
        if [validation["width"], validation["height"]] != list(size):
            raise OriginalCoverError(f"{name} output dimensions are invalid")
        derivative_validations[name] = _derivative_record(
            path,
            package_dir=package_dir,
            validation=validation,
            encoding=encodings[name],
        )

    catalog_hashes_after = {
        repo_relative(path): sha256_file(path)
        for path in LEGACY.CATALOG_PATHS
    }
    if catalog_hashes_before != catalog_hashes_after:
        raise OriginalCoverError("controlled catalog changed during private preparation")

    manifest = {
        "schema_version": "earnalism.private_cover_candidate.v3",
        "status": "PRIVATE_CANDIDATE_EDITORIAL_REVIEW_REQUIRED",
        "generated_at": generated_at,
        "slug": SLUG,
        "title": catalog["title"],
        "author": catalog["author"],
        "generation_mode": "deterministic_original_programmatic_graphical_composition",
        "rights": {
            "status": "ORIGINAL_COMPOSITION_NO_THIRD_PARTY_ART",
            "external_image_assets": [],
            "generated_image_model": None,
            "territorial_restriction": None,
            "commercial_use_blocker": None,
        },
        "copy": {
            "title_source": "controlled_catalog",
            "author_source": "controlled_catalog",
            "back_description_rendered": False,
            "reason": "canonical short description contains internal production language",
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
            "title": catalog["title"],
            "author": catalog["author"],
            "output_size": list(TARGET_SIZE),
            "generation_mode": manifest["generation_mode"],
            "external_image_assets": [],
            "generated_image_model": None,
            "front": front_recipe,
            "back": back_recipe,
            "script": {
                "path": repo_relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
                "helper_path": repo_relative(LEGACY_SCRIPT),
                "helper_sha256": sha256_file(LEGACY_SCRIPT),
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
            "manual_checks_required": [
                "Visual inspection of both masters and thumbnails",
                "Owner/editorial approval of the exact hash-bound pair",
                "Authenticated admin upload as pending canonical review",
                "Separate exact-checksum canonical promotion",
            ],
        },
    )
    (package_dir / "review_packet.md").write_text(
        f"""# Jekyll and Hyde original graphical cover candidate

This private candidate uses only deterministic programmatic shapes and exact
controlled-catalog title/author text. It contains no third-party illustration,
generated image-model output, placeholder art, or territorial rights caveat.

- Front SHA-256: `{manifest['front']['sha256']}`
- Back SHA-256: `{manifest['back']['sha256']}`
- Dimensions: `1600 × 2400`
- Public upload: not yet authorized
- Canonical promotion: not yet authorized
- Reader/audio release truth: unchanged

The canonical short description is intentionally absent from the back cover
because it contains internal production language. No replacement marketing
copy was invented.
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
