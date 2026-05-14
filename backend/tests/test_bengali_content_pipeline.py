import importlib
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.content_processor import process_chapter_content


FIXTURE = Path(__file__).parent / "fixtures" / "bengali_sample.txt"
TITLE = "বাংলার গল্প"
CHAPTER = "প্রথম অধ্যায়"
BODY = "এটি একটি পরীক্ষামূলক বাংলা অনুচ্ছেদ। পাঠটি সঠিকভাবে দেখা যাচ্ছে কি না যাচাই করা হচ্ছে।"


def test_bengali_txt_upload_preserves_unicode_text():
    result = process_chapter_content(FIXTURE.read_bytes(), "bengali_sample.txt", "bengali-fixture")

    html = result["content_html"]
    assert TITLE in html
    assert CHAPTER in html
    assert BODY in html
    assert result["language_hint"] == "bn"
    assert result["word_count"] >= 10
    assert "drop-cap" not in html
    assert "\ufffd" not in html
    assert result["warnings"] == []


def test_bengali_html_upload_preserves_headings_and_paragraphs():
    html = f"<h2>{CHAPTER}</h2><p>{BODY}</p>"
    result = process_chapter_content(html.encode("utf-8"), "chapter.html", "bengali-fixture")

    assert f"<h2>{CHAPTER}</h2>" in result["content_html"]
    assert BODY in result["content_html"]
    assert result["language_hint"] == "bn"
    assert result["warnings"] == []


def test_bengali_title_slug_uses_stable_ascii_fallback(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/earnalism_test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    server = importlib.import_module("server")

    assert server.slugify(TITLE, fallback="book-bengali01") == "book-bengali01"
    rendered = server.UTF8JSONResponse({"title": TITLE, "chapter": CHAPTER}).body.decode("utf-8")
    assert TITLE in rendered
    assert CHAPTER in rendered
    assert "\\u09" not in rendered
