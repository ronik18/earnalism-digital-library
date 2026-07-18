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

    html, warnings = server._manual_content_to_render_html("প্রথম অনুচ্ছেদ।\n\nদ্বিতীয় অনুচ্ছেদ।\nদ্বিতীয় লাইনের অংশ।")

    assert warnings == []
    assert html == "<p>প্রথম অনুচ্ছেদ।</p><p>দ্বিতীয় অনুচ্ছেদ।<br>দ্বিতীয় লাইনের অংশ।</p>"


def test_plain_text_reader_content_escapes_markup():
    server = _server_module()

    html, warnings = server._manual_content_to_render_html("৫ < ৬\n\nনিরাপদ পাঠ।")

    assert warnings == []
    assert "৫ &lt; ৬" in html
    assert "< ৬" not in html
    assert "নিরাপদ পাঠ।" in html


def test_html_reader_content_remains_sanitized_and_structured():
    server = _server_module()

    html, warnings = server._manual_content_to_render_html("<h2>অধ্যায়</h2><p>প্রথম অনুচ্ছেদ।</p><script>alert(1)</script>")

    assert "<h2>অধ্যায়</h2>" in html
    assert "<p>প্রথম অনুচ্ছেদ।</p>" in html
    assert "<script" not in html
    assert any("Unsafe scripts" in warning for warning in warnings)
