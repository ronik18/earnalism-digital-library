"""Read immutable source/check evidence only. Never authorizes or executes a release."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'internal/legal/india_release_source_contract.json'


def qualify(contract, git, checks):
    """Git and GitHub reads are injected so failure cases need no provider access."""
    if contract['scope'] != {'territories': ['IN'], 'deployment_authorized': False,
                             'publication_authorized': False, 'paid_sessions': False}:
        raise ValueError('Preparation scope changed')
    for key in ('application_sha', 'backend_artifact_sha', 'backend_review_sha',
                'frontend_review_sha', 'application_root_tree', 'backend_subtree',
                'frontend_subtree'):
        if not re.fullmatch('[0-9a-f]{40}', contract[key]):
            raise ValueError('Invalid immutable source identity: ' + key)
    app = contract['application_sha']
    backend = contract['backend_artifact_sha']
    reviewed_front = contract['frontend_review_sha']
    reviewed_back = contract['backend_review_sha']
    controller = git('rev-parse', 'HEAD')
    if git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Controller checkout is not clean')
    git('merge-base', '--is-ancestor', backend, app)
    git('merge-base', '--is-ancestor', app, controller)
    if git('rev-parse', app + '^{tree}') != contract['application_root_tree']:
        raise ValueError('Application root mismatch')
    # Squash-reviewed heads need not be ancestors. Require exact full-root equality,
    # then actual successful checks on that retained reviewed head, never SHA labels.
    for merged, reviewed in ((app, reviewed_front), (backend, reviewed_back)):
        if git('rev-parse', merged + '^{tree}') != git('rev-parse', reviewed + '^{tree}'):
            raise ValueError('Reviewed and merged trees differ')
    for rev in (backend, app, controller):
        if git('rev-parse', rev + ':backend') != contract['backend_subtree']:
            raise ValueError('Backend source changed')
    for rev in (app, reviewed_front, controller):
        if git('rev-parse', rev + ':frontend') != contract['frontend_subtree']:
            raise ValueError('Frontend source changed')
    for rev, required in contract['required_checks'].items():
        runs = checks(rev)
        for name in required:
            matching = [r for r in runs if r['name'] == name]
            if not matching or any(r['status'] != 'completed' or r['conclusion'] != 'success' for r in matching):
                raise ValueError('Exact-head check unavailable or unsuccessful: ' + name)
    return {'status': 'SOURCE_QUALIFIED_EXECUTION_HOLD', 'application_sha': app,
            'backend_artifact_sha': backend, 'frontend_artifact_sha': app,
            'controller_candidate_sha': controller, 'controller_review_accepted': False,
            'application_root_tree': contract['application_root_tree'],
            'backend_subtree': contract['backend_subtree'],
            'frontend_subtree': contract['frontend_subtree'],
            'provider_identity_verified': False, 'rollback_approved': False,
            'protected_release_approval': None, 'deployment_authorized': False,
            'publication_authorized': False, 'paid_sessions': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    def git(*a):
        return subprocess.check_output(['git', *a], cwd=ROOT, text=True, timeout=30).strip()

    def checks(rev):
        # No credentials or provider variables are read. This endpoint is read-only.
        raw = subprocess.check_output(['gh', 'api', '--paginate',
            f'repos/ronik18/earnalism-digital-library/commits/{rev}/check-runs?per_page=100',
            '--jq', '.check_runs[] | {name,status,conclusion}'], text=True, timeout=60)
        return [json.loads(line) for line in raw.splitlines() if line]

    report = qualify(json.loads(CONTRACT.read_text()), git, checks)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
