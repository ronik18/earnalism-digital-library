"""Bounded metadata projection of the actual controlled-publication resolver.

No manuscript, object URL, customer record, cache mutation or activation is
returned/performed. Hash domains remain separate; metadata is not audio admission.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

OPEN_WINDOW_UUID = '74251b53-9e18-49fb-9fff-bb7c505633d4'
OPEN_WINDOW_SLUG = 'the-open-window'
OPEN_WINDOW_SERVING_ID = 'controlled-the-open-window'
METADATA_FILES = ('public_book.json', 'reader_manifest.json', 'approval_evidence.json',
                  'source_evidence.json', 'checksum_manifest.json', 'publication_manifest.json')


class BindingUnavailable(ValueError):
    pass


def _read_metadata(root, name):
    path = root / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 512 * 1024:
        raise BindingUnavailable('Bounded publication metadata unavailable')
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise BindingUnavailable('Publication metadata is malformed')
    return value, hashlib.sha256(raw).hexdigest()


def _hashes(record):
    return {key: record[key] for key in ('source_hash', 'content_hash', 'provenance_hash',
            'manifest_sha256', 'publication_authorization_sha256', 'cover_provenance_sha256')
            if isinstance(record.get(key), str) and re.fullmatch(r'[a-fA-F0-9]{64}', record[key])}


def serving_binding_metadata(*, requested_uuid, uuid_rows, serving_doc, root):
    if requested_uuid != OPEN_WINDOW_UUID or len(uuid_rows) != 1:
        raise BindingUnavailable('Exact UUID association is unavailable or ambiguous')
    row = uuid_rows[0]
    if row.get('id') != requested_uuid or row.get('slug') != OPEN_WINDOW_SLUG:
        raise BindingUnavailable('UUID/title association mismatch')
    if not serving_doc or serving_doc.get('id') != OPEN_WINDOW_SERVING_ID or serving_doc.get('slug') != OPEN_WINDOW_SLUG:
        raise BindingUnavailable('Exact controlled serving identity unavailable')
    root = Path(root)
    if root.name != OPEN_WINDOW_SLUG or root.is_symlink():
        raise BindingUnavailable('Unexpected selected publication root')
    records, files = {}, {}
    for name in METADATA_FILES:
        records[name], files[name] = _read_metadata(root, name)
    public = records['public_book.json']
    if public.get('id') != serving_doc['id'] or public.get('slug') != serving_doc['slug']:
        raise BindingUnavailable('Selected packet and serving resolver disagree')
    # Compare the actual precedence-resolved values; do not equate hashes with
    # different meanings, or substitute a historical expected digest.
    for key in ('source_hash', 'content_hash', 'provenance_hash'):
        expected = next((records[name].get(key) for name in
            ('approval_evidence.json', 'source_evidence.json', 'public_book.json')
            if records[name].get(key)), None)
        if not isinstance(expected, str) or not re.fullmatch('[a-fA-F0-9]{64}', expected) or serving_doc.get(key) != expected:
            raise BindingUnavailable('Serving/source hash association unavailable')
    entries = records['checksum_manifest.json'].get('files')
    if not isinstance(entries, list):
        raise BindingUnavailable('Checksum metadata missing')
    declared = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('file'), str):
            raise BindingUnavailable('Malformed checksum metadata')
        name, digest = entry['file'], entry.get('sha256')
        if name in declared:
            raise BindingUnavailable('Ambiguous checksum entry')
        declared[name] = digest
    chapters = public.get('chapters')
    if not isinstance(chapters, list) or not chapters or not all(isinstance(chapter, dict) for chapter in chapters):
        raise BindingUnavailable('Ordered chapter metadata missing')
    ordered = sorted(chapters, key=lambda chapter: chapter.get('order', 0))
    result, ids, orders = [], set(), set()
    for chapter in ordered:
        chapter_id, order = chapter.get('id'), chapter.get('order')
        if not isinstance(chapter_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', chapter_id) or chapter_id in ids or type(order) is not int or order in orders:
            raise BindingUnavailable('Ambiguous chapter ordering')
        filename = f'chapters/{chapter_id}.json'
        digest = declared.get(filename)
        if not isinstance(digest, str) or not re.fullmatch('[a-fA-F0-9]{64}', digest):
            raise BindingUnavailable('Declared chapter file hash missing')
        ids.add(chapter_id); orders.add(order)
        result.append({'id': chapter_id, 'order': order, 'file': filename,
                       'declared_file_sha256': digest})
    for name in METADATA_FILES:
        _, after = _read_metadata(root, name)
        if after != files[name]:
            raise BindingUnavailable('Publication metadata changed during observation')
    return {
        'schema': 'earnalism.serving-publication-binding.v1',
        'requested_uuid': requested_uuid, 'uuid_association': 'exact-database-id-to-slug',
        'slug': OPEN_WINDOW_SLUG, 'serving_id': serving_doc['id'],
        'resolver': 'reader_book_access_doc/populate_cache=false; controlled packet required',
        'selected_root': str(root.resolve()), 'selection': 'first-complete-controlled-artifact-packet',
        'metadata_file_sha256': files,
        'hash_assertions_by_record': {name: _hashes(record) for name, record in records.items()},
        'serving_hashes': _hashes(serving_doc),
        'ordered_chapter_file_hashes': result,
        'chapter_hash_domain': 'declared JSON-file SHA256 in selected checksum manifest; no chapter body returned',
        'rights_metadata': {key: serving_doc.get(key) for key in
            ('rights_tier', 'verification_status', 'commercial_use_allowed', 'approved_to_publish', 'publication_status')},
        'limitation': 'Current serving metadata association; no audio admission, entitlement grant or claim of full-book acceptance',
    }
