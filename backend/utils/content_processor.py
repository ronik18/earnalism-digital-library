import base64
import io
import re
import uuid

import bleach
import mammoth
import markdown as md_lib
from PIL import Image as PILImage

from cloudinary.utils import cloudinary_url

from config.cloudinary import get_optimized_url, upload_image


ALLOWED_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5",
    "blockquote", "strong", "em", "b", "i", "u",
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
    "span": ["class", "style"],
    "div": ["class"],
    "figure": ["class"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "*": ["class"],
}


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


def process_chapter_content(file_bytes: bytes, filename: str, book_id: str) -> dict:
    ext = (filename or "").rsplit(".", 1)[-1].lower()

    if ext == "docx":
        result = mammoth.convert_to_html(io.BytesIO(file_bytes), style_map=STYLE_MAP)
        raw_html = result.value
    elif ext in ("md", "markdown"):
        decoded = file_bytes.decode("utf-8", errors="replace")
        raw_html = md_lib.markdown(
            decoded,
            extensions=["extra", "smarty", "tables", "toc", "nl2br"],
        )
    elif ext == "html":
        raw_html = file_bytes.decode("utf-8", errors="replace")
    elif ext == "txt":
        decoded = file_bytes.decode("utf-8", errors="replace")
        paragraphs = re.split(r"\n{2,}", decoded.strip())
        raw_html = "".join(f"<p>{p.strip().replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip())
    else:
        raise ValueError(f"Unsupported chapter format: .{ext}")

    processed = extract_and_upload_images(raw_html, book_id)
    clean = bleach.clean(processed, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    clean = re.sub(r"^(<p>)", r'<p class="drop-cap">', clean, count=1)

    plain = re.sub(r"<[^>]+>", "", clean)
    word_count = len(plain.split())
    return {
        "content_html": clean,
        "has_images": 'class="reader-img' in clean,
        "image_count": clean.count('class="reader-img'),
        "word_count": word_count,
        "reading_minutes": max(1, round(word_count / 238)),
    }


def process_book_cover(file_bytes: bytes, book_id: str) -> dict:
    result = upload_image(
        file_bytes,
        folder="earnalism/covers",
        public_id=f"cover_{book_id}",
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
