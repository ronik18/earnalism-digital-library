"""Journal content safety and edition-independent social interaction policy."""
import bleach

ALLOWED_TAGS = ['p', 'h2', 'h3', 'strong', 'em', 'blockquote', 'ul', 'ol', 'li', 'br', 'hr', 'a', 'img']

def sanitize_journal_html(value):
    return bleach.clean(value or '', tags=ALLOWED_TAGS,
        attributes={'a': ['href', 'title'], 'img': ['src', 'alt', 'title']},
        protocols=['https', 'http'], strip=True)
