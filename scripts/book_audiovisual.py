#!/usr/bin/env python3
"""Coordinate the existing Earnalism book skills; no provider or publication calls.

Planning is a private action packet, not qualification. Release checks delegate
to produce_release.evaluate, the existing sole release governor.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.produce_release import evaluate
from scripts.release_acceptance import measure_audiovisual

SKILLS = ('earnalism-book-production', 'earnalism-audiobook-go-live',
          'earnalism-audiobook-score', 'earnalism-video')
INVALIDATES = {
    'narration': ['fidelity', 'measured_timing', 'score', 'captions', 'visual_anchors', 'full_review', 'decision'],
    'score': ['mix_technical', 'soundtrack_listening', 'audiovisual_sync', 'decision'],
    'visual': ['composition', 'branding', 'readability', 'pixels', 'audiovisual_sync', 'decision'],
    'captions': ['caption_text', 'measured_timing', 'readability', 'audiovisual_sync', 'caption_delivery', 'decision'],
    'rights': ['rights', 'decision'],
    'technical': ['delivered_file_technical', 'decision'],
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def title_key(value: str) -> str:
    # Bengali vowel signs are combining marks; \w would silently erase them.
    value = unicodedata.normalize('NFKC', value).casefold()
    return ' '.join(''.join(c if unicodedata.category(c)[0] in 'LNM' else ' '
                            for c in value).split())


def records(value, locator='history', inherited_date=''):
    if isinstance(value, dict):
        date = str(value.get('at') or value.get('date') or inherited_date)
        yield locator, value, date
        for key, child in value.items():
            yield from records(child, f'{locator}.{key}', date)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from records(child, f'{locator}[{index}]', inherited_date)


def retained_score_metadata(record: dict, candidate_path: Path, candidate_sha256: str) -> dict:
    """Read the supported retained score packet, verifying actual source refs.

    The packet supplies discovery metadata only, never rights or acceptance.
    A filename or a Latin title is not language qualification.
    """
    value = record.get('result_record')
    if not isinstance(value, str):
        return {}
    result_path = Path(value)
    input_path = result_path.parent / 'candidate.json'
    try:
        result = json.loads(result_path.read_text(encoding='utf-8'))
        source = json.loads(input_path.read_text(encoding='utf-8'))
        if (result.get('schema') != 'earnalism.private_parallel_audiobook_score_result.v1'
                or source.get('schema') != 'earnalism.audiobook_score.input.v1'
                or result.get('candidate_sha256') != candidate_sha256
                or Path(str(result.get('candidate_path'))).resolve() != candidate_path.resolve()
                or source.get('fixture_mode', False) is not False):
            return {}
        refs = {}
        for name in ('manuscript', 'narration', 'timing'):
            ref = source.get(name) or {}
            path = input_path.parent / str(ref.get('path') or '')
            if (not path.is_file() or digest(path) != ref.get('sha256')
                    or result.get(f'{name}_sha256') != ref.get('sha256')
                    or record.get(f'{name}_sha256', ref.get('sha256')) != ref.get('sha256')):
                return {}
            refs[name] = {'path': str(path.resolve()), 'sha256': ref['sha256']}
        language = source['manuscript'].get('language')
        if language not in {'en', 'bn'}:
            return {}
        refs['scored_audio'] = {'path': str(candidate_path.resolve()), 'sha256': candidate_sha256}
        master_path = Path(str(result.get('master_path') or ''))
        if master_path.is_file() and digest(master_path) == result.get('master_sha256'):
            refs['lossless_scored_audio'] = {'path': str(master_path), 'sha256': result['master_sha256']}
        return {'language': language, 'verified_score_input': {'path': str(input_path), 'sha256': digest(input_path)},
                'verified_source_refs': refs, 'timing_scope': result.get('timing_scope'),
                'acceptance': 'NOT_INFERRED'}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def plan(title: str, history_path: Path, language: str | None = None) -> dict:
    """Resolve exact normalized identities, never fuzzy-match another edition."""
    if not title_key(title):
        raise ValueError('a nonempty book title is required')
    history = json.loads(history_path.read_text(encoding='utf-8'))
    matched, candidates, seen, owner_revisions = [], [], set(), []
    inferred_language = None
    known_title_languages = set()
    for locator, record, date in records(history):
        identities = [record.get(k) for k in ('title', 'name', 'slug', 'book_slug', 'title_slug')]
        # Explicit bilingual labels are aliases; arbitrary substrings are not.
        identities += [alias.strip() for value in identities if isinstance(value, str)
                       for alias in value.split('/') if '/' in value]
        if not any(isinstance(v, str) and title_key(v) == title_key(title) for v in identities):
            continue
        record_language = None
        if record.get('language') in {'en', 'bn'}:
            record_language = record['language']
        elif any(isinstance(v, str) and re.search('[\u0980-\u09ff]', v) for v in identities):
            record_language = 'bn'
        inferred_language = record_language or inferred_language
        if record_language:
            known_title_languages.add(record_language)
        matched.append({'record': locator, 'date': date,
                        'state': record.get('state') or record.get('status'),
                        'actual_full_listening': record.get('actual_full_listening'),
                        'next_action': record.get('next_action') or record.get('next_generated_prompt')})
        revision = record.get('owner_revision')
        if revision is not None:
            if (not isinstance(revision, dict)
                    or revision.get('schema') != 'earnalism.book_av_owner_revision.v1'
                    or revision.get('source') != 'human'
                    or revision.get('status') not in {'ACTIVE', 'RESOLVED'}
                    or revision.get('language') not in (None, 'en', 'bn')
                    or not isinstance(revision.get('source_ref'), str)
                    or not revision['source_ref'].strip()
                    or not isinstance(revision.get('required_changes'), list)
                    or not revision['required_changes']
                    or any(area not in INVALIDATES for area in revision['required_changes'])):
                raise ValueError('Owner revision requires explicit human source, status and affected areas')
            if revision.get('language') and record_language and revision['language'] != record_language:
                raise ValueError('Owner revision language conflicts with its title record')
            owner_revisions.append({**revision, 'record': locator, 'date': date,
                                    'language': revision.get('language') or record_language})
        for key in ('candidate_path', 'resulting_candidate_path', 'audio_path', 'scored_audio_path'):
            value = record.get(key)
            expected = (record.get('resulting_candidate_sha256') or record.get('candidate_sha256')
                        or record.get('audio_sha256') or record.get('input_candidate_sha256'))
            if not isinstance(value, str) or not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
                continue
            path = Path(value)
            if not path.is_absolute():
                path = history_path.parent / path
            identity = (str(path), expected)
            metadata = retained_score_metadata(record, path, expected)
            if identity in seen:
                if metadata:
                    for candidate in candidates:
                        if (candidate['path'], candidate['sha256']) == identity:
                            candidate.update(metadata)
                            candidate['language_matches_request'] = metadata['language'] == language if language else None
                continue
            seen.add(identity)
            verified = path.is_file() and digest(path) == expected
            candidates.append({'path': str(path), 'sha256': expected,
                               'retained_bytes_verified': verified, 'date': date,
                               'language': record_language or 'UNRESOLVED',
                               'language_matches_request': record_language == language if language else None,
                               'record': locator, 'acceptance': 'NOT_INFERRED', **metadata})
    matched.sort(key=lambda x: x['date'], reverse=True)
    candidates.sort(key=lambda x: x['date'], reverse=True)
    # Scope findings and resolutions to the requested edition's language. A
    # generic revision may inherit only an unambiguous matching-title context;
    # never borrow the requested language to reinterpret an English finding.
    context_language = next(iter(known_title_languages)) if len(known_title_languages) == 1 else None
    owner_revisions = [{**revision, 'language': revision['language'] or context_language}
                       for revision in owner_revisions]
    owner_revisions = [revision for revision in owner_revisions if revision['language'] is not None
                       and (language is None or revision['language'] == language)]
    # Later owner findings supersede historical acceptance for the current
    # candidate. Keep originals and proofs; do not suggest rejected narration
    # merely because its bytes still match. This is discovery, not a release gate.
    owner_revisions.sort(key=lambda x: x['date'])
    latest_revision = owner_revisions[-1] if owner_revisions else None
    active_revision = latest_revision if latest_revision and latest_revision['status'] == 'ACTIVE' else None
    changes = set(active_revision['required_changes']) if active_revision else set()
    if 'narration' in changes:
        for candidate in candidates:
            candidate['reuse_disposition'] = 'HISTORICAL_ONLY_OWNER_NARRATION_REVISION'
    retained = next((c for c in candidates if c['retained_bytes_verified']
                     and 'narration' not in changes
                     and (language is None or c['language'] == language)), None)
    next_prompt = (f'Resume {title} from its current exact edition and title checkpoint. '
                   'Preserve verified retained narration and scoring. Resolve full source, '
                   'audiovisual adaptation/model/voice/music/visual rights and measured timing; '
                   'prepare a contextual book_av_render job and private cinematic candidate. '
                   'Retain all title holds, consumed budgets and owner feedback. '
                   'Use produce_release.evaluate for final readiness; do not infer listening or GO LIVE.')
    if active_revision:
        next_prompt = (f'Resume {title} with the active owner revision in {latest_revision["record"]}. '
                       'Preserve previous assets and acceptance as history. Apply only the named changes; '
                       'reuse unchanged evidence within its actual scope. ')
        if 'narration' in changes:
            next_prompt += ('Qualify replacement narration against the requested voice/accent and actual remaining authority, '
                            'then measure its new clock before captions, music/scene timing and AV review. ')
        if 'visual' in changes:
            next_prompt += 'Replace rejected visual treatment with source-bound cinematic actions. '
        next_prompt += 'This packet grants no synthesis, spending, GPU allocation or publication authority.'
    return {'schema': 'earnalism.book_av_action_packet.v1', 'title': title,
            'language': language or inferred_language or 'UNRESOLVED_REQUIRES_EDITION',
            'history': {'path': str(history_path), 'sha256': digest(history_path)},
            'matched_records': matched, 'retained_candidates': candidates,
            'current_owner_revision': latest_revision,
            'preferred_retained_candidate': retained,
            'state': 'OWNER_REVISION_REQUIRED' if active_revision else 'PRIVATE_PREPARATION_REQUIRED',
            'actions': [
                {'skill': SKILLS[0], 'action': 'Resolve exact edition, complete source, covers and audiovisual rights through existing admin workflow.'},
                {'skill': SKILLS[1], 'action': ('Prepare replacement narration matching active owner voice/accent constraints; archive rejected recordings and qualify the actual audition under remaining authority.' if 'narration' in changes else 'Reuse eligible exact narration; otherwise qualify language/theme voices under existing authority. Bengali never falls back to English.')},
                {'skill': SKILLS[2], 'action': ('Retain cleared music stems and owner music preferences; rebuild the scored mix on newly measured replacement narration. Previous scored audio and timing remain historical.' if 'narration' in changes else 'Reuse qualified scored edition or prepare-director, plan and render from measured cues and cleared stems; preserve positively reviewed passages.')},
                {'skill': SKILLS[3], 'action': ('Replace owner-rejected visual treatment with source-bound cinematic character actions; keep old trials as history and qualify actual motion before scaling.' if 'visual' in changes else 'Prepare contextual storyboard and explicit independent delivery compositions, render privately, then collect actual final AV review and one destination-bound decision.')},
            ], 'network_calls': 0, 'provider_calls': 0, 'model_weights_trained': False,
            'publication_performed': False, 'acceptance_created': False,
            'next_generated_prompt': next_prompt}


def feedback(data: dict) -> dict:
    required = {'candidate_sha256', 'source', 'source_ref', 'scope', 'area', 'finding', 'fix', 'preserve'}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError('feedback requires exact candidate, source/source_ref, scope, area, finding, fix and preserve')
    if (not isinstance(data['candidate_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', data['candidate_sha256'])
            or data['source'] not in {'human', 'automatic'} or data['area'] not in INVALIDATES):
        raise ValueError('invalid feedback candidate/source/area')
    if any(not isinstance(data[k], str) or not data[k].strip() for k in required - {'candidate_sha256', 'source', 'area'}):
        raise ValueError('actual scoped feedback and preserve/fix decisions required')
    return {'schema': 'earnalism.book_av_feedback.v1',
            'recorded_at': datetime.now(timezone.utc).isoformat(), **data,
            'affected_evidence': INVALIDATES[data['area']],
            'acceptance_created': False, 'model_weights_trained': False,
            'next_generated_prompt': 'Apply the smallest evidenced correction to the exact candidate; preserve the recorded passages, reuse unchanged evidence, and re-evaluate affected checks through the existing governor.'}


def write_private_new(path: Path, data: dict):
    path = path.resolve()
    if path.is_relative_to(ROOT):
        raise ValueError('private packets and feedback must remain outside the repository')
    if not path.parent.is_dir():
        raise ValueError('create the private output parent directory first')
    with path.open('x', encoding='utf-8') as target:
        json.dump(data, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('plan')
    p.add_argument('--title', required=True)
    p.add_argument('--language', choices=['en', 'bn'])
    p.add_argument('--history', type=Path, default=ROOT / 'internal/earnalism_intelligence/title_decision_history.json')
    p.add_argument('--output', type=Path)
    for name in ('status', 'check'):
        p = commands.add_parser(name)
        p.add_argument('--manifest', type=Path, required=True)
        p.add_argument('--root', type=Path)
        p.add_argument('--reader-approval', type=Path)
        p.add_argument('--audio-samples-approval', type=Path)
    p = commands.add_parser('render')
    p.add_argument('--job', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p = commands.add_parser('feedback')
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('measure')
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--render-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'plan':
            result = plan(args.title, args.history.resolve(), args.language)
            if args.output:
                write_private_new(args.output, result)
        elif args.command in {'status', 'check'}:
            manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
            if not isinstance(manifest, dict) or 'audiovisual' not in manifest:
                raise ValueError('book audiovisual checks require an explicitly selected audiovisual manifest')
            result = evaluate(manifest, (args.root or args.manifest.parent).resolve(),
                              args.reader_approval, args.audio_samples_approval)
        elif args.command == 'feedback':
            result = feedback(json.loads(args.input.read_text(encoding='utf-8')))
            write_private_new(args.output, result)
        elif args.command == 'measure':
            manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
            report_path = args.render_report.resolve()
            result = measure_audiovisual(manifest, args.manifest.parent.resolve(),
                                         {'path': str(report_path), 'sha256': digest(report_path)})
            write_private_new(args.output, result)
        else:
            from scripts.book_av_render import render
            result = render(args.job.resolve(), args.output_dir.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2 if result.get('release_status') == 'BLOCKED' else 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError, wave.Error) as exc:
        print(json.dumps({'status': 'BLOCKED', 'detail': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
