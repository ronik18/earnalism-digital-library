from pathlib import Path
import json,hashlib,shutil
from datetime import datetime,timezone
R=Path('/tmp/earnalism-main-approved-integration');S=Path('/workspace/scratch/181ef0a25f05');D=S/'next-owner-accepted-final-nineteen-20261003-v3';L=R/'internal/earnalism_intelligence/book_go_live_477_continuation_20261002/owner-delegated-completion-20261003/next-cohort';p=S/'evidence-preservation-manifest-20261003-v2/evidence-preservation-manifest.json';d=json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(p,L/'worker-evidence-preservation-plan.json');rows=[]
for x in d['copy_plan']:
 f=Path(x['source_path']);assert sha(f)==x['sha256']and f.stat().st_size==x['bytes'];t=L/x['archive_relative_path'];t.parent.mkdir(parents=True,exist_ok=True);assert not t.exists();shutil.copyfile(f,t);assert sha(t)==x['sha256'];rows.append({**x,'actual_durable_path':str(t.relative_to(R)),'actual_sha256':sha(t)})
# Resolve every claimed reuse against exact final stage or already durable repository bytes; preserve unmatched predecessor bytes explicitly.
known={}
for base in [D,R/'data/controlled_publications',R/'backend/data/controlled_publications',R/'internal']:
 for f in base.rglob('*'):
  if f.is_file():known.setdefault(sha(f),str(f))
for x in d['existing_exact_bytes_reused']:
 h=x['sha256']
 if h in known:continue
 f=Path(x['source_path']);assert sha(f)==h;t=L/'worker-evidence/reused-predecessor-objects'/h/f.name;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,t);known[h]=str(t);rows.append({**x,'actual_durable_path':str(t.relative_to(R)),'actual_sha256':sha(t),'reason':'Exact older metadata bytes referenced by preservation plan, absent from final stage after deliberate new current binding corrections.'})
receipt={'schema':'earnalism.actual-worker-evidence-preservation.v1','preserved_at':datetime.now(timezone.utc).isoformat(),'plan_sha256':sha(p),'final_accepted_stage_receipt_sha256':sha(D/'acceptance-receipt.json'),'actual_copies':rows,'unchanged_reuse_count':len(d['existing_exact_bytes_reused']),'unresolved_historical_reference_count':len(d['missing_references']),'scope':'Actual exact local archive copy only; all original/derivative/source/recipe/licence facts preserved, no production observation inferred.'}
(L/'worker-evidence-preservation-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'copies':len(rows),'bytes':sum(x['bytes']for x in rows),'receipt_sha256':sha(L/'worker-evidence-preservation-receipt.json'),'original4':[{'path':x['actual_durable_path'],'sha256':x['actual_sha256']}for x in rows if x['actual_sha256'].startswith(('28acd2','e74da10','9fa719','49cf4e'))]}))
