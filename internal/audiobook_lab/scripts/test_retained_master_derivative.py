"""CI-safe tests. Fixture byte strings are NOT audio or listening evidence.
Real parent qualification tests do not mock adoption, editorial, rights or proofs.
"""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import retained_master_derivative as adapter
import audiobook_active_release_v2 as manager

ROOT = Path(__file__).resolve().parents[3]


class RetainedMasterDerivativeTests(unittest.TestCase):

    def parent(self, slug="the-open-window"):
        book = json.loads(
            (
                ROOT
                / "backend/data/controlled_publications"
                / slug
                / "public_book.json"
            ).read_text()
        )
        return (book, book["audiobook_packages"][adapter.PINS[slug]["descriptor"]])

    def fixture(self):
        audio = b"NOT_AUDIO_SYNTHETIC_BINDING_FIXTURE"
        source = "First unit.\n\nSecond unit."
        pin = copy.deepcopy(adapter.PINS["the-open-window"])
        pin.update(
            master=adapter.sha(audio),
            manuscript=adapter.sha(source.encode()),
            duration=2000,
            units=2,
        )
        parent = dict(
            slug="the-open-window",
            package_version=pin["parent"],
            release_descriptor_sha256=pin["descriptor"],
            source_sha256=pin["source"],
            manuscript_sha256=pin["manuscript"],
        )
        timing = [
            dict(
                id="u1",
                start_ms=0,
                end_ms=1000,
                source_char_start=0,
                source_char_end=11,
            ),
            dict(
                id="u2",
                start_ms=1000,
                end_ms=2000,
                source_char_start=13,
                source_char_end=len(source),
            ),
        ]
        return (pin, parent, audio, source, timing)

    def test_binding_positive_and_negative(self):
        pin, parent, audio, source, timing = self.fixture()
        with patch.dict(adapter.PINS, {"the-open-window": pin}):
            adapter.bindings("the-open-window", parent, audio, source, timing)
            cases = [
                (parent, audio + b"x", source, timing),
                (parent, audio, source + "x", timing),
            ]
            bad = copy.deepcopy(parent)
            bad["package_version"] = "sha256-" + "a" * 64
            cases.append((bad, audio, source, timing))
            bad = copy.deepcopy(parent)
            bad["source_sha256"] = "a" * 64
            cases.append((bad, audio, source, timing))
            bad = copy.deepcopy(timing)
            bad[1]["start_ms"] = 999
            cases.append((parent, audio, source, bad))
            bad = copy.deepcopy(timing)
            bad[1]["source_char_start"] = 10
            cases.append((parent, audio, source, bad))
            bad = copy.deepcopy(timing)
            bad[1]["source_char_start"] = 14
            cases.append((parent, audio, source, bad))
            bad = copy.deepcopy(timing)
            bad[1]["source_char_end"] = len(source) + 1
            cases.append((parent, audio, source, bad))
            for args in cases:
                with self.subTest(args=args[1:2]), self.assertRaises(ValueError):
                    adapter.bindings("the-open-window", *args)
            with self.assertRaises(ValueError):
                adapter.bindings("the-selfish-giant", parent, audio, source, timing)
            with self.assertRaises(ValueError):
                adapter.bindings("unknown-title", parent, audio, source, timing)

    def test_real_parent_native_qualification_unmocked(self):
        for slug in adapter.PINS:
            book, parent = self.parent(slug)
            proof = adapter.qualify_parent(ROOT, slug, parent)
            self.assertTrue(proof["native_editorial_and_india_rights_validated"])
            self.assertTrue(proof["native_production_acceptance_validated"])
            self.assertIn("HISTORICAL", proof["native_production_acceptance_scope"])

    def test_archival_parent_rights_and_proof_pins_cannot_be_forged(self):
        book, parent = self.parent()
        for key in ["rights_record", "acceptance"]:
            pin = copy.deepcopy(adapter.PINS["the-open-window"])
            pin[key] = "a" * 64
            with self.subTest(key=key), patch.dict(
                adapter.PINS, {"the-open-window": pin}
            ), self.assertRaises(ValueError):
                adapter.qualify_parent(ROOT, "the-open-window", parent)
        parent = copy.deepcopy(parent)
        parent["duration_ms"] += 1
        with self.assertRaises(ValueError):
            adapter.qualify_parent(ROOT, "the-open-window", parent)

    def test_parent_revocation_is_rechecked_after_successor_promotion(self):
        import open_window_successor_acceptance as frozen

        book, parent = self.parent()
        accepted, revoked = frozen.load_production_registry()
        revoked = frozenset(
            set(revoked) | {adapter.PINS["the-open-window"]["rights_decision"]}
        )
        with patch.object(
            frozen, "load_production_registry", return_value=(accepted, revoked)
        ), self.assertRaisesRegex(manager.ReleasePointerError, "rights gate denied"):
            adapter.qualify_parent(ROOT, "the-open-window", parent)

    def test_wrong_shipped_adoption_pin_denied(self):
        book, parent = self.parent()
        pin = copy.deepcopy(adapter.PINS["the-open-window"])
        pin["adoption"] = "a" * 64
        with patch.dict(adapter.PINS, {"the-open-window": pin}), self.assertRaisesRegex(
            ValueError, "trusted parent adoption changed"
        ):
            adapter.qualify_parent(ROOT, "the-open-window", parent)

    def test_registry_override_and_unreviewed_adoption_denied(self):
        with self.assertRaisesRegex(ValueError, "override forbidden"):
            adapter.validate_reviewed_adoption({}, registry_path="untrusted.json")
        with self.assertRaises(ValueError):
            adapter.validate_reviewed_adoption({})

    def test_prepare_after_successor_promotion_preserves_archived_parent_and_cues(self):
        book, parent = self.parent()
        slug = "the-open-window"
        source = json.loads(
            (
                ROOT
                / "backend/data/controlled_publications"
                / slug
                / "chapters/chapter-001.json"
            ).read_text()
        )["content"]
        split = source.index("\n\n")
        timing = [
            dict(
                id="fixture-1",
                start_ms=0,
                end_ms=1000,
                source_char_start=0,
                source_char_end=split,
            ),
            dict(
                id="fixture-2",
                start_ms=1000,
                end_ms=491436,
                source_char_start=split + 2,
                source_char_end=len(source),
            ),
        ]
        sentinel = b"NOT_AUDIO_EXPLICIT_PREPARE_FIXTURE"
        pin = copy.deepcopy(adapter.PINS[slug])
        pin.update(master=adapter.sha(sentinel), units=2)
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if path.name == "retained-timing-locks.json":
                return json.dumps({slug: adapter.sha(adapter.canonical(timing))})
            if path.name == "public_book.json" and path.parent.name == slug:
                promoted = json.loads(original_read(path, *args, **kwargs))
                promoted["audiobook_public_package_approval"] = {
                    "status": "PUBLIC_APPROVED",
                    "release_descriptor_sha256": "d" * 64,
                    "acceptance_sha256": "e" * 64,
                    "audio_rights_record_sha256": "f" * 64,
                    "audio_rights_decision_id": "new-continuous-successor",
                }
                return json.dumps(promoted)
            return original_read(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            master = root / "not-media.fixture"
            master.write_bytes(sentinel)
            times = root / "timing.json"
            times.write_text(json.dumps(timing))
            with patch.dict(adapter.PINS, {slug: pin}), patch.object(
                Path, "read_text", read
            ):
                adapter.prepare(ROOT, slug, master, times, root / "output")
            sidecar = json.loads(
                (root / "output/chapter-001-full.timestamps.json").read_text()
            )
            self.assertEqual(len(sidecar["cues"]), 2)
            for cue, unit in zip(sidecar["cues"], timing):
                self.assertEqual(
                    cue["text"],
                    source[unit["source_char_start"] : unit["source_char_end"]],
                )
                self.assertEqual(
                    (cue["start_ms"], cue["end_ms"]), (unit["start_ms"], unit["end_ms"])
                )
            self.assertEqual(
                " ".join(" ".join((c["text"] for c in sidecar["cues"])).split()),
                " ".join(source.split()),
            )
            self.assertFalse(sidecar["highlight_sync_enabled"])
            self.assertEqual(
                (root / "output/chapter-001-full.vtt").read_text().count(" --> "), 2
            )
            self.assertEqual(master.read_bytes(), sentinel)
            self.assertFalse(
                json.loads((root / "output/validation-result.json").read_text())[
                    "production_finalize_allowed"
                ]
            )
            import audiobook_package_storage_v2 as storage
            from types import SimpleNamespace

            plan = storage.load_storage_plan(root / "output/upload-plan.json")
            self.assertEqual(plan.release_status, "SOURCE_ADOPTION_PENDING")
            with self.assertRaisesRegex(
                storage.StorageSafetyError, "SOURCE_ADOPTION_PENDING"
            ):
                storage.require_production_plan_status(
                    SimpleNamespace(release_eligible=True), plan
                )

    def structural_draft(self, slug):
        book, parent = self.parent(slug)
        pin = adapter.PINS[slug]
        n = adapter.native(ROOT)
        locks = json.loads(
            (Path(adapter.__file__).parent / "retained-timing-locks.json").read_text()
        )
        hashes = {"timestamps": "a" * 64, "metadata": "b" * 64, "vtt": "c" * 64}
        descriptor = {
            "schema_version": "audiobook_release_descriptor.v1",
            "slug": slug,
            "controlled_source_sha256": pin["source"],
            "manuscript_sha256": pin["manuscript"],
            "master_mp3_sha256": pin["master"],
            "policy": adapter.POLICY,
            "parent_package_version": pin["parent"],
            "parent_release_descriptor_sha256": pin["descriptor"],
            "release_candidate_evidence": {"acceptance_policy": adapter.POLICY},
            "parent_qualification": adapter.qualify_parent(ROOT, slug, parent),
            "retained_measured_bounds_sha256": locks[slug],
            "retained_unit_count": pin["units"],
            "delivery_sidecar_sha256": hashes,
        }
        digest = adapter.sha(adapter.canonical(descriptor))
        prefix = n.immutable_release_prefix(slug, digest)
        assets = {}
        for role, mime in [
            ("audio", "audio/mpeg"),
            ("timestamps", "application/json"),
            ("vtt", "text/vtt"),
            ("metadata", "application/json"),
        ]:
            key = prefix + "delivery/fixture-" + role
            assets[role] = {
                "sha256": pin["master"] if role == "audio" else hashes[role],
                "size_bytes": (
                    (6217581 if slug == "the-selfish-giant" else 7864365)
                    if role == "audio"
                    else 100
                ),
                "mime_type": mime,
                "storage": {
                    "store": "draft-primary",
                    "bucket": "draft-primary",
                    "key": key,
                    "version_id": "DRAFT-NOT-UPLOADED",
                },
                "replicas": [
                    {
                        "store": "draft-dr",
                        "bucket": "draft-dr",
                        "key": key,
                        "version_id": "DRAFT-NOT-UPLOADED",
                    }
                ],
            }
        chunk = {
            "segment_id": "chapter-001-full",
            "order": 0,
            "start_word": 0,
            "end_word": parent["word_count"] - 1,
            "start_paragraph": 0,
            "end_paragraph": parent["paragraph_count"] - 1,
            "cumulative_start_ms": 0,
            "duration_ms": pin["duration"],
            "assets": assets,
        }
        track = {k: v for k, v in parent["tracks"][0].items() if k != "chunks"}
        track["chunks"] = [chunk]
        package = {
            **parent,
            "release_descriptor_sha256": digest,
            "release_evidence_version": adapter.POLICY,
            "segment_count": 1,
            "tracks": [track],
        }
        return (descriptor, n.with_canonical_package_version(package))

    def test_actual_manager_after_promotion_reaches_derivative_adoption_gate(self):
        descriptor, package = self.structural_draft("the-open-window")
        original_read = Path.read_text

        def promoted(path, *args, **kwargs):
            raw = original_read(path, *args, **kwargs)
            if (
                path.name == "public_book.json"
                and path.parent.name == "the-open-window"
            ):
                book = json.loads(raw)
                book["audiobook_public_package_approval"] = {
                    "status": "PUBLIC_APPROVED",
                    "release_descriptor_sha256": "d" * 64,
                    "acceptance_sha256": "e" * 64,
                    "audio_rights_record_sha256": "f" * 64,
                    "audio_rights_decision_id": "new-successor",
                }
                return json.dumps(book)
            return raw

        with patch.object(Path, "read_text", promoted), self.assertRaisesRegex(
            manager.ReleasePointerError, "exact reviewed derivative adoption required"
        ):
            manager.validate_qa_candidate_release_descriptor(
                descriptor, package, controlled_language="en"
            )

    def test_selfish_exact_cap_does_not_admit_777121(self):
        descriptor, package = self.structural_draft("the-selfish-giant")
        n = adapter.native(ROOT)
        n.validate_audiobook_package(
            package,
            expected_slug=package["slug"],
            expected_source_sha256=package["source_sha256"],
            expected_manuscript_sha256=package["manuscript_sha256"],
            expected_release_descriptor_sha256=package["release_descriptor_sha256"],
        )
        package["duration_ms"] = 777121
        package["tracks"][0]["chunks"][0]["duration_ms"] = 777121
        package = n.with_canonical_package_version(package)
        with self.assertRaisesRegex(n.AudiobookPackageValidationError, "720000"):
            n.validate_audiobook_package(
                package,
                expected_slug=package["slug"],
                expected_source_sha256=package["source_sha256"],
                expected_manuscript_sha256=package["manuscript_sha256"],
                expected_release_descriptor_sha256=package["release_descriptor_sha256"],
            )

    def registered_packets(self):
        folder = (
            ROOT
            / "internal/earnalism_intelligence/live_audiobook_campaign_20261031/continuous-master-preparation-20261101"
        )
        for slug in ("the-open-window", "the-selfish-giant"):
            packet = folder / slug
            yield packet, json.loads(
                (packet / "release-descriptor.json").read_text()
            ), json.loads((packet / "STRUCTURAL-DRAFT-NOT-UPLOADED.json").read_text())

    def test_registered_source_qa_is_not_storage_or_publication(self):
        import audiobook_package_builder_v2 as builder

        for packet, descriptor, package in self.registered_packets():
            with self.subTest(slug=descriptor["slug"]):
                self.assertEqual(
                    manager.validate_qa_candidate_release_descriptor(
                        descriptor, package, controlled_language="en"
                    ),
                    descriptor,
                )
                self.assertFalse(descriptor["publication_approved"])
                self.assertFalse(
                    descriptor["release_candidate_evidence"]["all_release_gates_passed"]
                )
                for track in package["tracks"]:
                    for chunk in track["chunks"]:
                        for asset in chunk["assets"].values():
                            self.assertEqual(
                                asset["storage"]["version_id"], "DRAFT-NOT-UPLOADED"
                            )
                with self.assertRaisesRegex(
                    builder.PackageBuildError, "Primary receipt"
                ):
                    builder.finalize_package(
                        semantics=json.loads(
                            (packet / "package-semantics.json").read_text()
                        ),
                        upload_plan=json.loads(
                            (packet / "upload-plan.json").read_text()
                        ),
                        primary_receipt={},
                        replica_receipt={},
                    )

    def test_registered_rebinding_does_not_expand_use_or_territory(self):
        from datetime import datetime, timezone
        from rights_decision_gate import (
            evaluate_accepted_record,
            load_production_registry,
        )

        registry = json.loads(
            (
                ROOT
                / "internal/audiobook_lab/release_gate/retained_master_derivative_adoptions.json"
            ).read_text()
        )
        accepted, revoked = load_production_registry()
        for entry in registry["adoptions"]:
            record = entry["record"]["audio_use_decision"]
            kwargs = dict(
                edition_id=record["edition_id"],
                operator_id="reo-enterprise",
                country="IN",
                country_trusted=True,
                use="audio_stream",
                required_components=record["components"],
                accepted_records=accepted,
                revoked_decision_ids=revoked,
                now=datetime.now(timezone.utc),
            )
            with self.subTest(slug=record["edition_id"]):
                self.assertTrue(evaluate_accepted_record(record, **kwargs).passed)
                for change in (
                    {"country": "US"},
                    {"use": "audio_download"},
                    {"revoked_decision_ids": frozenset([record["decision_id"]])},
                    {
                        "required_components": {
                            **record["components"],
                            "master_mp3": "f" * 64,
                        }
                    },
                ):
                    self.assertFalse(
                        evaluate_accepted_record(record, **{**kwargs, **change}).passed
                    )


if __name__ == "__main__":
    unittest.main()
