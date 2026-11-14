#!/usr/bin/env python3
"""Run the identical scratch trainer on existing Colab CUDA, without installs."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--expected-source-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-seconds',type=float,default=600)
    p.add_argument('--max-steps',type=int,default=4000)
    p.add_argument('--characters',type=int,default=48)
    p.add_argument('--seed',type=int,default=1701)
    a=p.parse_args()
    if not 1<=a.max_seconds<=600 or not 1<=a.max_steps<=6000 or not 6<=a.characters<=96:
        raise ValueError('Worker bound exceeded; do not start training')
    if hashlib.sha256(a.source.read_bytes()).hexdigest()!=a.expected_source_sha256:
        raise ValueError('Trainer source hash mismatch')
    import torch
    if not torch.cuda.is_available():
        raise ValueError('Actual Colab CUDA required; no CPU run relabelled as GPU')
    spec=importlib.util.spec_from_file_location('earnalism_original_motion',a.source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    report=module.train(a.output,device='cuda',seed=a.seed,characters=a.characters,
                        variants=2,frames=64,hidden=96,max_steps=a.max_steps,
                        max_seconds=a.max_seconds,batch_size=1024)
    print(json.dumps({'status':report['status'],'actual_cuda_device':report['actual_cuda_device'],
                      'steps':report['steps'],'engineering_checks':report['engineering_checks'],
                      'provider_downloads':0,'release_approved':False},indent=2))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'STOPPED_NO_GPU_TRAINING_CLAIM','detail':str(exc)}))
        sys.exit(2)
