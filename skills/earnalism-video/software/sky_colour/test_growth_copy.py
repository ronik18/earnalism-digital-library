"""Packaging-only regressions; neither generated words nor release approvals."""
import json
from pathlib import Path
import tempfile
import unittest

from . import package


class GrowthCopyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sources = [
            {'title': 'NASA: sky colour', 'url': 'https://spaceplace.nasa.gov/blue-sky/en/'},
            {'title': 'NWS: sky colour', 'url': 'https://www.weather.gov/fgz/SkyBlue'},
        ]
        (self.root/'sources.json').write_text(json.dumps({'sources': self.sources}))

    def tearDown(self):
        self.temp.cleanup()

    def test_complementary_truthful_titles_do_not_relabel_the_source_or_publish(self):
        landscape, shorts = package.metadata(self.root, False), package.metadata(self.root, True)
        self.assertEqual(landscape['title'], 'Why One Sun Gives Us Blue Skies and Red Sunsets | Earnalism')
        self.assertEqual(shorts['title'], 'Blue Sky. Red Sunset. What Changed?')
        self.assertNotEqual(landscape['title'], shorts['title'])
        for record in (landscape, shorts):
            self.assertEqual(record['privacyStatus'], 'private')
            self.assertFalse(record['publication_approved'])
            self.assertFalse(record['upload_automatically'])
            self.assertIsNone(record['publishAt'])
            self.assertIsNone(record['related_video'])
            self.assertEqual(record['english_captions'], 'captions.srt')
            self.assertEqual(record['transcript'], 'transcript.txt')
            self.assertEqual(record['audience_classification'], 'PENDING_OWNER_CHOICE_AT_AUTHORIZED_UPLOAD')
            self.assertEqual(record['category'], 'Education')

    def test_copy_retains_science_context_sources_and_brand_pair_without_sales_stack(self):
        descriptions = [package.metadata(self.root, portrait)['description'] for portrait in (False, True)]
        caption = package.instagram_caption(self.root)
        for text in descriptions + [caption]:
            self.assertIn('Blue light has not turned red.', text)
            self.assertIn('direct beam', text)
            self.assertIn('scattered', text)
            self.assertIn('can look orange or red', text)
            self.assertIn(package.DISCLOSURE, text)
            self.assertIn(package.SOLAR_CONTEXT, text)
            self.assertIn('#earnalism #learnalism', text)
            self.assertIn('selected audiobooks', text)
            self.assertNotIn('Read deeply', text)
            for source in self.sources:
                self.assertIn(source['url'], text)
        self.assertTrue(all(text.count('Subscribe to ') == 1 for text in descriptions))
        self.assertEqual(caption.count('Follow Everyday Science'), 1)
        self.assertNotIn('Subscribe to ', caption)
        self.assertNotIn('Explore ', caption)

    def test_preparing_copy_does_not_write_or_change_actual_audio_caption_inputs(self):
        protected = {}
        for filename in ('soundtrack.m4a', 'narration.wav', 'captions.srt', 'captions.vtt'):
            path = self.root/filename
            path.write_bytes(('protected '+filename).encode())
            protected[path] = path.read_bytes()
        before = {path.name for path in self.root.iterdir()}
        package.metadata(self.root, False)
        package.metadata(self.root, True)
        package.instagram_caption(self.root)
        self.assertEqual(before, {path.name for path in self.root.iterdir()})
        for path, data in protected.items():
            self.assertEqual(path.read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
