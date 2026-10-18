"""Complete bounded payload/report export. No provider or build operations."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

CAP = 64 * 1024 * 1024


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode()


def safe_name(name):
    value = PurePosixPath(name)
    if value.is_absolute() or not name or any(x in ('..', '.', '') for x in name.split('/')) or '\\' in name or re.match('^[A-Za-z]:', name):
        raise ValueError('Unsafe capture entry')
    if any(x.lower().startswith('.env') or x.lower() in ('.git', 'node_modules', '.npm-cache', '.secrets') for x in value.parts):
        raise ValueError('Private/cache/source path cannot enter capture')
    return value


def public_json(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if '/' not in key and re.search(r'(?:^|_)(?:secret|password|credential|token)(?:$|_)', key, re.I) and value not in (None, '', False, [], {}):
                raise ValueError('Unexpected private JSON field; do not redact/claim immutable equality')
            public_json(value)
    elif isinstance(data, list):
        for value in data:
            public_json(value)


def seal(root, reports, selected, context, output, cap=CAP):
    if not 0 < cap <= CAP:
        raise ValueError('Capture cap cannot be increased')
    root, reports, output = Path(root).resolve(), Path(reports).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(root):
        raise ValueError('Capture output must be fresh and outside source')
    output.mkdir()
    blobs, rows = {}, []

    def add(name, data, mode, origin=None):
        safe_name(name)
        if name in blobs:
            raise ValueError('Duplicate capture entry')
        if name.endswith('.json'):
            public_json(json.loads(data))
        if sum(len(x) for x in blobs.values()) + len(data) > cap:
            raise ValueError('Complete raw capture exceeds 64MiB; no omissions permitted')
        blobs[name] = data
        rows.append({'path': name, 'mode': mode, 'size': len(data),
                     'sha256': hashlib.sha256(data).hexdigest(), 'original_internal_link': origin})

    required = json.loads((reports / 'prebuilt-packaging.json').read_text())['required_assets']
    config_paths = []
    for entry in selected['files']:
        name = entry['path']
        safe_name(name)
        if not name.startswith('.vercel/output/') and name not in required:
            raise ValueError('Arbitrary source tree selected for capture')
        source = root / name
        if not source.is_file() or not source.resolve().is_relative_to(root):
            raise ValueError('Missing or external selected payload')
        link = str(source.resolve().relative_to(root)) if source.is_symlink() else None
        if link:
            safe_name(link)
        data = source.read_bytes()
        if len(data) != entry['size'] or hashlib.sha1(data).hexdigest() != entry['sha']:
            raise ValueError('Selected payload changed before sealing')
        if stat.S_IFMT(entry['mode']) != stat.S_IFREG:
            raise ValueError('Unsupported payload mode; no silent link normalization')
        if name.endswith('/.vc-config.json'):
            config_paths.append(name)
        add('payload/' + name, data, entry['mode'], link)
    if len(config_paths) != 4:
        raise ValueError('Missing/extra unchanged-F function runtime configuration')
    for source in sorted(reports.rglob('*')):
        if source.is_file():
            if source.is_symlink() or not source.resolve().is_relative_to(reports):
                raise ValueError('External report')
            add('reports/' + source.relative_to(reports).as_posix(), source.read_bytes(), stat.S_IFREG | 0o600)
    actual = {x['path'][8:]: x for x in rows if x['path'].startswith('payload/')}
    manifest = {'schema': 'reader-complete-capture.v1', 'context': context,
                'entries': sorted(rows, key=lambda x: x['path']), 'payload_files': len(actual),
                'canonical_entries_sha256': hashlib.sha256(canonical(sorted(rows, key=lambda x:x['path']))).hexdigest(),
                'self_binding': 'Manifest is separately hashed by external envelope; no circular self-hash.'}
    manifest_bytes = json.dumps(manifest, indent=2).encode()
    if sum(map(len, blobs.values())) + len(manifest_bytes) > cap:
        raise ValueError('Raw capture plus manifest exceeds cap')
    blobs['BUNDLE-MANIFEST.json'] = manifest_bytes
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        modes = {row['path']: row['mode'] for row in rows}
        for name, data in blobs.items():
            item = zipfile.ZipInfo(name)
            item.create_system = 3
            item.external_attr = modes.get(name, stat.S_IFREG | 0o600) << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, data)
    payload = buffer.getvalue()
    # Reserve a conservative 64KiB for the two-file, compression-level0 Actions wrapper.
    if len(payload) + 65536 > cap:
        raise ValueError('Compressed capture cannot fit actual upload cap')
    envelope = {'status': 'CAPTURE_COMPLETE_PENDING_INDEPENDENT_CONTENT_REVIEW',
                'context': context, 'archive_sha256': hashlib.sha256(payload).hexdigest(),
                'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
                'file_count': len(blobs), 'payload_files': len(actual),
                'raw_total_bytes': sum(map(len, blobs.values())), 'archive_bytes': len(payload),
                'maximum_raw_and_actual_artifact_bytes': cap, 'actions_wrapper_reserve_bytes': 65536,
                'rehydration': 'Restore regular bytes at captured relative paths/modes in fresh exactF checkout; original internal links materialized, traced source assets included. Re-select/re-verify before any separately approved reuse; no reuse permission here.'}
    envelope_bytes = json.dumps(envelope, indent=2).encode()
    if sum(map(len, blobs.values())) + len(envelope_bytes) > cap:
        raise ValueError('Raw capture including envelope exceeds cap')
    if len(payload)+len(envelope_bytes)+65536 > cap:
        raise ValueError('Actual upload wrapper bound exceeded')
    (output / 'release-candidate.zip').write_bytes(payload)
    (output / 'CAPTURE-ENVELOPE.json').write_bytes(envelope_bytes)
    return envelope


def inspect_archive(path, expected_sha):
    data = Path(path).read_bytes()
    if len(data) > CAP or hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError('Archive digest/size mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len({x.filename for x in entries}) != len(entries) or sum(x.file_size for x in entries) > CAP:
            raise ValueError('Duplicate/oversized archive')
        for item in entries:
            safe_name(item.filename)
            if stat.S_IFMT(item.external_attr >> 16) != stat.S_IFREG or item.flag_bits & 1:
                raise ValueError('Unsafe archived mode/encryption')
        manifest = json.loads(archive.read('BUNDLE-MANIFEST.json'))
        rows = manifest['entries']
        if len({row['path'] for row in rows}) != len(rows):
            raise ValueError('Duplicate manifest binding')
        if hashlib.sha256(canonical(rows)).hexdigest() != manifest['canonical_entries_sha256']:
            raise ValueError('Canonical inventory mismatch')
        if set(archive.namelist()) != {x['path'] for x in rows} | {'BUNDLE-MANIFEST.json'}:
            raise ValueError('Missing/unbound archive entry')
        for row in rows:
            body = archive.read(row['path'])
            if len(body) != row['size'] or hashlib.sha256(body).hexdigest() != row['sha256'] or archive.getinfo(row['path']).external_attr >> 16 != row['mode']:
                raise ValueError('Archived bytes differ')
        return manifest, {row['path']: archive.read(row['path']) for row in rows}


def preserve_failure(reports, output, reason):
    """Bounded reports-only failure packet; never labeled a complete payload."""
    reports, output = Path(reports), Path(output)
    output.mkdir(exist_ok=True)
    marker = {'status':'HOLD_CAPTURE_INCOMPLETE','error_class':reason,
              'payload_not_qualified':True,'no_automatic_retry':True}
    entries = {}
    total = 0
    for source in reports.rglob('*'):
        if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(reports.resolve()):
            continue
        name = 'reports/' + source.relative_to(reports).as_posix()
        safe_name(name)
        data = source.read_bytes()
        if name.endswith('.json'):
            public_json(json.loads(data))
        total += len(data)
        if total > CAP - 65536:
            marker['reports_not_uploaded_due_to_cap'] = True
            break
        entries[name] = data
    else:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in entries.items():
                archive.writestr(name,data)
        if len(buffer.getvalue()) + 65536 < CAP:
            data = buffer.getvalue()
            (output/'failure-evidence.zip').write_bytes(data)
            marker['reports_archive_sha256'] = hashlib.sha256(data).hexdigest()
            marker['retained_report_files'] = len(entries)
    (output/'CAPTURE-FAILURE.json').write_text(json.dumps(marker,indent=2)+'\n')
