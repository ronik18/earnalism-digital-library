import pathlib,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from comparison_review import rgb_difference,compare_frames
class ComparisonTests(unittest.TestCase):
 def test_identical_and_changed_bytes_are_not_an_audience_score(self):
  self.assertEqual(rgb_difference(b'\x00\x50\xff',b'\x00\x50\xff'),0)
  self.assertEqual(rgb_difference(b'\x00'*3,b'\xff'*3),255)
  with patch('comparison_review.subprocess.check_output',side_effect=[b'\x00'*6,b'\x00'*3+b'\xff'*3]):r=compare_frames('a','b',1,1)
  self.assertEqual([f['rgb_difference_0_255'] for f in r['frames']],[0,255]);self.assertEqual(r['audience_preference'],'UNKNOWN');self.assertFalse(r['human_approval'])
 def test_rejects_unaligned_or_incomplete_frames(self):
  for data in [(b'123',b'123456'),(b'12',b'12'),(b'',b'')]:
   with patch('comparison_review.subprocess.check_output',side_effect=data),self.assertRaises(ValueError):compare_frames('a','b',1,1)
if __name__=='__main__':unittest.main()
