import unittest

from internal.audiobook_lab.scripts.scrub_unapproved_public_audio_assets import (
    audio_release_approved,
    scrub_public_book,
    scrub_reader_manifest,
)


class ScrubUnapprovedPublicAudioAssetsTests(unittest.TestCase):
    def test_only_complete_approved_evidence_preserves_public_audio(self):
        approval = {
            "audio_public_release": "PUBLIC_AUDIO_RELEASE_APPROVED",
            "audiobook_enabled": True,
        }
        book = {"audio_enabled": True, "audiobook_enabled": True}
        self.assertTrue(audio_release_approved(approval, book))
        self.assertFalse(
            audio_release_approved(
                {**approval, "audio_public_release": "PUBLIC_AUDIO_RELEASE_BLOCKED_QA_REQUIRED"},
                book,
            )
        )

    def test_scrub_removes_all_discoverable_audio_fields(self):
        book = {
            "slug": "hidden",
            "audio_enabled": False,
            "audiobook_enabled": False,
            "audiobook_assets": {"mp3": "https://example.test/hidden.mp3"},
            "audiobook": {
                "url": "https://example.test/hidden.mp3",
                "assets": {"timestamps": "https://example.test/hidden.json"},
            },
        }
        scrubbed, removed_keys, removed_urls = scrub_public_book(book)
        self.assertEqual(set(removed_keys), {"audiobook", "audiobook_assets"})
        self.assertEqual(removed_urls, 3)
        self.assertNotIn("audiobook", scrubbed)
        self.assertNotIn("audiobook_assets", scrubbed)
        self.assertFalse(scrubbed["audio_enabled"])
        self.assertFalse(scrubbed["audiobook_enabled"])

    def test_reader_manifest_stays_reader_enabled_and_audio_hidden(self):
        manifest = {
            "reader_enabled": True,
            "audio": {
                "enabled": False,
                "url": "https://example.test/hidden.mp3",
                "assets": {"mp3": "https://example.test/hidden.mp3"},
            },
        }
        scrubbed, removed_urls = scrub_reader_manifest(manifest)
        self.assertTrue(scrubbed["reader_enabled"])
        self.assertFalse(scrubbed["audio"]["enabled"])
        self.assertEqual(scrubbed["audio"]["url"], "")
        self.assertEqual(scrubbed["audio"]["assets"], {})
        self.assertEqual(removed_urls, 2)


if __name__ == "__main__":
    unittest.main()
