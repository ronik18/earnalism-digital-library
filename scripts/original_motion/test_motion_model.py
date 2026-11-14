"""Research-model safeguards and actual original-data geometry tests."""
import tempfile
import unittest
import importlib.util
import json
from pathlib import Path
import numpy as np
try:
    from . import motion_model as m
except ImportError:
    import motion_model as m


class MotionTests(unittest.TestCase):
    def test_original_walk_teacher_really_plants_feet_in_world(self):
        body=m.character(101);case=m.case_parameters('walk',body,202)
        times=np.linspace(0,3,180,dtype=np.float32)
        x,root=m.inputs_for_case(body,case,times);state,contact=m.teacher_trajectory(body,case,times)
        j=m.forward_kinematics(state,np.broadcast_to(body,(len(times),8)),root)
        for foot,index in ((0,11),(1,14)):
            indices=np.flatnonzero(contact[:,foot]);groups=np.split(indices,np.where(np.diff(indices)>1)[0]+1)
            for g in groups:
                if len(g)>1:self.assertLess(float(np.linalg.norm(j[g,index]-j[g[0],index],axis=-1).max()),1e-5)

    def test_original_reach_reaches_requested_target(self):
        body=m.character(31);case=m.case_parameters('reach',body,32)
        times=np.linspace(0,3,60);x,root=m.inputs_for_case(body,case,times)
        state,_=m.teacher_trajectory(body,case,times);j=m.forward_kinematics(state,np.broadcast_to(body,(len(times),8)),root)
        target=np.array([case['target_x'],.94*(body[0]+body[1])+case['target_y']])
        self.assertLess(float(np.linalg.norm(j[-1,8]-target)),1e-5)

    def test_v2_corrects_standing_crouch_in_data_with_same_case_inputs(self):
        body=m.character(31);case=m.case_parameters('idle',body,32);times=np.linspace(0,3,60)
        old,_=m.teacher_trajectory(body,case,times,'v1');new,_=m.teacher_trajectory(body,case,times,'v2')
        self.assertLess(float(np.mean(np.abs(new[:,[7,9]]))),float(np.mean(np.abs(old[:,[7,9]])))*.4)
        _,root=m.inputs_for_case(body,case,times)
        joints=m.forward_kinematics(new,np.broadcast_to(body,(len(times),8)),root)
        self.assertLess(float(np.max(np.abs(joints[:,[11,14],1]))),1e-5)

    def test_v2_walk_support_is_world_planted_without_inference_ik(self):
        body=m.character(101);case=m.case_parameters('walk',body,202);times=np.linspace(0,3,180)
        _,root=m.inputs_for_case(body,case,times);state,contact=m.teacher_trajectory(body,case,times,'v2')
        joints=m.forward_kinematics(state,np.broadcast_to(body,(len(times),8)),root)
        for foot,index in ((0,11),(1,14)):
            indices=np.flatnonzero(contact[:,foot]);groups=np.split(indices,np.where(np.diff(indices)>1)[0]+1)
            for group in groups:
                if len(group)>1:self.assertLess(float(np.linalg.norm(joints[group,index]-joints[group[0],index],axis=-1).max()),1e-5)

    def test_v2_seat_height_is_predeclared_body_context(self):
        body=m.character(101);case=m.case_parameters('sit',body,202);times=np.linspace(0,3,60)
        state,_=m.teacher_trajectory(body,case,times,'v2')
        self.assertAlmostEqual(float(state[-1,10]),float(.55*(body[0]+body[1])),places=6)

    def test_whole_character_and_trajectory_splits(self):
        arrays,meta=m.make_dataset(characters=9,variants=1,frames=16)
        sets=[{x['character_id'] for x in meta['trajectories'] if x['split']==name}
              for name in ('train','validation','test')]
        self.assertFalse(sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
        for sid in np.unique(arrays['trajectory_id']):
            self.assertEqual(len(np.unique(arrays['split'][arrays['trajectory_id']==sid])),1)
        self.assertFalse(meta['captured_or_downloaded_training_material'])

    def test_unknown_action_has_no_teacher_or_semantic_fallback(self):
        with self.assertRaises(ValueError):m.case_parameters('fly',m.character(1),2)

    def test_fk_keeps_lengths_for_arbitrary_learned_angles(self):
        body=m.character(71);states=np.random.default_rng(3).normal(0,.5,(20,11)).astype(np.float32)
        j=m.forward_kinematics(states,np.broadcast_to(body,(20,8)),np.zeros(20))
        for a,b,length in ((9,10,body[0]),(10,11,body[1]),(6,7,body[2]),(7,8,body[3])):
            np.testing.assert_allclose(np.linalg.norm(j[:,b]-j[:,a],axis=-1),length,rtol=2e-6,atol=2e-6)

    @unittest.skipUnless(importlib.util.find_spec('torch'),'existing PyTorch needed for training-only checks')
    def test_training_controls_and_output_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):m.train(Path(folder)/'bad',max_steps=10001)
            with self.assertRaises(ValueError):m.train(folder,max_steps=1)

    @unittest.skipUnless(importlib.util.find_spec('torch'),'existing PyTorch needed for differentiable training check')
    def test_differentiable_rig_matches_numpy_and_has_finite_gradient(self):
        import torch
        body=m.character(101);case=m.case_parameters('reach',body,202);times=np.linspace(0,3,24)
        state,_=m.teacher_trajectory(body,case,times,'v2');bodies=np.broadcast_to(body,(len(times),8)).copy()
        prediction=torch.tensor(state,requires_grad=True)
        actual=m.torch_forward_kinematics(prediction,torch.tensor(bodies))
        expected=m.forward_kinematics(state,bodies,np.zeros(len(times)))
        np.testing.assert_allclose(actual.detach().numpy(),expected,atol=2e-6,rtol=2e-6)
        actual.square().mean().backward();self.assertTrue(bool(torch.isfinite(prediction.grad).all()))

    @unittest.skipUnless(importlib.util.find_spec('torch'),'existing PyTorch needed for genuine provenance fixture')
    def test_genuine_training_report_cannot_qualify_replaced_weights_or_source(self):
        # A real one-step scratch run supplies the receipt; no fabricated
        # training boolean or hand-authored PASS is used for this regression.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);run=root/'genuine'
            m.train(run,characters=6,variants=1,frames=16,hidden=16,
                    max_steps=1,max_seconds=30,batch_size=32)
            m.predict(run,root/'genuine-prediction',action='reach')
            original_model=(run/'model.json').read_bytes()
            trained=(run/'weights.npz').read_bytes()
            (run/'weights.npz').write_bytes((run/'initial-weights.npz').read_bytes())
            resealed=json.loads(original_model);resealed['model']['sha256']=m.sha(run/'weights.npz')
            m.write_json(run/'model.json',resealed)
            with self.assertRaisesRegex(ValueError,'report weights checksum'):
                m.predict(run,root/'must-not-exist')
            self.assertFalse((root/'must-not-exist').exists())
            (run/'weights.npz').write_bytes(trained);(run/'model.json').write_bytes(original_model)
            (run/'training-source.py').write_text('# unrelated source\n')
            with self.assertRaisesRegex(ValueError,'source_code checksum'):
                m.predict(run,root/'must-not-exist-either')
            self.assertFalse((root/'must-not-exist-either').exists())

    def test_finite_safe_arrays_must_form_one_composable_architecture(self):
        hidden=16
        weights={'W0':np.zeros((hidden,len(m.FEATURES)),np.float32),'b0':np.zeros(hidden,np.float32),
                 'W1':np.zeros((hidden,hidden),np.float32),'b1':np.zeros(hidden+1,np.float32),
                 'W2':np.zeros((len(m.STATE_NAMES),hidden),np.float32),'b2':np.zeros(len(m.STATE_NAMES),np.float32),
                 'input_mean':np.zeros(len(m.FEATURES),np.float32),'input_std':np.ones(len(m.FEATURES),np.float32),
                 'output_mean':np.zeros(len(m.STATE_NAMES),np.float32),'output_std':np.ones(len(m.STATE_NAMES),np.float32)}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'finite-but-incompatible.npz';np.savez_compressed(path,**weights)
            with self.assertRaisesRegex(ValueError,'shapes'):
                m.load_weights(path)


if __name__=='__main__':unittest.main()
