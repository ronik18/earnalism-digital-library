from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("repair_open_boat_source_omission.py")
SPEC = importlib.util.spec_from_file_location("repair_open_boat_source_omission", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_official_phrase_and_checksums_are_explicitly_bound() -> None:
    assert MODULE.OFFICIAL_SOURCE_URL.endswith("/45524/pg45524.txt")
    assert MODULE.OFFICIAL_DOWNLOAD_SHA256 == "0ebacd153c0ed8e37227d5a41e01da7cee5723ed50b29a15da9e824161793840"
    assert "clumsy cork contrivance" in MODULE.CANONICAL
    assert "get even the almost stove-like" in MODULE.CORRUPT


def test_plan_repairs_only_the_exact_omission() -> None:
    replacements = MODULE.plan()
    raw = replacements[MODULE.RAW_PATH].decode("utf-8")
    assert MODULE.CORRUPT_RAW not in raw
    assert raw.count(MODULE.CANONICAL_RAW) == 1
    assert MODULE.sha256_text(raw) == MODULE.EXPECTED_REPAIRED_RAW_SHA256
    assert (
        MODULE.sha256_text(raw.rstrip())
        == MODULE.EXPECTED_REPAIRED_RAW_CONTENT_SHA256
    )
