"""Read-only IN/US/GB inventory using existing rights validators; never activates.

Run from the repository root: python3 -m scripts.compliance_readiness.
Reports are internal: component hashes and reasons must not enter public JSON.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from backend.rights_decision_gate import evaluate_accepted_record, load_production_registry
from scripts.catalogue_clearance_release_bindings import exact_record_component_hashes
from scripts.bengali_rights_package_validator import checksum_manifest_matches


ROOT = Path(__file__).resolve().parents[1]
FACTS = "internal/legal/in_us_uk_20261108/business_facts.json"
COUNTRIES = ("IN", "US", "GB")
READER_USES = ("catalog_metadata", "cover_display", "reader_preview", "reader_delivery",
               "reading_pass_session", "reading_pass_renewal")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def country_holds(facts, country):
    """No flags supplied here constitute authority to open commerce."""
    if country not in COUNTRIES:
        raise ValueError("unsupported country")
    fields = ["legal_form", "india_turnover_and_gst", "pass_tax_classification",
              "tax_point", "invoice_and_reconciliation", "current_financial_acceptance"]
    fields += {"IN": [], "US": ["us_nexus_and_taxability"],
               "GB": ["uk_vat_registration", "uk_cancellation", "uk_privacy_scope"]}[country]
    return [field for field in fields if not isinstance(facts.get("evidence", {}).get(field), dict)
            or facts["evidence"][field].get("status") != "VERIFIED"
            or not isinstance(facts["evidence"][field].get("reference"), str)
            or not facts["evidence"][field]["reference"].strip()]


def inventory(root=ROOT, now=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone required")
    registry = root / "backend/data/rights_decision_registry.json"
    accepted, revoked = load_production_registry(registry)
    launch = load(root / "backend/data/controlled_launch.json")
    facts = load(root / FACTS)
    baseline = load(root / "internal/legal/catalogue_clearance_20261002/reviewed_release_authority_20261003.v1.json")
    rows = []
    for package in sorted((root / "backend/data/controlled_publications").iterdir()):
        if not package.is_dir():
            continue
        slug = package.name
        try:
            record = load(package / "rights_decision.json")
            components = exact_record_component_hashes(root, slug, record, package, baseline)
            if not checksum_manifest_matches(package):
                raise ValueError("checksum bundle invalid")
            error = None
        except (OSError, ValueError, KeyError, TypeError, AssertionError):
            error = "CURRENT_COMPONENT_OR_CHECKSUM_BINDING_UNVERIFIED"
        countries = {}
        for country in COUNTRIES:
            formats = {}
            for name, uses in (("reader", READER_USES), ("audio", ("audio_stream",))):
                reasons = []
                if error:
                    reasons.append(error)
                else:
                    for use in uses:
                        verdict = evaluate_accepted_record(record, edition_id=slug, operator_id="reo-enterprise",
                            country=country, country_trusted=True, use=use, required_components=components,
                            accepted_records=accepted, revoked_decision_ids=revoked, now=now)
                        reasons.extend(verdict.reasons)
                formats[name] = {"accepted_scope_matches": not reasons, "reasons": sorted(set(reasons))}
            countries[country] = formats
        rows.append({"slug": slug, "configured_live_reader": slug in launch.get("live_approved_slugs", []),
                     "countries": countries})
    return {"schema": "earnalism.compliance-inventory.v1", "evaluated_at": now.isoformat(),
            "registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
            "business_facts_sha256": hashlib.sha256((root / FACTS).read_bytes()).hexdigest(),
            "release_authorized": False, "reopening_authorized": False, "runtime_observed": False,
            "notice": "Planning report only. Does not change runtime country guards or accept rights. "
                      "Audio requires its separate package binding and release gates; this report never grants it. "
                      "VERIFIED fields are references to inspect, not authenticated approval.",
            "commerce_holds": {country: country_holds(facts, country) for country in COUNTRIES},
            "titles": rows}


if __name__ == "__main__":
    print(json.dumps(inventory(), ensure_ascii=False, indent=2))
