"""Disclosed mechanical retargeting of verified Earnalism NN predictions.

The NN checkpoint and its raw predictions are never changed. This separate
animation stage authors ground contacts, endpoint root easing and, when requested,
a seated lower body. Its analytic IK is not model inference or learned acting.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.original_motion import motion_model as model
from scripts.original_motion import learned_rig_render as raw_renderer

SCHEMA='earnalism.disclosed_motion_retargeting.v1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def ref(path):
    return {'path':str(Path(path).resolve()),'sha256':sha(path)}

def _groups(mask):
    indices=np.flatnonzero(mask)
    return [g for g in np.split(indices,np.flatnonzero(np.diff(indices)>1)+1) if len(g)]

def _smooth_three(values):
    padding=[(1,1)]+[(0,0)]*(values.ndim-1)
    padded=np.pad(values,padding,mode='edge')
    return .25*padded[:-2]+.5*padded[1:-1]+.25*padded[2:]

def _root_ease(root,times,seconds):
    if not seconds:return root.copy()
    duration=float(times[-1]);a=min(float(seconds),duration/4)
    if duration<=0 or a<=0:raise ValueError('Root ease needs a positive actual clock')
    t=np.asarray(times,np.float64);u=np.clip(t/a,0,1);v=np.clip((duration-t)/a,0,1)
    area=np.where(t<a,a*(u**3-.5*u**4),np.where(t>duration-a,duration-a-a*(v**3-.5*v**4),t-a/2))
    return root[0]+(root[-1]-root[0])*area/(duration-a)

def _contact_targets(raw_feet, contacts, times):
    """Lock raw-derived support anchors; blend corrections across swing only."""
    targets=raw_feet.copy().astype(np.float64);velocity=np.gradient(raw_feet,times,axis=0)
    groups=_groups(contacts)
    for group in groups:
        targets[group,0]=float(np.median(raw_feet[group,0]));targets[group,1]=0
    correction=targets-raw_feet
    for group in _groups(~contacts):
        a=int(group[0])-1;b=int(group[-1])+1
        if a<0 and b>=len(times):
            targets[group,1]=np.maximum(targets[group,1],0);continue
        if a<0:correction[group]=correction[b]
        elif b>=len(times):correction[group]=correction[a]
        else:
            duration=float(times[b]-times[a]);u=(times[group]-times[a])/duration
            h00=2*u**3-3*u**2+1;h10=u**3-2*u**2+u
            h01=-2*u**3+3*u**2;h11=u**3-u**2
            correction[group]=(h00[:,None]*correction[a]+h10[:,None]*duration*(-velocity[a])
                              +h01[:,None]*correction[b]+h11[:,None]*duration*(-velocity[b]))
        targets[group]=raw_feet[group]+correction[group]
    targets[:,1]=np.maximum(targets[:,1],0)
    return targets

def _solve_leg(dx,dy,upper,lower,bend_sign=-1):
    """Declared geometric constraint, independent of the training teacher."""
    cosine=(dx*dx+dy*dy-upper*upper-lower*lower)/(2*upper*lower)
    if np.any(cosine>1+1e-7) or np.any(cosine<-1-1e-7):raise ValueError('Unreachable declared foot constraint')
    bend=bend_sign*np.arccos(np.clip(cosine,-1,1))
    angle=np.arctan2(dy,dx)-np.arctan2(lower*np.sin(bend),upper+lower*np.cos(bend))+np.pi/2
    return angle,bend

def retarget_arrays(arrays,manifest,*,profile='grounded',seat=None,root_ease_seconds=.25,
                    window_point=False,rest_hands_on_lap=True,seat_reference=None):
    if profile not in ('grounded','seated_context'):raise ValueError('Unsupported explicit retargeting profile')
    if not isinstance(window_point,bool) or not isinstance(rest_hands_on_lap,bool):raise ValueError('Constraint switches require actual booleans')
    if (isinstance(root_ease_seconds,bool) or not isinstance(root_ease_seconds,(int,float))
            or not np.isfinite(root_ease_seconds) or not 0<=root_ease_seconds<=.5):raise ValueError('Root easing must be finite0..0.5 seconds')
    raw=np.asarray(arrays['joints'],np.float64);state=np.asarray(arrays['predicted_state'],np.float64).copy()
    body=np.asarray(arrays['body'],np.float64);times=np.asarray(arrays['time_seconds'],np.float64)
    root=np.asarray(arrays['root_x'],np.float64);count=len(times)
    if raw.shape!=(count,15,2) or state.shape!=(count,11) or body.shape!=(8,) or not np.isfinite(raw).all():
        raise ValueError('Malformed retained NN arrays')
    action=manifest['action'];locomotion=action in ('walk','run')
    if profile=='seated_context' and locomotion:raise ValueError('A walking actor cannot be silently seated')
    if profile=='grounded' and action=='sit':raise ValueError('Sitting needs explicitly authored seat context')
    if window_point and (profile!='grounded' or action!='point'):
        raise ValueError('Window target retargeting requires the actual standing point action')
    derived_root=_root_ease(root,times,root_ease_seconds if locomotion else 0)
    raw_world=raw.copy();raw_world[:,:,0]+=derived_root[:,None]-root[:,None]
    contacts=np.ones((count,2),bool)
    if locomotion:
        case=manifest['case'];phase=case['pace']*times+case['phase_offset'];stance=.62 if action=='walk' else .38
        contacts=np.stack(((phase%1)<stance,((phase+.5)%1)<stance),axis=1)
    targets=np.empty((count,2,2),np.float64)
    if profile=='seated_context':
        if not isinstance(seat,dict):raise ValueError('Seated retargeting needs a predeclared seat object')
        surface=seat.get('surface_y');forward=seat.get('feet_forward',.20)
        if not isinstance(surface,(int,float)) or not .2<=surface<=.8 or not isinstance(forward,(int,float)) or not 0<=forward<=.35:
            raise ValueError('Seat geometry outside supported original rig')
        if np.ptp(root)>1e-5:raise ValueError('Seated context requires a stationary authored root')
        if seat_reference is not None:
            if sha(seat_reference['path'])!=seat_reference['sha256']:raise ValueError('Seated NN reference changed')
            auxiliary=raw_renderer.load_prediction(seat_reference['path'])
            if auxiliary['action']!='sit' or auxiliary['fixture_mode']:raise ValueError('Seated reference must be an actual learned sit')
            with np.load(auxiliary['prediction']['path'],allow_pickle=False) as a:
                if not np.array_equal(a['body'],arrays['body']):raise ValueError('Seated reference body differs')
                late=a['predicted_state'][int(len(a['predicted_state'])*.8):]
                state[:,6:11]=np.median(late[:,6:11],axis=0)
        state[:,10]=surface
        for k,sign in ((0,-1),(1,1)):
            targets[:,k,0]=derived_root+sign*body[6]/2+forward;targets[:,k,1]=0
    else:
        for k,index in ((0,11),(1,14)):
            feet=_smooth_three(raw_world[:,index]) if locomotion else raw_world[:,index]
            targets[:,k]=_contact_targets(feet,contacts[:,k],times)
        if locomotion:state[:,10]=_smooth_three(state[:,10])
        if not locomotion:
            # These standing actions have no authored crouch. Stabilize tiny
            # NN pelvis noise instead of turning it into near-straight-knee IK
            # jitter. This fixed lower-body context is explicitly disclosed.
            state[:,10]=float(np.median(state[:,10]))
    # A small downward pelvis projection makes both exact leg lengths feasible.
    # It does not move a supporting foot or stretch either bone.
    max_reach=body[0]+body[1]-.003
    for k,sign in ((0,-1),(1,1)):
        dx=targets[:,k,0]-(derived_root+sign*body[6]/2)
        if np.any(np.abs(dx)>=max_reach):raise ValueError('Ground target exceeds horizontal leg reach')
        maximum=targets[:,k,1]+np.sqrt(max_reach**2-dx**2)
        if profile=='seated_context' and np.any(state[:,10]>maximum+1e-7):
            raise ValueError('Predeclared seat/feet geometry is unreachable')
        if locomotion:
            # Smooth minimum avoids a derivative kink where a noisy predicted
            # pelvis meets a fully extended-leg reach ceiling.
            softness=.002
            state[:,10]=-softness*np.logaddexp(-state[:,10]/softness,-maximum/softness)
        else:state[:,10]=np.minimum(state[:,10],maximum)
    for k,sign in ((0,-1),(1,1)):
        hip_x=derived_root+sign*body[6]/2
        state[:,6+k*2],state[:,7+k*2]=_solve_leg(targets[:,k,0]-hip_x,targets[:,k,1]-state[:,10],body[0],body[1])
    pose=model.forward_kinematics(state,np.broadcast_to(body,(count,8)),derived_root)
    if window_point:
        if np.ptp(root)>1e-5:raise ValueError('Fixed window gesture needs a stationary actor root')
        # Fixed authored wrist target on the window side, near shoulder level.
        # The positive elbow branch avoids the high-elbow/down-hook prototype.
        target=np.array([root[0]+body[5]/2+.97*(body[2]+body[3]),
                         .997*(body[0]+body[1])+body[4]*.82+.02])
        extent=model.smooth(np.asarray(arrays['inputs'])[:,11]/.5)
        wrist=pose[0,8][None,:]+(target-pose[0,8])[None,:]*extent[:,None]
        state[:,4],state[:,5]=_solve_leg(wrist[:,0]-pose[:,6,0],wrist[:,1]-pose[:,6,1],body[2],body[3],1)
    if profile=='seated_context' and rest_hands_on_lap:
        # Predeclared lap rests; the model's standing-rest arms are not reused
        # as dangling seated arms. These target constraints are authored.
        for shoulder,a,sign in ((3,2,-1),(6,4,1)):
            tx=derived_root+sign*body[6]/2+.15;ty=np.full(count,seat['surface_y']+.04)
            state[:,a],state[:,a+1]=_solve_leg(tx-pose[:,shoulder,0],ty-pose[:,shoulder,1],body[2],body[3],1)
    if not np.isfinite(state).all() or np.any(state[:,:10]<model.LOWER[:10]-1e-5) or np.any(state[:,:10]>model.UPPER[:10]+1e-5):
        raise ValueError('Derived joints exceed declared anatomical bounds')
    if np.any(state[:,10]<.20):raise ValueError('Derived pelvis below supported range')
    joints=model.forward_kinematics(state,np.broadcast_to(body,(count,8)),derived_root)
    error=np.max(np.abs(joints[:,[11,14]]-targets))
    if error>2e-6:raise ValueError('Mechanical constraint failed exact-length FK replay')
    return {'joints':joints,'time_seconds':times.astype(np.float32),'constrained_state':state.astype(np.float32),
            'derived_root_x':derived_root.astype(np.float32),'authored_contact_mask':contacts,
            'foot_targets':targets.astype(np.float32),'body':body.astype(np.float32)}

def metrics(joints,times,contacts,body):
    height=float(body[0]+body[1]+body[4]+body[7]);vel=np.diff(joints,axis=0)/np.diff(times)[:,None,None]
    accel=np.diff(vel,axis=0)/np.diff(times)[:-1,None,None];drift=[]
    for k,ji in ((0,11),(1,14)):
        for group in _groups(contacts[:,k]):
            drift.append(float(np.linalg.norm(joints[group,ji]-joints[group[0],ji],axis=-1).max()/height))
    return {'support_foot_drift_body_height_max':max(drift,default=0),
            'minimum_ankle_y_m':float(joints[:,[11,14],1].min()),
            'joint_speed_p95_m_s':float(np.quantile(np.linalg.norm(vel,axis=-1),.95)),
            'joint_acceleration_p95_m_s2':float(np.quantile(np.linalg.norm(accel,axis=-1),.95)),
            'joint_acceleration_max_m_s2':float(np.linalg.norm(accel,axis=-1).max())}

def measurements(arrays,derived):
    """Compute report evidence from the actual raw and replayed numeric arrays."""
    before=np.asarray(arrays['predicted_state']);after=derived['constrained_state']
    return {'raw_metrics':metrics(arrays['joints'],arrays['time_seconds'],derived['authored_contact_mask'],arrays['body']),
            'derived_metrics':metrics(derived['joints'],derived['time_seconds'],derived['authored_contact_mask'],arrays['body']),
            'correction':{'max_joint_displacement_m':float(np.linalg.norm(derived['joints']-arrays['joints'],axis=-1).max()),
              'max_pelvis_height_displacement_m':float(np.max(np.abs(after[:,10]-before[:,10]))),
              'max_lower_body_angle_change_rad':float(np.max(np.abs(after[:,6:10]-before[:,6:10]))),
              'upper_body_rotation_max_change_rad':float(np.max(np.abs(after[:,:6]-before[:,:6]))),
              'root_path_max_displacement_m':float(np.max(np.abs(derived['derived_root_x']-arrays['root_x'])))}}

def derive(manifest_path,output_dir,*,profile='grounded',seat=None,root_ease_seconds=.25,
           window_point=False,rest_hands_on_lap=True,seat_prediction_manifest=None):
    verified=raw_renderer.load_prediction(manifest_path)
    if verified['fixture_mode']:raise ValueError('Research retargeting requires actual trained NN prediction')
    with np.load(verified['prediction']['path'],allow_pickle=False) as a:arrays={k:a[k].copy() for k in a.files}
    output=Path(output_dir).resolve()
    if output.exists():raise ValueError('Preserve previous derived output')
    config={'profile':profile,'seat':seat,'root_ease_seconds':root_ease_seconds,'window_point':window_point,
            'rest_hands_on_lap':rest_hands_on_lap,'seat_reference':ref(seat_prediction_manifest) if seat_prediction_manifest else None}
    derived=retarget_arrays(arrays,verified['manifest'],**config)
    output.mkdir(parents=True);np.savez_compressed(output/'derived-motion.npz',**derived)
    report={'schema':SCHEMA,'raw_prediction_manifest':ref(manifest_path),'derived_motion':ref(output/'derived-motion.npz'),
            'raw_numeric_validation':verified['numeric_validation'],
            'configuration':config,
            'provenance':{'neural_checkpoint_unchanged':True,'raw_prediction_unchanged':True,
              'neural_state_indices_preserved':[0,1] if profile=='seated_context' and rest_hands_on_lap else [0,1,2,3] if window_point else [0,1,2,3,4,5],
              'ground_contact_schedule':'Authored gait phase from retained pace/phase controls; all standing feet planted',
              'pelvis_stabilization':'Stationary standing height uses raw median; locomotion uses explicit smooth reach ceiling with3mm leg slack',
              'support_anchor_source':'Median verified NN world foot position within each declared support interval; locomotion positions receive disclosed3-tap temporalfilter',
              'locomotion_temporal_filter':'Frame-aligned .25,.5,.25 foot-position and pelvis filter; no retiming' if verified['action'] in ('walk','run') else None,
              'geometric_leg_IK_used':True,'IK_is_model_inference':False,
              'seated_lower_body_source':'Authored fixed seat context; not learned sitting' if profile=='seated_context' else None,
              'seated_reference_source':config['seat_reference'],
              'pointing_arm_source':'Authored fixed window-direction wrist target and positive-elbow IK' if window_point else 'Retained NN arm rotations',
              'seated_rest_arm_source':'Authored fixed lap wrist targets and positive-elbow IK' if profile=='seated_context' and rest_hands_on_lap else None,
              'teacher_trajectory_called':False,'code':ref(Path(__file__))},
            **measurements(arrays,derived),
            'comparison_scope':('Authored seated context and held lower body: this is not a like-for-like NN motion-quality benchmark' if profile=='seated_context'
                 else 'Authored replacement hand target/arm branch: this is not a neural accuracy improvement' if window_point
                 else 'Same NN case and clock; explicitly disclosed mechanical ground/temporal corrections'),
            'research_only':True,'natural_acting_acceptance':'UNPERFORMED','release_approved':False}
    (output/'CONSTRAINT-MANIFEST.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

def load_verified_derivative(path):
    path=Path(path).resolve();packet=json.loads(path.read_text());raw=packet['raw_prediction_manifest']
    if packet.get('schema')!=SCHEMA or sha(raw['path'])!=raw['sha256']:raise ValueError('Derived raw manifest binding changed')
    if packet['provenance']['code']['sha256']!=sha(Path(__file__)):raise ValueError('Retargeting implementation changed; do not reuse old derivative as current')
    config=packet['configuration'];preserved=([0,1] if config['profile']=='seated_context' and config['rest_hands_on_lap']
                   else [0,1,2,3] if config['window_point'] else [0,1,2,3,4,5])
    provenance=packet['provenance']
    if (packet.get('research_only') is not True or packet.get('release_approved') is not False
            or packet.get('natural_acting_acceptance')!='UNPERFORMED'
            or provenance.get('neural_checkpoint_unchanged') is not True or provenance.get('raw_prediction_unchanged') is not True
            or provenance.get('IK_is_model_inference') is not False or provenance.get('geometric_leg_IK_used') is not True
            or provenance.get('teacher_trajectory_called') is not False
            or provenance.get('neural_state_indices_preserved')!=preserved):raise ValueError('Derived source/constraint disclosure is inconsistent')
    verified=raw_renderer.load_prediction(raw['path'])
    if verified['fixture_mode']:raise ValueError('Research retargeting requires actual trained NN prediction')
    derived_ref=packet['derived_motion']
    if sha(derived_ref['path'])!=derived_ref['sha256']:raise ValueError('Derived numerical bytes changed')
    with np.load(verified['prediction']['path'],allow_pickle=False) as a:arrays={k:a[k].copy() for k in a.files}
    replay=retarget_arrays(arrays,verified['manifest'],**packet['configuration'])
    with np.load(derived_ref['path'],allow_pickle=False) as a:
        if set(a.files)!=set(replay):raise ValueError('Unsupported derived array fields')
        for key,value in replay.items():
            if not np.array_equal(a[key],value):raise ValueError('Derived mechanical replay mismatch: '+key)
    measured=measurements(arrays,replay)
    measured['raw_numeric_validation']=verified['numeric_validation']
    for key,value in measured.items():
        # JSON comparison also rejects bools masquerading as numerical values.
        if json.dumps(packet.get(key),sort_keys=True,allow_nan=False)!=json.dumps(value,sort_keys=True,allow_nan=False):
            raise ValueError('Derived reported measurements differ from numerical replay: '+key)
    return {'joints':replay['joints'],'times':replay['time_seconds'],'manifest':packet,'raw':verified,'arrays':replay}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prediction',required=True);p.add_argument('--output',required=True)
    p.add_argument('--profile',choices=['grounded','seated_context'],default='grounded');p.add_argument('--seat-y',type=float)
    a=p.parse_args();r=derive(a.prediction,a.output,profile=a.profile,seat={'surface_y':a.seat_y,'feet_forward':.2} if a.profile=='seated_context' else None)
    print(json.dumps({'state':'EXPLICIT_RESEARCH_RETARGETING','raw':r['raw_metrics'],'derived':r['derived_metrics'],'correction':r['correction']},indent=2))
