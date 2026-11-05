"""Observed source-bound delivery text revisions, never generic ASR cleanup."""
from pathlib import Path
import copy,json,tempfile,shutil,unittest
from . import assemble
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output/episodes/06-sky-colour/production-v1'
class DeliveryRevisionTests(unittest.TestCase):
 def prepared(self):
  return assemble.load(SOURCE/'units.json'),assemble.load(SOURCE/'scene-units.json')
 def stage(self,root):
  for n in ['units.json','scene-units.json','delivery-resolution.json']:(root/n).write_bytes((SOURCE/n).read_bytes())
  for gid in ['sky-connected-01','sky-connected-02']:
   for branch,suffix in [('raw','.wav'),('alignment','.json')]:
    source=SOURCE/'imported'/branch/(gid+suffix);dest=root/'imported'/branch/(gid+suffix);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
  (root/'delivery-evidence').mkdir();shutil.copy2(SOURCE/'delivery-evidence/independent-asr-group02-output.txt',root/'delivery-evidence/independent-asr-group02-output.txt')
 def test_actual_observed_revisions_are_explicit_and_preserve_originals(self):
  groups,scenes=self.prepared();before={n:assemble.sha(SOURCE/n) for n in ['units.json','scene-units.json','imported/alignment/sky-connected-01.json','imported/alignment/sky-connected-02.json']}
  resolution,delivered,semantic=assemble.load_delivery_resolution(SOURCE,groups,scenes)
  self.assertIn('visible colors.',delivered[0]['text']);self.assertIn('sunlight scatter toward you',delivered[1]['text'])
  self.assertIn('scatter toward you',semantic[2]['anchors']['toward']);self.assertIn('visible colors',semantic[1]['anchors']['mixed'])
  self.assertEqual(before,{n:assemble.sha(SOURCE/n) for n in before})
  for original,accepted in zip(groups[:2],delivered[:2]):
   raw=assemble.load(SOURCE/'imported/alignment'/f"{original['id']}.json");wav=SOURCE/'imported/raw'/f"{original['id']}.wav"
   source={'audio_sha256':assemble.sha(wav),'duration':assemble.common.probe_wav(wav)['duration']};audit,words=assemble.delivery_audit(original,accepted,raw,source,resolution,SOURCE)
   self.assertTrue(audit['raw_differences']);self.assertTrue(audit['original_differences']);self.assertFalse(audit['differences']);self.assertFalse(audit['automatic_equivalence_applied']);self.assertEqual(audit['listening'],'PENDING');self.assertTrue(audit['resolution']['not_ASR_equivalence'])
 def test_unexpected_accepted_addition_or_omission_is_blocked(self):
  groups,scenes=self.prepared()
  for edit in [lambda s:s+' Buy now.',lambda s:s.replace('the Sun','Sun',1)]:
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);self.stage(root);d=assemble.load(root/'delivery-resolution.json');r=d['groups']['sky-connected-02'];r['accepted_delivery_text']=edit(r['accepted_delivery_text']);r['accepted_delivery_text_sha256']=assemble.hashlib.sha256(r['accepted_delivery_text'].encode()).hexdigest();(root/'delivery-resolution.json').write_text(json.dumps(d))
    with self.assertRaises(ValueError):assemble.load_delivery_resolution(root,groups,scenes)
 def test_changed_audio_or_alignment_binding_is_blocked(self):
  groups,scenes=self.prepared()
  for which in ['audio','alignment']:
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);self.stage(root)
    if which=='audio':
     p=root/'imported/raw/sky-connected-02.wav';p.write_bytes(p.read_bytes()+b'changed')
    else:
     p=root/'imported/alignment/sky-connected-02.json';d=assemble.load(p);d['recognized']=d['recognized'].replace('different path','same path');p.write_text(json.dumps(d))
     r=assemble.load(root/'delivery-resolution.json');r['groups']['sky-connected-02']['alignment_sha256']=assemble.sha(p);(root/'delivery-resolution.json').write_text(json.dumps(r))
    with self.assertRaises(ValueError):assemble.load_delivery_resolution(root,groups,scenes)
 def test_pending_or_broader_override_never_passes(self):
  groups,scenes=self.prepared()
  for mode in ['pending','extra_group','changed_second_evidence']:
   with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);self.stage(root);d=assemble.load(root/'delivery-resolution.json')
    if mode=='pending':d['state']='PENDING'
    elif mode=='extra_group':d['groups']['sky-connected-03']=d['groups']['sky-connected-02']
    else:(root/'delivery-evidence/independent-asr-group02-output.txt').write_text('changed')
    (root/'delivery-resolution.json').write_text(json.dumps(d))
    with self.assertRaises(ValueError):assemble.load_delivery_resolution(root,groups,scenes)
if __name__=='__main__':unittest.main()
