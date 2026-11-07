import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from participant_preview import make
class ParticipantPreviewTests(unittest.TestCase):
 def test_first_viewer_surface_does_not_expose_answers_or_sidebar(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);page='<video width="1920" height="1080" poster="landscape.png"><source src="landscape-preview.mp4?v=7"></video><section aria-labelledby="visual-heading">ANSWER SIDEBAR</section><details><summary>Two quick understanding checks</summary><details>ANSWER KEY</details></details><details><summary>Transcript and source</summary>TRANSCRIPT</details></main>'
   (p/'watch.html').write_text(page);(p/'portrait-short.html').write_text(page);make(p)
   for name in ['participant.html','participant-shorts.html']:
    text=(p/name).read_text();self.assertNotIn('ANSWER',text);self.assertNotIn('TRANSCRIPT',text)
   self.assertIn('portrait-preview.mp4', (p/'participant-shorts.html').read_text());self.assertEqual((p/'watch.html').read_text(),page)

 def test_new_study_view_does_not_resume_a_previous_participant(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);template=(pathlib.Path(__file__).resolve().parents[1]/'watch-template.html').read_text();(p/'watch.html').write_text(template);make(p)
   page=(p/'participant.html').read_text();self.assertIn('bind(video,0);',page);self.assertNotIn('const stored=sessionStorage.getItem(key)',page)
