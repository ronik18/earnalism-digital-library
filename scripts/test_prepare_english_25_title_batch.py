from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest


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


def test_prepare_title_rejects_duplicate_approval_evidence(tmp_path, monkeypatch):
    artifact_root = tmp_path / "controlled"
    content_root = tmp_path / "content"
    artifact_dir = artifact_root / "duplicate-title"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "approval_evidence.json").write_text("{}\n", encoding="utf-8")
    (artifact_dir / "approval_evidence 2.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "CONTROLLED_ROOT", artifact_root)
    monkeypatch.setattr(MODULE, "CONTENT_ROOT", content_root)
    plan = MODULE.TitlePlan("Duplicate", "duplicate-title", "bm_george", "male")
    with pytest.raises(ValueError, match="exactly one canonical approval_evidence.json"):
        MODULE.prepare_title(plan, "2026-08-16T00:00:00Z")


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
    assert 'EXPECTED_REPO_COMMIT = ""' in source
    assert "PERSIST_TO_GOOGLE_DRIVE = True" in source
    assert 'drive.mount("/content/drive", force_remount=False)' in source
    assert 'Path("/content/drive/MyDrive/Earnalism/private_audiobook_attempts")' in source
    assert "GO_LIVE_ENABLED = False" in source
    assert 'B2_AUDIO_OBJECT_KEY = ""' in source
    assert "OWNER_FULL_GENERATION_APPROVED = False" in source
    assert "OWNER_PUBLIC_RELEASE_INTENT = False" in source
    assert "Stop after the six-sample pilot" in source
    assert 'RUN = OUTPUT_ROOT / f"{BOOK_SLUG}-kokoro-{VOICE}-{ATTEMPT_FINGERPRINT[:12]}"' in source
    assert source.index("ATTEMPT_FINGERPRINT =") < source.index("RUN = OUTPUT_ROOT")
    assert source.index("RUN = OUTPUT_ROOT") < source.index("SOURCE_PATH = RUN")
    assert 'SPLITTER_SCHEMA = "earnalism.quote_aware_sentence_splitter.v2"' in source
    assert '"splitter_schema": SPLITTER_SCHEMA' in source
    assert "split_pattern=SENTENCE_BOUNDARY_PATTERN" in source
    assert "Six distinct source blocks are required." in source
    assert "len(set(representative_source_hashes)) == 6" in source
    assert '"sample_set_sha256":representative_sample_set_sha256' in source
    assert 'earnalism.kokoro_representative_objective_qa.v2' in source
    assert all(cell.get("outputs", []) == [] for cell in notebook["cells"] if cell.get("cell_type") == "code")


def test_quote_aware_splitter_preserves_owl_creek_text_and_boundaries():
    chapter = json.loads(
        (
            MODULE.ROOT
            / "data"
            / "controlled_publications"
            / "an-occurrence-at-owl-creek-bridge"
            / "chapters"
            / "chapter-001.json"
        ).read_text(encoding="utf-8")
    )
    text = re.sub(r"\s+", " ", chapter["content"]).strip()
    boundary = re.compile(
        r"(?:(?<=[.!?])|(?<=[.!?][”’\"']))\s+(?=[“‘\"'A-Z0-9])"
    )
    unsplit = re.compile(r"[.!?][”’\"']\s+[“‘\"'A-Z0-9]")
    units = [row.strip() for row in boundary.split(text) if row.strip()]
    assert " ".join(units) == text
    assert len(units) == 201
    assert max(len(row.split()) for row in units) <= 80
    assert not any(unsplit.search(row) for row in units)
