import unittest,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from caption_preview import label_timeline
class CaptionSafePreview(unittest.TestCase):
 def test_label_key_waits_for_each_spoken_anchor(self):
  rows=label_timeline({'scenes':[{'diagram':'phases','start':30,'end':53,'anchors':[{'phrase':'At first quarter','time':37},{'phrase':'First quarter means','time':42},{'phrase':'Near full Moon','time':48}]}]})
  at=lambda t:next(r['text'] for r in rows if r['start']<=t<r['end'])
  self.assertNotIn('¼',at(42));self.assertIn('¼',at(43));self.assertNotIn('¼',at(49));self.assertIn('Almost fully lit',at(49))
 def test_shell_contains_caption_rail_and_fullscreen_uses_shell(self):
  s=(pathlib.Path(__file__).resolve().parents[1]/'watch-template.html').read_text()
  self.assertIn('id="caption-safe-area"',s);self.assertIn('shell.requestFullscreen()',s);self.assertIn("track.mode='hidden'",s)
  self.assertIn('controlsList="nofullscreen nodownload"',s)
  self.assertLess(s.index('</video>'),s.index('id="caption-safe-area"'))

 def test_fullscreen_overrides_portrait_width_cap_and_keeps_replay(self):
  s=(pathlib.Path(__file__).resolve().parents[1]/'watch-template.html').read_text()
  self.assertIn('max-height:none;max-width:100%',s);self.assertIn('display:flex;flex-direction:column',s);self.assertIn('id="replay-preview"',s)

 def test_orbit_key_does_not_name_observer_view_before_it_arrives(self):
  rows=label_timeline({'scenes':[{'diagram':'orbit','start':0,'end':12,'anchors':[{'phrase':'From the ground','time':3}]}]})
  at=lambda t:next(r['text'] for r in rows if r['start']<=t<r['end'])
  self.assertNotIn('FROM EARTH',at(4));self.assertIn('FROM EARTH',at(5))

 def test_quarter_key_clears_at_visual_transition_without_gaps(self):
  rows=label_timeline({'scenes':[{'diagram':'phases','start':30,'end':53,'anchors':[{'phrase':'At first quarter','time':37},{'phrase':'First quarter means','time':42},{'phrase':'Near full Moon','time':48}]}]})
  for a,b in zip(rows,rows[1:]):self.assertEqual(a['end'],b['start'])
  at=lambda t:next(r['text'] for r in rows if r['start']<=t<r['end'])
  self.assertIn('¼',at(47.19))
  for t in (47.2,47.54,47.99):
   self.assertNotIn('¼',at(t));self.assertNotIn('Almost fully lit',at(t));self.assertIn('Changing view',at(t))
  self.assertIn('Almost fully lit',at(48))

 def test_companion_cards_limit_reading_load_and_preserve_timing(self):
  from caption_preview import reading_cards
  quarter=reading_cards('Diagram key: ¼ of the cycle → ½ of the visible disk')
  self.assertEqual([c['value'] for c in quarter['cards']],['¼ of the cycle','½ of the visible disk'])
  self.assertEqual(quarter['note'],'')
  changing=reading_cards('Diagram key: FROM ABOVE · FROM EARTH · Sunlight · Changing view')
  self.assertEqual(len(changing['cards']),2);self.assertIn('Changing view',changing['note'])
  before=reading_cards('Diagram key: FROM ABOVE · Sunlight')
  self.assertEqual(len(before['cards']),1)
 def test_cards_stay_outside_video_and_caption_area_and_use_safe_text(self):
  s=(pathlib.Path(__file__).resolve().parents[1]/'watch-template.html').read_text()
  self.assertIn('showDiagram(entry)',s);self.assertIn('span.textContent=text',s)
  self.assertIn('if(entry===lastDiagramEntry)return',s)
  self.assertIn('minmax(min(140px,100%),1fr)',s)
  self.assertLess(s.index('id="caption-text"'),s.index('id="diagram-key"'))
