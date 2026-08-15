#!/usr/bin/env python3
"""Render a checksum-bound, local-only reader preview for owner approval."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_ROOT = ROOT / "data" / "controlled_publications"
FORBIDDEN_READER_FURNITURE = re.compile(
    r"Project Gutenberg|Here ends No\. Four of the Western Classics|"
    r"Tomoye Press|Paul Elder and Company",
    re.IGNORECASE,
)
PICTURE_PLACEHOLDER_RE = re.compile(r"\[\s*Picture\s*:", re.IGNORECASE)
KNOWN_CROSS_TITLE_BOUNDARIES = {
    "the-happy-prince": ("The Nightingale and the Rose.",),
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_controlled_package(artifact_dir: Path) -> str:
    duplicates = sorted(
        path.name
        for path in artifact_dir.glob("approval_evidence*.json")
        if path.name != "approval_evidence.json"
    )
    if duplicates:
        raise ValueError("Duplicate approval evidence is forbidden: " + ", ".join(duplicates))

    manifest_path = artifact_dir / "checksum_manifest.json"
    manifest = read_json(manifest_path)
    failures: list[str] = []
    for row in manifest.get("files") or []:
        relative = str(row.get("file") or "")
        if not relative or relative == manifest_path.name:
            failures.append(f"invalid checksum row: {relative!r}")
            continue
        target = artifact_dir / relative
        if not target.is_file():
            failures.append(f"{relative}: missing")
        elif sha256_file(target) != str(row.get("sha256") or ""):
            failures.append(f"{relative}: checksum mismatch")
    if failures:
        raise ValueError("Controlled checksum failure: " + "; ".join(failures))
    return sha256_file(manifest_path)


def assert_reader_gate(artifact_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    public = read_json(artifact_dir / "public_book.json")
    source = read_json(artifact_dir / "source_evidence.json")
    approval = read_json(artifact_dir / "approval_evidence.json")
    reader = read_json(artifact_dir / "reader_manifest.json")
    if source.get("verification_status") != "approved" or source.get("qa_status") != "QA_PASSED":
        raise ValueError("Source rights or QA is not approved")
    if source.get("publication_region") != "IN":
        raise ValueError("Preview territory must remain IN")
    if source.get("reader_facing_boilerplate_removed") is not True:
        raise ValueError("Reader sanitation is not approved")
    if approval.get("approved_to_publish") is not True:
        raise ValueError("Reader publication approval is absent")
    if approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_NOT_APPROVED":
        raise ValueError("Audio release truth is not safely hidden")
    if any(
        value is True
        for value in (
            public.get("audio_enabled"),
            public.get("audiobook_enabled"),
            public.get("generate_audiobook"),
            reader.get("audio_enabled"),
            reader.get("audiobook_enabled"),
        )
    ):
        raise ValueError("Unapproved audio is exposed")
    return public, source


def opening_blocks(text: str, word_limit: int) -> list[str]:
    if FORBIDDEN_READER_FURNITURE.search(text):
        raise ValueError("Reader-facing source furniture remains")
    if PICTURE_PLACEHOLDER_RE.search(text):
        raise ValueError("Reader-facing picture placeholder remains")
    blocks = [re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n\s*\n", text)]
    selected: list[str] = []
    count = 0
    for block in blocks:
        if not block:
            continue
        block_words = len(block.split())
        if selected and count + block_words > word_limit:
            break
        selected.append(block)
        count += block_words
    if not selected:
        raise ValueError("Opening preview is empty")
    return selected


def assert_single_title_boundary(slug: str, text: str) -> None:
    for marker in KNOWN_CROSS_TITLE_BOUNDARIES.get(slug, ()):
        if marker in text:
            raise ValueError(f"Cross-title boundary remains in {slug}: {marker}")


def render(slug: str, voice: str, output_root: Path, word_limit: int) -> dict[str, Any]:
    artifact_dir = CONTROLLED_ROOT / slug
    manifest_sha = assert_controlled_package(artifact_dir)
    public, source = assert_reader_gate(artifact_dir)
    chapters = sorted(
        (row for row in (public.get("chapters") or []) if isinstance(row, dict)),
        key=lambda row: int(row.get("order") or 0),
    )
    if not chapters:
        raise ValueError("No narrative chapter is available")
    chapter_path = artifact_dir / "chapters" / f"{chapters[0]['id']}.json"
    chapter = read_json(chapter_path)
    chapter_text = str(chapter.get("content") or "")
    assert_single_title_boundary(slug, chapter_text)
    blocks = opening_blocks(chapter_text, word_limit)
    cover = ROOT / "frontend" / "public" / "assets" / "books" / slug / "front-cover.webp"
    if not cover.is_file():
        raise FileNotFoundError(cover)

    binding = {
        "schema": "earnalism.private_reader_gate_binding.v1",
        "repository_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "slug": slug,
        "voice": voice,
        "controlled_manifest_sha256": manifest_sha,
        "source_content_hash": str(source.get("content_hash") or ""),
        "chapter_sha256": sha256_file(chapter_path),
        "cover_sha256": sha256_file(cover),
        "preview_text_sha256": sha256_bytes("\n\n".join(blocks).encode("utf-8")),
    }
    fingerprint = sha256_bytes(
        json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    title = str(public.get("title") or slug)
    author = str(public.get("author") or "")
    description = str(public.get("description") or "A private controlled-edition preview.")
    prose = "\n".join(f"<p>{html.escape(block)}</p>" for block in blocks)
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — private Earnalism reader gate</title>
<style>
:root{{color-scheme:dark;--ink:#f5efe2;--muted:#cfc2ad;--gold:#d6a84f}}*{{box-sizing:border-box}}
body{{margin:0;background:#080a0b;color:var(--ink);font-family:Georgia,'Times New Roman',serif}}
main{{width:min(1120px,100%);margin:auto;padding:clamp(18px,4vw,52px)}}
.masthead{{display:grid;grid-template-columns:minmax(210px,350px) 1fr;gap:clamp(24px,5vw,72px);align-items:center;padding:16px 0 48px}}
.cover{{width:100%;border-radius:18px;box-shadow:0 28px 80px #000b,0 0 0 1px #d6a84f55}}
.eyebrow{{color:var(--gold);letter-spacing:.24em;text-transform:uppercase;font:600 12px/1.5 system-ui,sans-serif}}
h1{{font-size:clamp(46px,8vw,98px);font-weight:400;line-height:.95;margin:.2em 0}}
.author{{color:var(--gold);font-size:clamp(21px,3vw,34px);letter-spacing:.08em;text-transform:uppercase}}
.deck{{color:var(--muted);font-size:clamp(20px,2.5vw,30px);line-height:1.45;max-width:28em}}
.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}}.badge{{border:1px solid #d6a84f66;border-radius:999px;padding:7px 11px;color:#e8d8b9;font:600 11px/1 system-ui,sans-serif;letter-spacing:.08em}}
article{{background:linear-gradient(180deg,#191713,#11100e);border:1px solid #d6a84f4d;border-radius:24px;padding:clamp(24px,6vw,74px);box-shadow:0 24px 70px #0008}}
article h2{{color:var(--gold);font-size:14px;letter-spacing:.22em;text-transform:uppercase;font-family:system-ui,sans-serif}}
article p{{font-size:clamp(19px,2.2vw,26px);line-height:1.75;margin:0 0 1.15em}}
.evidence{{margin-top:30px;padding-top:20px;border-top:1px solid #ffffff1d;color:#a99e8e;font:12px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere}}
@media(max-width:720px){{.masthead{{grid-template-columns:1fr}}.cover{{max-width:300px;margin:auto}}main{{padding:16px}}}}
</style></head><body><main><section class="masthead">
<img class="cover" src="{html.escape(cover.as_uri())}" alt="Private preview cover for {html.escape(title)}">
<div><div class="eyebrow">Earnalism · private reader gate</div><h1>{html.escape(title)}</h1><div class="author">{html.escape(author)}</div>
<p class="deck">{html.escape(description)}</p><div class="badges"><span class="badge">Reader gate</span><span class="badge">Voice: {html.escape(voice)}</span><span class="badge">Not public</span></div></div></section>
<article><h2>Controlled opening preview</h2>{prose}<div class="evidence">Reader-gate fingerprint: {fingerprint}<br>Controlled manifest SHA-256: {manifest_sha}<br>Preview text SHA-256: {binding['preview_text_sha256']}<br>Status: PRIVATE_PREVIEW_OWNER_APPROVAL_PENDING</div></article>
</main></body></html>"""

    destination = output_root / slug
    destination.mkdir(parents=True, exist_ok=True)
    preview_path = destination / "reader-preview.html"
    preview_path.write_text(document, encoding="utf-8")
    evidence = {
        **binding,
        "reader_gate_fingerprint": fingerprint,
        "preview_path": str(preview_path),
        "preview_sha256": sha256_file(preview_path),
        "preview_word_count": sum(len(block.split()) for block in blocks),
        "public_exposure_authorized": False,
        "go_live_enabled": False,
        "full_title_generation_authorized": False,
        "status": "PRIVATE_PREVIEW_OWNER_APPROVAL_PENDING",
    }
    evidence_path = destination / "reader-preview-evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**evidence, "evidence_path": str(evidence_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--output-root", type=Path, default=Path("/private/tmp/earnalism-25-title-private-reader-previews"))
    parser.add_argument("--word-limit", type=int, default=950)
    args = parser.parse_args()
    print(json.dumps(render(args.slug, args.voice, args.output_root, args.word_limit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
