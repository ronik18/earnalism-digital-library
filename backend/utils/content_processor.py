import base64
import html
import io
import re
import uuid

import bleach
import mammoth
import markdown as md_lib
from PIL import Image as PILImage

from cloudinary.utils import cloudinary_url

from config.cloudinary import get_optimized_url, upload_image


BENGALI_RE = re.compile(r"[\u0980-\u09FF]")


ALLOWED_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5",
    "blockquote", "strong", "em", "b", "i", "u",
    "pre", "code",
    "ul", "ol", "li", "br", "hr",
    "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div", "a",
]

ALLOWED_ATTRS = {
    "img": [
        "src", "alt", "width", "height",
        "data-srcset", "data-dominant-color", "data-type",
        "class", "loading",
    ],
    "a": ["href", "title", "target"],
    "code": ["class"],
    "span": ["class"],
    "div": ["class"],
    "figure": ["class"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "*": ["class"],
}

UNSAFE_BLOCK_RE = re.compile(
    r"<(script|style|iframe|object|embed|form|input|button|meta|link)\b[\s\S]*?</\1\s*>",
    re.IGNORECASE,
)
UNSAFE_TAG_RE = re.compile(
    r"</?(script|style|iframe|object|embed|form|input|button|meta|link)\b[^>]*>",
    re.IGNORECASE,
)


def detect_image_type(img_bytes: bytes) -> str:
    try:
        img = PILImage.open(io.BytesIO(img_bytes)).convert("RGB")
        img_small = img.resize((64, 64))
        colors = img_small.getcolors(maxcolors=4096)
        if colors is None:
            return "photo"
        n = len(colors)
        if n < 32:
            return "diagram"
        if n < 256:
            return "illustration"
        return "photo"
    except Exception:
        return "photo"


def extract_and_upload_images(html: str, book_id: str) -> str:
    pattern = re.compile(
        r'<img([^>]*?)src="data:image/([^;]+);base64,([^"]+)"([^>]*?)>',
        re.IGNORECASE,
    )

    def replace_match(m):
        try:
            img_bytes = base64.b64decode(m.group(3))
            img_type = detect_image_type(img_bytes)
            pid = f"books/{book_id}/{uuid.uuid4().hex[:8]}"
            result = upload_image(
                img_bytes,
                folder=f"earnalism/books/{book_id}",
                public_id=pid,
            )
            return (
                f'<img{m.group(1)}'
                f' src="{result["url"]}"'
                f' data-srcset="{result["srcset"]}"'
                f' data-dominant-color="{result["dominant_color"]}"'
                f' data-type="{img_type}"'
                f' loading="lazy"'
                f' class="reader-img reader-img--{img_type}"'
                f'{m.group(4)}>'
            )
        except Exception:
            return f'<img{m.group(1)} src="" alt="Image unavailable" class="reader-img--error"{m.group(4)}>'

    return pattern.sub(replace_match, html)


STYLE_MAP = """
p[style-name='Heading 1'] => h2:fresh
p[style-name='Heading 2'] => h3:fresh
p[style-name='Heading 3'] => h4:fresh
p[style-name='Quote'] => blockquote:fresh
p[style-name='Block Text'] => blockquote:fresh
""".strip()


def contains_bengali_text(text: str) -> bool:
    return bool(BENGALI_RE.search(text or ""))


def decode_text_file(file_bytes: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return file_bytes.decode(encoding), warnings
        except UnicodeDecodeError:
            continue
    if file_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return file_bytes.decode("utf-16"), warnings
        except UnicodeDecodeError:
            pass
    warnings.append("File was not valid UTF-8; unreadable bytes were replaced. Save the manuscript as UTF-8 and upload again if text looks wrong.")
    return file_bytes.decode("utf-8", errors="replace"), warnings


def remove_unsafe_blocks(raw_html: str) -> tuple[str, bool]:
    cleaned = UNSAFE_BLOCK_RE.sub("", raw_html or "")
    cleaned = UNSAFE_TAG_RE.sub("", cleaned)
    return cleaned, cleaned != (raw_html or "")


def normalize_render_html(clean_html: str) -> str:
    clean_html = re.sub(
        r"<p>\s*(?:&nbsp;|\s|<br\s*/?>)*\s*</p>",
        "",
        clean_html or "",
        flags=re.IGNORECASE,
    )
    clean_html = re.sub(r"(?:<br\s*/?>\s*){3,}", "<br><br>", clean_html, flags=re.IGNORECASE)
    clean_html = re.sub(r">\s+<", "><", clean_html)
    clean_html = re.sub(r"[ \t]{2,}", " ", clean_html)
    return clean_html.strip()


def sanitize_chapter_html_fragment(raw_html: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    safe_html, removed_unsafe = remove_unsafe_blocks(raw_html)
    if removed_unsafe:
        warnings.append("Unsafe scripts, styles, or embedded content were removed.")
    clean = bleach.clean(safe_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    return normalize_render_html(clean), warnings


def process_chapter_content(file_bytes: bytes, filename: str, book_id: str) -> dict:
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    warnings: list[str] = []

    if ext == "docx":
        result = mammoth.convert_to_html(io.BytesIO(file_bytes), style_map=STYLE_MAP)
        raw_html = result.value
        warnings.extend(str(m.message) for m in result.messages if getattr(m, "message", None))
    elif ext in ("md", "markdown"):
        decoded, decode_warnings = decode_text_file(file_bytes)
        warnings.extend(decode_warnings)
        raw_html = md_lib.markdown(
            decoded,
            extensions=["extra", "smarty", "tables", "toc", "nl2br"],
        )
    elif ext == "html":
        raw_html, decode_warnings = decode_text_file(file_bytes)
        warnings.extend(decode_warnings)
    elif ext == "txt":
        decoded, decode_warnings = decode_text_file(file_bytes)
        warnings.extend(decode_warnings)
        paragraphs = re.split(r"\n{2,}", decoded.strip())
        raw_html = "".join(
            f"<p>{html.escape(p.strip()).replace(chr(10), '<br>')}</p>"
            for p in paragraphs
            if p.strip()
        )
    else:
        raise ValueError(f"Unsupported chapter format: .{ext}")

    raw_html, removed_unsafe = remove_unsafe_blocks(raw_html)
    if removed_unsafe:
        warnings.append("Unsafe scripts, styles, or embedded content were removed.")

    processed = extract_and_upload_images(raw_html, book_id)
    clean = bleach.clean(processed, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    clean = normalize_render_html(clean)

    plain = html.unescape(re.sub(r"<[^>]+>", "", clean)).strip()
    has_bengali = contains_bengali_text(plain)
    if clean and not has_bengali:
        clean = re.sub(r"^(<p>)", r'<p class="drop-cap">', clean, count=1)

    if not plain and 'class="reader-img' in clean:
        warnings.append("No readable text was extracted. This file appears image-only/scanned; OCR is required before it can become searchable/selectable text.")

    word_count = len(plain.split())
    return {
        "content_html": clean,
        "has_images": 'class="reader-img' in clean,
        "image_count": clean.count('class="reader-img'),
        "word_count": word_count,
        "reading_minutes": max(1, round(word_count / 238)),
        "language_hint": "bn" if has_bengali else "",
        "warnings": warnings,
    }


def process_book_cover(file_bytes: bytes, book_id: str, kind: str = "front") -> dict:
    cover_kind = "back" if kind == "back" else "front"
    public_prefix = "back_cover" if cover_kind == "back" else "cover"
    result = upload_image(
        file_bytes,
        folder=f"earnalism/covers/{cover_kind}",
        public_id=f"{public_prefix}_{book_id}",
    )
    thumbnail_url = get_optimized_url(
        result["public_id"], width=300, height=450, crop="fill"
    )
    blur_url, _ = cloudinary_url(
        result["public_id"],
        width=20, height=30, crop="fill", effect="blur:2000", quality=30,
    )
    return {
        "cover_url": result["url"],
        "thumbnail_url": thumbnail_url,
        "blur_placeholder": blur_url,
        "dominant_color": result["dominant_color"],
        "srcset": result["srcset"],
    }
