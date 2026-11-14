#!/usr/bin/env python3
"""Read-only diagnostics for actual learned weights and held-out trajectories.

No training, teacher fallback or acceptance is performed. Reference trajectories
are used only to measure errors and temporal behavior in the held-out set.
"""
import argparse
import json
from pathlib import Path
import numpy as np
try:
    from . import motion_model as m
except ImportError:
    import motion_model as m


def infer_einsum(weights, inputs):
    # Equivalent explicit contractions avoid spurious Apple Accelerate status
    # warnings observed with NumPy2 BLAS. No errors are suppressed.
    h=(inputs-weights['input_mean'])/weights['input_std']
    with np.errstate(all='raise'):
        for i in (0,1):
            h=np.tanh(np.einsum('ni,oi->no',h,weights['W'+str(i)],optimize=False)+weights['b'+str(i)])
        return (np.einsum('ni,oi->no',h,weights['W2'],optimize=False)+weights['b2'])*weights['output_std']+weights['output_mean']


def diagnose(model_dir):
    model_dir=Path(model_dir).resolve()
    model=json.loads((model_dir/'model.json').read_text())
    report=json.loads((model_dir/'training-report.json').read_text())
    if m.sha(model_dir/'weights.npz')!=model['model']['sha256'] or m.sha(model_dir/'training-report.json')!=model['training_report']['sha256']:
        raise ValueError('Model/report checksum mismatch')
    weights=m.load_weights(model_dir/'weights.npz')
    with np.load(model_dir/'dataset.npz',allow_pickle=False) as data:arrays={k:data[k].copy() for k in data.files}
    if m.sha(model_dir/'dataset.npz')!=report['dataset']['sha256']:raise ValueError('Dataset bytes changed')
    metadata=json.loads((model_dir/'dataset.json').read_text())
    test=arrays['split']==2;x=arrays['inputs'][test]
    state=infer_einsum(weights,x);truth=arrays['states'][test]
    body=x[:,m.BODY_SLICE];root=arrays['root_x'][test]
    learned=m.forward_kinematics(state,body,root);teacher=m.forward_kinematics(truth,body,root)
    ids=arrays['trajectory_id'][test];records=[]
    for item in metadata['trajectories']:
        if item['split']!='test':continue
        selected=np.flatnonzero(ids==item['trajectory_id']);dt=item['case']['duration_seconds']/(item['frames']-1)
        height=float(sum(item['body'][k] for k in (0,1,4,7)))
        row={'trajectory_id':item['trajectory_id'],'action':item['case']['action']}
        for name,poses in (('learned_raw',learned[selected]),('reference',teacher[selected])):
            v=np.diff(poses,axis=0)/dt/height
            a=np.diff(v,axis=0)/dt
            j=np.diff(a,axis=0)/dt
            row[name]={'velocity_p95_body_heights_per_second':float(np.quantile(np.linalg.norm(v,axis=-1),.95)),
                       'acceleration_p95_body_heights_per_second2':float(np.quantile(np.linalg.norm(a,axis=-1),.95)),
                       'jerk_p95_body_heights_per_second3':float(np.quantile(np.linalg.norm(j,axis=-1),.95)),
                       'minimum_ankle_y_body_height':float(poses[:,[11,14],1].min()/height),
                       'pelvis_start_to_end_y_body_height':float((poses[-1,0,1]-poses[0,0,1])/height)}
        records.append(row)
    # Change only action conditioning on the same body/time/target controls.
    probe=x[:min(128,len(x))].copy();probe[:,:len(m.ACTIONS)]=0;probe[:,m.ACTIONS.index('idle')]=1
    idle=infer_einsum(weights,probe)
    probe[:,:len(m.ACTIONS)]=0;probe[:,m.ACTIONS.index('wave')]=1
    wave=infer_einsum(weights,probe)
    conditioning=float(np.sqrt(np.mean((idle-wave)**2)))
    return {'schema':'earnalism.learned_motion_diagnostics.v1','model':m.ref(model_dir/'weights.npz'),
            'training_report':m.ref(model_dir/'training-report.json'),'heldout_trajectories':records,
            'action_conditioning_state_RMSE_idle_vs_wave':conditioning,
            'conditioning_changes_actual_pose':conditioning>1e-3,
            'measurement':'Raw network predictions; fixed world root path disclosed separately. Reference is original held-out procedural teacher, not human motion.',
            'not_acceptance':['Naturalness/human quality','Production readiness','Real-world generalization'],
            'teacher_used_at_inference':False,'new_training_or_provider_calls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=diagnose(a.model_dir)
    with a.output.open('x') as out:json.dump(result,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'output':str(a.output),'conditioning_changes_actual_pose':result['conditioning_changes_actual_pose'],'heldout_trajectory_count':len(result['heldout_trajectories']),'release_approved':False}))
