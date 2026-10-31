"""Exact retained source candidate, not playback/storage or production acceptance."""
import copy,json,unittest
from pathlib import Path
import owner_produced_package as owner
ROOT=Path(__file__).resolve().parents[3]
E=ROOT/'internal/audiobook_lab/release_gate/selfish_giant_music_20261031'
class MusicSuccessorTests(unittest.TestCase):
 def setUp(self):
  self.d=json.loads((E/'release-descriptor.json').read_text());self.p=json.loads((E/'delivery-mapping.json').read_text())
 def test_candidate_admission_uses_actual_shipped_source_registry(self):
  owner.validate(self.d,self.p,'en',owner.DOWNSTREAM)
 def test_default_adoption_remains_dry(self):
  dry=owner.load_adoption('the-selfish-giant');self.assertEqual(dry['identity']['master_wav_sha256'],'f394114ee8a6fd8c798ab84c2f22892632b086f211ad050b870dff38bb6aa6ed');self.assertNotIn('music',dry)
 def test_candidate_requires_exact_identity(self):
  identity={k:self.d[k] for k in ['slug','title','author','controlled_source_sha256','manuscript_sha256','master_wav_sha256','master_mp3_sha256']}
  identity['master_wav_sha256']='1'*64
  with self.assertRaises(owner.OwnerProducedError):owner.load_adoption('the-selfish-giant',identity=identity)
 def test_dry_music_credits_cannot_be_spoofed(self):
  d=copy.deepcopy(self.d);d['music']['credit']['composer']='Someone else'
  with self.assertRaises(owner.OwnerProducedError):owner.validate(d,self.p,'en',owner.DOWNSTREAM)
 def test_credits_cannot_be_omitted(self):
  d=copy.deepcopy(self.d);d.pop('music')
  with self.assertRaises(owner.OwnerProducedError):owner.validate(d,self.p,'en',owner.DOWNSTREAM)
 def test_old_asset_hash_cannot_use_new_mapping(self):
  p=copy.deepcopy(self.p);p['tracks'][0]['chunks'][-1]['assets']['audio']['sha256']='1'*64
  with self.assertRaises(owner.OwnerProducedError):owner.validate(self.d,p,'en',owner.DOWNSTREAM)
 def test_no_storage_or_public_pass(self):
  self.assertFalse(self.d['release_candidate_evidence']['all_release_gates_passed']);self.assertEqual(self.d['known_release_blockers'],owner.DOWNSTREAM)
 def test_mix_evidence_files_match_shipped_hashes(self):
  refs={'music_licence':'music-licence.json','music_suitability':'owner-music-acceptance.json','mix_integrity':'mix-integrity.json','public_music_credits':'public-credits.json'}
  for role,path in refs.items():self.assertEqual(owner.sha((E/path).read_bytes()),self.d['evidence_sha256'][role])
if __name__=='__main__':unittest.main()
