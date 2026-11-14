#!/usr/bin/env python3
"""Original-data scratch training for a narrow conditional 2D motion network.

This is a research skeletal-motion model, not a video foundation model. No
pretrained weights, network access, paid services or hidden teacher inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np

ACTIONS = ('idle', 'walk', 'run', 'point', 'reach', 'react', 'sit', 'wave', 'look')
JOINTS = ('pelvis', 'neck', 'head', 'Lshoulder', 'Lelbow', 'Lwrist',
          'Rshoulder', 'Relbow', 'Rwrist', 'Lhip', 'Lknee', 'Lankle', 'Rhip', 'Rknee', 'Rankle')
HIERARCHY = (-1, 0, 1, 1, 3, 4, 1, 6, 7, 0, 9, 10, 0, 12, 13)
BODY_NAMES = ('upper_leg', 'lower_leg', 'upper_arm', 'lower_arm', 'torso', 'shoulder_width', 'hip_width', 'head_length')
STATE_NAMES = ('trunk', 'head', 'Lupper_arm', 'Lforearm_relative', 'Rupper_arm',
               'Rforearm_relative', 'Lthigh', 'Lshin_relative', 'Rthigh', 'Rshin_relative', 'pelvis_height')
LOWER = np.array([-.6, -.8, -2.8, -2.8, -2.8, -2.8, -1.8, -2.9, -1.8, -2.9, .20], np.float32)
UPPER = np.array([.6, .8, 3.2, 2.8, 3.2, 2.8, 1.8, .2, 1.8, .2, 1.10], np.float32)
FEATURES = tuple('action_' + a for a in ACTIONS) + ('phase_sin', 'phase_cos', 'progress',
           'pace', 'effort', 'target_x', 'target_y', 'root_velocity') + BODY_NAMES
BODY_SLICE = slice(17, 25)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ref(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha(path)}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def smooth(value):
    x = np.clip(value, 0, 1)
    return x*x*(3-2*x)


def ik(dx, dy, upper, lower, bend=-1):
    """Original analytic two-bone teacher only; never used by model inference."""
    distance2 = dx*dx + dy*dy
    elbow = bend * np.arccos(np.clip((distance2-upper*upper-lower*lower)/(2*upper*lower), -.9999, .9999))
    shoulder = np.arctan2(dy, dx) - np.arctan2(lower*np.sin(elbow), upper+lower*np.cos(elbow))
    return shoulder + np.pi/2, elbow


def forward_kinematics(state, body, root_x):
    """Local rotations produce exact-length original 15-joint planar rigs."""
    state, body = np.asarray(state), np.asarray(body)
    n = len(state); j = np.zeros((n, 15, 2), np.float32)
    def up(angle, length): return np.stack((np.sin(angle)*length, np.cos(angle)*length), -1)
    def down(angle, length): return np.stack((np.sin(angle)*length, -np.cos(angle)*length), -1)
    j[:, 0] = np.stack((root_x, state[:, 10]), -1)
    trunk, head = state[:, 0], state[:, 1]
    j[:, 1] = j[:, 0] + up(trunk, body[:, 4])
    j[:, 2] = j[:, 1] + up(trunk+head, body[:, 7])
    across = np.stack((np.cos(trunk), -np.sin(trunk)), -1)
    for shoulder, elbow, wrist, sign, a in ((3,4,5,-1,2),(6,7,8,1,4)):
        j[:, shoulder] = j[:, 1] - up(trunk, body[:, 4]*.18) + across*(sign*body[:,5:6]/2)
        j[:, elbow] = j[:, shoulder] + down(state[:, a], body[:, 2])
        j[:, wrist] = j[:, elbow] + down(state[:, a]+state[:, a+1], body[:, 3])
    for hip,knee,ankle,sign,a in ((9,10,11,-1,6),(12,13,14,1,8)):
        j[:, hip] = j[:, 0] + np.stack((sign*body[:,6]/2, np.zeros(n)), -1)
        j[:, knee] = j[:, hip] + down(state[:, a], body[:, 0])
        j[:, ankle] = j[:, knee] + down(state[:, a]+state[:, a+1], body[:, 1])
    return j


def character(seed):
    rng = np.random.default_rng(seed)
    base = np.array([.43,.43,.29,.27,.48,.34,.18,.22])
    return (base * rng.uniform(.88,1.12,8)).astype(np.float32)


def case_parameters(action, body, seed, duration=3.):
    if action not in ACTIONS: raise ValueError('Unsupported action; no semantic fallback')
    rng = np.random.default_rng(seed)
    pace = rng.uniform(1.8,2.7) if action == 'run' else rng.uniform(.65,1.35)
    velocity = rng.uniform(.8,1.5) if action == 'run' else rng.uniform(.35,.8) if action == 'walk' else 0.
    velocity = min(velocity, pace*(body[0]+body[1])*.65)
    beta = rng.uniform(-.45,.25)
    reach = (.92 if action == 'point' else .75)*(body[2]+body[3])
    return {'action':action, 'pace':float(pace), 'effort':float(rng.uniform(.65,1.0)),
            'phase_offset':float(rng.uniform(0,1)), 'duration_seconds':float(duration),
            'target_x':float(body[5]/2+reach*np.cos(beta)),
            'target_y':float(body[4]*.82+reach*np.sin(beta)),
            'root_velocity':float(velocity), 'start_x':0.}


def inputs_for_case(body, case, times):
    t = np.asarray(times, np.float32); n=len(t)
    if case['action'] not in ACTIONS: raise ValueError('Unknown action')
    if not np.isfinite(t).all() or case['duration_seconds'] <= 0: raise ValueError('Invalid time')
    x = np.zeros((n, len(FEATURES)), np.float32)
    x[:, ACTIONS.index(case['action'])] = 1
    phase = case['pace']*t+case['phase_offset']
    x[:,9] = np.sin(2*np.pi*phase); x[:,10] = np.cos(2*np.pi*phase)
    x[:,11] = np.clip(t/case['duration_seconds'],0,1)
    for i,key in enumerate(('pace','effort','target_x','target_y','root_velocity'),12): x[:,i]=case[key]
    x[:,BODY_SLICE] = body
    root_x = case['start_x']+case['root_velocity']*t
    return x, root_x.astype(np.float32)


def teacher_trajectory(body, case, times):
    """Cleared original procedural data; no captured actor or book/audio data."""
    t = np.asarray(times); p=np.clip(t/case['duration_seconds'],0,1); n=len(t)
    action=case['action']; phase=case['pace']*t+case['phase_offset']; effort=case['effort']
    state=np.zeros((n,11),np.float32); state[:,10]=.94*(body[0]+body[1])
    state[:,2]=-.10; state[:,3]=-.12; state[:,4]=.10; state[:,5]=-.12
    contacts=np.ones((n,2),bool)
    feet=[]
    if action in ('walk','run'):
        stance=.62 if action=='walk' else .38
        stride=case['root_velocity']/case['pace']
        state[:,10]=(.90 if action=='walk' else .84)*(body[0]+body[1])
        state[:,10]+=(.012 if action=='walk' else .035)*np.abs(np.sin(2*np.pi*phase))
        state[:,0]=(.04 if action=='walk' else .12)*effort
        amplitude=.52 if action=='walk' else .9
        state[:,2]=amplitude*np.sin(2*np.pi*phase)
        state[:,4]=-state[:,2]
        state[:,3]=state[:,5]=-.25 if action=='walk' else -1.05
        for k,offset in enumerate((0,.5)):
            cycle=(phase+offset)%1; swing=np.clip((cycle-stance)/(1-stance),0,1)
            relative=stride*(.5-cycle)+stride*smooth(swing)
            y=(.09 if action=='walk' else .17)*np.sin(np.pi*swing)**2
            feet.append((relative,y)); contacts[:,k]=cycle<stance
    else:
        if action=='sit': state[:,10]-=.43*(body[0]+body[1])*smooth(p/.8)
        if action=='idle':state[:,10]+=.004*np.sin(2*np.pi*phase)*effort
        if action=='react':
            envelope=np.sin(np.pi*p)**2
            state[:,0]=-.28*effort*envelope;state[:,1]=.2*effort*envelope
            state[:,2]=-.8*envelope;state[:,3]=-1.0*envelope
            state[:,4]=.8*envelope;state[:,5]=-1.0*envelope
        if action=='look':state[:,1]=.55*smooth(p/.6)*effort
        for k in range(2):feet.append((np.full(n,.20*smooth(p/.8) if action=='sit' else 0),np.zeros(n)))
    for i,(fx,fy) in enumerate(feet):
        state[:,6+i*2],state[:,7+i*2]=ik(fx,fy-state[:,10],body[0],body[1],-1)
    if action in ('point','reach'):
        extent=smooth(p/(.50 if action=='point' else .65))
        sx=body[5]/2;sy=state[:,10]+body[4]*.82
        rest_x=sx+np.zeros(n);rest_y=sy-(body[2]+body[3])*.94
        goal_x=np.full(n,case['target_x']);goal_y=.94*(body[0]+body[1])+case['target_y']
        tx=rest_x+(goal_x-rest_x)*extent;ty=rest_y+(goal_y-rest_y)*extent
        state[:,4],state[:,5]=ik(tx-sx,ty-sy,body[2],body[3],-1)
        state[:,1]=.12*extent
    if action=='wave':
        extent=smooth(p/.3);state[:,4]=2.35*extent;state[:,5]=(.55+.28*np.sin(2*np.pi*phase))*extent
    return state,contacts


def make_dataset(seed=1701, characters=48, variants=2, frames=64):
    if characters<6 or variants<1 or frames<16: raise ValueError('Dataset too small for whole-character splits')
    train_count=max(2,int(characters*2/3));val_count=max(1,(characters-train_count)//2)
    rows=[];states=[];roots=[];contacts=[];split=[];ids=[];metadata=[]
    for person in range(characters):
        body=character(seed+person*7919)
        partition=0 if person<train_count else 1 if person<train_count+val_count else 2
        for ai,action in enumerate(ACTIONS):
            for variant in range(variants):
                sid=len(metadata);case=case_parameters(action,body,seed+person*10007+ai*97+variant)
                times=np.linspace(0,case['duration_seconds'],frames,dtype=np.float32)
                x,root=inputs_for_case(body,case,times);y,c=teacher_trajectory(body,case,times)
                rows.append(x);states.append(y);roots.append(root);contacts.append(c)
                split.extend([partition]*frames);ids.extend([sid]*frames)
                metadata.append({'trajectory_id':sid,'character_id':person,'split':('train','validation','test')[partition],
                                 'body':body.tolist(),'case':case,'frames':frames})
    arrays={'inputs':np.concatenate(rows),'states':np.concatenate(states),'root_x':np.concatenate(roots),
            'contacts':np.concatenate(contacts),'split':np.array(split,np.int8),'trajectory_id':np.array(ids,np.int32)}
    arrays['next_index']=np.arange(len(arrays['inputs']),dtype=np.int64)+1
    arrays['next_index'][frames-1::frames]-=1
    content=hashlib.sha256()
    for name,array in sorted(arrays.items()):
        if not np.isfinite(array).all():raise ValueError('Nonfinite generated data')
        content.update(name.encode());content.update(str(array.dtype).encode());content.update(str(array.shape).encode());content.update(array.tobytes())
    return arrays,{'schema':'earnalism.original_motion_dataset.v1','seed':seed,'characters':characters,'variants':variants,
                   'frames_per_trajectory':frames,'trajectory_count':len(metadata),'frame_count':len(split),
                   'content_sha256':content.hexdigest(),'source':'Original analytic two-bone IK and authored motion equations in motion_model.py',
                   'captured_or_downloaded_training_material':False,'split_unit':'whole character and complete trajectory',
                   'trajectories':metadata}


def numpy_predict(weights, x):
    h=(np.asarray(x,np.float32)-weights['input_mean'])/weights['input_std']
    for i in (0,1):h=np.tanh(h@weights['W'+str(i)].T+weights['b'+str(i)])
    return ((h@weights['W2'].T+weights['b2'])*weights['output_std']+weights['output_mean']).astype(np.float32)


def load_weights(path):
    expected={f'{prefix}{i}' for i in range(3) for prefix in ('W','b')}|{'input_mean','input_std','output_mean','output_std'}
    with np.load(path,allow_pickle=False) as f:
        if set(f.files)!=expected:raise ValueError('Unsupported safe weight array set')
        weights={k:f[k].copy() for k in f.files}
    if any(a.dtype!=np.float32 or not np.isfinite(a).all() for a in weights.values()):raise ValueError('Weights must be finite float32 arrays')
    if weights['W0'].shape[1]!=len(FEATURES) or weights['W2'].shape[0]!=len(STATE_NAMES):raise ValueError('Unsupported model dimensions')
    if np.any(weights['input_std']<=0) or np.any(weights['output_std']<=0):raise ValueError('Invalid scaling')
    return weights


def evaluate_predictions(predicted, arrays, metadata, mask):
    target=arrays['states'][mask];x=arrays['inputs'][mask];body=x[:,BODY_SLICE];root=arrays['root_x'][mask]
    joints=forward_kinematics(predicted,body,root);truth=forward_kinematics(target,body,root)
    height=body[:,0]+body[:,1]+body[:,4]+body[:,7]
    per_frame=np.sqrt(np.mean((joints-truth)**2,axis=(1,2)))/height
    report={'normalized_joint_RMSE':float(np.sqrt(np.mean(((joints-truth)/height[:,None,None])**2))),
            'state_RMSE':float(np.sqrt(np.mean((predicted-target)**2))),
            'finite_fraction':float(np.isfinite(joints).all(axis=(1,2)).mean()),'per_action':{}}
    selected_ids=arrays['trajectory_id'][mask];contact=arrays['contacts'][mask]
    for ai,action in enumerate(ACTIONS):
        a=x[:,ai]>0;item={'normalized_joint_RMSE':float(np.sqrt(np.mean(((joints[a]-truth[a])/height[a,None,None])**2)))}
        if action in ('point','reach'):
            final=a&(x[:,11]>=.85)
            goal=np.stack((root[final]+x[final,14],.94*(body[final,0]+body[final,1])+x[final,15]),-1)
            error=np.linalg.norm(joints[final,8]-goal,axis=-1)/height[final]
            item['final_target_error_body_height_mean']=float(error.mean());item['final_target_error_body_height_max']=float(error.max())
        if action in ('walk','run'):
            drifts=[]
            for sid in np.unique(selected_ids[a]):
                idx=np.flatnonzero(selected_ids==sid)
                for foot,ji in ((0,11),(1,14)):
                    active=contact[idx,foot];begin=None
                    for k,on in enumerate(np.r_[active,False]):
                        if on and begin is None:begin=k
                        if not on and begin is not None:
                            span=idx[begin:k]
                            if len(span)>1:drifts.append(float(np.linalg.norm(joints[span,ji]-joints[span[0],ji],axis=-1).max()/height[span[0]]))
                            begin=None
            item['support_foot_drift_body_height_max']=max(drifts,default=0.)
        report['per_action'][action]=item
    report['p95_frame_joint_error_body_height']=float(np.quantile(per_frame,.95))
    return report


def train(output_dir, *, device='cpu', seed=1701, characters=48, variants=2, frames=64,
          hidden=96, max_steps=2000, max_seconds=180., batch_size=1024):
    import torch
    from torch import nn
    if not 1<=max_steps<=10000 or not 1<=max_seconds<=1800 or not 16<=hidden<=256:raise ValueError('Bounded training controls required')
    output=Path(output_dir).resolve()
    if output.exists():raise ValueError('Run output already exists; preserve checkpoints')
    if device=='cuda' and not torch.cuda.is_available():raise ValueError('CUDA explicitly requested but no actual GPU is available')
    torch.set_num_threads(min(4,torch.get_num_threads()));torch.manual_seed(seed)
    if device=='cuda':torch.cuda.manual_seed_all(seed)
    output.mkdir(parents=True);started=time.monotonic();rng=np.random.default_rng(seed)
    (output/'training-source.py').write_bytes(Path(__file__).read_bytes())
    arrays,data_manifest=make_dataset(seed,characters,variants,frames)
    np.savez_compressed(output/'dataset.npz',**arrays);write_json(output/'dataset.json',data_manifest)
    train_mask=arrays['split']==0;val_mask=arrays['split']==1;test_mask=arrays['split']==2
    xmean=arrays['inputs'][train_mask].mean(0);xstd=np.maximum(arrays['inputs'][train_mask].std(0),.05)
    ymean=arrays['states'][train_mask].mean(0);ystd=np.maximum(arrays['states'][train_mask].std(0),.05)
    model=nn.Sequential(nn.Linear(len(FEATURES),hidden),nn.Tanh(),nn.Linear(hidden,hidden),nn.Tanh(),nn.Linear(hidden,len(STATE_NAMES))).to(device)
    def export():
        w={}
        for i,layer in enumerate((model[0],model[2],model[4])):
            w['W'+str(i)]=layer.weight.detach().cpu().numpy().astype(np.float32);w['b'+str(i)]=layer.bias.detach().cpu().numpy().astype(np.float32)
        return dict(w,input_mean=xmean.astype(np.float32),input_std=xstd.astype(np.float32),output_mean=ymean.astype(np.float32),output_std=ystd.astype(np.float32))
    initial=export();np.savez_compressed(output/'initial-weights.npz',**initial)
    tx=torch.tensor((arrays['inputs']-xmean)/xstd,device=device);ty=torch.tensor((arrays['states']-ymean)/ystd,device=device)
    choices=np.flatnonzero(train_mask);validation=torch.tensor(np.flatnonzero(val_mask),device=device)
    optimizer=torch.optim.Adam(model.parameters(),lr=.002)
    best=float('inf');best_state=None;history=[];steps=0
    for step in range(max_steps):
        if time.monotonic()-started>=max_seconds:break
        selected=rng.choice(choices,size=min(batch_size,len(choices)),replace=True)
        nxt=arrays['next_index'][selected]
        idx=torch.tensor(selected,device=device);ni=torch.tensor(nxt,device=device)
        model.train();pred=model(tx[idx]);pred_next=model(tx[ni]);target=ty[idx]
        loss=((pred-target)**2).mean()+.15*((pred_next-pred)-(ty[ni]-target)).square().mean()
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.);optimizer.step();steps=step+1
        if step%100==0 or step==max_steps-1:
            model.eval()
            with torch.no_grad():validation_loss=float(((model(tx[validation])-ty[validation])**2).mean().cpu())
            history.append({'step':steps,'training_loss':float(loss.detach().cpu()),'validation_loss':validation_loss,'elapsed_seconds':time.monotonic()-started})
            if validation_loss<best:best=validation_loss;best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    if steps==0 or best_state is None:raise ValueError('Training bound elapsed before a real checkpoint; no trained model claimed')
    model.load_state_dict(best_state);model.eval();weights=export();np.savez_compressed(output/'weights.npz',**weights)
    trained=numpy_predict(weights,arrays['inputs'][test_mask]);initial_pred=numpy_predict(initial,arrays['inputs'][test_mask])
    static_means=np.stack([arrays['states'][train_mask & (arrays['inputs'][:,i]>0)].mean(0) for i in range(len(ACTIONS))])
    static=static_means[np.argmax(arrays['inputs'][test_mask,:len(ACTIONS)],axis=1)]
    sample=np.flatnonzero(test_mask)[:256]
    with torch.no_grad():torch_values=(model(tx[torch.tensor(sample,device=device)])*torch.tensor(ystd,device=device)+torch.tensor(ymean,device=device)).cpu().numpy()
    parity=float(np.max(np.abs(torch_values-numpy_predict(weights,arrays['inputs'][sample]))))
    train_chars={t['character_id'] for t in data_manifest['trajectories'] if t['split']=='train'}
    val_chars={t['character_id'] for t in data_manifest['trajectories'] if t['split']=='validation'}
    test_chars={t['character_id'] for t in data_manifest['trajectories'] if t['split']=='test'}
    report={'schema':'earnalism.scratch_motion_training_report.v1','status':'RESEARCH_CHECKPOINT_TRAINED_METRICS_REPORTED',
       'device':device,'actual_cuda_device':torch.cuda.get_device_name(0) if device=='cuda' else None,
       'torch_version':torch.__version__,'numpy_version':np.__version__,'seed':seed,'steps':steps,
       'limits':{'max_steps':max_steps,'max_seconds':max_seconds,'batch_size':batch_size},
       'elapsed_seconds':time.monotonic()-started,'parameter_count':sum(p.numel() for p in model.parameters()),
       'dataset':ref(output/'dataset.npz'),'dataset_manifest':ref(output/'dataset.json'),
       'dataset_content_sha256':data_manifest['content_sha256'],'source_code':ref(output/'training-source.py'),
       'initial_weights':ref(output/'initial-weights.npz'),'weights':ref(output/'weights.npz'),
       'weights_differ_from_initial':sha(output/'weights.npz')!=sha(output/'initial-weights.npz'),
       'split_integrity':{'whole_trajectory':True,'train_character_ids':sorted(train_chars),'validation_character_ids':sorted(val_chars),'test_character_ids':sorted(test_chars),'character_overlap':bool(train_chars&val_chars or train_chars&test_chars or val_chars&test_chars)},
       'training_history':history,'model_raw_heldout':evaluate_predictions(trained,arrays,data_manifest,test_mask),
       'initial_random_heldout':evaluate_predictions(initial_pred,arrays,data_manifest,test_mask),
       'static_action_mean_heldout':evaluate_predictions(static,arrays,data_manifest,test_mask),
       'model_clipped_heldout':evaluate_predictions(np.clip(trained,LOWER,UPPER),arrays,data_manifest,test_mask),
       'numpy_export_max_abs_difference':parity,
       'not_claimed':['Premium/photorealistic video model','Natural human acting acceptance','Learned book comprehension','Lip synchronization','Real actor training data','Production release approval'],
       'provider_calls':0,'pretrained_weights':False,'teacher_used_at_model_inference':False}
    raw_error=report['model_raw_heldout']['normalized_joint_RMSE'];static_error=report['static_action_mean_heldout']['normalized_joint_RMSE'];initial_error=report['initial_random_heldout']['normalized_joint_RMSE']
    report['engineering_checks']={'learns_beyond_static_action_baseline':raw_error<static_error,'learns_beyond_random_initialization':raw_error<initial_error,'numpy_parity_below_1e_5':parity<1e-5,'whole_character_split_disjoint':not report['split_integrity']['character_overlap'],'all_predicted_frames_finite':report['model_raw_heldout']['finite_fraction']==1.0}
    write_json(output/'training-report.json',report)
    write_json(output/'model.json',{'schema':'earnalism.conditional_skeletal_motion_model.v1','research_only':True,'model':ref(output/'weights.npz'),'training_report':ref(output/'training-report.json'),'actions':ACTIONS,'joint_names':JOINTS,'hierarchy':HIERARCHY,'features':FEATURES,'state_names':STATE_NAMES,'architecture':[len(FEATURES),hidden,hidden,len(STATE_NAMES)],'activation':'tanh,tanh,linear','inference':'NumPy numerical arrays; no teacher or IK fallback','root_translation':'Explicit requested trajectory control; learned model predicts joint angles/pelvis height','bone_lengths':'Forward kinematics by construction, not learned naturalness'})
    return report


def predict(model_dir, output_dir, *, action='walk', duration=3., fps=30, seed=99001, travel=1.2, start_x=-.6):
    model_dir=Path(model_dir).resolve();output=Path(output_dir).resolve()
    if output.exists():raise ValueError('Prediction output exists; preserve previous candidate')
    if action not in ACTIONS or not .5<=duration<=30 or fps not in (24,25,30,60):raise ValueError('Unsupported action/duration/fps')
    manifest=json.loads((model_dir/'model.json').read_text());report=json.loads((model_dir/'training-report.json').read_text())
    if manifest.get('schema')!='earnalism.conditional_skeletal_motion_model.v1' or sha(model_dir/'weights.npz')!=manifest['model']['sha256'] or sha(model_dir/'training-report.json')!=manifest['training_report']['sha256'] or not report.get('weights_differ_from_initial'):raise ValueError('Trained model provenance mismatch')
    weights=load_weights(model_dir/'weights.npz');body=character(seed);case=case_parameters(action,body,seed+7,duration)
    case['start_x']=float(start_x);case['root_velocity']=float(travel/duration) if action in ('walk','run') else 0.
    times=np.arange(round(duration*fps),dtype=np.float32)/fps
    x,root_x=inputs_for_case(body,case,times);raw=numpy_predict(weights,x);state=np.clip(raw,LOWER,UPPER);joints=forward_kinematics(state,np.broadcast_to(body,(len(x),8)),root_x)
    if not np.isfinite(joints).all():raise ValueError('Nonfinite learned pose')
    output.mkdir(parents=True)
    np.savez_compressed(output/'prediction.npz',joints=joints,time_seconds=times,inputs=x,raw_predicted_state=raw,predicted_state=state,root_x=root_x,body=body)
    p={'schema':'earnalism.learned_motion_prediction.v1','action':action,'fps':fps,'duration_seconds':duration,
       'joint_names':JOINTS,'hierarchy':HIERARCHY,'coordinate_system':'x right, y up, metres; ground y=0',
       'prediction_file':ref(output/'prediction.npz'),'model':ref(model_dir/'weights.npz'),'training_report':ref(model_dir/'training-report.json'),
       'source_code':ref(Path(__file__)),'seed':seed,'case':case,'body':dict(zip(BODY_NAMES,body.tolist())),
       'provenance':{'prediction_source':'trained_model_inference','teacher_fallback':False,'inverse_kinematics_fallback':False,'root_translation':'Explicit user path, not learned','state_limits':'Fixed anatomical angle/height clipping; raw states retained','training_domain':'Original procedural synthetic2D skeletal motion'},
       'research_only':True,'natural_acting_acceptance':'UNPERFORMED','release_approved':False}
    write_json(output/'prediction.json',p)
    return p


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    t=subs.add_parser('train');t.add_argument('--output',required=True,type=Path)
    t.add_argument('--device',choices=['cpu','cuda'],default='cpu');t.add_argument('--seed',type=int,default=1701)
    for key,default in (('characters',48),('variants',2),('frames',64),('hidden',96),('max-steps',2000),('batch-size',1024)):t.add_argument('--'+key,type=int,default=default)
    t.add_argument('--max-seconds',type=float,default=180.)
    i=subs.add_parser('infer');i.add_argument('--model-dir',required=True,type=Path);i.add_argument('--output',required=True,type=Path)
    i.add_argument('--action',choices=ACTIONS,default='walk');i.add_argument('--duration',type=float,default=3.);i.add_argument('--fps',type=int,default=30);i.add_argument('--seed',type=int,default=99001);i.add_argument('--travel',type=float,default=1.2);i.add_argument('--start-x',type=float,default=-.6)
    a=p.parse_args(argv);values=vars(a);command=values.pop('command');out=values.pop('output')
    try:
        result=train(out,**values) if command=='train' else predict(output_dir=out,**values)
        print(json.dumps({'status':result.get('status','PREDICTION_EXPORTED'),'output':str(out),'engineering_checks':result.get('engineering_checks'),'release_approved':False},indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'FAILED_NO_PRODUCTION_CLAIM','detail':str(exc)}));return 2


if __name__=='__main__':raise SystemExit(main())
