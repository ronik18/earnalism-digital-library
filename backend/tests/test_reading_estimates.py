import json
import tempfile
import unittest
from pathlib import Path

from backend.reading_estimates import artifact_reading_estimate, text_word_count


class ReadingEstimatesTests(unittest.TestCase):
    def test_bengali_conjuncts_and_inline_markup(self):
        self.assertEqual(text_word_count('<p>ক্ষুধিত পাষাণ</p><p>বি<strong>চারক</strong> বাংলা।</p>'), 4)

    def test_non_reader_code_and_punctuation_are_excluded(self):
        self.assertEqual(text_word_count('<p>one&nbsp;two — •</p><script>three four</script><style>five</style>'), 2)

    def test_full_edition_and_cache_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'chapters').mkdir()
            chapters = [{'id': 'first', 'word_count': 1, 'is_preview': True}, {'id': 'last', 'word_count': 1}]
            for c in chapters:
                (root / 'chapters' / (c['id'] + '.json')).write_text(json.dumps({'content': '<p>' + 'বাংলা ' * 476 + '</p>'}))
            self.assertEqual(artifact_reading_estimate(root, chapters), {'estimated_reading_time': '4 min'})
            (root / 'chapters/last.json').write_text(json.dumps({'content': '<p>' + 'বাংলা ' * 952 + '</p>'}))
            self.assertEqual(artifact_reading_estimate(root, chapters), {'estimated_reading_time': '6 min'})

    def test_missing_or_empty_is_unknown_not_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(artifact_reading_estimate(directory, [{'id': 'missing'}]), {'estimated_reading_time': ''})
            self.assertEqual(artifact_reading_estimate(directory, []), {'estimated_reading_time': ''})

    def test_estimate_never_uses_unlisted_files(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'chapters').mkdir()
            (Path(directory) / 'chapters/other.json').write_text('{"content":"unlisted text"}')
            self.assertEqual(artifact_reading_estimate(directory, []), {'estimated_reading_time': ''})

    def test_bad_id_is_rejected(self):
        self.assertEqual(artifact_reading_estimate('.', [{'id': '../other'}]), {'estimated_reading_time': ''})

    def test_live_loaders_override_stale_estimate_without_mutating_artifacts(self):
        from backend.catalog_truth import load_controlled_artifact_book
        root = Path(__file__).resolve().parents[2] / 'data/controlled_publications'
        for slug, expected in [('muchiram-gurer-jibanchorit', '27 min'), ('dracula', '673 min')]:
            with self.subTest(slug=slug):
                source = root / slug / 'public_book.json'
                before = source.read_bytes()
                book = load_controlled_artifact_book(slug)
                self.assertIsNotNone(book)
                self.assertEqual(book['estimated_reading_time'], expected)
                self.assertEqual(source.read_bytes(), before)
                self.assertTrue(all('content' not in c for c in book['chapters']))


if __name__ == '__main__':
    unittest.main()
