"""Only the four observed notation edits in one hash-bound source are resolvable."""
from pathlib import Path
import copy,json,unittest
from . import assemble
ROOT=Path(__file__).resolve().parents[2]/'output/episodes/07-rainbow/production-v1'
class LiteralDeliveryTests(unittest.TestCase):
 def setUp(self):
  self.groups=assemble.load(ROOT/'units.json');self.scenes=assemble.load(ROOT/'scene-units.json');self.resolution=assemble.load(ROOT/'delivery-resolution.json')
 def validated(self,record=None,groups=None,scenes=None):return assemble.validate_delivery_resolution(ROOT,record or self.resolution,groups or self.groups,scenes or self.scenes)
 def test_exact_literal_and_numeric_notation_only(self):
  r,groups,scenes=self.validated();self.assertEqual(groups[1]['text'],self.groups[1]['text'].replace('colours','colors').replace('forty-two','42'))
  self.assertEqual(groups[2],self.groups[2]);self.assertEqual(scenes[3]['anchors']['angle'],'42 degrees');self.assertFalse(r['publication_approved']);self.assertEqual(r['human_listening'],'PENDING')
 def test_other_addition_omission_substitution_are_rejected(self):
  g=self.groups[1];d=copy.deepcopy(g);d['text']=assemble.literal_delivery_text(g);raw=assemble.load(ROOT/'imported/alignment'/f"{g['id']}.json")
  for text in (raw['recognized']+' magic',raw['recognized'].replace('some reflects','reflects'),raw['recognized'].replace('42','43')):
   changed=copy.deepcopy(raw);changed['recognized']=text
   with self.subTest(text=text),self.assertRaises(ValueError):assemble.validate_literal_alignment(g,d,changed)
 def test_stale_audio_alignment_input_and_extra_group_rejected(self):
  changes=[]
  a=copy.deepcopy(self.resolution);a['groups']['rainbow-connected-02']['audio_sha256']='0'*64;changes.append(a)
  a=copy.deepcopy(self.resolution);a['groups']['rainbow-connected-02']['alignment_sha256']='0'*64;changes.append(a)
  a=copy.deepcopy(self.resolution);a['prepared_inputs']['units.json']='0'*64;changes.append(a)
  a=copy.deepcopy(self.resolution);a['groups']['rainbow-connected-03']={};changes.append(a)
  a=copy.deepcopy(self.resolution);a['archive_sha256']='0'*64;changes.append(a)
  for changed in changes:
   with self.assertRaises(ValueError):self.validated(changed)
 def test_modified_delivered_text_and_in_memory_inputs_rejected(self):
  a=copy.deepcopy(self.resolution);a['groups']['rainbow-connected-01']['delivered_text']+=' A new sentence.'
  with self.assertRaises(ValueError):self.validated(a)
  groups=copy.deepcopy(self.groups);groups[0]['text']=groups[0]['text'].replace('rainbow','reflection')
  with self.assertRaises(ValueError):self.validated(groups=groups)
  scenes=copy.deepcopy(self.scenes);scenes[0]['anchors']['question']='Step toward it'
  with self.assertRaises(ValueError):self.validated(scenes=scenes)
 def test_resolved_display_preserves_every_actual_word_time(self):
  _,delivered,_=self.validated();byid={g['id']:g for g in delivered}
  for g in self.groups:
   if g['id'] not in assemble.LITERAL_SOURCE:continue
   raw=assemble.load(ROOT/'imported/alignment'/f"{g['id']}.json");wav=ROOT/'imported/raw'/f"{g['id']}.wav";source={'audio_sha256':assemble.sha(wav),'duration':assemble.common.probe_wav(wav)['duration']}
   audit,words=assemble.resolved_alignment_audit(g,byid[g['id']],raw,source,ROOT)
   self.assertEqual([(w['start'],w['end']) for w in words],[(w['start'],w['end']) for w in raw['word_times']]);self.assertEqual(audit['raw_differences'],assemble.LITERAL_DIFFERENCES[g['id']]);self.assertEqual(audit['differences'],[]);self.assertFalse(audit['automatic_equivalence_applied']);self.assertEqual(audit['listening'],'PENDING')
if __name__=='__main__':unittest.main()
