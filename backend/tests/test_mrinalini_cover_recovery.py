from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MRINALINI_PACKET = ROOT / "backend" / "data" / "controlled_publications" / "mrinalini"
GINNI_PACKET = ROOT / "backend" / "data" / "controlled_publications" / "book-d19e96859f"
COVER_ALIAS_FIELDS = (
    "cover_url",
    "cover_image_url",
    "coverImage",
    "cover_image",
    "thumbnail_url",
    "front_cover_url",
    "back_cover_url",
    "back_cover_image_url",
    "backCoverImage",
    "back_cover_thumbnail_url",
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_mrinalini_fallback_artifact_does_not_borrow_ginnis_cover_pair():
    mrinalini = read_json(MRINALINI_PACKET / "public_book.json")
    ginni = read_json(GINNI_PACKET / "public_book.json")

    assert mrinalini["slug"] == "mrinalini"
    assert mrinalini["author"] == "বঙ্কিমচন্দ্র চট্টোপাধ্যায়"
    assert len(mrinalini["chapters"]) == 46
    assert mrinalini["cover_status"] == "DESIGNED_PLACEHOLDER_NO_SAFE_LOCAL_COVER"
    assert all(not mrinalini.get(field) for field in COVER_ALIAS_FIELDS)
    assert "ff96c6fb" not in json.dumps(mrinalini, ensure_ascii=False)
    assert "89e10113" not in json.dumps(mrinalini, ensure_ascii=False)

    assert ginni["slug"] == "book-d19e96859f"
    assert ginni["author"] == "রবীন্দ্রনাথ ঠাকুর"
    assert len(ginni["chapters"]) == 1
    assert "ff96c6fb" in ginni["cover_image_url"]
    assert "ff96c6fb" in ginni["back_cover_image_url"]


def test_mrinalini_fallback_artifact_checksum_tracks_the_corrected_cover_truth():
    manifest = read_json(MRINALINI_PACKET / "checksum_manifest.json")
    entries = {entry["file"]: entry["sha256"] for entry in manifest["files"]}
    public_book = MRINALINI_PACKET / "public_book.json"

    assert entries["public_book.json"] == hashlib.sha256(public_book.read_bytes()).hexdigest()
