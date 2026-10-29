"""Bounded byte snapshot of declared delivered backend source; never a Git SHA claim."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time
from functools import lru_cache

SCHEMA = 'earnalism.runtime-source-files.v1'
SCOPE = 'git-tracked-backend-delivery-excluding-build-only-files-and-manifest-v1'
MANIFEST = '.runtime-source-manifest.json'
MAX_FILES = 4096
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_SECONDS = 4.0


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def delivered_path(path):
    """Fixed contract matching the reviewed backend .dockerignore; no private files."""
    if not isinstance(path, str) or not path or '\\' in path:
        return False
    p = PurePosixPath(path)
    if p.is_absolute() or str(p) != path or any(x in {'.', '..'} for x in p.parts):
        return False
    if path == MANIFEST or any(x in {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'venv', '.venv', 'tests'} for x in p.parts):
        return False
    if any(x == '.env' or x.startswith('.env.') or x in {'.git', '.ssh', '.aws'} for x in p.parts):
        return False
    if p.suffix in {'.pyc', '.pyo', '.pyd', '.pem', '.key'}:
        return False
    return True


def inventory_digest(rows):
    return hashlib.sha256(canonical({'scope': SCOPE, 'files': rows})).hexdigest()


def _regular_open(root, relative):
    # Anchor every component to an already-open directory: no traversal, symlink
    # following or blocking FIFO/device open, even across a rename race.
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise ValueError('not regular')
        return fd
    finally:
        os.close(directory)


def measure(root, *, clock=time.monotonic):
    """No path/content/environment output. A result covers only the declared files."""
    started = clock()
    fail = {'status': 'UNAVAILABLE', 'scope': SCOPE}
    try:
        root = Path(root)
        fd = _regular_open(root, MANIFEST)
        with os.fdopen(fd, 'rb') as f:
            raw = f.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ValueError('manifest bound')
        manifest = json.loads(raw)
        if set(manifest) != {'schema', 'scope', 'files', 'expected_sha256'} or manifest['schema'] != SCHEMA or manifest['scope'] != SCOPE:
            raise ValueError('manifest schema')
        rows = manifest['files']
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_FILES:
            raise ValueError('file bound')
        names = []
        total = 0
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'path', 'bytes', 'sha256'} or not delivered_path(row['path']):
                raise ValueError('entry')
            if type(row['bytes']) is not int or row['bytes'] < 0:
                raise ValueError('size')
            if not isinstance(row['sha256'], str) or len(row['sha256']) != 64 or any(c not in '0123456789abcdef' for c in row['sha256']):
                raise ValueError('digest')
            total += row['bytes']; names.append(row['path'])
        if names != sorted(set(names)) or total > MAX_TOTAL_BYTES or manifest['expected_sha256'] != inventory_digest(rows):
            raise ValueError('inventory bound or digest')
        actual = []
        for row in rows:
            if clock() - started > MAX_SECONDS:
                raise TimeoutError('time bound')
            fd = _regular_open(root, row['path'])
            with os.fdopen(fd, 'rb') as f:
                before = os.fstat(f.fileno())
                if before.st_size != row['bytes']:
                    raise ValueError('size mismatch')
                digest = hashlib.sha256(); count = 0
                while True:
                    if clock() - started > MAX_SECONDS:
                        raise TimeoutError('time bound')
                    data = f.read(65536)
                    if not data: break
                    count += len(data)
                    if count > row['bytes']: raise ValueError('file grew')
                    digest.update(data)
                after = os.fstat(f.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or count != row['bytes']:
                    raise ValueError('file changed')
            actual.append({'path': row['path'], 'bytes': count, 'sha256': digest.hexdigest()})
        observed = inventory_digest(actual)
        return {'status': 'MEASURED_MATCHES_MANIFEST' if observed == manifest['expected_sha256'] else 'MISMATCH',
                'scope': SCOPE, 'observed_sha256': observed,
                'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'file_count': len(rows),
                'measured_at_unix': time.time()}
    except Exception as error:
        return {**fail, 'reason': type(error).__name__}


@lru_cache(maxsize=1)
def runtime_source_attestation():
    # Immutable container source snapshot, once per process: no repeated 300MB
    # hashing on the public health route. Environment/provider IDs remain separate.
    result = measure(Path(__file__).resolve().parents[1])
    return {**result, "snapshot_cached_for_process": True}
