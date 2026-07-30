import argparse
import json
import shutil
from pathlib import Path

import pytest

import open_source_audiobook_onboarding as onboarding
import repair_tell_tale_manuscript_whitespace as repair


REPO_ROOT = Path(__file__).resolve().parents[1]


def _args(tmp_path: Path, *, check: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        primary_root=tmp_path / "data/controlled_publications",
        backend_root=tmp_path / "backend/data/controlled_publications",
        canonical_manuscript=(
            tmp_path
            / "internal/audiobook_lab/sprint1_publication/source_manuscripts"
            / repair.SLUG
            / "clean_manuscript.txt"
        ),
        report=tmp_path / "reconciliation.json",
        generated_at="2026-07-30T00:00:00Z",
        check=check,
    )


def _copy_repaired_packet(tmp_path: Path) -> argparse.Namespace:
    args = _args(tmp_path)
    for relative_root in (
        Path("data/controlled_publications"),
        Path("backend/data/controlled_publications"),
    ):
        source = REPO_ROOT / relative_root / repair.SLUG
        destination = tmp_path / relative_root / repair.SLUG
        shutil.copytree(source, destination)
    source_manuscript = (
        REPO_ROOT
        / "internal/audiobook_lab/sprint1_publication/source_manuscripts"
        / repair.SLUG
        / "clean_manuscript.txt"
    )
    args.canonical_manuscript.parent.mkdir(parents=True)
    shutil.copy2(source_manuscript, args.canonical_manuscript)
    return args


def _write_json(path: Path, payload: dict) -> None:
    path.write_bytes(repair.json_bytes(payload))


def _refresh_checksum(publication: Path, relative: str) -> None:
    manifest_path = publication / "checksum_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["files"]:
        if row["file"] == relative:
            row["sha256"] = repair.sha256_bytes(
                (publication / relative).read_bytes()
            )
            break
    _write_json(manifest_path, manifest)


def _restore_pre_repair_fixture(args: argparse.Namespace) -> None:
    for root in (args.primary_root, args.backend_root):
        publication = root / repair.SLUG
        chapter_path = publication / "chapters/chapter-001.json"
        chapter = json.loads(chapter_path.read_text(encoding="utf-8"))
        old_content = chapter["content"].replace("\n ", "\n\n ")
        assert old_content.count("\n\n ") == repair.EXPECTED_SOURCE_WRAP_REPAIRS
        assert repair.sha256_text(old_content) == repair.EXPECTED_OLD_CONTENT_SHA256
        chapter["content"] = old_content
        chapter["content_hash"] = repair.EXPECTED_OLD_CONTENT_SHA256
        chapter["sanitizedSha256"] = repair.EXPECTED_OLD_CONTENT_SHA256
        _write_json(chapter_path, chapter)

        old_content_hash = "295d3308f015f1233c4368286360ea19d7a7f314cfae96997ea1fea6b10c0771"
        for filename in ("public_book.json", "source_evidence.json"):
            path = publication / filename
            document = json.loads(path.read_text(encoding="utf-8"))
            document["content_hash"] = old_content_hash
            _write_json(path, document)
            _refresh_checksum(publication, filename)
        _refresh_checksum(publication, "chapters/chapter-001.json")
    args.canonical_manuscript.unlink()


def test_repairs_exact_historical_whitespace_artifact_and_preserves_truth(tmp_path):
    args = _copy_repaired_packet(tmp_path)
    _restore_pre_repair_fixture(args)
    before_truth = repair.audio_truth_snapshot(args.primary_root / repair.SLUG)

    report = repair.run(args)

    assert report["status"] == "CANONICAL_MANUSCRIPT_RECONCILED"
    assert report["source_wrap_artifacts_removed"] == 167
    assert report["prose_changed"] is False
    assert repair.sha256_bytes(args.canonical_manuscript.read_bytes()) == (
        repair.EXPECTED_CANONICAL_MANUSCRIPT_SHA256
    )
    assert repair.audio_truth_snapshot(args.primary_root / repair.SLUG) == before_truth
    repair.validate_mirrors(
        args.primary_root / repair.SLUG,
        args.backend_root / repair.SLUG,
    )


def test_repaired_packet_is_idempotent_and_checkable(tmp_path):
    args = _copy_repaired_packet(tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    repair.run(args)
    args.check = True
    checked = repair.run(args)

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file() and path != args.report
    }
    expected = {
        relative: payload
        for relative, payload in before.items()
        if tmp_path / relative != args.report
    }
    assert after == expected
    assert checked["check_mode"] is True


def test_refuses_any_substantive_prose_drift(tmp_path):
    args = _copy_repaired_packet(tmp_path)
    for root in (args.primary_root, args.backend_root):
        chapter_path = root / repair.SLUG / "chapters/chapter-001.json"
        chapter = json.loads(chapter_path.read_text(encoding="utf-8"))
        chapter["content"] = chapter["content"].replace("nervous", "calm", 1)
        _write_json(chapter_path, chapter)

    with pytest.raises(
        repair.ReconciliationError,
        match="unexpected controlled chapter content SHA-256",
    ):
        repair.run(args)


def test_audio_hidden_release_state_is_unchanged_in_repo():
    publication = REPO_ROOT / "data/controlled_publications" / repair.SLUG
    snapshot = repair.audio_truth_snapshot(publication)

    assert snapshot["approval_evidence.json"]["audiobook_enabled"] is False
    assert snapshot["approval_evidence.json"]["audio_public_release"] == (
        "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
    )
    assert snapshot["public_book.json"]["audiobook_enabled"] is False
    assert snapshot["public_book.json"]["generate_audiobook"] is False
    assert snapshot["reader_manifest.json"]["audiobook_enabled"] is False


def test_onboarding_now_matches_recovered_admin_manuscript_exactly(tmp_path):
    canonical_path = (
        REPO_ROOT
        / "internal/audiobook_lab/sprint1_publication/source_manuscripts"
        / repair.SLUG
        / "clean_manuscript.txt"
    )
    canonical = canonical_path.read_text(encoding="utf-8")
    body = canonical.removeprefix(f"{repair.TITLE}\n\n").rstrip("\n")
    book = {
        "slug": repair.SLUG,
        "title": repair.TITLE,
        "author": "Edgar Allan Poe",
        "is_published": True,
        "chapters": [
            {
                "id": "chapter-001",
                "order": 1,
                "title": repair.TITLE,
                "content": body,
            }
        ],
    }
    args = argparse.Namespace(
        output_dir=tmp_path / "out",
        public_audio_dir=tmp_path / "public",
        report_dir=tmp_path / "reports",
        controlled_publications_root=(
            REPO_ROOT / "data/controlled_publications"
        ),
        manifest_languages={repair.SLUG: "en"},
        skip_live_audio_assets=True,
        lang=None,
        max_chars=0,
        validate_only=False,
        dry_run=True,
        regenerate=False,
        copy_to_public=False,
        upload_to_cloudinary=False,
        english_provider="piper",
        bengali_provider="mms-tts",
        piper_binary="piper",
        piper_model="model.onnx",
        piper_config="model.onnx.json",
        piper_speaker="",
        piper_length_scale=1.08,
        english_chunk_chars=1100,
        bengali_chunk_chars=420,
        alignment_min_ratio=0.8,
        skip_alignment=True,
    )

    result = onboarding.generate_book(book, args)

    assert result.status == "DRY_RUN"
    assert result.source_reconciliation["status"] == "MATCH"
    assert result.source_reconciliation["live_sha256"] == (
        repair.EXPECTED_CANONICAL_MANUSCRIPT_SHA256
    )
    assert result.source_reconciliation["controlled_sha256"] == (
        repair.EXPECTED_CANONICAL_MANUSCRIPT_SHA256
    )
    assert result.controlled_release_truth["approved"] is False
