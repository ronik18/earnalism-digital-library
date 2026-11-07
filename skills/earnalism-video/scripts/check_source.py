#!/usr/bin/env python3
"""Verify archived source hashes; never qualifies runtime assets or publication."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess


def check(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    expected = manifest['files']
    if manifest.get('production_or_publication_approval') is not False:
        raise ValueError('A source archive cannot grant production/publication approval')
    for name, digest in expected.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or name == 'SOURCE_MANIFEST.json':
            raise ValueError('Unsafe or recursive source manifest path: ' + name)
        path = root / name
        if path.is_symlink() or root not in path.resolve().parents:
            raise ValueError('Source leaves archive: ' + name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Missing or changed source: ' + name)
    # In a Git checkout, also reject tracked files omitted from the hash inventory.
    result = subprocess.run(['git', 'ls-files', '-z', '--', '.'], cwd=root,
                            capture_output=True, check=False)
    if result.returncode == 0:
        tracked = set(result.stdout.decode().rstrip('\0').split('\0')) - {'SOURCE_MANIFEST.json', ''}
        if tracked != set(expected):
            raise ValueError('Tracked inventory differs: ' + repr(sorted(tracked ^ set(expected))))
    return {'status': 'PASS', 'source_files': len(expected),
            'runtime_assets_or_publication_approved': False}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default=str(Path(__file__).resolve().parents[1]))
    print(json.dumps(check(parser.parse_args().root), indent=2))
