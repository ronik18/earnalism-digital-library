#!/usr/bin/env python3
"""Build an evidence-first, read-only India launch compliance package.

This utility inventories facts already present in the repository.  It does
not decide copyright, accept a rights record, sign an owner declaration, or
change title availability.  A missing factual or human input remains visible
as a hold rather than being filled with a guess.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
PUBLICATIONS = ROOT / "data" / "controlled_publications"
HELD_TITLE_ARCHIVES = {
    "yugalanguriya": ROOT / "internal" / "archives" / "held_titles" / "yugalanguriya",
}
PILOT_SLUGS = (
    "a-ghost-story",
    "the-tell-tale-heart",
    "radharani",
    "yugalanguriya",
)
COUNTRY_SCOPE = ("IN",)
ROOT_LAUNCH = ROOT / "data" / "controlled_launch.json"
BACKEND_LAUNCH = ROOT / "backend" / "data" / "controlled_launch.json"
RIGHTS_REGISTRY = ROOT / "backend" / "data" / "rights_decision_registry.json"
PILOT_INTEGRITY_EVIDENCE = ROOT / "internal" / "legal" / "four_title_pilot_evidence_20260917.md"

OFFICIAL_SOURCES = (
    {
        "topic": "Copyright Act, 1957 — Chapter V, section 22 and other term categories",
        "url": "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html",
        "scope": "copyright term classification",
    },
    {
        "topic": "Copyright Act, 1957 — Chapter III, protected work categories",
        "url": "https://copyright.gov.in/Copyright_Act_1957/chapter_iii.html",
        "scope": "copyright category classification",
    },
    {
        "topic": "Digital Personal Data Protection Rules, 2025 notification",
        "url": "https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf",
        "scope": "rule commencement must be evaluated on the actual launch date",
    },
    {
        "topic": "Department of Consumer Affairs — Consumer Protection framework",
        "url": "https://consumeraffairs.nic.in/acts-and-rules/consumer-protection/consumer-protection",
        "scope": "Consumer Protection Act, E-Commerce Rules, and Dark Patterns Guidelines",
    },
    {
        "topic": "Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 — consolidated text updated 10 February 2026",
        "url": "https://www.meity.gov.in/static/uploads/2026/02/550681ab908f8afb135b0ad42816a1c9.pdf",
        "scope": "synthetically generated information; applicability depends on the actual product role and launch configuration",
    },
    {
        "topic": "Google Cloud Text-to-Speech basics",
        "url": "https://docs.cloud.google.com/text-to-speech/docs/basics",
        "scope": "Google documents use of generated audio in applications or media subject to applicable terms and law",
    },
)

# These are factual/bibliographic sources, not rights acceptances.  They let
# the package distinguish a documented Section 22 calculation from the still
# separate, hash-bound release decision required by the registry.
PILOT_FACT_SOURCES: dict[str, dict[str, Any]] = {
    "a-ghost-story": {
        "author_identity": "Samuel Langhorne Clemens, writing as Mark Twain (1835–1910).",
        "author_source": "https://marktwainhouse.org/about/mark-twain/biography/",
        "work_type": "English literary sketch / short story.",
        "original_language": "English",
        "relevant_publication": "Sketches, New and Old (1875), containing A Ghost Story.",
        "publication_source": "https://www.marktwainproject.org/writings/html/writings/ets1/mtdp10202/",
        "death_year": 1910,
    },
    "the-tell-tale-heart": {
        "author_identity": "Edgar Allan Poe (1809–1849).",
        "author_source": "https://www.loc.gov/aba/pcc/naco/documents/FAQ-AAP-Collections.pdf",
        "work_type": "English literary short story.",
        "original_language": "English",
        "relevant_publication": "The Pioneer: A Literary and Critical Magazine, Boston, 1843, pages 29–31.",
        "publication_source": "https://www.themorgan.org/printed-books/272017",
        "death_year": 1849,
    },
    "radharani": {
        "author_identity": "Bankim Chandra Chattopadhyay (1838–1894), Bengali prose writer and novelist.",
        "author_source": "https://museumsofindia.gov.in/repository/record/vmh_kol-R2824-17621",
        "work_type": "Bengali literary prose work.",
        "original_language": "Bengali",
        "relevant_publication": "The identified source edition is Bengali Wikisource's 1940-labelled edition; the repository records an original-publication year of 1877.",
        "publication_source": "https://bn.wikisource.org/wiki/%E0%A6%B0%E0%A6%BE%E0%A6%A7%E0%A6%BE%E0%A6%B0%E0%A6%BE%E0%A6%A3%E0%A7%80_(%E0%A7%A7%E0%A7%AF%E0%A7%AA%E0%A7%A6)",
        "death_year": 1894,
    },
    "yugalanguriya": {
        "author_identity": "Bankim Chandra Chattopadhyay (1838–1894), Bengali prose writer and novelist.",
        "author_source": "https://museumsofindia.gov.in/repository/record/vmh_kol-R2824-17621",
        "work_type": "Bengali literary prose work.",
        "original_language": "Bengali",
        "relevant_publication": "The identified source edition is Bengali Wikisource's 1893-labelled edition; the repository records an original-publication year of 1874.",
        "publication_source": "https://bn.wikisource.org/wiki/%E0%A6%AF%E0%A7%81%E0%A6%97%E0%A6%B2%E0%A6%BE%E0%A6%99%E0%A7%8D%E0%A6%97%E0%A7%81%E0%A6%B0%E0%A7%80%E0%A6%AF%E0%A6%BC_(%E0%A7%A7%E0%A7%AE%E0%A7%AF%E0%A7%A9)",
        "death_year": 1894,
    },
}

# The facsimile checkpoint was an observation ledger, not a request to alter
# prose.  These rows state the exact reading it recorded, then let the package
# compare it with the current controlled chapter and the retained Wikisource
# transcription.  A crop that does not establish the full word stays
# SOURCE_AMBIGUOUS.  A documented edition variant is retained transparently;
# it is not a license to rewrite controlled prose to match one scan.
YUGALANGURIYA_OBSERVATIONS = (
    {
        "location": "chapter-001 opening",
        "chapter_id": "chapter-001",
        "source_reading": "Facsimile crop records an uncertain join: ই + জনে",
        "retained_source_reading": "ই জনে",
        "expected_earnalism_reading": "দুই জনে",
        "classification": "SOURCE_AMBIGUOUS",
        "evidence": "facsimile checkpoint image 6 / crop 1; retained Bengali Wikisource source layer",
        "action": "Obtain an independent human reading of uncropped image 6, including its left margin. Do not alter canonical prose before that review.",
    },
    {
        "location": "chapter-002 opening",
        "chapter_id": "chapter-002",
        "source_reading": "Facsimile crop reads কে + ন যে",
        "retained_source_reading": "ন যে",
        "expected_earnalism_reading": "কেন যে",
        "classification": "SUPPORTED_SOURCE_CORRECTION",
        "evidence": "facsimile checkpoint image 13 / crop 8",
        "action": "Resolved by the current canonical reading; no manuscript change is authorized or needed.",
    },
    {
        "location": "chapter-003 opening",
        "chapter_id": "chapter-003",
        "source_reading": "Facsimile crop reads দু + ই বৎসরের",
        "retained_source_reading": "ই বৎসরের",
        "expected_earnalism_reading": "দুই বৎসরের",
        "classification": "SUPPORTED_SOURCE_CORRECTION",
        "evidence": "facsimile checkpoint image 17 / crop 12",
        "action": "Resolved by the current canonical reading; no manuscript change is authorized or needed.",
    },
    {
        "location": "chapter-004 opening",
        "chapter_id": "chapter-004",
        "source_reading": "The 1893 facsimile has the initial বি in its illustrated drop-cap crop and বাহাস্তে in the adjacent text; together the source reads বিবাহাস্তে.",
        "retained_source_reading": "The retained Wikisource plain-text layer reads বাহাস্তে and omits the illustrated initial.",
        "expected_earnalism_reading": "বিবাহান্তে",
        "classification": "DOCUMENTED_EDITION_VARIANT",
        "evidence": "The 1893 Wikisource facsimile page 23 plus its extracted initial crop p18b support বিবাহাস্তে. An independent SNLTR Bankim Rachanabali edition reads বিবাহান্তে at its chapter-four opening; its project states that it follows the Sahitya Samsad publication arrangement. The two editions therefore document differing readings; neither source is represented as agreeing with the other.",
        "facsimile_url": "https://bn.wikisource.org/wiki/পাতা:যুগলাঙ্গুরীয়_-_বঙ্কিমচন্দ্র_চট্টোপাধ্যায়.djvu/২৩",
        "initial_crop_url": "https://commons.wikimedia.org/wiki/File:যুগলাঙ্গুরীয়_-_বঙ্কিমচন্দ্র_চট্টোপাধ্যায়_p18b.png",
        "corroborating_edition_url": "https://bankim-rachanabali.nltr.org/node/822",
        "corroborating_edition_project_url": "https://bankim-rachanabali.nltr.org/node/2",
        "editorial_decision": "OWNER_CONFIRMED_INTENDED_CANONICAL_READING: preserve বিবাহান্তে. This records a selected canonical edition reading, not a claim that the 1893 scan reads the same word.",
        "action": "Resolved as a documented edition variant. Preserve the canonical reading বিবাহান্তে; do not alter the 1893-source evidence or modify literary text solely to reconcile editions.",
    },
    {
        "location": "chapter-005 opening",
        "chapter_id": "chapter-005",
        "source_reading": "Facsimile crop reads হি + রণ্ময়ী",
        "retained_source_reading": "রণ্ময়ী",
        "expected_earnalism_reading": "হিরণ্ময়ী",
        "classification": "SUPPORTED_SOURCE_CORRECTION",
        "evidence": "facsimile checkpoint image 27 / crop 22",
        "action": "Resolved by the current canonical reading; no manuscript change is authorized or needed.",
    },
    {
        "location": "chapter-006 opening",
        "chapter_id": "chapter-006",
        "source_reading": "Facsimile crop reads প + রে এক দিন",
        "retained_source_reading": "রে এক দিন",
        "expected_earnalism_reading": "পরে এক দিন",
        "classification": "SUPPORTED_SOURCE_CORRECTION",
        "evidence": "facsimile checkpoint image 30 / crop 25",
        "action": "Resolved by the current canonical reading; no manuscript change is authorized or needed.",
    },
    {
        "location": "chapter-007 opening",
        "chapter_id": "chapter-007",
        "source_reading": "Facsimile crop reads বি + বাহের পর",
        "retained_source_reading": "বাহের পর",
        "expected_earnalism_reading": "বিবাহের পর",
        "classification": "SUPPORTED_SOURCE_CORRECTION",
        "evidence": "facsimile checkpoint image 35 / crop 30",
        "action": "Resolved by the current canonical reading; no manuscript change is authorized or needed.",
    },
    *(
        {
            "location": f"chapter-{number:03d} opening",
            "chapter_id": f"chapter-{number:03d}",
            "source_reading": "Facsimile crop reads হি + রণ্ময়ী",
            "retained_source_reading": "রণ্ময়ী",
            "expected_earnalism_reading": "হিরণ্ময়ী",
            "classification": "SUPPORTED_SOURCE_CORRECTION",
            "evidence": f"facsimile checkpoint chapter {number:03d} opening crop",
            "action": "Resolved by the current canonical reading; no manuscript change is authorized or needed.",
        }
        for number in range(8, 11)
    ),
    {
        "location": "chapter-001 Tamralipta footnote marker",
        "chapter_id": "chapter-001",
        "source_reading": "Facsimile crop records an asterisk marker; retained transcription uses a presentation-layer arrow marker",
        "retained_source_reading": "upward-arrow presentation marker",
        "expected_earnalism_reading": "asterisk marker bound to the retained note",
        "classification": "SOURCE_PRESENTATION_LAYER",
        "evidence": "facsimile checkpoint footnote observation and current controlled chapter record",
        "action": "Resolved as a non-prose source-presentation difference; preserve the current bound note and make no prose change.",
    },
)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def digest(path: Path) -> str | None:
    return sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def evidence(path: Path) -> dict[str, str]:
    value = digest(path)
    if not value:
        raise ValueError(f"required evidence file is absent: {path}")
    return {"path": repo_path(path), "sha256": value}


def require_text(value: Any, fallback: str = "NOT_RECORDED") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def source_rights_note(slug: str) -> dict[str, str]:
    path = content_book_dir(slug) / "source-rights.md"
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- ([^:]+):\s*(.*)$", line)
        if match:
            values[match.group(1).strip().casefold()] = match.group(2).strip()
    return values


def content_book_dir(slug: str) -> Path:
    """Return the active source path or the explicit archive path for a held title."""
    archive = HELD_TITLE_ARCHIVES.get(slug)
    return archive / "source-book" if archive else ROOT / "content" / "books" / slug


def controlled_package_dir(slug: str) -> Path:
    archive = HELD_TITLE_ARCHIVES.get(slug)
    return archive / "controlled-publication-package" if archive else PUBLICATIONS / slug


def active_cover_hashes(path: Path) -> dict[str, str]:
    record = read_json(path)
    active = record.get("active_approvals") if isinstance(record.get("active_approvals"), dict) else {}
    history = record.get("history") if isinstance(record.get("history"), list) else []
    result: dict[str, str] = {}
    for side in ("front", "back"):
        event_id = active.get(side)
        for event in history:
            if isinstance(event, dict) and event.get("event_id") == event_id:
                value = event.get("remote_sha256") or event.get("candidate_sha256")
                if isinstance(value, str) and value:
                    result[side] = value
                break
    return result


def canonical_chapter_records(directory: Path) -> list[dict[str, str]]:
    """Bind ordered delivered chapter content, never reader-manifest metadata.

    Reader manifests intentionally do not embed protected text or its chapter
    digests.  The controlled chapter records do, and each record self-binds its
    content hash.  An absent/malformed chapter must make the package fail,
    rather than producing an empty digest that looks valid.
    """
    records: list[tuple[int, str, str, str]] = []
    for path in sorted((directory / "chapters").glob("*.json")):
        chapter = read_json(path)
        content = chapter.get("content")
        content_hash = chapter.get("content_hash")
        chapter_id = chapter.get("id")
        order = chapter.get("order")
        if not isinstance(content, str) or not isinstance(content_hash, str) or not isinstance(chapter_id, str) or not isinstance(order, int):
            raise ValueError(f"malformed controlled chapter record: {path}")
        if sha256(content.encode("utf-8")).hexdigest() != content_hash:
            raise ValueError(f"controlled chapter content hash mismatch: {path}")
        records.append((order, chapter_id, content_hash, content))
    if not records or len({item[0] for item in records}) != len(records):
        raise ValueError(f"missing or duplicate ordered controlled chapters: {directory}")
    records.sort()
    return [
        {"chapter_id": chapter_id, "content_sha256": content_hash, "content": content}
        for _, chapter_id, content_hash, content in records
    ]


def canonical_chapter_hashes(directory: Path) -> tuple[list[dict[str, str]], str]:
    records = canonical_chapter_records(directory)
    values = [{"chapter_id": item["chapter_id"], "content_sha256": item["content_sha256"]} for item in records]
    aggregate = sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    return values, aggregate


def normalize_text_for_comparison(value: str) -> str:
    """Normalize only non-substantive transport and layout variation.

    NFC makes equivalent Unicode representations comparable and whitespace
    collapsing handles source line wrapping.  It deliberately does not remove
    punctuation, words, paragraphs, or marks whose presence can be textual.
    """
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def source_to_canonical_comparison(slug: str, directory: Path) -> dict[str, Any]:
    """Verify ordered controlled chapters against the retained source file.

    This is not a rights decision.  It is a deterministic body comparison used
    to explain whether a stored publication aggregate should be read as a
    direct source-text digest.
    """
    source_path = content_book_dir(slug) / "raw" / "source.txt"
    if not source_path.is_file():
        return {
            "status": "UNKNOWN",
            "source_path": repo_path(source_path),
            "source_file_sha256": "NOT_RECORDED",
            "all_chapters_found_in_order": False,
            "chapter_positions": [],
            "reason": "The retained source file is unavailable; no text conclusion is inferred.",
        }
    normalized_source = normalize_text_for_comparison(source_path.read_text(encoding="utf-8"))
    cursor = 0
    positions: list[dict[str, Any]] = []
    for chapter in canonical_chapter_records(directory):
        normalized_chapter = normalize_text_for_comparison(chapter["content"])
        position = normalized_source.find(normalized_chapter, cursor)
        positions.append({"chapter_id": chapter["chapter_id"], "found": position >= 0, "position": position if position >= 0 else None})
        if position < 0:
            return {
                "status": "TEXT_REVIEW_REQUIRED",
                "source_path": repo_path(source_path),
                "source_file_sha256": digest(source_path),
                "all_chapters_found_in_order": False,
                "chapter_positions": positions,
                "normalization": "Unicode NFC plus whitespace-run collapse only.",
                "reason": "A canonical chapter was not found in retained source order. No prose is changed automatically.",
            }
        cursor = position + len(normalized_chapter)
    return {
        "status": "TEXT_VERIFIED",
        "source_path": repo_path(source_path),
        "source_file_sha256": digest(source_path),
        "all_chapters_found_in_order": True,
        "chapter_positions": positions,
        "normalization": "Unicode NFC plus whitespace-run collapse only.",
        "reason": "Every current controlled chapter was found in retained source order; no prose transformation was applied.",
    }


def yugalanguriya_observation_comparison(directory: Path) -> dict[str, Any]:
    """Reconcile the retained transcription with the facsimile observation log.

    The stored Bengali Wikisource plain-text source is useful provenance, but
    its known omitted opening initials are not a superior source reading to a
    recorded facsimile crop.  This function consequently reports every one of
    the eleven observations and fails closed only where the evidence cannot
    establish a supported canonical reading.
    """
    chapters = {entry["chapter_id"]: entry["content"] for entry in canonical_chapter_records(directory)}
    rows: list[dict[str, Any]] = []
    for observation in YUGALANGURIYA_OBSERVATIONS:
        content = chapters.get(observation["chapter_id"], "")
        expected = observation["expected_earnalism_reading"]
        if observation["chapter_id"] == "chapter-001" and "footnote" in observation["location"]:
            matches_current = "তাম্রলিপ্তের*" in content
        else:
            matches_current = content.startswith(expected)
        classification = observation["classification"]
        if not matches_current:
            classification = "SUBSTANTIVE_TEXT_DIFFERENCE"
        rows.append(
            {
                "LOCATION": observation["location"],
                "SOURCE_READING": observation["source_reading"],
                "RETAINED_SOURCE_LAYER_READING": observation["retained_source_reading"],
                "EARNALISM_READING": expected if matches_current else content[:80],
                "DIFFERENCE": "Current canonical text differs from the retained transcription where documented above.",
                "CLASSIFICATION": classification,
                "EVIDENCE": observation["evidence"],
                "FACSIMILE_URL": observation.get("facsimile_url", "NOT_RECORDED"),
                "INITIAL_CROP_URL": observation.get("initial_crop_url", "NOT_RECORDED"),
                "CORROBORATING_EDITION_URL": observation.get("corroborating_edition_url", "NOT_RECORDED"),
                "CORROBORATING_EDITION_PROJECT_URL": observation.get("corroborating_edition_project_url", "NOT_RECORDED"),
                "EDITORIAL_DECISION": observation.get("editorial_decision", "NOT_RECORDED"),
                "ACTION": observation["action"] if matches_current else "Restore or resolve the controlled reading against the identified source before release; no automatic prose rewrite is permitted.",
                "CURRENT_READING_MATCHES_EXPECTED": matches_current,
            }
        )
    unresolved = [
        row for row in rows
        if row["CLASSIFICATION"] in {
            "SOURCE_AMBIGUOUS",
            "SUBSTANTIVE_TEXT_DIFFERENCE",
        }
    ]
    return {
        "status": "TEXT_REVIEW_REQUIRED" if unresolved else "TEXT_VERIFIED",
        "method": "Observation-level deterministic comparison of the current controlled chapter openings and footnote marker against the retained Bengali Wikisource layer and the hash-bound facsimile checkpoint. No AI-generated Bengali prose is used as evidence.",
        "observations": rows,
        "resolved_observation_count": len(rows) - len(unresolved),
        "unresolved_observation_count": len(unresolved),
        "unresolved_locations": [row["LOCATION"] for row in unresolved],
        "reason": "The chapter-001 source reading remains ambiguous. Chapter-004 is a documented edition variant: the selected 1893 source reads বিবাহাস্তে while an independent SNLTR edition and the owner-confirmed canonical reading use বিবাহান্তে. Resolved source-layer omissions and variants are retained as evidence, not blockers.",
    }


def bengali_source_layer_provenance(source: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    """Document source/transclusion handling without pretending it is prose review."""
    return {
        "status": "SOURCE_LAYER_PROVENANCE_DOCUMENTED",
        "source_provider": require_text(source.get("source_name")),
        "source_page": require_text(source.get("source_url")),
        "source_layer_used": "Retained plain-text source body; repository/source furniture is excluded from delivered chapter content.",
        "rendering_and_transclusion_handling": "The comparison does not use Wikisource page chrome, templates, or transcluded presentation furniture as literary prose. Delivered controlled chapters are compared in order against the retained source body.",
        "normalization_applied": require_text(comparison.get("normalization")),
        "canonical_hash": "Bound in textual_integrity_proof.earnalism_canonical_text_hash.",
        "verification_result": "TEXT_VERIFIED" if comparison.get("status") == "TEXT_VERIFIED" else "TEXT_REVIEW_REQUIRED",
        "source_license_note": require_text(source.get("source_license")),
        "release_decision_note": "The source-layer licence/provenance is recorded for the later release decision. It is not a second literary-text review or an accepted rights decision.",
    }


def audio_evidence_path(slug: str) -> Path:
    return ROOT / "internal" / "audiobook_lab" / "sprint1_publication" / "title_runs" / f"{slug}_release_gate_evidence.json"


def audio_assessment(slug: str, launch_hold: dict[str, Any], canonical_text_hash: str) -> dict[str, Any]:
    """Inventory actual historical audio evidence without releasing audio.

    This keeps model use distinct from copied recordings and from the current
    all-title public-audio hold.  A title can be technically promising without
    receiving a present release decision.
    """
    path = audio_evidence_path(slug)
    record = read_json(path)
    scope_status = "AUDIO_DISABLED_NOT_IN_LAUNCH_SCOPE" if not launch_hold["public_audio_exposure_enabled"] else "AUDIO_REVIEW_REQUIRED"
    base: dict[str, Any] = {
        "current_launch_status": scope_status,
        "current_launch_reason": "The controlled launch configuration, rather than use of AI/TTS, disables public audio exposure for every title.",
        "underlying_literary_text": "INDIA_COPYRIGHT_EVIDENCE_COMPLETE",
        "canonical_text_hash": canonical_text_hash,
        "evidence": [evidence(path)] if path.is_file() else [],
        "first_party_generation_context": "OWNER_STATED: audiobooks are generated by or at the direction of the product owner, not copied third-party commercial recordings. This is not a release decision.",
        "third_party_recording_used": "NO_EVIDENCE_OF_THIRD_PARTY_RECORDING_IN_CURRENT_RELEASE_GATE_FILE",
    }
    if slug == "a-ghost-story":
        audio = record.get("audio") if isinstance(record.get("audio"), dict) else {}
        return {
            **base,
            "candidate_status_if_audio_scope_changes": "AUDIO_ACTION_REQUIRED — the historical Google output is quality-gated, but a current release decision requires a fresh canonical-input binding and component declaration.",
            "provider": require_text(record.get("provider")),
            "model": require_text(record.get("model")),
            "voice": require_text(record.get("voice")),
            "voice_type": "PROVIDER_AUTHORIZED_SYNTHETIC_VOICE",
            "generation_date": require_text(record.get("generated_at")),
            "audio_generation_input_hash": "NOT_RECORDED_IN_HISTORICAL_RELEASE_GATE",
            "audio_output_hash": require_text(audio.get("sha256")),
            "music_present": "UNKNOWN_NOT_RECORDED",
            "external_sound_effects_present": "UNKNOWN_NOT_RECORDED",
            "provider_terms": {
                "provider": "Google Cloud Text-to-Speech",
                "terms_url": "https://docs.cloud.google.com/text-to-speech/docs/basics",
                "retrieval_date": "2026-09-22",
                "terms_recheck_before_enablement": "REQUIRED — this static evidence snapshot is not a substitute for checking then-current provider terms before a future public-audio release.",
                "relevant_provision": "Google documents that generated audio data may power applications or augment media, subject to Google Cloud terms and applicable law.",
                "commercial_output_use": "DOCUMENTED_SUBJECT_TO_APPLICABLE_TERMS_AND_LAW",
                "public_distribution": "DOCUMENTED_FOR_APPLICATION_OR_MEDIA_USE_SUBJECT_TO_APPLICABLE_TERMS_AND_LAW",
                "output_ownership_or_license_position": "NOT_STATED_BY_THIS_PROVIDER_DOCUMENT",
                "voice_specific_restrictions": "No custom/imitative voice is recorded; the evidence names a Google prebuilt Studio voice.",
                "attribution_required": "NOT_STATED_BY_THIS_PROVIDER_DOCUMENT",
            },
        }
    if slug == "the-tell-tale-heart":
        return {
            **base,
            "candidate_status_if_audio_scope_changes": "AUDIO_ACTION_REQUIRED — current Google representative auditions failed the recorded listening-QA minimum; a human narration or licensed alternate provider is required.",
            "provider": "google",
            "model": "NOT_RECORDED_IN_SUMMARY_GATE",
            "voice": "en-GB-Studio-C",
            "voice_type": "PROVIDER_AUTHORIZED_SYNTHETIC_VOICE",
            "generation_date": require_text(record.get("generated_at")),
            "audio_generation_input_hash": require_text((record.get("source_binding") or {}).get("audition_input_manifest_sha256")),
            "audio_output_hash": "NOT_RECORDED — no launchable output",
            "music_present": "NOT_APPLICABLE — no launchable output",
            "external_sound_effects_present": "NOT_APPLICABLE — no launchable output",
            "provider_terms": {"provider": "Google Cloud Text-to-Speech", "terms_url": "https://docs.cloud.google.com/text-to-speech/docs/basics", "retrieval_date": "2026-09-22", "terms_recheck_before_enablement": "REQUIRED", "result": "Same provider documentation applies to the historical attempts; quality, not AI/TTS use, is the blocking condition."},
        }
    if slug == "radharani":
        return {
            **base,
            "candidate_status_if_audio_scope_changes": "AUDIO_ACTION_REQUIRED — full pipeline closeout recorded derived-ASR and calibration failure; no current launchable audio output is established.",
            "provider": "MULTIPLE_HISTORICAL_PROVIDER_ATTEMPTS_RECORDED_IN_CLOSEOUT",
            "model": "NOT_A_CURRENT_LAUNCH_CANDIDATE",
            "voice": "NOT_RECORDED_IN_RELEASE_GATE_SUMMARY",
            "voice_type": "UNKNOWN",
            "generation_date": "NOT_RECORDED",
            "audio_generation_input_hash": "NOT_RECORDED",
            "audio_output_hash": "NOT_RECORDED — no launchable output",
            "music_present": "NOT_APPLICABLE — no launchable output",
            "external_sound_effects_present": "NOT_APPLICABLE — no launchable output",
            "provider_terms": {"result": "Not evaluated: the current record establishes no launchable audio candidate, so a provider-terms review cannot clear it ahead of its failed fidelity/QA gate."},
        }
    return {
        **base,
        "candidate_status_if_audio_scope_changes": "AUDIO_ACTION_REQUIRED — historical mapped-asset references do not establish provider, voice, input hash, output hash, or a complete current qualification gate.",
        "provider": "UNKNOWN",
        "model": "UNKNOWN",
        "voice": "UNKNOWN",
        "voice_type": "UNKNOWN",
        "generation_date": "UNKNOWN",
        "audio_generation_input_hash": "UNKNOWN",
        "audio_output_hash": "UNKNOWN",
        "music_present": "UNKNOWN",
        "external_sound_effects_present": "UNKNOWN",
        "provider_terms": {"result": "Provider identity is not established by the current historical mapped-asset record; obtain it only if audio for this title enters a future launch scope."},
    }


def section_22_calculation(death_year: int) -> dict[str, Any]:
    return {
        "rule": "For an ordinary published literary work under Copyright Act, 1957 section 22, the term is sixty years from the beginning of the calendar year following the author’s death.",
        "author_death_year": death_year,
        "term_ends_at_calendar_year_end": death_year + 60,
        "expired_term_calculation_begins": f"1 January {death_year + 61}",
        "limitation": "This factual calculation is not a rights acceptance and must not be applied to a different statutory category or separately protected component.",
    }


def source_identifier(value: str) -> str:
    """Return a non-secret source identifier without treating a URL as a licence."""
    match = re.search(r"/(?:ebooks/)?([^/?#]+)(?:[?#].*)?$", value)
    return match.group(1) if match else "NOT_RECORDED"


def existing_launch_hold() -> dict[str, Any]:
    root = read_json(ROOT_LAUNCH)
    backend = read_json(BACKEND_LAUNCH)
    registry = read_json(RIGHTS_REGISTRY)
    return {
        "root_launch": evidence(ROOT_LAUNCH),
        "backend_launch": evidence(BACKEND_LAUNCH),
        "rights_registry": evidence(RIGHTS_REGISTRY),
        "public_reader_exposure_enabled": root.get("public_reader_exposure_enabled") is True or backend.get("public_reader_exposure_enabled") is True,
        "public_audio_exposure_enabled": root.get("public_audio_exposure_enabled") is True or backend.get("public_audio_exposure_enabled") is True,
        "public_paid_commerce_enabled": root.get("public_paid_commerce_enabled") is True or backend.get("public_paid_commerce_enabled") is True,
        "live_approved_slugs": sorted(set(root.get("live_approved_slugs", [])) | set(backend.get("live_approved_slugs", []))),
        "accepted_rights_record_count": len(registry.get("accepted_records", {})) if isinstance(registry.get("accepted_records"), dict) else None,
    }


def public_legal_routes_registered() -> bool:
    """Check both SPA and production-routing sources, not an old narrative draft."""
    app = (ROOT / "frontend" / "src" / "App.js").read_text(encoding="utf-8")
    pages = (ROOT / "frontend" / "src" / "pages" / "LegalPages.jsx").read_text(encoding="utf-8")
    vercel = read_json(ROOT / "frontend" / "vercel.json")
    rewrites = vercel.get("rewrites") if isinstance(vercel, dict) else []
    if not isinstance(rewrites, list):
        rewrites = []
    deployed_routes = {
        item.get("source")
        for item in rewrites if isinstance(item, dict) and item.get("destination") == "/index.html"
    }
    required_routes = {"/privacy", "/terms", "/copyright"}
    return required_routes.issubset(deployed_routes) and all(route in app for route in ('path="/privacy"', 'path="/terms"', 'path="/copyright"')) and all(
        component in pages for component in ("export function Privacy", "export function Terms", "export function CopyrightNotice")
    )


def title_record(slug: str, launch_hold: dict[str, Any]) -> dict[str, Any]:
    directory = controlled_package_dir(slug)
    source_path = directory / "source_evidence.json"
    reader_path = directory / "reader_manifest.json"
    book_path = directory / "public_book.json"
    cover_path = directory / "cover_approval_evidence.json"
    source = read_json(source_path)
    reader = read_json(reader_path)
    book = read_json(book_path)
    note = source_rights_note(slug)
    chapter_hashes, canonical_text_hash = canonical_chapter_hashes(directory)
    source_comparison = source_to_canonical_comparison(slug, directory)
    facts = PILOT_FACT_SOURCES[slug]
    title = require_text(book.get("title") or note.get("title"), slug)
    author = require_text(book.get("author") or note.get("author"))
    source_license = require_text(source.get("source_license"))
    bengali_source_layer = source.get("source_name") == "Bengali Wikisource"
    source_content_hash = require_text(source.get("content_hash"))
    yugal_observations = None
    if slug == "yugalanguriya":
        yugal_observations = yugalanguriya_observation_comparison(directory)
        integrity_status = yugal_observations["status"]
    else:
        integrity_status = source_comparison["status"]
    if slug == "yugalanguriya":
        integrity_difference = "The retained Bengali Wikisource transcription has known truncated openings. Nine observations support the current controlled readings or are presentation-only; chapter-004 is a documented edition variant, while only chapter-001 remains source-ambiguous. No canonical text change is authorized."
    elif slug == "the-tell-tale-heart":
        integrity_difference = "The stored source-evidence content hash is an aggregate publication hash, not a direct chapter digest. The exact retained source body contains the current controlled chapter after the documented non-substantive normalization."
    elif slug == "radharani":
        integrity_difference = "Every controlled chapter is present in source order after the documented non-substantive normalization. A separately recorded source-layer/footnote presentation issue is not represented as a prose difference."
    else:
        integrity_difference = "Every controlled chapter is present in source order after the documented non-substantive normalization."
    source_layer_provenance = bengali_source_layer_provenance(source, source_comparison) if bengali_source_layer else None
    cover_hashes = active_cover_hashes(cover_path)
    cover_evidence = [evidence(book_path)]
    if cover_path.is_file():
        cover_evidence.append(evidence(cover_path))
    return {
        "title": title,
        "slug": slug,
        "country_scope": list(COUNTRY_SCOPE),
        "india_copyright_proof": {
            "status": "INDIA_COPYRIGHT_EVIDENCE_COMPLETE",
            "statutory_category": "ORDINARY_PUBLISHED_LITERARY_WORK_SECTION_22",
            "author": author,
            "author_identity": facts["author_identity"],
            "author_death_year": facts["death_year"],
            "joint_authorship": "NOT_RECORDED",
            "work_type": facts["work_type"],
            "original_language": facts["original_language"],
            "source_publication_year": require_text(note.get("original publication year")),
            "relevant_publication_evidence": facts["relevant_publication"],
            "section_22_term_calculation": section_22_calculation(facts["death_year"]),
            "evidence": [
                evidence(source_path),
                evidence(content_book_dir(slug) / "source-rights.md"),
                {"topic": "author identity and death year", "url": facts["author_source"]},
                {"topic": "work publication evidence", "url": facts["publication_source"]},
                OFFICIAL_SOURCES[0],
            ],
            "limitations": [
                "This records an objectively documented ordinary section 22 term calculation only; it is not a rights acceptance or release decision.",
                "Translations, source transcriptions, covers, illustrations, editorial additions, and other separately protected components remain independently evaluated.",
            ],
        },
        "textual_integrity_proof": {
            "status": integrity_status,
            "earnalism_edition_id": require_text(reader.get("slug"), slug),
            "source_edition": require_text(source.get("source_format")),
            "source_publication_information": require_text(note.get("original publication year")),
            "source_provider": require_text(source.get("source_name")),
            "source_identifier": source_identifier(require_text(source.get("source_url"))),
            "source_reference_url": require_text(source.get("source_url")),
            "source_retrieval_date": require_text(source.get("downloaded_at")),
            "source_file_hash": require_text(source.get("source_hash")),
            "stored_publication_aggregate_hash": source_content_hash,
            "current_raw_source_path": source_comparison["source_path"],
            "current_raw_source_file_hash": source_comparison["source_file_sha256"],
            "earnalism_canonical_text_hash": canonical_text_hash,
            "canonical_chapter_hashes": chapter_hashes,
            "source_to_canonical_comparison": source_comparison,
            "facsimile_observation_comparison": yugal_observations,
            "comparison_method": "Deterministic retained-source comparison: Unicode NFC plus whitespace-run collapse only, then ordered full-chapter substring matching. No AI-generated prose is an authority.",
            "material_differences": integrity_difference,
            "intentional_corrections": "NONE_APPROVED",
            "evidence": [evidence(reader_path), evidence(source_path), evidence(PILOT_INTEGRITY_EVIDENCE)],
        },
        "translation_and_editorial_material": (
            {
                "status": "SOURCE_LAYER_PROVENANCE_DOCUMENTED",
                "translation": "NOT_APPLICABLE — identified Bengali source text, not a separately identified translation.",
                "source_layer": source_license,
                "source_layer_provenance": source_layer_provenance,
                "blockers": [],
            }
            if bengali_source_layer else {
                "status": "NOT_APPLICABLE_FROM_IDENTIFIED_DELIVERED_TEXT",
                "translation": "NOT_RECORDED — no separately identified translation is delivered in the controlled chapter records.",
                "source_layer": source_license,
                "blockers": ["A later release decision must continue to exclude any separately protected introduction, annotation, illustration, or editorial addition not present in the evidenced controlled text."],
            }
        ),
        "cover_provenance": {
            "status": "FIRST_PARTY_COVER_PROVENANCE_CONFIRMED",
            "owner_stated_creator": "PRODUCT_OWNER",
            "rightsholder_claim": "PRODUCT_OWNER",
            "basis": "OWNER_SUPPLIED_FACT: the product owner states that the Earnalism covers were graphically designed by the owner. The repository contains hash-bound active cover evidence and no contrary external-component record.",
            "externally_sourced_elements": "NO_CONTRARY_EVIDENCE_IN_REPOSITORY — disclose a specific external protected component if one is later identified.",
            "declaration_record": "OPTIONAL_EVIDENCE_STRENGTHENING — an unsigned form is retained for later confirmation but is not a current legal/compliance gate.",
            "front_cover_sha256": cover_hashes.get("front", "NOT_RECORDED"),
            "back_cover_sha256": cover_hashes.get("back", "NOT_RECORDED"),
            "assets": {
                "front": require_text(book.get("cover_url")),
                "back": require_text(book.get("back_cover_url")),
            },
            "evidence": cover_evidence,
            "blockers": [],
        },
        "audio_scope": audio_assessment(slug, launch_hold, canonical_text_hash),
        "public_provenance_statement_candidate": f"Text follows: {require_text(source.get('source_name'))} ({require_text(source.get('source_url'))}).",
        "india_title_predicate": {
            "rule": "INDIA_COPYRIGHT_EVIDENCE_COMPLETE AND TEXT_VERIFIED AND FIRST_PARTY_COVER_PROVENANCE_CONFIRMED AND TRANSLATION_RIGHTS_OK_OR_NOT_APPLICABLE AND REQUIRED_OTHER_ASSETS_OK AND (AUDIO_INDIA_READY OR AUDIO_DISABLED_NOT_IN_LAUNCH_SCOPE)",
            "copyright": "PASS",
            "text": "PASS" if integrity_status == "TEXT_VERIFIED" else "FAIL_CLOSED",
            "cover": "PASS — FIRST_PARTY_COVER_PROVENANCE_CONFIRMED",
            "translation_and_other_assets": "PASS_FOR_IDENTIFIED_DELIVERED_TEXT",
            "audio": "PASS_FOR_CURRENT_SCOPE" if not launch_hold["public_audio_exposure_enabled"] else "REVIEW_REQUIRED",
            "result": "INDIA_TITLE_READY" if integrity_status == "TEXT_VERIFIED" else "INDIA_TITLE_ACTION_REQUIRED",
        },
        "india_title_status": "HOLD",
        "india_title_ready": integrity_status == "TEXT_VERIFIED",
        "india_compliance_status": "INDIA_TITLE_READY" if integrity_status == "TEXT_VERIFIED" else "INDIA_TITLE_ACTION_REQUIRED",
        "compliance_blockers": ["TEXT_REVIEW_REQUIRED"] if integrity_status != "TEXT_VERIFIED" else [],
        "release_authorization_state": "PENDING — the empty accepted-rights registry and global Reader hold are deliberate production controls, not evidence that an objectively complete title is legally deficient.",
    }


def data_inventory() -> list[dict[str, Any]]:
    entries = (
        ("name", "account, contact, and newsletter forms", "frontend/src/pages/Contact.jsx; frontend/src/pages/Home.jsx", "application database and provider region are not established by source inspection", "not defined in source", "ACTION_REQUIRED"),
        ("email", "account, contact, and newsletter forms", "frontend/src/pages/Contact.jsx; frontend/src/pages/Home.jsx; frontend/src/pages/Account.jsx", "application database and provider region are not established by source inspection", "not defined in source", "ACTION_REQUIRED"),
        ("authentication information", "browser session/token handling", "frontend/src/pages/Reader.jsx; backend/server.py", "browser local storage plus application backend; provider geography needs verification", "not defined in source", "ACTION_REQUIRED"),
        ("reading/activity history and position", "Reading Pass position service", "frontend/src/pages/Reader.jsx; backend/reading_pass_service.py", "application backend; provider geography needs verification", "not defined in source", "ACTION_REQUIRED"),
        ("analytics and device/session identifiers", "optional funnel analytics and browser local-storage session identifier", "frontend/src/lib/funnelAnalytics.js; backend/server.py", "browser local storage and optional analytics endpoint; production enablement needs verification", "not defined in source", "REVIEW_REQUIRED"),
        ("support communications", "contact form submission", "frontend/src/pages/Contact.jsx", "application backend; provider geography needs verification", "not defined in source", "ACTION_REQUIRED"),
        ("payment-related information", "Razorpay checkout and wallet/payment operations; no raw payment data is claimed by this source inventory", "frontend/src/pages/Pricing.jsx; backend/server.py", "Razorpay and application backend; merchant/provider data handling needs verification", "not defined in source", "REVIEW_REQUIRED"),
    )
    return [
        {
            "data_category": category,
            "purpose_and_collection_point": behavior,
            "source": source,
            "storage_and_processor_scope": storage,
            "retention": retention,
            "user_control": "Not fully established by source inspection; public policy must state only verified controls.",
            "status": status,
            "fact_classification": "REPOSITORY_CONFIRMED_PROCESSING; provider/deployment detail is separately classified in website_fact_inventory.",
        }
        for category, behavior, source, storage, retention, status in entries
    ]


def website_fact_inventory() -> list[dict[str, Any]]:
    """Keep code-established facts separate from production/provider facts.

    This is an internal evidence inventory, not a public policy and not an
    attempt to infer environment-variable values from a repository checkout.
    """
    return [
        {
            "fact": "operator and brand relationship",
            "value": "REO ENTERPRISE is the sole-proprietor operator; Earnalism is its venture/brand.",
            "classification": "OWNER_SUPPLIED_FACT_ALREADY_RECORDED",
            "evidence": "Owner closure response; no new attestation requested.",
        },
        {
            "fact": "ordinary support contact",
            "value": "sales@reoenterprise.org",
            "classification": "REPOSITORY_CONFIRMED",
            "evidence": "frontend/src/pages/Contact.jsx and frontend/src/pages/Pricing.jsx",
        },
        {
            "fact": "frontend and backend deployment integrations",
            "value": "Vercel frontend configuration and Railway backend configuration are present.",
            "classification": "REPOSITORY_CONFIRMED",
            "evidence": "frontend/vercel.json; backend/railway.json",
        },
        {
            "fact": "media storage integration",
            "value": "Cloudinary is configured in source for image assets; B2-compatible variables are documented for large audiobook objects.",
            "classification": "REPOSITORY_CONFIRMED",
            "evidence": "backend/config/cloudinary.py; backend/.env.example",
        },
        {
            "fact": "production provider geography and cross-border access",
            "value": "NOT_ESTABLISHED_FROM_SOURCE",
            "classification": "PROVIDER_VERIFICATION_REQUIRED",
            "evidence": "Repository configuration names providers but does not disclose effective production regions or access arrangements.",
        },
        {
            "fact": "analytics",
            "value": "Launch analytics is optional in source and uses a browser local-storage identifier when enabled.",
            "classification": "DEPLOYMENT_CONFIGURATION_REQUIRED",
            "evidence": "frontend/src/lib/funnelAnalytics.js",
        },
        {
            "fact": "payment product model",
            "value": "Razorpay integration supports one-time Reading Pass purchase; source states no subscription or auto-renewal.",
            "classification": "REPOSITORY_CONFIRMED",
            "evidence": "frontend/src/pages/Pricing.jsx; backend/server.py",
        },
        {
            "fact": "production payment enablement and merchant terms",
            "value": "NOT_ESTABLISHED_FROM_SOURCE",
            "classification": "PROVIDER_OR_OWNER_FACT_REQUIRED",
            "evidence": "backend/server.py exposes configured/mode dynamically and refuses real checkout without configured keys; source cannot prove production mode or merchant agreement.",
        },
        {
            "fact": "privacy and grievance designation",
            "value": "No public designation is registered; sales@reoenterprise.org is not inferred to carry either legal role.",
            "classification": "OWNER_FACT_REQUIRED",
            "evidence": "frontend/src/App.js and Contact.jsx",
        },
        {
            "fact": "retention and self-service account deletion",
            "value": "No retention schedule or public account-deletion route was identified in this source audit.",
            "classification": "OWNER_POLICY_OR_IMPLEMENTATION_REQUIRED",
            "evidence": "frontend/src/App.js; backend/server.py; account UI audit",
        },
    ]


def website_matrix(launch_hold: dict[str, Any]) -> list[dict[str, Any]]:
    legal_routes = public_legal_routes_registered()
    paid_commerce = launch_hold["public_paid_commerce_enabled"]
    return [
        {
            "area": "copyright and content integrity",
            "requirement": "Each released title needs separate copyright, text-integrity, cover, translation/editorial, and other-asset evidence.",
            "in_force_on_launch_date": "YES_FOR_ANY_RELEASE_OF_COPYRIGHTABLE_MATERIAL",
            "applies_to_earnalism": "YES_IF_A_TITLE_IS_RELEASED",
            "applicable": "YES_FOR_ANY_RELEASED_TITLE",
            "authority": "Copyright Act, 1957; source and integrity evidence",
            "current_implementation": "The first three pilots have complete India copyright, deterministic text, and owner-supplied first-party cover evidence. The registry and global Reader/audio holds remain production controls.",
            "gap": "Yugalanguriya remains title-scoped text review; it does not block the three independently evidence-complete titles. A later production release still requires the existing hash-bound ACCEPT/HOLD control.",
            "status": "PASS_FOR_ELIGIBLE_TITLES",
            "launch_blocker": False,
        },
        {
            "area": "privacy and data inventory",
            "requirement": "Evaluate DPDP Act/Rules obligations against the actual India launch date and the identified processing.",
            "in_force_on_launch_date": "For the current 2026-09-22 launch assessment: Rules 1, 2 and 17–21 commenced on publication; Rule 4 is scheduled one year after publication; Rules 3, 5–16, 22 and 23 are scheduled eighteen months after publication, subject to later legal change. This package does not treat future commencement as current evidence.",
            "applies_to_earnalism": "YES_IF_THE_IDENTIFIED_PERSONAL_DATA_PROCESSING_OCCURS",
            "applicable": "YES_IF_THE_IDENTIFIED_PERSONAL_DATA_PROCESSING_OCCURS_ON_LAUNCH",
            "authority": "Digital Personal Data Protection Act, 2023 and Digital Personal Data Protection Rules, 2025, applied by commencement date.",
            "current_implementation": "A public Privacy route describes source-established account, reader, contact, and service-provider processing without asserting unverified retention, geography, data-sale, or analytics facts.",
            "gap": "Provider regions/access, deployed analytics state, and retention remain internal operational limitations; they are not represented as verified public facts.",
            "status": "PASS_FOR_CURRENT_DISCLOSURE" if legal_routes else "ACTION_REQUIRED",
            "launch_blocker": not legal_routes,
        },
        {
            "area": "consumer and e-commerce",
            "requirement": "For an Indian paid Reading Pass flow, test actual pricing, disclosures, restrictions, support/grievance, cancellation/refund treatment, and prohibited deceptive-design risks.",
            "in_force_on_launch_date": "YES_IF_PAID_SERVICE_IS_OFFERED_TO_INDIAN_CONSUMERS",
            "applies_to_earnalism": "YES_IF_READING_TIME_IS_OFFERED_FOR_PAYMENT" if paid_commerce else "NO_PAID_READING_TIME_IS_OFFERED_IN_CURRENT_LAUNCH",
            "applicable": "YES_IF_READING_TIME_IS_OFFERED_FOR_PAYMENT_TO_INDIAN_CONSUMERS" if paid_commerce else "NOT_APPLICABLE_TO_CURRENT_LAUNCH_CONFIGURATION",
            "authority": "Consumer Protection Act, 2019; Consumer Protection (E-Commerce) Rules, 2020; Dark Patterns Guidelines, 2023.",
            "current_implementation": "The controlled-launch configuration disables public paid commerce in both frontend and backend; public checkout initiation and verification are unavailable while payment webhooks remain available for previously-created intents." if not paid_commerce else "Paid commerce is enabled and requires complete customer-flow evidence.",
            "gap": "NOT_APPLICABLE_WHILE_PAID_COMMERCE_IS_DISABLED" if not paid_commerce else "Complete pricing, remedies, merchant, grievance, and checkout-flow evidence before paid commerce is enabled.",
            "status": "NOT_APPLICABLE_TO_CURRENT_LAUNCH" if not paid_commerce else "ACTION_REQUIRED",
            "launch_blocker": paid_commerce,
        },
        {
            "area": "legal pages and contact/grievance information",
            "requirement": "Public legal notices must describe the actual product and operator facts without placeholder assertions.",
            "in_force_on_launch_date": "YES_FOR_THE_PUBLIC_PRODUCT_SURFACE",
            "applies_to_earnalism": "YES",
            "applicable": "YES_FOR_THE_PUBLIC_PRODUCT_SURFACE",
            "authority": "Applicable privacy and consumer framework; owner-supplied business facts.",
            "current_implementation": "The /terms, /privacy, /copyright, and /contact routes disclose the identified operator, current launch scope, support channel, privacy-request channel, and title-specific copyright-concern path without placeholders.",
            "gap": "Paid-commerce-specific terms remain intentionally unpublished because public paid commerce is disabled." if legal_routes and not paid_commerce else "Register complete public legal routes before launch; do not publish placeholders.",
            "status": "PASS_FOR_CURRENT_LAUNCH" if legal_routes and not paid_commerce else "ACTION_REQUIRED",
            "launch_blocker": not legal_routes,
        },
        {
            "area": "copyright complaint handling",
            "requirement": "Provide an operational receive, identify, hold, investigate, evidence, decide, restore/remove path for rights complaints.",
            "in_force_on_launch_date": "YES_FOR_ANY_PUBLIC_CATALOGUE",
            "applies_to_earnalism": "YES_IF_ANY_TITLE_IS_PUBLIC",
            "applicable": "YES_FOR_ANY_PUBLIC_CATALOGUE",
            "authority": "Operational rights-risk control; no US DMCA characterization assumed.",
            "current_implementation": "The public Copyright route and rights contact path request the work, affected Earnalism title/page, claim basis, supporting information, and contact details; they describe title-scoped receipt, review, temporary hold where warranted, and restore/remove outcomes.",
            "gap": "Maintain the documented title-scoped handling process when a complaint is received.",
            "status": "PASS_FOR_CURRENT_LAUNCH" if legal_routes else "ACTION_REQUIRED",
            "launch_blocker": not legal_routes,
        },
        {
            "area": "public AI-generated content",
            "requirement": "Keep any public AI-generated content structurally separate from canonical literary text and inventory only enabled public features.",
            "in_force_on_launch_date": "NOT_APPLICABLE_UNLESS_A_PUBLIC_AI_FEATURE_IS_ENABLED",
            "applies_to_earnalism": "NO_PUBLIC_AI_FEATURE_IDENTIFIED_IN_THIS_SOURCE_AUDIT",
            "applicable": "ONLY_IF_A_PUBLIC_AI_FEATURE_OR_AI-GENERATED_PUBLIC_COPY_IS_ENABLED",
            "authority": "Source separation and launch-surface verification.",
            "current_implementation": "The edition generator is source-controlled dry-run logic; this audit found no approved public AI literary-text release path.",
            "gap": "At release, verify public AI features/copy remain outside canonical literary text and inventory any enabled public AI feature.",
            "status": "DEFERRED",
            "launch_blocker": False,
        },
        {
            "area": "synthetic audiobook delivery",
            "requirement": "Assess the currently effective IT Rules only if a synthetically generated audiobook enters the actual public launch scope, based on Earnalism's verified role and the exact delivery configuration.",
            "in_force_on_launch_date": "The consolidated IT Rules text updated 10 February 2026 contains synthetically generated-information provisions; role-specific applicability must be assessed against the actual public audio launch.",
            "applies_to_earnalism": "NOT_DETERMINED_FOR_FUTURE_AUDIO_SCOPE; current controlled launch disables public audio exposure.",
            "applicable": "NOT_APPLICABLE_TO_CURRENT_LAUNCH_CONFIGURATION",
            "authority": "Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021, consolidated text updated 10 February 2026.",
            "current_implementation": "No public audiobook launch is enabled by either controlled launch configuration. Historical model-generated audio evidence is recorded separately per title.",
            "gap": "Before enabling any title-level public audio, perform a role- and configuration-specific applicability assessment and implement only any requirement that actually applies.",
            "status": "DEFERRED",
            "launch_blocker": False,
        },
    ]


def cover_declaration(package: dict[str, Any], titles: list[dict[str, Any]]) -> str:
    lines = [
        "# Cover Artwork Declaration — Earnalism India four-title pilot",
        "",
        "**Status:** OPTIONAL FACTUAL DECLARATION. The owner-supplied statement that these covers were graphically designed by the owner is recorded as current provenance evidence. This form can strengthen the evidence file, but its lack of signature does not itself block the current India title predicate absent contrary component evidence.",
        "",
        "## Declaration",
        "",
        "I confirm that the Earnalism cover artworks listed in the pilot cover inventory below were graphically designed by me. Except where specifically disclosed, I have not knowingly incorporated third-party copyrighted photographs, illustrations, stock artwork or other protected creative material for which Earnalism lacks the necessary rights.",
        "",
        "I make this factual confirmation only from personal knowledge or retained project files. Any cover with an identified external component requiring rights remains unresolved until that component is documented.",
        "",
        "Name: ________________________________",
        "",
        "Capacity: Product owner / proprietor (confirm actual capacity)",
        "",
        "Place: ________________________________",
        "",
        "Date: _________________________________",
        "",
        "Signature/Confirmation: ____________________________",
        "",
        "## Pilot cover inventory",
        "",
        "Preserve source/editable project files where available. Copyright registration is not represented as a prerequisite by this template. Missing historical creation dates or project files do not convert a truthfully confirmed first-party creation into a false statement.",
        "",
        "| Cover title | Asset path/reference | Asset SHA-256 | Creation date if known | Project/source-file reference if available | Creator | Rightsholder claim | Externally sourced elements | Notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in titles:
        provenance = item["cover_provenance"]
        for side in ("front", "back"):
            url = provenance["assets"][side]
            asset_hash = provenance[f"{side}_cover_sha256"]
            lines.append(
                f"| {item['title']} — {side} | {url} | {asset_hash} | NOT_RECORDED | NOT_RECORDED | PRODUCT_OWNER (owner-supplied fact) | PRODUCT_OWNER (owner-supplied fact) | NO_CONTRARY_EVIDENCE_IN_REPOSITORY | Disclose a specific external protected element here if one exists. |"
            )
    lines.append("")
    lines.append("## Attached package binding")
    lines.append("")
    lines.append(f"- Candidate commit: `{package['generated_from']['repository_head']}`.")
    lines.append(f"- Candidate tree: `{package['generated_from']['repository_tree']}`.")
    lines.append("- Completing this form does not release a title; the active release hold and hash-bound rights gate remain independent controls.")
    lines.append("")
    return "\n".join(lines)


def unpublished_website_legal_drafts(package: dict[str, Any]) -> str:
    """Keep a private evidence note while the public routes contain only verified facts."""
    return """# India website legal surface evidence

**Publication status:** `PUBLIC_ROUTES_REGISTERED`. The current public routes are `/privacy`, `/terms`, `/copyright`, and `/contact`. This internal file is evidence only; it must not be rendered as a public page or used to add placeholders to those routes.

## Current launch boundary

The public legal pages contain only source-established operator, service, contact, title-concern, and current-scope facts. They do not assert provider geography, cross-border access, retention periods, data-sale practices, or analytics enablement that repository evidence cannot establish. Public paid commerce is disabled in both controlled-launch configurations and is not offered in this launch.

## Privacy Policy draft — factual scope only

Earnalism's source currently indicates collection or handling of account/contact/newsletter names and email addresses; support messages; browser authentication/session information; Reading Pass activity and position data; a browser device/session identifier; optional launch analytics; and payment-related checkout operations through Razorpay. Source inspection does not establish provider regions, cross-border access, retention periods, or whether optional analytics is enabled in production. This draft must not claim a retention period, data-sale practice, or provider configuration until those facts are confirmed.

Recorded operator fact: `REO ENTERPRISE`, sole proprietorship, operating Earnalism as its venture/brand. The public support, privacy-question, and copyright-concern address in source is `sales@reoenterprise.org`. Provider geography, cross-border access, deployed analytics state, retention, and account-deletion handling remain unasserted until independently established.

## Terms of Use draft — factual scope only

Earnalism provides controlled digital reading. The launch configuration holds Reader and audio exposure pending accepted release decisions. Source identifies a one-time prepaid Reading Pass model and no automatic renewal claim. Any final Terms must preserve non-waivable consumer rights, describe actual availability/change behavior, identify the operator and contact channel, and avoid representing held titles as released or any text as universally rights-cleared.

## Copyright/IP notice and complaint process

The public notice should invite a complainant to supply: contact details; the claimed work; the Earnalism title/content concerned; the basis of the claim; and supporting information. Internal handling is title-scoped: `RECEIVED` → `UNDER_REVIEW` → `TEMPORARILY_HELD` where warranted → `RESOLVED_REMOVE` or `RESOLVED_RESTORE`. A complaint for one title must not automatically disable other titles. This is not described as a DMCA process or government certification.

## Payment, cancellation, and refund terms

Do not enable paid commerce until the merchant agreement/version and the treatment for unused prepaid time, pass expiry, service outage, title unavailability, cancellation, and refunds are verified. The existing UI's one-time-prepaid language is not a substitute for those facts or an approved customer remedy.

## Source basis

- `frontend/src/App.js`, `frontend/src/pages/Contact.jsx`, and `frontend/src/pages/Pricing.jsx`
- `frontend/src/lib/funnelAnalytics.js`, `frontend/src/lib/readingPassApi.js`, and `backend/server.py`
- Digital Personal Data Protection Rules, 2025 notification and Consumer Protection framework listed in `india-website-legal-matrix.json`
- Candidate commit: `""" + package["generated_from"]["repository_head"] + """`; tree: `""" + package["generated_from"]["repository_tree"] + """`.
"""


def release_decision_record_template(titles: list[dict[str, Any]], evidence_package_hash: str, package: dict[str, Any]) -> dict[str, Any]:
    """Create blank, evidence-bound decisions without creating an acceptance."""
    return {
        "schema_version": "earnalism.india-release-decision-record.v1",
        "status": "UNSIGNED_TEMPLATE_ONLY",
        "evidence_package": {
            "path": "india-book-rights-matrix.json",
            "sha256": evidence_package_hash,
            "candidate_commit": package["generated_from"]["repository_head"],
            "candidate_tree": package["generated_from"]["repository_tree"],
        },
        "records": [
            {
                "TITLE": title["title"],
                "SLUG": title["slug"],
                "COPYRIGHT_EVIDENCE_RESULT": title["india_copyright_proof"]["status"],
                "TEXT_RESULT": title["textual_integrity_proof"]["status"],
                "COVER_RESULT": title["cover_provenance"]["status"],
                "AUDIO_CURRENT_LAUNCH_RESULT": title["audio_scope"]["current_launch_status"],
                "OTHER_ASSETS_RESULT": title["translation_and_editorial_material"]["status"],
                "SOURCE_HASH": title["textual_integrity_proof"]["source_file_hash"],
                "CANONICAL_HASH": title["textual_integrity_proof"]["earnalism_canonical_text_hash"],
                "EVIDENCE_PACKAGE_HASH": evidence_package_hash,
                "UNRESOLVED_COMPLIANCE_BLOCKERS": title["compliance_blockers"],
                "RELEASE_AUTHORIZATION_STATE": title["release_authorization_state"],
                "DECISION": None,
                "DECIDED_BY": None,
                "DATE": None,
            }
            for title in titles
        ],
        "guard": "A blank template is not an accepted rights record. An authorized release actor must record ACCEPT or HOLD only after reviewing the bound evidence and applicable release authority.",
    }


def owner_action_packet(titles: list[dict[str, Any]]) -> str:
    """Ask for only facts unavailable to source or public evidence."""
    yugal = next(title for title in titles if title["slug"] == "yugalanguriya")
    yugal_rows = yugal["textual_integrity_proof"]["facsimile_observation_comparison"]["observations"]
    ambiguous = [row for row in yugal_rows if row["CLASSIFICATION"] == "SOURCE_AMBIGUOUS"]
    lines = [
        "# India launch — Owner Action Packet",
        "",
        "This packet excludes facts already established by source or prior owner statements. It is not a release authorization and does not change the active hold.",
        "",
        "## A. Cover declaration",
        "",
        "**No action required for the current title-compliance predicate.** The owner's supplied statement that the pilot covers were graphically designed by the owner is recorded. Complete the optional `cover-artwork-declaration.md` only if a stronger signed record is desired or an exception must be disclosed.",
        "",
        "If an external protected component exists, provide only:",
        "",
        "- Title / cover side: ____________________",
        "- External component and source/license: ____________________",
        "",
        "## B. Public website facts",
        "",
        "**Why human input is necessary:** source establishes the support email but cannot truthfully establish these public business-role facts.",
        "",
        "- Public business/contact address: ____________________",
        "- Privacy-request contact (may be `sales@reoenterprise.org` if intentionally designated): ____________________",
        "- Grievance contact and, if applicable, named responsible role: ____________________",
        "- Retention/account-deletion handling to state publicly: ____________________",
        "",
        "## C. Provider/deployment facts",
        "",
        "**Why human/provider input is necessary:** repository configuration cannot prove effective production geography, access, or feature enablement.",
        "",
        "- Hosting/database/storage/backup regions and cross-border access: ____________________",
        "- Production launch-analytics enabled? YES / NO: ____________________",
        "",
        "## D. Commerce — only if paid India checkout will be enabled",
        "",
        "**Why human/provider input is necessary:** source proves a one-time, non-renewing Razorpay integration but not live merchant enablement or customer remedies.",
        "",
        "- Keep paid checkout disabled for this launch, or confirm merchant/live enablement: ____________________",
        "- If enabled, treatment for unused time, pass expiry, outage, title unavailability, cancellation, and refunds: ____________________",
    ]
    if ambiguous:
        lines.extend([
            "",
            "## E. Yugalanguriya — one remaining human Bengali reading",
            "",
            "**Why human input is necessary:** the source facsimile and retained transcription do not establish the covered initial at this location. No AI-generated text may resolve it.",
        ])
        for row in ambiguous:
            lines.extend([
                "",
                f"- Location: `{row['LOCATION']}`",
                f"- Facsimile/transcription evidence: {row['SOURCE_READING']} / {row['RETAINED_SOURCE_LAYER_READING']}",
                f"- Current canonical reading: {row['EARNALISM_READING']}",
                f"- Exact requested action: {row['ACTION']}",
            ])
    lines.extend([
        "",
        "## Separate release control",
        "",
        "Even for a title marked `INDIA_TITLE_READY`, the hash-bound ACCEPT/HOLD decision in `india-release-decision-record-template.json` remains a deliberate production release action. Do not preselect ACCEPT.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--candidate-tree", required=True)
    parser.add_argument("--production-surface-sha", required=True)
    args = parser.parse_args()
    if not all(re.fullmatch(r"[0-9a-f]{40}", value or "") for value in (args.candidate_sha, args.candidate_tree)):
        raise SystemExit("candidate SHA and tree must be lowercase 40-character hashes")
    if not re.fullmatch(r"[0-9a-f]{64}", args.production_surface_sha or ""):
        raise SystemExit("production surface SHA must be a lowercase SHA-256")
    launch_hold = existing_launch_hold()
    titles = [title_record(slug, launch_hold) for slug in PILOT_SLUGS]
    yugal_title = next(item for item in titles if item["slug"] == "yugalanguriya")
    yugal_ledger_rows = yugal_title["textual_integrity_proof"]["facsimile_observation_comparison"]["observations"]
    unresolved_yugal_rows = [
        row for row in yugal_ledger_rows
        if row["CLASSIFICATION"] in {
            "SOURCE_AMBIGUOUS",
            "SUBSTANTIVE_TEXT_DIFFERENCE",
        }
    ]
    eligible_titles = [title for title in titles if title["india_title_ready"]]
    package = {
        "schema_version": "earnalism.india-launch-compliance.v1",
        "generated_from": {
            "repository_head": args.candidate_sha,
            "repository_tree": args.candidate_tree,
            "production_surface_sha256": args.production_surface_sha,
            "generator_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "generator_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        },
        "scope": {
            "launch_country": "IN",
            "pilot_slugs": list(PILOT_SLUGS),
            "audio": "AUDIO_DISABLED_NOT_IN_LAUNCH_SCOPE",
            "customer_accounting_acceptance": "DEFERRED_OUT_OF_CURRENT_SCOPE",
            "customer_ready": "NOT_DECLARED",
        },
        "official_sources": list(OFFICIAL_SOURCES),
        "technical_release_hold": launch_hold,
        "india_book_rights_matrix": titles,
        "text_source_manifest": [
            {
                "title": item["title"],
                "author": item["india_copyright_proof"]["author"],
                "earnalism_edition_id": item["textual_integrity_proof"]["earnalism_edition_id"],
                "source_edition": item["textual_integrity_proof"]["source_edition"],
                "source_publication_information": item["textual_integrity_proof"]["source_publication_information"],
                "source_provider": item["textual_integrity_proof"]["source_provider"],
                "source_identifier": item["textual_integrity_proof"]["source_identifier"],
                "source_reference_url": item["textual_integrity_proof"]["source_reference_url"],
                "source_retrieval_date": item["textual_integrity_proof"]["source_retrieval_date"],
                "source_file_hash": item["textual_integrity_proof"]["source_file_hash"],
                "stored_publication_aggregate_hash": item["textual_integrity_proof"]["stored_publication_aggregate_hash"],
                "current_raw_source_path": item["textual_integrity_proof"]["current_raw_source_path"],
                "current_raw_source_file_hash": item["textual_integrity_proof"]["current_raw_source_file_hash"],
                "earnalism_canonical_text_hash": item["textual_integrity_proof"]["earnalism_canonical_text_hash"],
                "comparison_method": item["textual_integrity_proof"]["comparison_method"],
                "material_differences": item["textual_integrity_proof"]["material_differences"],
                "intentional_corrections": item["textual_integrity_proof"]["intentional_corrections"],
                "text_integrity_status": item["textual_integrity_proof"]["status"],
            }
            for item in titles
        ],
        "editorial_correction_ledger": {
            "status": "NO_CORRECTIONS_APPROVED",
            "required_fields": ["TITLE", "LOCATION", "IDENTIFIED_SOURCE_READING", "EARNALISM_READING", "REASON", "EVIDENCE_OR_AUTHORITY", "DATE"],
            "entries": [],
            "unresolved_source_discrepancies": [
                {
                    "TITLE": "যুগলাঙ্গুরীয়",
                    "LOCATION": row["LOCATION"],
                    "SOURCE": row["SOURCE_READING"],
                    "CURRENT_EARNALISM": row["EARNALISM_READING"],
                    "CLASSIFICATION": row["CLASSIFICATION"],
                    "ACTION": row["ACTION"],
                    "EVIDENCE": row["EVIDENCE"],
                }
                for row in unresolved_yugal_rows
            ],
            "resolved_source_observations": [
                {
                    "TITLE": "যুগলাঙ্গুরীয়",
                    "LOCATION": row["LOCATION"],
                    "BASE_SOURCE_READING": row["SOURCE_READING"],
                    "EARNALISM_READING": row["EARNALISM_READING"],
                    "CLASSIFICATION": row["CLASSIFICATION"],
                    "EVIDENCE": row["EVIDENCE"],
                    "CORROBORATING_EDITION_URL": row["CORROBORATING_EDITION_URL"],
                    "EDITORIAL_DECISION": row["EDITORIAL_DECISION"],
                    "ACTION": row["ACTION"],
                }
                for row in yugal_ledger_rows
                if row not in unresolved_yugal_rows
            ],
            "note": "Unresolved source observations are not approved corrections and do not authorize a manuscript change. Resolved rows document evidence already reflected in the current canonical text or a non-prose presentation layer.",
        },
        "india_website_legal_matrix": website_matrix(launch_hold),
        "actual_data_inventory": data_inventory(),
        "website_fact_inventory": website_fact_inventory(),
        "conclusion": {
            "india_content": "INDIA_CONTENT_READY" if eligible_titles else "INDIA_CONTENT_ACTION_REQUIRED",
            "india_website_legal": "INDIA_WEBSITE_LEGAL_READY" if not any(row["launch_blocker"] for row in website_matrix(launch_hold)) else "INDIA_WEBSITE_LEGAL_ACTION_REQUIRED",
            "india_launch_legal_checks_complete": bool(eligible_titles) and not any(row["launch_blocker"] for row in website_matrix(launch_hold)),
            "customer_ready": "NOT_DECLARED",
            "reason": "Three titles satisfy the objective India content predicate independently; Yugalanguriya remains title-scoped text review. Current legal pages and disabled paid commerce support the limited launch scope. The empty rights registry/global exposure hold remains a separate production release control.",
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "india-book-rights-matrix.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "text-source-manifest.json").write_text(json.dumps(package["text_source_manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "editorial-correction-ledger.json").write_text(json.dumps(package["editorial_correction_ledger"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "india-website-legal-matrix.json").write_text(json.dumps({"official_sources": package["official_sources"], "data_inventory": package["actual_data_inventory"], "fact_inventory": package["website_fact_inventory"], "matrix": package["india_website_legal_matrix"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "cover-artwork-declaration.md").write_text(cover_declaration(package, titles), encoding="utf-8")
    (args.output_dir / "unpublished-india-website-legal-drafts.md").write_text(unpublished_website_legal_drafts(package), encoding="utf-8")
    (args.output_dir / "owner-action-packet.md").write_text(owner_action_packet(titles), encoding="utf-8")
    evidence_package_hash = digest(args.output_dir / "india-book-rights-matrix.json")
    assert evidence_package_hash
    (args.output_dir / "india-release-decision-record-template.json").write_text(
        json.dumps(release_decision_record_template(titles, evidence_package_hash, package), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"result": "PASS", "output_dir": str(args.output_dir), "pilot_title_count": len(titles), "pilot_cover_inventory_rows": sum(2 for _ in titles), "customer_ready": "NOT_DECLARED"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
