import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from music_automation import respace_retimed_plan,transition_check
class RetimedCurveTests(unittest.TestCase):
 def test_small_timing_compression_preserves_gains_and_slew(self):
  p=[{'time':0,'gain_db':0},{'time':5.99,'gain_db':-4},{'time':9.99,'gain_db':-1.333333333}]
  result=respace_retimed_plan(p,11)
  self.assertEqual([k['gain_db'] for k in result],[k['gain_db'] for k in p]);self.assertAlmostEqual(result[1]['time'],6);self.assertFalse(transition_check(result,[])['issues']);self.assertAlmostEqual(p[1]['time'],5.99)
 def test_insufficient_room_or_large_shift_is_rejected(self):
  for p,end in [([{'time':0,'gain_db':0},{'time':5,'gain_db':-4}],10),([{'time':0,'gain_db':0},{'time':5.99,'gain_db':-4}],5.995)]:
   with self.assertRaises(ValueError):respace_retimed_plan(p,end)
 def test_nonfinite_duplicate_or_extra_fields_rejected(self):
  for p in [[{'time':0,'gain_db':0},{'time':1,'gain_db':float('nan')}],[{'time':0,'gain_db':0},{'time':0,'gain_db':0}],[{'time':0,'gain_db':0},{'time':2,'gain_db':0,'extra':1}]]:
   with self.assertRaises(ValueError):respace_retimed_plan(p,10)
