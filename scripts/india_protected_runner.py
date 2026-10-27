"""Protected read-only runner integration. This entry point cannot execute a release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from scripts.india_release_observer import NativeMetadataObserver, ProtectedReleasePreflight

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'ronik18/earnalism-digital-library'
CONTRACT = ROOT / 'internal/legal/india_release_source_contract.json'


def verified_source(env, git):
    expected = {
        'GITHUB_REPOSITORY': REPOSITORY,
        'GITHUB_REF': 'refs/heads/main',
        'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'RUNNER_ENVIRONMENT': 'self-hosted',
        'EARNALISM_RUN_MODE': 'READ_ONLY_OBSERVATION',
        'EARNALISM_EXECUTION_ENABLED': 'false',
    }
    if any(env.get(k) != v for k, v in expected.items()):
        raise ValueError('Protected main read-only runner context required')
    sha = env.get('GITHUB_SHA', '')
    if not re.fullmatch('[0-9a-f]{40}', sha) or env.get('EXPECTED_CONTROLLER_SHA') != sha:
        raise ValueError('Exact controller identity required')
    if git('rev-parse', 'HEAD') != sha or git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Controller checkout must be exact and clean')
    return sha


def journal_holds(journal, workspace, temporary):
    """Check existing host storage without creating, migrating or clearing it.

    These checks establish location/permissions only. Durability and protected
    host provisioning remain platform/operator facts, never inferred from a path.
    """
    path = Path(journal)
    if not path.exists():
        return ['FIXED_JOURNAL_NOT_PROVISIONED']
    resolved = path.resolve()
    if resolved != path or not path.is_dir():
        return ['FIXED_JOURNAL_NOT_A_REAL_DIRECTORY']
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            return ['FIXED_JOURNAL_HAS_SYMBOLIC_PARENT']
    if any(resolved == root.resolve() or root.resolve() in resolved.parents
           for root in (Path(workspace), Path(temporary))):
        return ['JOURNAL_MUST_BE_OUTSIDE_EPHEMERAL_RUNNER_DIRECTORIES']
    info = path.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        return ['JOURNAL_OWNER_OR_PERMISSIONS_UNQUALIFIED']
    return ['DURABLE_HOST_AND_PROTECTED_EXECUTOR_ATTESTATION_REQUIRED']


def observe(env, git, observer, contract):
    controller = verified_source(env, git)
    if contract.get('scope') != {'territories': ['IN'], 'deployment_authorized': False,
                                  'publication_authorized': False, 'paid_sessions': False}:
        raise ValueError('Reviewed India-only nonexecution scope required')
    app = contract.get('application_sha', '')
    if not re.fullmatch('[0-9a-f]{40}', app):
        raise ValueError('Reviewed application source contract required')
    if git('rev-parse', app + '^{tree}') != contract.get('application_root_tree'):
        raise ValueError('Application source tree differs from retained contract')
    for name in ('frontend', 'backend'):
        if git('rev-parse', app + ':' + name) != contract.get(name + '_subtree'):
            raise ValueError('Application subtree differs from retained contract')
    # Read the repository-bound contract; never accept dispatch JSON as approval.
    preflight = ProtectedReleasePreflight(observer)
    report = preflight.check({'source_sha': app})
    report['controller_sha'] = controller
    report['source_contract_sha256'] = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()).hexdigest()
    report['holds'] = sorted(set(report['holds'] + journal_holds(
        preflight.JOURNAL, env['GITHUB_WORKSPACE'], env['RUNNER_TEMP'])))
    report['execution_permitted'] = False
    report['provider_mutations'] = 0
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Output is a single sanitized report in the platform temporary directory.
    temporary = Path(os.environ['RUNNER_TEMP']).resolve()
    output = args.output.resolve()
    if output.parent != temporary or args.output.is_symlink():
        raise ValueError('Report must use the runner temporary directory')

    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True, timeout=30).strip()

    failed = False
    try:
        report = observe(os.environ, git, NativeMetadataObserver(ROOT), json.loads(CONTRACT.read_text()))
    except Exception as error:
        # Provider output, environment variables and exception messages may
        # contain sensitive material. Keep only the exception class in artifacts.
        report = {'status': 'OBSERVATION_UNAVAILABLE_HOLD', 'execution_permitted': False,
                  'holds': ['SOURCE_OR_PROVIDER_OBSERVATION_UNVERIFIED'],
                  'error_type': type(error).__name__, 'provider_mutations': 0}
        failed = True
    with output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report.get('status', 'OBSERVED_RELEASE_HOLD'), 'execution_permitted': False,
                      'holds': report['holds'], 'provider_mutations': 0}))
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
