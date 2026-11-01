"""Structural fixtures only; no successor adoption, media or storage receipt."""

import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "internal/audiobook_lab/scripts"))
import audiobook_packages as m
import owner_produced_package as owner


def candidate():
    book = json.loads(
        (
            ROOT
            / "backend/data/controlled_publications/the-selfish-giant/public_book.json"
        ).read_text()
    )
    p = copy.deepcopy(
        book["audiobook_packages"][
            "b5b378168211d61ac80341e74cbfacaf0d5590a18300a5c91db4684626e343a2"
        ]
    )
    p["segment_count"] = 1
    t = p["tracks"][0]
    c = copy.deepcopy(t["chunks"][0])
    c.update(
        segment_id="chapter-001-full",
        duration_ms=777120,
        end_word=1651,
        end_paragraph=22,
    )
    c["assets"]["audio"].update(
        sha256="8cbaecc48b84372dcab020b4514d2e50c4a6f386018de573baa98bb7e7fb6d0b",
        size_bytes=6217581,
    )
    t["chunks"] = [c]
    return p


def validate(p):
    # Pure topology/hash/storage-locator test only; fixture has no successor
    # adoption or new immutable receipts and cannot be released.
    p = m.with_canonical_package_version(p)
    return m.validate_audiobook_package(
        p,
        expected_slug=p["slug"],
        expected_source_sha256=p["source_sha256"],
        expected_manuscript_sha256=p["manuscript_sha256"],
        expected_release_descriptor_sha256=p["release_descriptor_sha256"],
    )


class DurationTests(unittest.TestCase):
    def test_exact_master_topology_native_pass(self):
        p = candidate()
        validate(p)
        self.assertEqual(
            m.segment_duration_limit_ms(p, p["tracks"][0], p["tracks"][0]["chunks"][0]),
            777120,
        )
        self.assertEqual(m.MAX_SEGMENT_DURATION_MS, 720000)

    def test_ordinary_boundary_native(self):
        for duration, admitted in [
            (720000, True),
            (720001, False),
            (777120, False),
            (900000, False),
        ]:
            with self.subTest(duration=duration):
                p = candidate()
                p["slug"] = "another-title"
                p["duration_ms"] = duration
                p["tracks"][0]["chunks"][0]["duration_ms"] = duration
                # Keep storage-prefix validity for ordinary title test.
                for asset in p["tracks"][0]["chunks"][0]["assets"].values():
                    asset["storage"]["key"] = asset["storage"]["key"].replace(
                        "/the-selfish-giant/", "/another-title/"
                    )
                    for replica in asset["replicas"]:
                        replica["key"] = replica["key"].replace(
                            "/the-selfish-giant/", "/another-title/"
                        )
                if admitted:
                    validate(p)
                else:
                    with self.assertRaises(m.AudiobookPackageValidationError):
                        validate(p)

    def test_individual_identity_tampering_denied_native(self):
        cases = [
            ("slug", "other"),
            ("source_sha256", "1" * 64),
            ("manuscript_sha256", "2" * 64),
            ("duration_ms", 777121),
            ("segment_count", 2),
            ("word_count", 1653),
            ("paragraph_count", 24),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                p = candidate()
                p[key] = value
                with self.assertRaises(m.AudiobookPackageValidationError):
                    validate(p)

    def test_asset_and_topology_tampering_denied_native(self):
        cases = [
            ("audio", "sha256", "3" * 64),
            ("audio", "size_bytes", 6217582),
            ("audio", "size_bytes", True),
            ("audio", "mime_type", "audio/wav"),
            ("track", "id", "other"),
            ("track", "chapter_id", "other"),
            ("segment", "order", 1),
            ("segment", "cumulative_start_ms", 1),
            ("segment", "duration_ms", 777121),
            ("segment", "duration_ms", 900000),
            ("segment", "duration_ms", True),
            ("segment", "duration_ms", "777120"),
            ("segment", "end_word", 1652),
            ("segment", "end_paragraph", 23),
        ]
        for section, key, value in cases:
            with self.subTest(section=section, key=key, value=value):
                p = candidate()
                t = p["tracks"][0]
                c = t["chunks"][0]
                target = (
                    c["assets"]["audio"]
                    if section == "audio"
                    else t if section == "track" else c
                )
                target[key] = value
                with self.assertRaises(m.AudiobookPackageValidationError):
                    validate(p)

    def test_multitrack_and_multisegment_helper_denied(self):
        for multiple in ["tracks", "chunks"]:
            p = candidate()
            t = p["tracks"][0]
            c = t["chunks"][0]
            if multiple == "tracks":
                p["tracks"].append(copy.deepcopy(t))
            else:
                t["chunks"].append(copy.deepcopy(c))
            self.assertEqual(m.segment_duration_limit_ms(p, t, c), 720000)
            with self.assertRaises(m.AudiobookPackageValidationError):
                validate(p)

    def test_builder_and_runtime_share_duration_decision(self):
        p = candidate()
        owner.validate_topology(p)
        validate(p)
        for section, key, value in [
            ("audio", "size_bytes", 6217582),
            ("segment", "duration_ms", 777121),
            ("package", "slug", "other"),
        ]:
            with self.subTest(section=section, key=key):
                p = candidate()
                target = (
                    p["tracks"][0]["chunks"][0]["assets"]["audio"]
                    if section == "audio"
                    else p["tracks"][0]["chunks"][0] if section == "segment" else p
                )
                target[key] = value
                with self.assertRaises(owner.OwnerProducedError):
                    owner.validate_topology(p)
                with self.assertRaises(m.AudiobookPackageValidationError):
                    validate(p)

    def test_other_native_guards_remain(self):
        for kind in ["replica", "prefix", "packagehash", "sourceexpectation"]:
            p = candidate()
            c = p["tracks"][0]["chunks"][0]
            with self.subTest(kind=kind):
                if kind == "replica":
                    c["assets"]["audio"]["replicas"] = []
                if kind == "prefix":
                    c["assets"]["audio"]["storage"]["key"] = "wrong/key"
                if kind in ["replica", "prefix"]:
                    with self.assertRaises(m.AudiobookPackageValidationError):
                        validate(p)
                else:
                    p = m.with_canonical_package_version(p)
                    if kind == "packagehash":
                        p["package_version"] = "sha256-" + "0" * 64
                    with self.assertRaises(m.AudiobookPackageValidationError):
                        m.validate_audiobook_package(
                            p,
                            expected_slug=p["slug"],
                            expected_source_sha256=(
                                "f" * 64
                                if kind == "sourceexpectation"
                                else p["source_sha256"]
                            ),
                            expected_manuscript_sha256=p["manuscript_sha256"],
                            expected_release_descriptor_sha256=p[
                                "release_descriptor_sha256"
                            ],
                        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
