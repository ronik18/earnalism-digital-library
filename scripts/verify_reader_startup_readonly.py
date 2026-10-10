"""Bounded read-only release preflight; never imports server/startup routines."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from pymongo import MongoClient

def main():
    root = Path(__file__).resolve().parents[1]
    uri = os.environ.get('MONGODB_URL') or os.environ.get('MONGO_URL')
    if not uri:
        raise SystemExit('Secure production Mongo loader unavailable')
    flags = {key: os.environ.get(key) for key in (
        'REDIS_CACHE_ENABLED', 'MULTI_REPLICA_ENABLED', 'REDIS_CONFIGURE_ON_STARTUP',
        'ENABLE_STARTUP_DB_MAINTENANCE', 'READING_PASS_V2_ENABLED', 'ENVIRONMENT',
        'COST_CONTROL_MODE', 'ENABLE_BACKGROUND_WORKERS', 'ENABLE_BOOK_RENDERING_JOBS')}
    required = {
        'reader_content_segments': [([('book_slug', 1), ('page_index', 1), ('segmentation_version', 1)], None)],
        'reader_segment_manifests': [([('book_slug', 1), ('segmentation_version', 1)], None), ([('book_slug', 1)], {'status': 'active'})],
        'reader_segment_activation_state': [([('book_slug', 1)], None)],
        'reader_segment_activation_operations': [([('operation_id', 1)], None)],
    }
    client = MongoClient(uri, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000)
    db = client[os.environ.get('DB_NAME') or urlparse(uri).path.lstrip('/').split('/')[0] or 'earnalism']
    rows, missing = [], []
    try:
        for collection, constraints in required.items():
            indexes = db[collection].index_information()
            for keys, partial in constraints:
                if not any(index.get('unique') is True and list(index.get('key', [])) == keys
                           and index.get('partialFilterExpression') == partial for index in indexes.values()):
                    missing.append({'collection': collection, 'keys': keys, 'partial': partial})
        for entry in json.loads((root / 'backend/data/approved_reader_bootstrap.json').read_text())['titles']:
            slug = entry['slug']
            pointer = db.reader_segment_activation_state.find_one({'book_slug': slug}, {'_id': 0, 'active_segmentation_version': 1, 'generation': 1})
            active = db.reader_segment_manifests.find_one({'book_slug': slug, 'status': 'active'}, {'_id': 0, 'version': 1, 'segmentation_version': 1, 'total_pages': 1})
            retained = list(db.reader_segment_manifests.find({'book_slug': slug}, {'_id': 0, 'segmentation_version': 1, 'created_by': 1, 'status': 1}))
            version = 'approved-html-v1-' + entry['record_sha256'][:32]
            operator_history = any(r.get('segmentation_version') != version or r.get('created_by') != 'system:owner-authorized-reader-bootstrap-v1' or r.get('status') != 'prepared' for r in retained)
            state = 'PRESERVE_POINTER' if pointer else 'PRESERVE_ACTIVE' if active else 'PRESERVE_OPERATOR_HISTORY' if operator_history else 'POTENTIAL_PREPARATION_AND_BOOTSTRAP'
            row = {'slug': slug, 'startup_content_path': state, 'pointer': pointer, 'active': active}
            if slug == 'agentic-ai-with-python' and active:
                segments = list(db.reader_content_segments.find({'book_slug': slug, 'segmentation_version': active['segmentation_version']}, {'_id': 0, 'page_index': 1, 'content_sha256': 1}).sort('page_index', 1))
                row.update(segment_count=len(segments), segment_hashes_digest=hashlib.sha256(json.dumps(segments, sort_keys=True).encode()).hexdigest(), activation_operations=db.reader_segment_activation_operations.count_documents({'book_slug': slug}))
            rows.append(row)
    finally:
        client.close()
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'production_writes': 0,
              'flags': flags, 'missing_indexes': missing, 'rows': rows,
              'potential_content_writers': [r['slug'] for r in rows if r['startup_content_path'] == 'POTENTIAL_PREPARATION_AND_BOOTSTRAP']}
    stable = {k: v for k, v in report.items() if k != 'observed_at'}
    report['state_digest'] = hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()

    # Metadata reads only, never server import/startup or mutation.
    agentic = next((row for row in rows if row['slug'] == 'agentic-ai-with-python'), {})
    expected_flags = {'REDIS_CACHE_ENABLED': 'false', 'MULTI_REPLICA_ENABLED': 'false',
                      'ENABLE_STARTUP_DB_MAINTENANCE': 'false', 'READING_PASS_V2_ENABLED': 'true',
                      'ENVIRONMENT': 'production', 'ENABLE_BACKGROUND_WORKERS': 'false',
                      'ENABLE_BOOK_RENDERING_JOBS': 'false'}
    pointer = agentic.get('pointer') or {}
    active = agentic.get('active') or {}
    valid = (all(str(flags.get(key)).lower() == value for key, value in expected_flags.items())
             and report['state_digest'] == 'ed619a46c84fac9c945bb9a142519eb3e578a8b0b3dfe59ed429302c2bf44010'
             and not missing and not report['potential_content_writers']
             and pointer.get('generation') == 1
             and active.get('version') == '2d6e081a92bbeac0e5364cf2'
             and agentic.get('segment_count') == 211
             and agentic.get('segment_hashes_digest') == 'df15333c38446899cb090888354e2bbf3cfdfd40979489ece414c376be020b62')
    if not valid:
        raise SystemExit('STARTUP_PREFLIGHT=FAIL: flags/index/publication/content prerequisites changed or unavailable')
    print(json.dumps({'observed_at': report['observed_at'], 'state_digest': report['state_digest'],
                      'startup_preflight': 'PASS', 'missing_indexes': 0,
                      'potential_content_writers': 0, 'planned_titles': len(rows),
                      'publication_generation': 1, 'manifest': active['version'], 'segments': 211,
                      'scope': 'startup prerequisites and protected publication metadata; not global business activity'}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('STARTUP_PREFLIGHT=FAIL: approved read-only evidence unavailable') from None
