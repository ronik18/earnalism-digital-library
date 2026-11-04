"""Read-only, test-only exact upstream archive verification; no provider API."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile


def need(condition, message):
    if not condition:
        raise ValueError(message)


def member_name(raw):
    name = raw[2:] if raw.startswith('./') else raw
    name = name.rstrip('/')
    need(name and not name.startswith('/') and '\\' not in name, 'unsafe archive name')
    need(all(x not in ('', '.', '..') for x in name.split('/')), 'unsafe archive components')
    need(name == 'backend' or name.startswith('backend/'), 'archive lost backend prefix')
    return name


def preflight(root):
    root = Path(root)
    need(root.is_absolute() and root.is_dir() and not root.is_symlink(), 'absolute real export required')
    for parent in (root, *root.parents):
        need(not parent.is_symlink(), 'symlink parent')
        for name in ('.railwayignore', '.ignore', '.git'):
            need(not (parent / name).exists() and not (parent / name).is_symlink(), 'unqualified ancestor ignore language or boundary')
    backend = root / 'backend'
    need(backend.is_dir() and not backend.is_symlink(), 'real backend required')
    for directory in (root, backend):
        info = directory.lstat()
        need(info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o022, 'unsafe export directory owner/mode')
    for base, dirs, files in os.walk(backend, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            need(not p.is_symlink(), 'input symlink forbidden')
            info = p.lstat()
            mode = info.st_mode
            need(info.st_uid == os.getuid(), 'input owner differs')
            need(not stat.S_IMODE(mode) & 0o022, 'input writable by others')
            if stat.S_ISREG(mode):
                need(info.st_nlink == 1, 'input hard link forbidden')
            need(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'special input forbidden')
            need(name not in ('.git', '.ignore', '.railwayignore'), 'unqualified nested boundary')
    return root


def git_modes(controller, source):
    need(len(source) == 40 and all(x in '0123456789abcdef' for x in source), 'exact Git input required')
    result = subprocess.run(['git', 'ls-tree', '-rz', '--full-tree', source, '--', 'backend'],
                            cwd=controller, capture_output=True, check=True)
    rows = {}
    for entry in result.stdout.split(b'\0'):
        if not entry:
            continue
        meta, path = entry.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        need(kind == 'blob' and mode in ('100644', '100755'), 'unsupported Git input mode')
        rows[path.decode()] = {'mode': 0o755 if mode == '100755' else 0o644, 'blob_oid': oid}
    return rows


def verify_archive(archive, report, root, modes):
    root = preflight(root)
    need(report.get('native_archive_qualification') is False, 'offline input must remain nonnative')
    ignore = root / '.gitignore'
    actual_ignore = hashlib.sha256(ignore.read_bytes()).hexdigest() if ignore.is_file() else None
    need(not ignore.is_symlink() and actual_ignore == report.get('root_ignore_sha256'), 'root ignore input differs')
    expected = {}
    dirs = {'backend'}
    for row in report['files']:
        name = member_name(row['path'])
        need(name != 'backend' and name not in expected, 'duplicate report member')
        need(set(row) >= {'path', 'bytes', 'sha256'}, 'incomplete member binding')
        expected[name] = row
        for parent in PurePosixPath(name).parents:
            if str(parent) != '.':
                dirs.add(str(parent))
    need(set(expected) == set(modes), 'complete Git backend inventory differs')
    disk = {str(p.relative_to(root)) for p in (root / 'backend').rglob('*') if p.is_file()}
    need(disk == set(expected), 'export disk inventory differs')
    for name, row in expected.items():
        b = (root / name).read_bytes()
        need(len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256'], 'export bytes differ')
        need(stat.S_IMODE((root / name).stat().st_mode) == modes[name]['mode'], 'export Git mode differs')
        need(hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == modes[name]['blob_oid'], 'export Git blob differs')
    seen = set()
    regular = []
    total = 0
    maximum = sum(x['bytes'] for x in expected.values())
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            name = member_name(member.name)
            need(name not in seen, 'duplicate archive entry')
            seen.add(name)
            need(member.isfile() or member.isdir(), 'link or special archive entry')
            if member.isdir():
                need(name in dirs, 'unexpected archive directory')
                continue
            need(name in expected, 'unexpected archive file')
            row = expected[name]
            need(member.size == row['bytes'], 'archive size differs')
            need(member.mode >= 0 and member.mode & ~0o107777 == 0, 'archive mode has unknown bits')
            need(stat.S_IFMT(member.mode) in (0, stat.S_IFREG), 'archive mode conflicts with regular type')
            permissions = stat.S_IMODE(member.mode)
            need(permissions == modes[name]['mode'], f'archive Git mode differs: {name}: raw={member.mode:o}, permissions={permissions:o}')
            total += member.size
            need(total <= maximum, 'archive expanded size exceeds bound')
            f = tar.extractfile(member)
            need(f is not None, 'unreadable regular member')
            h = hashlib.sha256()
            while block := f.read(1024 * 1024):
                h.update(block)
            need(h.hexdigest() == row['sha256'], 'archive content differs')
            regular.append({'path': name, 'bytes': member.size, 'sha256': h.hexdigest(), 'mode': permissions})
    need({x['path'] for x in regular} == set(expected), 'missing archive member')
    regular.sort(key=lambda x: x['path'])
    content_rows = [{k: row[k] for k in ('path', 'bytes', 'sha256')} for row in regular]
    need(content_rows == report['files'], 'canonical member report differs')
    with Path(archive).open('rb') as stream:
        archive_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = json.dumps(content_rows, sort_keys=True, separators=(',', ':')).encode()
    mode_manifest = json.dumps(regular, sort_keys=True, separators=(',', ':')).encode()
    return {'scope': 'EXACT_UPSTREAM_HELPER_ARCHIVE_CONTENT_VERIFIED_NOT_INSTALLED_CLI_UPLOAD_OR_NATIVE_PROOF',
            'input_git_source_sha': report['source'], 'controller_source_sha': report['controller_source'],
            'runtime_expected_sha256': report.get('runtime_expected_sha256'),
            'runtime_input_count': report.get('runtime_input_count'),
            'root_ignore_sha256': report.get('root_ignore_sha256'),
            'provider_git_sha': None, 'provider_git_metadata_status': 'NOT_OBSERVED_NO_PROVIDER_CALL', 'archive_sha256': archive_hash,
            'archive_member_manifest_sha256': hashlib.sha256(manifest).hexdigest(),
            'archive_member_modes_sha256': hashlib.sha256(mode_manifest).hexdigest(),
            'regular_members': len(regular), 'directory_members': len(seen) - len(regular),
            'uncompressed_regular_bytes': total, 'native_archive_qualification': False,
            'provider_upload_performed': False, 'runtime_qualification': False, 'provider_writes': 0,
            'members': regular}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--archive', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--expected-report-sha256', required=True)
    p.add_argument('--export-root', required=True)
    p.add_argument('--controller-root', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    raw = Path(a.report).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == a.expected_report_sha256, 'exact report digest differs')
    report = json.loads(raw)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.controller_root, text=True).strip()
    need(head == report['controller_source'], 'controller source differs')
    output = verify_archive(a.archive, report, a.export_root, git_modes(a.controller_root, report['source']))
    output['offline_export_report_sha256'] = hashlib.sha256(raw).hexdigest()
    target = Path(a.output)
    with target.open('x') as f:
        json.dump(output, f, indent=2)
        f.write('\n')
