"""Fixed prior-stable CLOSED role admission; no provider, variables or mutation."""
from pathlib import Path
import hashlib, json, os
from scripts.purchase_guard_source import validate
from scripts.build_runtime_source_manifest import build
ROOT=Path(__file__).resolve().parents[1]
def qualify(root=ROOT):
    m,base,closed=validate(root)
    if m['state']!='CLOSED' or m['application_source_sha']!='ca37aee6e6233392987611ff0f84a44179e27410':raise ValueError('Prior-stable CLOSED role required')
    if hashlib.sha256((root/'backend/reading_pass_service.py').read_bytes()).hexdigest()!='91252528b3106d35b54fabf9bfc46dbeac1f4be37ba355d9cca935bfb453853a':raise ValueError('Exact transaction-safeguarded stable service required')
    if any(os.environ.get(k,'false').lower() not in {'false','0','off','no',''} for k in ['REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED','MULTI_REPLICA_ENABLED']):raise ValueError('Rollback Redis must remain OFF')
    if build(root,'HEAD')!=json.loads((root/'backend/.runtime-source-manifest.json').read_text()):raise ValueError('Exact recovery inventory required')
    return {'role':'PRIOR_STABLE_CLOSED_REDIS_OFF','source_verified':True}
if __name__=='__main__':print(json.dumps(qualify()))
