import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from remix import remix
from studio import mix_score
class RemixTests(unittest.TestCase):
 def test_existing_destination_is_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);dest=p/'keep';dest.mkdir();(dest/'note').write_text('keep')
   with self.assertRaises(FileExistsError):remix(p/'source',dest)
   self.assertEqual((dest/'note').read_text(),'keep')
 def test_incomplete_source_cannot_create_edition(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   with self.assertRaises(ValueError):remix(p,p/'new')
   self.assertFalse((p/'new').exists())
 def test_unbounded_gain_rejected_before_ffmpeg(self):
  with tempfile.TemporaryDirectory() as d:
   for gain in [-7,19]:
    with self.assertRaises(ValueError):mix_score(d,gain)
