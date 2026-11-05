"""First visible mechanism must use its declared actual spoken cause anchor."""
from pathlib import Path
import copy,unittest
from . import assemble

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/'output/episodes/06-sky-colour/production-v1'

class MechanismAnchorTests(unittest.TestCase):
 def setUp(self):
  self.groups=assemble.load(PRE/'units.json');self.scenes=assemble.load(PRE/'scene-units.json')
  self.scenes[1]['anchors']['scatter']='scatter some of that light'
  self.words=[{'word':t,'start':i*.25,'end':i*.25+.2} for i,t in enumerate(assemble.common.tokens(' '.join(s['text'] for s in self.scenes)))]
 def test_explicit_cause_is_mapped_from_actual_words_before_redirect(self):
  assemble.validate_units(self.groups,self.scenes)
  result=assemble.map_scenes(self.scenes,self.words,50.)[1]
  self.assertLess(result['marks']['scatter'],result['marks']['redirect'])
  self.assertEqual(result['start']+result['marks']['scatter'],assemble.common.actual_anchor(self.words,'scatter some of that light'))
 def test_unspoken_or_unsupported_optional_anchor_is_rejected(self):
  wrong=copy.deepcopy(self.scenes);wrong[1]['anchors']['scatter']='an unspoken cause'
  with self.assertRaises(ValueError):assemble.map_scenes(wrong,self.words,50.)
  wrong=copy.deepcopy(self.scenes);wrong[1]['anchors']['estimated_flash']='scatter some of that light'
  with self.assertRaises(ValueError):assemble.validate_units(self.groups,wrong)
 def test_first_cause_cannot_be_moved_after_the_explanation(self):
  wrong=copy.deepcopy(self.scenes);wrong[1]['anchors']['scatter']='more strongly than red'
  with self.assertRaises(ValueError):assemble.map_scenes(wrong,self.words,50.)

if __name__=='__main__':unittest.main()
