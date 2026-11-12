"""Discovery-only reading estimates from the complete delivered chapter text.

Never use these estimates for listening, entitlement, or payment accounting.
"""
from functools import lru_cache
from html.parser import HTMLParser
import json
from pathlib import Path
import re

WORDS_PER_MINUTE = 238
BLOCKS = {"p", "div", "section", "article", "br", "li", "tr", "td", "th",
          "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}


class ReaderText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipped = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skipped += 1
        if tag in BLOCKS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skipped:
            self.skipped -= 1
        if tag in BLOCKS:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skipped:
            self.parts.append(data)


def text_word_count(content):
    parser = ReaderText()
    parser.feed(str(content or ""))
    # Whitespace-delimited lexical tokens preserve Bengali vowel signs and
    # conjuncts. Tags, punctuation-only tokens, and hidden code are not words.
    return sum(any(c.isalnum() for c in token)
               for token in re.findall(r"\S+", "".join(parser.parts)))


@lru_cache(maxsize=512)
def _count_artifact(signature):
    total = 0
    for filename, _mtime, _size in signature:
        chapter = json.loads(Path(filename).read_text(encoding="utf-8"))
        total += text_word_count(chapter.get("content"))
    return total


def artifact_reading_estimate(base, chapters):
    """Use only manifest-listed chapters, never previews or stale chapter counts.

    Call after normal artifact validation. Missing/empty text has no defensible
    estimate; fail explicitly rather than advertising a stale short duration.
    File signatures invalidate the cache after a text repair.
    """
    signature = []
    for chapter in chapters:
        chapter_id = str(chapter.get("id") or "")
        if not chapter_id or Path(chapter_id).name != chapter_id:
            return {"estimated_reading_time": ""}
        path = Path(base) / "chapters" / f"{chapter_id}.json"
        try:
            stat = path.stat()
        except OSError:
            return {"estimated_reading_time": ""}
        signature.append((str(path), stat.st_mtime_ns, stat.st_size))
    try:
        count = _count_artifact(tuple(signature))
    except (OSError, ValueError, TypeError):
        return {"estimated_reading_time": ""}
    return {"estimated_reading_time": f"{max(1, round(count / WORDS_PER_MINUTE))} min" if count else ""}
