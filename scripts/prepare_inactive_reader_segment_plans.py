#!/usr/bin/env python3
"""Prepare hash-only local page plans; this tool has no DB or release writes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.domain.reading_pass import canonical_page_records, segment_manifest
from backend.rights_decision_gate import evaluate_accepted_record, record_sha256

REQUIRED_COMPONENTS = frozenset({
    'public_book', 'reader_manifest', 'source_evidence', 'approval_evidence',
    'checksum_manifest', 'publication_manifest',
})


def prepare(root=ROOT):
    live = set(json.loads((root / 'data/controlled_launch.json').read_text())['live_approved_slugs'])
    plans = []
    for path in sorted((root / 'data/controlled_publications').glob('*/rights_decision.json')):
        record = json.loads(path.read_text())
        package = path.parent
        slug = package.name
        if slug in live or record.get('status') != 'ACCEPTED':
            continue
        manifest = json.loads((package / 'publication_manifest.json').read_text())
        if manifest['reader_release']['exposed'] or manifest['audio_release']['exposed']:
            raise ValueError(f'{slug}: inactive preparation must remain unexposed')
        components = {name: hashlib.sha256((package / (name + '.json')).read_bytes()).hexdigest()
                      for name in REQUIRED_COMPONENTS | set(record['components'])}
        result = evaluate_accepted_record(record, edition_id=slug, operator_id='reo-enterprise',
            country='IN', country_trusted=True, use='reader_preview', required_components=components,
            accepted_records={record['decision_id']: record_sha256(record)}, revoked_decision_ids=frozenset(),
            now=datetime.now(timezone.utc))
        if not result.passed:
            raise ValueError(f'{slug}: local record mismatch: {result.reasons}')
        book = json.loads((package / 'public_book.json').read_text())
        chapters = [json.loads((package / 'chapters' / (meta['id'] + '.json')).read_text())
                    for meta in sorted(book['chapters'], key=lambda chapter: chapter['order'])]
        for chapter in chapters:
            if hashlib.sha256(chapter['content'].encode()).hexdigest() != chapter['content_hash']:
                raise ValueError(f'{slug}: chapter identity mismatch')
        pages = canonical_page_records(book_slug=slug, chapters=chapters, target_characters=3200)
        plans.append({'slug': slug, 'state': 'INACTIVE_LOCAL_PLAN_NOT_PROMOTED', 'target_characters': 3200,
            'manifest': segment_manifest(pages),
            'pages': [{key: page[key] for key in ('page_index', 'chapter_id', 'content_sha256', 'is_public_preview')}
                      for page in pages]})
    return plans


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Write an internal local evidence packet, never a runtime registry.')
    args = parser.parse_args()
    output = json.dumps(prepare(), ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(output)
    else:
        print(output, end='')
