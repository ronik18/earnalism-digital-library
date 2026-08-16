#!/usr/bin/env python3
"""Deterministically repair and canonicalize The Picture of Dorian Gray reader."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "picture-of-dorian-gray"
ALIAS = "the-picture-of-dorian-gray"
SOURCE_SHA = "9e37dc7035cb6991073be62b6e8de858173cd8608a25ec5a5ca78c6608458932"
SOURCE_URL = "https://www.gutenberg.org/ebooks/174.txt.utf-8"
SOURCE_LANDING = "https://www.gutenberg.org/ebooks/174"
SOURCE = ROOT / "content/books" / SLUG / "raw/source.txt"
CONTENT = ROOT / "content/books" / SLUG
PACK = ROOT / "data/controlled_publications" / SLUG
BACKEND = ROOT / "backend/data/controlled_publications" / SLUG
ALIAS_CONTENT = ROOT / "content/books" / ALIAS
ALIAS_PACK = ROOT / "data/controlled_publications" / ALIAS
TOMBSTONE = ROOT / "internal/earnalism_intelligence/retired_aliases/the-picture-of-dorian-gray.json"
REPAIR_EVIDENCE = ROOT / "internal/earnalism_intelligence/picture_of_dorian_gray_reader_repair_20260816.json"
REPAIR_ID = "picture-of-dorian-gray-reader-repair-20260816"
BASE_COMMIT = "e78d0ae77808822ccbe9d6d9d65f3d0cbd29384c"
RIGHTS_URL = "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html"
RIGHTS = ("Oscar Wilde died in 1900. Under Section 22 of the Copyright Act, 1957 "
          "(India), copyright in a literary work subsists until sixty years from "
          "the beginning of the calendar year following the author's death; the "
          "term expired after 1960 and the work entered the public domain in India "
          "on 1 January 1961. Territory: IN.")
WORDS = re.compile(r"[\w]+(?:[’'][\w]+)?", re.UNICODE)
HEADINGS = ["THE PREFACE"] + [f"CHAPTER {n}." for n in
    ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
     "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX")]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_sha(text: str) -> str:
    return sha(text.encode("utf-8"))


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def read_json(path: Path):
    return json.loads(path.read_text())


def tokens(text: str) -> list[str]:
    return [x.casefold() for x in WORDS.findall(text)]


def source_bytes() -> bytes:
    data = SOURCE.read_bytes()
    if sha(data) != SOURCE_SHA:
        raise ValueError(f"archived source checksum changed: {sha(data)}")
    return data


def semantic_blocks(lines: list[str]) -> list[str]:
    blocks = []
    for block in re.split(r"\n\s*\n", "\n".join(lines).strip()):
        raw = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not raw:
            continue
        stripped = [line.strip() for line in raw]
        if len(raw) > 1 and all(line.startswith("  ") for line in raw):
            blocks.append("\n".join(stripped))
        else:
            blocks.append(" ".join(stripped))
    return blocks


def source_chapters() -> list[dict]:
    lines = source_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").splitlines()
    starts = []
    for i, line in enumerate(lines):
        title = line.strip()
        if title in HEADINGS and i >= 60:
            starts.append((i, title))
    if [title for _, title in starts] != HEADINGS:
        raise ValueError(f"unexpected revised-edition headings: {starts}")
    end = next((i for i, line in enumerate(lines) if line.startswith("*** END OF THE PROJECT GUTENBERG")), None)
    if end is None:
        raise ValueError("Gutenberg end marker missing")
    chapters = []
    for index, (start, title) in enumerate(starts):
        stop = starts[index + 1][0] if index + 1 < len(starts) else end
        blocks = semantic_blocks(lines[start + 1:stop])
        text = "\n\n".join(blocks)
        chapters.append({"order": index + 1, "title": "THE PREFACE" if index == 0 else title,
                         "text": text, "sha256": text_sha(text),
                         "word_count": len(tokens(text)), "semantic_blocks": len(blocks)})
    return chapters


def alias_files() -> list[Path]:
    return sorted([p for root in (ALIAS_CONTENT, ALIAS_PACK) if root.exists()
                   for p in root.rglob("*") if p.is_file()])


def alias_proof(chapters: list[dict]) -> dict:
    if not ALIAS_PACK.exists():
        if not TOMBSTONE.exists():
            raise ValueError("alias and its retirement tombstone are both missing")
        recorded = read_json(TOMBSTONE)
        proof = recorded.get("alias_proof", {})
        if not proof.get("alias_is_exact_ordered_subsequence") or proof.get(
                "alias_contributes_legitimate_narrative_absent_from_canonical") is not False:
            raise ValueError("recorded alias proof is not admissible")
        archive = proof.get("retired_files", [])
        manifest = text_sha(json.dumps(archive, sort_keys=True, separators=(",", ":")))
        if manifest != proof.get("retired_tree_manifest_sha256"):
            raise ValueError("recorded retired-tree manifest checksum differs")
        return proof
    canonical = []
    for chapter in chapters:
        canonical.extend(tokens(chapter["text"]))
    alias = []
    alias_chapters = sorted((ALIAS_PACK / "chapters").glob("chapter-*.json"))
    for path in alias_chapters:
        alias.extend(tokens(read_json(path)["content"]))
    display_suffix_removed = False
    if alias[-2:] == ["the", "end"]:
        alias = alias[:-2]
        display_suffix_removed = True
    cursor = 0
    positions = []
    for word in alias:
        while cursor < len(canonical) and canonical[cursor] != word:
            cursor += 1
        if cursor == len(canonical):
            raise ValueError(f"alias contributes token absent from canonical ordered source: {word}")
        positions.append(cursor)
        cursor += 1
    omitted = []
    alias_set = set(positions)
    run = []
    for i, word in enumerate(canonical):
        if i not in alias_set:
            run.append(word)
        elif run:
            omitted.append(run); run = []
    if run:
        omitted.append(run)
    archive = [{"path": str(p.relative_to(ROOT)), "sha256": sha(p.read_bytes()), "size": p.stat().st_size}
               for p in alias_files()]
    return {
        "method": "casefolded Unicode word-token ordered-subsequence proof",
        "canonical_token_count": len(canonical), "alias_narrative_token_count": len(alias),
        "matched_alias_token_count": len(positions), "alias_is_exact_ordered_subsequence": True,
        "alias_contributes_legitimate_narrative_absent_from_canonical": False,
        "display_only_the_end_removed_before_comparison": display_suffix_removed,
        "canonical_tokens_omitted_by_alias": sum(len(x) for x in omitted),
        "omitted_runs": [{"token_count": len(x), "text": " ".join(x)} for x in omitted],
        "retired_file_count": len(archive), "retired_files": archive,
        "retired_tree_manifest_sha256": text_sha(json.dumps(archive, sort_keys=True, separators=(",", ":"))),
    }


def private_truth(value: dict) -> dict:
    value = copy.deepcopy(value)
    value.update({"verification_status": "approved", "qa_status": "READY_FOR_APPROVAL",
        "approved_to_publish": False, "publication_status": "READER_APPROVAL_REQUIRED",
        "readerStatus": "reader_approval_required", "publicationStatus": "draft",
        "isPublic": False, "isLive": False, "showInPublicLibrary": False,
        "showInHomepage": False, "allowPublicReading": False, "is_published": False,
        "audio_enabled": False, "audiobook_enabled": False, "generate_audiobook": False,
        "audiobook_provider": "", "audiobook_voice": "", "audio_asset_slug": ""})
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
    chapters = source_chapters()
    proof = alias_proof(chapters)
    content_hash = text_sha("\n\n".join(c["text"] for c in chapters))
    word_count = sum(c["word_count"] for c in chapters)
    block_count = sum(c["semantic_blocks"] for c in chapters)
    fingerprint = text_sha(json.dumps({"slug": SLUG, "source_sha256": SOURCE_SHA,
        "chapter_sha256": [c["sha256"] for c in chapters], "rights_basis": RIGHTS,
        "cover_gate_passed": False, "alias_retired_manifest_sha256": proof["retired_tree_manifest_sha256"],
        "audio_enabled": False}, sort_keys=True, separators=(",", ":")))
    rep: dict[Path, bytes] = {}
    book = private_truth(read_json(CONTENT / "book.json"))
    book.update({"rightsTerritoryBasis": RIGHTS, "chapterCount": 21, "wordCountApprox": word_count,
        "readingTimeMinutesApprox": math.ceil(word_count / 240), "updatedAt": at,
        "readerPackageFingerprint": fingerprint, "coverGatePassed": False,
        "coverStatus": "BLOCKED_UNPROVEN_EXACT_SLUG_GRAPHICAL_COVER",
        "releaseBlockers": ["exact_slug_cover_provenance_required", "fresh_checksum_bound_reader_approval_required"]})
    rep[CONTENT / "book.json"] = json_bytes(book)
    rep[CONTENT / "source-rights.md"] = f"""# Source Rights Note: The Picture of Dorian Gray

- Title: The Picture of Dorian Gray
- Author: Oscar Wilde
- Author death year: 1900
- Original publication year: 1890; revised book edition 1891
- Official source: Project Gutenberg eBook #174
- Source landing page: {SOURCE_LANDING}
- Controlled source download: {SOURCE_URL}
- Controlled source SHA-256: {SOURCE_SHA}
- India commercial-use rights basis: {RIGHTS}
- Rights statute: Copyright Act, 1957 (India), Section 22
- Rights reference: {RIGHTS_URL}
- Commercial use allowed in publication territory IN: yes
- Reader-facing boilerplate removed: contents/front furniture and Gutenberg license matter.
- Exact raw source archive: content/books/{SLUG}/raw/source.txt
- Cover gate: blocked; no exact-slug graphical cover has checksum-bound legal provenance.
- Updated at UTC: {at}
- Status: reader_repair_ready_for_cover_and_owner_approval
""".encode()
    public = private_truth(read_json(PACK / "public_book.json"))
    public.update({"subtitle": "Complete Revised Edition", "source_hash": SOURCE_SHA,
        "source_hash_domain": "exact_archived_download_bytes", "content_hash": content_hash,
        "content_hash_domain": "chapter_text_utf8_joined_by_double_lf", "rights_basis": RIGHTS,
        "rights_territory": "IN", "cover_status": "BLOCKED_UNPROVEN_EXACT_SLUG_GRAPHICAL_COVER",
        "cover_gate_passed": False, "release_blockers": ["exact_slug_cover_provenance_required",
        "fresh_checksum_bound_reader_approval_required"], "estimated_reading_time": f"{math.ceil(word_count/240)} min",
        "updated_at": at, "reader_package_fingerprint": fingerprint})
    reader = read_json(PACK / "reader_manifest.json")
    public_rows = []
    reader_rows = []
    old_controlled = sorted((PACK / "chapters").glob("chapter-*.json"))
    old_content = sorted((CONTENT / "chapters").glob("*.json"))
    for index, chapter in enumerate(chapters, 1):
        reading = max(1, math.ceil(chapter["word_count"] / 240))
        slug_title = "preface" if index == 1 else f"chapter-{index-1}"
        content_path = CONTENT / f"chapters/{index:03d}-{slug_title}.json"
        base_content = read_json(old_content[min(index - 1, len(old_content) - 1)])
        base_content.update({"bookSlug": SLUG, "chapterNumber": index, "id": f"chapter-{index:03d}",
            "title": chapter["title"], "content": chapter["text"], "sourceSha256": SOURCE_SHA,
            "sourceSha256Domain": "exact_archived_download_bytes", "sanitizedSha256": chapter["sha256"],
            "wordCountApprox": chapter["word_count"], "characterCount": len(chapter["text"]),
            "readingTimeMinutesApprox": reading, "sourceTitle": "The Picture of Dorian Gray"})
        rep[content_path] = json_bytes(base_content)
        controlled_path = PACK / f"chapters/chapter-{index:03d}.json"
        base_controlled = read_json(old_controlled[min(index - 1, len(old_controlled) - 1)])
        base_controlled.update({"id": f"chapter-{index:03d}", "bookSlug": SLUG, "order": index,
            "title": chapter["title"], "content": chapter["text"], "content_hash": chapter["sha256"],
            "sourceSha256": SOURCE_SHA, "sanitizedSha256": chapter["sha256"],
            "word_count": chapter["word_count"], "reading_minutes": reading,
            "is_preview": index == 1, "updated_at": at})
        rep[controlled_path] = json_bytes(base_controlled)
        row = {k: base_controlled[k] for k in ("id", "order", "title", "is_preview", "has_images",
            "image_count", "word_count", "reading_minutes", "language_hint", "processing_status",
            "processing_warnings", "uploaded_at", "updated_at") if k in base_controlled}
        public_rows.append(copy.deepcopy(row)); reader_rows.append(copy.deepcopy(row))
    public["chapters"] = public_rows
    rep[PACK / "public_book.json"] = json_bytes(public)
    reader.update({"slug": SLUG, "chapter_count": 21, "chapters": reader_rows,
        "preview_chapter_ids": ["chapter-001"], "reader_status": "reader_approval_required",
        "cover_gate_passed": False, "release_blockers": public["release_blockers"],
        "audio_enabled": False, "audiobook_enabled": False, "generated_at": at,
        "reader_package_fingerprint": fingerprint})
    rep[PACK / "reader_manifest.json"] = json_bytes(reader)
    source = read_json(PACK / "source_evidence.json")
    source.update({"source_url": SOURCE_URL, "source_landing_page": SOURCE_LANDING,
        "source_hash": SOURCE_SHA, "source_hash_domain": "exact_archived_download_bytes",
        "content_hash": content_hash, "content_hash_domain": "chapter_text_utf8_joined_by_double_lf",
        "rights_basis": RIGHTS, "rights_statute": "Copyright Act, 1957 (India), Section 22",
        "rights_statute_url": RIGHTS_URL, "publication_region": "IN", "author_death_year": 1900,
        "original_publication_year": 1890, "revised_edition_year": 1891,
        "verification_status": "approved", "qa_status": "READY_FOR_APPROVAL", "verified_at": at,
        "official_download_sha256": SOURCE_SHA, "reader_package_fingerprint": fingerprint,
        "raw_source_archive": f"content/books/{SLUG}/raw/source.txt", "reader_facing_boilerplate_removed": True})
    rep[PACK / "source_evidence.json"] = json_bytes(source)
    approval = private_truth(read_json(PACK / "approval_evidence.json"))
    approval.update({"approval_scope": "cover_and_fresh_checksum_bound_reader_approval_required",
        "reader_approval": "NOT_REQUESTED", "reader_public_release": "READER_APPROVAL_REQUIRED",
        "cover_gate_passed": False, "release_blockers": public["release_blockers"],
        "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
        "reader_package_fingerprint": fingerprint})
    rep[PACK / "approval_evidence.json"] = json_bytes(approval)
    rep[PACK / "highlight_sync.json"] = json_bytes({"slug": SLUG,
        "status": "INVALIDATED_STALE_OR_ESTIMATED_SYNC", "generatedAt": at,
        "source": REPAIR_ID, "chapters": [], "totalDurationMs": 0,
        "audio_enabled": False, "audiobook_enabled": False,
        "note": "No synchronization is admissible until measured timing is bound to approved audio bytes."})
    tombstone = {"schema": "earnalism.reader_alias_retirement.v1", "alias": ALIAS,
        "canonical_slug": SLUG, "retired_at": at, "retired_from_git_commit": BASE_COMMIT,
        "recovery_command": f"git show {BASE_COMMIT}:<path-from-retired-files>",
        "retirement_reason": "Malformed duplicate omitted the Preface and absorbed narrative into chapter titles.",
        "alias_proof": proof, "canonical_source_sha256": SOURCE_SHA,
        "canonical_reader_package_fingerprint": fingerprint}
    tombstone["tombstone_sha256"] = text_sha(json.dumps(tombstone, sort_keys=True, separators=(",", ":")))
    rep[TOMBSTONE] = json_bytes(tombstone)
    repair = {"schema": "earnalism.picture_of_dorian_gray_reader_repair.v1",
        "repair_id": REPAIR_ID, "slug": SLUG, "repaired_at": at,
        "official_source_url": SOURCE_URL, "official_source_sha256": SOURCE_SHA,
        "edition_structure": HEADINGS, "reader_package_fingerprint": fingerprint,
        "chapter_count": 21, "word_count": word_count, "semantic_blocks": block_count,
        "content_sha256": content_hash, "chapter_evidence": chapters, "rights_territory": "IN",
        "rights_statute": "Copyright Act, 1957 (India), Section 22", "author_death_year": 1900,
        "public_domain_in_india_from": "1961-01-01", "normalized_narrative_text_and_order_preserved": True,
        "alias_retirement": tombstone, "legacy_estimated_sync_invalidated": True,
        "cover_gate_passed": False, "audio_enabled": False, "root_backend_byte_parity": True,
        "release_blockers": public["release_blockers"], "preview_rendered": False}
    repair["evidence_sha256"] = text_sha(json.dumps(repair, sort_keys=True, separators=(",", ":")))
    rep[PACK / "reader_repair_evidence.json"] = json_bytes(repair)
    rep[PACK / "checksum_manifest.json"] = checksum_manifest(rep, at)
    relative = {p.relative_to(PACK) for p in PACK.rglob("*") if p.is_file()} | {p.relative_to(PACK) for p in rep if p.is_relative_to(PACK)}
    for rel in sorted(relative):
        payload = rep[PACK / rel] if PACK / rel in rep else (PACK / rel).read_bytes()
        rep[PACK / rel] = payload; rep[BACKEND / rel] = payload
    update_intelligence(rep, repair, at)
    keep_content = {p for p in rep if p.is_relative_to(CONTENT)} | {SOURCE, CONTENT / "raw/source-landing.html"}
    obsolete = {p for p in old_content if p not in keep_content}
    obsolete.update(alias_files())
    return rep, repair, obsolete


def update_intelligence(rep: dict[Path, bytes], repair: dict, at: str) -> None:
    base = ROOT / "internal/earnalism_intelligence"
    ledger = base / "decision_ledger.jsonl"
    text = ledger.read_text()
    if REPAIR_ID not in text:
        row = {"timestamp": at, "workstream": "english_25_title_controlled_release",
            "slug_or_area": SLUG, "decision": REPAIR_ID,
            "evidence": {"official_source_sha256": SOURCE_SHA, "content_sha256": repair["content_sha256"],
                "chapter_count": 21, "word_count": repair["word_count"],
                "alias_exact_ordered_subsequence": True, "alias_unique_narrative": False,
                "root_backend_byte_parity": True, "cover_gate_passed": False, "audio_enabled": False},
            "selected_option": "Canonicalize Preface plus Chapters I-XX and retire the malformed duplicate with a recovery tombstone.",
            "customer_experience_reason": "One complete source of truth prevents malformed chapter navigation and missing prose.",
            "release_gate_reason": "Source, rights, structure, alias proof, checksums, and mirrors pass; cover and fresh owner approval remain blocked.",
            "result": "READER_REPAIRED_COVER_AND_OWNER_APPROVAL_PENDING",
            "next_action": "Prove an exact-slug graphical cover, then render a private checksum-bound preview."}
        text = text.rstrip() + "\n" + json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    rep[ledger] = text.encode()
    history_path = base / "title_decision_history.json"
    history = read_json(history_path)
    history.setdefault("titles", {})[SLUG] = {"latest_decision": "READER_REPAIRED_COVER_AND_OWNER_APPROVAL_PENDING",
        "decision_reason": "Exact PG 174 source, India Section 22 rights, semantic structure, alias retirement, checksums, and mirrors pass.",
        "updated_at": at, "language": "en", "territory": "IN",
        "public_reader_status": "PRIVATE_COVER_AND_READER_APPROVAL_REQUIRED",
        "public_audio_status": "AUDIO_HIDDEN_NOT_REQUESTED", "source_sha256": SOURCE_SHA,
        "content_sha256": repair["content_sha256"], "next_action": "Prove cover provenance, then render private preview."}
    history["titles"].pop(ALIAS, None)
    rep[history_path] = json_bytes(history)
    learnings_path = base / "sprint_learnings.md"
    learnings = learnings_path.read_text()
    marker = "## Picture of Dorian Gray canonical reader repair - 2026-08-16"
    if marker not in learnings:
        learnings = learnings.rstrip() + "\n\n" + marker + """

- PG 174 is the revised Preface plus Chapters I-XX edition. The duplicate `the-` slug was an exact ordered subset: it omitted the Preface and two 12-word passages accidentally absorbed into chapter titles, and contributed no unique narrative.
- Duplicate retirement is recoverable when every retired file is checksum-bound to the pre-repair Git commit and a tombstone records the exact recovery path.
- Oscar Wilde died in 1900; India Section 22 places this work in India's public domain from 1 January 1961. Cover provenance remains an independent fail-closed gate.
"""
    rep[learnings_path] = learnings.encode()
    rep[REPAIR_EVIDENCE] = json_bytes(repair)
    batch = ROOT / "scripts/prepare_english_25_title_batch.py"
    batch_text = batch.read_text().replace('TitlePlan("The Picture of Dorian Gray", "the-picture-of-dorian-gray",',
                                           'TitlePlan("The Picture of Dorian Gray", "picture-of-dorian-gray",')
    rep[batch] = batch_text.encode()
    # These are current operator/catalog inputs rather than immutable historical evidence.
    # Canonicalize only their slug reference; cover provenance remains independently blocked.
    for relative in ("package.json", "launch_title_public_naming_map.json",
                     "launch_title_public_naming_map.csv", "book_cover_art_briefs.json"):
        path = ROOT / relative
        rep[path] = path.read_text().replace(ALIAS, SLUG).encode()


def verify_written(rep: dict[Path, bytes]) -> None:
    for path, payload in rep.items():
        if path.read_bytes() != payload:
            raise ValueError(f"written bytes differ: {path}")
    for package in (PACK, BACKEND):
        rows = {row["file"]: row["sha256"] for row in read_json(package / "checksum_manifest.json")["files"]}
        managed = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()
                   and p.name not in {"checksum_manifest.json", "publication_manifest.json"}}
        if "checksum_manifest.json" in rows or set(rows) != managed:
            raise ValueError(f"manifest coverage differs: {package}")
        for rel, digest in rows.items():
            if sha((package / rel).read_bytes()) != digest:
                raise ValueError(f"checksum differs: {package / rel}")
    root_files = {p.relative_to(PACK) for p in PACK.rglob("*") if p.is_file()}
    backend_files = {p.relative_to(BACKEND) for p in BACKEND.rglob("*") if p.is_file()}
    if root_files != backend_files or any((PACK / p).read_bytes() != (BACKEND / p).read_bytes() for p in root_files):
        raise ValueError("root/backend mirror differs")
    if ALIAS_CONTENT.exists() or ALIAS_PACK.exists():
        raise ValueError("retired alias still exists")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repaired-at", default="2026-08-16T00:00:00Z")
    args = parser.parse_args()
    rep, repair, obsolete = plan(args.repaired_at)
    changed = [str(p.relative_to(ROOT)) for p, payload in rep.items() if not p.exists() or p.read_bytes() != payload]
    if args.write:
        for path in sorted(obsolete, reverse=True):
            if path.exists(): path.unlink()
        for directory in (ALIAS_CONTENT / "chapters", ALIAS_CONTENT, ALIAS_PACK / "chapters", ALIAS_PACK):
            if directory.exists() and not any(directory.iterdir()): directory.rmdir()
        for path, payload in rep.items():
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
        verify_written(rep)
    print(json.dumps({**repair, "mode": "write" if args.write else "dry-run",
        "changed_files": changed, "retired_files": [str(p.relative_to(ROOT)) for p in sorted(obsolete)]}, indent=2))


if __name__ == "__main__":
    main()
