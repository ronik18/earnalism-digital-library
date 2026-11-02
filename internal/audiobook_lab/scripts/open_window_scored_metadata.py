"""Exact retained Ryan metadata, applied only inside proof-bound Open promotion."""
import json
import open_window_scored_retained as scored
from native_scored_metadata import apply_to_document

DISCLOSURE='AI voice: Ryan. Music: Heartwarming/Heartbreaking, Kevin MacLeod (https://incompetech.com), CC BY 4.0 https://creativecommons.org/licenses/by/4.0/; edited.'


def metadata_for_package(package,descriptor_sha256,controlled_language):
    if package.get('release_evidence_version')!=scored.POLICY:return None
    descriptor=json.loads((scored.DATA/'frozen-v5/release-descriptor.PROPOSED.json').read_text())
    scored.require(descriptor_sha256==scored.DESCRIPTOR_SHA==package.get('release_descriptor_sha256'),
        'Exact retained Ryan narrator descriptor required')
    scored.validate(descriptor,package,controlled_language,scored.common.DOWNSTREAM)
    audio=package['tracks'][0]['chunks'][0]['assets']['audio']
    scored.require(audio['sha256']==scored.SOURCE['master_mp3_sha256'] and len(DISCLOSURE)<=160,
        'Exact retained Ryan recording/disclosure required')
    return {'audiobook_provider':'','audiobook_voice':'Ryan','narration_disclosure':DISCLOSURE,
        'duration_ms':package['duration_ms'],'size_bytes':audio['size_bytes']}
