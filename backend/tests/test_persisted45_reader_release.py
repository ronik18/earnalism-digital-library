"""Exact Reader-only cohort and owner-removal checks; no production writes."""
import json
from pathlib import Path

from backend import catalog_truth
from backend.rights_decision_gate import record_sha256
from scripts.catalogue_clearance_release_bindings import (
    TEXT_USES, assert_current_reviewed_release, assert_reviewed_authority,
)

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'internal/legal/catalogue_clearance_20261002/persisted45_reader_20261108'
REMOVED = {'gitanjali', 'nishkriti', 'the-metamorphosis'}


def load(path):
    return json.loads(path.read_text())


def test_exact_45_additive_reader_release_preserves_all_prior_audio_permissions():
    receipt = load(ARCHIVE / 'successor.json')
    baseline = assert_reviewed_authority(ROOT)
    previous = load(ROOT / receipt['preserved_predecessor_files'][
        'internal/legal/catalogue_clearance_20261002/reviewed_release_authority_20261003.v1.json']['path'])
    slugs = set(receipt['slugs'])
    assert len(slugs) == 45 and not slugs & REMOVED
    assert set(baseline['titles']) == set(previous['titles']) | slugs
    assert all(baseline['titles'][s] == b for s, b in previous['titles'].items())
    registry = load(ROOT / 'backend/data/rights_decision_registry.json')
    prior_registry = load(ROOT / receipt['preserved_predecessor_files'][
        'backend/data/rights_decision_registry.json']['path'])
    expected = dict(prior_registry)
    expected['accepted_records'] = {**prior_registry['accepted_records'], **receipt['added_accepted_records']}
    assert registry == expected
    bootstrap = load(ROOT / 'backend/data/approved_reader_bootstrap.json')
    prior_bootstrap = load(ROOT / receipt['preserved_predecessor_files'][
        'backend/data/approved_reader_bootstrap.json']['path'])
    assert {r['slug']: r for r in bootstrap['titles'] if r['slug'] not in slugs} == {
        r['slug']: r for r in prior_bootstrap['titles']}
    for slug in slugs:
        package = assert_current_reviewed_release(ROOT, slug, baseline)
        record = load(package / 'rights_decision.json')
        assert record['territories'] == ['IN'] and set(record['uses']) == TEXT_USES
        assert registry['accepted_records'][record['decision_id']] == record_sha256(record)
        assert not load(package / 'publication_manifest.json')['audio_release']['exposed']


def test_removed_editions_have_no_active_payloads_and_cannot_be_reexposed():
    policy = load(ROOT / 'data/catalog_exclusions.json')
    assert policy == load(ROOT / 'backend/data/catalog_exclusions.json')
    receipt = load(ROOT / 'internal/legal/catalogue_clearance_20261002/removed_titles_20261110/removal-manifest.json')
    assert set(receipt['slugs']) == REMOVED
    for row in receipt['source_files']:
        assert not (ROOT / row['path']).exists()
    for slug in REMOVED:
        assert policy['titles'][slug]['reader_excluded'] is True
        assert slug not in catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS
        spoofed = {'slug': slug, 'id': slug, 'is_published': True,
                   'publication_status': 'LIVE_APPROVED', 'audio_enabled': True}
        assert not catalog_truth.is_live_approved_book(spoofed)
        assert not catalog_truth.can_expose_reader(spoofed)
        assert not catalog_truth.can_expose_audio(spoofed)
