"""Verify actual CLI-selected files retain configured and traced function assets."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(root, manifest, *, prebuilt=False):
    root = Path(root).resolve()
    selected = {entry['path'].replace('\\', '/') for entry in manifest['files']}
    config = json.loads((root / 'frontend/vercel.json').read_text())
    required = set()
    for function, settings in config.get('functions', {}).items():
        patterns = settings.get('includeFiles', [])
        if isinstance(patterns, str):
            patterns = [patterns]
        for pattern in patterns:
            matches = [p for p in (root / 'frontend').glob(pattern) if p.is_file()]
            if not matches:
                raise ValueError(f'{function}: missing includeFiles asset {pattern}')
            required.update(p.resolve() for p in matches)
    output = root / '.vercel/output'
    if prebuilt:
        if not (output / 'config.json').is_file():
            raise ValueError('prebuilt output/config.json missing')
        functions = output / 'functions'
        if not functions.is_dir():
            raise ValueError('prebuilt functions missing')
        for config_path in functions.rglob('.vc-config.json'):
            trace = json.loads(config_path.read_text())
            for name in trace.get('filePathMap', {}):
                target = (root / name).resolve()
                if not target.is_relative_to(root) or not target.is_file():
                    raise ValueError(f'missing or external mapped function asset: {name}')
                required.add(target)
        for p in functions.rglob('*'):
            if p.is_symlink():
                try:
                    target = p.resolve(strict=True)
                except FileNotFoundError as error:
                    raise ValueError(f'broken function trace: {p.relative_to(root)}') from error
                if not target.is_relative_to(root):
                    raise ValueError(f'function trace outside deployment root: {p.relative_to(root)}')
                if target.is_file() and not target.is_relative_to(output):
                    required.add(target)
    if not required:
        raise ValueError('no function assets found; packaging check cannot be vacuous')
    missing = sorted(str(p.relative_to(root)) for p in required
                     if str(p.relative_to(root)) not in selected)
    if missing:
        raise ValueError('required function assets excluded from deployment: ' + ', '.join(missing))
    unexpected_build_files = sorted(name for name in selected if name.startswith('frontend/build/')
                                    and root / name not in required)
    if unexpected_build_files:
        raise ValueError('unneeded generated build files included: ' + ', '.join(unexpected_build_files))
    return {'status': 'PASS', 'prebuilt': prebuilt, 'required_assets': {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(required)}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--prebuilt', action='store_true')
    parser.add_argument('--compare', type=Path, help='Require identical critical asset hashes to source packaging.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.root, json.loads(args.manifest.read_text()), prebuilt=args.prebuilt)
    if args.compare:
        other = json.loads(args.compare.read_text())['required_assets']
        for name, digest in other.items():
            if result['required_assets'].get(name) != digest:
                raise ValueError(f'source/prebuilt critical asset differs: {name}')
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end='')
