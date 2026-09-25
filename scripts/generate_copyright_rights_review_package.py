#!/usr/bin/env python3
"""Generate a read-only, fail-closed copyright evidence package.

The package inventories repository-controlled publication inputs.  It does
not evaluate law, create a decision record, or make any source authoritative
for publication.  A qualified reviewer must make each eventual decision.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.rights_decision_gate import evaluate_runtime_path

PUBLICATIONS = ROOT / "data" / "controlled_publications"
RUNTIME_PUBLICATIONS = ROOT / "backend" / "data" / "controlled_publications"
HELD_TITLE_ARCHIVES = {
    "yugalanguriya": ROOT / "internal" / "archives" / "held_titles" / "yugalanguriya",
}
REGISTRY = ROOT / "backend" / "data" / "rights_decision_registry.json"
ROOT_LAUNCH = ROOT / "data" / "controlled_launch.json"
BACKEND_LAUNCH = ROOT / "backend" / "data" / "controlled_launch.json"
PILOT_SLUGS = (
    "a-ghost-story",
    "the-tell-tale-heart",
    "radharani",
    "yugalanguriya",
)
RELEASE_RIGHTS_OPERATOR_ID = "reo-enterprise"
RELEASE_RIGHTS_COMPONENT_FILENAMES = (
    "public_book.json",
    "reader_manifest.json",
    "source_evidence.json",
    "approval_evidence.json",
    "checksum_manifest.json",
    "publication_manifest.json",
)
COMPONENT_FIELDS = (
    "title", "slug", "asset_component", "component_sha256", "author_creator", "source",
    "source_url_or_archival_reference", "source_edition", "publication_date",
    "author_death_year", "jurisdictions_assessed", "claimed_rights_basis",
    "license", "license_version", "attribution_requirement",
    "modification_commercial_use_conditions", "provenance_evidence",
    "uncertainties", "review_status", "qualified_reviewer", "review_date",
    "decision",
)
OFFICIAL_INDIA_MATERIALS = (
    {
        "topic": "Copyright Act, 1957, Chapter III (protected work categories)",
        "url": "https://copyright.gov.in/Copyright_Act_1957/chapter_iii.html",
    },
    {
        "topic": "Copyright Act, 1957, Chapter V (terms, including sections 22 and 27)",
        "url": "https://copyright.gov.in/Copyright_Act_1957/chapter_v.html",
    },
    {
        "topic": "Copyright Rules, 2013",
        "url": "https://www.copyright.gov.in/Copyright_Rules_2013/index.html",
    },
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def digest(path: Path) -> str | None:
    return sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def repository_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def evidence(path: Path) -> list[dict[str, str]]:
    value = digest(path)
    return [{"path": repository_path(path), "sha256": value}] if value else []


def source_rights_note(slug: str) -> dict[str, str]:
    path = content_book_dir(slug) / "source-rights.md"
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- ([^:]+):\s*(.*)$", line)
        if match:
            values[match.group(1).strip().casefold()] = match.group(2).strip()
    return values


def content_book_dir(slug: str) -> Path:
    archive = HELD_TITLE_ARCHIVES.get(slug)
    return archive / "source-book" if archive else ROOT / "content" / "books" / slug


def controlled_package_dir(slug: str) -> Path:
    archive = HELD_TITLE_ARCHIVES.get(slug)
    if archive:
        return archive / "controlled-publication-package"
    runtime_package = RUNTIME_PUBLICATIONS / slug
    # Runtime packages are authoritative when they carry their own accepted
    # decision. Existing pilot decisions remain in the review/control-plane
    # package and must not be shadowed by decision-less runtime directories.
    if (runtime_package / "rights_decision.json").is_file():
        return runtime_package
    return PUBLICATIONS / slug


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else "NOT_RECORDED"


def optional(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def component(
    *, title: str, slug: str, name: str, creator: Any, source: Any,
    reference: Any, edition: Any, publication_date: Any, death_year: Any,
    jurisdictions: list[str], basis: Any, license_name: Any,
    attribution: Any, conditions: Any, provenance: list[dict[str, str]],
    uncertainties: list[str], status: str, component_sha256: Any = "NOT_RECORDED",
) -> dict[str, Any]:
    row = {
        "title": title,
        "slug": slug,
        "asset_component": name,
        "component_sha256": text(component_sha256),
        "author_creator": text(creator),
        "source": text(source),
        "source_url_or_archival_reference": text(reference),
        "source_edition": text(edition),
        "publication_date": text(publication_date),
        "author_death_year": text(death_year),
        "jurisdictions_assessed": jurisdictions,
        "claimed_rights_basis": text(basis),
        "license": text(license_name),
        "license_version": "NOT_RECORDED",
        "attribution_requirement": text(attribution),
        "modification_commercial_use_conditions": text(conditions),
        "provenance_evidence": provenance,
        "uncertainties": uncertainties,
        "review_status": status,
        "qualified_reviewer": "NOT_RECORDED",
        "review_date": "NOT_RECORDED",
        "decision": "PENDING_QUALIFIED_REVIEW",
    }
    if tuple(row) != COMPONENT_FIELDS:
        raise AssertionError("component evidence schema drift")
    return row


def active_cover_evidence(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    payload = read_json(path)
    if not payload:
        return [], ["No cover approval/provenance record is present in the controlled publication directory."]
    approvals = payload.get("active_approvals")
    if not isinstance(approvals, dict) or not approvals:
        return evidence(path), ["Cover evidence exists but has no active approval mapping."]
    return evidence(path), [
        "The record documents an owner visual-assignment event, not a qualified rights decision.",
        "The creator, licence, licence version, commercial-use scope, and territory scope require qualified review.",
    ]


def active_cover_sha256(path: Path, kind: str) -> str:
    payload = read_json(path)
    approvals = payload.get("active_approvals") if isinstance(payload.get("active_approvals"), dict) else {}
    active_event = approvals.get(kind)
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    for event in history:
        if isinstance(event, dict) and event.get("event_id") == active_event:
            return text(event.get("remote_sha256") or event.get("candidate_sha256"))
    return "NOT_RECORDED"


def detected_audio(book: dict[str, Any]) -> bool:
    return bool(
        book.get("audio_enabled") is True
        or book.get("audiobook_enabled") is True
        or book.get("audio_url")
        or isinstance(book.get("audiobook"), dict)
        or isinstance(book.get("audiobook_assets"), dict)
    )


def chapter_declares_visual_asset(chapter: Any) -> bool:
    if not isinstance(chapter, dict):
        return False
    if chapter.get("has_images") is True:
        return True
    count = chapter.get("image_count")
    return isinstance(count, int) and not isinstance(count, bool) and count > 0


def accepted_controlled_release(slug: str, directory: Path, jurisdictions: list[str], registry: dict[str, Any]) -> bool:
    """Evaluate the current exact runtime decision without creating one."""
    country = next((item for item in jurisdictions if item == "IN"), "")
    decision = read_json(directory / "rights_decision.json")
    required_components = {
        name.removesuffix(".json"): digest(directory / name)
        for name in RELEASE_RIGHTS_COMPONENT_FILENAMES
    }
    if not country or not decision or any(value is None for value in required_components.values()):
        return False
    accepted_records = registry.get("accepted_records")
    revoked = registry.get("revoked_decision_ids")
    if not isinstance(accepted_records, dict) or not isinstance(revoked, list):
        return False
    verdict = evaluate_runtime_path(
        "catalog_cta",
        record=decision,
        edition_id=slug,
        operator_id=RELEASE_RIGHTS_OPERATOR_ID,
        country=country,
        country_trusted=True,
        required_components=required_components,
        accepted_records=accepted_records,
        revoked_decision_ids=frozenset(item for item in revoked if isinstance(item, str)),
        now=datetime.now(timezone.utc),
    )
    return verdict.passed is True


def title_inventory(
    slug: str,
    pilot_countries: dict[str, list[str]],
    registry: dict[str, Any],
    live_slugs: set[str],
) -> dict[str, Any]:
    directory = controlled_package_dir(slug)
    book_path = directory / "public_book.json"
    source_path = directory / "source_evidence.json"
    approval_path = directory / "approval_evidence.json"
    cover_path = directory / "cover_approval_evidence.json"
    book = read_json(book_path)
    source = read_json(source_path)
    approval = read_json(approval_path)
    note = source_rights_note(slug)
    title = text(book.get("title") or note.get("title") or slug)
    author = text(book.get("author") or source.get("author_name") or source.get("author") or note.get("author"))
    author_death_year = text(source.get("author_death_year") or note.get("author death year"))
    publication_date = text(source.get("original_publication_year") or note.get("original publication year"))
    commercial_dispositions = registry.get("commercial_batch_dispositions")
    commercial_disposition = (
        commercial_dispositions.get(f"controlled-{slug}")
        if isinstance(commercial_dispositions, dict)
        else None
    )
    jurisdictions = list(pilot_countries.get(slug, []))
    if not jurisdictions and isinstance(commercial_disposition, dict):
        jurisdictions = list(commercial_disposition.get("countries") or [])
    accepted_rights = accepted_controlled_release(slug, directory, jurisdictions, registry)
    accepted_for_publication = accepted_rights and slug in live_slugs
    rights_accepted_unexposed = (
        accepted_rights
        and slug not in live_slugs
        and isinstance(commercial_disposition, dict)
        and commercial_disposition.get("status") == "RIGHTS_ACCEPTED_UNEXPOSED"
        and commercial_disposition.get("access_mode") == "COMMERCIAL_ENTITLEMENT"
    )
    source_provenance = evidence(source_path) + evidence(content_book_dir(slug) / "source-rights.md")
    source_complete = all(source.get(key) for key in ("content_hash", "source_hash", "source_url", "source_name", "source_license", "rights_basis"))
    text_status = "EVIDENCE_READY_FOR_REVIEW" if source_complete else "HOLD"
    core_uncertainties = [
        "Repository source statements are factual inputs only; a qualified reviewer must determine the applicable legal effect.",
    ]
    if not accepted_rights:
        core_uncertainties.append("No accepted hash-bound rights record exists in the production registry.")
    if not jurisdictions:
        core_uncertainties.insert(0, "No intended-publication jurisdiction is recorded for this non-pilot title.")
    rows: list[dict[str, Any]] = [
        component(
            title=title, slug=slug, name="underlying_literary_text", creator=author,
            source=source.get("source_name"), reference=source.get("source_url"),
            edition=note.get("source type"), publication_date=publication_date,
            death_year=author_death_year, jurisdictions=jurisdictions,
            basis=source.get("rights_basis"), license_name=source.get("source_license"),
            attribution=source.get("required_attribution"),
            conditions=source.get("commercial_use_allowed"), provenance=source_provenance,
            uncertainties=core_uncertainties, status=text_status, component_sha256=source.get("content_hash"),
        ),
        component(
            title=title, slug=slug, name="exact_digital_text_or_transcription", creator=author,
            source=source.get("source_name"), reference=source.get("source_url"),
            edition=note.get("source format downloaded"), publication_date=source.get("downloaded_at"),
            death_year=author_death_year, jurisdictions=jurisdictions,
            basis="Repository source/content hashes bind the extracted text; legal authority for this exact transcription is not recorded.",
            license_name=source.get("source_license"), attribution=source.get("required_attribution"),
            conditions=source.get("commercial_use_allowed"), provenance=source_provenance,
            uncertainties=core_uncertainties + ["Text extraction/normalisation may create edition-specific questions."], status=text_status,
            component_sha256=source.get("source_hash"),
        ),
    ]
    translator = optional(source.get("translator_name"))
    if translator:
        rows.append(component(
            title=title, slug=slug, name="translation_or_adaptation", creator=translator,
            source=source.get("source_name"), reference=source.get("source_url"),
            edition=note.get("source edition"), publication_date=source.get("revised_edition_year"),
            death_year=source.get("translator_death_year"), jurisdictions=jurisdictions,
            basis=source.get("rights_basis"), license_name=source.get("source_license"),
            attribution=source.get("required_attribution"), conditions="NOT_RECORDED",
            provenance=source_provenance,
            uncertainties=core_uncertainties + ["Translation/adaptation is independently protectable and no accepted decision is recorded."],
            status="HOLD", component_sha256=source.get("content_hash"),
        ))
    rows.append(component(
        title=title, slug=slug, name="editorial_notes_annotations_or_edition_material", creator="NOT_RECORDED",
        source="NOT_RECORDED", reference="NOT_RECORDED", edition=note.get("source type"),
        publication_date="NOT_RECORDED", death_year="NOT_RECORDED", jurisdictions=jurisdictions,
        basis="NOT_RECORDED", license_name="NOT_RECORDED", attribution="NOT_RECORDED",
        conditions="NOT_RECORDED", provenance=source_provenance,
        uncertainties=core_uncertainties + ["Reviewer must confirm whether the delivered edition contains editorial additions, notes, annotations, or a protected typographic selection."],
        status="HOLD", component_sha256="NOT_RECORDED",
    ))
    cover_provenance, cover_uncertainties = active_cover_evidence(cover_path)
    cover_urls = {key: book.get(key) for key in ("cover_url", "back_cover_url")}
    for kind, url_key in (("front_cover_artwork", "cover_url"), ("back_cover_artwork", "back_cover_url")):
        reference = cover_urls[url_key]
        rows.append(component(
            title=title, slug=slug, name=kind, creator="NOT_RECORDED",
            source="controlled publication cover mapping" if reference else "NOT_RECORDED",
            reference=reference, edition="NOT_RECORDED", publication_date="NOT_RECORDED",
            death_year="NOT_RECORDED", jurisdictions=jurisdictions, basis="NOT_RECORDED",
            license_name="NOT_RECORDED", attribution="NOT_RECORDED", conditions="NOT_RECORDED",
            provenance=cover_provenance + evidence(book_path),
            uncertainties=cover_uncertainties + (["No cover URL is mapped in the book record."] if not reference else []),
            status="HOLD", component_sha256=active_cover_sha256(cover_path, "front" if kind == "front_cover_artwork" else "back"),
        ))
    chapters = book.get("chapters") if isinstance(book.get("chapters"), list) else []
    if any(chapter_declares_visual_asset(chapter) for chapter in chapters):
        rows.append(component(
            title=title, slug=slug, name="illustrations_photographs_maps_or_graphics", creator="NOT_RECORDED",
            source="chapter metadata", reference=repository_path(book_path), edition="NOT_RECORDED",
            publication_date="NOT_RECORDED", death_year="NOT_RECORDED", jurisdictions=jurisdictions,
            basis="NOT_RECORDED", license_name="NOT_RECORDED", attribution="NOT_RECORDED",
            conditions="NOT_RECORDED", provenance=evidence(book_path),
            uncertainties=core_uncertainties + ["Chapter metadata declares visual material; item-level provenance is absent."], status="HOLD",
            component_sha256="NOT_RECORDED",
        ))
    if detected_audio(book):
        audio = book.get("audiobook") if isinstance(book.get("audiobook"), dict) else {}
        audio_provenance = evidence(approval_path) + evidence(book_path)
        rows.extend((
            component(
                title=title, slug=slug, name="audio_narration_or_sound_recording", creator=book.get("audiobook_voice"),
                source=audio.get("provider") or book.get("audiobook_provider"), reference=audio.get("url") or book.get("audio_url"),
                edition=audio.get("model") or book.get("audiobook_model"), publication_date=audio.get("updated_at") or book.get("audiobook_assets_updated_at"),
                death_year="NOT_APPLICABLE", jurisdictions=jurisdictions, basis="NOT_RECORDED",
                license_name="NOT_RECORDED", attribution="NOT_RECORDED", conditions="NOT_RECORDED",
                provenance=audio_provenance,
                uncertainties=core_uncertainties + ["Voice authority, provider terms/version, master provenance, and permitted territories/uses require separate qualified review."],
                status="HOLD", component_sha256=approval.get("audio_sha256"),
            ),
            component(
                title=title, slug=slug, name="music_or_other_sound", creator="NOT_RECORDED",
                source="NOT_RECORDED", reference="NOT_RECORDED", edition="NOT_RECORDED",
                publication_date="NOT_RECORDED", death_year="NOT_APPLICABLE", jurisdictions=jurisdictions,
                basis="NOT_RECORDED", license_name="NOT_RECORDED", attribution="NOT_RECORDED", conditions="NOT_RECORDED",
                provenance=audio_provenance,
                uncertainties=core_uncertainties + ["Audio-related metadata exists, but no music-absence confirmation or music-rights evidence is recorded."], status="HOLD",
                component_sha256="NOT_RECORDED",
            ),
        ))
    rows.append(component(
        title=title, slug=slug, name="third_party_metadata_and_promotional_copy", creator="NOT_RECORDED",
        source="controlled publication book metadata", reference=repository_path(book_path), edition="NOT_RECORDED",
        publication_date=book.get("created_at"), death_year="NOT_APPLICABLE", jurisdictions=jurisdictions,
        basis="NOT_RECORDED", license_name="NOT_RECORDED", attribution="NOT_RECORDED", conditions="NOT_RECORDED",
        provenance=evidence(book_path),
        uncertainties=core_uncertainties + ["The provenance of descriptive, biographical, taxonomy, and promotional metadata must be reviewed before public use."], status="HOLD",
        component_sha256=digest(book_path),
    ))
    return {
        "slug": slug,
        "title": title,
        "jurisdictions_assessed": jurisdictions,
        "title_release_status": (
            "ACCEPTED_FOR_CONTROLLED_RELEASE"
            if accepted_for_publication
            else "RIGHTS_ACCEPTED_UNEXPOSED"
            if rights_accepted_unexposed
            else "HOLD"
        ),
        "rights_status": "ACCEPTED" if accepted_rights else "HOLD",
        "title_release_reason": (
            "Exact hash-bound Reader decision is accepted and the title remains on the controlled live allowlist; audio remains disabled."
            if accepted_for_publication
            else "India text Reader rights are hash-bound and accepted, but the title remains unexposed pending separate commercial activation gates."
            if rights_accepted_unexposed
            else "No current accepted hash-bound rights decision exists; the title remains held."
        ),
        "components": rows,
    }


def git_value(argument: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", argument], text=True).strip()


def build_package(args: argparse.Namespace) -> dict[str, Any]:
    registry = read_json(REGISTRY)
    pilot_dispositions = registry.get("pilot_dispositions") if isinstance(registry.get("pilot_dispositions"), dict) else {}
    countries = {
        slug: list((pilot_dispositions.get(f"controlled-{slug}") or {}).get("countries") or [])
        for slug in PILOT_SLUGS
    }
    publication_slugs = {directory.name for directory in PUBLICATIONS.iterdir() if directory.is_dir()}
    publication_slugs.update(HELD_TITLE_ARCHIVES)
    root_launch = read_json(ROOT_LAUNCH)
    backend_launch = read_json(BACKEND_LAUNCH)
    live_slugs = set(root_launch.get("live_approved_slugs") or [])
    titles = [title_inventory(slug, countries, registry, live_slugs) for slug in sorted(publication_slugs)]
    components = [component for title in titles for component in title["components"]]
    accepted_slugs = sorted(title["slug"] for title in titles if title["title_release_status"] == "ACCEPTED_FOR_CONTROLLED_RELEASE")
    rights_accepted_slugs = sorted(title["slug"] for title in titles if title["rights_status"] == "ACCEPTED")
    unexposed_rights_accepted_slugs = sorted(title["slug"] for title in titles if title["title_release_status"] == "RIGHTS_ACCEPTED_UNEXPOSED")
    accepted_records = registry.get("accepted_records") or {}
    release_state_consistent = (
        root_launch.get("public_reader_exposure_enabled") is True
        and root_launch.get("public_audio_exposure_enabled") is False
        and sorted(root_launch.get("live_approved_slugs") or []) == accepted_slugs
        and backend_launch == root_launch
        # The registry intentionally retains superseded accepted decisions as
        # immutable history. Current live titles are validated against their
        # active decision and exact component hashes in title_inventory(); do
        # not require historical registry count to equal current live count.
        and set(accepted_slugs) == live_slugs
        and set(unexposed_rights_accepted_slugs) == {
            slug
            for slug in rights_accepted_slugs
            if slug not in live_slugs
            and isinstance((registry.get("commercial_batch_dispositions") or {}).get(f"controlled-{slug}"), dict)
            and (registry.get("commercial_batch_dispositions") or {}).get(f"controlled-{slug}", {}).get("status") == "RIGHTS_ACCEPTED_UNEXPOSED"
            and root_launch.get("title_access_modes", {}).get(slug) == "COMMERCIAL_ENTITLEMENT"
        }
        and (pilot_dispositions.get("controlled-yugalanguriya") or {}).get("status") == "HOLD"
    )
    return {
        "schema_version": "earnalism.copyright-rights-review-package.v1",
        "generated_from": {
            "repository_head": args.candidate_sha,
            "repository_tree": args.candidate_tree,
            "production_surface_sha256": args.production_surface_sha,
            "generator_head": git_value("HEAD"),
            "generator_tree": git_value("HEAD^{tree}"),
        },
        "scope": {
            "inventory": "All repository-controlled controlled-publication records.",
            "qualified_review_priority": list(PILOT_SLUGS),
            "pilot_countries": {slug: countries[slug] for slug in PILOT_SLUGS},
            "excluded_from_this_phase": ["customer/accounting acceptance", "rights acceptance", "publication activation", "production mutation"],
        },
        "jurisdiction_review_material": {
            "india_official_materials": list(OFFICIAL_INDIA_MATERIALS),
            "non_india_requirement": "A qualified reviewer must determine the applicable law, use scope, and territory for every intended public act; no public-domain conclusion is inferred from another jurisdiction.",
        },
        "technical_fail_closed_evidence": {
            "root_controlled_launch": {"path": repository_path(ROOT_LAUNCH), "sha256": digest(ROOT_LAUNCH)},
            "backend_controlled_launch": {"path": repository_path(BACKEND_LAUNCH), "sha256": digest(BACKEND_LAUNCH)},
            "rights_registry": {"path": repository_path(REGISTRY), "sha256": digest(REGISTRY)},
            "accepted_rights_record_count": len(registry.get("accepted_records") or {}),
            "pilot_dispositions": {slug: (pilot_dispositions.get(f"controlled-{slug}") or {}).get("status", "MISSING") for slug in PILOT_SLUGS},
            "public_reader_exposure_enabled": root_launch.get("public_reader_exposure_enabled"),
            "public_audio_exposure_enabled": root_launch.get("public_audio_exposure_enabled"),
            "live_approved_slugs": root_launch.get("live_approved_slugs"),
            "root_backend_launch_parity": backend_launch == root_launch,
            "result": "PASS" if release_state_consistent else "FAIL",
        },
        "inventory_summary": {
            "title_count": len(titles),
            "component_count": len(components),
            "component_status_counts": {status: sum(row["review_status"] == status for row in components) for status in ("HOLD", "EVIDENCE_READY_FOR_REVIEW")},
            "titles_with_hold": sum(title["title_release_status"] == "HOLD" for title in titles),
            "accepted_rights_record_count": len(registry.get("accepted_records") or {}),
            "live_accepted_rights_record_count": len(accepted_slugs),
            "rights_accepted_unexposed_count": len(unexposed_rights_accepted_slugs),
        },
        "titles": titles,
        "qualified_reviewer_checklist": [
            "Is the underlying text authorised for each intended act and territory?",
            "Is the exact delivered transcription, edition, translation, or adaptation authorised?",
            "Are cover and other artistic assets independently authorised?",
            "Are any licence conditions, notices, and attribution obligations satisfied?",
            "Is commercial digital distribution within the documented scope?",
            "Does each proposed decision contain the exact component hashes, operator identity, uses, territories, validity, evidence, and reviewer attribution required by backend/rights_decision_gate.py?",
            "Do unresolved facts require the title to remain HOLD?",
        ],
        "conclusion": "INDIA_RELEASE_EVIDENCE_COMPLETE_FOR_CONTROLLED_ALLOWLIST" if release_state_consistent else "COPYRIGHT_EVIDENCE_INCOMPLETE",
        "conclusion_reason": (
            "The current exact registry and allowlist agree on the accepted India Reader titles; Yugalanguriya and every unlisted title remain HOLD."
            if release_state_consistent
            else "The current registry, immutable decision artifacts, and controlled launch allowlist do not form a consistent accepted release state."
        ),
    }


def markdown(package: dict[str, Any]) -> str:
    summary = package["inventory_summary"]
    technical = package["technical_fail_closed_evidence"]
    lines = [
        "# Copyright / Rights qualified-review packet",
        "",
        "> This is an evidence package, not legal advice, a rights decision, a publication approval, or a release instruction.",
        "",
        "## Binding and scope",
        "",
        f"- Assessed technical candidate: `{package['generated_from']['repository_head']}` (tree `{package['generated_from']['repository_tree']}`).",
        f"- Production-surface fingerprint: `{package['generated_from']['production_surface_sha256']}`.",
        f"- Generator revision: `{package['generated_from']['generator_head']}` (tree `{package['generated_from']['generator_tree']}`).",
        f"- Full repository-controlled inventory: {summary['title_count']} titles and {summary['component_count']} component rows in `copyright-rights-inventory.json`.",
        "- The three current controlled-release titles are reported from their immutable accepted records; Yugalanguriya and all other controlled titles remain held.",
        "- Customer/accounting acceptance, rights acceptance, publication activation, deployment, and production mutation are outside this packet.",
        "",
        "## Technical fail-closed evidence",
        "",
        "| Gate | Evidence | Result |",
        "| --- | --- | --- |",
        f"| Reader exposure | `{technical['root_controlled_launch']['path']}` | `{technical['public_reader_exposure_enabled']}` |",
        f"| Audio exposure | `{technical['root_controlled_launch']['path']}` | `{technical['public_audio_exposure_enabled']}` |",
        f"| Live title allowlist | `{technical['root_controlled_launch']['path']}` | `{technical['live_approved_slugs']}` |",
        f"| Accepted rights records | `{technical['rights_registry']['path']}` | `{technical['accepted_rights_record_count']}` |",
        f"| Root/backend parity | controlled-launch SHA-256 bindings | `{technical['root_backend_launch_parity']}` |",
        f"| Controlled-release consistency | registry and allowlist bindings | `{technical['result']}` |",
        "",
        "## Pilot title disposition package",
        "",
        "| Title | Text | Covers | Other assets | Jurisdictions | Release status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for title in package["titles"]:
        if title["slug"] not in PILOT_SLUGS:
            continue
        rows = title["components"]
        text_state = next(row["review_status"] for row in rows if row["asset_component"] == "underlying_literary_text")
        cover_state = "HOLD" if any("cover" in row["asset_component"] for row in rows) else "NOT_RECORDED"
        other_state = "HOLD" if any(row["asset_component"] not in {"underlying_literary_text", "exact_digital_text_or_transcription", "front_cover_artwork", "back_cover_artwork"} for row in rows) else "NOT_RECORDED"
        countries = ", ".join(title["jurisdictions_assessed"]) or "NOT_RECORDED"
        lines.append(f"| {title['title']} (`{title['slug']}`) | {text_state} | {cover_state} | {other_state} | {countries} | `{title['title_release_status']}` |")
    lines.extend([
        "",
        "## Jurisdiction material for qualified review",
        "",
        "The following India materials are official legal inputs, not automated legal conclusions:",
        "",
    ])
    for material in package["jurisdiction_review_material"]["india_official_materials"]:
        lines.append(f"- [{material['topic']}]({material['url']})")
    lines.extend([
        "",
        "The current public release is assessed for India. This evidence package does not represent a global legal-clearance conclusion.",
        "",
        "## Required reviewer decisions",
        "",
    ])
    lines.extend(f"- {item}" for item in package["qualified_reviewer_checklist"])
    lines.extend([
        "",
        "## Current conclusion",
        "",
        f"`{package['conclusion']}` — {package['conclusion_reason']}",
        "",
        "This packet reports existing immutable decisions but does not create or alter them. Every title without a current accepted hash-bound decision remains HOLD.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only copyright/rights review package from controlled-publication evidence.")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--candidate-tree", required=True)
    parser.add_argument("--production-surface-sha", required=True)
    args = parser.parse_args()
    for name in ("candidate_sha", "candidate_tree", "production_surface_sha"):
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", getattr(args, name)):
            raise SystemExit(f"{name} must be a lowercase Git SHA or SHA-256")
    package = build_package(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "copyright-rights-inventory.json").write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "qualified-review-packet.md").write_text(markdown(package), encoding="utf-8")
    print(json.dumps({"result": "PASS", "output_dir": str(args.output_dir), "title_count": package["inventory_summary"]["title_count"], "component_count": package["inventory_summary"]["component_count"], "conclusion": package["conclusion"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
