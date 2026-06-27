#!/usr/bin/env python3
"""Build a clean upload manifest for held-back Gutenberg collection stories."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "book_import_manifest.json"
DEFAULT_DEDUPE_REPORT = ROOT / "output/bulk_upload_manifest/20260602T185043Z/dedupe_and_category_report.json"
DEFAULT_FINAL_REPORT = ROOT / "output/bulk_upload_manifest/20260602T185043Z/final_upload_manifest_report.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output/gutenberg_collection_extract"


KEY_ALIASES = {
    "authorlatin": "author_latin",
    "authordeathyear": "author_death_year",
    "originalpublicationyear": "original_publication_year",
    "sourceurl": "source_url",
    "sourcetype": "source_type",
    "sourcelicense": "source_license",
    "rightsbasis": "rights_basis",
    "commercialuseallowed": "commercial_use_allowed",
    "audioallowed": "audio_allowed",
    "requiresattribution": "requires_attribution",
    "requiressharealike": "requires_share_alike",
    "categoryslug": "category_slug",
    "shortdescription": "short_description",
    "aboutauthor": "about_author",
    "ispublished": "is_published",
    "attributionnotice": "required_attribution",
    "forbiddensourceterms": "forbidden_source_terms",
}


SOURCE_REPAIRS: dict[tuple[str, str], dict[str, Any]] = {
    ("The Tell-Tale Heart", "Edgar Allan Poe"): {"gutenberg_id": 2148},
    ("The Murders in the Rue Morgue", "Edgar Allan Poe"): {"gutenberg_id": 2147},
    ("The Masque of the Red Death", "Edgar Allan Poe"): {"gutenberg_id": 1064},
    ("The Pit and the Pendulum", "Edgar Allan Poe"): {"gutenberg_id": 2148},
    ("Berenice", "Edgar Allan Poe"): {"gutenberg_id": 2148},
    ("The Purloined Letter", "Edgar Allan Poe"): {"gutenberg_id": 2148},
    ("Ligeia", "Edgar Allan Poe"): {"gutenberg_id": 2149},
    ("The Imp of the Perverse", "Edgar Allan Poe"): {"gutenberg_id": 2148},
    ("The Gift of the Magi", "O. Henry"): {"gutenberg_id": 7256},
    ("The Last Leaf", "O. Henry"): {"gutenberg_id": 3707},
    ("After Twenty Years", "O. Henry"): {"gutenberg_id": 2776},
    ("The Ransom of Red Chief", "O. Henry"): {"gutenberg_id": 1595},
    ("A Retrieved Reformation", "O. Henry"): {"gutenberg_id": 1646},
    ("The Furnished Room", "O. Henry"): {"gutenberg_id": 2776},
    ("The Cop and the Anthem", "O. Henry"): {"gutenberg_id": 2776},
    ("The Lady with the Dog", "Anton Chekhov"): {"gutenberg_id": 13415},
    ("The Bishop", "Anton Chekhov"): {"gutenberg_id": 13419},
    ("The Student", "Anton Chekhov"): {"gutenberg_id": 1944},
    ("Ward No. 6", "Anton Chekhov"): {"gutenberg_id": 13409},
    ("The Bet", "Anton Chekhov"): {"gutenberg_id": 55283},
    ("The Darling", "Anton Chekhov"): {"gutenberg_id": 13416, "end_title_variants": ["Ariadne"]},
    ("Gooseberries", "Anton Chekhov"): {"gutenberg_id": 1883},
    ("The Man in a Case", "Anton Chekhov"): {"gutenberg_id": 1883},
    ("A Scandal in Bohemia", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Red-Headed League", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Speckled Band", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Five Orange Pips", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Man with the Twisted Lip", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Adventure of the Blue Carbuncle", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Adventure of the Copper Beeches", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Adventure of the Engineer's Thumb", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Adventure of the Noble Bachelor", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Adventure of the Beryl Coronet", "Arthur Conan Doyle"): {"gutenberg_id": 1661},
    ("The Adventure of the Final Problem", "Arthur Conan Doyle"): {"gutenberg_id": 834},
    ("The Adventure of the Greek Interpreter", "Arthur Conan Doyle"): {"gutenberg_id": 834},
    ("The Adventure of the Empty House", "Arthur Conan Doyle"): {"gutenberg_id": 108, "end_title_variants": ["The Adventure of the Norwood Builder"]},
    ("The Adventure of the Dancing Men", "Arthur Conan Doyle"): {"gutenberg_id": 108},
    ("The Adventure of the Solitary Cyclist", "Arthur Conan Doyle"): {"gutenberg_id": 108},
    ("The Adventure of the Second Stain", "Arthur Conan Doyle"): {"gutenberg_id": 108},
    ("The Adventure of Charles Augustus Milverton", "Arthur Conan Doyle"): {"gutenberg_id": 108},
    ("The Adventure of the Priory School", "Arthur Conan Doyle"): {"gutenberg_id": 108, "end_title_variants": ["The Adventure of Black Peter"]},
    ("The Adventure of the Abbey Grange", "Arthur Conan Doyle"): {"gutenberg_id": 108},
    ("The Adventure of the Six Napoleons", "Arthur Conan Doyle"): {"gutenberg_id": 108, "end_title_variants": ["The Three Students"]},
    ("To Build a Fire", "Jack London"): {"gutenberg_id": 2429, "end_title_variants": ["That Spot"]},
    ("Love of Life", "Jack London"): {"gutenberg_id": 710, "end_title_variants": ["A Day's Lodging"]},
    ("The Necklace", "Guy de Maupassant"): {"gutenberg_id": 3080, "end_title_variants": ["The Marquis de Fumerol"]},
    ("Boule de Suif", "Guy de Maupassant"): {"gutenberg_id": 3077, "end_title_variants": ["Two Friends"]},
    ("The Story of an Hour", "Kate Chopin"): {
        "source_url": "https://en.wikisource.org/wiki/The_Story_of_an_Hour",
        "source_type": "wikisource_html",
        "source_license": (
            "Underlying 1894 story is public domain in the U.S. and India; "
            "Wikisource transcription/source layer is reused under CC BY-SA terms."
        ),
        "rights_basis": "Kate Chopin died in 1904 and the story was first published in 1894. Public domain in India and the U.S.",
        "required_attribution": (
            "Source transcription from English Wikisource, reused under CC BY-SA terms. "
            "Original literary text is public domain."
        ),
    },
    ("Désirée's Baby", "Kate Chopin"): {"gutenberg_id": 160},
    ("An Occurrence at Owl Creek Bridge", "Ambrose Bierce"): {"gutenberg_id": 375},
    ("A Horseman in the Sky", "Ambrose Bierce"): {"gutenberg_id": 5661},
    ("The Celebrated Jumping Frog of Calaveras County", "Mark Twain"): {"gutenberg_id": 10947, "end_title_variants": ["Elder Brown's Backslide"]},
    ("A Ghost Story", "Mark Twain"): {"gutenberg_id": 3189, "end_title_variants": ["The Capitoline Venus"]},
    ("The Stolen White Elephant", "Mark Twain"): {"gutenberg_id": 3181},
    ("Rip Van Winkle", "Washington Irving"): {"gutenberg_id": 60976},
    ("The Legend of Sleepy Hollow", "Washington Irving"): {"gutenberg_id": 41},
    ("Young Goodman Brown", "Nathaniel Hawthorne"): {"gutenberg_id": 512},
    ("The Minister's Black Veil", "Nathaniel Hawthorne"): {"gutenberg_id": 13707},
    ("Rappaccini's Daughter", "Nathaniel Hawthorne"): {"gutenberg_id": 512, "end_title_variants": ["Mrs. Bullfrog"]},
    ("The Ambitious Guest", "Nathaniel Hawthorne"): {"gutenberg_id": 13707},
    ("Feathertop", "Nathaniel Hawthorne"): {"gutenberg_id": 512, "end_title_variants": ["The New Adam and Eve"]},
    ("A White Heron", "Sarah Orne Jewett"): {"gutenberg_id": 74980, "end_title_variants": ["The Flight of Betsey Lane"]},
    ("The Open Boat", "Stephen Crane"): {"gutenberg_id": 45524},
    ("The Bride Comes to Yellow Sky", "Stephen Crane"): {"gutenberg_id": 45524},
    ("A Mystery of Heroism", "Stephen Crane"): {"gutenberg_id": 6979},
    ("Markheim", "Robert Louis Stevenson"): {"gutenberg_id": 344},
    ("The Suicide Club", "Robert Louis Stevenson"): {
        "gutenberg_id": 839,
        "end_title_variants": ["The Rajah's Diamond"],
    },
    ("The Outcasts of Poker Flat", "Bret Harte"): {"gutenberg_id": 6373, "end_title_variants": ["Miggles"]},
    ("The Luck of Roaring Camp", "Bret Harte"): {"gutenberg_id": 6373},
    ("A Wagner Matinee", "Willa Cather"): {"gutenberg_id": 346},
    ("Paul's Case", "Willa Cather"): {"gutenberg_id": 346},
    ("The Revolt of Mother", "Mary E. Wilkins Freeman"): {"gutenberg_id": 50543},
    ("Sredni Vashtar", "Saki"): {"gutenberg_id": 3688},
    ("The Open Window", "Saki"): {"gutenberg_id": 269, "end_title_variants": ["The Treasure Ship"]},
    ("Tobermory", "Saki"): {"gutenberg_id": 3688},
    ("The Happy Prince", "Oscar Wilde"): {"gutenberg_id": 902},
    ("The Selfish Giant", "Oscar Wilde"): {"gutenberg_id": 902, "end_title_variants": ["The Devoted Friend"]},
    ("The Fiddler of the Reels", "Thomas Hardy"): {"gutenberg_id": 3047},
    ("The Withered Arm", "Thomas Hardy"): {"gutenberg_id": 3056, "end_title_variants": ["Fellow-Townsmen"]},
    ("The Country of the Blind", "H.G. Wells"): {"gutenberg_id": 11870},
    ("The Door in the Wall", "H.G. Wells"): {"gutenberg_id": 11870},
    ("Rikki-Tikki-Tavi", "Rudyard Kipling"): {"gutenberg_id": 35997, "end_title_variants": ["Toomai of the Elephants"]},
    ("The Deadliest Game", "Richard Connell"): {
        "canonical_title": "The Most Dangerous Game",
        "source_url": "https://en.wikisource.org/wiki/O._Henry_Memorial_Award_Prize_Stories_of_1924/The_Most_Dangerous_Game",
        "source_type": "wikisource_html",
        "title_variants": ["The Most Dangerous Game"],
        "source_license": (
            "Underlying 1924 story is public domain in the U.S. and India; "
            "Wikisource transcription/source layer is reused under CC BY-SA terms."
        ),
        "rights_basis": (
            "Richard Connell died in 1949 and the story was first published in 1924. "
            "Public domain in India and the U.S.; canonical title corrected from manifest alias."
        ),
        "required_attribution": (
            "Source transcription from English Wikisource, reused under CC BY-SA terms. "
            "Original literary text is public domain."
        ),
    },
    ("A Jury of Her Peers", "Susan Glaspell"): {
        "gutenberg_id": 20872,
        "end_title_variants": ["The Bunker Mouse"],
        "source_license": "Project Gutenberg public-domain anthology text; source evidence kept internal/admin-only.",
        "rights_basis": (
            "Susan Glaspell died in 1948 and the story was first published in 1917. "
            "Public domain in India and the U.S."
        ),
    },
}


TITLE_VARIANTS: dict[tuple[str, str], list[str]] = {
    ("The Speckled Band", "Arthur Conan Doyle"): ["The Adventure of the Speckled Band"],
    ("The Adventure of the Final Problem", "Arthur Conan Doyle"): ["The Final Problem"],
    ("The Adventure of the Greek Interpreter", "Arthur Conan Doyle"): ["The Greek Interpreter"],
    ("The Deadliest Game", "Richard Connell"): ["The Most Dangerous Game"],
    ("The Necklace", "Guy de Maupassant"): ["The Diamond Necklace"],
    ("Feathertop", "Nathaniel Hawthorne"): ["Feathertop: A Moralized Legend"],
}


SKIPPED_SOURCE_REPAIRS: dict[tuple[str, str], str] = {
    ("In the Penal Colony", "Franz Kafka"): (
        "No exact Project Gutenberg source found; existing Gutenberg ID 7849 is The Trial, "
        "and no clean English Wikisource page was available for importer validation."
    ),
}


@dataclass
class SourceText:
    cleaned: str
    lines: list[str]
    warnings: list[str]
    download_log: dict[str, Any]


def load_importer() -> Any:
    spec = importlib.util.spec_from_file_location("earnalism_import_books", ROOT / "scripts/import_books.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load scripts/import_books.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["earnalism_import_books"] = module
    spec.loader.exec_module(module)
    return module


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_manifest_objects(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'"books"\s*:\s*\[', text)
    start = match.end() if match else 0
    books: list[dict[str, Any]] = []
    in_string = False
    escaped = False
    depth = 0
    object_start: int | None = None
    for index, char in enumerate(text[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                object_start = index
            depth += 1
            continue
        if char == "}" and depth:
            depth -= 1
            if depth == 0 and object_start is not None:
                books.append(json.loads(text[object_start : index + 1]))
                object_start = None
    return books


def normalize_book(raw: dict[str, Any]) -> dict[str, Any]:
    book: dict[str, Any] = {}
    for key, value in raw.items():
        normalized = KEY_ALIASES.get(key, key)
        book[normalized] = value
    if "source_type" in book:
        source_type = str(book["source_type"]).strip()
        source_type_aliases = {
            "gutenberghtml": "gutenberg",
            "gutenberghtml": "gutenberg",
            "gutenberg_text": "gutenberg",
            "wikisourcebengalihtml": "wikisource_bengali_html",
        }
        book["source_type"] = source_type_aliases.get(source_type.lower().replace("_", ""), source_type)
    if "category_slug" in book:
        book["category_slug"] = str(book["category_slug"]).strip()
    book["is_published"] = False
    book["availability"] = "draft"
    book["audiobook_enabled"] = False
    book["generate_audiobook"] = False
    return book


def target_manifest_ids(dedupe_report: Path, final_report: Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    details_by_id: dict[str, dict[str, Any]] = {}
    ids: list[str] = []
    dedupe = json.loads(dedupe_report.read_text(encoding="utf-8"))
    for item in dedupe.get("skipped_books_detail", []):
        manifest_id = item.get("manifest_id")
        if not manifest_id:
            continue
        details_by_id[manifest_id] = item
        reasons = " | ".join(item.get("reasons") or [])
        if "Gutenberg ebook" not in reasons:
            continue
        if any(
            phrase in reasons
            for phrase in (
                "current importer would upload the whole collection",
                "wrong full text",
                "manual source review",
                "known source/title mismatch",
            )
        ):
            ids.append(manifest_id)

    final = json.loads(final_report.read_text(encoding="utf-8"))
    for item in final.get("post_preflight_sanity_skipped", []):
        manifest_id = item.get("manifest_id")
        if manifest_id:
            ids.append(manifest_id)
            details_by_id.setdefault(manifest_id, item)
    return ids, details_by_id


def plain_key(value: str, drop_articles: bool = False) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("&", " and ")
    value = re.sub(r"^\s*(?:[ivxlcdm]+|\d{1,3})\s*[.):-]\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\s*(?:chapter|story|part)\s+(?:[ivxlcdm]+|\d{1,3})\s*[.)::-]?\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().casefold()
    if drop_articles:
        value = re.sub(r"^(?:the|a|an)\s+", "", value)
    return re.sub(r"\s+", " ", value)


def title_variants(book: dict[str, Any], repair: dict[str, Any]) -> list[str]:
    title = str(book.get("title") or "")
    author = str(book.get("author") or "")
    variants = [str(repair.get("canonical_title") or title), title]
    variants.extend(TITLE_VARIANTS.get((title, author), []))
    variants.extend(repair.get("title_variants") or [])
    if title.startswith("The Adventure of "):
        variants.append(f"The {title.removeprefix('The Adventure of ')}")
    unique: list[str] = []
    for variant in variants:
        if variant and variant not in unique:
            unique.append(variant)
    return unique


def title_match(line: str, variants: list[str]) -> bool:
    line_keys = {plain_key(line), plain_key(line, drop_articles=True)}
    for variant in variants:
        variant_keys = {plain_key(variant), plain_key(variant, drop_articles=True)}
        if line_keys & variant_keys:
            return True
        for line_key in line_keys:
            for variant_key in variant_keys:
                if not variant_key or not line_key.startswith(f"{variant_key} "):
                    continue
                suffix = line_key[len(variant_key) :].strip()
                if re.fullmatch(r"(?:\d+\s*){1,3}", suffix):
                    return True
    return False


def word_count(importer: Any, text: str) -> int:
    return len(importer.words(text))


def line_word_count(line: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", line or ""))


def is_roman_or_numeric(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[ivxlcdm]+|\d{1,3})\.?\s*$", line or "", re.IGNORECASE))


def title_like_ratio(line: str) -> float:
    tokens = [token for token in re.split(r"\s+", line.strip()) if token]
    if not tokens:
        return 0.0
    good = 0
    for token in tokens:
        clean = re.sub(r"^[\"'“‘(\[]+|[\"'”’),.!?\]:;]+$", "", token)
        if not clean:
            continue
        if clean.isupper() or clean[:1].isupper() or clean.casefold() in {
            "a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
            "of", "on", "or", "the", "to", "with", "without",
        }:
            good += 1
    return good / len(tokens)


def plausible_heading(lines: list[str], index: int) -> bool:
    line = lines[index].strip()
    if not line or len(line) > 130 or is_roman_or_numeric(line):
        return False
    if re.search(r"[.!?;:]$", line):
        return False
    if re.match(r"(?i)^(by|translated by|from|copyright|contents)\b", line):
        return False
    if line_word_count(line) > 14:
        return False
    prev_blank = index == 0 or not lines[index - 1].strip()
    next_blank = index == len(lines) - 1 or not lines[index + 1].strip()
    if not (prev_blank or next_blank):
        return False
    return line.isupper() or title_like_ratio(line) >= 0.75


def isolated_heading_line(lines: list[str], index: int) -> bool:
    line = lines[index].strip()
    if not line or len(line) > 130 or is_roman_or_numeric(line):
        return False
    if re.match(r"(?i)^(by|translated by|from|copyright|contents|language|loc class)\b", line):
        return False
    if line_word_count(line) > 14:
        return False
    prev_blank = index == 0 or not lines[index - 1].strip()
    next_blank = index == len(lines) - 1 or not lines[index + 1].strip()
    return prev_blank or next_blank


def toc_end_heading(lines: list[str], index: int) -> bool:
    if not isolated_heading_line(lines, index):
        return False
    line = lines[index].strip()
    if line.startswith(("“", "\"", "'", "—", "-", "_")):
        return False
    return line.isupper() or title_like_ratio(line) >= 0.82


def candidate_heading_keys(lines: list[str]) -> Counter[str]:
    keys: Counter[str] = Counter()
    for index in range(len(lines)):
        if plausible_heading(lines, index):
            key = plain_key(lines[index], drop_articles=True)
            if key:
                keys[key] += 1
    return keys


def toc_heading_keys(lines: list[str]) -> set[str]:
    keys: set[str] = set()
    contents_index: int | None = None
    for index, raw_line in enumerate(lines[:1000]):
        if plain_key(raw_line) == "contents":
            contents_index = index
            break
    if contents_index is None:
        return keys
    for raw_line in lines[contents_index + 1 : min(len(lines), contents_index + 350)]:
        line = raw_line.strip()
        if not line:
            continue
        pieces = [line]
        delimiter_split = False
        if " -- " in line:
            delimiter_split = True
            pieces = [piece.strip(" .") for piece in line.split(" -- ")]
        for piece in pieces:
            if not piece or len(piece) > 160:
                continue
            if re.match(r"(?i)^(contents|language|loc class|subject|release date|credits|author|title)$", piece):
                continue
            if line_word_count(piece) > 14:
                continue
            looks_like_contents_entry = (
                delimiter_split
                or piece.isupper()
                or bool(re.match(r"(?i)^(?:chapter\s+)?(?:[ivxlcdm]+|\d{1,3})\b", piece))
                or (bool(re.search(r"\b\d{1,4}\s*$", piece)) and title_like_ratio(piece) >= 0.75)
            )
            if not looks_like_contents_entry:
                continue
            key = plain_key(piece, drop_articles=True)
            if key and len(key) > 2:
                keys.add(key)
    return keys


def find_start_index(lines: list[str], variants: list[str]) -> int | None:
    matches = [index for index, line in enumerate(lines) if title_match(line, variants)]
    if not matches:
        return None
    return matches[-1]


def should_skip_initial_line(line: str, author: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    author_key = plain_key(author)
    line_key = plain_key(stripped)
    if re.match(r"(?i)^by\s+", stripped):
        return True
    if re.match(r"(?i)^\[?(?:note|copyright)\b", stripped):
        return True
    if author_key and (line_key == author_key or line_key == f"by {author_key}"):
        return True
    if re.match(r"^[*_\-=\s]{3,}$", stripped):
        return True
    if re.match(r"(?i)^(translated|translation|illustrated|edited)\b", stripped):
        return True
    return False


def body_start_offset(lines: list[str], start_index: int, author: str) -> int:
    index = start_index + 1
    while index < len(lines) and should_skip_initial_line(lines[index], author):
        index += 1
    return max(0, index - (start_index + 1))


def body_words_between(importer: Any, lines: list[str], start: int, end: int) -> int:
    return word_count(importer, "\n".join(lines[start:end]))


def find_end_index(
    importer: Any,
    lines: list[str],
    body_start: int,
    known_keys: set[str],
    repair: dict[str, Any],
) -> int | None:
    override_variants = repair.get("end_title_variants") or []
    if override_variants:
        for index in range(body_start + 1, len(lines)):
            if title_match(lines[index], override_variants):
                return index
    known_or_toc_keys = set(known_keys) | toc_heading_keys(lines)
    for index in range(body_start + 1, len(lines)):
        if body_words_between(importer, lines, body_start, index) < 500:
            continue
        if re.match(r"(?i)^\s*chapter\b", lines[index].strip()):
            continue
        key = plain_key(lines[index], drop_articles=True)
        if key in known_or_toc_keys and toc_end_heading(lines, index):
            return index
    return None


def source_key(book: dict[str, Any]) -> str:
    return f"{book.get('source_type', '')}:{book.get('source_url', '')}"


def load_source_text(importer: Any, book: dict[str, Any], cache: dict[str, SourceText]) -> SourceText:
    key = source_key(book)
    if key in cache:
        return cache[key]
    body, download_log = importer.download_source(book["source_url"], book.get("source_type", ""))
    raw = importer.decode_utf8(body)
    cleaned, warnings = importer.sanitize_text(raw, book)
    item = SourceText(cleaned=cleaned, lines=cleaned.split("\n"), warnings=warnings, download_log=download_log)
    cache[key] = item
    return item


def apply_source_repair(book: dict[str, Any], repair: dict[str, Any]) -> None:
    if repair.get("canonical_title"):
        book["title"] = repair["canonical_title"]
    if repair.get("gutenberg_id"):
        book["source_url"] = f"https://www.gutenberg.org/ebooks/{repair['gutenberg_id']}"
        book["source_type"] = "gutenberg"
        book["source_license"] = "Project Gutenberg public-domain text; source evidence kept internal/admin-only."
        book["rights_basis"] = (
            f"{book.get('author', 'Author')} died {book.get('author_death_year')}; "
            f"first published {book.get('original_publication_year')}. Public domain in India and the U.S."
        )
    else:
        for key in ("source_url", "source_type", "source_license", "rights_basis", "required_attribution"):
            if repair.get(key):
                book[key] = repair[key]


def minimum_for_extracted(words_found: int) -> int:
    return max(350, min(2500, int(words_found * 0.72)))


def build_manifest(args: argparse.Namespace) -> int:
    importer = load_importer()
    raw_books = parse_manifest_objects(args.manifest)
    raw_by_id = {book.get("id"): book for book in raw_books}
    target_ids, report_details = target_manifest_ids(args.dedupe_report, args.final_report)

    out_dir = args.output_dir / utc_stamp()
    text_dir = out_dir / "prepared_texts"
    text_dir.mkdir(parents=True, exist_ok=True)

    selected: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    seen_title_author: set[tuple[str, str]] = set()
    source_cache: dict[str, SourceText] = {}

    normalized_targets: list[dict[str, Any]] = []
    for manifest_id in target_ids:
        raw = raw_by_id.get(manifest_id)
        if not raw:
            decisions.append({"manifest_id": manifest_id, "status": "skipped", "reason": "manifest item not found"})
            continue
        book = normalize_book(raw)
        detail = report_details.get(manifest_id, {})
        if detail.get("redistributed_category"):
            book["category_slug"] = detail["redistributed_category"]
        normalized_targets.append(book)

    source_known_keys: dict[str, set[str]] = defaultdict(set)
    for book in normalized_targets:
        title = str(book.get("title") or "")
        author = str(book.get("author") or "")
        repair = SOURCE_REPAIRS.get((title, author), {})
        if not repair:
            continue
        repaired = dict(book)
        apply_source_repair(repaired, repair)
        for variant in title_variants(book, repair):
            source_known_keys[source_key(repaired)].add(plain_key(variant, drop_articles=True))

    for book in normalized_targets:
        manifest_id = str(book.get("id") or "")
        original_title = str(book.get("title") or "")
        author = str(book.get("author") or "")
        original_key = (original_title.casefold(), author.casefold())
        if original_key in seen_title_author:
            decisions.append({
                "manifest_id": manifest_id,
                "title": original_title,
                "author": author,
                "status": "skipped",
                "reason": "duplicate title/author already selected from another manifest row",
            })
            continue
        seen_title_author.add(original_key)

        skip_reason = SKIPPED_SOURCE_REPAIRS.get((original_title, author))
        if skip_reason:
            decisions.append({
                "manifest_id": manifest_id,
                "title": original_title,
                "author": author,
                "status": "skipped",
                "reason": skip_reason,
            })
            continue

        repair = SOURCE_REPAIRS.get((original_title, author))
        if not repair:
            decisions.append({
                "manifest_id": manifest_id,
                "title": original_title,
                "author": author,
                "status": "skipped",
                "reason": "no verified source repair configured",
            })
            continue

        try:
            apply_source_repair(book, repair)
            variants = title_variants({"title": original_title, "author": author}, repair)
            source = load_source_text(importer, book, source_cache)
            start_index = find_start_index(source.lines, variants)
            if start_index is None:
                raise ValueError(f"story heading not found for variants: {', '.join(variants)}")
            offset = body_start_offset(source.lines, start_index, author)
            body_start = start_index + 1 + offset
            end_index = find_end_index(
                importer,
                source.lines,
                body_start,
                source_known_keys.get(source_key(book), set()),
                repair,
            )
            range_lines = source.lines[body_start:end_index]
            extracted = "\n".join(range_lines).strip()
            extracted_words = word_count(importer, extracted)
            if extracted_words < 700:
                raise ValueError(f"extracted story range too short: {extracted_words} words")
            if extracted_words > 40000:
                raise ValueError(f"extracted story range too large: {extracted_words} words")
            if re.search(r"(?i)\b(project gutenberg|gutenberg\.org|pglaf|distributed proofreaders)\b", extracted):
                raise ValueError("source boilerplate remains inside extracted story range")

            text_slug = importer.slugify(f"{manifest_id}-{book.get('title')}", fallback=f"book-{len(selected) + 1}")
            prepared_text_path = text_dir / f"{text_slug}.txt"
            prepared_text_path.write_text(extracted, encoding="utf-8")

            chapter_rules = book.get("chapter_rules") if isinstance(book.get("chapter_rules"), dict) else {}
            chapter_rules["force_single_chapter"] = True
            book["chapter_rules"] = chapter_rules
            book["prepared_text_path"] = str(prepared_text_path)
            book["text_extraction"] = {
                "start_marker": source.lines[start_index].strip(),
                "start_occurrence": "last",
                "include_start_marker": False,
                "body_start_offset": offset,
            }
            if end_index is not None:
                book["text_extraction"]["end_marker"] = source.lines[end_index].strip()
            book["minimum_word_count"] = minimum_for_extracted(extracted_words)
            book["import_notes"] = [
                f"Generated from manifest row {manifest_id}.",
                "Single-story range extracted from verified source for reader-ready draft upload.",
            ]
            selected.append(book)
            decisions.append({
                "manifest_id": manifest_id,
                "title": book.get("title"),
                "original_title": original_title,
                "author": author,
                "status": "selected",
                "source_url": book.get("source_url"),
                "download_url": source.download_log.get("download_url"),
                "start_marker": book["text_extraction"]["start_marker"],
                "end_marker": book["text_extraction"].get("end_marker", ""),
                "word_count": extracted_words,
                "minimum_word_count": book["minimum_word_count"],
            })
            print(f"selected {manifest_id}: {book.get('title')} ({extracted_words} words)")
        except Exception as exc:  # noqa: BLE001 - report and continue with other books
            decisions.append({
                "manifest_id": manifest_id,
                "title": original_title,
                "author": author,
                "status": "skipped",
                "source_url": book.get("source_url"),
                "reason": str(exc),
            })
            print(f"skipped {manifest_id}: {original_title} - {exc}")

    manifest_path = out_dir / "gutenberg_collection_extracted_manifest.json"
    report_path = out_dir / "gutenberg_collection_extraction_report.json"
    manifest_payload = {"all_or_nothing": False, "books": selected}
    report_payload = {
        "generated_at": now_iso(),
        "source_manifest": str(args.manifest),
        "dedupe_report": str(args.dedupe_report),
        "final_report": str(args.final_report),
        "target_case_count": len(target_ids),
        "unique_title_author_count": len(seen_title_author),
        "selected_count": len(selected),
        "skipped_count": len([item for item in decisions if item.get("status") == "skipped"]),
        "selected_source_distribution": dict(Counter(item.get("source_url", "") for item in selected)),
        "decisions": decisions,
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest {manifest_path}")
    print(f"report {report_path}")
    print(f"selected {len(selected)}; skipped {report_payload['skipped_count']}; target cases {len(target_ids)}")
    return 0 if selected else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dedupe-report", type=Path, default=DEFAULT_DEDUPE_REPORT)
    parser.add_argument("--final-report", type=Path, default=DEFAULT_FINAL_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.manifest = args.manifest.expanduser().resolve()
    args.dedupe_report = args.dedupe_report.expanduser().resolve()
    args.final_report = args.final_report.expanduser().resolve()
    args.output_dir = args.output_dir.expanduser().resolve()
    return build_manifest(args)


if __name__ == "__main__":
    raise SystemExit(main())
