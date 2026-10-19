"""Fail before publication if the built dependency resolution differs from review."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

REFERENCE = Path(__file__).with_name('frontend_build_dependency_reference.json')
FIELDS = ('version', 'resolved', 'integrity')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def runtime_identity(*, cli_path=None, search_path=None):
    # Version probes never inherit the release job's credentials or npm config.
    with tempfile.TemporaryDirectory(prefix='reader-version-probe-') as temp:
        private = Path(temp)
        for name in ('user.npmrc', 'global.npmrc'):
            (private / name).write_text('')
        env = {'PATH': search_path or os.environ['PATH'], 'HOME': temp,
               'NPM_CONFIG_USERCONFIG': str(private / 'user.npmrc'),
               'NPM_CONFIG_GLOBALCONFIG': str(private / 'global.npmrc')}
        probe = lambda cmd: subprocess.check_output(cmd, env=env, timeout=15, text=True).strip()
        cli = cli_path or shutil.which('vercel')
        if not cli:
            raise ValueError('Vercel CLI unavailable')
        package = Path(cli).resolve().parents[1]
        return {'system': platform.system(), 'machine': platform.machine(),
                'node': probe(['node', '--version']), 'npm': probe(['npm', '--version']),
                'vercel': json.loads((package / 'package.json').read_text())['version'],
                'selector_sha256': digest((package / 'dist/chunks/chunk-GNY6U33Z.js').read_bytes())}


def compare_entries(locked, installed, reference):
    expected = {key: {field: value.get(field) for field in FIELDS}
                for key, value in locked.items() if key}
    for key in reference['darwin_optional_omissions']:
        source = locked.get(key, {})
        if source.get('os') != ['darwin'] or source.get('optional') is not True:
            raise ValueError('Unproven optional platform omission')
        del expected[key]
    for key, identity in reference['observed_unlocked_tools'].items():
        if key in expected:
            raise ValueError('Observed unlocked tool unexpectedly present in F lock')
        expected[key] = identity
    actual = {key: {field: value.get(field) for field in FIELDS}
              for key, value in installed.items()}
    if len(actual) != reference['installed_count'] or set(actual) != set(expected):
        raise ValueError('Installed dependency set differs from reviewed resolution')
    if any(actual[key] != expected[key] for key in expected):
        # Do not print unexpected resolved URLs or other potentially private data.
        raise ValueError('Installed dependency version/resolved/integrity differs from review')
    return actual


def regular_bytes(root, relative):
    path = root / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError('Missing or external dependency manifest')
    return path.read_bytes()


def verify(root, reference, runtime):
    root = Path(root).resolve()
    git = lambda *args: subprocess.check_output(['git', '-C', str(root), *args])
    if git('rev-parse', 'HEAD').decode().strip() != reference['frontend_sha']:
        raise ValueError('Unexpected frontend source SHA')
    if git('status', '--porcelain', '--untracked-files=all', '-z'):
        raise ValueError('Dirty frontend source')
    if runtime != reference['runtime']:
        raise ValueError('Build runtime/CLI identity differs from reviewed Linux resolution')
    for name, key in (('package.json', 'package_json_sha256'), ('package-lock.json', 'package_lock_sha256')):
        data = regular_bytes(root, 'frontend/' + name)
        if digest(data) != reference[key] or data != git('show', reference['frontend_sha'] + ':frontend/' + name):
            raise ValueError('Dependency source manifest differs from exact F')
    locked = json.loads(regular_bytes(root, 'frontend/package-lock.json'))['packages']
    installed = json.loads(regular_bytes(root, 'frontend/node_modules/.package-lock.json'))['packages']
    actual = compare_entries(locked, installed, reference)
    encoded = json.dumps(actual, sort_keys=True, separators=(',', ':')).encode()
    return {'status': 'PASS_EXACT_REVIEWED_BUILD_DEPENDENCY_IDENTITIES',
            'source_sha': reference['frontend_sha'], 'source_full_status': 'CLEAN',
            'runtime': runtime, 'installed_count': len(actual),
            'canonical_installed_identity_sha256': digest(encoded), 'installed': actual,
            'reference': reference['provenance'],
            'limit': 'Post-build publication gate; not prevention of prior install execution, output equivalence, or production environment approval.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.source_root, json.loads(REFERENCE.read_text()), runtime_identity())
        encoded = json.dumps(result, indent=2) + '\n'
        if args.output:
            args.output.write_text(encoded)
        print(json.dumps({key: value for key, value in result.items() if key != 'installed'}))
    except Exception:
        # Deliberately omit exception details, source bytes, credentials and env.
        raise SystemExit('BUILD_DEPENDENCY_IDENTITY=FAIL; no publication permitted') from None
