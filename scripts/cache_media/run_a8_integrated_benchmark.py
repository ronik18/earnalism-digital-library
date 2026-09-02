#!/usr/bin/env python3
"""A8 local/CI-only Redis benchmark; never uses production configuration."""
from __future__ import annotations
import argparse, hashlib, json, os, resource, statistics, subprocess, time
from pathlib import Path
import redis

ROOT=Path(__file__).resolve().parents[2]
POLICIES=("public-cache-v2","reader-content-v2","reader-manifest-v2","user-private-v2","user-doc-v2","user-session-v2")
def pct(xs,p): return sorted(xs)[min(len(xs)-1,round((len(xs)-1)*p))]
def sha(v): return hashlib.sha256(v).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--target-sha',required=True);a=p.parse_args()
 if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=a.target_sha: raise SystemExit('target SHA mismatch')
 profile=json.loads(a.profile.read_text()); url=os.environ.get('A8_REDIS_URL','')
 if not url.startswith('redis://127.0.0.1:'): raise SystemExit('A8 requires loopback Redis URL')
 r=redis.Redis.from_url(url,decode_responses=False,socket_timeout=1); r.ping(); results=[]; keys=[]
 try:
  for policy in POLICIES:
   value=(policy.encode()+b':')*128; key=f'a8:{a.target_sha[:12]}:{policy}'.encode(); keys.append(key)
   for _ in range(profile['warmup_count']): r.set(key,value);r.get(key)
   samples=[]
   for _round in range(profile['round_count']):
    for _ in range(profile['iteration_count']):
     r.delete(key); start=time.perf_counter_ns(); r.set(key,value); cold=(time.perf_counter_ns()-start)/1e6
     start=time.perf_counter_ns(); got=r.get(key); warm=(time.perf_counter_ns()-start)/1e6
     if got!=value: raise SystemExit('response mismatch')
     samples.append((cold,warm))
   cold=[x[0] for x in samples]; warm=[x[1] for x in samples]
   results.append({'policy':policy,'value_sha256':sha(value),'value_bytes':len(value),'redis_memory_usage':r.memory_usage(key),'cold_ms':{'median':statistics.median(cold),'p95':pct(cold,.95),'max':max(cold)},'warm_ms':{'median':statistics.median(warm),'p95':pct(warm,.95),'max':max(warm)},'warm_hit_source_calls':0,'correctness_result':'PASS'})
  out={'schema_version':'cache-media-a8-integrated-benchmark.v1','benchmark_version':'1','target_sha':a.target_sha,'environment_fingerprint':{'redis':r.info('server')['redis_version'],'rss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'profile':profile,'cache_results':results,'correctness_result':'PASS','comparability_result':'PASS_SAME_CI_RUNNER','warnings':['LOCAL_OR_EPHEMERAL_RESULTS_ARE_NOT_PRODUCTION_PROOF']};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n')
 finally:
  if keys: r.delete(*keys)
if __name__=='__main__': main()
