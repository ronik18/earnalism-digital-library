"""Source-only contract; reads explicit Git blobs, never providers or settings."""
import ast
import hashlib
import json
import os
import stat
import types
from pathlib import Path
import re
import subprocess

SCHEMA = 'earnalism.purchase-guard-source.v1'
SUCCESSOR_SCHEMA = 'earnalism.purchase-guard-source.v2'
PAIRED_SCHEMA = 'earnalism.purchase-guard-source.v3'
PATH = 'internal/legal/purchase_guard_source.json'
ANCHOR = '    if ENVIRONMENT == "production" and request.method == "POST" and request.url.path == COMMERCE_ORDER_PATH:\n        commerce = commerce_territory_verdict('
BRANCH = '\n    if ENVIRONMENT == "production" and request.method == "POST" and request.url.path == COMMERCE_ORDER_PATH:\n        return JSONResponse(status_code=503, content={"detail": {"code": "PURCHASE_INITIATION_CLOSED", "message": "New Reading Pass purchases are temporarily paused. Existing reading and listening access remains available."}}, headers={"Cache-Control": "no-store"})\n'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def guard_only_server(approved_base, base):
    if not re.fullmatch('[0-9a-f]{64}', approved_base) or sha(base) != approved_base:
        raise ValueError('Approved base bytes required')
    text = base.decode('utf-8')
    if text.count(ANCHOR) != 1 or 'PURCHASE_INITIATION_CLOSED' in text:
        raise ValueError('Exact unguarded anchor required')
    return text.replace(ANCHOR, BRANCH + ANCHOR, 1).encode('utf-8')

def exact_git_server(repo, ref):
    if not re.fullmatch('[0-9a-f]{40}', ref):
        raise ValueError('Exact Git source SHA required, not placeholder')
    return subprocess.check_output(['git','-c','remote.origin.promisor=false','show',ref+':backend/server.py'],cwd=repo,env={**__import__('os').environ,'GIT_NO_LAZY_FETCH':'1'},timeout=10)

def _preserved_purchase_handlers(historical, application):
    """A successor is not a new financial or territorial policy approval."""
    names = {'enforce_public_release_country', 'payments_create_topup',
             'payments_verify', 'payments_webhook', '_credit_wallet_for_intent',
             'admin_wallet_adjust', 'admin_wallet_refund_review',
             'admin_wallet_refund_approve', 'reading_pass_lease_renew'}
    def functions(source):
        return {n.name: ast.dump(n, include_attributes=False)
                for n in ast.parse(source).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names}
    old, new = functions(historical), functions(application)
    if set(old) != names or old != new:
        raise ValueError('Successor changes protected purchase, financial or lease handlers')


def _validate(repo, *, base_reader=exact_git_server, check_pair=True):
    repo=Path(repo); m=json.loads((repo/PATH).read_text())
    expected={'schema','state','approved_merged_584_sha','approved_base_server_sha256','closed_server_sha256','owner_receipt_path','owner_receipt_sha256'}
    paired = m.get('schema') == PAIRED_SCHEMA
    successor = m.get('schema') in {SUCCESSOR_SCHEMA, PAIRED_SCHEMA}
    if successor:
        expected |= {'application_source_sha', 'application_server_sha256', 'application_closed_server_sha256'}
    if paired:
        expected.add('guarded_bootstrap_source_sha')
    if set(m)!=expected or m['schema'] not in {SCHEMA, SUCCESSOR_SCHEMA, PAIRED_SCHEMA} or m['state'] not in {'OPEN','CLOSED'}:
        raise ValueError('Operational source contract malformed')
    if not re.fullmatch('[0-9a-f]{40}',m['approved_merged_584_sha']):raise ValueError('Unknown actual merged base')
    # Fixed reviewed receipt destination only: arbitrary private paths are forbidden.
    if m['owner_receipt_path']!='internal/legal/purchase_guard_owner_acceptance.json':raise ValueError('Unexpected approval path')
    receipt=(repo/m['owner_receipt_path']).read_bytes()
    if sha(receipt)!=m['owner_receipt_sha256']:raise ValueError('Owner receipt differs')
    approval=json.loads(receipt)
    scope=approval.get('scope',{})
    if approval.get('answer')!='Approve temporary purchase pause' or not all(scope.get(k) is True for k in ('guarded_recovery_bootstrap_on_existing_backend','temporary_new_pass_purchase_pause','reopen_after_verified_final_rollout','remain_closed_if_safe_recovery_not_complete','existing_reader_listener_preserved','verify_refund_webhook_code_preserved')):
        raise ValueError('Required actual owner scope missing')
    base=base_reader(repo,m['approved_merged_584_sha'])
    closed=guard_only_server(m['approved_base_server_sha256'],base)
    if sha(closed)!=m['closed_server_sha256']:raise ValueError('Closed server binding differs')
    if successor:
        application = base_reader(repo, m['application_source_sha'])
        if sha(application) != m['application_server_sha256']:
            raise ValueError('Application source binding differs')
        _preserved_purchase_handlers(base, application)
        closed = guard_only_server(m['application_server_sha256'], application)
        if sha(closed) != m['application_closed_server_sha256']:
            raise ValueError('Successor closed source binding differs')
        base = application
    actual=(repo/'backend/server.py').read_bytes()
    if actual != (closed if m['state']=='CLOSED' else base):raise ValueError('Whole server equality failed')
    if paired and check_pair:
        _validate_pair(repo, m, base, closed)
    return m,base,closed

def validate(repo, *, base_reader=exact_git_server):
    return _validate(repo, base_reader=base_reader)

def validate_purchase_protocol_source(repo, *, base_reader=exact_git_server):
    """Validate exact server/owner/financial protocol, NOT backend recovery.

    Ordinary application CI may change unrelated backend modules. This narrow
    source check cannot qualify that changed backend against historical A/B.
    Native callers must retain validate()/validate_paired_source() unchanged.
    """
    return _validate(repo, base_reader=base_reader, check_pair=False)


def normal_guard_source(repo):
    """Signed-country tests inspect the exact bound underlying application."""
    _,base,_=validate_purchase_protocol_source(repo)
    return base.decode('utf-8')


def _git(repo, *args):
    """Local immutable objects only; never hydrate through credentials/network."""
    return subprocess.check_output(['git', '-c', 'remote.origin.promisor=false', *args],
        cwd=repo, env={**__import__('os').environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1'}, timeout=60)


def _git_blob(repo, ref, path):
    if not re.fullmatch('[0-9a-f]{40}', ref):
        raise ValueError('Exact paired source SHA required')
    return _git(repo, 'show', ref + ':' + path)


def backend_tree(repo, ref):
    """All tracked backend members, including build-only inputs; no path loss."""
    rows = {}
    for item in _git(repo, 'ls-tree', '-rlz', ref, '--', 'backend').split(b'\0'):
        if not item:
            continue
        header, name = item.split(b'\t', 1)
        mode, kind, oid, size = header.decode().split()
        name = name.decode('utf-8')
        if mode not in {'100644', '100755'} or kind != 'blob':
            raise ValueError('Paired backend requires regular committed files')
        rows[name] = {'mode': mode, 'oid': oid, 'bytes': int(size)}
    if not rows:
        raise ValueError('Paired backend unavailable')
    return rows


def _verified_helper_bytes(repo, head, path):
    """No-follow physical read; assume-unchanged/skip-worktree cannot hide drift."""
    raw = _git(repo, 'ls-tree', '-z', head, '--', path).rstrip(b'\0')
    if not raw or b'\0' in raw:
        raise ValueError('Exact committed inventory helper required')
    header, name = raw.split(b'\t', 1)
    mode, kind, _oid = header.decode().split()
    if name.decode() != path or mode not in {'100644', '100755'} or kind != 'blob':
        raise ValueError('Regular committed inventory helper required')
    expected = _git_blob(repo, head, path)
    root = os.open(Path(repo).resolve(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = path.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            os.close(root)
            root = child
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            required = 0o755 if mode == '100755' else 0o644
            if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != required
                    or info.st_size != len(expected) or stream.read() != expected):
                raise ValueError('Committed inventory helper bytes/mode differ: ' + path)
    except OSError as exc:
        raise ValueError('Unsafe committed inventory helper: ' + path) from exc
    finally:
        os.close(root)
    return expected


def _committed_inventory_helpers(repo, head):
    """Execute only both verified immutable helper blobs; never disk module code."""
    builder_path = 'scripts/build_runtime_source_manifest.py'
    contract_path = 'backend/utils/runtime_source_attestation.py'
    # Verify BOTH before executing either, including their physical Git modes.
    builder_bytes = _verified_helper_bytes(repo, head, builder_path)
    contract_bytes = _verified_helper_bytes(repo, head, contract_path)
    contract = types.ModuleType('committed_runtime_source_attestation')
    contract.__file__ = str(Path(repo) / contract_path)
    exec(compile(contract_bytes, contract.__file__ + '@' + head, 'exec'), contract.__dict__)
    builder = types.ModuleType('committed_runtime_source_manifest_builder')
    builder.__file__ = str(Path(repo) / builder_path)
    exec(compile(builder_bytes, builder.__file__ + '@' + head, 'exec'), builder.__dict__)
    # The existing build() algorithm is unchanged, but its disk loader is never used.
    builder.module = lambda _repo: contract
    return builder.build, contract


def _validate_pair(repo, manifest, application, closed):
    """Admit a retained CLOSED ancestor without changing the active normal role."""
    if manifest['state'] != 'OPEN':
        raise ValueError('Paired controller must retain normal OPEN source')
    target = manifest['guarded_bootstrap_source_sha']
    if not re.fullmatch('[0-9a-f]{40}', target):
        raise ValueError('Exact committed bootstrap source required')
    head = _git(repo, 'rev-parse', 'HEAD').decode().strip()
    if target == head:
        raise ValueError('Bootstrap and normal controller roles must differ')
    if subprocess.run(['git', '-c', 'remote.origin.promisor=false', 'merge-base',
            '--is-ancestor', target, head], cwd=repo,
            env={**__import__('os').environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1'},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10).returncode:
        raise ValueError('Bootstrap source must remain an ancestor of controller HEAD')
    parents = _git(repo, 'show', '-s', '--format=%P', target).decode().split()
    if len(parents) != 1:
        raise ValueError('Bootstrap requires one exact normal parent')
    parent = parents[0]
    changed = set(_git(repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z',
        parent, target).decode().rstrip('\0').split('\0'))
    required = {'backend/server.py', 'backend/.runtime-source-manifest.json', PATH}
    if changed != required:
        raise ValueError('Bootstrap differs outside exact three-path containment')
    normal_contract = {key: value for key, value in manifest.items()
        if key != 'guarded_bootstrap_source_sha'}
    normal_contract['schema'] = SUCCESSOR_SCHEMA
    closed_contract = {**normal_contract, 'state': 'CLOSED'}
    if (json.loads(_git_blob(repo, parent, PATH)) != normal_contract
            or json.loads(_git_blob(repo, target, PATH)) != closed_contract):
        raise ValueError('Paired source changes underlying approval or application contract')
    for ref in (parent, target):
        if _git_blob(repo, ref, manifest['owner_receipt_path']) != (Path(repo) / manifest['owner_receipt_path']).read_bytes():
            raise ValueError('Paired source changed actual owner receipt')
    if (_git_blob(repo, parent, 'backend/server.py') != application
            or _git_blob(repo, target, 'backend/server.py') != closed):
        raise ValueError('Paired server is not the exact deterministic guard transform')
    normal_tree, closed_tree, active_tree = (backend_tree(repo, ref)
        for ref in (parent, target, head))
    if normal_tree != active_tree:
        raise ValueError('Normal controller backend differs from qualified normal parent')
    if set(normal_tree) != set(closed_tree):
        raise ValueError('Bootstrap backend membership changed')
    for path in normal_tree:
        old, new = normal_tree[path], closed_tree[path]
        if old['mode'] != new['mode']:
            raise ValueError('Bootstrap executable mode changed')
        if path not in required and old != new:
            raise ValueError('Bootstrap changed unrelated backend source')
    # Verify consumed executable helpers independently of Git's stat/index flags,
    # then reuse their immutable committed bytes, not current disk imports.
    build, _contract = _committed_inventory_helpers(repo, head)
    manifests = {}
    for role, ref in (('normal', parent), ('closed', target)):
        declared = json.loads(_git_blob(repo, ref, 'backend/.runtime-source-manifest.json'))
        if declared != build(repo, ref):
            raise ValueError('Paired runtime inventory does not match full committed source')
        manifests[role] = declared['expected_sha256']
    # Root ignore semantics must not drift between the exported role and controller.
    for ref in (parent, target):
        old = _git(repo, 'ls-tree', ref, '--', '.gitignore')
        current = _git(repo, 'ls-tree', head, '--', '.gitignore')
        if old != current:
            raise ValueError('Paired root ignore semantics changed')
    return {'schema': 'earnalism.guarded-bootstrap-source-pair.v1',
        'scope': 'SOURCE_ONLY_NOT_PROVIDER_OR_APPROVAL_QUALIFICATION',
        'controller_source_sha': head, 'bootstrap_source_sha': target,
        'controller_contract_committed': json.loads(_git_blob(repo, head, PATH)) == manifest,
        'normal_parent_source_sha': parent,
        'normal_backend_tree': _git(repo, 'rev-parse', parent + ':backend').decode().strip(),
        'closed_backend_tree': _git(repo, 'rev-parse', target + ':backend').decode().strip(),
        'normal_runtime_sha256': manifests['normal'],
        'closed_runtime_sha256': manifests['closed'],
        'normal_server_sha256': sha(application), 'closed_server_sha256': sha(closed),
        'provider_writes': 0}


def validate_paired_source(repo):
    manifest, application, closed = _validate(repo, check_pair=False)
    if manifest['schema'] != PAIRED_SCHEMA:
        raise ValueError('Explicit committed source pair required')
    return _validate_pair(Path(repo), manifest, application, closed)
