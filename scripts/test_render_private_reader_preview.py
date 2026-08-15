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
