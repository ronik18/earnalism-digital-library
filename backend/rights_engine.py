from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse


RIGHTS_METADATA_FIELDS = [
    "work_title",
    "work_slug",
    "author_name",
    "author_death_year",
    "original_publication_year",
    "country_of_origin",
    "source_url",
    "source_name",
    "source_license",
    "translator_name",
    "translator_death_year",
    "illustrator_name",
    "illustrator_death_year",
    "editor_name",
    "edition_publication_year",
    "rights_tier",
    "verification_status",
    "blocked_reason",
    "publication_region",
    "verified_at",
]

RIGHTS_REPORT_FILENAMES = {
    "quarantine": "rights_quarantine_report.csv",
    "approved": "rights_approved_report.csv",
    "blocked": "rights_blocked_report.csv",
}

APPROVED_STATUSES = {"approved", "verified"}
TIER_A = "A"
TIER_B = "B"
TIER_C = "C"
REGION_INDIA = {"india", "in", "india-only", "india_only"}
GLOBAL_REGIONS = {"global", "world", "worldwide", "all"}

PUBLIC_DOMAIN_LICENSE_RE = re.compile(
    r"\b(public\s*domain|cc0|project\s+gutenberg|gutenberg|wikisource|pd[-\s]?old|pd[-\s]?india)\b",
    re.IGNORECASE,
)
UNSAFE_LICENSE_RE = re.compile(
    r"\b(all\s+rights\s+reserved|non[-\s]?commercial|cc[-\s]?by[-\s]?nc|orphan|unknown|unclear|restricted)\b",
    re.IGNORECASE,
)


@dataclass
class RightsDecision:
    status: str
    rights_tier: str
    publication_region: str
    issues: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def approved(self) -> bool:
        return self.status == "approved" and not self.issues


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _year(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        year = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if year < 0 or year > 9999:
        return None
    return year


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _is_public_domain_india(death_year: int | None, *, current_year: int) -> bool:
    if death_year is None:
        return False
    # India generally protects literary/artistic works for life + 60 years.
    return death_year + 60 < current_year


def _source_host(source_url: str) -> str:
    return urlparse(source_url or "").netloc.lower()


def _source_has_strong_confidence(metadata: dict[str, Any]) -> bool:
    source_url = _text(metadata.get("source_url"))
    source_name = _lower(metadata.get("source_name"))
    source_license = _text(metadata.get("source_license"))
    host = _source_host(source_url)
    if not source_url or not source_license:
        return False
    if not PUBLIC_DOMAIN_LICENSE_RE.search(f"{source_name} {source_license} {host}"):
        return False
    return any(token in host for token in ("gutenberg.org", "wikisource.org")) or bool(PUBLIC_DOMAIN_LICENSE_RE.search(source_license))


def rights_metadata_for_book(book: dict[str, Any]) -> dict[str, Any]:
    raw = book.get("rights_metadata") if isinstance(book.get("rights_metadata"), dict) else {}
    metadata = {field: raw.get(field, "") for field in RIGHTS_METADATA_FIELDS}
    metadata["work_title"] = _text(metadata.get("work_title") or book.get("title"))
    metadata["work_slug"] = _text(metadata.get("work_slug") or book.get("slug"))
    metadata["author_name"] = _text(metadata.get("author_name") or book.get("author"))
    metadata["publication_region"] = _text(metadata.get("publication_region") or "global").lower()
    metadata["rights_tier"] = _text(metadata.get("rights_tier")).upper().replace("TIER ", "")
    metadata["verification_status"] = _lower(metadata.get("verification_status"))
    return metadata


def evaluate_rights(book: dict[str, Any], *, current_year: int | None = None) -> RightsDecision:
    current_year = current_year or _current_year()
    metadata = rights_metadata_for_book(book)
    issues: list[str] = []
    quarantine_only = False

    for field_name in ("work_title", "work_slug", "author_name", "source_url", "source_name", "source_license"):
        if not _text(metadata.get(field_name)):
            issues.append(f"{field_name} is required.")
            quarantine_only = True

    author_death_year = _year(metadata.get("author_death_year"))
    original_publication_year = _year(metadata.get("original_publication_year"))
    if author_death_year is None:
        issues.append("author_death_year is required.")
        quarantine_only = True
    elif not _is_public_domain_india(author_death_year, current_year=current_year):
        issues.append("author is not deterministically public domain in India.")

    if original_publication_year is None:
        issues.append("original_publication_year is required.")
        quarantine_only = True

    source_license = _text(metadata.get("source_license"))
    if source_license and UNSAFE_LICENSE_RE.search(source_license):
        issues.append("source_license is restricted, unclear, or unsafe.")

    translator_name = _text(metadata.get("translator_name"))
    translator_death_year = _year(metadata.get("translator_death_year"))
    if translator_name:
        if translator_death_year is None:
            issues.append("modern or unknown translation rights block publishing until separately verified.")
        elif not _is_public_domain_india(translator_death_year, current_year=current_year):
            issues.append("translator rights are not deterministically public domain in India.")

    illustrator_name = _text(metadata.get("illustrator_name"))
    illustrator_death_year = _year(metadata.get("illustrator_death_year"))
    if illustrator_name:
        if illustrator_death_year is None:
            issues.append("modern or unknown illustration rights block publishing until separately verified.")
        elif not _is_public_domain_india(illustrator_death_year, current_year=current_year):
            issues.append("illustration rights are not deterministically public domain in India.")

    editor_name = _text(metadata.get("editor_name"))
    edition_publication_year = _year(metadata.get("edition_publication_year"))
    if editor_name:
        if edition_publication_year is None:
            issues.append("editorial or edition rights are unknown until edition_publication_year is verified.")
            quarantine_only = True
        elif original_publication_year is not None and edition_publication_year > original_publication_year:
            issues.append("modern or later edition/editorial rights block publishing until separately verified.")

    rights_tier = _text(metadata.get("rights_tier")).upper()
    if rights_tier not in {TIER_A, TIER_B, TIER_C}:
        issues.append("rights_tier must be A, B, or C.")
        quarantine_only = True
    elif rights_tier == TIER_C:
        issues.append("Tier C rights block all publishing.")

    verification_status = _lower(metadata.get("verification_status"))
    if verification_status not in APPROVED_STATUSES:
        issues.append("verification_status must be approved before publishing.")
        quarantine_only = True
    if verification_status in APPROVED_STATUSES and not _text(metadata.get("verified_at")):
        issues.append("verified_at is required for approved rights metadata.")
        quarantine_only = True

    publication_region = _lower(metadata.get("publication_region") or "global")
    if rights_tier == TIER_A and not _source_has_strong_confidence(metadata):
        issues.append("Tier A requires public-domain source confidence.")
    if rights_tier == TIER_B and publication_region in GLOBAL_REGIONS:
        issues.append("Tier B blocks global publishing; use India-only publication_region or upgrade rights evidence.")

    if _text(metadata.get("blocked_reason")):
        issues.append(f"blocked_reason: {_text(metadata.get('blocked_reason'))}")

    if not issues:
        return RightsDecision(status="approved", rights_tier=rights_tier, publication_region=publication_region, metadata=metadata)

    status = "quarantine" if quarantine_only else "blocked"
    return RightsDecision(status=status, rights_tier=rights_tier or TIER_C, publication_region=publication_region, issues=issues, metadata=metadata)


def rights_publish_blockers(book: dict[str, Any], *, current_year: int | None = None) -> list[str]:
    decision = evaluate_rights(book, current_year=current_year)
    return [] if decision.approved else decision.issues


def rights_report_rows(books: Iterable[dict[str, Any]], report_kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for book in books:
        decision = evaluate_rights(book)
        if decision.status != report_kind:
            continue
        metadata = decision.metadata
        rows.append({
            "book_slug": _text(book.get("slug")),
            "book_title": _text(book.get("title")),
            "decision_status": decision.status,
            "decision_issues": " | ".join(decision.issues),
            **{field: metadata.get(field, "") for field in RIGHTS_METADATA_FIELDS},
        })
    return rows


def rights_report_csv(rows: list[dict[str, Any]]) -> str:
    fieldnames = ["book_slug", "book_title", "decision_status", "decision_issues", *RIGHTS_METADATA_FIELDS]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()
