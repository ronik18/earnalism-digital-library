"""Exact approved cover pair; no image upload or production mutation."""
import hashlib,json
from pathlib import Path
from backend.catalog_truth import load_controlled_artifact_book
from backend.rights_decision_gate import load_production_registry,record_sha256
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={'front':'ab934152cb8fb81836c9e644bae2af453d11871df22f7183e5de0fc25838bdfc','back':'05d22a1728308733d7a25f4271a47f310aecf23f9e73e63191e971b79d524b3a'}
def read(path):return json.loads(path.read_text())
def test_exact_revised_cover_pair_mirrors_and_checksum_bindings():
    a=ROOT/'data/controlled_publications/the-open-window';b=ROOT/'backend/data/controlled_publications/the-open-window'
    for name in ['public_book.json','reader_manifest.json','approval_evidence.json','checksum_manifest.json','rights_decision.json','cover_approval_evidence.json','publication_manifest.json']:
        assert (a/name).read_bytes()==(b/name).read_bytes()
    for row in read(b/'checksum_manifest.json')['files']:
        assert hashlib.sha256((b/row['file']).read_bytes()).hexdigest()==row['sha256']
    evidence=read(b/'cover_approval_evidence.json');book=read(b/'public_book.json')
    for kind,sha in EXPECTED.items():
        event=next(x for x in evidence['history'] if x['event_id']==evidence['active_approvals'][kind])
        assert event['candidate_sha256']==event['remote_sha256']==sha
        assert event['cloudinary']['version_id']
        assert event['cloudinary']['url']==book['cover_url' if kind=='front' else 'back_cover_url']
        assert event['reader_audio_release_truth_unchanged'] is True
    projected=load_controlled_artifact_book('the-open-window',artifact_dir=b)
    assert EXPECTED['front'] in projected['cover_url']
    assert EXPECTED['back'] in projected['back_cover_url']
    assert projected['audio_enabled'] is False
    from backend.publication_manifest import canonical_sha256
    manifest=read(b/'publication_manifest.json')
    assert manifest['manifest_sha256']==canonical_sha256(manifest)
    assert manifest['reader_release']['cover_url']==book['cover_url']
    for name,digest in manifest['artifacts'].items():
        assert hashlib.sha256((b/(name+'.json')).read_bytes()).hexdigest()==digest

    assert book['audiobook_package_canary']['candidate_release_descriptor_sha256']=='028f65d8551523eecaad03bb5b476070f0c48c1fb0771bf9abc9163ecd5ba4b2'
def test_cover_successor_preserves_reader_permissions_and_audio_hold():
    directory=ROOT/'backend/data/controlled_publications/the-open-window';decision=read(directory/'rights_decision.json');registry,_=load_production_registry()
    assert registry[decision['decision_id']]==record_sha256(decision)
    assert 'india-20261025-the-open-window-reader-cover-canary-metadata' in registry
    assert decision['territories']==['IN']
    assert 'audio_stream' not in decision['uses']
    assert decision['uses']==['catalog_metadata','cover_display','reader_preview','reader_delivery','reading_pass_session','reading_pass_renewal']
    boot=read(ROOT/'backend/data/approved_reader_bootstrap.json')
    row=next(x for x in boot['titles'] if x['slug']=='the-open-window')
    assert row['decision_id']==decision['decision_id'] and row['record_sha256']==record_sha256(decision)
