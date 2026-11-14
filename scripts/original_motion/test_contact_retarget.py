"""Synthetic unit fixtures for authored constraints; not learned-motion evidence.

The seven actual trained-prediction replays are recorded separately by the private
Open Window trial report. These tests never train weights or claim acting quality.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

try:
    from . import contact_retarget as retarget
except ImportError:
    import contact_retarget as retarget


class ContactRetargetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='contact-retarget-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.times=np.arange(72,dtype=np.float32)/24
        self.body=np.array([.43,.43,.29,.27,.48,.34,.18,.22],np.float32)
        state=np.zeros((len(self.times),11),np.float32)
        state[:,0]=.005*np.sin(self.times*2);state[:,1]=.01*np.cos(self.times*2)
        state[:,2]=.05;state[:,4]=-.05
        state[:,6]=.1+.003*np.sin(self.times*4);state[:,7]=-.2
        state[:,8]=.1+.003*np.cos(self.times*4);state[:,9]=-.2
        state[:,10]=.85+.001*np.sin(self.times*3)
        root=np.zeros(len(self.times),np.float32)
        self.arrays={'joints':retarget.model.forward_kinematics(state,np.broadcast_to(self.body,(len(state),8)),root),
                     'predicted_state':state,'body':self.body,'time_seconds':self.times,'root_x':root,
                     'inputs':np.zeros((len(state),25),np.float32)}
        self.arrays['inputs'][:,11]=np.linspace(0,1,len(state))
        self.manifest={'action':'idle','case':{'pace':1.,'phase_offset':.1}}

    def assert_bones(self,joints):
        pairs=((9,10,0),(10,11,1),(12,13,0),(13,14,1),
               (3,4,2),(4,5,3),(6,7,2),(7,8,3),(0,1,4),(1,2,7))
        for a,b,k in pairs:
            np.testing.assert_allclose(np.linalg.norm(joints[:,b]-joints[:,a],axis=-1),self.body[k],atol=2e-7)

    def make_packet(self):
        prediction=self.root/'synthetic-arrays.npz';np.savez(prediction,**self.arrays)
        manifest=self.root/'synthetic-manifest.json';manifest.write_text(json.dumps(self.manifest))
        verified={'fixture_mode':False,'prediction':{'path':str(prediction)},'manifest':self.manifest,
                  'numeric_validation':{'unit_test_mock_only':True},'action':'idle'}
        with patch.object(retarget.raw_renderer,'load_prediction',return_value=verified):
            retarget.derive(manifest,self.root/'derived')
        return self.root/'derived/CONSTRAINT-MANIFEST.json',verified

    def test_ground_contacts_preserve_lengths_upper_states_clock_and_raw(self):
        before={k:v.copy() for k,v in self.arrays.items()}
        result=retarget.retarget_arrays(self.arrays,self.manifest)
        self.assert_bones(result['joints'])
        np.testing.assert_array_equal(result['constrained_state'][:,:6],self.arrays['predicted_state'][:,:6])
        np.testing.assert_array_equal(result['time_seconds'],self.times)
        for foot in (11,14):
            np.testing.assert_allclose(result['joints'][:,foot],np.broadcast_to(result['joints'][0,foot],(72,2)),atol=2e-7)
        self.assertGreaterEqual(result['joints'][:,[11,14],1].min(),-2e-7)
        for key in before:np.testing.assert_array_equal(before[key],self.arrays[key])
        again=retarget.retarget_arrays(self.arrays,self.manifest)
        for key in result:np.testing.assert_array_equal(result[key],again[key])

    def test_root_ease_preserves_endpoints_and_clock_while_settling_velocity(self):
        root=np.linspace(0,1.5,len(self.times));eased=retarget._root_ease(root,self.times,.25)
        self.assertAlmostEqual(eased[0],root[0],places=12);self.assertAlmostEqual(eased[-1],root[-1],places=12)
        speed=np.diff(eased)/np.diff(self.times)
        self.assertLess(speed[0],speed[len(speed)//2]/4)
        self.assertLess(speed[-1],speed[len(speed)//2]/4)
        self.assertTrue(np.all(np.diff(eased)>=0))

    def test_seat_stays_exact_and_lap_rest_has_explicit_targets(self):
        seat={'surface_y':.47,'feet_forward':.2}
        result=retarget.retarget_arrays(self.arrays,self.manifest,profile='seated_context',seat=seat)
        np.testing.assert_allclose(result['joints'][:,0,1],seat['surface_y'],atol=3e-8)
        np.testing.assert_array_equal(result['constrained_state'][:,:2],self.arrays['predicted_state'][:,:2])
        for wrist,sign in ((5,-1),(8,1)):
            np.testing.assert_allclose(result['joints'][:,wrist,0],sign*self.body[6]/2+.15,atol=2e-7)
            np.testing.assert_allclose(result['joints'][:,wrist,1],seat['surface_y']+.04,atol=2e-7)
        self.assert_bones(result['joints'])
        np.testing.assert_allclose(result['joints'][:,[11,14],1],0,atol=2e-7)

    def test_impossible_predeclared_seat_rejects_instead_of_moving_chair(self):
        with self.assertRaisesRegex(ValueError,'seat/feet geometry is unreachable'):
            retarget.retarget_arrays(self.arrays,self.manifest,profile='seated_context',seat={'surface_y':.8,'feet_forward':.35})
        with self.assertRaisesRegex(ValueError,'predeclared seat'):
            retarget.retarget_arrays(self.arrays,self.manifest,profile='seated_context')

    def test_window_target_has_forward_wrist_and_lower_elbow(self):
        manifest={**self.manifest,'action':'point'}
        result=retarget.retarget_arrays(self.arrays,manifest,window_point=True)
        pose=result['joints'][-1]
        self.assertGreater(pose[8,0]-pose[6,0],.5)
        self.assertLess(pose[7,1],pose[6,1])
        np.testing.assert_array_equal(result['constrained_state'][:,:4],self.arrays['predicted_state'][:,:4])
        self.assert_bones(result['joints'])
        with self.assertRaisesRegex(ValueError,'actual standing point'):
            retarget.retarget_arrays(self.arrays,self.manifest,window_point=True)

    def test_invalid_switches_and_easing_reject(self):
        for invalid in (True,float('nan'),-.01,.51,'0.25'):
            with self.subTest(invalid=invalid),self.assertRaisesRegex(ValueError,'Root easing'):
                retarget.retarget_arrays(self.arrays,self.manifest,root_ease_seconds=invalid)
        for key in ('window_point','rest_hands_on_lap'):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'actual booleans'):
                retarget.retarget_arrays(self.arrays,self.manifest,**{key:1})
        with self.assertRaisesRegex(ValueError,'explicitly authored seat'):
            retarget.retarget_arrays(self.arrays,{**self.manifest,'action':'sit'})
        with self.assertRaisesRegex(ValueError,'cannot be silently seated'):
            retarget.retarget_arrays(self.arrays,{**self.manifest,'action':'walk'},profile='seated_context')

    def test_derivation_rejects_fixture_claim_and_existing_output(self):
        with patch.object(retarget.raw_renderer,'load_prediction',return_value={'fixture_mode':True}):
            with self.assertRaisesRegex(ValueError,'actual trained NN'):
                retarget.derive('synthetic-placeholder',self.root/'no-output')
        packet,verified=self.make_packet()
        with patch.object(retarget.raw_renderer,'load_prediction',return_value=verified):
            with self.assertRaisesRegex(ValueError,'Preserve previous'):
                retarget.derive(packet,self.root/'derived')

    def test_loader_replays_arrays_and_rejects_forged_provenance(self):
        path,verified=self.make_packet();original=json.loads(path.read_text())
        with patch.object(retarget.raw_renderer,'load_prediction',return_value=verified):
            loaded=retarget.load_verified_derivative(path)
            self.assertEqual(loaded['joints'].shape,(72,15,2))
            for key,value in (('IK_is_model_inference',True),('geometric_leg_IK_used',False),
                              ('teacher_trajectory_called',True),('neural_checkpoint_unchanged',False),
                              ('raw_prediction_unchanged',False),('neural_state_indices_preserved',[0])):
                packet=copy.deepcopy(original);packet['provenance'][key]=value;path.write_text(json.dumps(packet))
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'disclosure is inconsistent'):
                    retarget.load_verified_derivative(path)
            for key,value in (('release_approved',True),('research_only',False),('natural_acting_acceptance','PASS')):
                packet=copy.deepcopy(original);packet[key]=value;path.write_text(json.dumps(packet))
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'disclosure is inconsistent'):
                    retarget.load_verified_derivative(path)
            path.write_text(json.dumps(original));fixture={**verified,'fixture_mode':True}
            with patch.object(retarget.raw_renderer,'load_prediction',return_value=fixture):
                with self.assertRaisesRegex(ValueError,'actual trained NN'):
                    retarget.load_verified_derivative(path)

    def test_changed_numeric_bytes_and_rehashed_nonreplay_arrays_reject(self):
        path,verified=self.make_packet();packet=json.loads(path.read_text());npz=Path(packet['derived_motion']['path'])
        original=npz.read_bytes();npz.write_bytes(original+b'changed')
        with patch.object(retarget.raw_renderer,'load_prediction',return_value=verified):
            with self.assertRaisesRegex(ValueError,'numerical bytes changed'):
                retarget.load_verified_derivative(path)
            npz.write_bytes(original)
            with np.load(npz) as a:arrays={k:a[k].copy() for k in a.files}
            arrays['joints'][0,2,0]+=.01;np.savez_compressed(npz,**arrays)
            packet['derived_motion']=retarget.ref(npz);path.write_text(json.dumps(packet))
            with self.assertRaisesRegex(ValueError,'mechanical replay mismatch'):
                retarget.load_verified_derivative(path)

    def test_reported_measurements_and_raw_validation_must_match_replay(self):
        path,verified=self.make_packet();original=json.loads(path.read_text())
        with patch.object(retarget.raw_renderer,'load_prediction',return_value=verified):
            for key,field,value in (('raw_metrics','support_foot_drift_body_height_max',99.),
                                    ('derived_metrics','minimum_ankle_y_m',99.),
                                    ('correction','max_joint_displacement_m',0.),
                                    ('raw_numeric_validation','unit_test_mock_only',False)):
                packet=copy.deepcopy(original);packet[key][field]=value;path.write_text(json.dumps(packet))
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'reported measurements differ'):
                    retarget.load_verified_derivative(path)


if __name__=='__main__':unittest.main()
