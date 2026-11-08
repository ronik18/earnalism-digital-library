"""Verify the exact 45-title Reader addition without granting audio or broader rights."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from datetime import datetime, timezone
from backend.rights_decision_gate import evaluate_accepted_record, record_sha256
from scripts.catalogue_clearance_release_bindings import assert_reviewed_authority, assert_current_reviewed_release, REVIEWED_AUTHORITY
ROOT = Path(__file__).resolve().parents[1]
REGISTRY = 'backend/data/rights_decision_registry.json'
REF = 'persisted45_reader_successor_20261108'
HELD = {'gitanjali', 'nishkriti', 'the-metamorphosis'}
def read(path): return json.loads((ROOT/path).read_text())
def sha(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
class ReaderSuccessorTests(unittest.TestCase):
    def setUp(self):
        self.baseline = read(REVIEWED_AUTHORITY)
        ref = self.baseline[REF]
        self.assertEqual(sha(ref['path']), ref['sha256'])
        self.receipt = read(ref['path'])
        self.slugs = set(self.receipt['slugs'])
        self.assertEqual(len(self.slugs), 45)
        self.assertFalse(self.slugs & HELD)
    def prior(self, path):
        entry = self.receipt['preserved_predecessor_files'][path]
        self.assertEqual(sha(entry['path']), entry['sha256'])
        original = subprocess.check_output(['git','show',self.receipt['parent_source_head']+':'+path],cwd=ROOT)
        self.assertEqual((ROOT/entry['path']).read_bytes(),original)
        return read(entry['path'])
    def test_registry_addition_is_exact_and_audio_permissions_are_unchanged(self):
        prior = self.prior(REGISTRY)
        current = read(REGISTRY)
        added = self.receipt['added_accepted_records']
        self.assertEqual(len(added), 45)
        self.assertFalse(set(added) & set(prior['accepted_records']))
        expected = copy.deepcopy(prior)
        expected['accepted_records'].update(added)
        self.assertEqual(current, expected)
    def test_previous_titles_and_launch_controls_are_preserved(self):
        previous = self.prior(REVIEWED_AUTHORITY)
        self.assertEqual(len(previous['titles']), 52)
        self.assertEqual(set(self.baseline['titles']) - set(previous['titles']), self.slugs)
        for slug, binding in previous['titles'].items():
            self.assertEqual(self.baseline['titles'][slug], binding)
        for path in ['data/controlled_launch.json', 'backend/data/controlled_launch.json']:
            old = self.prior(path)
            expected = copy.deepcopy(old)
            expected['live_approved_slugs'] += self.receipt['slugs']
            # Ordering carries no permission; compare membership separately.
            current = read(path)
            self.assertEqual(set(current['live_approved_slugs']), set(expected['live_approved_slugs']))
            self.assertEqual(len(current['live_approved_slugs']), 97)
            expected['live_approved_slugs'] = current['live_approved_slugs']
            expected['title_access_modes'].update({s:'COMMERCIAL_ENTITLEMENT' for s in self.slugs})
            self.assertEqual(current, expected)
            self.assertFalse(set(current['live_approved_slugs']) & HELD)
    def test_new_titles_pass_exact_reader_scope_and_deny_audio_foreign_and_tampered_rights(self):
        baseline = assert_reviewed_authority(ROOT)
        registry = read(REGISTRY)
        for slug in sorted(self.slugs):
            package = assert_current_reviewed_release(ROOT, slug, baseline)
            record = json.loads((package/'rights_decision.json').read_text())
            self.assertEqual(self.receipt['added_accepted_records'][record['decision_id']], record_sha256(record))
            self.assertEqual(set(record['uses']), {'catalog_metadata','cover_display','reader_preview','reader_delivery','reading_pass_session','reading_pass_renewal'})
            for country, trusted, use, allowed in [('IN',True,'reader_delivery',True),('US',True,'reader_delivery',False),('IN',False,'reader_delivery',False),('IN',True,'audio_stream',False),('IN',True,'audio_download',False)]:
                verdict = evaluate_accepted_record(record, edition_id=slug, operator_id='reo-enterprise',country=country,country_trusted=trusted,use=use,required_components=record['components'],accepted_records=registry['accepted_records'],revoked_decision_ids=frozenset(registry['revoked_decision_ids']),now=datetime.now(timezone.utc))
                self.assertIs(verdict.passed,allowed,(slug,country,use,verdict.reasons))
            changed = copy.deepcopy(record);changed['territories'].append('US')
            verdict = evaluate_accepted_record(changed,edition_id=slug,operator_id='reo-enterprise',country='IN',country_trusted=True,use='reader_delivery',required_components=changed['components'],accepted_records=registry['accepted_records'],revoked_decision_ids=frozenset(),now=datetime.now(timezone.utc))
            self.assertFalse(verdict.passed)
    def test_original_manuscripts_and_held_packages_are_byte_preserved(self):
        parent = self.receipt['parent_source_head']
        for slug in self.slugs:
            package = ROOT/'data/controlled_publications'/slug
            for chapter in (package/'chapters').glob('*.json'):
                relative = str(chapter.relative_to(ROOT))
                old = subprocess.check_output(['git','show',parent+':'+relative],cwd=ROOT)
                self.assertEqual(chapter.read_bytes(),old,relative)
            old = subprocess.check_output(['git','show',parent+':data/controlled_publications/'+slug+'/rights_decision.json'],cwd=ROOT)
            self.assertEqual((package/'historical-noncover-rights-decision.json').read_bytes(),old)
        for slug in HELD:
            for prefix in ['data/controlled_publications/','backend/data/controlled_publications/']:
                self.assertEqual(subprocess.check_output(['git','diff',parent,'--',prefix+slug],cwd=ROOT),b'')
    def test_bootstrap_adds_only_exact_titles_and_preserves_existing_rows(self):
        path = 'backend/data/approved_reader_bootstrap.json'
        old = self.prior(path);current = read(path)
        self.assertEqual(current['titles'][:len(old['titles'])],old['titles'])
        added = current['titles'][len(old['titles']):]
        self.assertEqual({r['slug'] for r in added},self.slugs)
        self.assertEqual(len(added),45)
        for row in added:
            binding = self.baseline['titles'][row['slug']]
            self.assertEqual(row,{'slug':row['slug'],'decision_id':binding['decision_id'],'record_sha256':binding['record_sha256']})
        expected = copy.deepcopy(old);expected['titles'] = current['titles']
        self.assertEqual(current,expected)
if __name__ == '__main__': unittest.main()
