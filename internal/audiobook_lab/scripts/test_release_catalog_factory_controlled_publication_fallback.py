import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("release_catalog_factory.py")
SPEC = importlib.util.spec_from_file_location("release_catalog_factory_fallback", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ControlledPublicationFallbackTests(unittest.TestCase):
    def make_packet(self, root, slug, marker):
        packet = root / slug
        (packet / "chapters").mkdir(parents=True)
        (packet / "public_book.json").write_text(
            json.dumps({"slug": slug, "marker": marker}), encoding="utf-8"
        )
        (packet / "reader_manifest.json").write_text(
            json.dumps({"slug": slug, "chapters": []}), encoding="utf-8"
        )
        (packet / "source_evidence.json").write_text(
            json.dumps({"slug": slug, "source": marker}), encoding="utf-8"
        )
        (packet / "chapters" / "chapter-001.json").write_text(
            json.dumps({"id": "chapter-001", "content": marker}), encoding="utf-8"
        )
        return packet

    def test_root_packet_remains_authoritative_when_both_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "data"
            backend = base / "backend"
            expected = self.make_packet(root, "story", "root")
            self.make_packet(backend, "story", "backend")
            with patch.object(MODULE, "CONTROLLED_PUBLICATION_ROOTS", (root, backend)):
                self.assertEqual(MODULE.controlled_publication_base("story"), expected)
                self.assertEqual(MODULE.load_book_payloads("story")[0]["marker"], "root")

    def test_backend_packet_is_used_when_root_has_only_a_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "data"
            backend = base / "backend"
            (root / "story").mkdir(parents=True)
            (root / "story" / "highlight_sync.json").write_text("{}", encoding="utf-8")
            expected = self.make_packet(backend, "story", "backend")
            with patch.object(MODULE, "CONTROLLED_PUBLICATION_ROOTS", (root, backend)):
                self.assertEqual(MODULE.controlled_publication_base("story"), expected)
                self.assertEqual(MODULE.load_book_payloads("story")[0]["marker"], "backend")
                chapters = MODULE.controlled_chapter_paths("story")
                self.assertEqual([path.name for path in chapters], ["chapter-001.json"])

    def test_audited_graphical_runtime_pair_satisfies_cover_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = {
                "covers": [
                    {
                        "slug": "story",
                        "front_back_pair_exists": True,
                        "front_cover_status": "GRAPHICAL_COVER_APPROVED",
                        "back_cover_status": "GRAPHICAL_COVER_APPROVED",
                        "cover_is_graphical_content_themed": True,
                        "cover_is_typography_only_plain": False,
                        "cover_broken_or_404": False,
                    }
                ]
            }
            (root / "book_cover_audit_report.json").write_text(
                json.dumps(report), encoding="utf-8"
            )
            with patch.object(MODULE, "ROOT", root):
                result = MODULE.cover_inventory(
                    {"slug": "story"}, dry_run=True, slug="story"
                )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["effective_source"], "GRAPHICAL_RUNTIME_FALLBACK")

    def test_explicit_audiobook_use_does_not_require_public_release_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "data"
            packet = self.make_packet(root, "story", "root")
            (packet / "public_book.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "author_death_year": 1894,
                        "original_publication_year": 1886,
                    }
                ),
                encoding="utf-8",
            )
            (packet / "source_evidence.json").write_text(
                json.dumps(
                    {
                        "slug": "story",
                        "source_url": "https://example.invalid/source",
                        "source_name": "Project Gutenberg",
                        "source_license": "Public domain",
                        "source_hash": "abc123",
                        "rights_basis": "Author died 1894; published 1886; public domain.",
                        "downloaded_at": "2026-07-13T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            (packet / "approval_evidence.json").write_text(
                json.dumps(
                    {
                        "rights_tier": "A",
                        "verification_status": "approved",
                        "audiobook_use_approved": True,
                        "audio_public_release": "PUBLIC_AUDIO_RELEASE_NOT_APPROVED",
                    }
                ),
                encoding="utf-8",
            )
            state = MODULE.BookState(
                slug="story",
                title="Story",
                author="Author",
                language="eng",
                order=1,
                catalog_dir=base,
                run_dir=base,
            )
            with patch.object(MODULE, "CONTROLLED_PUBLICATION_ROOTS", (root,)):
                result = MODULE.rights_metadata_report(state)
            self.assertTrue(result["content_use_approved"])
            self.assertTrue(result["audiobook_use_approved"])
            self.assertEqual(
                result["audiobook_use_approval_source"],
                "approval_evidence.audiobook_use_approved",
            )
            self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
