"""Read-only audit of a captured public catalogue against canonical Reader text.

Usage: python3 -m scripts.audit_reading_estimates --snapshot FILE --output FILE
No credentials, network, content mutation or publication operation is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path

from backend.catalog_truth import load_controlled_artifact_book
from backend.reading_estimates import artifact_reading_estimate, text_word_count

ROOT = Path(__file__).resolve().parents[1]


def audit(snapshot):
    rows = []
    for live in snapshot:
        if live.get('publication_status') != 'LIVE_APPROVED':
            continue
        slug = live['slug']
        base = ROOT / 'data/controlled_publications' / slug
        raw = json.loads((base / 'public_book.json').read_text())
        chapters = raw['chapters']
        count = sum(text_word_count(json.loads((base / 'chapters' / f"{c['id']}.json").read_text()).get('content')) for c in chapters)
        estimate = artifact_reading_estimate(base, chapters)['estimated_reading_time']
        rows.append({'slug': slug, 'title': live['title'], 'chapters': len(chapters),
                     'words': count, 'old': live.get('estimated_reading_time'),
                     'corrected': estimate, 'changed': estimate != live.get('estimated_reading_time'),
                     'reader_artifact_valid': load_controlled_artifact_book(slug) is not None,
                     'chapter_metadata_matches_live': chapters == live.get('chapters')})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.snapshot.read_bytes()
    rows = audit(json.loads(raw))
    result = {'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
              'method': 'Reader HTML text; whitespace lexical tokens excluding punctuation-only tokens; 238 words/minute rounded, minimum one. Chapter headings inside content included; separate UI titles excluded.',
              'scope': 'Canonical local Reader bytes paired with public chapter metadata; not a fresh remote full-text extraction or an audiobook duration.',
              'books': rows}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'audited': len(rows), 'changed': sum(x['changed'] for x in rows),
                      'validated': sum(x['reader_artifact_valid'] for x in rows),
                      'chapter_metadata_matches': sum(x['chapter_metadata_matches_live'] for x in rows)}))


if __name__ == '__main__':
    main()
