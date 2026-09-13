#!/usr/bin/env python3
"""Integrate owner-supplied Agentic AI chapter JSON without importing its private handoff."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "agentic-ai-with-python"
ARTIFACT_ROOTS = (ROOT / "data" / "controlled_publications" / SLUG, ROOT / "backend" / "data" / "controlled_publications" / SLUG)


def dump(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def chapter_inputs(replacement_root: Path) -> list[dict]:
    expected = load(replacement_root / "EXPECTED_MANUSCRIPT.json")
    rows = expected.get("chapters") or expected.get("selected_chapters") or []
    by_id = {str(row.get("id") or row.get("chapter_id")): row for row in rows if isinstance(row, dict)}
    chapters: list[dict] = []
    for order in range(1, 15):
        chapter_id = f"chapter-{order:03d}"
        raw = load(replacement_root / "manuscript" / "chapters" / f"{chapter_id}.json")
        if raw.get("id") != chapter_id or int(raw.get("order") or 0) != order or not isinstance(raw.get("content"), str):
            raise ValueError(f"Invalid replacement chapter: {chapter_id}")
        content_hash = sha(raw["content"])
        row = by_id.get(chapter_id, {})
        expected_hash = str(row.get("content_sha256") or row.get("content_hash") or row.get("sha256") or "")
        if expected_hash and expected_hash != content_hash:
            raise ValueError(f"Replacement content hash mismatch: {chapter_id}")
        raw["content_hash"] = content_hash
        raw["processing_status"] = "ready"
        chapters.append(raw)
    return chapters


def update_root(artifact: Path, chapters: list[dict], generated_at: str) -> None:
    public = load(artifact / "public_book.json")
    reader = load(artifact / "reader_manifest.json")
    source = load(artifact / "source_evidence.json")
    approval = load(artifact / "approval_evidence.json")
    if public.get("slug") != SLUG or reader.get("slug") != SLUG or approval.get("audiobook_enabled") is not False:
        raise ValueError(f"Unexpected reader-only artifact state: {artifact}")
    old_reader = {item.get("id"): item for item in reader.get("chapters", [])}
    chapter_meta = []
    for item in chapters:
        content = item["content"]
        word_count = len(content.replace("<", " <").replace(">", "> ").split())
        old = old_reader.get(item["id"], {})
        chapter_meta.append({"id": item["id"], "order": item["order"], "title": item["title"], "word_count": word_count, "reading_minutes": max(1, round(word_count / 220)), "is_preview": old.get("is_preview") is True, "has_images": False, "image_count": 0, "language_hint": "en", "processing_status": "ready", "processing_warnings": []})
    content_hash = sha(json.dumps([{key: item[key] for key in ("id", "order", "title", "content_hash")} for item in chapters], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    provenance_hash = sha(json.dumps({"slug": SLUG, "content_hash": content_hash, "revision": "owner-authorized-2026-09-12"}, sort_keys=True))
    public.update({"chapters": chapter_meta, "estimated_reading_time": sum(item["reading_minutes"] for item in chapter_meta), "content_hash": content_hash, "provenance_hash": provenance_hash, "audio_enabled": False, "audiobook_enabled": False, "generate_audiobook": False, "audiobook_assets": {}})
    reader.update({"chapters": chapter_meta, "chapter_count": 14, "preview_chapter_ids": [item["id"] for item in chapter_meta if item["is_preview"]], "audio_enabled": False, "audiobook_enabled": False})
    source.update({"content_hash": content_hash, "provenance_hash": provenance_hash, "reader_revision": {"revision": "owner-authorized-2026-09-12", "chapter_count": 14, "selected_content_sha256": {item["id"]: item["content_hash"] for item in chapters}, "handoff_approval_fields_not_imported": True}})
    for item in chapters:
        (artifact / "chapters" / f"{item['id']}.json").write_bytes(dump(item))
    (artifact / "public_book.json").write_bytes(dump(public))
    (artifact / "reader_manifest.json").write_bytes(dump(reader))
    (artifact / "source_evidence.json").write_bytes(dump(source))
    from backend.publication_manifest import build_manifest, validate_manifest
    manifest = build_manifest(artifact, publish_approved=True, generated_at=generated_at)
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError(f"Publication manifest rejected: {errors}")
    (artifact / "publication_manifest.json").write_bytes(dump(manifest))
    files = []
    for file in sorted(path for path in artifact.rglob("*.json") if path.name not in {"checksum_manifest.json", "publication_manifest.json"}):
        files.append({"file": file.relative_to(artifact).as_posix(), "sha256": sha(file.read_bytes())})
    (artifact / "checksum_manifest.json").write_bytes(dump({"slug": SLUG, "generated_at": generated_at, "files": files}))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replacement-root", type=Path, required=True)
    args = parser.parse_args()
    chapters = chapter_inputs(args.replacement_root.resolve())
    generated_at = datetime.now(timezone.utc).isoformat()
    for artifact in ARTIFACT_ROOTS:
        update_root(artifact, chapters, generated_at)
    if any((ARTIFACT_ROOTS[0] / item).read_bytes() != (ARTIFACT_ROOTS[1] / item).read_bytes() for item in ["public_book.json", "reader_manifest.json", "source_evidence.json", "publication_manifest.json", "checksum_manifest.json"]):
        raise ValueError("Publication roots are not byte-identical after integration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
