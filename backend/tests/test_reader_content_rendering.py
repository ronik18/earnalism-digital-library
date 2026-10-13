import importlib
import os
import sys


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _server_module():
    os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    os.environ.setdefault("JWT_SECRET", "test-secret")
    return importlib.import_module("server")


def test_plain_text_reader_content_becomes_semantic_paragraphs():
    server = _server_module()

    html, warnings = server._manual_content_to_render_html(
        "প্রথম অনুচ্ছেদ।\n\nদ্বিতীয় অনুচ্ছেদ।\nদ্বিতীয় লাইনের অংশ।"
    )

    assert warnings == []
    assert html == "<p>প্রথম অনুচ্ছেদ।</p><p>দ্বিতীয় অনুচ্ছেদ।<br>দ্বিতীয় লাইনের অংশ।</p>"


def test_plain_text_reader_content_escapes_markup():
    server = _server_module()

    html, warnings = server._manual_content_to_render_html("৫ < ৬\n\nনিরাপদ পাঠ।")

    assert warnings == []
    assert "৫ &lt; ৬" in html
    assert "< ৬" not in html


def test_html_reader_content_remains_sanitized_and_structured():
    server = _server_module()

    html, warnings = server._manual_content_to_render_html(
        "<h2>অধ্যায়</h2><p>প্রথম অনুচ্ছেদ।</p><script>alert(1)</script>"
    )

    assert "<h2>অধ্যায়</h2>" in html
    assert "<p>প্রথম অনুচ্ছেদ।</p>" in html
    assert "<script" not in html
    assert any("Unsafe scripts" in warning for warning in warnings)


def test_plain_text_reader_preserves_source_ligature_notation():
    rendered, warnings = _server_module()._manual_content_to_render_html(
        "Visit Ph<oe>nixville, and read the encyclop<ae>dia."
    )
    assert warnings == []
    assert rendered == "<p>Visit Ph&lt;oe&gt;nixville, and read the encyclop&lt;ae&gt;dia.</p>"


def test_plain_text_reader_escapes_unknown_angle_bracket_notation():
    rendered, warnings = _server_module()._manual_content_to_render_html(
        "Use <notation> literally & keep 2 < 3."
    )
    assert warnings == []
    assert rendered == "<p>Use &lt;notation&gt; literally &amp; keep 2 &lt; 3.</p>"


def test_manual_reader_html_keeps_code_superscript_and_filters_xss():
    rendered, _ = _server_module()._manual_content_to_render_html(
        '<p onclick="evil()">Before<sup>2</sup></p>'
        '<pre><code>    preserved\n</code></pre>'
        '<img src="javascript:evil()" onerror="evil()">'
        '<script>evil()</script>'
    )
    assert "Before<sup>2</sup>" in rendered
    assert "<pre><code>    preserved\n</code></pre>" in rendered
    assert "onclick" not in rendered and "onerror" not in rendered
    assert "javascript:" not in rendered and "evil()" not in rendered


def test_manual_reader_detects_every_sanitizer_supported_html_tag():
    from utils.content_processor import ALLOWED_TAGS
    server = _server_module()
    for tag in ALLOWED_TAGS:
        assert server.HTML_TAG_RE.search(f"<{tag}>")
        assert server.HTML_TAG_RE.search(f"</{tag}>")


def test_acres_retained_chapter_eight_preserves_complete_plain_text():
    import hashlib
    import html
    import json
    import re
    from pathlib import Path

    path = Path(BACKEND_DIR) / "data/controlled_publications/acres-of-diamonds/chapters/chapter-008.json"
    chapter = json.loads(path.read_text(encoding="utf-8"))
    source = chapter["content"]
    assert hashlib.sha256(source.encode()).hexdigest() == chapter["content_hash"]
    assert "Ph<oe>nixville," in source
    rendered, warnings = _server_module()._manual_content_to_render_html(source)
    visible = html.unescape(re.sub(r"<[^>]+>", " ", rendered))
    assert warnings == []
    assert "Ph<oe>nixville," in visible
    assert re.sub(r"\s+", " ", visible).strip() == re.sub(r"\s+", " ", source).strip()
