import pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio
class StableMediaRetry(unittest.TestCase):
 def test_metadata_only_failure_retries_once_against_same_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'movie.mp4';p.write_bytes(b'fixed source bytes');record={'sha256':studio.sha(p)}
   with patch('studio._verify_media_once',side_effect=[ValueError('Media changed during verification'),record]) as attempt:r=studio.verify_media(p)
   self.assertEqual(attempt.call_count,2);self.assertTrue(r['metadata_only_retry'])
 def test_actual_content_change_never_retries(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'movie.mp4';p.write_bytes(b'original')
   def change(*args):p.write_bytes(b'changed');raise ValueError('Media changed during verification')
   with patch('studio._verify_media_once',side_effect=change) as attempt,self.assertRaises(ValueError):studio.verify_media(p)
   self.assertEqual(attempt.call_count,1)
 def test_other_errors_and_repeated_instability_remain_failures(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'movie.mp4';p.write_bytes(b'original')
   for errors,count in [([ValueError('Silent soundtrack')],1),([ValueError('Media changed during verification')]*2,2)]:
    with patch('studio._verify_media_once',side_effect=errors) as attempt,self.assertRaises(ValueError):studio.verify_media(p)
    self.assertEqual(attempt.call_count,count)
