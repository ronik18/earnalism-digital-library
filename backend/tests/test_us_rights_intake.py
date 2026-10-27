"""Accepted rights remain isolated from runtime activation."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from rights_decision_gate import evaluate_accepted_record, load_production_registry, record_sha256
ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'internal/legal/us_rights_intake_20261028'
INDEX = json.loads((PACKET / 'intake.json').read_text())

@pytest.mark.parametrize('entry', INDEX['records'], ids=lambda x: x['slug'])
def test_exact_accepted_scope_and_runtime_isolation(entry):
    slug = entry['slug']
    record = json.loads((PACKET / (slug + '.accepted.json')).read_text())
    original = json.loads((PACKET / (slug + '.proposed.json')).read_text())
    assert original['status'] == 'PROPOSED' and not original['accepted_by']
    assert record['components'] == original['components']
    assert record['territories'] == ['US']
    assert record['valid_from'] == original['valid_from']
    assert record_sha256(record) == entry['accepted_record_sha256']
    receipt = (PACKET / 'owner-acceptance.json').read_bytes()
    assert hashlib.sha256(receipt).hexdigest() == INDEX['owner_receipt_sha256']
    assert INDEX['owner_receipt_sha256'] in record['evidence_sha256']
    assert hashlib.sha256((ROOT / 'backend/data/controlled_publications' / slug / 'rights_decision.json').read_bytes()).hexdigest() == entry['existing_IN_record_sha256']
    accepted, revoked = load_production_registry()
    assert record['decision_id'] not in accepted
    args = dict(edition_id=slug, operator_id='reo-enterprise', country='US', country_trusted=True,
                required_components=record['components'], accepted_records={record['decision_id']:record_sha256(record)},
                revoked_decision_ids=revoked, now=datetime.fromisoformat(INDEX['accepted_at_utc']))
    for use in record['uses']:
        assert evaluate_accepted_record(record, use=use, **args).passed
    for use in ('audio_stream', 'audio_download', 'content_export', 'ai_generation'):
        assert not evaluate_accepted_record(record, use=use, **args).passed
    assert not evaluate_accepted_record(record, use='reader_delivery', **{**args, 'accepted_records':accepted}).passed
    assert not evaluate_accepted_record(record, use='reader_delivery', **{**args, 'country':'IN'}).passed
    changed = {**record['components'], 'public_book':'f'*64}
    assert not evaluate_accepted_record(record, use='reader_delivery', **{**args, 'required_components':changed}).passed
    assert not evaluate_accepted_record(record, use='reader_delivery', **{**args, 'country_trusted':False}).passed


def test_reviewed_components_still_match_source():
    checks = json.loads((PACKET / 'component-bindings.json').read_text())
    for entry in checks['component_checks']:
        assert hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']
