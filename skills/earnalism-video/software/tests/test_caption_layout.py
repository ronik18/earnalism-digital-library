import unittest,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from caption_layout import compose,quality
class CaptionTests(unittest.TestCase):
 def test_short_tail_rejoins_phrase_without_word_loss(self):
  text='So that crescent is not a missing piece. It is a different view of a sunlit round world.'
  words=[dict(word=w,start=i*.45,end=(i+1)*.45) for i,w in enumerate(text.split())]
  result=compose(words)
  self.assertEqual(' '.join(c['text'] for c in result),text)
  self.assertFalse(quality(result));self.assertTrue(all(len(c['text'].split())>1 for c in result))
  boundaries={(w['start'],w['end']) for w in words}
  self.assertTrue(all(any(w['start']==c['start'] for w in words) and any(w['end']==c['end'] for w in words) for c in result))
 def test_unreadable_delivery_rejected(self):
  self.assertTrue(quality([dict(start=0,end=.3,text='piece.')]))
 def test_no_invented_timing_for_impossible_speech(self):
  with self.assertRaisesRegex(ValueError,'readability'):compose([dict(word='impossibly',start=0,end=.1)])
 def test_player_recovery_and_portrait_fit_are_present(self):
  import studio
  template=(studio.BASE/'watch-template.html').read_text()
  self.assertIn('reload-preview',template);self.assertIn('switch-codec',template)
  self.assertIn('video.load()',template);self.assertIn('{{VISUAL_DESCRIPTION}}',template)

 def test_punctuation_restoration_never_changes_a_lexical_word(self):
  from caption_layout import punctuate
  words=[dict(word='earth',start=0,end=1),dict(word='turns',start=1,end=2)]
  fixed=punctuate(words,'Earth turns.')
  self.assertEqual(fixed[0]['start'],0);self.assertEqual(fixed[-1]['end'],2)
  self.assertEqual(fixed[-1]['word'],'turns.')
  self.assertEqual(punctuate(words,'Earth stops.'),words)

 def test_em_dash_preserves_sentence_case_lexical_content_and_timing(self):
  from caption_layout import punctuate
  raw='the fridge moves heat it does not disappear'.split()
  words=[dict(word=w,start=i*.5,end=(i+1)*.5) for i,w in enumerate(raw)]
  fixed=punctuate(words,'The fridge moves heat—it does not disappear.')
  self.assertEqual([w['word'] for w in fixed],['The','fridge','moves','heat—','it','does','not','disappear.'])
  self.assertEqual([(w['start'],w['end']) for w in fixed],[(w['start'],w['end']) for w in words])
  self.assertEqual(' '.join(c['text'] for c in compose(fixed)),'The fridge moves heat—it does not disappear.')
  self.assertEqual(punctuate(words,'The fridge moves light—it does not disappear.'),words)

 def test_brief_adjacent_sentences_choose_valid_merge(self):
  words=[dict(word=w,start=a,end=b) for w,a,b in [('No',0,.4),('bubbles.',.4,.98),('No',.98,1.4),('boiling.',1.4,1.98),('So',1.98,2.5),('where',2.5,2.9),('does',2.9,3.1),('it',3.1,3.3),('go?',3.3,3.6)]]
  result=compose(words)
  self.assertFalse(quality(result))
  self.assertEqual(' '.join(c['text'] for c in result),' '.join(w['word'] for w in words))
  self.assertTrue(all(c['end']-c['start']>=1 for c in result))
