from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("prepare_english_25_title_batch.py")
SPEC = importlib.util.spec_from_file_location("prepare_english_25_title_batch", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_batch_plan_has_unique_canonical_slugs_and_two_female_voices():
    plans = MODULE.TITLE_PLANS
    assert len(plans) == 25
    assert len({plan.slug for plan in plans}) == 25
    assert {plan.slug for plan in plans if plan.voice == "hf_alpha"} == {
        "a-white-heron",
        "the-enchanted-april",
    }
    assert any(plan.slug == "jekyll-and-hyde" for plan in plans)
    assert not any(
        plan.slug == "the-strange-case-of-dr-jekyll-and-mr-hyde" for plan in plans
    )


def test_public_book_normalization_removes_every_historical_audio_pointer():
    source = {
        "formats": ["Ebook", "Audiobook"],
        "audio_enabled": True,
        "audiobook_enabled": True,
        "generate_audiobook": True,
        "audiobook_provider": "historical_mapped_assets",
        "audiobook_voice": "old",
        "audio_asset_slug": "old",
        "audiobook": {"url": "https://example.invalid/book.mp3"},
        "audiobook_assets": {"mp3": "https://example.invalid/book.mp3"},
        "audiobook_assets_updated_at": "old",
    }
    result = MODULE.normalize_public_book(source)
    assert result["formats"] == ["Ebook"]
    assert result["audio_enabled"] is False
    assert result["audiobook_enabled"] is False
    assert result["generate_audiobook"] is False
    assert result["audiobook_provider"] == ""
    assert result["audiobook_voice"] == ""
    assert result["audio_asset_slug"] == ""
    assert "audiobook" not in result
    assert "audiobook_assets" not in result
    assert "audiobook_assets_updated_at" not in result


def test_source_normalization_preserves_the_approved_india_territory():
    result = MODULE.normalize_source(
        {"slug": "example"},
        {
            "author_name": "Example Author",
            "author_death_year": 1900,
            "original_publication_year": 1901,
            "rights_basis": "Public domain.",
            "verified_at": "2026-08-15T00:00:00Z",
        },
    )
    assert result["publication_region"] == "IN"


def test_existing_approved_cover_is_not_replaced():
    source = {
        "cover_url": "https://cdn.example.test/front.webp",
        "cover_image_url": "https://cdn.example.test/front.webp",
    }
    assert MODULE.assign_generated_cover(source, "not-a-real-slug") == source


def test_rights_parser_uses_basis_and_download_timestamp_fallbacks(tmp_path):
    note = tmp_path / "source-rights.md"
    note.write_text(
        "\n".join(
            [
                "# Source Rights Note",
                "- Author: Robert Louis Stevenson",
                "- Author death year: 1894",
                "- Source URL: https://example.invalid/source",
            ]
        ),
        encoding="utf-8",
    )
    source = {
        "rights_basis": "Author died 1894. Original publication 1886. Public domain.",
        "downloaded_at": "2026-07-01T10:36:20Z",
    }
    result = MODULE.parse_rights_note(note, source)
    assert result["author_death_year"] == 1894
    assert result["original_publication_year"] == 1886
    assert result["verified_at"] == "2026-07-01T10:36:20Z"


def test_checksum_manifest_excludes_itself_and_covers_managed_files(tmp_path):
    (tmp_path / "chapters").mkdir()
    (tmp_path / "public_book.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "chapters" / "chapter-001.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "checksum_manifest.json").write_text("{}\n", encoding="utf-8")
    replacement = MODULE.json_bytes({"audio_enabled": False})
    manifest = MODULE.checksum_manifest(
        tmp_path,
        {tmp_path / "public_book.json": replacement},
        "2026-08-15T00:00:00Z",
    )
    rows = {row["file"]: row["sha256"] for row in manifest["files"]}
    assert set(rows) == {"public_book.json", "chapters/chapter-001.json"}
    assert rows["public_book.json"] == MODULE.sha256_bytes(replacement)
    assert json.loads(replacement)["audio_enabled"] is False


def test_shared_colab_notebook_defaults_are_private_and_stop_before_full_generation():
    notebook = json.loads(
        (MODULE.ROOT / "colab" / "Earnalism_Audiobook_Pipeline.ipynb").read_text(
            encoding="utf-8"
        )
    )
    source = "".join(
        line
        for cell in notebook["cells"]
        for line in cell.get("source", [])
        if cell.get("cell_type") == "code"
    )
    assert 'BOOK_SLUG = ""' in source
    assert 'VOICE = ""' in source
    assert "PERSIST_TO_GOOGLE_DRIVE = True" in source
    assert "GO_LIVE_ENABLED = False" in source
    assert 'B2_AUDIO_OBJECT_KEY = ""' in source
    assert "OWNER_FULL_GENERATION_APPROVED = False" in source
    assert "OWNER_PUBLIC_RELEASE_INTENT = False" in source
    assert "Stop after the six-sample pilot" in source
    assert all(cell.get("outputs", []) == [] for cell in notebook["cells"] if cell.get("cell_type") == "code")
