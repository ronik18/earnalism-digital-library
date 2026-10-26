"""Fail-closed recognition of approved protected package-v2 delivery.

This validates a canonical publication binding; it does not grant rights, leases,
change rollout, or make an arbitrary package public.
"""
import hashlib
import json
import re
try:
    from .audiobook_packages import validate_audiobook_package, validate_active_release_state
    from .rights_decision_gate import load_production_registry, load_audio_package_binding
except ImportError:
    from audiobook_packages import validate_audiobook_package, validate_active_release_state
    from rights_decision_gate import load_production_registry, load_audio_package_binding

MODE = 'PROTECTED_PACKAGE_V2'
SCHEMA = 'audiobook_protected_package_publication.v1'
SHA = re.compile(r'^[a-f0-9]{64}$')


def protected_package_publication_valid(book):
    try:
        if book.get('audiobook_release_mode') != MODE:
            return False
        approval = book['audiobook_public_package_approval']
        accepted, revoked = load_production_registry()
        audio_decision = approval.get('audio_rights_decision_id')
        audio_digest = approval.get('audio_rights_record_sha256')
        if (not isinstance(audio_decision, str) or not audio_decision
                or not isinstance(audio_digest, str) or not SHA.fullmatch(audio_digest)
                or audio_decision in revoked or accepted.get(audio_decision) != audio_digest):
            return False
        state = validate_active_release_state(book['audiobook_active_release'])
        slug = book['slug']; descriptor = state['active_release_descriptor_sha256']
        rights_binding = load_audio_package_binding(slug, descriptor)
        if not rights_binding or rights_binding['decision_id'] != audio_decision or rights_binding['record_sha256'] != audio_digest:
            return False
        if (state['slug'] != slug or state['status'] != 'ACTIVE'
                or state['candidate_release_descriptor_sha256'] or state['rollout']['percentage'] != 0
                or approval['schema_version'] != SCHEMA or approval['status'] != 'PUBLIC_APPROVED'
                or approval['slug'] != slug or approval['release_descriptor_sha256'] != descriptor
                or approval['endpoint'] != f'/api/reader/book/{slug}/audiobook/manifest'):
            return False
        package = validate_audiobook_package(book['audiobook_packages'][descriptor], expected_slug=slug,
            expected_source_sha256=book['source_hash'],
            expected_manuscript_sha256=book['audiobook_manuscript_sha256'],
            expected_release_descriptor_sha256=descriptor)
        acceptance = approval['acceptance']
        encoded = json.dumps(acceptance,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        if (hashlib.sha256(encoded).hexdigest() != approval['acceptance_sha256']
                or acceptance['schema_version'] != 'audiobook_public_package_acceptance.v1'
                or acceptance['release_descriptor_sha256'] != descriptor
                or acceptance['package_version'] != package['package_version']
                or acceptance['duration_ms'] != package['duration_ms']
                or acceptance['segment_count'] != package['segment_count']
                or set(acceptance['production_proof_sha256']) != {'playback','business','accounting'}
                or any(not SHA.fullmatch(v) for v in acceptance['production_proof_sha256'].values())
                or not re.fullmatch(r'[a-f0-9]{40}',acceptance['accounting_commit'])):
            return False
        evidence = book['audiobook_package_release_evidence'][descriptor]
        if (evidence['schema_version'] != 'audiobook_package_release_evidence.v1'
                or evidence['slug'] != slug or evidence['release_descriptor_sha256'] != descriptor
                or evidence['package_version'] != package['package_version']
                or evidence['release_eligible'] is not True or evidence['receipt_roles'] != ['primary','replica']
                or evidence['primary_release_manifest_store'] != 'prod'
                or evidence['replica_release_manifest_store'] != 'dr'
                or not evidence['primary_release_manifest_version_id']
                or not evidence['replica_release_manifest_version_id']
                or evidence['primary_release_manifest_version_id'] == evidence['replica_release_manifest_version_id']
                or type(evidence['release_manifest_size_bytes']) is not int or evidence['release_manifest_size_bytes'] <= 0
                or evidence['release_manifest_key'] != f'v1/prod/sprint1/{slug}/releases/{descriptor}/release-manifest.json'):
            return False
        if any(not SHA.fullmatch(evidence[k]) for k in ('primary_receipt_sha256','replica_receipt_sha256',
                'release_manifest_sha256','primary_release_manifest_receipt_sha256','replica_release_manifest_receipt_sha256')):
            return False
        for track in package['tracks']:
            for chunk in track['chunks']:
                for asset in chunk['assets'].values():
                    if asset['storage']['store'] != 'prod' or not asset['replicas'] or any(r['store'] != 'dr' for r in asset['replicas']):
                        return False
        return True
    except (KeyError,TypeError,ValueError,AttributeError,OSError):
        return False
