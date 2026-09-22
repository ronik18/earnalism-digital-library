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


def canonical_chapter_hashes(directory: Path) -> tuple[list[dict[str, str]], str]:
    """Bind ordered delivered chapter content, never reader-manifest metadata.

    Reader manifests intentionally do not embed protected text or its chapter
    digests.  The controlled chapter records do, and each record self-binds its
    content hash.  An absent/malformed chapter must make the package fail,
    rather than producing an empty digest that looks valid.
    """
    records: list[tuple[int, str, str]] = []
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
        records.append((order, chapter_id, content_hash))
    if not records or len({item[0] for item in records}) != len(records):
        raise ValueError(f"missing or duplicate ordered controlled chapters: {directory}")
    records.sort()
    values = [{"chapter_id": chapter_id, "content_sha256": content_hash} for _, chapter_id, content_hash in records]
    aggregate = sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    return values, aggregate


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
    title = require_text(book.get("title") or note.get("title"), slug)
    author = require_text(book.get("author") or note.get("author"))
    source_license = require_text(source.get("source_license"))
    bengali_source_layer = source.get("source_name") == "Bengali Wikisource"
    single_chapter_hash = chapter_hashes[0]["content_sha256"] if len(chapter_hashes) == 1 else None
    source_content_hash = require_text(source.get("content_hash"))
    direct_source_binding = single_chapter_hash == source_content_hash if single_chapter_hash else None
    integrity_status = "TEXT_VERIFIED" if slug == "a-ghost-story" and direct_source_binding is True else "TEXT_REVIEW_REQUIRED"
    if slug == "the-tell-tale-heart" and direct_source_binding is False:
        integrity_difference = "The current delivered chapter hash differs from the stored source-evidence content hash. Treat earlier comparison reporting as historical until the exact current source-to-canonical comparison is reproduced and explained."
    elif integrity_status == "TEXT_VERIFIED":
        integrity_difference = "No material difference recorded in the completed source-comparison evidence; the single controlled chapter also matches the stored source-evidence content hash."
    else:
        integrity_difference = "Existing source-comparison evidence records a presentation/footnote difference, an unresolved source-reading repair proposal, or a current aggregate source-to-canonical binding that needs review; no canonical text change is authorized."
    copyright_blockers = [
        "Author/date/category facts are recorded in repository source notes but lack an independently attested factual citation in this package.",
        "No accepted hash-bound rights decision exists in the production registry.",
    ]
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
            "status": "INDIA_COPYRIGHT_REVIEW_REQUIRED",
            "statutory_category": "ORDINARY_PUBLISHED_LITERARY_WORK_CLAIMED_REQUIRES_FACTUAL_CONFIRMATION",
            "author": author,
            "author_death_year": require_text(note.get("author death year")),
            "joint_authorship": "NOT_RECORDED",
            "source_publication_year": require_text(note.get("original publication year")),
            "term_rule_to_apply_after_category_confirmation": "Copyright Act, 1957 section 22 only if the work is an ordinary published literary work and no different statutory category applies.",
            "evidence": [evidence(source_path), evidence(ROOT / "content" / "books" / slug / "source-rights.md")],
            "blockers": copyright_blockers,
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
            "stored_source_content_hash": source_content_hash,
            "earnalism_canonical_text_hash": canonical_text_hash,
            "canonical_chapter_hashes": chapter_hashes,
            "direct_single_chapter_source_binding": direct_source_binding if direct_source_binding is not None else "NOT_APPLICABLE_MULTI_CHAPTER",
            "comparison_method": "Recorded four-title deterministic source comparison: documented NFC, line-ending, and whitespace normalization; source-to-canonical paragraph/body checks. No AI-generated prose is an authority.",
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
            "INDIA_COPYRIGHT_REVIEW_REQUIRED",
            "OWNER_DECLARATION_PENDING_SIGNATURE",
            *( ["TEXT_REVIEW_REQUIRED"] if integrity_status != "TEXT_VERIFIED" else [] ),
            *( ["CURRENT_DELIVERED_TEXT_HASH_DIFFERS_FROM_STORED_SOURCE_EVIDENCE"] if slug == "the-tell-tale-heart" and direct_source_binding is False else [] ),
            *( ["SOURCE_LAYER_OR_EDITORIAL_REVIEW_REQUIRED"] if bengali_source_layer else [] ),
            "No accepted release decision is recorded; the global Reader hold remains active.",
        ],
    }


def data_inventory() -> list[dict[str, Any]]:
    entries = (
        ("name", "account, contact, and newsletter forms", "frontend/src/pages/Contact.jsx; frontend/src/pages/Home.jsx", "ACTION_REQUIRED"),
        ("email", "account, contact, and newsletter forms", "frontend/src/pages/Contact.jsx; frontend/src/pages/Home.jsx; frontend/src/pages/Account.jsx", "ACTION_REQUIRED"),
        ("authentication information", "browser session/token handling", "frontend/src/pages/Reader.jsx; backend/server.py", "ACTION_REQUIRED"),
        ("reading/activity history and position", "Reading Pass position service", "frontend/src/pages/Reader.jsx; backend/reading_pass_service.py", "ACTION_REQUIRED"),
        ("analytics and device/session identifiers", "optional funnel analytics; browser local-storage session identifier", "frontend/src/lib/funnelAnalytics.js; backend/server.py", "REVIEW_REQUIRED"),
        ("support communications", "contact form submission", "frontend/src/pages/Contact.jsx", "ACTION_REQUIRED"),
        ("payment-related information", "Razorpay checkout and wallet/payment operations; no raw payment data claimed by this source inventory", "frontend/src/pages/Pricing.jsx; backend/server.py", "REVIEW_REQUIRED"),
    )
    return [
        {"data_category": category, "observed_product_behavior": behavior, "source": source, "status": status}
        for category, behavior, source, status in entries
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


def cover_declaration(package: dict[str, Any], all_titles: list[dict[str, Any]]) -> str:
    lines = [
        "# Cover Artwork Declaration — Earnalism catalogue",
        "",
        "**Status:** UNSIGNED FACTUAL DECLARATION TEMPLATE. This document does not create a rights decision, accept a title for release, or assert facts not personally confirmed by the declarant.",
        "",
        "## Declaration",
        "",
        "I, the undersigned product owner, declare only the cover facts I have personally verified. For every listed cover I confirm as personally created, I identify the creator and claimed rightsholder as the product owner and state whether any external protected component was used. Any UNKNOWN entry remains unresolved and is not cleared by this declaration.",
        "",
        "Name: ________________________________",
        "",
        "Capacity: Product owner / proprietor (confirm actual capacity)",
        "",
        "Signature: ____________________________",
        "",
        "Date: _________________________________",
        "",
        "Place: ________________________________",
        "",
        "## Catalogue cover inventory",
        "",
        "Complete the factual fields below only from personal knowledge or retained project files. Preserve source/editable project files where available. Copyright registration is not represented as a prerequisite by this template.",
        "",
        "| Cover title | Asset path/reference | Asset SHA-256 | Creation date if known | Project/source-file reference if available | Creator | Rightsholder claim | Externally sourced elements | Notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in all_titles:
        book = item["book"]
        for side, url_key in (("front", "cover_url"), ("back", "back_cover_url")):
            url = require_text(book.get(url_key))
            asset_hash = item["cover_hashes"].get(side, "NOT_RECORDED")
            lines.append(
                f"| {item['title']} — {side} | {url} | {asset_hash} | UNKNOWN | UNKNOWN | PRODUCT_OWNER (pending signature) | PRODUCT_OWNER (pending signature) | UNKNOWN | Complete only if personally verified. |"
            )
    lines.append("")
    lines.append("## Attached package binding")
    lines.append("")
    lines.append(f"- Candidate commit: `{package['generated_from']['repository_head']}`.")
    lines.append(f"- Candidate tree: `{package['generated_from']['repository_tree']}`.")
    lines.append("- Signing this declaration does not release a title; the active release hold and hash-bound rights gate remain independent controls.")
    lines.append("")
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
    all_titles: list[dict[str, Any]] = []
    for directory in sorted(path for path in PUBLICATIONS.iterdir() if path.is_dir()):
        book = read_json(directory / "public_book.json")
        if not book:
            continue
        note = source_rights_note(directory.name)
        all_titles.append({
            "slug": directory.name,
            "title": require_text(book.get("title") or note.get("title"), directory.name),
            "book": book,
            "cover_hashes": active_cover_hashes(directory / "cover_approval_evidence.json"),
        })
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
                "stored_source_content_hash": item["textual_integrity_proof"]["stored_source_content_hash"],
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
            "note": "Existing Yugalanguriya repair proposals remain review proposals and are intentionally not ledger entries or manuscript changes.",
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
    (args.output_dir / "cover-artwork-declaration.md").write_text(cover_declaration(package, all_titles), encoding="utf-8")
    print(json.dumps({"result": "PASS", "output_dir": str(args.output_dir), "pilot_title_count": len(titles), "catalogue_cover_inventory_rows": sum(2 for _ in all_titles), "customer_ready": "NOT_DECLARED"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
