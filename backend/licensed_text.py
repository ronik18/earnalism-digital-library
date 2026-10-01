"""Optional, immutable attribution for licensed transcription layers only."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


def public_license_notice(package_dir):
    base = Path(package_dir)
    try:
        book = json.loads((base / "public_book.json").read_text())
        raw = (base / "license_notice.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != book.get("license_notice_sha256"):
            return None
        notice = json.loads(raw)
        if notice.get("schema_version") != "earnalism.text-license.v1" or notice.get("slug") != book.get("slug"):
            return None
        if notice.get("license") != "CC-BY-SA-4.0" or notice.get("license_url") != "https://creativecommons.org/licenses/by-sa/4.0/":
            return None
        if not all(isinstance(notice.get(k), str) and notice[k].strip() for k in ("attribution", "changes", "scope", "disclaimer")):
            return None
        for key in ("source_url", "contributors_url"):
            parsed = urlparse(notice.get(key, ""))
            if parsed.scheme != "https" or parsed.hostname not in {"bn.wikisource.org", "en.wikisource.org"}:
                return None
        chapters = sorted(book.get("chapters") or [], key=lambda c: c.get("order", 0))
        actual = []
        for meta in chapters:
            chapter = json.loads((base / "chapters" / (meta["id"] + ".json")).read_text())
            actual.append(hashlib.sha256(chapter["content"].encode()).hexdigest())
        if not actual or actual != notice.get("chapter_sha256"):
            return None
        return {key: notice[key] for key in ("schema_version", "slug", "license", "license_url", "attribution", "changes", "scope", "disclaimer", "source_url", "contributors_url")}
    except (OSError, ValueError, KeyError, TypeError):
        return None
