import unittest
from scripts.reconcile_bengali_source_evidence import paragraphs, difference, fold

class BengaliSourceReconciliationTests(unittest.TestCase):
    def test_inline_spacing_is_retained(self):
        p,_=paragraphs('<div class="prp-pages-output"><p>আমি <i>আজ</i> যাব।</p></div>','গল্প')
        self.assertEqual(p,['আমি আজ যাব।'])
    def test_source_furniture_removed_and_recorded(self):
        p,f=paragraphs('<div class="prp-pages-output"><p>গল্প</p><p>আসল কথা।</p><p>১৩২১</p></div>','বই/গল্প')
        self.assertEqual(p,['আসল কথা।'])
        self.assertEqual(len(f),2)
        self.assertIn('not_verified_first_publication',f[-1]['kind'])
    def test_missing_paragraph_is_not_matching(self):
        d=difference('প্রথম।\n\nশেষ।',['প্রথম।','হারানো।','শেষ।'])
        self.assertEqual(d['status'],'SOURCE_RECONCILIATION_REQUIRED')
        self.assertEqual(d['changes'][0]['source'],['হারানো।'])
    def test_punctuation_difference_not_normalized_away(self):
        self.assertNotEqual(fold("ক'রে"),fold('ক’রে'))
    def test_unchanged_text_passes_formatting_only(self):
        self.assertEqual(difference('প্রথম।\n\nশেষ।',['প্রথম।',' শেষ। '])['status'],'EXACT_MATCH_FORMATTING_ONLY')


class AppliedSourceRepairIntegrityTests(unittest.TestCase):
    def test_chapter_order_repairs_preserve_literary_hashes(self):
        import json, hashlib
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        evidence=root/'internal/legal/catalogue_clearance_20261002/bengali/chapter-order-repairs.json'
        if not evidence.exists():self.skipTest('No appliedchapterorderevidence in thischeckout')
        for record in json.loads(evidence.read_text())['repairs']:
            package=root/'data/controlled_publications'/record['slug']
            book=json.loads((package/'public_book.json').read_text())
            reader=json.loads((package/'reader_manifest.json').read_text())
            self.assertEqual([c['id'] for c in book['chapters']],[c['id'] for c in record['after_order']])
            n=record['preview_chapter_count_preserved']
            self.assertEqual(reader['preview_chapter_ids'],[c['id']for c in book['chapters'][:n]])
            for row in record['after_order']:
                chapter=json.loads((package/'chapters'/(row['id']+'.json')).read_text())
                self.assertEqual(hashlib.sha256(chapter['content'].encode()).hexdigest(),row['content_sha256'])
                self.assertEqual(chapter['order'],row['order'])

    def test_no_ambiguous_khata_first_publication_year_is_certified(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        source=root/'data/controlled_publications/book-0deb35c750/source_evidence.json'
        if not source.exists():self.skipTest('No held Bengali package')
        row=json.loads(source.read_text())
        if row.get('original_publication_evidence',{}).get('status')=='DISPUTED_NOT_AN_ACCEPTED_FIRST_YEAR':
            self.assertNotIn('original_publication_year',row)

class MuchiramCompletenessTest(unittest.TestCase):
    def test_fourteen_source_chapters_and_original_preview_are_bound(self):
        import json,hashlib
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        package=root/'data/controlled_publications/muchiram-gurer-jibanchorit'
        manifest=json.loads((package/'reader_manifest.json').read_text())
        source=json.loads((root/'internal/legal/catalogue_clearance_20261002/bengali/muchiram-fourteen-chapter-source-comparison.json').read_text())
        self.assertEqual(manifest['chapter_count'],14)
        self.assertEqual(manifest['preview_chapter_ids'],['chapter-001','chapter-002'])
        for i,row in enumerate(source['chapters'],1):
            chapter=json.loads((package/f'chapters/chapter-{i:03d}.json').read_text())
            self.assertEqual(difference(chapter['content'],row['paragraphs'])['status'],'EXACT_MATCH_FORMATTING_ONLY')
            self.assertEqual(chapter['content_hash'],hashlib.sha256(chapter['content'].encode()).hexdigest())

if __name__=='__main__': unittest.main()
