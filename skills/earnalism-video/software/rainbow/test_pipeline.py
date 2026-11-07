"""Engineering fixtures only; no generated/listened media or release acceptance."""
from pathlib import Path
import copy,hashlib,json,tempfile,unittest
from unittest.mock import patch
from html.parser import HTMLParser
from . import assemble,pipeline,package_preview
from ..sky_colour.finish import shoulder
ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'output/episodes/07-rainbow/production-v1'
class RainbowPipelineTests(unittest.TestCase):
 def setUp(self):
  self.groups=json.loads((PREP/'units.json').read_text());self.scenes=json.loads((PREP/'scene-units.json').read_text())
 def fixture_words(self):
  words=[]
  for i,word in enumerate(' '.join(s['text'] for s in self.scenes).split()):words.append({'word':word,'start':i*.3,'end':(i+1)*.3})
  return words
 def test_production_input_groups_are_exact_and_complete(self):
  assemble.validate_units(self.groups,self.scenes)
  self.assertEqual(hashlib.sha256(' '.join(x['text'] for x in self.groups).encode()).hexdigest(),'4cb9dbfd9e832834782ffdf918af5891aff66f62338077addea6d9a1d4198a37')
 def test_missing_staging_anchor_and_estimated_timing_are_rejected(self):
  broken=copy.deepcopy(self.scenes);del broken[0]['anchors']['change']
  with self.assertRaises(ValueError):assemble.validate_units(self.groups,broken)
  broken=copy.deepcopy(self.scenes);broken[0]['start']=0
  with self.assertRaises(ValueError):assemble.validate_units(self.groups,broken)
 def test_actual_word_mapping_crosses_generation_boundaries(self):
  words=self.fixture_words();scenes=assemble.map_scenes(self.scenes,words,len(words)*.3)
  self.assertEqual(len(scenes),7);self.assertEqual(scenes[0]['start'],0)
  self.assertAlmostEqual(scenes[-1]['end'],len(words)*.3)
  self.assertTrue(all(a['end']==b['start'] for a,b in zip(scenes,scenes[1:])))
  words[5]['word']='wrong'
  with self.assertRaises(ValueError):assemble.map_scenes(self.scenes,words,len(words)*.3)
 def test_bounded_original_acoustic_plan_preserves_authored_rests(self):
  words=self.fixture_words();t={'duration':len(words)*.3,'scenes':assemble.map_scenes(self.scenes,words,len(words)*.3)};plan=pipeline.phrase_plan(t)
  self.assertTrue(plan['events']);self.assertEqual(plan['publication_approved'],False)
  for event in plan['events']:
   self.assertFalse(any(a<=event['time']<=b for a,b in plan['quiet_intervals']))
  for a,b in plan['quiet_intervals']:
   self.assertEqual(shoulder((a+b)/2,plan['quiet_intervals']),0)
  self.assertFalse(any(e['time']>=t['scenes'][-1]['start'] for e in plan['events']))
 def test_builder_is_disabled_isolated_and_idempotent(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'units.json').write_text(json.dumps(self.groups));pipeline.build(p)
   source=(p/'colab-launch.py').read_text();compile(source,'launch','exec')
   self.assertIn('RUN_RAINBOW = False',source);self.assertIn('EXISTING_COMPUTE_ALLOWED = False',source)
   self.assertIn('/content/earnalism-rainbow-v1',source);self.assertIn('threading.Timer(1500,runtime.unassign)',source)
   before={x.name:x.read_bytes() for x in p.iterdir()};pipeline.build(p);self.assertEqual(before,{x.name:x.read_bytes() for x in p.iterdir()})
 def test_destination_metadata_remains_private_and_caption_specific(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'sources.json').write_text(json.dumps([{'title':'Test scientific source','url':'https://example.org/rainbow'}]))
   for portrait in (False,True):
    m=package_preview.metadata(p,portrait);self.assertEqual(m['privacyStatus'],'private');self.assertFalse(m['upload_automatically']);self.assertFalse(m['publication_approved'])
    self.assertIn('#earnalism #learnalism',m['description']);self.assertEqual(m['english_captions'],'captions.srt')
   self.assertEqual(package_preview.metadata(p,True)['video'],'clean-shorts/video.mp4')
   self.assertIn('#earnalism #learnalism',package_preview.instagram_caption(p))
 def test_both_player_pages_render_full_and_join_listening_without_stale_links(self):
  class Media(HTMLParser):
   def __init__(self):super().__init__();self.audio=[];self.links=[]
   def handle_starttag(self,tag,attrs):
    value=dict(attrs)
    if tag=='audio':self.audio.append(value)
    if tag=='a':self.links.append(value.get('href',''))
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'sources.json').write_text(json.dumps([{'title':'Fixture research','url':'https://example.org/rainbow'}]));(p/'transcript.txt').write_text('A private engineering fixture.');(p/'props.json').write_text(json.dumps({'captions':[{'start':0,'end':1,'text':'A fixture.'}]}))
   clips=[{'join_time':join,'variant':variant,'path':f'listening/{join}-{variant}.wav'} for join in (15.68,42.48,68.08) for variant in ('dry','scored')]
   with patch.object(package_preview,'join_listening_clips',return_value=clips):
    for portrait in (False,True):
     text=package_preview.page(p,portrait);media=Media();media.feed(text)
     self.assertEqual(len(media.audio),8);self.assertEqual(text.count('id="listening-details"'),1)
     self.assertIn('15.68-second transition',text);self.assertIn('not proof of an audible defect',text)
     self.assertIn('#listening-details',media.links);self.assertNotIn('landscape-narration-only.mp4',media.links)
     self.assertIn('Keep the Sun behind you',text);self.assertNotIn('patch of sky send sunlight',text)
 def test_join_clip_paths_cannot_escape_private_candidate(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);(p/'mix-provenance.json').write_text(json.dumps({'body_duration':90.48}));(p/'listening-clips.json').write_text(json.dumps({'clips':[{'path':'../outside.wav'}]}))
   with self.assertRaises(ValueError):package_preview.join_listening_clips(p)
if __name__=='__main__':unittest.main()
