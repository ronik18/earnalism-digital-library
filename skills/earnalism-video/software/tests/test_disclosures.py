import json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import studio

class DisclosureTests(unittest.TestCase):
 def test_prepare_discloses_without_authorizing_publication(self):
  episode=studio.BASE/'episodes/private-test.json'
  defaults=studio.load(studio.BASE/'config/defaults.json')
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)
   studio.write(root/'config/defaults.json',defaults)
   with patch.object(studio,'BASE',root),patch.object(studio,'verify_original'):
    folder=studio.prepare(episode)
   metadata=studio.load(folder/'youtube.json')
   self.assertIn(studio.VIDEO_DISCLOSURE,metadata['description'])
   for source in studio.load(episode)['sources']:
    self.assertIn(source['url'],metadata['description'])
   self.assertEqual(metadata['privacyStatus'],'private')
   self.assertIs(metadata['upload_automatically'],False)
   review=studio.load(folder/'review.json')
   self.assertEqual(review['reviewer'],'')
   for field in ('factual','rights','voice','audiovisual','technical','delivery'):
    self.assertIs(review[field],False)
   with self.assertRaisesRegex(ValueError,'never publish'):studio.release_check(folder)

 def test_both_watch_formats_show_disclosure_and_keep_sources_escaped(self):
  with tempfile.TemporaryDirectory() as d:
   folder=pathlib.Path(d)
   studio.write(folder/'episode.json',{'topic':'Moon <test>','scenes':[{'text':'An illustration.'}],'sources':[{'publisher':'Research <source>','url':'https://example.com/?a=1&b=2'}]})
   (folder/'landscape.mp4').touch()
   studio.draft_watch(folder)
   for name in ('watch.html','portrait-short.html'):
    page=(folder/name).read_text()
    self.assertIn('data-production-disclosure>'+studio.PLAYER_DISCLOSURE,page)
    self.assertLess(page.index('</video>'),page.index(studio.PLAYER_DISCLOSURE))
    self.assertLess(page.index(studio.PLAYER_DISCLOSURE),page.index('<details'))
    self.assertIn('Research &lt;source&gt;',page)
    self.assertIn('a=1&amp;b=2',page)
    self.assertIn('noindex,nofollow',page)
    self.assertNotIn('{{DISCLOSURE}}',page)
    self.assertNotIn('Original instrumental score',page)
   self.assertIn('portrait-preview.mp4?v=7',(folder/'portrait-short.html').read_text())

if __name__=='__main__':unittest.main()
