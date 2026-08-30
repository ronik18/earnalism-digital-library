#!/usr/bin/env python3
"""Prepare a private, hash-bound P0 cover candidate for A Ghost Story.

This uses the established Pillow-based cover-candidate workflow: it accepts
only local, text-free art bases, adds all reader-facing text deterministically,
and cannot upload or promote either cover.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SLUG = "a-ghost-story"
SIZE = (1600, 2400)
PACKAGE = ROOT / "internal/audiobook_lab/sprint1_publication/cover_candidates" / SLUG / "p0_v1"
CATALOGS = tuple(ROOT / part / "controlled_publications" / SLUG / "public_book.json" for part in ("data", "backend/data"))
FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Georgia.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf")
IVORY, GOLD, INK = (246, 238, 215, 255), (187, 151, 82, 235), (15, 17, 20, 215)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> tuple[dict, dict[str, str]]:
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in CATALOGS]
    for field in ("slug", "title", "author", "short_description", "rights_basis"):
        if rows[0].get(field) != rows[1].get(field):
            raise ValueError(f"controlled mirrors diverge on {field}")
    if rows[0].get("slug") != SLUG:
        raise ValueError("unexpected slug")
    return rows[0], {str(path.relative_to(ROOT)): sha(path) for path in CATALOGS}


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidate = FONT_BOLD if bold else FONT_REGULAR
    if not candidate.is_file():
        raise ValueError(f"approved deterministic cover font unavailable: {candidate}")
    return ImageFont.truetype(str(candidate), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont, width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        probe = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), probe, font=face)[2] > width:
            lines.append(current); current = word
        else:
            current = probe
    if current: lines.append(current)
    return lines


def text_block(draw: ImageDraw.ImageDraw, text: str, y: int, width: int, sizes: range, max_lines: int, *, bold: bool, fill: tuple) -> dict:
    for size in sizes:
        face = font(size, bold=bold); lines = wrap(draw, text, face, width)
        if len(lines) <= max_lines: break
    else: raise ValueError(f"copy cannot fit: {text}")
    boxes = []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=face); left = (SIZE[0] - (box[2] - box[0])) // 2
        draw.text((left, y), line, font=face, fill=fill)
        boxes.append([left, y, left + box[2] - box[0], y + box[3] - box[1]])
        y += (box[3] - box[1]) + max(12, size // 6)
    return {"text": text, "font_size": face.size, "boxes": boxes}


def base(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB").resize(SIZE, Image.Resampling.LANCZOS)


def shade(image: Image.Image, top: int, bottom: int) -> Image.Image:
    overlay = Image.new("RGBA", SIZE, (*INK[:3], 0)); alpha = Image.new("L", (1, SIZE[1]))
    alpha.putdata([round(top + (bottom - top) * y / (SIZE[1] - 1)) for y in range(SIZE[1])])
    overlay.putalpha(alpha.resize(SIZE)); return Image.alpha_composite(image.convert("RGBA"), overlay)


def frame(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((52, 52, 1548, 2348), radius=28, outline=(19, 18, 19, 220), width=18)
    draw.rounded_rectangle((76, 76, 1524, 2324), radius=20, outline=GOLD, width=4)


def render_front(art: Path, title: str, author: str) -> tuple[Image.Image, dict]:
    image = shade(ImageEnhance.Contrast(base(art)).enhance(1.04), 205, 64); draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((130, 118, 1470, 690), radius=38, fill=(20, 22, 24, 224), outline=GOLD, width=3)
    title_box = text_block(draw, title, 220, 1120, range(150, 87, -4), 2, bold=True, fill=IVORY)
    author_box = text_block(draw, author, 540, 980, range(66, 39, -2), 1, bold=False, fill=GOLD)
    frame(draw); return image.convert("RGB"), {"title": title_box, "author": author_box}


def render_back(art: Path, title: str, author: str, description: str, rights: str) -> tuple[Image.Image, dict]:
    image = shade(ImageEnhance.Color(base(art)).enhance(.82), 96, 155); draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((120, 235, 1480, 2185), radius=42, fill=(16, 20, 23, 205), outline=GOLD, width=3)
    title_box = text_block(draw, title, 340, 1080, range(112, 75, -3), 2, bold=True, fill=IVORY)
    author_box = text_block(draw, author, 650, 950, range(58, 40, -2), 1, bold=False, fill=GOLD)
    desc_box = text_block(draw, description, 1080, 1050, range(51, 36, -2), 5, bold=False, fill=IVORY)
    rights_box = text_block(draw, "Public-domain text. Earnalism digital edition.", 1820, 1000, range(31, 22, -1), 2, bold=False, fill=GOLD)
    draw.rectangle((1120, 2030, 1395, 2155), outline=GOLD, width=2)
    frame(draw); return image.convert("RGB"), {"title": title_box, "author": author_box, "description": desc_box, "rights": rights_box, "barcode_zone": [1120, 2030, 1395, 2155]}


def save(image: Image.Image, path: Path) -> dict:
    image.save(path, "PNG", optimize=True, dpi=(300, 300))
    from backend.config.book_cover import validate_book_cover
    result = validate_book_cover(path.read_bytes(), "image/png", 8 * 1024 * 1024)
    if [result["width"], result["height"]] != list(SIZE): raise ValueError("wrong output dimensions")
    return result


def review_board(current_front: Path, current_back: Path, front: Path, back: Path) -> Path:
    """Create a clearly labelled static review board; it is not a live UI capture."""
    board = Image.new("RGB", (3600, 2800), "#111416")
    draw = ImageDraw.Draw(board)
    label = font(36, bold=True)
    small = font(25)
    slots = [
        ("Current wrong front", current_front, (80, 180), (560, 795)),
        ("Current wrong back", current_back, (680, 180), (560, 795)),
        ("Proposed front — native-resolution source", front, (1280, 180), (560, 795)),
        ("Proposed back — native-resolution source", back, (1880, 180), (560, 795)),
        ("Library desktop", front, (80, 1400), (310, 465)),
        ("Library mobile", front, (470, 1400), (180, 270)),
        ("Book Detail desktop", front, (730, 1400), (310, 465)),
        ("Book Detail mobile", front, (1120, 1400), (180, 270)),
        ("Listener locked desktop", front, (1380, 1400), (310, 465)),
        ("Listener locked mobile", front, (1770, 1400), (180, 270)),
        ("SEO/social-card crop", front, (2030, 1400), (420, 220)),
        ("Thumbnail crop", front, (80, 2125), (180, 270)),
    ]
    for title, path, (x, y), (w, h) in slots:
        with Image.open(path) as image:
            image = ImageOps.fit(image.convert("RGB"), (w, h), Image.Resampling.LANCZOS)
        draw.rounded_rectangle((x - 24, y - 60, x + w + 24, y + h + 42), radius=18, fill="#1b2023", outline="#bb9752", width=3)
        draw.text((x, y - 48), title, font=small, fill="#f6eed7")
        board.paste(image, (x, y))
    with Image.open(front) as image:
        blurred = ImageOps.fit(image.convert("RGB"), (180, 270), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(14))
    blur_x, blur_y = 360, 2125
    draw.rounded_rectangle((blur_x - 24, blur_y - 60, blur_x + 180 + 24, blur_y + 270 + 42), radius=18, fill="#1b2023", outline="#bb9752", width=3)
    draw.text((blur_x, blur_y - 48), "Blur-placeholder preview", font=small, fill="#f6eed7")
    board.paste(blurred, (blur_x, blur_y))
    draw.text((80, 55), "A Ghost Story — owner review board", font=label, fill="#f6eed7")
    draw.text((80, 1080), "PROPOSED_METADATA_ASSIGNMENT_NOT_LIVE", font=label, fill="#bb9752")
    draw.text((80, 2600), "Static visual placement plus shared-component contract evidence only; no deployed or assigned cover is claimed.", font=small, fill="#bb9752")
    target = PACKAGE / "owner-review-board.png"; board.save(target, "PNG", optimize=True); return target


def main() -> None:
    catalog, catalog_hashes = load(); PACKAGE.mkdir(parents=True, exist_ok=True)
    front_art, back_art = PACKAGE / "source_art/a-ghost-story-front-art-base-v1.png", PACKAGE / "source_art/a-ghost-story-back-art-base-v1.png"
    front, recipe_front = render_front(front_art, catalog["title"], catalog["author"])
    back, recipe_back = render_back(back_art, catalog["title"], catalog["author"], catalog["short_description"], catalog["rights_basis"])
    front_path, back_path = PACKAGE / "a-ghost-story_front_1600x2400_v1.png", PACKAGE / "a-ghost-story_back_1600x2400_v1.png"
    front_check, back_check = save(front, front_path), save(back, back_path)
    board = review_board(PACKAGE / "current-wrong-front.png", PACKAGE / "current-wrong-back.png", front_path, back_path)
    rollback = {"front": catalog.get("cover_url"), "back": catalog.get("back_cover_url"), "front_sha256": sha(PACKAGE / "current-wrong-front.png"), "back_sha256": sha(PACKAGE / "current-wrong-back.png")}
    manifest = {"schema_version": "earnalism.private_cover_candidate.v1", "status": "OWNER_A_GHOST_STORY_ASSIGNMENT_APPROVAL_REQUIRED", "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "slug": SLUG, "title": catalog["title"], "author": catalog["author"], "language": "en", "rights": {"tier": catalog["rights_tier"], "basis": catalog["rights_basis"], "source_evidence": "data/controlled_publications/a-ghost-story/source_evidence.json"}, "generation_mode": "text_free_ai_art_plus_existing_deterministic_pillow_typography", "source_art": {"front": {"path": str(front_art.relative_to(ROOT)), "sha256": sha(front_art)}, "back": {"path": str(back_art.relative_to(ROOT)), "sha256": sha(back_art)}}, "front": {"path": str(front_path.relative_to(ROOT)), "sha256": sha(front_path), **front_check}, "back": {"path": str(back_path.relative_to(ROOT)), "sha256": sha(back_path), **back_check}, "catalog_hashes": catalog_hashes, "current_defect": {"classification": "WRONG_TITLE_ART", "assigned_title": "Bharat at the Crossroads", "front": rollback["front"], "back": rollback["back"], "front_sha256": rollback["front_sha256"], "back_sha256": rollback["back_sha256"]}, "rollback": rollback, "composition": {"front": recipe_front, "back": recipe_back}, "review": {"board": str(board.relative_to(ROOT)), "admin_upload_status": "UPLOADED_PENDING_CANONICAL_REVIEW", "canonical_promotion_status": "NOT_PROMOTED", "owner_editorial_review_required": False, "owner_assignment_review_required": True, "assignment_plan": str((PACKAGE / "a-ghost-story-cover-assignment-plan.json").relative_to(ROOT)), "staged_candidate_records": str((PACKAGE / "staged-candidate-records.json").relative_to(ROOT))}, "constraints": {"private_only": True, "public_catalog_mutated": False, "reader_state_mutated": False, "audiobook_release_state_mutated": False}}
    (PACKAGE / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (PACKAGE / "review_packet.md").write_text(f"""# A Ghost Story controlled cover-assignment review\n\nThe live pair is **WRONG_TITLE_ART**: both files visibly belong to *Bharat at the Crossroads* and match its authoritative Cloudinary mapping. The approved pair is privately staged, not canonical, and has made no reader, audio, rights, publication, or public-metadata mutation.\n\n- Title/author: **{catalog['title']}** — **{catalog['author']}**\n- Rights: tier {catalog['rights_tier']}; {catalog['rights_basis']}\n- Proposed front SHA-256: `{manifest['front']['sha256']}`\n- Proposed back SHA-256: `{manifest['back']['sha256']}`\n- Existing rollback pair: `{rollback['front']}` and `{rollback['back']}`\n- Owner-review artifact: `{board.name}` (current wrong pair, proposed pair, native-resolution front/back, thumbnail crop, blur preview, and proposed Library/Book Detail/locked Listener desktop/mobile placement contexts). Every proposed surface is labeled `PROPOSED_METADATA_ASSIGNMENT_NOT_LIVE`.\n- Routed-component contract: `backend/tests/test_a_ghost_story_cover_assignment_plan.py` validates immutable assets and non-cover safety; `frontend/src/lib/aGhostStoryCoverAssignment.test.js` validates exact staged metadata through `BookCoverImage` source resolution and asserts its use by Library, Book Detail, and locked Listener surfaces.\n\n## Gate\n\n`OWNER_A_GHOST_STORY_ASSIGNMENT_APPROVAL_REQUIRED`\n\n`APPROVE_A_GHOST_STORY_ART` authorized only authenticated private candidate upload. Only `APPROVE_A_GHOST_STORY_ASSIGNMENT` may authorize canonical assignment. Until then, public cover fields remain unchanged.\n""", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__": main()
