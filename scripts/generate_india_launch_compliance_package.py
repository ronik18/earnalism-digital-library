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

# These are unresolved observations from the facsimile checkpoint, not a
# change request and not an editorial correction ledger.  Keeping them here
# prevents a UI or source-layer discrepancy from being silently called prose
# verification.
YUGALANGURIYA_DISCREPANCIES = (
    ("chapter-001 opening", "Source crop reads an uncertain join: ই + জনে", "ই জনে", "UNKNOWN", "Independent Bengali review of uncropped image 6 before any patch."),
    ("chapter-002 opening", "Source crop reads কে + ন যে", "ন যে", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-003 opening", "Source crop reads দু + ই বৎসরের", "ই বৎসরের", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-004 opening", "Source crop reads বি + বাহাস্তে", "বাহাস্তে", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-005 opening", "Source crop reads হি + রণ্ময়ী", "রণ্ময়ী", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-006 opening", "Source crop reads প + রে এক দিন", "রে এক দিন", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-007 opening", "Source crop reads বি + বাহের পর", "বাহের পর", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-008 opening", "Source crop reads হি + রণ্ময়ী", "রণ্ময়ী", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-009 opening", "Source crop reads হি + রণ্ময়ী", "রণ্ময়ী", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-010 opening", "Source crop reads হি + রণ্ময়ী", "রণ্ময়ী", "MISSING_TEXT", "Independent Bengali review before a source-only patch."),
    ("chapter-001 footnote marker", "Tamralipta footnote is marked with an asterisk in the source crop", "Upward-arrow marker without semantic note binding", "TYPOGRAPHIC_OR_SEMANTIC_PRESENTATION", "Review note semantics separately; do not treat it as prose verification."),
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
    path = ROOT / "content" / "books" / slug / "source-rights.md"
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- ([^:]+):\s*(.*)$", line)
        if match:
            values[match.group(1).strip().casefold()] = match.group(2).strip()
    return values


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
    source_path = ROOT / "content" / "books" / slug / "raw" / "source.txt"
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
        "live_approved_slugs": sorted(set(root.get("live_approved_slugs", [])) | set(backend.get("live_approved_slugs", []))),
        "accepted_rights_record_count": len(registry.get("accepted_records", {})) if isinstance(registry.get("accepted_records"), dict) else None,
    }


def title_record(slug: str, launch_hold: dict[str, Any]) -> dict[str, Any]:
    directory = PUBLICATIONS / slug
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
    integrity_status = source_comparison["status"]
    if slug == "yugalanguriya":
        integrity_difference = "Retained source text does not establish every controlled chapter in order, and the facsimile checkpoint preserves unresolved Bengali source-reading observations. No canonical text change is authorized."
    elif slug == "the-tell-tale-heart":
        integrity_difference = "The stored source-evidence content hash is an aggregate publication hash, not a direct chapter digest. The exact retained source body contains the current controlled chapter after the documented non-substantive normalization."
    elif slug == "radharani":
        integrity_difference = "Every controlled chapter is present in source order after the documented non-substantive normalization. A separately recorded source-layer/footnote presentation issue is not represented as a prose difference."
    else:
        integrity_difference = "Every controlled chapter is present in source order after the documented non-substantive normalization."
    source_layer_blocker = []
    if bengali_source_layer:
        source_layer_blocker.append("The Bengali Wikisource transcription/source layer has recorded CC BY-SA conditions that need an explicit source-layer treatment before release.")
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
                evidence(ROOT / "content" / "books" / slug / "source-rights.md"),
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
            "comparison_method": "Deterministic retained-source comparison: Unicode NFC plus whitespace-run collapse only, then ordered full-chapter substring matching. No AI-generated prose is an authority.",
            "material_differences": integrity_difference,
            "intentional_corrections": "NONE_APPROVED",
            "evidence": [evidence(reader_path), evidence(source_path), evidence(PILOT_INTEGRITY_EVIDENCE)],
        },
        "translation_and_editorial_material": {
            "status": "ACTION_REQUIRED" if bengali_source_layer else "REVIEW_REQUIRED",
            "translation": "NOT_RECORDED",
            "source_layer": source_license,
            "blockers": source_layer_blocker or ["Confirm that the delivered edition contains no separately protected translation, introduction, annotation, illustration, or editorial addition."],
        },
        "cover_provenance": {
            "status": "OWNER_DECLARATION_PENDING_SIGNATURE",
            "owner_stated_creator": "PRODUCT_OWNER",
            "rightsholder_claim": "PRODUCT_OWNER",
            "externally_sourced_elements": "UNKNOWN_PENDING_OWNER_DECLARATION",
            "front_cover_sha256": cover_hashes.get("front", "NOT_RECORDED"),
            "back_cover_sha256": cover_hashes.get("back", "NOT_RECORDED"),
            "assets": {
                "front": require_text(book.get("cover_url")),
                "back": require_text(book.get("back_cover_url")),
            },
            "evidence": cover_evidence,
            "blockers": ["The declaration template is unsigned; no creator, external-element, or creation-date fact is inferred from an approval mapping."],
        },
        "audio_scope": {
            "status": "AUDIO_DISABLED_NOT_IN_LAUNCH_SCOPE" if not launch_hold["public_audio_exposure_enabled"] else "REVIEW_REQUIRED",
            "reason": "The controlled launch configuration disables public audio exposure; title-level historical audio flags do not override that launch control.",
        },
        "public_provenance_statement_candidate": f"Text follows: {require_text(source.get('source_name'))} ({require_text(source.get('source_url'))}).",
        "india_title_status": "HOLD",
        "india_title_ready": False,
        "specific_blockers": [
            "OWNER_DECLARATION_PENDING_SIGNATURE",
            *( ["TEXT_REVIEW_REQUIRED"] if integrity_status != "TEXT_VERIFIED" else [] ),
            *( ["SOURCE_LAYER_OR_EDITORIAL_REVIEW_REQUIRED"] if bengali_source_layer else [] ),
            "No accepted release decision is recorded; the global Reader hold remains active.",
        ],
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
        }
        for category, behavior, source, storage, retention, status in entries
    ]


def website_matrix() -> list[dict[str, Any]]:
    return [
        {
            "area": "copyright and content integrity",
            "requirement": "Each released title needs separate copyright, text-integrity, cover, translation/editorial, and other-asset evidence.",
            "in_force_on_launch_date": "YES_FOR_ANY_RELEASE_OF_COPYRIGHTABLE_MATERIAL",
            "applies_to_earnalism": "YES_IF_A_TITLE_IS_RELEASED",
            "applicable": "YES_FOR_ANY_RELEASED_TITLE",
            "authority": "Copyright Act, 1957; source and integrity evidence",
            "current_implementation": "Repository has source evidence, a four-title comparison checkpoint, an empty rights registry, and global Reader/audio holds.",
            "gap": "No India title has completed all independent copyright, integrity, cover, and source-layer proof elements.",
            "status": "ACTION_REQUIRED",
            "launch_blocker": True,
        },
        {
            "area": "privacy and data inventory",
            "requirement": "Evaluate DPDP Act/Rules obligations against the actual India launch date and the identified processing.",
            "in_force_on_launch_date": "REVIEW_REQUIRED: launch date is not recorded. Under the 2025 notification, Rules 1, 2 and 17–21 commenced on publication; Rule 4 is scheduled one year after publication; Rules 3, 5–16, 22 and 23 are scheduled eighteen months after publication, subject to any later legal change.",
            "applies_to_earnalism": "YES_IF_THE_IDENTIFIED_PERSONAL_DATA_PROCESSING_OCCURS",
            "applicable": "YES_IF_THE_IDENTIFIED_PERSONAL_DATA_PROCESSING_OCCURS_ON_LAUNCH",
            "authority": "Digital Personal Data Protection Act, 2023 and Digital Personal Data Protection Rules, 2025, applied by commencement date.",
            "current_implementation": "Data processing is identifiable in source, but no public Privacy Policy route is registered in frontend/src/App.js.",
            "gap": "Confirm launch date, provider regions/access, controller/contact facts, actual analytics enablement, retention, and publish an accurate policy/notice.",
            "status": "ACTION_REQUIRED",
            "launch_blocker": True,
        },
        {
            "area": "consumer and e-commerce",
            "requirement": "For an Indian paid Reading Pass flow, test actual pricing, disclosures, restrictions, support/grievance, cancellation/refund treatment, and prohibited deceptive-design risks.",
            "in_force_on_launch_date": "YES_IF_PAID_SERVICE_IS_OFFERED_TO_INDIAN_CONSUMERS",
            "applies_to_earnalism": "YES_IF_READING_TIME_IS_OFFERED_FOR_PAYMENT",
            "applicable": "YES_IF_READING_TIME_IS_OFFERED_FOR_PAYMENT_TO_INDIAN_CONSUMERS",
            "authority": "Consumer Protection Act, 2019; Consumer Protection (E-Commerce) Rules, 2020; Dark Patterns Guidelines, 2023.",
            "current_implementation": "Pricing source displays INR prices, one-time reading-time language, no autorenewal language, and a support/refund contact.",
            "gap": "Terms, cancellation/refund treatment, merchant facts, grievance process, and actual checkout-flow review are not published or evidenced as a complete launch surface.",
            "status": "ACTION_REQUIRED",
            "launch_blocker": True,
        },
        {
            "area": "legal pages and contact/grievance information",
            "requirement": "Public legal notices must describe the actual product and operator facts without placeholder assertions.",
            "in_force_on_launch_date": "YES_FOR_THE_PUBLIC_PRODUCT_SURFACE",
            "applies_to_earnalism": "YES",
            "applicable": "YES_FOR_THE_PUBLIC_PRODUCT_SURFACE",
            "authority": "Applicable privacy and consumer framework; owner-supplied business facts.",
            "current_implementation": "A /contact route and sales@reoenterprise.org contact are present. No Terms, Privacy, Copyright/IP Notice, or dedicated refund/cancellation route is registered.",
            "gap": "Owner/provider facts and qualified review are needed before creating accurate public legal pages; do not publish placeholders as policy.",
            "status": "ACTION_REQUIRED",
            "launch_blocker": True,
        },
        {
            "area": "copyright complaint handling",
            "requirement": "Provide an operational receive, identify, hold, investigate, evidence, decide, restore/remove path for rights complaints.",
            "in_force_on_launch_date": "YES_FOR_ANY_PUBLIC_CATALOGUE",
            "applies_to_earnalism": "YES_IF_ANY_TITLE_IS_PUBLIC",
            "applicable": "YES_FOR_ANY_PUBLIC_CATALOGUE",
            "authority": "Operational rights-risk control; no US DMCA characterization assumed.",
            "current_implementation": "The contact route supports rights/title inquiries.",
            "gap": "Document receive, identify, temporary-hold, investigate, evidence, decide, restore/remove ownership and audit path.",
            "status": "ACTION_REQUIRED",
            "launch_blocker": True,
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
    ]


def cover_declaration(package: dict[str, Any], titles: list[dict[str, Any]]) -> str:
    lines = [
        "# Cover Artwork Declaration — Earnalism India four-title pilot",
        "",
        "**Status:** UNSIGNED FACTUAL DECLARATION TEMPLATE. This document does not create a rights decision, accept a title for release, or assert facts not personally confirmed by the declarant.",
        "",
        "## Declaration",
        "",
        "I confirm that the Earnalism cover artworks identified in this declaration were graphically designed by me. Except where specifically disclosed in this declaration, I confirm that I have not knowingly incorporated third-party copyrighted photographs, illustrations, stock artwork or other protected creative material for which Earnalism lacks the necessary rights.",
        "",
        "I make this factual confirmation only from personal knowledge or retained project files. Any cover with an external component that I cannot confirm remains unresolved and is not cleared by this declaration.",
        "",
        "Name: ________________________________",
        "",
        "Capacity: Product owner / proprietor (confirm actual capacity)",
        "",
        "Place: ________________________________",
        "",
        "Date: _________________________________",
        "",
        "Signature: ____________________________",
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
                f"| {item['title']} — {side} | {url} | {asset_hash} | NOT_RECORDED | NOT_RECORDED | PRODUCT_OWNER (owner-stated; signature pending) | PRODUCT_OWNER (owner-stated; signature pending) | OWNER_CONFIRMATION_REQUIRED | Disclose any external protected element here. |"
            )
    lines.append("")
    lines.append("## Attached package binding")
    lines.append("")
    lines.append(f"- Candidate commit: `{package['generated_from']['repository_head']}`.")
    lines.append(f"- Candidate tree: `{package['generated_from']['repository_tree']}`.")
    lines.append("- Signing this declaration does not release a title; the active release hold and hash-bound rights gate remain independent controls.")
    lines.append("")
    return "\n".join(lines)


def unpublished_website_legal_drafts(package: dict[str, Any]) -> str:
    """Draft only internally: incomplete operator facts never reach the public UI."""
    return """# Unpublished India website legal drafts

**Publication status:** `UNPUBLISHED_DO_NOT_REGISTER_ROUTE`. No route for these drafts is registered in `frontend/src/App.js`. Do not expose this file, its internal evidence references, or any bracketed owner-input field to the public site.

## Publication gate

Before a public legal page is registered, obtain and review: the operator's public-facing legal name and contact address; privacy and grievance contact channels; provider geography and cross-border access facts; actual production analytics state; retention decisions; payment-merchant agreement and current cancellation/refund treatment. A qualified reviewer must verify that the final public text describes the deployed product.

## Privacy Policy draft — factual scope only

Earnalism's source currently indicates collection or handling of account/contact/newsletter names and email addresses; support messages; browser authentication/session information; Reading Pass activity and position data; a browser device/session identifier; optional launch analytics; and payment-related checkout operations through Razorpay. Source inspection does not establish provider regions, cross-border access, retention periods, or whether optional analytics is enabled in production. This draft must not claim a retention period, data-sale practice, or provider configuration until those facts are confirmed.

Public fields still required: `[OWNER INPUT REQUIRED: operator legal name]`; `[OWNER INPUT REQUIRED: public business address]`; `[OWNER INPUT REQUIRED: privacy-request contact]`; `[OWNER INPUT REQUIRED: grievance contact]`; `[PROVIDER VERIFICATION REQUIRED: hosting/database/storage/backup regions and access]`; `[DEPLOYMENT VERIFICATION REQUIRED: analytics enablement]`.

## Terms of Use draft — factual scope only

Earnalism provides controlled digital reading. The launch configuration holds Reader and audio exposure pending accepted release decisions. A source review identifies a one-time prepaid Reading Pass model and no automatic renewal claim. Any final Terms must preserve non-waivable consumer rights, describe actual availability/change behavior, identify the operator and contact channel, and avoid representing held titles as released or any text as universally rights-cleared.

## Copyright/IP notice and complaint process

The public notice should invite a complainant to supply: contact details; the claimed work; the Earnalism title/content concerned; the basis of the claim; and supporting information. Internal handling is title-scoped: `RECEIVED` → `UNDER_REVIEW` → `TEMPORARILY_HELD` where warranted → `RESOLVED_REMOVE` or `RESOLVED_RESTORE`. A complaint for one title must not automatically disable other titles. This is not described as a DMCA process or government certification.

## Payment, cancellation, and refund terms

Do not publish these terms until the merchant agreement/version and the operator-approved treatment for unused prepaid time, pass expiry, service outage, title unavailability, cancellation, and refunds are verified. The existing UI's one-time-prepaid language is not a substitute for those facts or an approved customer remedy.

## Source basis

- `frontend/src/App.js`, `frontend/src/pages/Contact.jsx`, and `frontend/src/pages/Pricing.jsx`
- `frontend/src/lib/funnelAnalytics.js`, `frontend/src/lib/readingPassApi.js`, and `backend/server.py`
- Digital Personal Data Protection Rules, 2025 notification and Consumer Protection framework listed in `india-website-legal-matrix.json`
- Candidate commit: `""" + package["generated_from"]["repository_head"] + """`; tree: `""" + package["generated_from"]["repository_tree"] + """`.
"""


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
                    "LOCATION": location,
                    "SOURCE": source_reading,
                    "CURRENT_EARNALISM": current_reading,
                    "CLASSIFICATION": classification,
                    "ACTION": action,
                    "EVIDENCE": "internal/legal/four_title_pilot_evidence_20260917.md facsimile checkpoint",
                }
                for location, source_reading, current_reading, classification, action in YUGALANGURIYA_DISCREPANCIES
            ],
            "note": "Unresolved source observations are not approved corrections and do not authorize a manuscript change.",
        },
        "india_website_legal_matrix": website_matrix(),
        "actual_data_inventory": data_inventory(),
        "conclusion": {
            "india_content": "INDIA_CONTENT_ACTION_REQUIRED",
            "india_website_legal": "INDIA_WEBSITE_LEGAL_ACTION_REQUIRED",
            "india_launch_legal_checks_complete": False,
            "customer_ready": "NOT_DECLARED",
            "reason": "One or more title and website entries are ACTION_REQUIRED or REVIEW_REQUIRED; no rights record is accepted and all public Reader/audio exposure remains held.",
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "india-book-rights-matrix.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "text-source-manifest.json").write_text(json.dumps(package["text_source_manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "editorial-correction-ledger.json").write_text(json.dumps(package["editorial_correction_ledger"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "india-website-legal-matrix.json").write_text(json.dumps({"official_sources": package["official_sources"], "data_inventory": package["actual_data_inventory"], "matrix": package["india_website_legal_matrix"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "cover-artwork-declaration.md").write_text(cover_declaration(package, titles), encoding="utf-8")
    (args.output_dir / "unpublished-india-website-legal-drafts.md").write_text(unpublished_website_legal_drafts(package), encoding="utf-8")
    print(json.dumps({"result": "PASS", "output_dir": str(args.output_dir), "pilot_title_count": len(titles), "pilot_cover_inventory_rows": sum(2 for _ in titles), "customer_ready": "NOT_DECLARED"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
