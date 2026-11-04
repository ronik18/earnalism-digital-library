"""Execute only the compiled pure helper on disposable synthetic inputs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from verify_railway_helper_archive import member_name, need, preflight


def regular_members(archive):
    with tarfile.open(archive, 'r:gz') as t:
        return sorted(member_name(x.name) for x in t if x.isfile())


def run(binary):
    results = []
    with tempfile.TemporaryDirectory(prefix='railway-helper-fixtures-') as tmp:
        base = Path(tmp).resolve()
        for case, git_boundary, ignore_name, rule, included in [
            ('absent_git_keeps_gitignored_file', False, '.gitignore', 'ignored.txt\n', True),
            ('present_git_applies_gitignore', True, '.gitignore', 'ignored.txt\n', False),
            ('railwayignore_without_git', False, '.railwayignore', 'ignored.txt\n', False),
            ('ignore_without_git', False, '.ignore', 'ignored.txt\n', False),
        ]:
            root = base / case
            backend = root / 'backend'
            backend.mkdir(parents=True)
            (backend / 'keep.txt').write_text('keep\n')
            (backend / 'ignored.txt').write_text('ignored\n')
            (root / ignore_name).write_text(rule)
            if git_boundary:
                (root / '.git').mkdir()
            output = base / (case + '.tgz')
            subprocess.run([str(binary), str(backend), str(root), str(output)], check=True, timeout=90,
                           env={'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                                'XDG_CONFIG_HOME': str(base / 'empty-config')})
            names = regular_members(output)
            expected = ['backend/keep.txt'] + (['backend/ignored.txt'] if included else [])
            need(names == sorted(expected), 'upstream ignore semantics differ: ' + case)
            results.append({'case': case, 'regular_members': names, 'result': 'PASS_EXECUTED_HELPER'})
        # Link input must be rejected before the upstream function (which follows links).
        root = base / 'link-preflight'
        (root / 'backend').mkdir(parents=True)
        (root / 'backend' / 'link').symlink_to(base / 'outside')
        try:
            preflight(root)
        except ValueError:
            results.append({'case': 'input_link_preflight_rejected', 'result': 'PASS_NO_HELPER_CALL'})
        else:
            raise ValueError('link preflight accepted')
    return {'scope': 'EXACT_UPSTREAM_HELPER_SYNTHETIC_FIXTURES_ONLY', 'provider_calls': 0,
            'native_archive_qualification': False, 'cases': results}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--binary', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    result = run(Path(a.binary).resolve(strict=True))
    with Path(a.output).open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
