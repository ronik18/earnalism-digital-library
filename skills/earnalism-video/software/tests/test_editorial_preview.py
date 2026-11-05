import pathlib,unittest
class EditorialPreviewTests(unittest.TestCase):
 def test_sources_remain_accessible_without_visible_video_downloads(self):
  page=(pathlib.Path(__file__).resolve().parents[1]/'watch-template.html').read_text()
  self.assertNotIn(' download',page)
  self.assertIn('nodownload',page)
  self.assertIn('{{SOURCES}}',page)
  self.assertIn('{{DISCLOSURE}}',page)
  self.assertIn('{{DIAGRAM_CONTEXT}}',page)
  self.assertIn('id="replay-preview"',page)
  self.assertNotIn('EARNALISM — SEE DIFFERENTLY.',page)
  self.assertNotIn('copy-proof',page)

 def test_external_delivery_keeps_diagram_context_and_source_references(self):
  import sys
  sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
  from studio import youtube_metadata
  r=youtube_metadata({'topic':'Why does the Moon have phases?','diagram_context':'Illustrative schematics, not to scale. Earth-view disk orientation uses a northern-hemisphere convention.','sources':[{'url':'https://science.nasa.gov/moon/moon-phases/'}]})
  self.assertIn('northern-hemisphere convention',r['description'])
  self.assertIn('not to scale',r['description'])
  self.assertIn('https://science.nasa.gov',r['description'])
