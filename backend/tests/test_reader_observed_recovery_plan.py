"""Offline observed Reader proposals: no execution, live DB or customer session."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import pytest

os.environ.setdefault('MONGODB_URL', 'mongodb://127.0.0.1:27017/reader_plan_dummy')
os.environ.setdefault('JWT_SECRET', 'reader-plan-dummy-not-production')
from backend import server
from backend.domain.reading_pass import canonical_page_records, segment_manifest

EVIDENCE = Path(__file__).resolve().parents[2] / 'internal/earnalism_intelligence/reader_completeness_20261031'
PLAN = json.loads((EVIDENCE / 'PREPARED-26-DISPOSITION.json').read_text())


def test_observed_scope_and_nonexecuting_evidence_bindings():
    assert PLAN['production_operations'] == 0 and PLAN['execution_adapter'] is None
    rows = PLAN['rows']; assert len(rows) == len({r['slug'] for r in rows}) == 26
    for role, name in [('diagnosis', 'ATLAS-26-DIAGNOSIS.json'), ('parity', 'ATLAS-PAGE-HASH-PARITY.json'), ('revocation', 'ATLAS-REVOCATION-METADATA.json')]:
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == PLAN['input_sha256'][role]
    assert sum(not r['observed_physical_pointer_present'] for r in rows) == 24
    assert sum(r['page_scope'].startswith('COMPLETE_SOURCE') for r in rows) == 12
    by = {r['slug']: r for r in rows}
    for r in rows:
        assert r['state'] == 'OFFLINE_PROPOSAL_ONLY_NOT_LIVE_AUTHORITY'
        assert r['rollback'] == 'RETAIN_OLD_VERSIONS_ONLY_NOT_APPROVED_CUSTOMER_READY_RESTORE_TARGET'
        if not r['observed_physical_pointer_present']:
            assert r['observed_generation'] is None
            assert r['promotion_precondition']['expected_activation_generation'] == 0
            assert 'NOT_OBSERVED_ZERO' in r['promotion_precondition']['generation_basis']
    assert by['acres-of-diamonds']['promotion_precondition']['expected_result_generation'] == 2
    assert by['the-principles-of-scientific-management']['promotion_precondition'] is None


@pytest.mark.parametrize('proposal', PLAN['rows'], ids=[r['slug'] for r in PLAN['rows']])
def test_prepared_successor_matches_current_complete_source_and_india_rights(proposal):
    slug = proposal['slug']
    book = server._controlled_artifact_doc(slug, include_content=True)
    assert book and book['chapters']
    chapters = []
    for chapter in sorted(book['chapters'], key=lambda c: c.get('order', 0)):
        rendered, warnings = server._manual_content_to_render_html(chapter['content'])
        assert not warnings
        chapters.append({**chapter, 'content': rendered})
    records = canonical_page_records(book_slug=slug, chapters=chapters, target_characters=3200,
                                    segmentation_version=proposal['candidate_segmentation_version'])
    manifest = segment_manifest(records)
    assert manifest['version'] == proposal['candidate_manifest_version']
    assert len(records) == proposal['candidate_pages']
    if proposal['page_scope'].startswith('IDENTICAL'):
        metadata = [[r['page_index'], r['chapter_id'], r['content_sha256']] for r in records]
        assert hashlib.sha256(json.dumps(metadata, separators=(',', ':')).encode()).hexdigest() == proposal['ordered_page_metadata_sha256']
    decision, components = server._release_rights_artifact(slug)
    accepted, revoked = server.load_production_registry()
    assert server.record_sha256(decision) == proposal['rights_record_sha256']
    verdict = server.evaluate_runtime_path('reading_pass_page', record=decision, edition_id=slug,
        operator_id=server.RELEASE_RIGHTS_OPERATOR_ID, country='IN', country_trusted=True,
        required_components=components, accepted_records=accepted, revoked_decision_ids=revoked,
        now=datetime.now(timezone.utc))
    assert verdict.passed, verdict.reasons
