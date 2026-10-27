import hashlib
import json
from backend.licensed_text import public_license_notice

def package(tmp_path):
    (tmp_path/'chapters').mkdir()
    (tmp_path/'chapters'/'c1.json').write_text(json.dumps({'content':'Actual text'}))
    notice={'schema_version':'earnalism.text-license.v1','slug':'test','license':'CC-BY-SA-4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','attribution':'Wikisource contributors','changes':'Formatting only','scope':'Transcription only','disclaimer':'No warranties','source_url':'https://bn.wikisource.org/w/index.php?oldid=123','contributors_url':'https://bn.wikisource.org/w/index.php?action=history','chapter_sha256':[hashlib.sha256(b'Actual text').hexdigest()]}
    raw=json.dumps(notice).encode();(tmp_path/'license_notice.json').write_bytes(raw)
    (tmp_path/'public_book.json').write_text(json.dumps({'slug':'test','chapters':[{'id':'c1','order':1}],'license_notice_sha256':hashlib.sha256(raw).hexdigest()}))
    return notice

def test_bound_notice(tmp_path):
    notice=package(tmp_path)
    result=public_license_notice(tmp_path)
    assert result['attribution']==notice['attribution']
    assert 'chapter_sha256' not in result

def test_missing_notice(tmp_path):
    assert public_license_notice(tmp_path) is None

def test_tampered_notice(tmp_path):
    package(tmp_path);(tmp_path/'license_notice.json').write_text('{}')
    assert public_license_notice(tmp_path) is None

def test_content_mismatch(tmp_path):
    package(tmp_path);(tmp_path/'chapters'/'c1.json').write_text(json.dumps({'content':'Other edition'}))
    assert public_license_notice(tmp_path) is None

def test_database_metadata_cannot_forge_public_license(monkeypatch, tmp_path):
    from backend import catalog_truth as truth
    monkeypatch.setattr(truth, 'normalize_book_publication_status', lambda _: truth.PUBLIC_STATUS_LIVE_APPROVED)
    monkeypatch.setattr(truth, 'can_expose_preview', lambda _: True)
    monkeypatch.setattr(truth, 'can_expose_audio', lambda _: False)
    monkeypatch.setattr(truth, 'controlled_artifact_dir', lambda _: tmp_path)
    projected = truth.public_book_projection({'slug': 'test', 'title': 'Title', 'text_license': {'license': 'CC-BY-SA-4.0'}})
    assert 'text_license' not in projected
    assert projected['audio_enabled'] is False


def test_public_notice_requires_canonical_bound_package(monkeypatch, tmp_path):
    from backend import catalog_truth as truth
    package(tmp_path)
    monkeypatch.setattr(truth, 'normalize_book_publication_status', lambda _: truth.PUBLIC_STATUS_LIVE_APPROVED)
    monkeypatch.setattr(truth, 'can_expose_preview', lambda _: True)
    monkeypatch.setattr(truth, 'can_expose_audio', lambda _: False)
    monkeypatch.setattr(truth, 'controlled_artifact_dir', lambda _: tmp_path)
    projected = truth.public_book_projection({'slug': 'test', 'title': 'Title'})
    assert projected['text_license']['license'] == 'CC-BY-SA-4.0'
    assert 'chapter_sha256' not in projected['text_license']
    assert projected['audio_enabled'] is False


def test_held_package_cannot_expose_public_license(monkeypatch, tmp_path):
    from backend import catalog_truth as truth
    package(tmp_path)
    monkeypatch.setattr(truth, 'normalize_book_publication_status', lambda _: 'QUARANTINED')
    monkeypatch.setattr(truth, 'controlled_artifact_dir', lambda _: tmp_path)
    projected = truth.public_book_projection({'slug': 'test', 'title': 'Title'})
    assert 'text_license' not in projected
    assert projected['reader_enabled'] is False


def test_cc0_notice_is_bound_and_does_not_claim_sharealike(tmp_path):
    notice = package(tmp_path)
    notice.update(license='CC0-1.0', license_url='https://creativecommons.org/publicdomain/zero/1.0/',
                  source_url='https://standardebooks.org/ebooks/test',
                  contributors_url='https://github.com/standardebooks/test')
    raw = json.dumps(notice).encode()
    (tmp_path/'license_notice.json').write_bytes(raw)
    book = json.loads((tmp_path/'public_book.json').read_text())
    book['license_notice_sha256'] = hashlib.sha256(raw).hexdigest()
    (tmp_path/'public_book.json').write_text(json.dumps(book))
    assert public_license_notice(tmp_path)['license'] == 'CC0-1.0'
    notice['contributors_url'] = 'https://github.com/other/test'
    raw = json.dumps(notice).encode()
    (tmp_path/'license_notice.json').write_bytes(raw)
    book['license_notice_sha256'] = hashlib.sha256(raw).hexdigest()
    (tmp_path/'public_book.json').write_text(json.dumps(book))
    assert public_license_notice(tmp_path) is None


def test_radharani_notice_successor_preserves_india_scope_and_exact_chapters():
    from backend.rights_decision_gate import load_production_registry, record_sha256, evaluate_accepted_record
    from datetime import datetime, timezone
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    base = root / 'backend/data/controlled_publications/radharani'
    record = json.loads((base / 'rights_decision.json').read_text())
    previous = json.loads((root / 'internal/legal/us_catalogue_attribution_20261028/radharani-prior-rights_decision.json').read_text())
    assert record['territories'] == previous['territories'] == ['IN']
    for key in ('uses', 'valid_from', 'valid_until'):
        assert record[key] == previous[key]
    assert public_license_notice(base)['license'] == 'CC-BY-SA-4.0'
    assert record['components']['license_notice'] == hashlib.sha256((base / 'license_notice.json').read_bytes()).hexdigest()
    for name in ('public_book.json','publication_manifest.json','checksum_manifest.json','rights_decision.json','license_notice.json'):
        assert (base / name).read_bytes() == (root / 'data/controlled_publications/radharani' / name).read_bytes()
    accepted, revoked = load_production_registry()
    assert accepted[previous['decision_id']] == record_sha256(previous)
    assert accepted[record['decision_id']] == record_sha256(record)
    args = dict(edition_id='radharani', operator_id='reo-enterprise',country_trusted=True,use='reader_delivery', required_components=record['components'],accepted_records=accepted,revoked_decision_ids=revoked,now=datetime.now(timezone.utc))
    assert evaluate_accepted_record(record,country='IN',**args).passed
    assert not evaluate_accepted_record(record,country='US',**args).passed
