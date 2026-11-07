"""Neutral private card-choice evidence; never fabricates viewers or grants release approval."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import tempfile

NAME = 'viewer-study.json'
SCHEMA = 'earnalism.viewer-study.v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Actual nonblank text required: ' + label)
    return value


def _image(folder, asset):
    if not isinstance(asset, dict) or set(asset) != {'path', 'sha256'}:
        raise ValueError('Card asset path and SHA256 required')
    root = Path(folder).resolve()
    raw = Path(_text(asset['path'], 'asset path'))
    path = (root / raw).resolve()
    if raw.is_absolute() or '..' in raw.parts or not path.is_relative_to(root):
        raise ValueError('Card asset must remain inside this candidate')
    if not path.is_file() or path.stat().st_size == 0 or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise ValueError('Actual local card image required')
    header = path.read_bytes()[:16]
    image_header = header.startswith(b'\x89PNG\r\n\x1a\n') or header.startswith(b'\xff\xd8\xff') or (header.startswith(b'RIFF') and header[8:12] == b'WEBP')
    if not image_header or sha(path) != asset['sha256']:
        raise ValueError('Missing, changed or invalid card image')


def _cards(folder, cards):
    if not isinstance(cards, list) or len(cards) < 3:
        raise ValueError('At least two owned candidate variants and one owned/authorized distractor required')
    clean = json.loads(json.dumps(cards, allow_nan=False))
    ids = set()
    counts = {'candidate': 0, 'distractor': 0}
    pairs = set()
    for card in clean:
        if not isinstance(card, dict) or set(card) != {'id', 'role', 'title', 'asset', 'rights_note'}:
            raise ValueError('Complete explicit card definition required')
        if not isinstance(card['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]+', card['id']) or card['id'] == 'none' or card['id'] in ids:
            raise ValueError('Distinct safe card IDs required; none is reserved')
        ids.add(card['id'])
        if card['role'] not in counts:
            raise ValueError('Card role must be candidate or distractor')
        counts[card['role']] += 1
        _text(card['title'], 'title')
        _text(card['rights_note'], 'creator ownership/authorization note')
        _image(folder, card['asset'])
        if card['role'] == 'candidate':
            pairs.add((card['title'], card['asset']['sha256']))
    if counts['candidate'] < 2 or counts['distractor'] < 1 or len(pairs) < 2:
        raise ValueError('Two distinct candidate variants and an explicit distractor required')
    return sorted(clean, key=lambda value: value['id'])


def _manifest(folder, required=True):
    root = Path(folder).resolve()
    path = root / 'delivery-manifest.json'
    if not path.exists():
        if required:
            raise ValueError('Final delivery manifest required for actual study qualification')
        return None
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError('Nonempty delivery manifest required')
    if NAME in manifest or 'delivery-manifest.json' in manifest:
        raise ValueError('Study sidecar and manifest must remain outside their own delivery hash cycle')
    for name, digest in manifest.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ValueError('Invalid delivery manifest entry')
        raw = Path(name)
        asset = (root / raw).resolve()
        if raw.is_absolute() or '..' in raw.parts or not asset.is_relative_to(root) or not asset.is_file() or sha(asset) != digest:
            raise ValueError('Delivery changed; retain historical study and rebind a new pending study')
    return sha(path)


def pending(folder, cards):
    normalized = _cards(folder, cards)
    return {'schema': SCHEMA, 'status': 'PENDING',
            'delivery_manifest_sha256': _manifest(folder, required=False),
            'cards': normalized, 'cards_sha256': canonical(normalized),
            'reviewer': '', 'human_confirmed': False, 'reviewed_at': None,
            'protocol': {'no_coaching_before_selection': False,
                         'no_answers_before_selection': False,
                         'order_method': '', 'order_limitation': ''},
            'participants': [],
            'note': 'Pending actual anonymous human responses. No simulated/global/top-three personas, audience predictions, growth claims or release approval.'}


def _reviewer(record):
    if record.get('status') != 'PASS' or record.get('human_confirmed') is not True:
        raise ValueError('Study remains pending; actual human review required')
    _text(record.get('reviewer'), 'reviewer')
    try:
        timestamp = dt.datetime.fromisoformat(record['reviewed_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None or timestamp > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
            raise ValueError()
    except (KeyError, TypeError, AttributeError, ValueError):
        raise ValueError('Timezone-aware actual human review timestamp required')


def validate(folder, record):
    if not isinstance(record, dict) or record.get('schema') != SCHEMA:
        raise ValueError('Invalid viewer-study schema')
    manifest_hash = _manifest(folder)
    if record.get('delivery_manifest_sha256') != manifest_hash:
        raise ValueError('Stale viewer-study manifest binding')
    cards = _cards(folder, record.get('cards'))
    if record.get('cards_sha256') != canonical(cards):
        raise ValueError('Study cards changed; create a new pending study')
    _reviewer(record)
    protocol = record.get('protocol', {})
    if not isinstance(protocol, dict) or protocol.get('no_coaching_before_selection') is not True or protocol.get('no_answers_before_selection') is not True:
        raise ValueError('Neutral choice before coaching or answers must be confirmed')
    if protocol.get('order_method') not in ('counterbalanced', 'limited'):
        raise ValueError('Counterbalanced orders or explicit order limitation required')
    if protocol['order_method'] == 'limited':
        _text(protocol.get('order_limitation'), 'order limitation')
    participants = record.get('participants')
    if not isinstance(participants, list) or not participants:
        raise ValueError('Actual participant records required; no simulated feedback')
    ids, orders = set(), set()
    card_ids = {card['id'] for card in cards}
    counts = {card['id']: 0 for card in cards}
    counts['none'] = 0
    first_time_count = 0
    completed = {'yes': 0, 'no': 0, 'unknown': 0}
    satisfaction = {str(value): 0 for value in range(1, 6)}
    satisfaction['unknown'] = 0
    next_lesson = {'yes': 0, 'no': 0, 'unsure': 0, 'unknown': 0}
    required = {'id', 'first_time', 'response_kind', 'shown_order', 'actual_selected_card', 'verbatim_reason', 'expected_payoff'}
    for person in participants:
        if not isinstance(person, dict) or not required.issubset(person) or set(person) - required - {'postwatch'}:
            raise ValueError('Use the anonymous actual-response schema; no identity or persona fields')
        if not isinstance(person['id'], str) or not re.fullmatch(r'P[0-9]{2,6}', person['id']) or person['id'] in ids:
            raise ValueError('Unique anonymous participant IDs such as P01 required')
        ids.add(person['id'])
        if not isinstance(person['first_time'], bool) or person['response_kind'] != 'actual_human':
            raise ValueError('Actual human response and prior-viewing status required')
        first_time_count += person['first_time']
        order = person['shown_order']
        if not isinstance(order, list) or len(order) != len(card_ids) or any(not isinstance(value, str) for value in order) or set(order) != card_ids:
            raise ValueError('Actual complete displayed card order required for each participant')
        orders.add(tuple(order))
        choice = person['actual_selected_card']
        if not isinstance(choice, str) or choice not in card_ids | {'none'}:
            raise ValueError('Actual choice must name a shown card or explicit none')
        counts[choice] += 1
        _text(person['verbatim_reason'], 'verbatim reason')
        _text(person['expected_payoff'], 'expected payoff')
        post = person.get('postwatch')
        if post is None:
            post = {}
        if not isinstance(post, dict) or set(post) - {'watched_card_id', 'completed', 'satisfaction', 'next_lesson_intent', 'verbatim_comment'}:
            raise ValueError('Only actual optional postwatch responses may be recorded')
        candidates = {card['id'] for card in cards if card['role'] == 'candidate'}
        if post.get('watched_card_id') is not None and post['watched_card_id'] not in candidates:
            raise ValueError('Postwatch candidate card is unknown')
        if any(post.get(key) is not None for key in ('completed', 'satisfaction', 'next_lesson_intent', 'verbatim_comment')) and post.get('watched_card_id') not in candidates:
            raise ValueError('Actual postwatch responses need the watched candidate card')
        completion = post.get('completed')
        if completion is not None and not isinstance(completion, bool):
            raise ValueError('Completion must be an actual boolean or unknown null')
        completed['unknown' if completion is None else 'yes' if completion else 'no'] += 1
        rating = post.get('satisfaction')
        if rating is not None and (isinstance(rating, bool) or not isinstance(rating, int) or rating not in range(1, 6)):
            raise ValueError('Actual satisfaction rating must be 1–5 or unknown null')
        satisfaction['unknown' if rating is None else str(rating)] += 1
        intent = post.get('next_lesson_intent')
        if intent not in (None, 'yes', 'no', 'unsure'):
            raise ValueError('Actual next-lesson intent must be yes/no/unsure or unknown null')
        next_lesson['unknown' if intent is None else intent] += 1
        if post.get('verbatim_comment') is not None:
            _text(post['verbatim_comment'], 'verbatim postwatch comment')
    if not first_time_count:
        raise ValueError('At least one genuine first-time participant required')
    if protocol['order_method'] == 'counterbalanced' and len(orders) < 2:
        raise ValueError('Counterbalance needs actual different orders; otherwise record the limitation')
    if protocol['order_method'] == 'counterbalanced':
        for card_id in card_ids:
            positions = [sum(person['shown_order'][index] == card_id for person in participants) for index in range(len(card_ids))]
            if max(positions) - min(positions) > 1:
                raise ValueError('Observed card positions are unbalanced; record the order limitation')
    return {'status': 'DESCRIPTIVE_STUDY_RECORDED', 'participants': len(participants),
            'first_time_participants': first_time_count, 'choice_counts': counts,
            'postwatch_completion_counts': completed, 'postwatch_satisfaction_counts': satisfaction,
            'next_lesson_intent_counts': next_lesson,
            'order_method': protocol['order_method'], 'order_limitation': protocol.get('order_limitation', ''),
            'publication_approval': False, 'causal_proof': False, 'growth_or_revenue_prediction': False,
            'note': 'Descriptive responses from this sample only; no global audience representation or production approval.'}


def reset(folder, cards):
    folder = Path(folder)
    record = pending(folder, cards)
    sidecar = folder / NAME
    if sidecar.exists():
        history = folder / 'logs/viewer-study-history'
        history.mkdir(parents=True, exist_ok=True)
        archive = history / (sha(sidecar) + '.json')
        if not archive.exists():
            with archive.open('xb') as stream:
                stream.write(sidecar.read_bytes())
    with tempfile.NamedTemporaryFile(mode='w', dir=folder, prefix='.viewer-study-', suffix='.tmp', delete=False) as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False, allow_nan=False)
        temporary = Path(stream.name)
    try:
        os.replace(temporary, sidecar)
    finally:
        temporary.unlink(missing_ok=True)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'check'))
    parser.add_argument('folder')
    parser.add_argument('cards', nargs='?')
    args = parser.parse_args()
    folder = Path(args.folder)
    if args.command == 'init':
        if not args.cards:
            parser.error('init requires CARDS.json with owned/authorized assets')
        result = pending(folder, json.loads(Path(args.cards).read_text()))
        with (folder / NAME).open('x') as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
    else:
        if args.cards:
            parser.error('check reads the existing sidecar; no cards argument')
        result = validate(folder, json.loads((folder / NAME).read_text()))
    print(json.dumps(result, indent=2, ensure_ascii=False))
