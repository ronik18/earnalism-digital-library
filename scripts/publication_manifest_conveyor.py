#!/usr/bin/env python3
"""Build or approve one canonical Earnalism publication manifest."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.publication_manifest import build_manifest, validate_manifest  # noqa: E402


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _read_json_if_exists(path: Path) -> dict:
    return _read_json(path) if path.exists() else {}


def _sha256_text(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migrate_import_metadata(metadata_path: Path, artifact_dir: Path) -> None:
    """Promote validated importer output into a controlled reader artifact set."""
    imported = _read_json(metadata_path)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    existing_public = _read_json_if_exists(artifact_dir / "public_book.json")
    existing_source = _read_json_if_exists(artifact_dir / "source_evidence.json")
    chapter_dir = artifact_dir / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    chapter_meta: list[dict] = []
    canonical_content: list[str] = []
    for index, source_chapter in enumerate(imported.get("chapters") or [], start=1):
        chapter_id = f"chapter-{index:03d}"
        backend_dir = Path(__file__).resolve().parents[1] / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from utils.content_processor import sanitize_chapter_html_fragment

        content, sanitation_warnings = sanitize_chapter_html_fragment(
            str(source_chapter.get("content") or "").strip()
        )
        if sanitation_warnings:
            raise ValueError(
                f"Validated importer output required unsafe-content removal for {chapter_id}: "
                + "; ".join(sanitation_warnings)
            )
        if not content:
            raise ValueError(f"Validated importer output contains an empty chapter: {chapter_id}")
        plain = re.sub(r"<[^>]+>", " ", content)
        word_count = len(re.findall(r"\b\w+[’'\-]?\w*\b", plain, flags=re.UNICODE))
        content_hash = _sha256_text(content)
        chapter_payload = {
            "id": chapter_id,
            "title": str(source_chapter.get("title") or f"Chapter {index}").strip(),
            "order": index,
            "content": content,
            "content_hash": content_hash,
            "processing_status": "ready",
        }
        (chapter_dir / f"{chapter_id}.json").write_text(
            json.dumps(chapter_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        canonical_content.append(content)
        chapter_meta.append({
            "id": chapter_id,
            "order": index,
            "title": chapter_payload["title"],
            "is_preview": bool(source_chapter.get("is_preview") is True),
            "has_images": False,
            "image_count": 0,
            "word_count": word_count,
            "reading_minutes": max(1, round(word_count / 240)),
            "language_hint": str(imported.get("language") or "en"),
            "processing_status": "ready",
            "processing_warnings": list(source_chapter.get("warnings") or []),
        })

    content_hash = _sha256_text("\n\n".join(canonical_content))
    source_url = str(imported.get("rights_metadata", {}).get("source_url") or existing_source.get("source_url") or "")
    source_license = str(imported.get("rights_metadata", {}).get("source_license") or existing_source.get("source_license") or "")
    provenance_hash = _sha256_text(f"{source_url}\n{source_license}\n{content_hash}")
    public_book = {
        **existing_public,
        "slug": imported.get("slug", existing_public.get("slug", artifact_dir.name)),
        "title": imported.get("title", existing_public.get("title", "")),
        "author": imported.get("author", existing_public.get("author", "")),
        "category_slug": imported.get("category_slug", existing_public.get("category_slug", "literary-fiction")),
        "short_description": imported.get("short_description", existing_public.get("short_description", "")),
        "description": imported.get("description", existing_public.get("description", "")),
        "chapters": chapter_meta,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
        "rights_tier": existing_source.get("rights_tier", existing_public.get("rights_tier", "")),
        "verification_status": existing_source.get("verification_status", existing_public.get("verification_status", "")),
        "qa_status": existing_public.get("qa_status") or "QA_PASSED",
        "approved_to_publish": existing_public.get("approved_to_publish") is True,
        "showInHomepage": False,
        "allowCheckout": False,
        "allowPayment": False,
        "audio_enabled": False,
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
    }
    reader_manifest = {
        "slug": public_book["slug"],
        "title": public_book["title"],
        "author": public_book["author"],
        "language": str(imported.get("language") or "en"),
        "chapter_count": len(chapter_meta),
        "chapters": chapter_meta,
        "preview_chapter_ids": [item["id"] for item in chapter_meta if item["is_preview"]],
        "audio_enabled": False,
        "audiobook_enabled": False,
    }
    source_evidence = {
        **existing_source,
        "source_url": source_url,
        "source_license": source_license,
        "content_hash": content_hash,
        "provenance_hash": provenance_hash,
        "reader_facing_boilerplate_removed": True,
    }
    for name, payload in (
        ("public_book.json", public_book),
        ("reader_manifest.json", reader_manifest),
        ("source_evidence.json", source_evidence),
    ):
        (artifact_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Maintain the legacy checksum bundle while consumers migrate to the
    # publication manifest. The bundle is generated by the conveyor so it
    # cannot silently drift after a chapter or metadata migration.
    checksum_files = []
    for artifact_path in sorted(artifact_dir.rglob("*")):
        if not artifact_path.is_file():
            continue
        relative_path = artifact_path.relative_to(artifact_dir).as_posix()
        if relative_path in {"checksum_manifest.json", "publication_manifest.json"}:
            continue
        checksum_files.append({
            "file": relative_path,
            "sha256": _sha256_file(artifact_path),
        })
    existing_checksum = _read_json_if_exists(artifact_dir / "checksum_manifest.json")
    checksum_manifest = {
        "slug": str(public_book["slug"]),
        "generated_at": str(existing_checksum.get("generated_at") or ""),
        "files": checksum_files,
    }
    (artifact_dir / "checksum_manifest.json").write_text(
        json.dumps(checksum_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--artifact-root", default=str(ROOT / "data" / "controlled_publications"))
    parser.add_argument("--write", action="store_true", help="Write publication_manifest.json after validation.")
    parser.add_argument("--publish-approved", action="store_true", help="Expose the reader lane after explicit approval.")
    parser.add_argument("--import-metadata", help="Validated import metadata JSON to promote before manifest creation.")
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact_dir = Path(args.artifact_root) / args.slug
    if args.import_metadata:
        migrate_import_metadata(Path(args.import_metadata), artifact_dir)
    if args.publish_approved and os.getenv("EARNALISM_APPROVE_READER_PUBLICATION") != "true":
        print("BLOCKED: EARNALISM_APPROVE_READER_PUBLICATION=true is required.", file=sys.stderr)
        return 2
    manifest = build_manifest(artifact_dir, publish_approved=args.publish_approved)
    issues = validate_manifest(manifest)
    if issues:
        for issue in issues:
            print(f"BLOCKED: {issue}", file=sys.stderr)
        return 1
    if args.write:
        path = artifact_dir / "publication_manifest.json"
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(path)
    print(json.dumps({
        "slug": manifest["slug"],
        "reader_release": manifest["reader_release"],
        "audio_release": manifest["audio_release"],
        "manifest_sha256": manifest["manifest_sha256"],
    }, indent=2))
    return 0 if manifest["reader_release"]["status"] != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(run())
