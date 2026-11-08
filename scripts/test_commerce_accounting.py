from copy import deepcopy
import unittest
import json
from pathlib import Path
import shutil
import tempfile

from scripts.commerce_accounting import prepare_books, SCHEMA
from scripts.compliance_readiness import country_holds, inventory, ROOT, FACTS


def event(kind, at, **extra):
    return {"id": kind, "kind": kind, "reference": kind, "payment_id": "p1", "currency": "INR",
            "at": f"2026-11-08T00:00:{at:02d}Z", "evidence_sha256": "a" * 64, **extra}


def capture(gross=1180, tax=180, seconds=100):
    return event("capture", 0, gross_minor=gross, tax_minor=tax, granted_seconds=seconds,
                 tax_snapshot={"country": "IN", "classification": "fixture-not-real-tax-advice",
                               "rule_version": "fixture-v1", "tax_point": "capture",
                               "registration_basis": "fixture", "customer_location_evidence_ref": "fixture"})


def books(*events):
    return prepare_books({"schema": SCHEMA, "scope": "complete_payment_histories", "events": list(events)})


class AccountingTests(unittest.TestCase):
    def test_capture_usage_refund_settlement_reconcile_without_mutation(self):
        rows = [capture(), event("usage", 1, delivered_seconds=25),
                event("refund", 2, returned_seconds=75, gross_minor=885, tax_minor=135),
                event("settlement", 3, gross_minor=295, bank_minor=285, fee_minor=10, bank_evidence_ref="bank")]
        original = deepcopy(rows)
        result = books(*rows)
        self.assertEqual(rows, original)
        self.assertFalse(result["exceptions"])
        self.assertEqual(result["payments"]["p1"]["revenue"], 250)
        self.assertEqual(result["status"], "DRAFT_NOT_FINANCIAL_ACCEPTANCE")
        self.assertTrue(all(sum(x["debit_minus_credit_minor"] for x in row["entries"]) == 0
                            for row in result["journals"]))
        self.assertTrue(all(d["status"] == "DRAFT_NOT_ISSUED" for d in result["draft_documents"]))

    def test_identical_replay_is_idempotent(self):
        self.assertEqual(books(capture(), capture())["unique_events"], 1)

    def test_conflicting_replay_fails(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            books(capture(), capture(gross=2000))

    def test_second_economic_reference_fails(self):
        another = capture()
        another["id"] = "other-delivery-id"
        with self.assertRaisesRegex(ValueError, "economic reference"):
            books(capture(), another)

    def test_out_of_order_input_is_sorted_by_event_time(self):
        self.assertEqual(books(event("usage", 1, delivered_seconds=10), capture())["payments"]["p1"]["used"], 10)

    def test_usage_before_capture_is_not_hidden(self):
        c = capture()
        c["at"] = "2026-11-08T00:01:00Z"
        with self.assertRaises(ValueError):
            books(c, event("usage", 1, delivered_seconds=1))

    def test_rounding_is_cumulative_across_usage_and_refund(self):
        result = books(capture(gross=3, tax=0, seconds=2), event("usage", 1, delivered_seconds=1),
                       event("refund", 2, returned_seconds=1, gross_minor=1, tax_minor=0))
        self.assertEqual(result["payments"]["p1"]["revenue"], 2)
        self.assertEqual(result["payments"]["p1"]["refunded_net"], 1)
        with self.assertRaises(ValueError):
            books(capture(gross=1, tax=0, seconds=2), event("usage", 1, delivered_seconds=1),
                  event("refund", 2, returned_seconds=1, gross_minor=1, tax_minor=0))

    def test_multiple_small_usage_recognises_exact_pack_total(self):
        usages = []
        for n in range(1, 8):
            u = event("usage", n, delivered_seconds=1)
            u["id"] = u["reference"] = str(n)
            usages.append(u)
        self.assertEqual(books(capture(gross=3, tax=0, seconds=7), *usages)["payments"]["p1"]["revenue"], 3)

    def test_pending_settlement_is_an_exception(self):
        self.assertEqual(books(capture())["exceptions"][0]["unreconciled_minor"], 1180)

    def test_different_payment_exceptions_cannot_net_to_false_reconciliation(self):
        c1 = capture(gross=100, tax=0, seconds=100)
        settlement = event("settlement", 1, gross_minor=100, fee_minor=0, bank_minor=100, bank_evidence_ref="b")
        refund = event("refund", 2, returned_seconds=100, gross_minor=100, tax_minor=0)
        c2 = capture(gross=100, tax=0, seconds=100)
        c2.update(id="capture2", reference="capture2", payment_id="p2")
        result = books(c1, c2, settlement, refund)
        self.assertEqual([x["unreconciled_minor"] for x in result["exceptions"]], [-100, 100])

    def test_unknown_adjustment_field_is_not_silently_discarded(self):
        c = capture()
        c["chargeback_minor"] = 100
        with self.assertRaisesRegex(ValueError, "fields"):
            books(c)

    def test_invalid_or_unsupported_events_fail(self):
        cases = [event("usage", 1, delivered_seconds=101), event("usage", 1, delivered_seconds=True),
                 event("usage", 1, delivered_seconds=0), event("chargeback", 1),
                 event("refund", 1, returned_seconds=1, gross_minor=1180, tax_minor=180),
                 event("settlement", 1, gross_minor=1180, fee_minor=10, bank_minor=1180, bank_evidence_ref="b")]
        for row in cases:
            with self.subTest(row=row), self.assertRaises(ValueError):
                books(capture(), row)

    def test_tax_missing_unsupported_or_cross_currency_fails(self):
        for field, value in (("tax_snapshot", None), ("currency", "EUR"), ("gross_minor", 1.0),
                             ("tax_minor", -1), ("evidence_sha256", "fake"), ("at", "2026-11-08")):
            c = capture()
            c[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                books(c)
        c = capture()
        c["tax_snapshot"]["tax_point"] = "redemption"
        with self.assertRaises(ValueError):
            books(c)
        with self.assertRaises(ValueError):
            books(capture(), event("usage", 1, delivered_seconds=1, currency="USD"))

    def test_us_requires_customer_state(self):
        c = capture()
        c["tax_snapshot"]["country"] = "US"
        with self.assertRaisesRegex(ValueError, "state"):
            books(c)

    def test_country_holds_are_independent_and_need_references(self):
        facts = {"evidence": {}}
        for key in country_holds(facts, "IN"):
            facts["evidence"][key] = {"status": "VERIFIED", "reference": "test-only"}
        self.assertFalse(country_holds(facts, "IN"))
        self.assertIn("uk_vat_registration", country_holds(facts, "GB"))
        self.assertIn("us_nexus_and_taxability", country_holds(facts, "US"))
        facts["evidence"]["tax_point"]["reference"] = ""
        self.assertIn("tax_point", country_holds(facts, "IN"))


class InventoryTests(unittest.TestCase):
    def test_current_reader_checks_actual_components_and_manuscript(self):
        slug = "a-ghost-story"
        relative = Path("backend/data/controlled_publications") / slug
        baseline_path = Path("internal/legal/catalogue_clearance_20261002/reviewed_release_authority_20261003.v1.json")
        baseline = json.loads((ROOT / baseline_path).read_text())
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            shutil.copytree(ROOT / relative, target / relative)
            members = ["backend/data/rights_decision_registry.json", "backend/data/controlled_launch.json",
                       str(baseline_path), FACTS]
            members.extend(baseline["titles"][slug]["component_paths"].values())
            for member in set(members):
                dest = target / member
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / member, dest)
            before = inventory(target)
            row = before["titles"][0]
            self.assertTrue(row["countries"]["IN"]["reader"]["accepted_scope_matches"])
            self.assertFalse(row["countries"]["GB"]["reader"]["accepted_scope_matches"])
            self.assertFalse(row["countries"]["IN"]["audio"]["accepted_scope_matches"])
            chapter = next((target / relative / "chapters").glob("*.json"))
            chapter.write_text(chapter.read_text() + " ")
            after = inventory(target)
            self.assertIn("CURRENT_COMPONENT_OR_CHECKSUM_BINDING_UNVERIFIED",
                          after["titles"][0]["countries"]["IN"]["reader"]["reasons"])
            self.assertFalse(after["release_authorized"])
            self.assertFalse(after["runtime_observed"])

    def test_inventory_cannot_omit_a_held_controlled_package(self):
        result = inventory()
        packages = {p.name for p in (ROOT / "backend/data/controlled_publications").iterdir() if p.is_dir()}
        self.assertEqual({row["slug"] for row in result["titles"]}, packages)
        self.assertFalse(result["reopening_authorized"])


if __name__ == "__main__":
    unittest.main()
