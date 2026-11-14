"""Original tiny synthetic renderer fixtures; never real trained-motion proof."""
import copy
import json
import shutil
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np

try:
    from .learned_rig_render import JOINT_NAMES, background, digest, evaluate_interaction, load_prediction, render, render_frame, viewport
except ImportError:
    from learned_rig_render import JOINT_NAMES, background, digest, evaluate_interaction, load_prediction, render, render_frame, viewport


class LearnedRigRenderTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='rig-render-tests-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.pose=np.array([[0,.9],[0,1.48],[0,1.7],[-.19,1.44],[-.3,1.15],[-.32,.95],
                            [.19,1.44],[.3,1.15],[.32,.95],[-.12,.88],[-.12,.46],[-.12,.03],
                            [.12,.88],[.12,.46],[.12,.03]],dtype=np.float32)
        self.joints=np.repeat(self.pose[None,:,:],24,axis=0)
        for i in range(24):
            self.joints[i,8]=[.32+i*.012,.95+i*.025]
            self.joints[i,7]=[.3+i*.004,1.15+i*.012]
        self.pred=self.root/'fixture-prediction.npz'
        np.savez(self.pred,joints=self.joints,time_seconds=np.arange(24,dtype=np.float32)/24)
        self.model=self.root/'fixture-model.npz';np.savez(self.model,test_only=np.ones((2,2)))
        self.training=self.root/'fixture-training.json'
        self.training.write_text(json.dumps({'synthetic_renderer_fixture_only':True,'training_performed':False}))
        def ref(path):return {'path':str(path),'sha256':digest(path)}
        self.manifest={'schema':'earnalism.learned_motion_prediction.v1','fixture_mode':True,
                       'action':'reach','fps':24,'duration_seconds':1.,'joint_names':JOINT_NAMES,
                       'prediction_file':ref(self.pred),'model':ref(self.model),'training_report':ref(self.training),
                       'provenance':{'prediction_source':'synthetic_test_fixture','teacher_fallback':False}}
        self.path=self.root/'fixture.json';self.save()

    def save(self):self.path.write_text(json.dumps(self.manifest))

    def test_real_encoded_fixture_frames_follow_supplied_wrist_motion(self):
        result=render(self.path,self.root/'rendered')
        self.assertTrue(result['fixture_mode'])
        self.assertEqual(result['state'],'PRIVATE_FIXTURE_RENDERED_NO_TRAINING_EVIDENCE')
        self.assertEqual(result['output']['decode'],'PASS')
        self.assertFalse(result['output']['audio_present'])
        self.assertFalse(result['teacher_fallback_used'])
        self.assertFalse(result['release_approved'])
        self.assertEqual(result['observed_prediction_motion']['moving_joint_count_at_5mm'],2)
        hashes=[still['sha256'] for still in result['stills']]
        self.assertEqual(len(set(hashes)),3)
        with self.assertRaisesRegex(ValueError,'Output exists'):
            render(self.path,self.root/'rendered')

    def test_pose_pixels_change_only_when_prediction_changes(self):
        stage=viewport(self.joints);base=background('reach',stage,'a'*64)
        a=render_frame(self.joints[0],stage,base)
        b=render_frame(self.joints[-1],stage,base)
        repeat=render_frame(self.joints[0],stage,base)
        self.assertEqual(a.tobytes(),repeat.tobytes())
        self.assertNotEqual(a.tobytes(),b.tobytes())
        pixel=(round(self.joints[-1,8,0]*stage['scale']+stage['x_offset']),
               round(stage['y_offset']-self.joints[-1,8,1]*stage['scale']))
        self.assertNotEqual(a.getpixel(pixel),b.getpixel(pixel))
        self.assertTrue(24<pixel[0]<936 and 85<pixel[1]<455)

    def test_missing_model_hash_and_teacher_fallback_reject(self):
        self.manifest['model']['sha256']='0'*64;self.save()
        with self.assertRaisesRegex(ValueError,'checksum'):
            load_prediction(self.path)
        self.manifest['model']['sha256']=digest(self.model)
        self.manifest['provenance']['teacher_fallback']=True;self.save()
        with self.assertRaisesRegex(ValueError,'no teacher fallback'):
            load_prediction(self.path)
        self.manifest['provenance']['teacher_fallback']=False
        self.manifest['provenance']['inverse_kinematics_fallback']=True;self.save()
        with self.assertRaisesRegex(ValueError,'Inverse-kinematics fallback'):
            load_prediction(self.path)

    def test_fixture_cannot_masquerade_as_actual_trained_inference(self):
        self.manifest['fixture_mode']=False;self.save()
        with self.assertRaisesRegex(ValueError,'Actual trained model inference'):
            load_prediction(self.path)

    def test_nonfinite_or_wrong_clock_predictions_reject(self):
        bad=self.joints.copy();bad[3,5,0]=np.nan
        np.savez(self.pred,joints=bad,time_seconds=np.arange(24,dtype=np.float32)/24)
        self.manifest['prediction_file']['sha256']=digest(self.pred);self.save()
        with self.assertRaisesRegex(ValueError,'nonfinite'):
            load_prediction(self.path)
        np.savez(self.pred,joints=self.joints,time_seconds=np.arange(24,dtype=np.float32)/30)
        self.manifest['prediction_file']['sha256']=digest(self.pred);self.save()
        with self.assertRaisesRegex(ValueError,'actual frame clock'):
            load_prediction(self.path)

    def test_fixed_seat_requires_actual_support_and_never_changes_predictions(self):
        manifest=copy.deepcopy(self.manifest)
        manifest.update(action='sit',body={'upper_leg':.43,'lower_leg':.43,'torso':.48,'head_length':.22},
                        interaction_target={'kind':'seat','x':0.,'surface_y':.5,'width':.9,
                                            'declared_before_model_inference':True})
        seated=self.joints.copy()
        for hip,knee,ankle in ((9,10,11),(12,13,14)):
            seated[:,hip,1]=.5
            seated[:,knee]=seated[:,hip]+[.4,0]
            seated[:,ankle]=seated[:,knee]+[0,-.47]
        before=seated.tobytes()
        match=evaluate_interaction(seated,manifest)
        self.assertTrue(match['rendered'])
        self.assertFalse(match['pose_changed'])
        self.assertEqual(seated.tobytes(),before)
        self.assertFalse(evaluate_interaction(self.joints,manifest)['rendered'])
        manifest['interaction_target']['declared_before_model_inference']=False
        self.assertFalse(evaluate_interaction(seated,manifest)['rendered'])

    def test_matched_seat_is_fixed_context_in_pixels_not_a_pose_replacement(self):
        manifest=copy.deepcopy(self.manifest)
        manifest.update(action='sit',body={'upper_leg':.43,'lower_leg':.43,'torso':.48,'head_length':.22},
                        interaction_target={'kind':'seat','x':0.,'surface_y':.5,'width':.9,
                                            'declared_before_model_inference':True})
        seated=self.joints.copy()
        for hip,knee,ankle in ((9,10,11),(12,13,14)):
            seated[:,hip,1]=.5;seated[:,knee]=seated[:,hip]+[.4,0];seated[:,ankle]=seated[:,knee]+[0,-.47]
        stage=viewport(seated);match=evaluate_interaction(seated,manifest)
        plain=background('sit',stage,'a'*64,fixture=True)
        with_seat=background('sit',stage,'a'*64,fixture=True,interaction=match)
        self.assertNotEqual(plain.tobytes(),with_seat.tobytes())
        unsupported=evaluate_interaction(self.joints,manifest)
        omitted=background('sit',stage,'a'*64,fixture=True,interaction=unsupported)
        self.assertEqual(plain.tobytes(),omitted.tobytes())

    def make_small_trained_prediction(self):
        """Actually optimize a tiny network's output bias for a numeric test.

        This is a real bounded parameter update, not a production quality or
        human-motion claim. Inference still uses the maintained full network.
        """
        try:
            from . import motion_model as m
        except ImportError:
            import motion_model as m
        rng=np.random.default_rng(19);hidden=16
        weights={'W0':rng.normal(0,.01,(hidden,len(m.FEATURES))).astype(np.float32),
                 'b0':np.zeros(hidden,np.float32),'W1':rng.normal(0,.01,(hidden,hidden)).astype(np.float32),
                 'b1':np.zeros(hidden,np.float32),'W2':np.zeros((len(m.STATE_NAMES),hidden),np.float32),
                 'b2':np.zeros(len(m.STATE_NAMES),np.float32),
                 'input_mean':np.zeros(len(m.FEATURES),np.float32),
                 'input_std':np.ones(len(m.FEATURES),np.float32),
                 'output_mean':np.array([0.]*10+[.9],np.float32),
                 'output_std':np.ones(len(m.STATE_NAMES),np.float32)*.01}
        initial=self.root/'initial-weights.npz';np.savez(initial,**weights)
        history=[];started=time.monotonic();target=np.ones(len(m.STATE_NAMES),np.float32)*.1
        for step in range(20):
            error=weights['b2']-target
            heldout=m.numpy_predict(weights,np.ones((1,len(m.FEATURES)),np.float32))
            heldout_target=weights['output_mean']+target*weights['output_std']
            history.append({'step':step+1,'training_loss':float(np.mean(error**2)),
                            'validation_loss':float(np.mean(((heldout-heldout_target)/weights['output_std'])**2)),
                            'elapsed_seconds':time.monotonic()-started})
            weights['b2']-=np.float32(.4)*error
        np.savez(self.model,**weights)
        source=self.root/'training-source.py';source.write_bytes(Path(__file__).read_bytes())
        def ref(path):return {'path':str(path),'sha256':digest(path)}
        report={'schema':'earnalism.scratch_motion_training_report.v1',
                'status':'RESEARCH_CHECKPOINT_TRAINED_METRICS_REPORTED','steps':20,'device':'cpu',
                'limits':{'max_steps':20,'max_seconds':90,'batch_size':1},
                'elapsed_seconds':time.monotonic()-started,
                'weights_differ_from_initial':True,'weights':ref(self.model),'initial_weights':ref(initial),
                'source_code':ref(source),'training_history':history,
                'pretrained_weights':False,'teacher_used_at_model_inference':False,
                'parameter_count':sum(weights[k].size for k in weights if k[0] in 'Wb'),
                'test_only':'Actual bias optimization for provenance/numeric replay regression, not motion acceptance.'}
        self.training.write_text(json.dumps(report))
        body=m.character(31);case=m.case_parameters('reach',body,32,duration=1.)
        times=np.arange(24,dtype=np.float32)/24;inputs,root=m.inputs_for_case(body,case,times)
        raw=m.numpy_predict(weights,inputs);state=np.clip(raw,m.LOWER,m.UPPER)
        joints=m.forward_kinematics(state,np.broadcast_to(body,(24,8)),root)
        np.savez(self.pred,joints=joints,time_seconds=times,inputs=inputs,raw_predicted_state=raw,
                 predicted_state=state,root_x=root,body=body)
        self.manifest.update(fixture_mode=False,prediction_file=ref(self.pred),model=ref(self.model),
                             training_report=ref(self.training),case=case,
                             body=dict(zip(m.BODY_NAMES,body.tolist())),
                             provenance={'prediction_source':'trained_model_inference','teacher_fallback':False,
                                         'inverse_kinematics_fallback':False})
        self.save()

    def test_nonfixture_dummy_training_claim_is_rejected(self):
        self.manifest['fixture_mode']=False
        self.manifest['provenance']['prediction_source']='trained_model_inference';self.save()
        with self.assertRaises(ValueError):
            load_prediction(self.path)

    def test_fractional_inference_duration_covers_source_and_loads_on_frame_grid(self):
        try:
            from . import motion_model as m
        except ImportError:
            import motion_model as m
        self.make_small_trained_prediction()
        model_dir=self.root/'trained';model_dir.mkdir()
        shutil.copy2(self.model,model_dir/'weights.npz')
        shutil.copy2(self.training,model_dir/'training-report.json')
        def ref(path):return {'path':str(path),'sha256':digest(path)}
        (model_dir/'model.json').write_text(json.dumps({
            'schema':'earnalism.conditional_skeletal_motion_model.v1','research_only':True,
            'model':ref(model_dir/'weights.npz'),'training_report':ref(model_dir/'training-report.json'),
            'architecture':[len(m.FEATURES),16,16,len(m.STATE_NAMES)],
            'features':m.FEATURES,'state_names':m.STATE_NAMES,'joint_names':m.JOINTS,
            'hierarchy':m.HIERARCHY,'activation':'tanh,tanh,linear','actions':m.ACTIONS}))
        out=self.root/'fractional'
        prediction=m.predict(model_dir,out,action='look',duration=1.001,fps=24)
        actual=load_prediction(out/'prediction.json')
        self.assertEqual(len(actual['joints']),25)
        self.assertEqual(prediction['duration_seconds'],25/24)
        self.assertEqual(prediction['requested_duration_seconds'],1.001)
        self.assertEqual(prediction['case']['duration_seconds'],1.001)
        self.assertGreaterEqual(actual['duration_seconds'],1.001)
        self.assertLess(actual['duration_seconds']-1.001,1/24)
        retained=Path(prediction['source_code']['path'])
        self.assertEqual(retained.parent,out.resolve())
        self.assertEqual(retained.read_bytes(),Path(m.__file__).read_bytes())

    def test_actual_trained_checkpoint_replays_and_forged_joint_pixels_reject(self):
        self.make_small_trained_prediction()
        result=load_prediction(self.path)
        self.assertEqual(result['numeric_validation']['status'],'TRAINED_CHECKPOINT_AND_NUMPY_FK_REPLAY_VERIFIED')
        self.assertLessEqual(result['numeric_validation']['maximum_absolute_errors']['joints'],2e-5)
        with np.load(self.pred,allow_pickle=False) as archive:arrays={k:archive[k].copy() for k in archive.files}
        arrays['joints'][:,8,0]+=.05  # Refreshed digest cannot make an invented wrist a model prediction.
        np.savez(self.pred,**arrays);self.manifest['prediction_file']['sha256']=digest(self.pred);self.save()
        with self.assertRaisesRegex(ValueError,'Predicted joint sequence.*numerical replay'):
            load_prediction(self.path)


if __name__=='__main__':unittest.main()
