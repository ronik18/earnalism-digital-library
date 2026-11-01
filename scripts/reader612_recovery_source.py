"""Offline exact prior-Reader CLOSED role. Never imports the server or a provider.

The immutable recovery commit is separate from the normal OPEN application PR.
The historical owner receipt proves source semantics only, never execution authority.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts.purchase_guard_source import guard_only_server, validate
from scripts.build_runtime_source_manifest import build

BASE = '3fe9bc598d5c7fa1a8f1d0265bcba0ed704b5a92'
PRIOR = '9a1b166e189cebc9b2b75baf20a95d2eb33a3c12'
PATH = 'internal/legal/reader612_recovery_source.json'
ROLE = 'PRIOR_READER_CORE_CLOSED_RECOVERY'


def blob(repo, ref, path):
    if not re.fullmatch('[0-9a-f]{40}', ref):
        raise ValueError('Immutable source required')
    return subprocess.check_output(['git', '-c', 'remote.origin.promisor=false',
        'show', ref + ':' + path], cwd=repo, timeout=30,
        env={**__import__('os').environ, 'GIT_NO_LAZY_FETCH': '1'})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def definitions(data):
    result = {}
    for node in ast.parse(data).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = ast.dump(node, include_attributes=False)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[node.name + '.' + child.name] = ast.dump(child, include_attributes=False)
    return result


def materialize(repo):
    """Only a fresh isolated checkout at BASE; never modify an existing candidate."""
    repo = Path(repo)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=repo, text=True).strip()
    if head != BASE or dirty:
        raise ValueError('Clean exact base required')
    current = blob(repo, BASE, 'backend/server.py')
    prior = blob(repo, PRIOR, 'backend/reading_pass_service.py')
    new = blob(repo, BASE, 'backend/reading_pass_service.py')
    a, b = definitions(new), definitions(prior)
    delta = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
    if delta != {'ReadingPassService.renew_lease', 'ReadingPassService.start_session', '_preparation_retry_context'}:
        raise ValueError('Unexpected Reader recovery delta')
    (repo/'backend/server.py').write_bytes(guard_only_server(sha(current), current))
    (repo/'backend/reading_pass_service.py').write_bytes(prior)
    m = json.loads((repo/'internal/legal/purchase_guard_source.json').read_text())
    m.update(state='CLOSED', application_source_sha=BASE,
             application_server_sha256=sha(current),
             application_closed_server_sha256=sha((repo/'backend/server.py').read_bytes()))
    (repo/'internal/legal/purchase_guard_source.json').write_text(json.dumps(m, indent=2)+'\n')
    record = {'schema':'earnalism.reader612-recovery-source.v1', 'role':ROLE,
        'base_source_sha':BASE, 'prior_reader_source_sha':PRIOR,
        'prior_reader_sha256':sha(prior), 'closed_server_sha256':m['application_closed_server_sha256'],
        'execution_authorized':False, 'native_qualified':False}
    (repo/PATH).write_text(json.dumps(record, indent=2)+'\n')
    return record


def qualify(repo, *, environment):
    """Verify actual role files, Git inventory and source defaults, not a SHA label."""
    from scripts.qualify_stable_rollback_profile import effective_redis_flags
    repo = Path(repo)
    r = json.loads((repo/PATH).read_text())
    expected = {'schema','role','base_source_sha','prior_reader_source_sha',
        'prior_reader_sha256','closed_server_sha256','execution_authorized','native_qualified'}
    if (set(r) != expected or r['schema'] != 'earnalism.reader612-recovery-source.v1'
            or r['role'] != ROLE or r['base_source_sha'] != BASE or r['prior_reader_source_sha'] != PRIOR
            or r['execution_authorized'] is not False or r['native_qualified'] is not False):
        raise ValueError('Exact source-only role required')
    m, _, closed = validate(repo)
    if m['state'] != 'CLOSED' or m['application_source_sha'] != BASE or sha(closed) != r['closed_server_sha256']:
        raise ValueError('Current CLOSED server required')
    prior = blob(repo, PRIOR, 'backend/reading_pass_service.py')
    if sha(prior) != r['prior_reader_sha256'] or (repo/'backend/reading_pass_service.py').read_bytes() != prior:
        raise ValueError('Exact prior Reader required')
    manifest = json.loads((repo/'backend/.runtime-source-manifest.json').read_text())
    baseline = json.loads(blob(repo, BASE, 'backend/.runtime-source-manifest.json'))
    old = {x['path']:x for x in baseline['files']}
    actual = {x['path']:x for x in manifest['files']}
    if set(old) != set(actual) or {p for p in old if old[p] != actual[p]} != {'server.py','reading_pass_service.py'}:
        raise ValueError('Only server and Reader payload delta permitted')
    if build(repo, 'HEAD') != manifest:
        raise ValueError('Exact recovery Git inventory required')
    # Hash actual files as well, so a clean Git label cannot hide an altered payload.
    for p, row in actual.items():
        data = (repo/'backend'/p).read_bytes()
        if len(data) != row['bytes'] or sha(data) != row['sha256']:
            raise ValueError('Actual recovery payload differs')
    if any(effective_redis_flags((repo/'backend/server.py').read_text(), environment).values()):
        raise ValueError('Rollback Redis must remain OFF')
    return {'role':ROLE, 'source_verified':True, 'runtime_sha256':manifest['expected_sha256'],
        'file_count':len(actual), 'execution_authorized':False, 'native_qualified':False}


def qualify_binding(repo, binding, *, environment):
    from scripts.backend_upload_payload import qualify as payload_qualify
    repo = Path(repo)
    if (binding.get('schema') != 'earnalism.reader612-native-source-binding.v1'
            or binding.get('role') != ROLE or binding.get('application_base') != BASE
            or binding.get('prior_reader_source') != PRIOR
            or binding.get('execution_authorized') is not False or binding.get('native_qualified') is not False):
        raise ValueError('Source preparation is not execution authority')
    result = qualify(repo, environment=environment)
    identity = subprocess.check_output(['git','rev-parse','HEAD','HEAD^{tree}'], cwd=repo, text=True).splitlines()
    if identity != [binding['source_sha'], binding['tree_sha']]:
        raise ValueError('Recovery source/tree mismatch')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=all'], cwd=repo).strip():
        raise ValueError('Clean recovery source required')
    payload = payload_qualify(repo)
    membership = sha(json.dumps(payload['files'], sort_keys=True, separators=(',',':')).encode())
    if (membership != binding['payload_membership_sha256'] or len(payload['files']) != binding['payload_files']
            or result['runtime_sha256'] != binding['runtime_sha256']):
        raise ValueError('Recovery payload binding mismatch')
    return {**result, 'source_sha':identity[0], 'tree_sha':identity[1],
        'payload_membership_sha256':membership, 'payload_files':len(payload['files']),
        'scope':'OFFLINE_SOURCE_AND_CLI_MEMBERSHIP_NOT_NATIVE_QUALIFICATION'}


if __name__ == '__main__':
    import argparse
    import os
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--binding', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(qualify_binding(args.source_root, json.loads(args.binding.read_text()),
        environment={k:os.environ[k] for k in ('REDIS_CACHE_ENABLED','REDIS_PUBLIC_METADATA_ENABLED','MULTI_REPLICA_ENABLED','REDIS_URL') if k in os.environ})))
