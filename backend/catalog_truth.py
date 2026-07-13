from __future__ import annotations

import json
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
ROOT = MODULE_DIR.parent if MODULE_DIR.name == "backend" else MODULE_DIR


def first_existing_path(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


CONTROLLED_ARTIFACT_REQUIRED_FILES = (
    "public_book.json",
    "reader_manifest.json",
    "approval_evidence.json",
    "source_evidence.json",
    "checksum_manifest.json",
)


def controlled_publications_root_candidates() -> tuple[Path, ...]:
    candidates = (
        ROOT / "data" / "controlled_publications",
        MODULE_DIR / "data" / "controlled_publications",
        Path.cwd() / "data" / "controlled_publications",
        Path.cwd() / "backend" / "data" / "controlled_publications",
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return tuple(unique)


def first_controlled_publications_root() -> Path:
    for candidate in controlled_publications_root_candidates():
        if candidate.exists():
            return candidate
    return controlled_publications_root_candidates()[0]


def controlled_artifact_dir_candidates(slug: str) -> tuple[Path, ...]:
    normalized = normalize_slug(slug) if "normalize_slug" in globals() else str(slug or "").strip().lower()
    return tuple(root / normalized for root in controlled_publications_root_candidates())


def first_controlled_artifact_dir(slug: str) -> Path:
    candidates = controlled_artifact_dir_candidates(slug)
    for candidate in candidates:
        if candidate.exists() and all((candidate / filename).exists() for filename in CONTROLLED_ARTIFACT_REQUIRED_FILES):
            return candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


CONTROLLED_LAUNCH_CONFIG_PATH = first_existing_path(
    ROOT / "data" / "controlled_launch.json",
    MODULE_DIR / "data" / "controlled_launch.json",
    Path.cwd() / "data" / "controlled_launch.json",
    Path.cwd() / "backend" / "data" / "controlled_launch.json",
)
DRACULA_ARTIFACT_DIR = first_controlled_artifact_dir("dracula")
CONTROLLED_PUBLICATIONS_DIR = first_controlled_publications_root()
DRACULA_REQUIRED_ARTIFACT_FILES = CONTROLLED_ARTIFACT_REQUIRED_FILES


def controlled_launch_config() -> dict[str, Any]:
    fallback = {
        "live_approved_slugs": ["dracula"],
        "pipeline_slugs": ["kshudhita-pashan"],
        "audio_enabled_slugs": [],
    }
    if not CONTROLLED_LAUNCH_CONFIG_PATH.exists():
        return fallback
    try:
        loaded = json.loads(CONTROLLED_LAUNCH_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback
    return loaded if isinstance(loaded, dict) else fallback


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_slug_tuple(values: Any, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, list):
        return fallback
    slugs = tuple(str(value or "").strip().lower() for value in values if str(value or "").strip())
    return slugs or fallback


CONTROLLED_LAUNCH_CONFIG = controlled_launch_config()
CONTROLLED_LIVE_BOOK_SLUGS = normalized_slug_tuple(
    CONTROLLED_LAUNCH_CONFIG.get("live_approved_slugs"),
    ("dracula",),
)
LIVE_APPROVED_SLUG = CONTROLLED_LIVE_BOOK_SLUGS[0]
PIPELINE_CANDIDATE_SLUGS = set(
    normalized_slug_tuple(CONTROLLED_LAUNCH_CONFIG.get("pipeline_slugs"), ("kshudhita-pashan",))
)
AUDIO_ENABLED_SLUGS = set(normalized_slug_tuple(CONTROLLED_LAUNCH_CONFIG.get("audio_enabled_slugs"), ()))

PUBLIC_STATUS_LIVE_APPROVED = "LIVE_APPROVED"
PUBLIC_STATUS_PIPELINE_CANDIDATE = "PIPELINE_CANDIDATE"
PUBLIC_STATUS_COMING_SOON = "COMING_SOON"
PUBLIC_STATUS_RIGHTS_REVIEW = "RIGHTS_REVIEW"
PUBLIC_STATUS_QUARANTINE = "QUARANTINE"
PUBLIC_STATUS_HIDDEN = "HIDDEN"
PUBLIC_AUDIO_RELEASE_APPROVED_STATUSES = {"APPROVED", "PUBLIC_AUDIO_RELEASE_APPROVED"}
PUBLIC_AUDIO_QA_PASSED_STATUSES = {"APPROVED", "PASS", "PASSED", "QA_PASSED"}

SAFE_PUBLIC_BOOK_FIELDS = {
    "id",
    "slug",
    "title",
    "subtitle",
    "author",
    "category_slug",
    "short_description",
    "description",
    "cover_url",
    "cover_image_url",
    "thumbnail_url",
    "blur_placeholder",
    "dominant_color",
    "back_cover_url",
    "back_cover_image_url",
    "back_cover_thumbnail_url",
    "back_cover_blur_placeholder",
    "back_cover_dominant_color",
    "estimated_reading_time",
    "formats",
    "benefits",
    "who_for",
    "learnings",
    "about_author",
    "chapters",
    "is_published",
    "created_at",
    "updated_at",
}

INTERNAL_RIGHTS_FIELDS = {
    "rights_metadata",
    "source_url",
    "source_name",
    "source_license",
    "source_text_url",
    "source_hash",
    "content_hash",
    "provenance_hash",
    "rights_basis",
    "rights_decision",
    "source_metadata",
    "source_evidence",
    "ingestion",
    "qa_issues",
    "source_load_issues",
}

INTERNAL_AUDIO_FIELDS = {
    "audio_assets",
    "audio_files",
    "audiobook_url",
    "audiobook",
    "audiobook_assets",
    "audiobook_assets_updated_at",
    "audiobook_provider",
    "audiobook_voice",
    "audio_asset_slug",
    "b2_url",
    "cloudinary_audio",
    "generate_audiobook",
    "has_audio",
    "listen_url",
    "narration_url",
    "voice_url",
    "waveform_url",
}


def normalize_slug(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_upper(value: Any) -> str:
    return normalize_text(value).upper()


def explicit_preview_chapter_ids(book: dict[str, Any]) -> tuple[str, ...]:
    """Return only chapter ids carrying an explicit preview approval marker."""
    chapters = book.get("chapters")
    if not isinstance(chapters, list):
        return ()
    preview_ids: list[str] = []
    seen: set[str] = set()
    for chapter in chapters:
        if not isinstance(chapter, dict) or chapter.get("is_preview") is not True:
            continue
        chapter_id = normalize_text(chapter.get("id"))
        if chapter_id and chapter_id not in seen:
            seen.add(chapter_id)
            preview_ids.append(chapter_id)
    return tuple(preview_ids)


def nested_dict(book: dict[str, Any], key: str) -> dict[str, Any]:
    value = book.get(key)
    return value if isinstance(value, dict) else {}


@lru_cache(maxsize=64)
def controlled_audio_release_evidence(slug: str) -> dict[str, Any]:
    normalized = normalize_slug(slug)
    if not normalized:
        return {}
    return read_json_file(first_controlled_artifact_dir(normalized) / "approval_evidence.json")


def audio_public_release_status(book: dict[str, Any]) -> str:
    evidence = controlled_audio_release_evidence(normalize_slug(book.get("slug")))
    if evidence:
        return normalize_upper(
            evidence.get("audio_public_release") or evidence.get("public_audio_release")
        )
    audiobook = nested_dict(book, "audiobook")
    return normalize_upper(
        book.get("audio_public_release")
        or book.get("public_audio_release")
        or book.get("audiobook_release_gate")
        or audiobook.get("release_gate")
    )


def audio_release_qa_status(book: dict[str, Any]) -> str:
    evidence = controlled_audio_release_evidence(normalize_slug(book.get("slug")))
    if evidence:
        return normalize_upper(evidence.get("audio_qa_status") or evidence.get("qa_status"))
    audiobook = nested_dict(book, "audiobook")
    return normalize_upper(book.get("audio_qa_status") or audiobook.get("qa_status"))


def safe_public_value(key: str, value: Any) -> Any:
    if key != "chapters" or not isinstance(value, list):
        return value
    chapters: list[dict[str, Any]] = []
    for chapter in value:
        if not isinstance(chapter, dict):
            continue
        chapters.append({field: chapter.get(field) for field in chapter if field != "content"})
    return chapters


def safe_public_fields(book: dict[str, Any]) -> dict[str, Any]:
    return {
        key: safe_public_value(key, book.get(key))
        for key in SAFE_PUBLIC_BOOK_FIELDS
        if key in book
    }


def first_text(book: dict[str, Any], *keys: str, fallback_evidence: dict[str, Any] | None = None) -> str:
    sources: list[dict[str, Any]] = [book, nested_dict(book, "rights_metadata"), nested_dict(book, "source_metadata"), nested_dict(book, "ingestion")]
    if fallback_evidence:
        sources.append(fallback_evidence)
        rights_metadata = nested_dict(fallback_evidence, "rights_decision").get("metadata", {})
        if isinstance(rights_metadata, dict):
            sources.append(rights_metadata)
        sources.append(nested_dict(fallback_evidence, "ingestion"))
    for source in sources:
        for key in keys:
            value = source.get(key)
            if normalize_text(value):
                return normalize_text(value)
    return ""


@lru_cache(maxsize=1)
def dracula_approval_evidence() -> dict[str, Any]:
    evidence_path = ROOT / "output" / "publication_candidates" / "dracula" / "source_evidence.json"
    approval_path = ROOT / "APPROVED_TO_PUBLISH.md"
    payload: dict[str, Any] = {}
    if evidence_path.exists():
        try:
            loaded = json.loads(evidence_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload.update(loaded)
        except json.JSONDecodeError:
            payload["source_evidence_error"] = "invalid_json"
    payload["approved_to_publish_artifact"] = (
        approval_path.exists()
        and "Work Slug: dracula" in approval_path.read_text(encoding="utf-8", errors="ignore")
    )
    return payload


def _artifact_dir(path: str | Path | None = None) -> Path:
    return Path(path) if path else first_controlled_artifact_dir("dracula")


def _artifact_json(name: str, *, artifact_dir: str | Path | None = None) -> dict[str, Any]:
    return read_json_file(_artifact_dir(artifact_dir) / name)


def controlled_artifact_dir(slug: str) -> Path:
    return first_controlled_artifact_dir(normalize_slug(slug))


@lru_cache(maxsize=8)
def dracula_artifact_validation_issues(artifact_dir: str = "") -> tuple[str, ...]:
    base = _artifact_dir(artifact_dir or None)
    issues: list[str] = []
    if not base.exists():
        return ("Dracula artifact directory is missing.",)

    for filename in DRACULA_REQUIRED_ARTIFACT_FILES:
        if not (base / filename).exists():
            issues.append(f"Missing required Dracula artifact file: {filename}")

    public_book = _artifact_json("public_book.json", artifact_dir=base)
    reader_manifest = _artifact_json("reader_manifest.json", artifact_dir=base)
    approval_evidence = _artifact_json("approval_evidence.json", artifact_dir=base)
    source_evidence = _artifact_json("source_evidence.json", artifact_dir=base)
    checksum_manifest = _artifact_json("checksum_manifest.json", artifact_dir=base)

    if normalize_slug(public_book.get("slug")) != LIVE_APPROVED_SLUG:
        issues.append("public_book.json slug is not dracula.")
    if normalize_text(public_book.get("title")) != "Dracula":
        issues.append("public_book.json title is not Dracula.")
    if normalize_text(public_book.get("author")) != "Bram Stoker":
        issues.append("public_book.json author is not Bram Stoker.")
    if public_book.get("is_published") is not True:
        issues.append("public_book.json is_published is not true.")
    if normalize_upper(public_book.get("rights_tier")) != "A":
        issues.append("public_book.json rights_tier is not Tier A.")
    if normalize_text(public_book.get("verification_status")).lower() not in {"approved", "verified"}:
        issues.append("public_book.json verification_status is not approved.")
    if normalize_upper(public_book.get("qa_status")) not in {"QA_PASSED", "PASS", "PASSED"}:
        issues.append("public_book.json qa_status is not QA_PASSED.")
    if public_book.get("approved_to_publish") is not True:
        issues.append("public_book.json approved_to_publish is not true.")
    if public_book.get("audio_enabled", False) is not False or public_book.get("audiobook_enabled", False) is not False:
        issues.append("public_book.json audio flags are not disabled.")

    for key in ("source_hash", "content_hash", "provenance_hash"):
        if not normalize_text(source_evidence.get(key)):
            issues.append(f"source_evidence.json missing {key}.")

    if normalize_text(source_evidence.get("source_url")) != "https://www.gutenberg.org/ebooks/345":
        issues.append("source_evidence.json source_url is not Project Gutenberg eBook #345.")
    if "Project Gutenberg" not in normalize_text(source_evidence.get("source_name")):
        issues.append("source_evidence.json source_name is not Project Gutenberg.")
    if "Project Gutenberg" not in normalize_text(source_evidence.get("source_license")):
        issues.append("source_evidence.json source_license is not Project Gutenberg License.")

    if approval_evidence.get("approved_to_publish") is not True:
        issues.append("approval_evidence.json approved_to_publish is not true.")
    if normalize_upper(approval_evidence.get("rights_tier")) != "A":
        issues.append("approval_evidence.json rights_tier is not Tier A.")
    if normalize_text(approval_evidence.get("verification_status")).lower() not in {"approved", "verified"}:
        issues.append("approval_evidence.json verification_status is not approved.")
    if normalize_upper(approval_evidence.get("qa_status")) not in {"QA_PASSED", "PASS", "PASSED"}:
        issues.append("approval_evidence.json qa_status is not QA_PASSED.")

    manifest_chapters = reader_manifest.get("chapters")
    if int(reader_manifest.get("chapter_count") or 0) != 27:
        issues.append("reader_manifest.json chapter_count is not 27.")
    if not isinstance(manifest_chapters, list) or len(manifest_chapters) != 27:
        issues.append("reader_manifest.json does not contain 27 chapter metadata records.")
    if reader_manifest.get("audio_enabled") is not False or reader_manifest.get("audiobook_enabled") is not False:
        issues.append("reader_manifest.json audio flags are not disabled.")
    if "chapter-001" not in (reader_manifest.get("preview_chapter_ids") or []):
        issues.append("reader_manifest.json does not unlock chapter-001 as preview.")

    chapter_dir = base / "chapters"
    chapter_files = sorted(chapter_dir.glob("chapter-*.json"))
    if len(chapter_files) != 27:
        issues.append(f"Expected 27 Dracula chapter files, found {len(chapter_files)}.")
    for index in range(1, 28):
        expected = chapter_dir / f"chapter-{index:03d}.json"
        chapter = read_json_file(expected)
        if not chapter:
            issues.append(f"Missing or invalid Dracula chapter file: {expected.name}")
            continue
        if normalize_text(chapter.get("id")) != f"chapter-{index:03d}":
            issues.append(f"{expected.name} has the wrong id.")
        if int(chapter.get("order") or 0) != index:
            issues.append(f"{expected.name} has the wrong order.")
        if not normalize_text(chapter.get("title")):
            issues.append(f"{expected.name} is missing title.")
        if not normalize_text(chapter.get("content")):
            issues.append(f"{expected.name} is missing content.")

    checksum_files = checksum_manifest.get("files")
    if not isinstance(checksum_files, list):
        issues.append("checksum_manifest.json files list is missing.")
    else:
        for entry in checksum_files:
            if not isinstance(entry, dict):
                issues.append("checksum_manifest.json contains an invalid file entry.")
                continue
            rel = normalize_text(entry.get("file"))
            expected_hash = normalize_text(entry.get("sha256"))
            if not rel or not expected_hash:
                issues.append("checksum_manifest.json file entry is missing path or sha256.")
                continue
            target = base / rel
            if not target.exists():
                issues.append(f"Checksum target is missing: {rel}")
                continue
            if rel == "checksum_manifest.json":
                continue
            if file_sha256(target) != expected_hash:
                issues.append(f"Checksum mismatch for Dracula artifact: {rel}")

    return tuple(issues)


def dracula_artifact_status(*, artifact_dir: str | Path | None = None) -> dict[str, Any]:
    base = _artifact_dir(artifact_dir)
    issues = list(dracula_artifact_validation_issues(str(base)))
    public_book = _artifact_json("public_book.json", artifact_dir=base)
    reader_manifest = _artifact_json("reader_manifest.json", artifact_dir=base)
    artifact_book = load_dracula_artifact_book(include_content=False, artifact_dir=base) if not issues else None
    self_contained_for_truth_gate = bool(artifact_book and is_live_approved_book(artifact_book))
    return {
        "available": not issues,
        "artifact_dir": str(base),
        "issues": issues,
        "slug": normalize_slug(public_book.get("slug")),
        "title": normalize_text(public_book.get("title")),
        "chapter_count": int(reader_manifest.get("chapter_count") or 0),
        "audio_enabled": bool(public_book.get("audio_enabled", False)),
        "audiobook_enabled": bool(public_book.get("audiobook_enabled", False)),
        "self_contained_for_truth_gate": self_contained_for_truth_gate,
        "fallback_requires_legacy_output_evidence": not self_contained_for_truth_gate,
    }


def load_dracula_artifact_book(
    *,
    include_content: bool = False,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    base = _artifact_dir(artifact_dir)
    if dracula_artifact_validation_issues(str(base)):
        return None
    public_book = _artifact_json("public_book.json", artifact_dir=base)
    approval_evidence = _artifact_json("approval_evidence.json", artifact_dir=base)
    source_evidence = _artifact_json("source_evidence.json", artifact_dir=base)
    chapters: list[dict[str, Any]] = []
    for chapter_meta in sorted(public_book.get("chapters") or [], key=lambda item: item.get("order", 0)):
        chapter_id = normalize_text(chapter_meta.get("id"))
        chapter = dict(chapter_meta)
        if include_content and chapter_id:
            content_payload = read_json_file(base / "chapters" / f"{chapter_id}.json")
            chapter["content"] = content_payload.get("content", "")
            chapter["content_hash"] = content_payload.get("content_hash", "")
        chapters.append(chapter)

    def evidence_value(key: str, default: Any = "") -> Any:
        for source in (approval_evidence, source_evidence, public_book):
            if key in source and source.get(key) not in (None, ""):
                return source.get(key)
        return default

    return {
        **public_book,
        "chapters": chapters,
        "source_url": evidence_value("source_url"),
        "source_name": evidence_value("source_name"),
        "source_license": evidence_value("source_license"),
        "source_hash": evidence_value("source_hash"),
        "content_hash": evidence_value("content_hash"),
        "provenance_hash": evidence_value("provenance_hash"),
        "rights_basis": evidence_value("rights_basis"),
        "approved_to_publish": bool(evidence_value("approved_to_publish", True)),
        "publication_status": PUBLIC_STATUS_LIVE_APPROVED,
        "rights_tier": evidence_value("rights_tier", "A"),
        "verification_status": evidence_value("verification_status", "approved"),
        "qa_status": evidence_value("qa_status", "QA_PASSED"),
        "audio_enabled": False,
        "audiobook_enabled": False,
        "generate_audiobook": False,
        "audiobook_assets": {},
        "audiobook": {},
    }


CONTROLLED_REQUIRED_ARTIFACT_FILES = DRACULA_REQUIRED_ARTIFACT_FILES


@lru_cache(maxsize=64)
def controlled_artifact_validation_issues(slug: str, artifact_dir: str = "") -> tuple[str, ...]:
    normalized = normalize_slug(slug)
    if normalized == "dracula":
        return dracula_artifact_validation_issues(artifact_dir)
    base = Path(artifact_dir) if artifact_dir else controlled_artifact_dir(normalized)
    issues: list[str] = []
    if normalized not in CONTROLLED_LIVE_BOOK_SLUGS:
        issues.append(f"{normalized or 'unknown'} is not in the controlled live allowlist.")
    if not base.exists():
        return (f"Controlled publication artifact directory is missing for {normalized}.",)
    for filename in CONTROLLED_REQUIRED_ARTIFACT_FILES:
        if not (base / filename).exists():
            issues.append(f"Missing required controlled artifact file for {normalized}: {filename}")
    public_book = read_json_file(base / "public_book.json")
    reader_manifest = read_json_file(base / "reader_manifest.json")
    source_evidence = read_json_file(base / "source_evidence.json")
    approval_evidence = read_json_file(base / "approval_evidence.json")
    if normalize_slug(public_book.get("slug")) != normalized:
        issues.append("public_book.json slug does not match artifact slug.")
    if public_book.get("is_published") is not True:
        issues.append("public_book.json is_published is not true.")
    if public_book.get("isPublic") is not True or public_book.get("isLive") is not True:
        issues.append("public_book.json public/live flags are not true.")
    if public_book.get("showInHomepage") is not False:
        issues.append("public_book.json showInHomepage must remain false for batch 1.")
    if public_book.get("allowCheckout") is not False or public_book.get("allowPayment") is not False:
        issues.append("public_book.json checkout/payment flags must remain false.")
    audio_allowed = normalized in AUDIO_ENABLED_SLUGS
    if not audio_allowed and (public_book.get("audio_enabled") is not False or public_book.get("audiobook_enabled") is not False):
        issues.append("public_book.json audio flags are not disabled.")
    if audio_allowed:
        assets = public_book.get("audiobook_assets") if isinstance(public_book.get("audiobook_assets"), dict) else {}
        if not assets.get("mp3") or not assets.get("timestamps"):
            issues.append("public_book.json audiobook assets are incomplete for an audio-enabled slug.")
    if public_book.get("approved_to_publish") is not True:
        issues.append("public_book.json approved_to_publish is not true.")
    if normalize_text(public_book.get("verification_status")).lower() not in {"approved", "verified"}:
        issues.append("public_book.json verification_status is not approved.")
    if normalize_upper(public_book.get("qa_status")) not in {"QA_PASSED", "PASS", "PASSED"}:
        issues.append("public_book.json qa_status is not QA_PASSED.")
    if int(reader_manifest.get("chapter_count") or 0) <= 0:
        issues.append("reader_manifest.json chapter_count must be greater than zero.")
    if reader_manifest.get("audio_enabled") is not False or reader_manifest.get("audiobook_enabled") is not False:
        issues.append("reader_manifest.json audio flags are not disabled.")
    manifest_preview_ids = {
        normalize_text(chapter_id)
        for chapter_id in (reader_manifest.get("preview_chapter_ids") or [])
        if normalize_text(chapter_id)
    }
    manifest_chapter_preview_ids = set(explicit_preview_chapter_ids(reader_manifest))
    public_chapter_preview_ids = set(explicit_preview_chapter_ids(public_book))
    if manifest_preview_ids != manifest_chapter_preview_ids:
        issues.append("reader_manifest.json preview_chapter_ids do not match explicit chapter preview markers.")
    if manifest_chapter_preview_ids != public_chapter_preview_ids:
        issues.append("public_book.json and reader_manifest.json explicit preview chapters do not match.")
    for key in ("source_hash", "content_hash", "provenance_hash"):
        if not normalize_text(source_evidence.get(key)):
            issues.append(f"source_evidence.json missing {key}.")
    if not normalize_text(source_evidence.get("source_url")):
        issues.append("source_evidence.json missing source_url.")
    if approval_evidence.get("approved_to_publish") is not True:
        issues.append("approval_evidence.json approved_to_publish is not true.")
    return tuple(issues)


def controlled_artifact_status(slug: str, *, artifact_dir: str | Path | None = None) -> dict[str, Any]:
    normalized = normalize_slug(slug)
    base = Path(artifact_dir) if artifact_dir else controlled_artifact_dir(normalized)
    issues = list(controlled_artifact_validation_issues(normalized, str(base)))
    public_book = read_json_file(base / "public_book.json")
    reader_manifest = read_json_file(base / "reader_manifest.json")
    artifact_book = load_controlled_artifact_book(normalized, include_content=False, artifact_dir=base) if not issues else None
    self_contained_for_truth_gate = bool(artifact_book and is_live_approved_book(artifact_book))
    return {
        "available": not issues,
        "artifact_dir": str(base),
        "issues": issues,
        "slug": normalize_slug(public_book.get("slug")),
        "title": normalize_text(public_book.get("title")),
        "chapter_count": int(reader_manifest.get("chapter_count") or 0),
        "audio_enabled": bool(public_book.get("audio_enabled", False)),
        "audiobook_enabled": bool(public_book.get("audiobook_enabled", False)),
        "self_contained_for_truth_gate": self_contained_for_truth_gate,
        "fallback_requires_legacy_output_evidence": False,
    }


def load_controlled_artifact_book(
    slug: str,
    *,
    include_content: bool = False,
    artifact_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    normalized = normalize_slug(slug)
    if normalized == "dracula":
        return load_dracula_artifact_book(include_content=include_content, artifact_dir=artifact_dir)
    base = Path(artifact_dir) if artifact_dir else controlled_artifact_dir(normalized)
    if controlled_artifact_validation_issues(normalized, str(base)):
        return None
    public_book = read_json_file(base / "public_book.json")
    approval_evidence = read_json_file(base / "approval_evidence.json")
    source_evidence = read_json_file(base / "source_evidence.json")
    chapters: list[dict[str, Any]] = []
    for chapter_meta in sorted(public_book.get("chapters") or [], key=lambda item: item.get("order", 0)):
        chapter_id = normalize_text(chapter_meta.get("id"))
        chapter = dict(chapter_meta)
        if include_content and chapter_id:
            content_payload = read_json_file(base / "chapters" / f"{chapter_id}.json")
            chapter["content"] = content_payload.get("content", "")
            chapter["content_hash"] = content_payload.get("content_hash", "")
        chapters.append(chapter)

    def evidence_value(key: str, default: Any = "") -> Any:
        for source in (approval_evidence, source_evidence, public_book):
            if key in source and source.get(key) not in (None, ""):
                return source.get(key)
        return default

    audio_allowed = normalized in AUDIO_ENABLED_SLUGS
    artifact_audio_enabled = bool(public_book.get("audio_enabled", False)) if audio_allowed else False
    artifact_audiobook_enabled = bool(public_book.get("audiobook_enabled", False)) if audio_allowed else False
    artifact_generate_audiobook = bool(public_book.get("generate_audiobook", False)) if audio_allowed else False
    artifact_audiobook_assets = (
        dict(public_book.get("audiobook_assets"))
        if audio_allowed and isinstance(public_book.get("audiobook_assets"), dict)
        else {}
    )
    artifact_audiobook = (
        dict(public_book.get("audiobook"))
        if audio_allowed and isinstance(public_book.get("audiobook"), dict)
        else {}
    )

    return {
        **public_book,
        "chapters": chapters,
        "source_url": evidence_value("source_url"),
        "source_name": evidence_value("source_name"),
        "source_license": evidence_value("source_license"),
        "source_hash": evidence_value("source_hash"),
        "content_hash": evidence_value("content_hash"),
        "provenance_hash": evidence_value("provenance_hash"),
        "rights_basis": evidence_value("rights_basis"),
        "approved_to_publish": bool(evidence_value("approved_to_publish", True)),
        "publication_status": PUBLIC_STATUS_LIVE_APPROVED,
        "rights_tier": evidence_value("rights_tier", "A"),
        "verification_status": evidence_value("verification_status", "approved"),
        "qa_status": evidence_value("qa_status", "QA_PASSED"),
        "audio_enabled": artifact_audio_enabled,
        "audiobook_enabled": artifact_audiobook_enabled,
        "generate_audiobook": artifact_generate_audiobook,
        "audiobook_provider": public_book.get("audiobook_provider", "") if audio_allowed else "",
        "audiobook_voice": public_book.get("audiobook_voice", "") if audio_allowed else "",
        "audio_asset_slug": public_book.get("audio_asset_slug", normalized) if audio_allowed else normalized,
        "audiobook_assets_updated_at": public_book.get("audiobook_assets_updated_at", "") if audio_allowed else "",
        "audiobook_assets": artifact_audiobook_assets,
        "audiobook": artifact_audiobook,
    }


def evidence_for_book(book: dict[str, Any]) -> dict[str, Any]:
    return dracula_approval_evidence() if normalize_slug(book.get("slug")) == LIVE_APPROVED_SLUG else {}


def rights_tier(book: dict[str, Any]) -> str:
    return normalize_upper(first_text(book, "rights_tier", fallback_evidence=evidence_for_book(book)))


def verification_status(book: dict[str, Any]) -> str:
    return normalize_text(first_text(book, "verification_status", fallback_evidence=evidence_for_book(book))).lower()


def qa_status(book: dict[str, Any]) -> str:
    return normalize_upper(first_text(book, "qa_status", "source_qa_status", fallback_evidence=evidence_for_book(book)))


def blocked_reason(book: dict[str, Any]) -> str:
    return first_text(book, "blocked_reason", fallback_evidence=evidence_for_book(book))


def publication_status(book: dict[str, Any]) -> str:
    return normalize_upper(first_text(book, "publication_status", "launch_status", fallback_evidence=evidence_for_book(book)))


def approved_to_publish(book: dict[str, Any]) -> bool:
    evidence = evidence_for_book(book)
    explicit = book.get("approved_to_publish")
    if isinstance(explicit, bool):
        return explicit
    status = publication_status(book)
    return bool(
        explicit
        or evidence.get("approved_to_publish_artifact")
        or status in {"LIVE_APPROVED", "APPROVED_TO_PUBLISH", "PUBLISHED_CORE_READING_ONLY"}
    )


def traceability_hashes(book: dict[str, Any]) -> dict[str, str]:
    evidence = evidence_for_book(book)
    return {
        "source_hash": first_text(book, "source_hash", fallback_evidence=evidence),
        "content_hash": first_text(book, "content_hash", fallback_evidence=evidence),
        "provenance_hash": first_text(book, "provenance_hash", fallback_evidence=evidence),
    }


def source_metadata_present(book: dict[str, Any]) -> bool:
    evidence = evidence_for_book(book)
    return all(
        first_text(book, key, fallback_evidence=evidence)
        for key in ("source_url", "source_name", "source_license")
    )


def is_live_approved_book(book: dict[str, Any]) -> bool:
    if normalize_slug(book.get("slug")) not in CONTROLLED_LIVE_BOOK_SLUGS:
        return False
    if book.get("is_published") is not True:
        return False
    if rights_tier(book) != "A":
        return False
    if verification_status(book) not in {"approved", "verified", "published_core_reading_only"}:
        return False
    if blocked_reason(book):
        return False
    if qa_status(book) not in {"QA_PASSED", "PASS", "PASSED"}:
        return False
    hashes = traceability_hashes(book)
    if not all(hashes.values()):
        return False
    if not source_metadata_present(book):
        return False
    return approved_to_publish(book)


def is_pipeline_candidate(book: dict[str, Any]) -> bool:
    slug = normalize_slug(book.get("slug"))
    if not slug or slug in CONTROLLED_LIVE_BOOK_SLUGS:
        return False
    if slug in PIPELINE_CANDIDATE_SLUGS:
        return True
    stage = normalize_upper(book.get("pipeline_stage"))
    status = publication_status(book)
    return "PIPELINE" in stage or status in {"PIPELINE_CANDIDATE", "COMING_SOON_PIPELINE"}


def normalize_book_publication_status(book: dict[str, Any]) -> str:
    if is_live_approved_book(book):
        return PUBLIC_STATUS_LIVE_APPROVED
    if is_pipeline_candidate(book):
        return PUBLIC_STATUS_PIPELINE_CANDIDATE
    if rights_tier(book) == "C" or blocked_reason(book):
        return PUBLIC_STATUS_QUARANTINE
    if book.get("is_published") is not True:
        return PUBLIC_STATUS_HIDDEN
    if rights_tier(book) != "A" or verification_status(book) not in {"approved", "verified"}:
        return PUBLIC_STATUS_RIGHTS_REVIEW
    return PUBLIC_STATUS_COMING_SOON


def can_expose_reader(book: dict[str, Any]) -> bool:
    return is_live_approved_book(book)


def can_expose_preview(book: dict[str, Any]) -> bool:
    return is_live_approved_book(book) and bool(explicit_preview_chapter_ids(book))


def can_expose_audio(book: dict[str, Any]) -> bool:
    slug = normalize_slug(book.get("slug"))
    if slug not in AUDIO_ENABLED_SLUGS or not is_live_approved_book(book):
        return False
    evidence = controlled_audio_release_evidence(slug)
    if evidence and evidence.get("audiobook_enabled") is not True:
        return False
    return (
        audio_public_release_status(book) in PUBLIC_AUDIO_RELEASE_APPROVED_STATUSES
        and audio_release_qa_status(book) in PUBLIC_AUDIO_QA_PASSED_STATUSES
    )


def public_pipeline_projection(book: dict[str, Any]) -> dict[str, Any]:
    projected = safe_public_fields(book)
    projected.update(
        {
            "publication_status": PUBLIC_STATUS_PIPELINE_CANDIDATE,
            "launch_status": PUBLIC_STATUS_PIPELINE_CANDIDATE,
            "reader_enabled": False,
            "preview_enabled": False,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "public_route": "",
            "reader_url": "",
            "preview_url": "",
            "audio_url": "",
            "audio_status": "BLOCKED_UNTIL_RIGHTS_QA",
            "cta_label": "Notify Me",
            "secondary_cta_label": "Reading Circle",
            "public_json_ld_enabled": False,
            "source_note": "Source and rights verification are still in the pipeline.",
            "rights_note": "Not publicly readable until rights and QA approval are complete.",
        }
    )
    for field in [*INTERNAL_RIGHTS_FIELDS, *INTERNAL_AUDIO_FIELDS]:
        projected.pop(field, None)
    return projected


def public_book_projection(book: dict[str, Any] | None) -> dict[str, Any] | None:
    if not book:
        return book
    status = normalize_book_publication_status(book)
    if status == PUBLIC_STATUS_PIPELINE_CANDIDATE:
        return public_pipeline_projection(book)

    projected = safe_public_fields(book)
    slug = normalize_slug(book.get("slug"))
    live = status == PUBLIC_STATUS_LIVE_APPROVED
    preview = live and can_expose_preview(book)
    projected.update(
        {
            "publication_status": status,
            "launch_status": status,
            "reader_enabled": live,
            "preview_enabled": preview,
            "audio_enabled": False,
            "audiobook_enabled": False,
            "public_route": f"/book/{slug}" if live else "",
            "reader_url": f"/reader/{slug}" if live else "",
            "preview_url": f"/reader/{slug}" if preview else "",
            "audio_url": "",
            "audio_status": "NOT_AVAILABLE" if live else "BLOCKED_UNTIL_RIGHTS_QA",
            "cta_label": (
                "Start Dracula"
                if live and slug == LIVE_APPROVED_SLUG
                else "Read"
                if live
                else "Notify Me"
            ),
            "secondary_cta_label": (
                "Read Chapter 1 Free"
                if preview and slug == LIVE_APPROVED_SLUG
                else "Read Free Preview"
                if preview
                else "Details"
                if live
                else "Coming Soon"
            ),
            "public_json_ld_enabled": live,
            "source_note": (
                "Source verified for the controlled Dracula reading launch."
                if live and slug == LIVE_APPROVED_SLUG
                else "Public-domain source verified for controlled reading."
                if live
                else "Source and rights verification are still in the pipeline."
            ),
            "rights_note": (
                "Approved classic reading release."
                if live
                else "Not publicly readable until rights and QA approval are complete."
            ),
        }
    )
    for field in [*INTERNAL_RIGHTS_FIELDS, *INTERNAL_AUDIO_FIELDS]:
        projected.pop(field, None)
    return projected


def live_approved_mongo_query(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch controlled-launch candidates; Python truth gates decide exposure.

    Production data can lag the file-backed Dracula approval artifact. Public
    endpoints therefore fetch only the explicit controlled slugs from MongoDB,
    then call `public_book_projection`/`can_expose_reader` before anything is
    exposed. This avoids both broad catalog leaks and false negatives caused by
    incomplete DB rights metadata.
    """

    query: dict[str, Any] = {
        "slug": {"$in": list(CONTROLLED_LIVE_BOOK_SLUGS)},
        "is_published": True,
    }
    if extra:
        for key, value in extra.items():
            query[key] = value
    return query


def catalog_truth_row(book: dict[str, Any], *, sitemap_urls: set[str] | None = None) -> dict[str, Any]:
    slug = normalize_slug(book.get("slug"))
    status = normalize_book_publication_status(book)
    sitemap_urls = sitemap_urls or set()
    hashes = traceability_hashes(book)
    return {
        "slug": slug,
        "title": normalize_text(book.get("title")),
        "author": normalize_text(book.get("author")),
        "classification": status,
        "is_published": bool(book.get("is_published")),
        "publication_status": publication_status(book) or status,
        "rights_tier": rights_tier(book) or "UNKNOWN",
        "verification_status": verification_status(book) or "unknown",
        "qa_status": qa_status(book) or "unknown",
        "approved_to_publish": approved_to_publish(book),
        "reader_enabled": can_expose_reader(book),
        "preview_enabled": can_expose_preview(book),
        "audio_enabled": can_expose_audio(book),
        "audiobook_enabled": False,
        "source_url_present": bool(first_text(book, "source_url", fallback_evidence=evidence_for_book(book))),
        "source_hash_present": bool(hashes["source_hash"]),
        "content_hash_present": bool(hashes["content_hash"]),
        "provenance_hash_present": bool(hashes["provenance_hash"]),
        "public_route": f"/book/{slug}" if status == PUBLIC_STATUS_LIVE_APPROVED else "",
        "reader_route": f"/reader/{slug}" if status == PUBLIC_STATUS_LIVE_APPROVED else "",
        "sitemap_inclusion": f"/book/{slug}" in sitemap_urls or f"https://theearnalism.com/book/{slug}" in sitemap_urls,
    }


def catalog_truth_summary(
    rows: list[dict[str, Any]],
    *,
    sitemap_urls: set[str] | None = None,
    frontend_live_slugs: set[str] | None = None,
) -> dict[str, Any]:
    sitemap_urls = sitemap_urls or set()
    live_rows = [row for row in rows if row["classification"] == PUBLIC_STATUS_LIVE_APPROVED]
    pipeline_rows = [row for row in rows if row["classification"] == PUBLIC_STATUS_PIPELINE_CANDIDATE]
    unapproved_reader = [row for row in rows if row["classification"] != PUBLIC_STATUS_LIVE_APPROVED and row["reader_enabled"]]
    unapproved_audio = [row for row in rows if row["classification"] != PUBLIC_STATUS_LIVE_APPROVED and row["audio_enabled"]]
    unapproved_sitemap = [
        row
        for row in rows
        if row["classification"] != PUBLIC_STATUS_LIVE_APPROVED and row["sitemap_inclusion"]
    ]
    backend_live_slugs = {row["slug"] for row in live_rows}
    if frontend_live_slugs is None:
        backend_frontend_truth_mismatch: bool | str = "not_checked"
    else:
        backend_frontend_truth_mismatch = backend_live_slugs != frontend_live_slugs
    return {
        "live_approved_count": len(live_rows),
        "dracula_only_live_approved": [row["slug"] for row in live_rows] == [LIVE_APPROVED_SLUG],
        "backend_live_approved_slugs": sorted(backend_live_slugs),
        "frontend_controlled_live_slugs": sorted(frontend_live_slugs) if frontend_live_slugs is not None else [],
        "pipeline_candidate_count": len(pipeline_rows),
        "unapproved_reader_link_count": len(unapproved_reader),
        "unapproved_audio_link_count": len(unapproved_audio),
        "unapproved_sitemap_count": len(unapproved_sitemap),
        "backend_frontend_truth_mismatch": backend_frontend_truth_mismatch,
        "launch_blockers": ["Unapproved reader links detected"] * bool(unapproved_reader)
        + ["Unapproved audio links detected"] * bool(unapproved_audio)
        + ["Unapproved sitemap entries detected"] * bool(unapproved_sitemap)
        + ["Backend/frontend controlled live slug mismatch"] * bool(backend_frontend_truth_mismatch is True),
    }
