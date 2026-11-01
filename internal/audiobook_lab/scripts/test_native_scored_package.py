"""Synthetic contract fixtures only; no real adoption/provider/storage/release PASS."""
import copy
import hashlib
import json
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import native_scored_package as native
import owner_produced_package as legacy
import audiobook_active_release_v2 as manager
from rights_decision_gate import record_sha256
from audiobook_packages import with_canonical_package_version, build_active_release_state
import protected_package_publication as runtime_publication


class NativeScoredContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.registry = self.base / "adoptions.json"
        self.patch = patch.object(native, "REGISTRY", self.registry)
        self.patch.start()
        evidence = {k: hashlib.sha256(("SYNTHETIC_NOT_AUTHORITY_" + k).encode()).hexdigest() for k in native.EVIDENCE_ROLES}
        identity = {**native.SOURCE, "master_wav_sha256": "1" * 64, "master_mp3_sha256": "2" * 64}
        assets = {role: {"sha256": hashlib.sha256(("SYNTHETIC_" + role).encode()).hexdigest(), "size_bytes": 16, "mime_type": mime} for role, mime in legacy.ROLES.items()}
        self.package = {
            "slug": "the-selfish-giant", "source_sha256": native.SOURCE["controlled_source_sha256"],
            "manuscript_sha256": native.SOURCE["manuscript_sha256"], "duration_ms": 2000,
            "segment_count": 1, "word_count": 1652, "paragraph_count": 23,
            "sync_tier": native.SYNC_TIER, "highlight_sync_enabled": False,
            "tracks": [{"id": "chapter-001", "chapter_id": "chapter-001", "order": 0, "title": "The Selfish Giant",
                "start_word": 0, "end_word": 1651, "start_paragraph": 0, "end_paragraph": 22,
                "chunks": [{"segment_id": "chapter-001-full", "order": 0, "start_word": 0, "end_word": 1651,
                    "start_paragraph": 0, "end_paragraph": 22, "cumulative_start_ms": 0, "duration_ms": 2000, "assets": assets}]}],
        }
        mapping = legacy.mapping(self.package)
        proof = {"schema": "earnalism.container_metadata_audio_reuse.v1", "status": "PASS_EXACT_DECODED_PCM_AND_ELEMENTARY_PACKET_EQUALITY_METADATA_ONLY",
            "items": {name: {"file_sha256": digest, "canonical_decoded_PCM": {"sha256": "3" * 64, "bytes": 96000 * 8},
                "elementary_encoded_audio_packets": {"sha256": "4" * 64, "bytes": 1024}} for name, digest in [("listened", "5" * 64), ("delivery", identity["master_mp3_sha256"])]},
            "canonical_decoded_PCM_format": {"sample_rate": 48000, "channels": 2, "format": "f32le", "frames": 96000}}
        self.adoption = {
            "status": "ADOPTED", "policy": native.POLICY, "identity": identity,
            "adopted_by": "SYNTHETIC_FIXTURE_NOT_OWNER", "authority_reference": "SYNTHETIC_FIXTURE_ONLY", "authority_evidence_sha256": "6" * 64,
            "unresolved_material_defects": [], "unresolved_wording_findings": [], "generation": copy.deepcopy(native.GENERATION),
            "generation_counts": {"responses": 17, "one_shot_limit": 17, "retries": 0, "new_allocations": 0},
            "evidence_sha256": evidence, "human_scores": {k: .96 if k == "confidence_score" else 9.5 for k in native.SCORES},
            "quality": {**dict.fromkeys(["full_title_listening_performed", "full_scored_mix_listening_performed", "all_joins_reviewed", "music_continuity_and_intelligibility_reviewed", "first_words_match", "last_words_match", "ordered_content_integrity"], True),
                "fatal_flags": [], "auto_estimated_sync": False, "asr_score": 9.99, "source_coverage": 1.0},
            "reader_paragraph_map_sha256": "7" * 64, "reader_content_sha256": legacy.sha(legacy.READER_CONTENT.read_bytes()),
            "source_units_sha256": "8" * 64, "duration_ms": 2000, "master_samples": 96000,
            "chunk_mapping_sha256": mapping, "listened_master_mp3_sha256": "5" * 64, "container_metadata_reuse": proof,
            "alignment": {"audio_derived_or_measured": True, "auto_estimated_sync": False, "paragraph_count": 23, "word_count": 1652,
                "timestamps_sha256": assets["timestamps"]["sha256"], "master_mp3_sha256": identity["master_mp3_sha256"]},
            "score": {"licensed_instrumental_score": True, "attribution_bound": True, "reviewed_mp3_sha256": "5" * 64, "rights_evidence_sha256": evidence["music_rights"]},
        }
        components = {"source_file": identity["controlled_source_sha256"], "selected_manuscript": identity["manuscript_sha256"],
            "master_wav": identity["master_wav_sha256"], "master_mp3": identity["master_mp3_sha256"], "audio_component_bindings": mapping,
            "model_voice_licence": evidence["model_voice_licence"], "music_rights": evidence["music_rights"],
            "listened_master_mp3": "5" * 64, "container_metadata_reuse": evidence["container_metadata_reuse"]}
        self.rights = {"schema_version": "earnalism.rights-decision.v1", "decision_id": "synthetic-native-contract-not-authority", "edition_id": "the-selfish-giant", "operator_id": "reo-enterprise",
            "status": "ACCEPTED", "components": components, "territories": ["IN"], "uses": ["audio_stream"],
            "valid_from": "2020-01-01T00:00:00+00:00", "valid_until": "2099-01-01T00:00:00+00:00", "basis": "SYNTHETIC_TEST_ONLY", "evidence_sha256": ["9" * 64], "accepted_by": "SYNTHETIC", "conditions_satisfied": True}
        self.adoption["audio_use_decision"] = self.rights
        self.descriptor = {**identity, "schema_version": "audiobook_release_descriptor.v1", "generation": copy.deepcopy(native.GENERATION), "evidence_sha256": evidence,
            "known_release_blockers": legacy.DOWNSTREAM, "release_candidate_status": "OWNER_PRODUCED_NATIVE_SCORED_QA_ADOPTED_STORAGE_PENDING",
            "sync_tier": native.SYNC_TIER, "highlight_sync_enabled": False, "reader_paragraph_map_sha256": "7" * 64,
            "source_units_sha256": "8" * 64, "measured_alignment_sha256": evidence["measured_alignment"],
            "sample_rate": 48000, "channels": 2, "master_samples": 96000, "duration_ms": 2000, "listened_master_mp3_sha256": "5" * 64}
        self.trust = patch.object(native, "load_production_registry", side_effect=lambda: ({self.rights["decision_id"]: record_sha256(self.rights)}, frozenset()))
        self.trust.start()
        self.rebind()

    def tearDown(self):
        self.trust.stop()
        self.patch.stop()
        self.tmp.cleanup()

    def rebind(self):
        self.registry.write_text(json.dumps({"schema": "earnalism.native-scored-adoptions.v1", "adoptions": [{"record": self.adoption, "record_sha256": native.sha(native.canonical(self.adoption))}]}))
        self.descriptor["release_candidate_evidence"] = {"acceptance_policy": native.POLICY, "status": "OWNER_PRODUCED_NATIVE_SCORED_QA_ADOPTED",
            "adoption_sha256": native.sha(native.canonical(self.adoption)), "human_scores": self.adoption["human_scores"], "all_release_gates_passed": False, "highlight_sync_enabled": False}
        self.package["release_descriptor_sha256"] = native.sha(native.canonical(self.descriptor))

    def validate(self):
        return native.validate(self.descriptor, self.package, "en", legacy.DOWNSTREAM)

    def test_reviewed_exact_source_candidate_not_public_ready(self):
        result = self.validate()
        self.assertFalse(result["release_candidate_evidence"]["all_release_gates_passed"])
        self.assertEqual(result["known_release_blockers"], legacy.DOWNSTREAM)

    def test_empty_committed_native_registry_denies(self):
        self.registry.write_text(json.dumps({"schema": "earnalism.native-scored-adoptions.v1", "adoptions": []}))
        with self.assertRaises(native.Error): self.validate()

    def test_changed_master_not_the_adopted_identity(self):
        self.descriptor["master_mp3_sha256"] = "a" * 64
        self.package["release_descriptor_sha256"] = native.sha(native.canonical(self.descriptor))
        with self.assertRaises(native.Error): self.validate()

    def test_legacy_ryan_cannot_be_relabelled_native(self):
        self.descriptor["generation"]["voice"] = "Ryan"
        self.adoption["generation"]["voice"] = "Ryan"
        self.rebind()
        with self.assertRaises(native.Error): self.validate()

    def test_generation_limit_or_new_allocation_denied(self):
        for key, value in [("responses", 18), ("retries", 1), ("new_allocations", 1)]:
            with self.subTest(key=key):
                old = self.adoption["generation_counts"][key]
                self.adoption["generation_counts"][key] = value
                self.rebind()
                with self.assertRaises(native.Error): self.validate()
                self.adoption["generation_counts"][key] = old

    def test_model_revision_not_invented(self):
        self.descriptor["generation"]["model_revision"] = "invented-dated-revision"
        self.adoption["generation"]["model_revision"] = "invented-dated-revision"
        self.rebind()
        with self.assertRaises(native.Error): self.validate()

    def test_fatal_defect_and_missing_full_scored_review_denied(self):
        for field, value in [("full_scored_mix_listening_performed", False), ("music_continuity_and_intelligibility_reviewed", False), ("fatal_flags", ["robotic_texture_detected"]), ("auto_estimated_sync", True)]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.adoption["quality"])
                self.adoption["quality"][field] = value
                self.rebind()
                with self.assertRaises(native.Error): self.validate()
                self.adoption["quality"] = original

    def test_nan_boolean_low_score_or_low_confidence_denied(self):
        for field, value in [("naturalness_score", float("nan")), ("pronunciation_score", True), ("overall_listening_score", 8.8), ("confidence_score", .89)]:
            with self.subTest(field=field):
                original = self.adoption["human_scores"][field]
                self.adoption["human_scores"][field] = value
                self.rebind()
                with self.assertRaises(native.Error): self.validate()
                self.adoption["human_scores"][field] = original

    def test_estimated_sync_or_wrong_audio_sidecar_denied(self):
        for field, value in [("auto_estimated_sync", True), ("master_mp3_sha256", "a" * 64), ("timestamps_sha256", "b" * 64)]:
            with self.subTest(field=field):
                original = self.adoption["alignment"][field]
                self.adoption["alignment"][field] = value
                self.rebind()
                with self.assertRaises(native.Error): self.validate()
                self.adoption["alignment"][field] = original

    def test_music_rights_and_independent_india_rights_required(self):
        self.adoption["score"]["attribution_bound"] = False
        self.rebind()
        with self.assertRaises(native.Error): self.validate()
        self.adoption["score"]["attribution_bound"] = True
        self.rights["territories"] = ["US"]
        self.rebind()
        with self.assertRaises(native.Error): self.validate()

    def test_metadata_proof_cannot_hide_changed_audio(self):
        self.adoption["container_metadata_reuse"]["items"]["delivery"]["canonical_decoded_PCM"]["sha256"] = "c" * 64
        self.rebind()
        with self.assertRaises(native.Error): self.validate()

    def test_packet_changes_and_frame_drift_denied(self):
        for part, key, value in [("elementary_encoded_audio_packets", "sha256", "c" * 64), ("canonical_decoded_PCM", "bytes", 8)]:
            with self.subTest(part=part):
                original = copy.deepcopy(self.adoption["container_metadata_reuse"])
                self.adoption["container_metadata_reuse"]["items"]["delivery"][part][key] = value
                self.rebind()
                with self.assertRaises(native.Error): self.validate()
                self.adoption["container_metadata_reuse"] = original

    def test_storage_independent_mapping_must_remain_exact(self):
        self.package["tracks"][0]["chunks"][0]["assets"]["audio"]["sha256"] = "c" * 64
        with self.assertRaises(native.Error): self.validate()

    def test_revocation_is_not_overridden_by_owner_scores(self):
        with patch.object(native, "load_production_registry", return_value=({self.rights["decision_id"]: record_sha256(self.rights)}, frozenset([self.rights["decision_id"]]))):
            with self.assertRaises(native.Error): self.validate()

    def test_manager_dispatches_new_profile_without_legacy_label(self):
        self.assertEqual(manager.validate_qa_candidate_release_descriptor(self.descriptor, self.package, controlled_language="en"), self.descriptor)

    def test_publication_tags_must_disclose_ai_credit_score_and_drop_draft_claims(self):
        tags = {"title": "The Selfish Giant", "artist": "Earnalism; AI narrator: Cedar",
            "comment": "AI narration: Cedar via OpenAI. Music: Heartwarming and Heartbreaking by Kevin MacLeod; https://creativecommons.org/licenses/by/4.0/. Actual arranged score."}
        native.validate_publication_tags(tags)
        for key, value in [("title", "Wrong book"), ("artist", "Ryan"), ("comment", "AI narration: Cedar via OpenAI. PRIVATE SCORED DRAFT"),
                ("comment", tags["comment"] + " Proposed changes: music")]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(native.Error): native.validate_publication_tags({**tags, key: value})

    def test_publication_tags_reject_standalone_hold_language_private_paths_and_signed_credentials(self):
        tags={"title":"The Selfish Giant","artist":"Earnalism; AI narrator: Cedar",
            "comment":"AI narration: Cedar via OpenAI. Music: Heartwarming and Heartbreaking by Kevin MacLeod; https://creativecommons.org/licenses/by/4.0/. Actual arranged score."}
        for leakage in ("Private draft; not published.","Pending owner review.","DRAFT", "private", "review complete",
                "/Users/ronikbasak/private.mp3", "/tmp/local.mp3", "file:///home/operator/book.mp3", "C:\\Users\\operator\\book.mp3",
                "https://example.invalid/audio?X-Amz-Signature=secret", "https://example.invalid/audio?X-Amz-Credential=secret",
                "Authorization: Bearer secret"):
            with self.subTest(leakage=leakage):
                with self.assertRaises(native.Error): native.validate_publication_tags({**tags,"comment":tags["comment"]+"\n"+leakage})

    def test_final_v2_runtime_contract_requires_new_audio_rights_and_actual_acceptance_shape(self):
        # Entire publication authority/proof fixture is synthetic, never committed/adopted.
        package = copy.deepcopy(self.package)
        package.update(schema_version="audiobook_package_manifest.v2", release_evidence_version=native.POLICY)
        descriptor = package["release_descriptor_sha256"]
        prefix = f"v1/prod/sprint1/the-selfish-giant/releases/{descriptor}/"
        for role, asset in package["tracks"][0]["chunks"][0]["assets"].items():
            asset.update(storage={"store":"prod","bucket":"synthetic-primary","key":prefix+role,"version_id":"synthetic-prod-"+role},
                replicas=[{"store":"dr","bucket":"synthetic-dr","key":prefix+role,"version_id":"synthetic-dr-"+role}])
        package = with_canonical_package_version(package)
        self.assertEqual(native.validate(self.descriptor, package, "en", legacy.DOWNSTREAM), self.descriptor)
        acceptance={"schema_version":"audiobook_public_package_acceptance.v1","release_descriptor_sha256":descriptor,
            "package_version":package["package_version"],"duration_ms":2000,"segment_count":1,
            "production_proof_sha256":{k:"a"*64 for k in ("playback","business","accounting")},"accounting_commit":"b"*40}
        digest=record_sha256(self.rights)
        book={"slug":"the-selfish-giant","source_hash":native.SOURCE["controlled_source_sha256"],
            "audiobook_manuscript_sha256":native.SOURCE["manuscript_sha256"],"audiobook_release_mode":"PROTECTED_PACKAGE_V2",
            "audiobook_packages":{descriptor:package},"audiobook_active_release":build_active_release_state(
                slug="the-selfish-giant",active_release_descriptor_sha256=descriptor,retained_release_descriptor_sha256s=[descriptor]),
            "audiobook_public_package_approval":{"schema_version":runtime_publication.SCHEMA,"status":"PUBLIC_APPROVED",
                "slug":"the-selfish-giant","release_descriptor_sha256":descriptor,
                "endpoint":"/api/reader/book/the-selfish-giant/audiobook/manifest","audio_rights_decision_id":self.rights["decision_id"],
                "audio_rights_record_sha256":digest,"acceptance":acceptance,"acceptance_sha256":native.sha(native.canonical(acceptance))},
            "audiobook_package_release_evidence":{descriptor:{"schema_version":"audiobook_package_release_evidence.v1",
                "slug":"the-selfish-giant","release_descriptor_sha256":descriptor,"package_version":package["package_version"],
                "release_eligible":True,"receipt_roles":["primary","replica"],"primary_release_manifest_store":"prod",
                "replica_release_manifest_store":"dr","primary_release_manifest_version_id":"synthetic-prod-manifest",
                "replica_release_manifest_version_id":"synthetic-dr-manifest","release_manifest_size_bytes":4000,
                "release_manifest_key":prefix+"release-manifest.json",**{k:"c"*64 for k in ("primary_receipt_sha256","replica_receipt_sha256",
                    "release_manifest_sha256","primary_release_manifest_receipt_sha256","replica_release_manifest_receipt_sha256")}}}}
        with patch.object(runtime_publication,"load_production_registry",return_value=({self.rights["decision_id"]:digest},frozenset())), \
                patch.object(runtime_publication,"load_audio_package_binding",return_value={"decision_id":self.rights["decision_id"],"record_sha256":digest}):
            self.assertTrue(runtime_publication.protected_package_publication_valid(book))
            # No stale legacy/global flag can replace current descriptor-bound proof.
            book["audiobook_public_package_approval"]["acceptance"]["duration_ms"]=777120
            self.assertFalse(runtime_publication.protected_package_publication_valid(book))

    def test_48k_stereo_wav_and_old_24k_mono_contracts_separate(self):
        for name, channels, rate, validator in [("new.wav", 2, 48000, native.wav_identity), ("old.wav", 1, 24000, legacy.wav_identity)]:
            p = self.base / name
            with wave.open(str(p), "wb") as w:
                w.setnchannels(channels); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b"\0" * channels * 2 * 96)
            self.assertEqual(validator(p.read_bytes())["sample_rate"], rate)
        with self.assertRaises(native.Error): native.wav_identity((self.base / "old.wav").read_bytes())
        with self.assertRaises(native.Error): legacy.wav_identity((self.base / "new.wav").read_bytes())


class MetadataOnlyActualDecodeTests(unittest.TestCase):
    def test_actual_non_speech_metadata_copy_keeps_pcm_and_packets(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); prior = base / "synthetic-tone.mp3"; delivery = base / "metadata-only.mp3"; other = base / "different-tone.mp3"
            for path, frequency in [(prior, 440), (other, 880)]:
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=48000:duration=0.1", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k", str(path)], check=True, timeout=15)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(prior), "-map", "0:a:0", "-c:a", "copy", "-metadata", "title=metadata-test-only", str(delivery)], check=True, timeout=15)
            self.assertNotEqual(prior.read_bytes(), delivery.read_bytes())
            self.assertEqual(native.decoded_pcm_identity(prior), native.decoded_pcm_identity(delivery))
            self.assertNotEqual(native.decoded_pcm_identity(prior), native.decoded_pcm_identity(other))


if __name__ == "__main__":
    unittest.main()
