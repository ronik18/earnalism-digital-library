"""Opt-in Library view of the existing rights-filtered public projection.

Preserve release, access, attribution, cover, audio and discovery fields verbatim.
Only omit detail-only editorial fields; chapter identity/preview flags remain.
This view never grants access and is not a Reader content/manifest response.
"""
DETAIL_ONLY_FIELDS = frozenset({'description', 'about_author', 'learnings', 'benefits'})
CHAPTER_SHELF_FIELDS = frozenset({'id', 'title', 'is_preview', 'chapter_number'})


def library_summary(books):
    return [
        {key: ([{field: value for field, value in chapter.items() if field in CHAPTER_SHELF_FIELDS}
                for chapter in value] if key == 'chapters' and isinstance(value, list) else value)
         for key, value in book.items() if key not in DETAIL_ONLY_FIELDS}
        for book in books
    ]
