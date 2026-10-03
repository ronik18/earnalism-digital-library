import importlib.util
import unittest
from pathlib import Path
P=Path(__file__).with_name('reconcile_english_source_evidence.py')
spec=importlib.util.spec_from_file_location('reconcile_english',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class EvidenceTests(unittest.TestCase):
 def test_id_only_trusted_source_host(self):
  self.assertEqual(m.pg_id('https://www.gutenberg.org/ebooks/84.txt.utf-8'),84)
  self.assertIsNone(m.pg_id('https://evil.example/gutenberg.org/ebooks/84'))
 def test_containment_is_not_full_edition(self):
  r=m.compare([{'id':'one','content':'A short passage.'}], 'Prefix A short passage. Omitted ending.')
  self.assertEqual(r['status'],'ALL_CHAPTERS_MATCH_SOURCE');self.assertFalse(r['complete_edition_proven'])
 def test_punctuation_change_is_not_normalized_away(self):
  self.assertEqual(m.compare([{'id':'one','content':'Book—text.'}], 'Book-text.')['status'],'SOURCE_TEXT_DIFFERS')
 def test_chapter_order_is_strict(self):
  self.assertEqual(m.compare([{'id':'one','content':'First'},{'id':'two','content':'Second'}],'Second First')['status'],'SOURCE_TEXT_DIFFERS')
 def test_empty_is_not_verified(self):
  self.assertEqual(m.compare([], 'Text')['status'],'SOURCE_TEXT_DIFFERS')
 def test_frankenstein_repaired_phrase_is_in_body_not_heading(self):
  chapter=m.load(m.ROOT/'data/controlled_publications/frankenstein/chapters/chapter-015.json')
  self.assertEqual(chapter['title'],'Chapter 11')
  self.assertTrue(chapter['content'].startswith('“It is with considerable difficulty that I remember the original era of'))
  self.assertEqual(chapter['content_hash'],m.sha(chapter['content'].encode()))
 def test_live_titles_excluded_and_alias_preserved(self):
  rows=m.inventory();slugs={r['slug'] for r in rows}
  self.assertNotIn('the-adventures-of-sherlock-holmes',slugs)
  alias=next(r for r in rows if r['slug']=='the-strange-case-of-dr-jekyll-and-mr-hyde')
  self.assertTrue(alias['superseded_alias']);self.assertEqual(alias['canonical_slug'],'jekyll-and-hyde')
 def test_nested_illustration_caption_exclusion(self):
  self.assertEqual(m.strip_illustration_blocks('A [Illustration: image [Copyright 1894]] B'),'A  B')
  with self.assertRaises(ValueError):m.strip_illustration_blocks('A [Illustration: unfinished')
 def test_pride_migration_has_complete_61_chapter_reader(self):
  reader=m.load(m.ROOT/'data/controlled_publications/pride-and-prejudice/reader_manifest.json')
  self.assertEqual(reader['chapter_count'],61)
  self.assertEqual(reader['chapters'][-1]['id'],'chapter-061')
 def test_dracula_restored_preface_order(self):
  reader=m.load(m.ROOT/'data/controlled_publications/dracula/reader_manifest.json')
  self.assertEqual(reader['chapter_count'],28)
  self.assertEqual(reader['chapters'][0]['id'],'chapter-000')
  self.assertEqual(reader['chapters'][0]['order'],1)
 def test_pride_extractor_rejects_incomplete_or_wrong_edition(self):
  with self.assertRaises(ValueError):m.extract_pride_narrative('It is a truth universally acknowledged\nCHAPTER II.\nOnly two.\n*** END OF THE PROJECT GUTENBERG')
 def test_noncover_clearance_history_preserves_audio_denial_and_fail_closed_promotion(self):
  live=set(m.load(m.ROOT/'data/controlled_launch.json').get('live_approved_slugs',[]))
  for clearance in m.load(m.DEFAULT/'noncover_text_clearances.json')['clearances']:
   slug=clearance['slug']
   package=m.ROOT/'data/controlled_publications'/slug
   record=m.load(package/'rights_decision.json');authority=m.load(package/'publication_authorization.json');manifest=m.load(package/'publication_manifest.json')
   is_live=slug in live
   self.assertEqual(record['status'],'ACCEPTED');self.assertEqual(record['territories'],['IN'])
   self.assertNotIn('audio_stream',record['uses']);self.assertNotIn('audio_delivery',record['uses'])
   self.assertFalse(authority['production_activation_authorized_by_this_file'])
   self.assertFalse(authority['audio_authorized']);self.assertFalse(manifest['audio_release']['exposed'])
   if is_live:
    self.assertIn('cover_display',record['uses'])
    self.assertTrue(manifest['reader_release']['exposed']);self.assertEqual(manifest['reader_release']['status'],'APPROVED')
   else:
    self.assertNotIn('cover_display',record['uses'])
    self.assertFalse(manifest['reader_release']['exposed'])
   self.assertNotIn('rights_decision.json',[x['file'] for x in m.load(package/'checksum_manifest.json')['files']])
   for name,digest in record['components'].items():
    component=package/(name+'.json')
    if component.exists():self.assertEqual(digest,m.sha(component.read_bytes()))
    else:self.assertIn(digest,record.get('evidence_sha256',[]))
   ordered=m.load(package/'reader_manifest.json')['chapters']
   chapters=[m.load(package/'chapters'/(x['id']+'.json')) for x in ordered]
   self.assertEqual(authority['content_sha256'],m.sha('\n\n'.join(x['content'] for x in chapters).encode()))
   self.assertEqual(authority['chapter_sha256'],{x['id']:m.sha(x['content'].encode()) for x in chapters})
 def test_whitespace_only_normalization(self):
  self.assertEqual(m.compare([{'id':'one','content':'A\n\nparagraph'}],'A paragraph')['status'],'ALL_CHAPTERS_MATCH_SOURCE')
 def test_missing_chapters_restored_without_hiding_narrative(self):
  live=set(m.load(m.ROOT/'data/controlled_launch.json').get('live_approved_slugs',[]))
  for slug,cid in [('the-principles-of-scientific-management','chapter-004'),('the-suicide-club','chapter-001'),('ward-no-6','chapter-001')]:
   package=m.ROOT/'data/controlled_publications'/slug
   public=m.load(package/'public_book.json');reader=m.load(package/'reader_manifest.json')
   self.assertEqual([x['id'] for x in public['chapters']],[x['id'] for x in reader['chapters']])
   for entry in reader['chapters']:
    chapter=m.load(package/'chapters'/(entry['id']+'.json'))
    self.assertTrue(chapter['content']);self.assertEqual(chapter['content_hash'],m.sha(chapter['content'].encode()))
   restored=m.load(package/'chapters'/(cid+'.json'))
   self.assertGreater(len(restored['content']),10000)
   source=m.load(package/'source_evidence.json')
   self.assertEqual(source['official_electronic_source_verification']['comparison']['status'],'ALL_CHAPTERS_MATCH_SOURCE')
   manifest=m.load(package/'publication_manifest.json');is_live=slug in live
   self.assertEqual(manifest['reader_release']['exposed'],is_live)
   if is_live:
    self.assertEqual(manifest['reader_release']['status'],'APPROVED');self.assertTrue(manifest['reader_release']['cover_url'])
   else:
    self.assertEqual(manifest['reader_release']['status'],'BLOCKED')
 def test_licensed_transcription_has_hash_bound_public_notice(self):
  p=m.ROOT/'data/controlled_publications/the-most-dangerous-game'
  notice=m.load(p/'license_notice.json');book=m.load(p/'public_book.json');chapter=m.load(p/'chapters/chapter-001.json')
  self.assertEqual(notice['license'],'CC-BY-SA-4.0')
  self.assertIn('oldid=12072546',notice['source_url'])
  self.assertTrue(notice['attribution']);self.assertTrue(notice['changes']);self.assertTrue(notice['disclaimer'])
  self.assertEqual(notice['chapter_sha256'],[m.sha(chapter['content'].encode())])
  self.assertEqual(book['license_notice_sha256'],m.sha((p/'license_notice.json').read_bytes()))
 def test_first_party_permission_does_not_reuse_historical_audio_approval(self):
  p=m.ROOT/'data/controlled_publications/bharat-at-the-crossroads'
  authority=m.load(p/'publication_authorization.json');source=m.load(p/'source_evidence.json');decision=m.load(p/'rights_decision.json');approval=m.load(p/'approval_evidence.json')
  self.assertEqual(authority['scope'],'TEXT_READER_ONLY_NON_COVER_COMPONENTS')
  self.assertFalse(authority['audio_authorized']);self.assertFalse(authority['production_activation_authorized_by_this_file'])
  self.assertEqual(source['source_type'],'original_work_internal_admin_source')
  self.assertIn('permission',decision['basis'].lower())
  self.assertEqual(approval['historical_admin_import_claim']['approval_scope'],'explicit_owner_approved_audio_only_release')
 def test_hungry_stones_is_selected_translator_not_whole_anthology(self):
  p=m.ROOT/'data/controlled_publications/hungry-stones';source=m.load(p/'source_evidence.json')
  self.assertEqual(len(m.load(p/'reader_manifest.json')['chapters']),1)
  facts=source['text_component_clearance']['lifetime_publication_evidence']
  self.assertEqual(facts['translators'][0]['name'],'Panna Lal Basu')
  self.assertEqual(facts['translators'][0]['death_year'],1956)
  self.assertIn('not whole mixed-translator anthology',facts['basis'])
 def test_copyrighted_wyllie_translation_stays_held(self):
  p=m.ROOT/'data/controlled_publications/the-metamorphosis';source=m.load(p/'source_evidence.json')
  self.assertFalse(source['commercial_use_allowed'])
  self.assertTrue(source['text_license_review']['explicit_copyrighted_notice'])
  self.assertFalse(m.load(p/'publication_manifest.json')['reader_release']['exposed'])
  self.assertNotEqual(m.load(p/'rights_decision.json').get('status'),'ACCEPTED')
 def test_milverton_whole_story_includes_opening_narrative_and_card(self):
  p=m.ROOT/'data/controlled_publications/the-adventure-of-charles-augustus-milverton'
  chapter=m.load(p/'chapters/chapter-001.json');source=m.load(p/'source_evidence.json')
  self.assertTrue(chapter['content'].startswith('It is years since the incidents'))
  self.assertIn('CHARLES AUGUSTUS MILVERTON,',chapter['content'])
  self.assertTrue(chapter['content'].endswith('as we turned away from the window.'))
  boundary=source['text_component_clearance']['whole_work_boundary_evidence']
  self.assertEqual(boundary['content_sha256'],m.sha(chapter['content'].encode()))
  self.assertEqual(boundary['source_sha256'],source['source_hash'])
if __name__=='__main__':unittest.main()
