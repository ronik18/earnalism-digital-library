"""Offline draft books from a complete, explicitly normalised evidence extract.

No network/database/provider access; no invoices are issued and no balances are
changed. An input assertion is not independent payment or tax qualification.
Use the existing qualified exporter to supply evidence; never capture anew here.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re


SCHEMA = "earnalism.accounting-extract.v1"
CURRENCIES = {"INR", "USD", "GBP"}


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name}: integer >= {minimum} required")
    return value


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty string required")
    return value


def instant(value):
    parsed = datetime.fromisoformat(text(value, "timestamp").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _round(value):
    # Nonnegative rational amounts; round once on cumulative recognition.
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def prepare_books(extract):
    """Build balanced draft journals, draft receipt/credit-note data and exceptions.

    Input must cover each payment's entire event history, not just this month's
    movements. Duplicate identical events collapse; conflicting identities fail.
    Imported tax amounts/classifications are checked, never guessed from a country.
    """
    if not isinstance(extract, dict) or set(extract) != {"schema", "scope", "events"}:
        raise ValueError("extract shape invalid")
    if extract["schema"] != SCHEMA or extract["scope"] != "complete_payment_histories":
        raise ValueError("complete payment histories required")
    if not isinstance(extract["events"], list):
        raise ValueError("events must be an array")
    seen, provider_keys, events = {}, {}, []
    for original in extract["events"]:
        event = deepcopy(original)
        if not isinstance(event, dict):
            raise ValueError("event object required")
        identifier = text(event.get("id"), "event id")
        identity = digest(event)
        if identifier in seen:
            if seen[identifier] != identity:
                raise ValueError("conflicting event id")
            continue
        seen[identifier] = identity
        if not re.fullmatch(r"[a-f0-9]{64}", text(event.get("evidence_sha256"), "evidence hash")):
            raise ValueError("invalid evidence hash")
        instant(event.get("at"))
        text(event.get("payment_id"), "payment id")
        kind = event.get("kind")
        if kind not in {"capture", "usage", "refund", "settlement"}:
            raise ValueError("unsupported event kind; reconcile manually")
        common = {"id", "kind", "reference", "payment_id", "currency", "at", "evidence_sha256"}
        fields = {"capture": {"gross_minor", "tax_minor", "granted_seconds", "tax_snapshot"},
                  "usage": {"delivered_seconds"},
                  "refund": {"returned_seconds", "gross_minor", "tax_minor"},
                  "settlement": {"gross_minor", "fee_minor", "bank_minor", "bank_evidence_ref"}}
        if set(event) != common | fields[kind]:
            raise ValueError("event fields invalid; do not silently drop adjustments")
        # Different event IDs must not recognise the same economic event twice.
        reference = text(event.get("reference"), "economic reference")
        key = (kind, reference)
        if key in provider_keys:
            raise ValueError("duplicate economic reference")
        provider_keys[key] = identifier
        events.append(event)
    priority = {"capture": 0, "usage": 1, "refund": 2, "settlement": 3}
    events.sort(key=lambda e: (instant(e["at"]), priority[e["kind"]], e["id"]))
    payments, journals, documents = {}, [], []
    totals = defaultdict(int)

    def post(event, currency, entries):
        if sum(amount for _, amount in entries) != 0:
            raise ValueError("unbalanced journal")
        journals.append({"event_id": event["id"], "evidence_sha256": event["evidence_sha256"],
                         "at": event["at"], "currency": currency,
                         "entries": [{"account": account, "debit_minus_credit_minor": amount}
                                     for account, amount in entries if amount]})
        for account, amount in entries:
            totals[(currency, account)] += amount

    for event in events:
        payment_id, kind = event["payment_id"], event["kind"]
        if kind == "capture":
            if payment_id in payments:
                raise ValueError("duplicate capture")
            currency = event.get("currency")
            if currency not in CURRENCIES:
                raise ValueError("unsupported currency")
            gross = integer(event.get("gross_minor"), "gross", 1)
            tax = integer(event.get("tax_minor"), "tax")
            seconds = integer(event.get("granted_seconds"), "seconds", 1)
            if tax >= gross:
                raise ValueError("invalid tax split")
            snapshot = event.get("tax_snapshot")
            if not isinstance(snapshot, dict):
                raise ValueError("tax snapshot required even for no collection")
            for field in ("classification", "rule_version", "tax_point", "registration_basis",
                          "customer_location_evidence_ref"):
                text(snapshot.get(field), field)
            if snapshot.get("country") not in {"IN", "US", "GB"}:
                raise ValueError("unsupported country")
            if snapshot["country"] == "US":
                text(snapshot.get("state"), "US state")
            # This draft path supports tax accounted on collection only. Voucher
            # redemption tax and mixed allocations require their own reviewed path.
            if snapshot["tax_point"] != "capture":
                raise ValueError("unsupported tax point; do not infer voucher treatment")
            payments[payment_id] = dict(currency=currency, gross=gross, tax=tax, seconds=seconds,
                                       used=0, refunded_seconds=0, revenue=0, refunded_net=0,
                                       refunded_tax=0, settled=0)
            post(event, currency, [("provider_clearing", gross),
                                   ("customer_advances", -(gross - tax)), ("output_tax", -tax)])
            documents.append({"status": "DRAFT_NOT_ISSUED", "type": "receipt",
                              "payment_id": payment_id, "event_id": event["id"], "currency": currency,
                              "gross_minor": gross, "tax_minor": tax, "tax_snapshot": deepcopy(snapshot)})
            continue
        if payment_id not in payments:
            raise ValueError("event precedes or lacks its capture")
        p = payments[payment_id]
        if event.get("currency") != p["currency"]:
            raise ValueError("cross-currency event; explicit FX reconciliation required")
        net = p["gross"] - p["tax"]
        if kind == "usage":
            used = integer(event.get("delivered_seconds"), "delivered seconds", 1)
            if p["used"] + p["refunded_seconds"] + used > p["seconds"]:
                raise ValueError("over-consumption")
            p["used"] += used
            recognised = (_round(Fraction(net * (p["used"] + p["refunded_seconds"]), p["seconds"]))
                          - p["refunded_net"])
            delta = recognised - p["revenue"]
            if recognised + p["refunded_net"] > net:
                raise ValueError("recognition exceeds remaining consideration")
            p["revenue"] = recognised
            post(event, p["currency"], [("customer_advances", delta), ("access_revenue", -delta)])
        elif kind == "refund":
            seconds = integer(event.get("returned_seconds"), "returned seconds", 1)
            tax = integer(event.get("tax_minor"), "refund tax")
            gross = integer(event.get("gross_minor"), "refund gross", 1)
            if tax > gross or p["used"] + p["refunded_seconds"] + seconds > p["seconds"]:
                raise ValueError("invalid unused-time refund")
            p["refunded_seconds"] += seconds
            target_net = (_round(Fraction(net * (p["used"] + p["refunded_seconds"]), p["seconds"]))
                          - p["revenue"])
            target_tax = _round(Fraction(p["tax"] * p["refunded_seconds"], p["seconds"]))
            # Provider-confirmed amounts must reconcile to the documented allocation.
            if gross - tax != target_net - p["refunded_net"] or tax != target_tax - p["refunded_tax"]:
                raise ValueError("refund allocation mismatch; manual adjustment required")
            if target_net + p["revenue"] > net:
                raise ValueError("refund exceeds customer advance")
            p["refunded_net"], p["refunded_tax"] = target_net, target_tax
            post(event, p["currency"], [("customer_advances", gross - tax),
                                       ("output_tax", tax), ("provider_clearing", -gross)])
            documents.append({"status": "DRAFT_NOT_ISSUED", "type": "credit_note",
                              "payment_id": payment_id, "event_id": event["id"],
                              "currency": p["currency"], "gross_minor": gross, "tax_minor": tax})
        else:
            gross = integer(event.get("gross_minor"), "settlement gross", 1)
            fees = integer(event.get("fee_minor"), "fee")
            bank = integer(event.get("bank_minor"), "bank")
            if fees + bank != gross or p["settled"] + gross > p["gross"]:
                raise ValueError("settlement mismatch")
            text(event.get("bank_evidence_ref"), "bank evidence reference")
            p["settled"] += gross
            post(event, p["currency"], [("bank", bank), ("provider_fees_gross", fees),
                                       ("provider_clearing", -gross)])
    exceptions = []
    for payment_id, payment in sorted(payments.items()):
        amount = (payment["gross"] - payment["refunded_net"] - payment["refunded_tax"]
                  - payment["settled"])
        if amount:
            exceptions.append({"payment_id": payment_id, "currency": payment["currency"],
                               "account": "provider_clearing", "unreconciled_minor": amount})
    return {"status": "DRAFT_NOT_FINANCIAL_ACCEPTANCE", "input_sha256": digest(extract),
            "unique_events": len(events), "journals": journals, "draft_documents": documents,
            "balances": [{"currency": c, "account": a, "debit_minus_credit_minor": v}
                         for (c, a), v in sorted(totals.items())],
            "exceptions": exceptions, "payments": payments,
            "limitations": ["No source authenticity or complete-history attestation established by this tool",
                            "No actual invoice issuance, statutory filing or financial acceptance",
                            "No cross-currency settlement, voucher-redemption tax, chargeback or consumed-time refund posting",
                            "Unsupported events fail; resolve through reviewed adjusting entries, never delete history"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extract", type=Path, help="Private existing-evidence extract; never a live URL")
    args = parser.parse_args()
    result = prepare_books(json.loads(args.extract.read_text()))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 2 if result["exceptions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
