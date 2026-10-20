"""Exact retained-successor editorial acceptance, never an acoustic PASS.

Adoptions come only from the reviewed programme registry, not descriptor flags
or environment variables. The shipped registry intentionally has no adoption.
Package/source, receipt/version, cohort/auth/lease/accounting validators remain
in the release manager; this verifier replaces only its legacy numeric QA gate.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Mapping
from datetime import datetime, timezone
from rights_decision_gate import evaluate_accepted_record, load_production_registry

POLICY = 'open_window_retained_successor.v1'
REGISTRY = Path(__file__).resolve().parents[1] / 'release_gate/open_window_successor_adoptions.json'
IDENTITY = {
    'slug': 'the-open-window',
    'book_uuid': '74251b53-9e18-49fb-9fff-bb7c505633d4',
    'controlled_source_sha256': '058d0cda5a3c8449cbce06e0698048251881be4c6fc8d06fd0bc3a1bb8ec8587',
    'manuscript_sha256': 'f43d04cc2097668e91190ada89e283ad4908c360c4d7f6011a44b8f83d9659be',
    'master_mp3_sha256': '1fd37c818d4869eac8548811c714bd8907d0753ffa31b37fbf63d6e4764059a5',
    'master_wav_sha256': 'dc2388473bf44a571265cf1e230e846c1d5282434b7c9cc8f5d182c9887cba66',
}
ACCEPTANCE_SHA = '3c54a757db57f9df5d680ab4c52d0d892fcac4312ee25cf6c44894cb0ad0d301'
AUDIO_DECISION_SHA = '7f00f2deb1d2ab014801e5154429983bb9198324d8a8c37e17e7cae5a1511cef'
AUDIO_PROPOSITION_SHA = '90cbae317923f226bbff8d3b25c4f0bd81173697eb6af1ddbf94ee79f92eb971'
TRIAGE_SHA = 'd662ae5bcd0b62916d4d588574b87ce0e5c760944e236436dfd0608781843bf0'
QA_SHA = '787aed8eaa7ac80677de1c56ee88c25a26b800ae2652ba97136eedb6695ea8b7'
CHUNK_MAPPING_SHA = '3f8361e7b146c3304b0608eec2476dabfa33b59b4ca5df028f73807599b47c8d'
LEXICAL_UNITS = ['u000002', 'u000010', 'u000017', 'u000031', 'u000034', 'u000035']


class SuccessorAcceptanceError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value) and value != '0' * 64


def chunk_mapping_digest(package):
    """Pin unchanged audio/sidecar bytes and order, excluding future store locators."""
    try:
        tracks = []
        count = 0
        for track in package['tracks']:
            chunks = []
            for chunk in track['chunks']:
                count += 1
                assets = {role: {k: asset[k] for k in ('sha256', 'size_bytes', 'mime_type')}
                          for role, asset in chunk['assets'].items()}
                chunks.append({**{k: v for k, v in chunk.items() if k != 'assets'}, 'assets': assets})
            tracks.append({**{k: v for k, v in track.items() if k != 'chunks'}, 'chunks': chunks})
        if count != 29:
            raise ValueError()
        return hashlib.sha256(canonical(tracks)).hexdigest()
    except (KeyError, TypeError, ValueError, AttributeError):
        raise SuccessorAcceptanceError('Exact 29-chunk successor audio/sidecar mapping is incomplete') from None


def load_trusted_adoption():
    """Only a separately reviewed registry change can adopt the real records."""
    try:
        registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
        if registry.get('schema') != 'earnalism.successor-adoption-registry.v1':
            raise ValueError()
        entries = registry['adoptions']
        if not isinstance(entries, list):
            raise ValueError()
        matches = [e for e in entries if isinstance(e, dict) and e.get('record', {}).get('policy') == POLICY]
        if len(matches) != 1:
            raise ValueError()
        entry = matches[0]
        record = entry['record']
        if not digest(entry.get('record_sha256')) or hashlib.sha256(canonical(record)).hexdigest() != entry['record_sha256']:
            raise ValueError()
        return record
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise SuccessorAcceptanceError('Exact successor policy/audio-use adoption is missing or untrusted') from None


def validate(descriptor, package, controlled_language, downstream_gates):
    adopted = load_trusted_adoption()
    if (adopted.get('status') != 'ADOPTED' or adopted.get('policy') != POLICY
            or any(adopted.get(k) != v for k, v in IDENTITY.items())
            or adopted.get('acceptance_representation_sha256') != ACCEPTANCE_SHA
            or adopted.get('unaddressed_material_defects') != []
            or not digest(adopted.get('deployed_source_join_sha256'))):
        raise SuccessorAcceptanceError('Exact successor adoption/source/material-defect binding is incomplete')
    decision = adopted.get('policy_adoption')
    if (not isinstance(decision, Mapping) or decision.get('status') != 'ADOPTED'
            or not digest(decision.get('decision_sha256'))
            or not isinstance(decision.get('adopted_by'), str) or not decision['adopted_by'].strip()
            or not isinstance(decision.get('authority_reference'), str) or not decision['authority_reference'].strip()):
        raise SuccessorAcceptanceError('Independently adopted editorial policy is required')
    rights = adopted.get('audio_use_decision')
    accepted, revoked = load_production_registry()
    decision_id = rights.get('decision_id') if isinstance(rights, dict) else None
    if accepted.get(decision_id) != AUDIO_DECISION_SHA:
        raise SuccessorAcceptanceError('Exact audio-use decision is not adopted in the trusted rights registry')
    verdict = evaluate_accepted_record(rights, edition_id=IDENTITY['slug'], operator_id='reo-enterprise',
        country='IN', country_trusted=True, use='audio_stream',
        required_components={'source_file': IDENTITY['controlled_source_sha256'],
            'selected_manuscript': IDENTITY['manuscript_sha256'],
            'master_mp3': IDENTITY['master_mp3_sha256'], 'master_wav': IDENTITY['master_wav_sha256'],
            'audio_component_bindings': 'a0ca9abe6741ce0f5a7df8ee863fd4f7664cda65da2eac8f1900872de82611fe'},
        accepted_records=accepted, revoked_decision_ids=revoked, now=datetime.now(timezone.utc))
    if not verdict.passed:
        raise SuccessorAcceptanceError('Native exact India audio-use rights gate denied the successor')
    if chunk_mapping_digest(package) != CHUNK_MAPPING_SHA:
        raise SuccessorAcceptanceError('Successor chunk order, audio, sidecar or timing mapping changed')
    candidate = descriptor.get('release_candidate_evidence')
    gates = candidate.get('gates') if isinstance(candidate, Mapping) else None
    evidence = descriptor.get('evidence_sha256')
    if (any(descriptor.get(k) != v for k, v in IDENTITY.items())
            or str(controlled_language or '').strip().lower() not in ('en', 'eng', 'english')
            or descriptor.get('release_candidate_status') != 'OWNER_ACCEPTED_UNCERTAINTY_STORAGE_PENDING'
            or descriptor.get('known_release_blockers') != downstream_gates
            or not isinstance(candidate, Mapping) or candidate.get('acceptance_policy') != POLICY
            or candidate.get('status') != 'OWNER_ACCEPTED_UNCERTAINTY'
            or candidate.get('acceptance_representation_sha256') != ACCEPTANCE_SHA
            or candidate.get('human_scores') is not None or candidate.get('acoustic_pass_claimed') is not False
            or candidate.get('all_release_gates_passed') is not False
            or candidate.get('all_pre_storage_release_gates_passed') is not False
            or candidate.get('unit24_disposition') != 'OWNER_ACCEPTED_UNCERTAINTY_UNIT24_ONLY'
            or candidate.get('remaining_lexical_uncertainty_units') != LEXICAL_UNITS
            or not isinstance(gates, Mapping) or gates.get('confirmed_material_defects') != []
            or any(gates.get(k) is not True for k in ('reader_truth', 'source_content_toc',
                'first_words_match', 'last_words_match', 'ordered_content_integrity', 'front_cover', 'back_cover'))
            or gates.get('sync_tier') != 'SOURCE_UNIT_PARAGRAPH_BOUNDS_ONLY'
            or gates.get('highlight_sync_enabled') is not False
            or any(k.endswith('_score') or k in ('listening_minimum_scores', 'listening_sample_count') for k in gates)
            or not isinstance(evidence, Mapping)
            or any(not digest(v) for v in evidence.values())
            or any(evidence.get(k) != v for k, v in {
                'successor_acceptance': ACCEPTANCE_SHA, 'remaining_region_triage': TRIAGE_SHA,
                'master_provenance_and_qa': QA_SHA, 'audio_use_proposition': AUDIO_PROPOSITION_SHA,
                'deployed_source_join': adopted['deployed_source_join_sha256'],
                'policy_adoption': adopted['policy_adoption']['decision_sha256'],
                'audio_use_adoption': AUDIO_DECISION_SHA}.items())):
        raise SuccessorAcceptanceError('Successor editorial evidence is incomplete, inflated or mismatched')
    padding = descriptor.get('padding_disposition') or {}
    if (descriptor.get('duration_ms') != 491436 or descriptor.get('sample_rate') != 24000
            or descriptor.get('master_samples') != 11794472
            or padding.get('preserve_audio_bytes') is not True
            or padding.get('paragraph_019_terminal_silent_samples') != 11
            or padding.get('exact_sample_trim_enforced') is not False):
        raise SuccessorAcceptanceError('Measured untrimmed successor padding must remain disclosed')
    return dict(descriptor)
