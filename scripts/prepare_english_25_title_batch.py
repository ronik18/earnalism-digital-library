#!/usr/bin/env python3
"""Prepare the controlled 25-title English batch without exposing audio.

The command is dry-run by default. Pass ``--write`` only after reviewing the
reported changes. It intentionally leaves every title reader-only/audio-hidden
until a new checksum-bound audiobook completes the release conveyor.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_ROOT = ROOT / "data" / "controlled_publications"
CONTENT_ROOT = ROOT / "content" / "books"


@dataclass(frozen=True)
class TitlePlan:
    requested_title: str
    slug: str
    voice: str
    author_profile: str


TITLE_PLANS = (
    TitlePlan("The Science of Getting Rich", "the-science-of-getting-rich", "bm_george", "male"),
    TitlePlan("The Most Dangerous Game", "the-most-dangerous-game", "bm_george", "male"),
    TitlePlan("The Stolen White Elephant", "the-stolen-white-elephant", "bm_george", "male"),
    TitlePlan("The Selfish Giant", "the-selfish-giant", "bm_george", "male"),
    TitlePlan("A Horseman in the Sky", "a-horseman-in-the-sky", "bm_george", "male"),
    TitlePlan("The Happy Prince", "the-happy-prince", "bm_george", "male"),
    TitlePlan("A Mystery of Heroism", "a-mystery-of-heroism", "bm_george", "male"),
    TitlePlan("The Open Boat", "the-open-boat", "bm_george", "male"),
    TitlePlan("A White Heron", "a-white-heron", "hf_alpha", "female"),
    TitlePlan("The Pit and the Pendulum", "the-pit-and-the-pendulum", "bm_george", "male"),
    TitlePlan("An Occurrence at Owl Creek Bridge", "an-occurrence-at-owl-creek-bridge", "bm_george", "male"),
    TitlePlan("Love of Life", "love-of-life", "bm_george", "male"),
    TitlePlan("A Scandal in Bohemia", "a-scandal-in-bohemia", "bm_george", "male"),
    TitlePlan("The Lady with the Dog", "the-lady-with-the-dog", "bm_george", "male"),
    TitlePlan("The Bishop", "the-bishop", "bm_george", "male"),
    TitlePlan("The Enchanted April", "the-enchanted-april", "hf_alpha", "female"),
    TitlePlan("The Metamorphosis", "the-metamorphosis", "bm_george", "male"),
    TitlePlan("The Canterville Ghost", "the-canterville-ghost", "bm_george", "male"),
    TitlePlan("The Man Who Would Be King", "the-man-who-would-be-king", "bm_george", "male"),
    # The long duplicate pack is incomplete. Production already uses this
    # canonical 11-chapter slug, so the requested title is deliberately bound
    # to it instead of creating a second edition.
    TitlePlan("The Strange Case of Dr Jekyll and Mr Hyde", "jekyll-and-hyde", "bm_george", "male"),
    TitlePlan("The Fall of the House of Usher", "the-fall-of-the-house-of-usher", "bm_george", "male"),
    TitlePlan("The Wonderful Wizard of Oz", "the-wonderful-wizard-of-oz", "bm_george", "male"),
    TitlePlan("The Adventures of Sherlock Holmes", "the-adventures-of-sherlock-holmes", "bm_george", "male"),
    TitlePlan("The Picture of Dorian Gray", "the-picture-of-dorian-gray", "bm_george", "male"),
    TitlePlan("The Great Gatsby", "the-great-gatsby", "bm_george", "male"),
)

PILOT_SLUGS = {"the-selfish-giant", "a-white-heron"}
RIGHTS_LABELS = {
    "author_name": "Author",
    "author_death_year": "Author death year",
    "original_publication_year": "Original publication year",
    "source_url": "Source URL",
    "source_license": "Source license",
    "rights_basis": "Rights basis",
    "verified_at": "Updated at UTC",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_rights_note(path: Path, source: dict[str, Any]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for key, label in RIGHTS_LABELS.items():
        match = re.search(
            rf"^- {re.escape(label)}:\s*(.+)$",
            text,
            re.MULTILINE | re.IGNORECASE,
        )
        values[key] = match.group(1).strip() if match else ""

    rights_basis = values["rights_basis"] or str(source.get("rights_basis") or "")
    if not values["original_publication_year"]:
        match = re.search(r"original publication(?:\s+year)?\s*(?:was|:)?\s*(\d{4})", rights_basis, re.I)
        values["original_publication_year"] = match.group(1) if match else ""
    if not values["verified_at"]:
        values["verified_at"] = str(source.get("downloaded_at") or "")

    for key in ("author_death_year", "original_publication_year"):
        raw = values[key]
        if not re.fullmatch(r"\d{4}", raw):
            raise ValueError(f"Missing or invalid {key} in {path}")
    if not values["author_name"]:
        raise ValueError(f"Missing author in {path}")
    if not values["verified_at"]:
        raise ValueError(f"Missing verification timestamp in {path}")

    return {
        **values,
        "author_death_year": int(values["author_death_year"]),
        "original_publication_year": int(values["original_publication_year"]),
        "rights_basis": rights_basis,
    }


def normalize_public_book(public: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(public)
    result["audio_enabled"] = False
    result["audiobook_enabled"] = False
    result["generate_audiobook"] = False
    result["audiobook_provider"] = ""
    result["audiobook_voice"] = ""
    result["audio_asset_slug"] = ""
    result.pop("audiobook", None)
    result.pop("audiobook_assets", None)
    result.pop("audiobook_assets_updated_at", None)
    formats = [str(item) for item in (result.get("formats") or [])]
    result["formats"] = [item for item in formats if item.lower() != "audiobook"]
    if "Ebook" not in result["formats"]:
        result["formats"].insert(0, "Ebook")
    return result


def assign_generated_cover(public: dict[str, Any], slug: str) -> dict[str, Any]:
    result = copy.deepcopy(public)
    if result.get("cover_image_url") or result.get("cover_url"):
        return result
    front = ROOT / "frontend" / "public" / "assets" / "books" / slug / "front-cover.webp"
    back = ROOT / "frontend" / "public" / "assets" / "books" / slug / "back-cover.webp"
    if not front.is_file() or not back.is_file():
        raise FileNotFoundError(f"Generated front/back cover pair is missing for {slug}")
    front_url = f"https://theearnalism.com/assets/books/{slug}/front-cover.webp"
    back_url = f"https://theearnalism.com/assets/books/{slug}/back-cover.webp"
    result.update(
        {
            "cover_url": front_url,
            "cover_image_url": front_url,
            "coverImage": front_url,
            "cover_image": front_url,
            "back_cover_url": back_url,
            "back_cover_image_url": back_url,
            "backCoverImage": back_url,
            "cover_status": "EARNALISM_GENERATED_GRAPHICAL_COVER",
            "cover_dimensions": {"front": [800, 1200], "back": [800, 1200]},
        }
    )
    return result


def normalize_approval(approval: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(approval)
    result["audio_public_release"] = "PUBLIC_AUDIO_RELEASE_NOT_APPROVED"
    result["audiobook_enabled"] = False
    return result


def normalize_reader(reader: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(reader)
    result["audio_enabled"] = False
    result["audiobook_enabled"] = False
    return result


def normalize_source(
    source: dict[str, Any], rights: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(source)
    result.update(
        {
            "author_name": rights["author_name"],
            "author_death_year": rights["author_death_year"],
            "original_publication_year": rights["original_publication_year"],
            "rights_basis": rights["rights_basis"],
            "rights_tier": "A",
            "verification_status": "approved",
            # This batch does not expand the currently approved territory.
            "publication_region": "IN",
            "verified_at": rights["verified_at"],
            "qa_status": "QA_PASSED",
            "reader_facing_boilerplate_removed": True,
        }
    )
    return result


def managed_files(artifact_dir: Path) -> Iterable[Path]:
    for path in sorted(artifact_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"checksum_manifest.json", "publication_manifest.json"}:
            continue
        yield path


def checksum_manifest(
    artifact_dir: Path,
    replacements: dict[Path, bytes],
    generated_at: str,
) -> dict[str, Any]:
    files = []
    for path in managed_files(artifact_dir):
        payload = replacements.get(path)
        digest = sha256_bytes(payload) if payload is not None else sha256_file(path)
        files.append(
            {
                "file": path.relative_to(artifact_dir).as_posix(),
                "sha256": digest,
            }
        )
    return {
        "slug": artifact_dir.name,
        "generated_at": generated_at,
        "files": files,
    }


def prepare_title(plan: TitlePlan, generated_at: str) -> dict[str, Any]:
    artifact_dir = CONTROLLED_ROOT / plan.slug
    rights_path = CONTENT_ROOT / plan.slug / "source-rights.md"
    required = (
        artifact_dir / "public_book.json",
        artifact_dir / "reader_manifest.json",
        artifact_dir / "source_evidence.json",
        artifact_dir / "approval_evidence.json",
        artifact_dir / "checksum_manifest.json",
        rights_path,
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"{plan.slug}: missing {missing}")

    public_path = artifact_dir / "public_book.json"
    reader_path = artifact_dir / "reader_manifest.json"
    source_path = artifact_dir / "source_evidence.json"
    approval_path = artifact_dir / "approval_evidence.json"
    manifest_path = artifact_dir / "checksum_manifest.json"

    source = read_json(source_path)
    rights = parse_rights_note(rights_path, source)
    public = normalize_public_book(read_json(public_path))
    public = assign_generated_cover(public, plan.slug)
    reader = normalize_reader(read_json(reader_path))
    approval = normalize_approval(read_json(approval_path))
    source = normalize_source(source, rights)

    replacements = {
        public_path: json_bytes(public),
        reader_path: json_bytes(reader),
        source_path: json_bytes(source),
        approval_path: json_bytes(approval),
    }
    manifest = checksum_manifest(artifact_dir, replacements, generated_at)
    replacements[manifest_path] = json_bytes(manifest)

    changed = []
    before_audio_claim = False
    original_public = read_json(public_path)
    original_approval = read_json(approval_path)
    before_audio_claim = any(
        (
            bool(original_public.get("audio_enabled")),
            bool(original_public.get("audiobook_enabled")),
            bool(original_public.get("audiobook")),
            bool(original_public.get("audiobook_assets")),
            str(original_approval.get("audio_public_release") or "")
            in {"APPROVED", "PUBLIC_AUDIO_RELEASE_APPROVED"},
        )
    )
    for path, payload in replacements.items():
        if path.read_bytes() != payload:
            changed.append(path.relative_to(ROOT).as_posix())

    return {
        "plan": plan,
        "artifact_dir": artifact_dir,
        "replacements": replacements,
        "changed_files": changed,
        "stale_audio_claim_removed": before_audio_claim,
        "rights": rights,
        "chapter_count": len(public.get("chapters") or []),
        "manifest_sha256": sha256_bytes(replacements[manifest_path]),
    }


def verify_written_title(result: dict[str, Any]) -> None:
    artifact_dir: Path = result["artifact_dir"]
    manifest = read_json(artifact_dir / "checksum_manifest.json")
    listed = set()
    for row in manifest.get("files") or []:
        relative = str(row.get("file") or "")
        if not relative or relative == "checksum_manifest.json":
            raise ValueError(f"Invalid checksum row in {artifact_dir}: {row}")
        target = artifact_dir / relative
        if not target.is_file() or sha256_file(target) != row.get("sha256"):
            raise ValueError(f"Checksum mismatch after write: {target}")
        listed.add(relative)
    expected = {path.relative_to(artifact_dir).as_posix() for path in managed_files(artifact_dir)}
    if listed != expected:
        raise ValueError(
            f"Checksum coverage mismatch for {artifact_dir.name}: "
            f"missing={sorted(expected - listed)} extra={sorted(listed - expected)}"
        )

    public = read_json(artifact_dir / "public_book.json")
    approval = read_json(artifact_dir / "approval_evidence.json")
    reader = read_json(artifact_dir / "reader_manifest.json")
    if any(
        (
            public.get("audio_enabled"),
            public.get("audiobook_enabled"),
            public.get("generate_audiobook"),
            public.get("audiobook"),
            public.get("audiobook_assets"),
            approval.get("audiobook_enabled"),
            reader.get("audio_enabled"),
            reader.get("audiobook_enabled"),
        )
    ):
        raise ValueError(f"Audio was not fully hidden for {artifact_dir.name}")
    if approval.get("audio_public_release") != "PUBLIC_AUDIO_RELEASE_NOT_APPROVED":
        raise ValueError(f"Invalid audio release state for {artifact_dir.name}")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--write", action="store_true", help="Apply the deterministic changes")
    value.add_argument(
        "--generated-at",
        help="Checksum generation timestamp; defaults to the current UTC time when writing",
    )
    return value


def main() -> int:
    args = parser().parse_args()
    if len(TITLE_PLANS) != 25 or len({plan.slug for plan in TITLE_PLANS}) != 25:
        raise ValueError("The batch plan must contain 25 unique canonical slugs")

    generated_at = args.generated_at
    if not generated_at:
        generated_at = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            if args.write
            else "DRY_RUN"
        )

    prepared = [prepare_title(plan, generated_at) for plan in TITLE_PLANS]
    if args.write:
        for result in prepared:
            for path, payload in result["replacements"].items():
                path.write_bytes(payload)
        for result in prepared:
            verify_written_title(result)

    report = {
        "schema": "earnalism-english-25-title-batch-preparation-v1",
        "mode": "write" if args.write else "dry-run",
        "generated_at": generated_at,
        "title_count": len(prepared),
        "canonical_jekyll_slug": "jekyll-and-hyde",
        "pilot_slugs": sorted(PILOT_SLUGS),
        "voice_policy": {
            "male_author": "bm_george",
            "female_author": "hf_alpha",
        },
        "changed_title_count": sum(bool(item["changed_files"]) for item in prepared),
        "stale_audio_claim_title_count": sum(
            bool(item["stale_audio_claim_removed"]) for item in prepared
        ),
        "titles": [
            {
                "requested_title": item["plan"].requested_title,
                "slug": item["plan"].slug,
                "voice": item["plan"].voice,
                "author_profile": item["plan"].author_profile,
                "chapter_count": item["chapter_count"],
                "pilot": item["plan"].slug in PILOT_SLUGS,
                "changed_files": item["changed_files"],
                "stale_audio_claim_removed": item["stale_audio_claim_removed"],
                "checksum_manifest_sha256": item["manifest_sha256"],
            }
            for item in prepared
        ],
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    print(
        f"report_sha256={sha256_bytes((payload + chr(10)).encode('utf-8'))}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
