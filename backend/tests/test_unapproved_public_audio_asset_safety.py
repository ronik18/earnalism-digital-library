import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTROLLED_ROOT = ROOT / "backend" / "data" / "controlled_publications"
AUDIO_KEYS = ("audiobook", "audiobook_assets", "audio_assets", "audio_url", "audiobook_url")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def public_urls(value):
    if isinstance(value, str):
        return [value] if value.startswith(("https://", "http://")) else []
    if isinstance(value, dict):
        return [url for item in value.values() for url in public_urls(item)]
    if isinstance(value, list):
        return [url for item in value for url in public_urls(item)]
    return []


def audio_release_approved(approval: dict, public_book: dict) -> bool:
    return (
        approval.get("audio_public_release") == "PUBLIC_AUDIO_RELEASE_APPROVED"
        and approval.get("audiobook_enabled") is True
        and public_book.get("audio_enabled") is True
        and public_book.get("audiobook_enabled") is True
    )


def test_unapproved_controlled_publications_expose_no_direct_audio_urls():
    violations = {}
    for public_path in CONTROLLED_ROOT.glob("*/public_book.json"):
        approval_path = public_path.parent / "approval_evidence.json"
        approval = read_json(approval_path) if approval_path.exists() else {}
        public_book = read_json(public_path)
        if audio_release_approved(approval, public_book):
            continue
        urls = [
            url
            for key in AUDIO_KEYS
            for url in public_urls(public_book.get(key))
        ]
        if urls:
            violations[public_path.parent.name] = len(urls)
    assert violations == {}


def test_known_approved_audiobooks_retain_provider_assets():
    for slug in ("book-2b9853ec52", "a-ghost-story"):
        title_dir = CONTROLLED_ROOT / slug
        approval = read_json(title_dir / "approval_evidence.json")
        public_book = read_json(title_dir / "public_book.json")
        assert audio_release_approved(approval, public_book)
        assert str(public_book["audiobook_assets"]["mp3"]).startswith("https://")


def test_d19_failed_qa_packet_is_explicitly_audio_hidden():
    title_dir = CONTROLLED_ROOT / "book-d19e96859f"
    approval = read_json(title_dir / "approval_evidence.json")
    public_book = read_json(title_dir / "public_book.json")

    assert approval["audio_public_release"] == "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
    assert approval["audiobook_enabled"] is False
    assert public_book["audio_enabled"] is False
    assert public_book["audiobook_enabled"] is False
    assert public_book["generate_audiobook"] is False
    assert public_book["audiobook_assets"] == {}
    assert public_book["audiobook"] == {}
    assert not [
        url
        for key in AUDIO_KEYS
        for url in public_urls(public_book.get(key))
    ]
