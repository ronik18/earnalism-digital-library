import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.content_processor import process_chapter_content, sanitize_chapter_html_fragment


def test_sanitizer_preserves_preformatted_whitespace_and_nested_markup():
    pre = '<pre><code>if True:\n\t  value = 1\n    <strong>return</strong>  value\n\n\n</code></pre>'
    raw = '<p>Prose  spacing.</p>\n' + pre + '\n<p>After.</p>'
    clean, _ = sanitize_chapter_html_fragment(raw)
    assert pre in clean
    assert '<p>Prose spacing.</p>' in clean
    uploaded = process_chapter_content(raw.encode(), 'chapter.html', 'local-fixture')
    assert pre in uploaded['content_html']


def test_superscript_preserved_without_unsafe_attributes_or_urls():
    raw = '<p>Before<sup onclick="evil()" style="color:red">2</sup>after <a href="javascript:evil()">link</a></p><script>evil()</script>'
    clean, warnings = sanitize_chapter_html_fragment(raw)
    assert 'Before<sup>2</sup>after' in clean
    assert 'onclick' not in clean
    assert 'style=' not in clean
    assert 'javascript:' not in clean
    assert 'evil()' not in clean
    assert warnings
    uploaded = process_chapter_content(raw.encode(), 'chapter.html', 'local-fixture')
    assert 'Before<sup>2</sup>after' in uploaded['content_html']


def test_preformatted_security_filtering_runs_before_preservation():
    raw = '<pre onclick="evil()"><code>    safe\n<script>evil()</script><a href="javascript:evil()">    link</a>\n</code></pre>'
    clean, _ = sanitize_chapter_html_fragment(raw)
    assert '<code>    safe\n' in clean
    assert '<a>    link</a>' in clean
    assert 'onclick' not in clean
    assert 'javascript:' not in clean
    assert 'evil()' not in clean


def test_multiple_pre_blocks_and_escaped_markup_keep_independent_contexts():
    raw = '<p>Before  prose.</p><PRE>  first\n\n\n</PRE><p>&lt;pre&gt;  prose</p><pre>\t second<br>\n<br>\n<br>  last</pre>'
    clean, _ = sanitize_chapter_html_fragment(raw)
    assert '<pre>  first\n\n\n</pre>' in clean
    assert '<pre>\t second<br>\n<br>\n<br>  last</pre>' in clean
    assert '<p>Before prose.</p>' in clean
    assert '&lt;pre&gt; prose' in clean


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


def test_mixed_html_wraps_top_level_text_before_reader_pagination():
    raw = """
    <h2>Chapter One</h2>
    Read the Python file.
    Find the bug.

    <p>That is why agents need guardrails.</p>

    ```python
    result = agent.run(task)
    assert result
    ```
    """

    clean, warnings = sanitize_chapter_html_fragment(raw)

    assert warnings == []
    assert "<p>Read the Python file.<br>Find the bug.</p>" in clean
    assert "<p>That is why agents need guardrails.</p>" in clean
    assert "<pre><code>result = agent.run(task)\nassert result</code></pre>" in clean
    assert "&lt;p&gt;" not in clean
