import unittest
from scripts.reconcile_bengali_source_evidence import paragraphs, difference, fold

class BengaliSourceReconciliationTests(unittest.TestCase):
    def test_inline_spacing_is_retained(self):
        p,_=paragraphs('<div class="prp-pages-output"><p>আমি <i>আজ</i> যাব।</p></div>','গল্প')
        self.assertEqual(p,['আমি আজ যাব।'])
    def test_direct_transcluded_literary_nodes_are_not_dropped(self):
        html='<div class="prp-pages-output"><div class="wikisource-header-template">Source furniture</div>First literary paragraph.<div class="wst-nop"></div><span>Second</span> literary paragraph.<p>Third paragraph.</p></div>'
        actual,_=paragraphs(html,'Title')
        self.assertEqual(actual,['First literary paragraph.','Second literary paragraph.','Third paragraph.'])

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
                current_hash=hashlib.sha256(chapter['content'].encode()).hexdigest()
                if current_hash!=row['content_sha256']:
                    repair_file=root/'internal/legal/catalogue_clearance_20261002/bengali/multichapter-narrow-source-repairs.json'
                    repairs=json.loads(repair_file.read_text())['repairs']
                    expected=row['content_sha256']
                    for later in repairs:
                        if later['slug']==record['slug'] and later['chapter']==row['id'] and later['before_sha256']==expected:expected=later['after_sha256']
                    self.assertEqual(expected,current_hash)
                else:self.assertEqual(current_hash,row['content_sha256'])
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
        source=json.loads((root/'internal/legal/catalogue_clearance_20261002/bengali/muchiram-gurer-jibanchorit-multichapter-source-comparison.json').read_text())
        self.assertEqual(manifest['chapter_count'],14)
        self.assertEqual(manifest['preview_chapter_ids'],['chapter-001','chapter-002'])
        for i,row in enumerate(source['comparisons'],1):
            chapter=json.loads((package/f'chapters/chapter-{i:03d}.json').read_text())
            self.assertEqual(difference(chapter['content'],row['source_paragraphs_for_reader'])['status'],'EXACT_MATCH_FORMATTING_ONLY')
            self.assertEqual(chapter['content_hash'],hashlib.sha256(chapter['content'].encode()).hexdigest())

class FullRenderedNotesTests(unittest.TestCase):
    def test_literary_text_after_transclusion_is_not_discarded(self):
        body, _ = paragraphs('<div class="mw-parser-output"><div class="prp-pages-output"><p>First page</p></div><p>Final printed page</p></div>', 'Title')
        self.assertEqual(body, ['First page', 'Final printed page'])

    def test_literary_table_text_is_not_discarded(self):
        body, _ = paragraphs('<div class="prp-pages-output"><p>Prose</p><table><tr><td>Poem line one</td><td>Poem line two</td></tr></table></div>', 'Title')
        self.assertIn('Poem line one', ' '.join(body))
        self.assertIn('Poem line two', ' '.join(body))

    def test_original_footnotes_outside_transclusion_are_preserved(self):
        body, furniture = paragraphs('<div class="mw-parser-output"><div class="prp-pages-output"><p>Original prose</p></div><ol class="references"><li><span class="reference-text">Original author note</span></li></ol></div>', 'Title')
        self.assertEqual(body, ['Original prose', '↑ Original author note'])
        self.assertEqual(furniture, [])

class FinalClearanceBindingsTests(unittest.TestCase):
    def test_local_text_decisions_bind_current_bytes_without_audio_and_preserve_fail_closed_promotion(self):
        import json, hashlib
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        report=json.loads((root/'internal/legal/catalogue_clearance_20261002/bengali/local-text-clearances.json').read_text())
        live=set(json.loads((root/'data/controlled_launch.json').read_text()).get('live_approved_slugs',[]))
        self.assertEqual(report['count'],16)
        for row in report['titles']:
            package=root/'data/controlled_publications'/row['slug']
            decision=json.loads((package/'rights_decision.json').read_text())
            manifest=json.loads((package/'publication_manifest.json').read_text())
            is_live=row['slug'] in live
            self.assertEqual(decision['status'],'ACCEPTED')
            self.assertEqual(decision['territories'],['IN'])
            self.assertNotIn('audio_delivery',decision['uses'])
            self.assertNotIn('audio_stream',decision['uses'])
            self.assertFalse(manifest['audio_release']['exposed'])
            if is_live:
                self.assertIn('cover_display',decision['uses'])
                self.assertTrue(manifest['reader_release']['exposed'])
                self.assertEqual(manifest['reader_release']['status'],'APPROVED')
            else:
                self.assertNotIn('cover_display',decision['uses'])
                self.assertFalse(manifest['reader_release']['exposed'])
            required_components={'public_book','reader_manifest','source_evidence','approval_evidence','checksum_manifest','publication_manifest'}
            self.assertTrue(required_components.issubset(decision['components']))
            for name,value in decision['components'].items():
                component=package/(name+'.json')
                if component.exists():
                    self.assertEqual(value,hashlib.sha256(component.read_bytes()).hexdigest())
                else:
                    self.assertNotIn(name,required_components)
                    self.assertRegex(value,r'^[0-9a-f]{64}$')
            auth=json.loads((package/'publication_authorization.json').read_text())
            self.assertFalse(auth['audio_authorized'])
            self.assertFalse(auth['production_activation_authorized_by_this_file'])
            self.assertIn('TEXT_READER',auth['scope'])
            if is_live:
                self.assertTrue(auth.get('publication_authorized'))
            else:
                self.assertEqual(auth['scope'],'TEXT_READER_ONLY')
            notice=json.loads((package/'license_notice.json').read_text())
            chapters=sorted([json.loads(f.read_text())for f in (package/'chapters').glob('*.json')],key=lambda c:c['order'])
            self.assertEqual(notice['chapter_sha256'],[hashlib.sha256(c['content'].encode()).hexdigest()for c in chapters])

    def test_original_replacements_preserve_auditable_old_identity(self):
        import json, hashlib
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        for slug in ['book-95624627d5','book-5aedda79fe','book-a23625bf36']:
            receipt=json.loads((root/f'internal/legal/catalogue_clearance_20261002/bengali/{slug}-original1894-edition-migration.json').read_text())
            chapter=json.loads(next((root/'data/controlled_publications'/slug/'chapters').glob('*.json')).read_text())
            self.assertEqual(receipt['new_chapter_sha256'],hashlib.sha256(chapter['content'].encode()).hexdigest())
            self.assertNotEqual(receipt['chapter_sha256'],receipt['new_chapter_sha256'])
            self.assertEqual(len(receipt['base_git_commit']),40)
            self.assertNotIn('content',receipt)

if __name__=='__main__': unittest.main()
)
            auth=json.loads((package/'publication_authorization.json').read_text())
            self.assertFalse(auth['audio_authorized'])
            self.assertFalse(auth['production_activation_authorized_by_this_file'])
            self.assertIn('TEXT_READER',auth['scope'])
            if is_live:
                self.assertTrue(auth.get('publication_authorized'))
            else:
                self.assertEqual(auth['scope'],'TEXT_READER_ONLY')
            notice=json.loads((package/'license_notice.json').read_text())
            chapters=sorted([json.loads(f.read_text())for f in (package/'chapters').glob('*.json')],key=lambda c:c['order'])
            self.assertEqual(notice['chapter_sha256'],[hashlib.sha256(c['content'].encode()).hexdigest()for c in chapters])

    def test_original_replacements_preserve_auditable_old_identity(self):
        import json, hashlib
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        for slug in ['book-95624627d5','book-5aedda79fe','book-a23625bf36']:
            receipt=json.loads((root/f'internal/legal/catalogue_clearance_20261002/bengali/{slug}-original1894-edition-migration.json').read_text())
            chapter=json.loads(next((root/'data/controlled_publications'/slug/'chapters').glob('*.json')).read_text())
            self.assertEqual(receipt['new_chapter_sha256'],hashlib.sha256(chapter['content'].encode()).hexdigest())
            self.assertNotEqual(receipt['chapter_sha256'],receipt['new_chapter_sha256'])
            self.assertEqual(len(receipt['base_git_commit']),40)
            self.assertNotIn('content',receipt)

if __name__=='__main__': unittest.main()
