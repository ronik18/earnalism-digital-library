#!/usr/bin/env python3
"""Deterministically repair The Enchanted April controlled reader package."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SLUG = "the-enchanted-april"
SOURCE = Path("/private/tmp/pg16389.txt")
SOURCE_URL = "https://www.gutenberg.org/cache/epub/16389/pg16389.txt"
SOURCE_SHA = "d2d5a31f295361fb742f44729d3de6082cd7bff742a0484cd178731d66ef8370"
CONTENT = ROOT / "content/books" / SLUG
RAW = CONTENT / "raw/source.txt"
PACK = ROOT / "data/controlled_publications" / SLUG
BACKEND = ROOT / "backend/data/controlled_publications" / SLUG
FRONT = ROOT / "frontend/public/assets/books" / SLUG / "front-cover.webp"
BACK = ROOT / "frontend/public/assets/books" / SLUG / "back-cover.webp"
FRONT_SHA = "094e542561e8ef5ba2d6ed07c989e4ef69bcbcd00ae079525beb1d848a01a7f7"
BACK_SHA = "135b4c8820ee8c4eb3d0cf27d5d0e4e013c62ae7df23c390558abca95f39588f"
COVER_AUDIT = "internal/earnalism_intelligence/english_25_title_generated_cover_audit.json"
RIGHTS_URL = "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html"
RIGHTS = ("Elizabeth von Arnim died in 1941. Under Section 22 of the Copyright Act, "
          "1957 (India), copyright in a literary work subsists until sixty years from "
          "the beginning of the calendar year following the author's death; the term "
          "expired after 2001 and the work entered the public domain in India on "
          "1 January 2002. Territory: IN.")
REPAIR_ID = "enchanted-april-reader-repair-20260816"
WORDS = re.compile(r"\b\w+[’'\-]?\w*\b", re.UNICODE)
CHAPTER_19_RESTORATION = "completely owing to the absence of any ill effects produced by it on"
CHAPTER_22_RESTORATION = "extraordinary, the developments produced by San Salvatore. She and Mrs."


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha(text: str) -> str:
    return sha(text.encode("utf-8"))


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def read_json(path: Path):
    return json.loads(path.read_text())


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def source_bytes() -> bytes:
    data = SOURCE.read_bytes()
    if sha(data) != SOURCE_SHA:
        raise ValueError(f"official source checksum changed: {sha(data)}")
    return data


def verify_covers() -> None:
    for path, expected in ((FRONT, FRONT_SHA), (BACK, BACK_SHA)):
        if sha(path.read_bytes()) != expected:
            raise ValueError(f"cover checksum mismatch: {path}")
        with Image.open(path) as image:
            if image.format != "WEBP" or image.size != (800, 1200):
                raise ValueError(f"cover format/dimensions differ: {path}: {image.format} {image.size}")
    audit = read_json(ROOT / COVER_AUDIT)
    rows = audit if isinstance(audit, list) else audit.get("rows", audit.get("titles", audit.get("covers", [])))
    row = next((x for x in rows if x.get("slug") == SLUG), None)
    if not row or row.get("front_sha256") != FRONT_SHA or row.get("back_sha256") != BACK_SHA:
        raise ValueError("generated-cover audit binding missing")
    if row.get("art_source") != "deterministic_vector_primitives_no_external_art":
        raise ValueError("cover provenance differs")


def source_chapters():
    lines = source_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").splitlines()
    if len(lines) < 8767:
        raise ValueError("official source unexpectedly short")
    expected = [f"Chapter {i}" for i in range(1, 23)]
    starts = []
    for i in range(71, 8766):
        if lines[i].strip() in expected and (not starts or lines[i].strip() != starts[-1][1]):
            starts.append((i, lines[i].strip()))
    if [x[1] for x in starts] != expected:
        raise ValueError(f"unexpected chapter headings: {starts}")
    out = []
    for index, (start, title) in enumerate(starts):
        stop = starts[index + 1][0] if index + 1 < len(starts) else 8766
        body = "\n".join(lines[start + 1:stop]).strip()
        blocks = []
        for block in re.split(r"\n\s*\n", body):
            raw_lines = [line.rstrip() for line in block.splitlines() if line.strip()]
            if not raw_lines:
                continue
            stripped = [line.strip() for line in raw_lines]
            if len(raw_lines) > 1 and all(line.startswith("  ") for line in raw_lines):
                blocks.append("\n".join(stripped))
            else:
                blocks.append(" ".join(stripped))
        text = "\n\n".join(blocks)
        old = read_json(PACK / f"chapters/chapter-{index + 1:03d}.json")["content"]
        source_norm, old_norm = normalized(text), normalized(old)
        source_restoration = None
        if source_norm != old_norm:
            if index == 18 and source_norm.replace(CHAPTER_19_RESTORATION + " ", "", 1) == old_norm:
                source_restoration = CHAPTER_19_RESTORATION
            elif index == 21 and source_norm.replace(CHAPTER_22_RESTORATION + " ", "", 1) == old_norm:
                source_restoration = CHAPTER_22_RESTORATION
            else:
                raise ValueError(f"chapter {index + 1} changed normalized narrative outside an audited source restoration")
        elif index == 18 and CHAPTER_19_RESTORATION in source_norm:
            source_restoration = CHAPTER_19_RESTORATION
        elif index == 21 and CHAPTER_22_RESTORATION in source_norm:
            source_restoration = CHAPTER_22_RESTORATION
        out.append({"title": title, "text": text, "sha256": text_sha(text),
                    "word_count": len(WORDS.findall(text)), "semantic_blocks": len(blocks)})
        if source_restoration:
            out[-1]["source_restoration"] = source_restoration
    return out


def private_truth(value: dict) -> dict:
    value = copy.deepcopy(value)
    value.update({"verification_status": "approved",
                  "qa_status": "READY_FOR_APPROVAL",
                  "approved_to_publish": False,
                  "publication_status": "READER_APPROVAL_REQUIRED",
                  "readerStatus": "reader_approval_required", "publicationStatus": "draft",
                  "isPublic": False, "isLive": False, "showInPublicLibrary": False,
                  "showInHomepage": False, "allowPublicReading": False, "is_published": False,
                  "audio_enabled": False, "audiobook_enabled": False,
                  "generate_audiobook": False, "audiobook_provider": "",
                  "audiobook_voice": "", "audio_asset_slug": ""})
    return value


def checksum_manifest(replacements: dict[Path, bytes], at: str) -> bytes:
    paths = {p for p in PACK.rglob("*") if p.is_file()} | {p for p in replacements if p.is_relative_to(PACK)}
    rows = []
    for path in sorted(paths):
        if path.name in {"checksum_manifest.json", "publication_manifest.json"}:
            continue
        payload = replacements[path] if path in replacements else path.read_bytes()
        rows.append({"file": path.relative_to(PACK).as_posix(), "sha256": sha(payload)})
    return json_bytes({"slug": SLUG, "generated_at": at, "files": rows})


def plan(at: str):
    verify_covers()
    chapters = source_chapters()
    content_hash = text_sha("\n\n".join(c["text"] for c in chapters))
    word_count = sum(c["word_count"] for c in chapters)
    block_count = sum(c["semantic_blocks"] for c in chapters)
    minutes = math.ceil(word_count / 240)
    fingerprint = text_sha(json.dumps({"slug": SLUG, "source_sha256": SOURCE_SHA,
        "chapter_sha256": [c["sha256"] for c in chapters], "rights_basis": RIGHTS,
        "front_cover_sha256": FRONT_SHA, "back_cover_sha256": BACK_SHA,
        "audio_enabled": False}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    rep: dict[Path, bytes] = {RAW: source_bytes()}
    front_url = f"https://theearnalism.com/assets/books/{SLUG}/front-cover.webp"
    back_url = f"https://theearnalism.com/assets/books/{SLUG}/back-cover.webp"
    book = read_json(CONTENT / "book.json")
    book.update({"rightsTerritoryBasis": RIGHTS, "readerStatus": "reader_approval_required",
        "publicationStatus": "draft", "isPublic": False, "isLive": False,
        "showInPublicLibrary": False, "showInHomepage": False, "allowPublicReading": False,
        "is_published": False, "wordCountApprox": word_count,
        "readingTimeMinutesApprox": minutes, "updatedAt": at,
        "readerPackageFingerprint": fingerprint, "coverImage": front_url,
        "backCoverImage": back_url, "coverAssets": [
            {"role": "front", "path": f"frontend/public/assets/books/{SLUG}/front-cover.webp", "sha256": FRONT_SHA, "width": 800, "height": 1200, "format": "webp"},
            {"role": "back", "path": f"frontend/public/assets/books/{SLUG}/back-cover.webp", "sha256": BACK_SHA, "width": 800, "height": 1200, "format": "webp"}]})
    rep[CONTENT / "book.json"] = json_bytes(book)
    rep[CONTENT / "source-rights.md"] = f"""# Source Rights Note: The Enchanted April

- Title: The Enchanted April
- Author: Elizabeth von Arnim
- Author death year: 1941
- Original publication year: 1922
- Source landing page: https://www.gutenberg.org/ebooks/16389
- Controlled source download: {SOURCE_URL}
- Controlled source SHA-256: {SOURCE_SHA}
- India commercial-use rights basis: {RIGHTS}
- Rights statute: Copyright Act, 1957 (India), Section 22
- Rights reference: {RIGHTS_URL}
- Commercial use allowed in publication territory IN: yes
- Reader-facing boilerplate removed: Gutenberg front matter through line 71 and end/license furniture beginning at line 8767.
- Exact raw source archive: content/books/{SLUG}/raw/source.txt
- Cover provenance: {COVER_AUDIT}; deterministic vector primitives, no external artwork.
- Updated at UTC: {at}
- Status: reader_repair_ready_for_owner_approval
""".encode()
    public = private_truth(read_json(PACK / "public_book.json"))
    public.update({"subtitle": "Complete Edition", "source_hash": SOURCE_SHA,
        "source_hash_domain": "exact_download_bytes", "content_hash": content_hash,
        "content_hash_domain": "chapter_text_utf8_joined_by_double_lf", "rights_basis": RIGHTS,
        "rights_territory": "IN", "cover_status": "EARNALISM_GENERATED_GRAPHICAL_COVER_VERIFIED",
        "cover_gate_passed": True, "release_blockers": ["fresh_checksum_bound_reader_approval_required"],
        "cover_url": front_url, "cover_image_url": front_url, "coverImage": front_url,
        "cover_image": front_url, "back_cover_url": back_url, "back_cover_image_url": back_url,
        "backCoverImage": back_url, "cover_dimensions": {"width": 800, "height": 1200},
        "estimated_reading_time": f"{minutes} min", "updated_at": at,
        "reader_package_fingerprint": fingerprint})
    reader = read_json(PACK / "reader_manifest.json")
    public_rows, reader_rows = copy.deepcopy(public["chapters"]), copy.deepcopy(reader["chapters"])
    for n, chapter in enumerate(chapters, 1):
        reading = max(1, math.ceil(chapter["word_count"] / 240))
        cp = CONTENT / f"chapters/{n:03d}-chapter-{n}.json"
        cd = read_json(cp)
        cd.update({"content": chapter["text"], "sourceSha256": SOURCE_SHA,
            "sourceSha256Domain": "exact_download_bytes", "sanitizedSha256": chapter["sha256"],
            "wordCountApprox": chapter["word_count"], "characterCount": len(chapter["text"]),
            "readingTimeMinutesApprox": reading})
        rep[cp] = json_bytes(cd)
        pp = PACK / f"chapters/chapter-{n:03d}.json"
        pd = read_json(pp)
        pd.update({"content": chapter["text"], "content_hash": chapter["sha256"],
            "sanitizedSha256": chapter["sha256"], "word_count": chapter["word_count"],
            "reading_minutes": reading, "updated_at": at})
        rep[pp] = json_bytes(pd)
        public_rows[n - 1].update({"is_preview": n == 1, "word_count": chapter["word_count"],
                                   "reading_minutes": reading, "updated_at": at})
        reader_rows[n - 1].update({"is_preview": n == 1, "word_count": chapter["word_count"],
                                   "reading_minutes": reading, "updated_at": at})
    public["chapters"] = public_rows
    rep[PACK / "public_book.json"] = json_bytes(public)
    reader.update({"chapters": reader_rows, "chapter_count": 22,
        "preview_chapter_ids": ["chapter-001"], "reader_status": "reader_approval_required",
        "cover_gate_passed": True, "release_blockers": ["fresh_checksum_bound_reader_approval_required"],
        "audio_enabled": False, "audiobook_enabled": False, "generated_at": at,
        "reader_package_fingerprint": fingerprint})
    rep[PACK / "reader_manifest.json"] = json_bytes(reader)
    evidence = read_json(PACK / "source_evidence.json")
    evidence.update({"source_url": SOURCE_URL, "source_download_url": SOURCE_URL,
        "source_hash": SOURCE_SHA, "source_hash_domain": "exact_download_bytes",
        "content_hash": content_hash, "content_hash_domain": "chapter_text_utf8_joined_by_double_lf",
        "rights_basis": RIGHTS, "rights_statute": "Copyright Act, 1957 (India), Section 22",
        "rights_statute_url": RIGHTS_URL, "publication_region": "IN", "author_death_year": 1941,
        "original_publication_year": 1922, "verification_status": "approved",
        "qa_status": "READY_FOR_APPROVAL", "verified_at": at,
        "official_download_sha256": SOURCE_SHA, "reader_package_fingerprint": fingerprint,
        "raw_source_archive": f"content/books/{SLUG}/raw/source.txt",
        "reader_facing_boilerplate_removed": True, "cover_audit": COVER_AUDIT,
        "front_cover_sha256": FRONT_SHA, "back_cover_sha256": BACK_SHA})
    rep[PACK / "source_evidence.json"] = json_bytes(evidence)
    approval = read_json(PACK / "approval_evidence.json")
    approval.update({"approved_to_publish": False, "verification_status": "approved",
        "qa_status": "READY_FOR_APPROVAL",
        "approval_scope": "fresh_checksum_bound_reader_approval_required",
        "reader_approval": "NOT_REQUESTED", "reader_public_release": "READER_APPROVAL_REQUIRED",
        "cover_gate_passed": True,
        "release_blockers": ["fresh_checksum_bound_reader_approval_required"],
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED", "audio_enabled": False,
        "audiobook_enabled": False, "reader_package_fingerprint": fingerprint})
    rep[PACK / "approval_evidence.json"] = json_bytes(approval)
    rep[PACK / "highlight_sync.json"] = json_bytes({"slug": SLUG,
        "status": "INVALIDATED_STALE_ESTIMATED_SYNC", "generatedAt": at,
        "source": "enchanted_april_reader_repair", "chapters": [], "totalDurationMs": 0,
        "audio_enabled": False, "audiobook_enabled": False,
        "note": "Legacy estimated timing is inadmissible. Future audio requires measured synchronization bound to approved audio bytes."})
    repair = {"schema": "earnalism.enchanted_april_reader_repair.v1", "repair_id": REPAIR_ID,
        "slug": SLUG, "repaired_at": at, "official_source_url": SOURCE_URL,
        "official_source_sha256": SOURCE_SHA, "raw_source_archived_exactly": True,
        "rights_territory": "IN", "rights_statute": "Copyright Act, 1957 (India), Section 22",
        "author_death_year": 1941, "public_domain_in_india_from": "2002-01-01",
        "reader_package_fingerprint": fingerprint, "chapter_count": 22, "word_count": word_count,
        "semantic_blocks": block_count, "content_sha256": content_hash,
        "chapter_evidence": chapters, "normalized_chapter_equality_except_source_restoration": True,
        "source_restorations": [
            {"chapter": 19, "text": CHAPTER_19_RESTORATION, "reason": "The prior package omitted these exact official-source words."},
            {"chapter": 22, "text": CHAPTER_22_RESTORATION, "reason": "The prior package omitted these exact official-source words."}],
        "narrative_words_order_unchanged": True, "legacy_estimated_sync_invalidated": True,
        "front_cover_sha256": FRONT_SHA, "back_cover_sha256": BACK_SHA,
        "cover_dimensions": [800, 1200], "cover_provenance_audit": COVER_AUDIT,
        "cover_gate_passed": True, "audio_enabled": False, "root_backend_byte_parity": True,
        "release_blockers": ["fresh_checksum_bound_reader_approval_required"], "preview_rendered": False}
    repair["evidence_sha256"] = text_sha(json.dumps(repair, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    rep[PACK / "reader_repair_evidence.json"] = json_bytes(repair)
    rep[PACK / "checksum_manifest.json"] = checksum_manifest(rep, at)
    relative = {p.relative_to(PACK) for p in PACK.rglob("*") if p.is_file()} | {p.relative_to(PACK) for p in rep if p.is_relative_to(PACK)}
    for rel in sorted(relative):
        payload = rep[PACK / rel] if PACK / rel in rep else (PACK / rel).read_bytes()
        rep[PACK / rel] = payload
        rep[BACKEND / rel] = payload
    update_intelligence(rep, repair, at)
    return rep, repair


def update_intelligence(rep: dict[Path, bytes], repair: dict, at: str) -> None:
    base = ROOT / "internal/earnalism_intelligence"
    ledger = base / "decision_ledger.jsonl"
    text = ledger.read_text()
    if REPAIR_ID not in text:
        row = {"timestamp": at, "workstream": "english_25_title_controlled_release",
            "slug_or_area": SLUG, "decision": REPAIR_ID,
            "evidence": {"official_source_sha256": SOURCE_SHA,
                "content_sha256": repair["content_sha256"], "chapter_count": 22,
                "word_count": repair["word_count"], "semantic_blocks": repair["semantic_blocks"],
                "normalized_chapter_equality_except_source_restoration": True, "root_backend_byte_parity": True,
                "cover_gate_passed": True, "audio_enabled": False},
            "selected_option": "Reflow the exact official source into semantic paragraphs and stop at fresh owner approval.",
            "customer_experience_reason": "Readers should receive coherent literary paragraphs, a complete edition, and verified exact-title covers.",
            "release_gate_reason": "Source, India rights, cover provenance, checksums, mirrors, and structure pass; fresh owner approval remains required.",
            "result": "READER_REPAIRED_OWNER_APPROVAL_PENDING",
            "next_action": "Run private preview prechecks and request checksum-bound owner approval in a separate authorized step."}
        text = text.rstrip() + "\n" + json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    rep[ledger] = text.encode()
    history_path = base / "title_decision_history.json"
    history = read_json(history_path)
    history.setdefault("titles", {})[SLUG] = {"latest_decision": "READER_REPAIRED_OWNER_APPROVAL_PENDING",
        "decision_reason": "Exact source, India rights, semantic structure, cover provenance, checksums, and mirrors pass.",
        "updated_at": at, "language": "en", "territory": "IN",
        "public_reader_status": "PRIVATE_READER_APPROVAL_REQUIRED",
        "public_audio_status": "AUDIO_HIDDEN_NOT_REQUESTED", "source_sha256": SOURCE_SHA,
        "content_sha256": repair["content_sha256"],
        "next_action": "Run private preview prechecks and request fresh checksum-bound owner approval."}
    rep[history_path] = json_bytes(history)
    learnings_path = base / "sprint_learnings.md"
    learnings = learnings_path.read_text()
    marker = "## Enchanted April deterministic reader repair - 2026-08-16"
    if marker not in learnings:
        learnings = learnings.rstrip() + "\n\n" + marker + """

- The official 2025 plaintext preserves exactly 22 chapter headings; exact source-byte hashing and whitespace-normalized chapter comparison make semantic reflow deterministic. Chapters 19 and 22 also restore two exact phrases omitted by the prior package, with no editorial rewriting or reordering.
- India release evidence for Elizabeth von Arnim must cite Copyright Act 1957 Section 22 and her 1941 death year; the work entered India's public domain on 1 January 2002.
- Exact-title deterministic vector covers may pass the graphical-cover gate only when dimensions, bytes, checksums, and no-external-art provenance all match the repository audit.
"""
    rep[learnings_path] = learnings.encode()
    rep[base / "enchanted_april_reader_repair_20260816.json"] = json_bytes(repair)


def verify_written(rep: dict[Path, bytes]) -> None:
    for path, payload in rep.items():
        if path.read_bytes() != payload:
            raise ValueError(f"written bytes differ: {path}")
    for package in (PACK, BACKEND):
        rows = {row["file"]: row["sha256"] for row in read_json(package / "checksum_manifest.json")["files"]}
        managed = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file() and p.name not in {"checksum_manifest.json", "publication_manifest.json"}}
        if "checksum_manifest.json" in rows or set(rows) != managed:
            raise ValueError(f"manifest coverage differs: {package}")
        for rel, digest in rows.items():
            if sha((package / rel).read_bytes()) != digest:
                raise ValueError(f"checksum differs: {package / rel}")
    root_files = {p.relative_to(PACK) for p in PACK.rglob("*") if p.is_file()}
    backend_files = {p.relative_to(BACKEND) for p in BACKEND.rglob("*") if p.is_file()}
    if root_files != backend_files:
        raise ValueError("mirror file sets differ")
    for rel in root_files:
        if (PACK / rel).read_bytes() != (BACKEND / rel).read_bytes():
            raise ValueError(f"mirror differs: {rel}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repaired-at", default="2026-08-16T00:00:00Z")
    args = parser.parse_args()
    rep, repair = plan(args.repaired_at)
    changed = [str(p.relative_to(ROOT)) for p, payload in rep.items() if not p.exists() or p.read_bytes() != payload]
    if args.write:
        for path, payload in rep.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        verify_written(rep)
    print(json.dumps({**repair, "mode": "write" if args.write else "dry-run", "changed_files": changed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
