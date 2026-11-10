"""Action-scoped release decisions. No provider, generation or mutation operations.

Text timing is inapplicable only to the reviewed standalone audio consumer. A
warning is not a confirmed defect, and neither kind of finding can replace a
missing mandatory fidelity/rights/playback/accounting acceptance.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.domain.audio_quality import classify_quality_findings
from backend.domain.editorial_release_policy import (
    uses_automated_editorial_policy, routine_review_not_applicable,
)

CONSUMER_CONTRACT = ROOT / 'internal/earnalism_intelligence/listener_text_sync_consumer.json'
FEATURES_OFF = {key: False for key in (
    'read_along', 'highlighting', 'captions', 'text_linked_navigation',
)}
SHA = re.compile(r'^[a-f0-9]{64}$')
CONSUMER_SOURCES = (
    'frontend/src/App.js',
    'frontend/src/experiences-v2/listener/ListenerExperienceV2Route.jsx',
    'frontend/src/experiences-v2/listener/ListenerExperienceV2.jsx',
    'frontend/src/lib/audioPackageManifest.js',
    'frontend/src/lib/audiobookPlayback.js',
    'frontend/src/experiences-v2/reader/ReaderExperienceV2Route.jsx',
    'frontend/src/experiences-v2/shared/ReleaseTruthAdapter.js',
    'frontend/src/pages/Reader.jsx',
    'frontend/src/pages/BookDetail.jsx',
    'frontend/src/lib/audioReleaseSafety.js',
    'frontend/src/components/ReaderAudiobookPanel.jsx',
    'frontend/src/components/PremiumListeningRail.jsx',
)


def _binding(manifest: Mapping[str, Any]) -> dict:
    audio = manifest.get('audio') if isinstance(manifest.get('audio'), Mapping) else {}
    source = manifest.get('manuscript') if isinstance(manifest.get('manuscript'), Mapping) else {}
    return {'slug': manifest.get('slug'), 'audio_sha256': audio.get('sha256'),
            'manuscript_sha256': source.get('sha256'),
            'package_version': audio.get('package_version'),
            'release_descriptor_sha256': manifest.get('release_descriptor_sha256')}


def validate_sync_not_applicable(manifest: Mapping[str, Any], check: Mapping[str, Any]) -> None:
    """Verify source/consumer and exact candidate binding; unknown defaults strict.

    This does not waive package/schema/sidecar integrity, content or media clocks.
    The registry records one reviewed consumer, not a title-name exception.
    """
    proof = check.get('applicability')
    if check.get('status') != 'NOT_APPLICABLE' or not isinstance(proof, dict):
        raise ValueError('text sync requires measured acceptance or verified NOT_APPLICABLE evidence')
    contract = json.loads(CONSUMER_CONTRACT.read_text(encoding='utf-8'))
    if (contract.get('schema') != 'earnalism.reviewed_text_sync_consumer.v1'
            or contract.get('consumer') != 'listener_v2_audio_only.v1'
            or not isinstance(contract.get('sources'), dict)
            or set(contract['sources']) != set(CONSUMER_SOURCES)
            or any(not isinstance(v, str) or not SHA.fullmatch(v) for v in contract['sources'].values())):
        raise ValueError('complete reviewed consumer source contract is required')
    binding = _binding(manifest)
    if (not isinstance(binding['slug'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,119}', binding['slug'])
            or any(not isinstance(binding[k], str) or not SHA.fullmatch(binding[k])
                   for k in ('audio_sha256', 'manuscript_sha256', 'release_descriptor_sha256'))
            or not isinstance(binding['package_version'], str)
            or not re.fullmatch(r'sha256-[a-f0-9]{64}', binding['package_version'])):
        raise ValueError('text-sync applicability must bind exact source, audio, descriptor and package')
    for record in (manifest, manifest.get('audio') or {}):
        if (any(key in record and record[key] is not False for key in ('highlight_sync_enabled', 'read_along_enabled', 'captions_enabled', 'text_linked_navigation_enabled'))
                or (record.get('sync_tier') is not None and record['sync_tier'] not in {'AUDIO_ONLY_NO_SYNC', 'NONE', 'NO_SYNC'})
                or (record.get('sync_mode') is not None and record['sync_mode'] not in {'none', 'audio_only'})):
            raise ValueError('an unsynced release must disable text-sync features and make no sync claim')
    delivery = manifest.get('delivery')
    expected_delivery = {'consumer': contract['consumer'],
                         'route': f"/listener/{binding['slug']}",
                         'features': FEATURES_OFF, 'sync_claim': 'NONE'}
    if delivery != expected_delivery or any(type(v) is not bool for v in delivery['features'].values()):
        raise ValueError('nonconsumer acceptance requires disabled text-sync features; retired customer features cannot be restored')
    if (proof.get('schema') != 'earnalism.text_sync_applicability.v1'
            or proof.get('status') != 'NOT_APPLICABLE'
            or proof.get('binding') != binding or proof.get('delivery') != delivery
            or proof.get('consumer_sources') != contract['sources']):
        raise ValueError('text-sync nonconsumer evidence is missing, stale or bound to another candidate')
    # Verify actual local consumer bytes, not a caller-supplied unused-feature flag.
    for relative, expected in contract['sources'].items():
        path = ROOT / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('selected consumer source changed; reassess text-sync applicability')


def automated_check_accepted(manifest: Mapping[str, Any], name: str,
                             check: Mapping[str, Any]) -> bool:
    try:
        automated_editorial = uses_automated_editorial_policy(manifest)
    except ValueError:
        return False
    if (automated_editorial and name == 'audio_review_samples'
            and dict(check) == routine_review_not_applicable()):
        return True
    # Historical measured PASS is evidence, never permission to restore retired UI.
    for record in (manifest, manifest.get('audio') or {}):
        if any(key in record and record[key] is not False for key in (
            'read_along_enabled', 'highlight_sync_enabled', 'text_linked_navigation_enabled',
        )):
            return False
    delivery = manifest.get('delivery') or {}
    features = delivery.get('features') or {}
    if any(key in features and features[key] is not False for key in (
        'read_along', 'highlighting', 'text_linked_navigation',
    )):
        return False
    if check.get('status') == 'PASS':
        if automated_editorial:
            try:
                validate_bound_automated_check(manifest, name, check, ROOT)
            except (ValueError, OSError, KeyError, TypeError):
                return False
        return True
    if name != 'synchronization' or check.get('status') != 'NOT_APPLICABLE':
        return False
    try:
        validate_sync_not_applicable(manifest, check)
    except (ValueError, OSError, KeyError, TypeError):
        return False
    return True


def automated_candidate_binding(manifest: Mapping[str, Any]) -> dict:
    audio = manifest.get('audio') or {}
    return {**_binding(manifest), 'model': audio.get('model'), 'voice': audio.get('voice'),
            'duration_seconds': audio.get('duration_seconds')}


def validate_bound_automated_check(manifest: Mapping[str, Any], name: str,
                                  check: Mapping[str, Any], root: Path) -> dict:
    """Read and checksum exact-candidate evidence at evaluation AND promotion."""
    if check.get('status') != 'PASS':
        raise ValueError(f'{name} requires actual automated PASS evidence')
    path = root / str(check.get('evidence_path') or '')
    expected = check.get('evidence_sha256')
    data = path.read_bytes() if path.is_file() else b''
    if (not isinstance(expected, str) or not SHA.fullmatch(expected)
            or not path.is_file() or hashlib.sha256(data).hexdigest() != expected):
        raise ValueError(f'{name} evidence checksum mismatch or missing file')
    evidence = json.loads(data)
    if (not isinstance(evidence, dict)
            or evidence.get('schema') != 'earnalism.automated_release_check.v1'
            or evidence.get('check') != name or evidence.get('status') != 'PASS'
            or evidence.get('binding') != automated_candidate_binding(manifest)):
        raise ValueError(f'{name} evidence is not bound to this exact candidate')
    return {**dict(check), 'status': 'PASS', 'evidence_path': str(path.resolve()),
            'binding': evidence['binding']}


def automated_candidate_blockers(manifest: Mapping[str, Any]) -> list[str]:
    """Validate the complete candidate, never treat a pilot set as a full master.

    Human-review exemption does not authorize generation or publication. Existing
    runtime credentials, rights checks, exact gate and private staging still bind.
    """
    try:
        if not uses_automated_editorial_policy(manifest):
            return []
    except ValueError as exc:
        return [str(exc)]
    issues = []
    audio = manifest.get('audio') or {}
    source = manifest.get('manuscript') or {}
    if not isinstance(audio, Mapping) or not isinstance(source, Mapping):
        return ['Complete audio and manuscript metadata are required']
    if manifest.get('owner_public_release_intent') is not True:
        issues.append('Explicit job publication authority is required')
    if manifest.get('release_holds') or manifest.get('publication_hold') is True:
        issues.append('An existing release hold remains active')
    if (not isinstance(manifest.get('slug'), str)
            or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,119}', manifest['slug'])):
        issues.append('A valid title slug is required')
    if not audio.get('path') or not audio.get('model') or not audio.get('voice'):
        issues.append('A complete master path, model and voice are required')
    for label, value in [('audio', audio.get('sha256')), ('manuscript', source.get('sha256')),
                         ('descriptor', manifest.get('release_descriptor_sha256'))]:
        if not isinstance(value, str) or not SHA.fullmatch(value):
            issues.append(f'Exact {label} checksum binding is required')
    if (not isinstance(audio.get('package_version'), str)
            or not re.fullmatch(r'sha256-[a-f0-9]{64}', audio['package_version'])):
        issues.append('An immutable audio package version is required')
    duration = audio.get('duration_seconds')
    if type(duration) not in (int, float) or not 0 < duration < float('inf'):
        issues.append('A finite positive full-master duration is required')
    root = Path(str(manifest.get('artifact_root') or ROOT))
    path = root / str(audio.get('path') or '')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != audio.get('sha256'):
        issues.append('Full master is missing or changed after candidate preparation')
    return issues
