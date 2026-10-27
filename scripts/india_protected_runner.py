"""Protected read-only runner integration. This entry point cannot execute a release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from scripts.india_release_observer import (
    NativeMetadataObserver, ProtectedReleasePreflight, journal_location_holds as journal_holds,
)

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'ronik18/earnalism-digital-library'
CONTRACT = ROOT / 'internal/legal/india_release_source_contract.json'


def verified_source(env, git):
    expected = {
        'GITHUB_REPOSITORY': REPOSITORY,
        'GITHUB_REF': 'refs/heads/main',
        'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'EARNALISM_RUN_MODE': 'READ_ONLY_OBSERVATION',
        'EARNALISM_EXECUTION_ENABLED': 'false',
    }
    if any(env.get(k) != v for k, v in expected.items()):
        raise ValueError('Protected main read-only runner context required')
    if env.get('RUNNER_ENVIRONMENT') not in {'self-hosted', 'github-hosted'}:
        raise ValueError('Known platform runner required for read-only observation')
    sha = env.get('GITHUB_SHA', '')
    if not re.fullmatch('[0-9a-f]{40}', sha) or env.get('EXPECTED_CONTROLLER_SHA') != sha:
        raise ValueError('Exact controller identity required')
    if git('rev-parse', 'HEAD') != sha or git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Controller checkout must be exact and clean')
    return sha


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
    report = preflight.check({'source_sha': app}, workspace=env['GITHUB_WORKSPACE'],
                             temporary=env['RUNNER_TEMP'])
    report['controller_sha'] = controller
    report['observation_runner'] = env['RUNNER_ENVIRONMENT']
    report['source_contract_sha256'] = hashlib.sha256(
        json.dumps(contract, sort_keys=True).encode()).hexdigest()
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
