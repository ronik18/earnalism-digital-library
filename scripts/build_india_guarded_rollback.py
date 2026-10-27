"""Build an offline guarded containment source; never deploy, publish or run server."""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'f98ce89f02f55e688e21a4ed5e02ca4b6c516d16'
GUARD = 'f98ce89f02f55e688e21a4ed5e02ca4b6c516d16'
BACKEND_TREE = '1dc5a64416b92980e31119bea76f9333e09f7bcd'
CLOSED_BRANCH = '''
    if ENVIRONMENT == "production" and request.method == "POST" and request.url.path == COMMERCE_ORDER_PATH:
        return JSONResponse(status_code=503, content={"detail": {"code": "PURCHASE_INITIATION_CLOSED"}}, headers={"Cache-Control": "no-store"})
'''


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, timeout=60)


def function(source):
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.AsyncFunctionDef)
             and n.name == 'enforce_public_release_country']
    if len(nodes) != 1:
        raise ValueError('Ambiguous middleware')
    return nodes[0]


def guard_only_server(base, approved):
    if base != approved:
        raise ValueError('Containment must retain the entire qualified current server')
    node = function(base)
    lines = base.splitlines(keepends=True)
    # Add one fail-closed branch after the docstring. All current guard,
    # settlement, Listener and balance code is retained byte-for-byte.
    insert = node.body[0].end_lineno
    result = ''.join(lines[:insert]) + CLOSED_BRANCH + ''.join(lines[insert:])
    reduced = function(result)
    reduced.body.pop(1)
    if ast.dump(reduced, include_attributes=False) != ast.dump(node, include_attributes=False):
        raise ValueError('Containment changed existing middleware')
    ast.parse(result)
    return result


def build(output):
    output = output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('Use a new output directory outside the repository')
    if git('rev-parse', BASE + ':backend').decode().strip() != BACKEND_TREE:
        raise ValueError('Frozen backend subtree mismatch')
    base = git('show', BASE + ':backend/server.py').decode()
    approved = git('show', GUARD + ':backend/server.py').decode()
    server = guard_only_server(base, approved).encode()
    output.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(git('archive', BASE, 'backend'))) as archive:
        for member in archive.getmembers():
            target = output / member.name
            if not target.resolve().is_relative_to(output) or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe source archive member')
            if member.isdir(): target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
                # Git tar archives can add group-write permission (0664/0775).
                # Git source tracks only canonical0644 versus executable0755.
                os.chmod(target, 0o755 if member.mode & 0o111 else 0o644)
    (output / 'backend/server.py').write_bytes(server)
    files = {str(p.relative_to(output)): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                                        'mode': oct(p.stat().st_mode & 0o777)}
             for p in sorted(output.rglob('*')) if p.is_file()}
    report = {'status': 'OFFLINE_SOURCE_BUILT_NOT_RELEASE_QUALIFIED', 'base': BASE,
              'backend_subtree': BACKEND_TREE,
              'guard_source': GUARD, 'changed_paths': ['backend/server.py'],
              'files': files, 'source_manifest_sha256': hashlib.sha256(
                  json.dumps(files, sort_keys=True).encode()).hexdigest(),
              'provider_artifact': None, 'provider_git_sha': None,
              'protected_approval': None, 'deployment_authorized': False,
              'requires': ['reviewed immutable source identity', 'actual isolated qualification',
                           'provider-built rollback artifact/config qualification',
                           'protected rollback approval'],
              'limitation': 'Current-source fail-closed purchase containment; retains latest financial, Listener and entitlement code. Not generic failure recovery or approved provider rollback.'}
    (output / 'SOURCE-RECEIPT.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = build(args.output)
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
