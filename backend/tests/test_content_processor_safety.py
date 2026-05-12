import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.content_processor import process_chapter_content


def test_html_upload_strips_unsafe_blocks_and_preserves_structure():
    raw = b"""
    <h2>Chapter One</h2>
    <script>alert('x')</script>
    <p>First paragraph.</p>
    <p>&nbsp;</p>
    <style>body{display:none}</style>
    <blockquote>Quoted text</blockquote>
    <ul><li>Point one</li></ul>
    """

    result = process_chapter_content(raw, "chapter.html", "safety-fixture")
    html = result["content_html"]

    assert "<script" not in html
    assert "alert('x')" not in html
    assert "<style" not in html
    assert "display:none" not in html
    assert "<h2>Chapter One</h2>" in html
    assert "<blockquote>Quoted text</blockquote>" in html
    assert "<li>Point one</li>" in html
    assert "&nbsp;" not in html
    assert any("Unsafe scripts" in warning for warning in result["warnings"])
