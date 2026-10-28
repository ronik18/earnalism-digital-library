"""Read immutable source/check evidence only. Never authorizes or executes a release."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'internal/legal/india_release_source_contract.json'
SEO_METADATA = 'frontend/static-seo/controlled-publication-public.json'
ATTRIBUTION_DIGESTS = {
    'data/controlled_publications/radharani/public_book.json',
    'data/controlled_publications/radharani/publication_manifest.json',
}


def qualify_ui_reuse(reuse, app, git):
    """Reuse UI evidence only across the exact reviewed attribution digest delta."""
    baseline, reviewed = reuse['baseline_sha'], reuse['review_sha']
    for value in (baseline, reviewed, reuse['baseline_root_tree'], reuse['old_blob'], reuse['new_blob']):
        if not re.fullmatch('[0-9a-f]{40}', value):
            raise ValueError('Invalid UI reuse identity')
    git('merge-base', '--is-ancestor', baseline, app)
    if (git('rev-parse', baseline + '^{tree}') != reuse['baseline_root_tree']
            or git('rev-parse', reviewed + '^{tree}') != reuse['baseline_root_tree']):
        raise ValueError('Prior UI review root differs')
    if git('diff', '--name-only', baseline, app, '--', 'frontend').splitlines() != [SEO_METADATA]:
        raise ValueError('Unexpected frontend changes outside reviewed metadata')
    for rev, blob in ((baseline, reuse['old_blob']), (app, reuse['new_blob'])):
        if git('rev-parse', rev + ':' + SEO_METADATA) != blob:
            raise ValueError('Reviewed metadata blob differs')
    before = json.loads(git('show', baseline + ':' + SEO_METADATA))
    after = json.loads(git('show', app + ':' + SEO_METADATA))
    left, right = before.pop('generated_from'), after.pop('generated_from')
    if before != after or set(left) != set(right):
        raise ValueError('Unexpected public metadata changes')
    if {key for key in left if left[key] != right[key]} != ATTRIBUTION_DIGESTS:
        raise ValueError('Unexpected attribution digest changes')
    for key in ATTRIBUTION_DIGESTS:
        if right[key] != hashlib.sha256(git('show', app + ':' + key).encode()).hexdigest():
            raise ValueError('Derived attribution digest differs from source')


def qualify(contract, git, checks):
    """Git and GitHub reads are injected so failure cases need no provider access."""
    if contract['scope'] != {'territories': ['IN'], 'deployment_authorized': False,
                             'publication_authorized': False, 'paid_sessions': False}:
        raise ValueError('Preparation scope changed')
    for key in ('application_sha', 'backend_artifact_sha', 'backend_review_sha',
                'frontend_artifact_sha', 'frontend_review_sha', 'application_root_tree', 'backend_subtree',
                'frontend_subtree'):
        if not re.fullmatch('[0-9a-f]{40}', contract[key]):
            raise ValueError('Invalid immutable source identity: ' + key)
    app = contract['application_sha']
    backend = contract['backend_artifact_sha']
    frontend = contract['frontend_artifact_sha']
    reviewed_front = contract['frontend_review_sha']
    reviewed_back = contract['backend_review_sha']
    controller = git('rev-parse', 'HEAD')
    if git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Controller checkout is not clean')
    git('merge-base', '--is-ancestor', backend, app)
    git('merge-base', '--is-ancestor', frontend, app)
    git('merge-base', '--is-ancestor', app, controller)
    if git('rev-parse', app + '^{tree}') != contract['application_root_tree']:
        raise ValueError('Application root mismatch')
    # Squash-reviewed heads need not be ancestors. Require exact full-root equality,
    # then actual successful checks on that retained reviewed head, never SHA labels.
    for merged, reviewed in ((frontend, reviewed_front), (backend, reviewed_back)):
        if git('rev-parse', merged + '^{tree}') != git('rev-parse', reviewed + '^{tree}'):
            raise ValueError('Reviewed and merged trees differ')
    for rev in (backend, app, controller):
        if git('rev-parse', rev + ':backend') != contract['backend_subtree']:
            raise ValueError('Backend source changed')
    for rev in (app, frontend, reviewed_front, controller):
        if git('rev-parse', rev + ':frontend') != contract['frontend_subtree']:
            raise ValueError('Frontend source changed')
    reuse = contract.get('frontend_ui_review_reuse')
    if contract.get('ui_review_mode') == 'EXACT_APPLICATION_REVIEW':
        if reuse is not None:
            raise ValueError('Exact application review must not reuse prior UI evidence')
        if not {'focused-owner-review', 'seamless-brand-review', 'verify-published-owner-review'}.issubset(
                contract['required_checks'].get(reviewed_front, [])):
            raise ValueError('Exact application browser review checks missing')
        review_sources = (reviewed_front, reviewed_back)
    else:
        if contract.get('ui_review_mode') is not None:
            raise ValueError('Unsupported UI review mode')
        qualify_ui_reuse(reuse, app, git)
        review_sources = (reviewed_front, reviewed_back, reuse['review_sha'])
    required_checks = contract['required_checks']
    for reviewed in review_sources:
        if not {'regression gate', 'reconcile'}.issubset(required_checks.get(reviewed, [])):
            raise ValueError('Reviewed source qualification checks missing')
    for rev, required in required_checks.items():
        runs = checks(rev)
        for name in required:
            matching = [r for r in runs if r['name'] == name]
            if not matching or any(r['status'] != 'completed' or r['conclusion'] != 'success' for r in matching):
                raise ValueError('Exact-head check unavailable or unsuccessful: ' + name)
    return {'status': 'SOURCE_QUALIFIED_EXECUTION_HOLD', 'application_sha': app,
            'backend_artifact_sha': backend, 'frontend_artifact_sha': frontend,
            'frontend_review_sha': reviewed_front, 'backend_review_sha': reviewed_back,
            'controller_candidate_sha': controller, 'controller_review_accepted': False,
            'application_root_tree': contract['application_root_tree'],
            'backend_subtree': contract['backend_subtree'],
            'frontend_subtree': contract['frontend_subtree'],
            'identity_kind': 'REVIEWED_GIT_SOURCE_NOT_PROVIDER_ARTIFACT',
            'provider_artifacts_qualified': False, 'frontend_binary_reuse_approved': False,
            'provider_identity_verified': False, 'rollback_approved': False,
            'protected_release_approval': None, 'deployment_authorized': False,
            'publication_authorized': False, 'paid_sessions': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    def git(*a):
        value = subprocess.check_output(['git', *a], cwd=ROOT, text=True, timeout=30)
        return value if a[0] == 'show' else value.strip()

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
