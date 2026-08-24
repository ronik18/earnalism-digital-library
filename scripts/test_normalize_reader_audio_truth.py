from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import normalize_reader_audio_truth as normalizer


def test_normalizer_is_explicit_and_preserves_reader_content(tmp_path: Path):
    package = tmp_path / "reader-only"
    package.mkdir()
    chapter = package / "chapters"
    chapter.mkdir()
    (chapter / "chapter-001.json").write_text('{"content":"kept"}\n', encoding="utf-8")
    (package / "public_book.json").write_text(json.dumps({"audio_enabled": True, "audiobook_enabled": True, "audiobook_assets": {"mp3": "private"}}), encoding="utf-8")
    (package / "reader_manifest.json").write_text(json.dumps({"audio_enabled": True, "audiobook_enabled": True}), encoding="utf-8")
    (package / "approval_evidence.json").write_text(json.dumps({"audiobook_enabled": True, "audio_public_release": "PUBLIC_AUDIO_RELEASE_APPROVED"}), encoding="utf-8")
    (package / "checksum_manifest.json").write_text(json.dumps({"slug": "reader-only", "files": [
        {"file": "public_book.json", "sha256": ""},
        {"file": "reader_manifest.json", "sha256": ""},
        {"file": "approval_evidence.json", "sha256": ""},
        {"file": "chapters/chapter-001.json", "sha256": hashlib.sha256((chapter / "chapter-001.json").read_bytes()).hexdigest()},
    ]}), encoding="utf-8")

    result = normalizer.normalize_slug(tmp_path, "reader-only", apply=True)

    assert result["applied"] is True
    assert json.loads((package / "public_book.json").read_text(encoding="utf-8"))["audio_enabled"] is False
    assert json.loads((package / "approval_evidence.json").read_text(encoding="utf-8"))["audiobook_enabled"] is False
    assert (chapter / "chapter-001.json").read_text(encoding="utf-8") == '{"content":"kept"}\n'
    checksums = json.loads((package / "checksum_manifest.json").read_text(encoding="utf-8"))
    assert all(row["sha256"] for row in checksums["files"])
