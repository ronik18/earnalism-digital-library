import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from listening_coverage import verify_coverage
class Coverage(unittest.TestCase):
 def test_overlapping_windows_cover_union_once(self):
  x=verify_coverage(45,[{'start':0,'end':25},{'start':20,'end':45}],30)
  self.assertEqual(x['covered_union_seconds'],45)
 def test_long_input_would_truncate(self):
  with self.assertRaises(ValueError):verify_coverage(93,[{'start':0,'end':93}],30)
 def test_gap_not_hidden_by_overlap_elsewhere(self):
  with self.assertRaises(ValueError):verify_coverage(45,[{'start':0,'end':20},{'start':21,'end':45}],30)
 def test_missing_ending_rejected(self):
  with self.assertRaises(ValueError):verify_coverage(45,[{'start':0,'end':30}],30)
 def test_no_audio_is_not_coverage(self):
  with self.assertRaises(ValueError):verify_coverage(45,[],30)
if __name__=='__main__':unittest.main()
