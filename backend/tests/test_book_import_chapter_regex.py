from scripts.import_books import detect_regex_chapters


def test_manifest_heading_regex_ignores_nested_roman_sections():
    text = """I. A FIRST STORY

Opening text.

I

Nested section.

II. THE SECOND STORY

Second story text.
"""
    chapters, warnings = detect_regex_chapters(
        text,
        r"^(?P<title>(?:I|II)\.\s+(?:A|THE) [A-Z ]+)$",
    )

    assert [chapter["title"] for chapter in chapters] == ["I. A FIRST STORY", "II. THE SECOND STORY"]
    assert "Nested section" in chapters[0]["content"]
    assert warnings == ["Used manifest-owned chapter heading regex for deterministic indexing."]

