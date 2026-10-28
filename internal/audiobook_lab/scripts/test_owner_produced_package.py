"""Synthetic local fixtures only. No adoption, upload, publication or inference."""

import copy, json, tempfile, wave, unittest, sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import owner_produced_package as owner
import audiobook_active_release_v2 as manager
from rights_decision_gate import record_sha256


class OwnerProducedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        def put(name, raw):
            p = self.root / name
            p.write_bytes(raw)
            return {"path": name, "sha256": owner.sha(raw)}

        self.put = put
        self.manuscript = put("source.txt", b"First unit.\n\nLast unit.")
        with wave.open(str(self.root / "master.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\0" * 96000)
        wav = put("master.wav", (self.root / "master.wav").read_bytes())
        mp3 = put("master.mp3", b"SYNTHETIC_NOT_MP3")
        identity = {
            "slug": "the-selfish-giant",
            "title": "The Selfish Giant",
            "author": "Oscar Wilde",
            "controlled_source_sha256": "1" * 64,
            "manuscript_sha256": self.manuscript["sha256"],
            "master_wav_sha256": wav["sha256"],
            "master_mp3_sha256": mp3["sha256"],
        }
        evidence = {
            k: put(k + ".json", owner.canonical({"fixtureOnly": True, "role": k}))
            for k in owner.EVIDENCE_ROLES
        }
        self.files = {}
        chunks = []
        for i in range(2):
            sid = f"unit-{i}"
            assets = {}
            for role, mime in owner.ROLES.items():
                ref = put(
                    sid + "-" + role + ".fixture",
                    ("SYNTHETIC_NOT_AUDIO:" + sid + role).encode(),
                )
                self.files[sid + "-" + role] = ref
                assets[role] = {
                    "sha256": ref["sha256"],
                    "size_bytes": len((self.root / ref["path"]).read_bytes()),
                    "mime_type": mime,
                }
            chunks.append(
                {
                    "segment_id": sid,
                    "order": i,
                    "start_word": i * 2,
                    "end_word": i * 2 + 1,
                    "start_paragraph": i,
                    "end_paragraph": i,
                    "cumulative_start_ms": i * 1000,
                    "duration_ms": 1000,
                    "assets": assets,
                }
            )
        self.package = {
            "slug": identity["slug"],
            "source_sha256": identity["controlled_source_sha256"],
            "manuscript_sha256": identity["manuscript_sha256"],
            "duration_ms": 2000,
            "segment_count": 2,
            "word_count": 4,
            "paragraph_count": 2,
            "sync_tier": "SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY",
            "highlight_sync_enabled": False,
            "tracks": [
                {
                    "id": "chapter-001",
                    "chapter_id": "chapter-001",
                    "title": "The Selfish Giant",
                    "order": 0,
                    "start_word": 0,
                    "end_word": 3,
                    "start_paragraph": 0,
                    "end_paragraph": 1,
                    "chunks": chunks,
                }
            ],
        }
        components = {
            "source_file": identity["controlled_source_sha256"],
            "selected_manuscript": identity["manuscript_sha256"],
            "master_wav": wav["sha256"],
            "master_mp3": mp3["sha256"],
            "audio_component_bindings": owner.mapping(self.package),
        }
        self.rights = {
            "schema_version": "earnalism.rights-decision.v1",
            "decision_id": "synthetic-owner-produced-fixture",
            "edition_id": "the-selfish-giant",
            "operator_id": "reo-enterprise",
            "status": "ACCEPTED",
            "components": components,
            "territories": ["IN"],
            "uses": ["audio_stream"],
            "valid_from": "2020-01-01T00:00:00+00:00",
            "valid_until": "2099-01-01T00:00:00+00:00",
            "basis": "SYNTHETIC_FIXTURE_NOT_AUTHORITY",
            "evidence_sha256": ["2" * 64],
            "accepted_by": "SYNTHETIC_FIXTURE",
            "conditions_satisfied": True,
        }
        self.units = [
            {
                "id": "unit-0",
                "text": "First unit.",
                "source_start": 0,
                "source_end": 11,
                "start_word": 0,
                "end_word": 1,
                "text_sha256": owner.sha(b"First unit."),
            },
            {
                "id": "unit-1",
                "text": "Last unit.",
                "source_start": 13,
                "source_end": 23,
                "start_word": 2,
                "end_word": 3,
                "text_sha256": owner.sha(b"Last unit."),
            },
        ]
        self.adoption = {
            "status": "ADOPTED",
            "policy": owner.POLICY,
            "identity": identity,
            "authority_reference": "SYNTHETIC_FIXTURE",
            "adopted_by": "SYNTHETIC_FIXTURE",
            "authority_evidence_sha256": "3" * 64,
            "unresolved_material_defects": [],
            "unresolved_wording_findings": [],
            "evidence_sha256": {k: v["sha256"] for k, v in evidence.items()},
            "generation": {
                "provider": "owner_colab_qwen",
                "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
                "model_revision": "0c0e3051f131929182e2c023b9537f8b1c68adfe",
                "voice": "Ryan",
                "runtime_revision": "4" * 64,
            },
            "chunk_mapping_sha256": owner.mapping(self.package),
            "source_units_sha256": owner.sha(owner.canonical(self.units)),
            "reader_paragraph_map_sha256": owner.sha(
                owner.canonical(
                    owner.reader_paragraph_map((self.root / "source.txt").read_text())
                )
            ),
            "reader_content_sha256": owner.sha(owner.READER_CONTENT.read_bytes()),
            "duration_ms": 2000,
            "master_samples": 48000,
            "audio_use_decision": self.rights,
        }
        self.descriptor = {
            **identity,
            "schema_version": "audiobook_release_descriptor.v1",
            "source_units_sha256": self.adoption["source_units_sha256"],
            "reader_paragraph_map_sha256": self.adoption["reader_paragraph_map_sha256"],
            "release_candidate_status": "OWNER_PRODUCED_QA_ADOPTED_STORAGE_PENDING",
            "known_release_blockers": owner.DOWNSTREAM,
            "evidence_sha256": self.adoption["evidence_sha256"],
            "generation": self.adoption["generation"],
            "sync_tier": "SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY",
            "highlight_sync_enabled": False,
            "duration_ms": 2000,
            "sample_rate": 24000,
            "master_samples": 48000,
            "release_candidate_evidence": {
                "acceptance_policy": owner.POLICY,
                "status": "OWNER_PRODUCED_QA_ADOPTED",
                "adoption_sha256": owner.sha(owner.canonical(self.adoption)),
                "human_scores": None,
                "all_release_gates_passed": False,
                "highlight_sync_enabled": False,
            },
        }
        self.package["release_descriptor_sha256"] = owner.sha(
            owner.canonical(self.descriptor)
        )
        self.bundle = {
            "schema": "earnalism.owner-produced-local-package.v1",
            "release_descriptor": self.descriptor,
            "package_identity": self.package,
            "evidence_files": evidence,
            "master_wav": wav,
            "master_mp3": mp3,
            "manuscript": self.manuscript,
            "source_units": self.units,
            "asset_files": self.files,
        }
        self.trust = patch.object(owner, "load_adoption", return_value=self.adoption)
        self.trust.start()
        self.reg = patch.object(
            owner,
            "load_production_registry",
            return_value=(
                {self.rights["decision_id"]: record_sha256(self.rights)},
                frozenset(),
            ),
        )
        self.reg.start()

    def tearDown(self):
        self.trust.stop()
        self.reg.stop()
        self.tmp.cleanup()

    def validate(self):
        return owner.validate(self.descriptor, self.package, "en", owner.DOWNSTREAM)

    def prepare(self):
        p = self.root / "bundle.json"
        p.write_text(json.dumps(self.bundle))
        return owner.prepare(p, self.root / "out")

    def test_actual_empty_registry_denies(self):
        self.trust.stop()
        with self.assertRaises(owner.OwnerProducedError):
            self.validate()

    def test_exact_adopted_fixture_without_public_claim(self):
        self.assertFalse(
            self.validate()["release_candidate_evidence"]["all_release_gates_passed"]
        )

    def test_manager_dispatch(self):
        self.assertEqual(
            manager.validate_qa_candidate_release_descriptor(
                self.descriptor, self.package, controlled_language="en"
            ),
            self.descriptor,
        )

    def test_mutations_fail_closed(self):
        for field, value in [
            ("master_wav_sha256", "0" * 64),
            ("manuscript_sha256", "5" * 64),
            ("slug", "the-open-window"),
            ("duration_ms", 1001),
            ("master_samples", 1),
            ("highlight_sync_enabled", True),
            ("known_release_blockers", []),
        ]:
            original = copy.deepcopy(self.descriptor)
            self.descriptor[field] = value
            with self.subTest(field=field), self.assertRaises(owner.OwnerProducedError):
                self.validate()
            self.descriptor.clear()
            self.descriptor.update(original)

    def test_no_scores_or_waiver(self):
        self.descriptor["release_candidate_evidence"]["human_scores"] = {"overall": 10}
        with self.assertRaises(owner.OwnerProducedError):
            self.validate()

    def test_changed_order_or_assets(self):
        for mutation in ("order", "hash"):
            p = copy.deepcopy(self.package)
            if mutation == "order":
                p["tracks"][0]["chunks"].reverse()
            else:
                p["tracks"][0]["chunks"][0]["assets"]["audio"]["sha256"] = "5" * 64
            with self.assertRaises(owner.OwnerProducedError):
                owner.validate(self.descriptor, p, "en", owner.DOWNSTREAM)

    def test_revoked_or_reader_rights_denied(self):
        with patch.object(
            owner,
            "load_production_registry",
            return_value=({}, frozenset([self.rights["decision_id"]])),
        ):
            with self.assertRaises(owner.OwnerProducedError):
                self.validate()

    def test_unresolved_wording_denied(self):
        self.adoption["unresolved_wording_findings"] = ["unit-1"]
        with self.assertRaises(owner.OwnerProducedError):
            self.validate()

    def test_local_prepare_no_upload_or_existing_overwrite(self):
        r = self.prepare()
        self.assertFalse(r["upload_performed"])
        self.assertFalse(r["public_release_approved"])
        out = self.root / "out"
        plan = json.loads((out / "upload-plan.json").read_text())
        self.assertEqual(len(plan["assets"]), 10)
        self.assertTrue(
            all(
                x["key"].startswith("v1/prod/sprint1/the-selfish-giant/releases/")
                for x in plan["assets"]
            )
        )
        with self.assertRaises(owner.OwnerProducedError):
            self.prepare()

    def test_local_changed_file_denied(self):
        (self.root / "master.mp3").write_bytes(b"changed")
        with self.assertRaises(owner.OwnerProducedError):
            self.prepare()

    def test_local_lexical_omission_denied(self):
        self.bundle["source_units"][1]["text"] = "Last"
        with self.assertRaises(owner.OwnerProducedError):
            self.prepare()

    def test_local_source_unit_order_denied(self):
        self.bundle["source_units"].reverse()
        with self.assertRaises(owner.OwnerProducedError):
            self.prepare()

    def test_redistribution_same_global_words_denied(self):
        self.bundle["source_units"][0]["text"] = "First unit. Last"
        self.bundle["source_units"][1]["text"] = "unit."
        with self.assertRaises(owner.OwnerProducedError):
            self.prepare()

    def test_unit_offsets_and_hash_bound(self):
        self.bundle["source_units"][1]["source_start"] = 11
        # Even if supplied manifest/descriptor is altered, reviewed adoption pins it.
        self.descriptor["source_units_sha256"] = owner.sha(
            owner.canonical(self.bundle["source_units"])
        )
        with self.assertRaises(owner.OwnerProducedError):
            self.prepare()

    def test_local_path_escape_denied(self):
        self.bundle["evidence_files"]["objective_qa"]["path"] = "../outside"
        with self.assertRaises(owner.OwnerProducedError):
            self.prepare()

    def test_real_registry_shape_and_changed_adoption(self):
        self.trust.stop()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "registry.json"
            p.write_text(
                json.dumps(
                    {
                        "schema": "earnalism.owner-produced-adoptions.v1",
                        "adoptions": [
                            {"record": self.adoption, "record_sha256": "0" * 64}
                        ],
                    }
                )
            )
            with patch.object(owner, "REGISTRY", p), self.assertRaises(
                owner.OwnerProducedError
            ):
                owner.load_adoption("the-selfish-giant")

    def test_wrong_voice_and_licence_binding_denied(self):
        self.descriptor["generation"] = dict(
            self.descriptor["generation"], voice="Other"
        )
        with self.assertRaises(owner.OwnerProducedError):
            self.validate()
        self.descriptor["generation"] = self.adoption["generation"]
        self.descriptor["evidence_sha256"] = dict(
            self.adoption["evidence_sha256"], model_voice_licence="0" * 64
        )
        with self.assertRaises(owner.OwnerProducedError):
            self.validate()

    def split_first_unit(self):
        units = [
            {
                "id": "generation-a",
                "delivery_segment_id": "unit-0",
                "text": "First ",
                "source_start": 0,
                "source_end": 6,
                "start_word": 0,
                "end_word": 0,
                "text_sha256": owner.sha(b"First "),
            },
            {
                "id": "generation-b",
                "delivery_segment_id": "unit-0",
                "text": "unit.",
                "source_start": 6,
                "source_end": 11,
                "start_word": 1,
                "end_word": 1,
                "text_sha256": owner.sha(b"unit."),
            },
            dict(self.units[1], delivery_segment_id="unit-1"),
        ]
        return units

    def test_many_generation_units_one_real_paragraph_delivery(self):
        units = self.split_first_unit()
        self.bundle["source_units"] = units
        digest = owner.sha(owner.canonical(units))
        self.adoption["source_units_sha256"] = digest
        self.descriptor["source_units_sha256"] = digest
        self.descriptor["release_candidate_evidence"]["adoption_sha256"] = owner.sha(
            owner.canonical(self.adoption)
        )
        self.package["release_descriptor_sha256"] = owner.sha(
            owner.canonical(self.descriptor)
        )
        self.assertFalse(self.prepare()["public_release_approved"])

    def test_regrouping_or_unit_order_denied(self):
        units = self.split_first_unit()
        source = (self.root / "source.txt").read_text()
        paras = owner.reader_paragraph_map(source)["paragraphs"]
        for kind in ("regroup", "order", "missing"):
            u = copy.deepcopy(units)
            if kind == "regroup":
                u[1]["delivery_segment_id"] = "unit-1"
            if kind == "order":
                u[0], u[1] = u[1], u[0]
            if kind == "missing":
                u.pop(1)
            with self.subTest(kind=kind), self.assertRaises(owner.OwnerProducedError):
                owner.validate_source_grouping(source, u, self.package, paras)

    def test_inside_paragraph_boundary_and_fake_unit_paragraphs_denied(self):
        source = (self.root / "source.txt").read_text()
        paras = owner.reader_paragraph_map(source)["paragraphs"]
        u = self.split_first_unit()
        # First generation unit must not be emitted as its own paragraph chunk.
        p = copy.deepcopy(self.package)
        p["tracks"][0]["chunks"][0]["end_word"] = 0
        with self.assertRaises(owner.OwnerProducedError):
            owner.validate_source_grouping(source, u, p, paras)
        p = copy.deepcopy(self.package)
        p["tracks"][0]["chunks"][1]["start_paragraph"] = 2
        with self.assertRaises(owner.OwnerProducedError):
            owner.validate_source_grouping(source, u, p, paras)

    def test_actual_canonical_reader_map_is_not_unit_numbering(self):
        chapter = json.loads(
            (
                owner.ROOT
                / "backend/data/controlled_publications/the-selfish-giant/chapters/chapter-001.json"
            ).read_text()
        )
        self.assertEqual(
            owner.sha(chapter["content"].encode()),
            "c55bef9dcd5883e156af940deb849c67a78a8fae7fc7a1e50ea814aa9ce866c5",
        )
        self.assertEqual(
            len(owner.reader_paragraph_map(chapter["content"])["paragraphs"]), 23
        )

    def test_reader_reflow_binding_change_and_duration_limit_denied(self):
        self.adoption["reader_content_sha256"] = "0" * 64
        with self.assertRaises(owner.OwnerProducedError):
            self.validate()
        p = copy.deepcopy(self.package)
        p["tracks"][0]["chunks"][0]["duration_ms"] = 720001
        with self.assertRaises(owner.OwnerProducedError):
            owner.validate_topology(p)

    def test_pcm_and_float_wav_framing(self):
        import struct

        fmt = struct.pack("<HHIIHH", 3, 1, 24000, 96000, 4, 32)
        data = struct.pack("<fff", 0.0, 0.1, -0.1)
        body = (
            b"WAVE"
            + b"fmt "
            + struct.pack("<I", len(fmt))
            + fmt
            + b"data"
            + struct.pack("<I", len(data))
            + data
        )
        raw = b"RIFF" + struct.pack("<I", len(body)) + body
        self.assertEqual(owner.wav_identity(raw)["samples"], 3)
        self.assertEqual(owner.wav_identity(raw)["format"], "IEEE_FLOAT")
        for bad in [
            raw[:-1],
            raw.replace(b"WAVE", b"FAKE", 1),
            raw[:20] + b"\x06\x00" + raw[22:],
        ]:
            with self.assertRaises(owner.OwnerProducedError):
                owner.wav_identity(bad)

    def test_generic_finalize_and_structural_guard(self):
        from audiobook_package_builder_v2 import finalize_package

        self.prepare()
        out = self.root / "out"
        plan = json.loads((out / "upload-plan.json").read_text())
        semantics = json.loads((out / "package-semantics.json").read_text())

        def rows(store):
            return [
                dict(
                    x,
                    store=store,
                    bucket="fixture-" + store,
                    version_id="fixture-version-" + store,
                )
                for x in plan["assets"]
            ]

        primary = {
            "receipt_role": "primary",
            "release_eligible": True,
            "passed": True,
            "objects": rows("prod"),
        }
        replica = {
            "receipt_role": "replica",
            "store": {"release_eligible": True},
            "passed": True,
            "objects": rows("dr"),
        }
        package = finalize_package(
            semantics=semantics,
            upload_plan=plan,
            primary_receipt=primary,
            replica_receipt=replica,
        )
        self.assertEqual(
            owner.validate(self.descriptor, package, "en", owner.DOWNSTREAM),
            self.descriptor,
        )
        package["tracks"][0]["chunks"][0]["cumulative_start_ms"] = 9
        with self.assertRaises(owner.OwnerProducedError):
            owner.validate(self.descriptor, package, "en", owner.DOWNSTREAM)


if __name__ == "__main__":
    unittest.main()
