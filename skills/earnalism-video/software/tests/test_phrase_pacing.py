import pathlib,sys,tempfile,json,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from audio_derivation import repair_phrases,check_unit,validate_phrase_plan,sha
import test_audio_derivation as fixtures
class PhrasePacingTests(unittest.TestCase):
 def test_repair_preserves_parent_and_rejects_tampering(self):
  with tempfile.TemporaryDirectory() as d:
   src,dst,scene=fixtures.DerivationTests().fixture(pathlib.Path(d));(dst/'raw').mkdir();before=sha(src/'raw/fixture.wav')
   repair_phrases(src,dst,scene,[{'start':0,'end':.6,'tempo':.8},{'start':.6,'end':1.2,'tempo':1.2}]);self.assertEqual(before,sha(src/'raw/fixture.wav'));self.assertEqual(check_unit(dst,'fixture')['derivation']['pitch_shift'],False)
   (dst/'pace-source/raw/fixture.wav').write_bytes(b'tampered')
   with self.assertRaises(ValueError):check_unit(dst,'fixture')
 def test_plan_rejects_gaps_and_excessive_changes(self):
  for plan in [[{'start':0,'end':1,'tempo':.6}],[{'start':.1,'end':1,'tempo':1}],[{'start':0,'end':.9,'tempo':1}]]:
   with self.assertRaises(ValueError):validate_phrase_plan(plan,1)
 def test_existing_audio_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   src,dst,scene=fixtures.DerivationTests().fixture(pathlib.Path(d));(dst/'raw').mkdir();(dst/'raw/fixture.wav').write_bytes(b'keep')
   with self.assertRaises(FileExistsError):repair_phrases(src,dst,scene,[{'start':0,'end':1.2,'tempo':1}])
 def test_whole_passage_slowdown_preserves_measured_tone_pitch(self):
  import array,subprocess,math
  with tempfile.TemporaryDirectory() as d:
   src,dst,scene=fixtures.DerivationTests().fixture(pathlib.Path(d));(dst/'raw').mkdir();before=sha(src/'raw/fixture.wav')
   repair_phrases(src,dst,scene,[{'start':0,'end':1.2,'tempo':.75}])
   def pitch(p):
    values=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-ar','24000','-ac','1','-f','f32le','-']))
    if sys.byteorder!='little':values.byteswap()
    values=values[2400:-2400]
    crossings=sum(a<=0<b for a,b in zip(values,values[1:]));return crossings/(len(values)/24000)
   self.assertLess(abs(pitch(src/'raw/fixture.wav')-pitch(dst/'raw/fixture.wav')),2)
   self.assertEqual(before,sha(src/'raw/fixture.wav'))
   self.assertGreater(check_unit(dst,'fixture')['audio']['duration_seconds'],1.45)
   with self.assertRaisesRegex(ValueError,'stack'):
    other=pathlib.Path(d)/'other';(other/'raw').mkdir(parents=True);repair_phrases(dst,other,scene,[{'start':0,'end':1.2,'tempo':.84}])

 def test_recorded_cycle_case_needs_selective_sentence_repair(self):
  from pace_review import canonical_sentence_rates
  r=json.loads((pathlib.Path(__file__).parent/'fixtures/cycle-pacing-v30.json').read_text())
  def contrast(key):
   rates=canonical_sentence_rates(r[key]['word_times'],r['text'])
   self.assertIsNotNone(rates)
   values=[v['wpm'] for v in rates if v['words']>=6]
   return max(values)/min(values)
  self.assertGreater(contrast('before'),1.5)
  self.assertGreater(contrast('uniform_rejected'),1.5)
  self.assertLessEqual(contrast('repaired'),1.35)
