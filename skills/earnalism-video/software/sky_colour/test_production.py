"""Focused no-generation regressions; synthetic times are test data only."""
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
from . import assemble,build_colab,finish,package,release
ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/'output/episodes/06-sky-colour/production-v1'
class SkyProductionTests(unittest.TestCase):
 def setUp(self):
  self.groups=assemble.load(PRE/'units.json');self.scenes=assemble.load(PRE/'scene-units.json')
 def fake_words(self):
  return [{'word':t,'start':i*.25,'end':i*.25+.20} for i,t in enumerate(assemble.common.tokens(' '.join(g['text'] for g in self.groups)))]
 def test_four_connected_groups_preserve_all_six_semantic_beats(self):
  assemble.validate_units(self.groups,self.scenes)
  self.assertEqual([len(g['text'].split()) for g in self.groups],[51,44,53,50])
  wrong=copy.deepcopy(self.groups);wrong[0]['text']=wrong[0]['text'].replace('Blue','Red',1)
  with self.assertRaises(ValueError):assemble.validate_units(wrong,self.scenes)
 def test_worker_limits_and_complete_thoughts_not_relaxed(self):
  wrong=copy.deepcopy(self.groups);wrong[0]['text']='word '*65+'word.'
  with self.assertRaises(ValueError):assemble.validate_units(wrong)
  wrong=copy.deepcopy(self.groups);wrong[0]['text']='x'*521+'.'
  with self.assertRaises(ValueError):assemble.validate_units(wrong)
  wrong=copy.deepcopy(self.groups);wrong[0]['text']=wrong[0]['text'].rstrip('.')
  with self.assertRaises(ValueError):assemble.validate_units(wrong)
 def test_semantic_scenes_follow_ASR_inside_connected_group(self):
  words=self.fake_words();scenes=assemble.map_scenes(self.scenes,words,50.)
  self.assertEqual(scenes[1]['start'],7.5)
  self.assertNotEqual(scenes[1]['start'],51*.25)
  self.assertEqual(len(scenes),6);self.assertEqual(scenes[-1]['end'],50.)
  self.assertEqual(scenes[1]['marks']['mixed'],0.)
 def test_missing_ambiguous_and_subword_anchors_block(self):
  words=self.fake_words();bad=copy.deepcopy(words);bad[0]['word']='mistake'
  with self.assertRaises(ValueError):assemble.map_scenes(self.scenes,bad,50.)
  bad_scenes=copy.deepcopy(self.scenes);bad_scenes[0]['anchors']['question']='Sun'
  with self.assertRaises(ValueError):assemble.map_scenes(bad_scenes,words,50.)
  merged=copy.deepcopy(words);merged[29]['word']+=' '+merged[30]['word'];merged[29]['end']=merged[30]['end'];del merged[30]
  with self.assertRaises(ValueError):assemble.map_scenes(self.scenes,merged,50.)
 def test_colab_builder_has_new_paths_disabled_flags_and_reused_guard(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);(p/'units.json').write_text(json.dumps(self.groups));build_colab.build(p)
   launcher=(p/'colab-launch.py').read_text();nb=json.loads((p/'Earnalism_Everyday_Science_06_Narration.ipynb').read_text())
   self.assertIn('RUN_SKY_COLOUR = False',launcher);self.assertIn('EXISTING_COMPUTE_ALLOWED = False',launcher)
   self.assertIn("if 'sky_colour_shutdown_guard' not in globals():",launcher)
   self.assertIn('/content/earnalism-sky-colour-v1',launcher);self.assertNotIn('/content/earnalism-condensation-v1',launcher)
   self.assertTrue(all(c.get('execution_count') is None and not c.get('outputs') for c in nb['cells'] if c['cell_type']=='code'))
 def test_original_B_recipe_and_worker_are_pinned(self):
  baseline,_=assemble.common.published_b_reference();self.assertEqual(baseline['segments'][0]['speaker'],'Ryan');self.assertEqual(baseline['segments'][0]['seed'],20261028)
  self.assertEqual(baseline['generation']['temperature'],.85);self.assertEqual(assemble.common.WORKER_SHA256,'55500c69d0529ded866c744d5242d1c9320625bece8eb56958b8086948e2beeb')
 def test_score_uses_actual_anchors_with_rest_zeros(self):
  scenes=assemble.map_scenes(self.scenes,self.fake_words(),50.);t={'duration':50.,'scenes':scenes};p=finish.phrase_plan(t)
  self.assertTrue(p['events']);self.assertEqual(p['listening'],'PENDING');self.assertFalse(p['publication_approved'])
  for r in p['rests']:
   self.assertEqual(finish.shoulder((r['start']+r['end'])/2,p['quiet_intervals']),0.)
   self.assertFalse(any(r['start']<=e['time']<=r['end'] for e in p['events']))
  p2=copy.deepcopy(t);p2['scenes'][3]['marks'].pop('predict')
  with self.assertRaises(ValueError):finish.phrase_plan(p2)
 def test_first_post_rest_motif_retained_even_while_fade_in_is_quiet(self):
  timeline={'duration':50.,'scenes':assemble.map_scenes(self.scenes,self.fake_words(),50.)};p=finish.phrase_plan(timeline)
  scene=timeline['scenes'][1];expected=[finish.mark(scene,'mixed')+.55+i*.17 for i in range(3)]
  actual=[e['time'] for e in p['events'] if e['instrument']=='piano' and any(abs(e['time']-x)<1e-9 for x in expected)]
  self.assertEqual(actual,expected)
  self.assertTrue(all(finish.shoulder(t,p['quiet_intervals'])<.08 for t in expected))
  for rest in p['rests']:
   self.assertFalse(any(rest['start']<=e['time']<=rest['end'] for e in p['events']))
 def test_rendered_test_score_keeps_literal_rest_interiors_zero(self):
  # Acoustic test only, not production narration or video. Leave one measurable
  # phrase outside overlapping rest shoulders so EBU R128 can measure it.
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);rests=[[0.,1.],[10.,11.],[23.,24.]]
   p={'duration':24.,'events':[{'time':t,'midi':64,'instrument':'piano','velocity':.25,'duration':5.8,'pan':-.1} for t in (1.55,6.)], 'quiet_intervals':rests,'fade_out_seconds':3.2,'fade_in_seconds':4.5}
   finish.render_score(root,p);pcm=finish.pcm(root/'score.wav')
   for a,b in rests:
    interior=pcm[round((a+.01)*48000)*2:round((b-.01)*48000)*2]
    self.assertEqual(max(abs(v) for v in interior),0.)
 def test_static_master_gain_respects_peak_cap_and_finite_measurements(self):
  self.assertAlmostEqual(finish.choose_static_score_gain({'input_i':-47.,'input_tp':-31.}),17.)
  self.assertAlmostEqual(finish.choose_static_score_gain({'input_i':-50.,'input_tp':-20.}),11.)
  for value in (float('nan'),float('inf'),-float('inf')):
   with self.assertRaises(ValueError):finish.choose_static_score_gain({'input_i':value,'input_tp':-20.})
 def test_static_master_preserves_identical_phrases_and_rejects_gain_drift(self):
  import array,math,subprocess
  rate=48000
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);data=array.array('f',[0.])*(rate*12*2)
   phrase=array.array('f')
   for i in range(round(rate*1.6)):
    t=i/rate;value=.035*math.sin(2*math.pi*440*t)*min(1,t/.012)*math.exp(-t*2)
    phrase.extend((value,value))
   for at in (3.,8.):
    first=round(at*rate)*2;data[first:first+len(phrase)]=phrase
   source=root/'input.wav';output=root/'master.wav'
   subprocess.run(['ffmpeg','-v','error','-n','-f','f32le','-ar',str(rate),'-ac','2','-i','-','-c:a','pcm_f32le',str(source)],input=data.tobytes(),check=True)
   proof=finish.master_score(source,output);actual=finish.pcm(output)
   first,second=round(3*rate)*2,round(8*rate)*2
   self.assertEqual(actual[first:first+len(phrase)],actual[second:second+len(phrase)])
   self.assertEqual(max(abs(x) for x in actual[:rate*2*2]),0.)
   self.assertTrue(proof['constant_gain_verification']['constant_gain_verified']);self.assertFalse(proof['adaptive_gain']);self.assertEqual(proof['listening'],'PENDING')
   # A time-varying gain must fail, even if the resulting track has ample peak
   # headroom. This recreates the defect without altering a production master.
   altered=array.array('f',actual)
   for i in range(second,len(altered)):altered[i]*=.5
   bad=root/'gain-drift.wav'
   subprocess.run(['ffmpeg','-v','error','-n','-f','f32le','-ar',str(rate),'-ac','2','-i','-','-c:a','pcm_f32le',str(bad)],input=altered.tobytes(),check=True)
   with self.assertRaises(ValueError):finish.verify_static_score_gain(source,bad,proof['gain_db'])
 def test_package_copy_is_sky_specific_and_private(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);(p/'sources.json').write_text(json.dumps({'sources':[{'title':'NASA Sky','url':'https://spaceplace.nasa.gov/blue-sky/en/'}]}));m=package.metadata(p,True)
   self.assertEqual(m['privacyStatus'],'private');self.assertFalse(m['upload_automatically']);self.assertFalse(m['publication_approved'])
   self.assertEqual(m['video'],'clean-shorts/video.mp4');self.assertIn('#earnalism #learnalism',m['description'])
   self.assertNotIn('glass',m['description'].lower());self.assertIn('sky',m['title'].lower())
 def test_fixed_mix_routing_preserves_same_dry_voice_component(self):
  # A generated tone is test data only, not narration or an audition.
  import array,math,subprocess,sys
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);tone=array.array('f',(0.1*math.sin(2*math.pi*220*i/48000) for i in range(12000)));zero=array.array('f',[0.])*24000
   for name,data,channels in [('v.wav',tone,1),('s.wav',zero,2)]:
    subprocess.run(['ffmpeg','-v','error','-n','-f','f32le','-ar','48000','-ac',str(channels),'-i','-','-c:a','pcm_f32le',str(p/name)],input=data.tobytes(),check=True)
   subprocess.run(['ffmpeg','-v','error','-n','-i',str(p/'v.wav'),'-i',str(p/'s.wav'),'-filter_complex',finish.MIX_FILTER,'-map','[a]','-ar','48000','-ac','2','-c:a','pcm_f32le',str(p/'m.wav')],check=True)
   finish.run(*finish.append_ident_command(p/'v.wav',finish.IDENT_ROOT/'source-sound.wav',p/'dry.wav',8/30))
   mixed=finish.pcm(p/'m.wav');dry=finish.pcm(p/'dry.wav')
   self.assertEqual(mixed,dry[:len(mixed)])
   self.assertTrue(finish.verify_ident_tail(p/'dry.wav',finish.IDENT_ROOT/'source-sound.wav',12800)['exact_decoded_pcm_match'])
 def test_release_requires_sky_schema_and_never_infers_publication(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);r=root/'candidate';r.mkdir();path=r/'delivery-manifest.json'
   with patch.object(release,'sha',return_value=release.ORIGINAL_SHA),patch.object(release,'validate_inputs'):
    path.write_text(json.dumps({'schema':'earnalism.condensation-private-kit.v1','publication_approved':False,'files':{}}))
    with self.assertRaises(ValueError):release.check_private(r,root)
    path.write_text(json.dumps({'schema':'earnalism.sky-colour-private-kit.v1','publication_approved':False,'files':{}}))
    self.assertFalse(release.check_private(r,root)['publication_approved'])
    path.write_text(json.dumps({'schema':'earnalism.sky-colour-private-kit.v1','publication_approved':True,'files':{}}))
    with self.assertRaises(ValueError):release.check_private(r,root)
 def test_fresh_assembly_refuses_partial_outputs(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)
   for n in ['units.json','scene-units.json','baseline-job.json','generation-plan.json']:(p/n).write_bytes((PRE/n).read_bytes())
   (p/'.sky-assembly-lock.json').write_text('{}')
   with self.assertRaises(ValueError):assemble.assemble(p)
if __name__=='__main__':unittest.main()
