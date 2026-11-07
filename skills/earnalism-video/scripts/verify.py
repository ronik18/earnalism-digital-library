#!/usr/bin/env python3
"""Quick source/default preflight; run the full regression suite only with --full."""
import argparse,pathlib,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--full',action='store_true');a=p.parse_args();root=pathlib.Path(a.project).resolve();software=root/'video_studio'
subprocess.run([sys.executable,str(software/'studio.py'),'checksum'],check=True,cwd=root)
subprocess.run([sys.executable,str(software/'expectations.py'),'--root',str(software)],check=True,cwd=root)
if a.full:
 subprocess.run([sys.executable,'-m','unittest','discover','-s',str(software/'tests'),'-v'],check=True,cwd=root)
 node_tests=sorted({p for directory in ('src','tests','comparison-player') for p in (software/directory).glob('*.test.mjs')})
 if not node_tests:raise ValueError('No Node regression tests discovered')
 subprocess.run(['node','--test',*[str(p) for p in node_tests]],check=True,cwd=root)
else:
 print('QUICK_PREFLIGHT_PASS; no media decoding, full regression suite or human approval performed. Use --full when software changes justify it.')
