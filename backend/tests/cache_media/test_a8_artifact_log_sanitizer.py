from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("a8_sanitizer", ROOT / "scripts/cache_media/sanitize_a8_artifact_logs.py")
sanitizer = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(sanitizer)


def test_sanitizer_redacts_runner_forms_preserves_suffixes_and_is_idempotent():
    source = """/home/runner/work/repo/repo/backend/server.py:123\n/__w/repo/repo/frontend/x.js:2\n/opt/hostedtoolcache/Python/3.11/x\n/private/tmp/a8/x\n/Users/example/project/a.py\nD:\\a\\repo\\repo\\x.py\nC:\\Users\\example\\x\nhttps://example.test/path\nsha256:0123456789abcdef\n"""
    first, counts = sanitizer.sanitize_text(source)
    second, repeat = sanitizer.sanitize_text(first)
    assert first == second and not repeat
    assert counts and "<REPO_ROOT>/backend/server.py:123" in first
    assert "https://example.test/path" in first and "sha256:0123456789abcdef" in first
    assert not any(token in first for token in ("/home/runner", "/__w/", "/opt/hostedtoolcache", "/private/tmp", "/Users/", "D:\\a\\", "C:\\Users\\"))


def test_sanitizer_recurses_json_strings_without_changing_numeric_values():
    clean, _ = sanitizer.sanitize_json({"trace": ["/home/runner/work/repo/repo/backend/server.py:7"], "p95": 12.5})
    assert clean["trace"] == ["<REPO_ROOT>/backend/server.py:7"]
    assert clean["p95"] == 12.5
