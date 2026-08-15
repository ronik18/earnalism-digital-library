from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("render_private_reader_preview.py")
SPEC = importlib.util.spec_from_file_location("render_private_reader_preview", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_opening_blocks_rejects_picture_placeholders() -> None:
    with pytest.raises(ValueError, match="picture placeholder"):
        MODULE.opening_blocks("[Picture: decorative art]\n\nNarrative.", 100)


def test_happy_prince_cross_title_boundary_is_rejected() -> None:
    with pytest.raises(ValueError, match="Cross-title boundary"):
        MODULE.assert_single_title_boundary(
            "the-happy-prince",
            "The Happy Prince shall praise me.\n\nThe Nightingale and the Rose.",
        )


def test_unrelated_narrative_passes_boundary_guard() -> None:
    MODULE.assert_single_title_boundary("a-white-heron", "A complete narrative.")


def private_pending_payloads() -> tuple[dict, dict, dict, dict]:
    public = {
        "isPublic": False,
        "isLive": False,
        "showInPublicLibrary": False,
        "showInHomepage": False,
        "allowPublicReading": False,
        "is_published": False,
        "audio_enabled": False,
        "audiobook_enabled": False,
    }
    source = {
        "verification_status": "approved",
        "qa_status": "READY_FOR_APPROVAL",
        "publication_region": "IN",
        "reader_facing_boilerplate_removed": True,
    }
    approval = {
        "approved_to_publish": False,
        "qa_status": "READY_FOR_APPROVAL",
        "reader_public_release": "READER_APPROVAL_REQUIRED",
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
    }
    reader = {"audio_enabled": False, "audiobook_enabled": False}
    return public, source, approval, reader


def test_safe_private_preapproval_candidate_can_render() -> None:
    MODULE.assert_private_preview_state(*private_pending_payloads())


def test_private_preapproval_candidate_must_remain_hidden() -> None:
    public, source, approval, reader = private_pending_payloads()
    public["isPublic"] = True
    with pytest.raises(ValueError, match="safe private gate"):
        MODULE.assert_private_preview_state(public, source, approval, reader)


def test_private_preapproval_candidate_cannot_expose_audio() -> None:
    public, source, approval, reader = private_pending_payloads()
    public["audio_enabled"] = True
    with pytest.raises(ValueError, match="Unapproved audio"):
        MODULE.assert_private_preview_state(public, source, approval, reader)


def test_explicit_private_cover_override_is_supported(tmp_path: Path) -> None:
    cover = tmp_path / "front-cover.png"
    cover.write_bytes(b"private cover bytes")
    assert MODULE.resolve_cover("missing-local-cover", cover) == cover.resolve()
