import unittest,sys,tempfile,subprocess,wave,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from music_automation import validate_plan,apply
class PlanOverrideTests(unittest.TestCase):
 def test_valid_combined_phrase_plan(self):
  self.assertEqual(validate_plan([{'time':0,'gain_db':-2},{'time':6,'gain_db':1}],8)[1]['gain_db'],1)
 def test_bad_bounds_slew_order_and_nonfinite_rejected(self):
  for p in [[{'time':0,'gain_db':9},{'time':6,'gain_db':0}],[{'time':0,'gain_db':0},{'time':1,'gain_db':2}],[{'time':2,'gain_db':0},{'time':1,'gain_db':0}],[{'time':0,'gain_db':float('nan')},{'time':6,'gain_db':0}]]:
   with self.assertRaises(ValueError):validate_plan(p,8)
 def test_invalid_override_does_not_rename_or_write_source(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   for n in ['narration.wav','score-ducked.wav']:
    with wave.open(str(p/n),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\0\0'*48000)
   raw=(p/'score-ducked.wav').read_bytes()
   with self.assertRaises(ValueError):apply(p,[{'time':0,'gain_db':0},{'time':1,'gain_db':4}])
   self.assertEqual((p/'score-ducked.wav').read_bytes(),raw);self.assertFalse((p/'score-ducked-before-automation.wav').exists())
 def test_already_automated_source_is_rejected_before_mutation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'score-ducked.wav').write_bytes(b'current');(p/'score-ducked-before-automation.wav').write_bytes(b'original')
   with self.assertRaises(FileExistsError):apply(p)
   self.assertEqual((p/'score-ducked.wav').read_bytes(),b'current');self.assertEqual((p/'score-ducked-before-automation.wav').read_bytes(),b'original')
if __name__=='__main__':unittest.main()
