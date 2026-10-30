"""Fixed prior-stable CLOSED role admission; no provider, variables or mutation."""
from pathlib import Path
import ast, hashlib, json, os
from types import SimpleNamespace
from scripts.purchase_guard_source import validate
from scripts.build_runtime_source_manifest import build
ROOT=Path(__file__).resolve().parents[1]
def effective_redis_flags(source, environment):
    # Source is already bound by validate() in qualify(); never import server.
    names={'MULTI_REPLICA_ENABLED','REDIS_URL','REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED'}
    nodes=[]
    for node in ast.parse(source).body:
        if isinstance(node,ast.FunctionDef) and node.name=='_env_bool':nodes.append(node)
        elif isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in names:nodes.append(node)
    if len(nodes)!=5:raise ValueError('Exact source flag declarations required')
    ns={'os':SimpleNamespace(environ=environment)}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'bound-stable-redis-flags','exec'),ns)
    return {key:ns[key] for key in sorted(names-{'REDIS_URL'})}

def qualify(root=ROOT):
    m,base,closed=validate(root)
    if m['state']!='CLOSED' or m['application_source_sha']!='ca37aee6e6233392987611ff0f84a44179e27410':raise ValueError('Prior-stable CLOSED role required')
    if hashlib.sha256((root/'backend/reading_pass_service.py').read_bytes()).hexdigest()!='91252528b3106d35b54fabf9bfc46dbeac1f4be37ba355d9cca935bfb453853a':raise ValueError('Exact transaction-safeguarded stable service required')
    if any(effective_redis_flags((root/'backend/server.py').read_text(),os.environ).values()):raise ValueError('Rollback Redis must remain OFF')
    if build(root,'HEAD')!=json.loads((root/'backend/.runtime-source-manifest.json').read_text()):raise ValueError('Exact recovery inventory required')
    return {'role':'PRIOR_STABLE_CLOSED_REDIS_OFF','source_verified':True}
if __name__=='__main__':print(json.dumps(qualify()))
