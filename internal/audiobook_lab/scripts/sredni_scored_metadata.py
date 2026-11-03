"""Exact selected Sredni credits. Metadata is not playback/publication authority."""
import json
import sredni_scored_retained as scored

PACKAGE='sha256-8185d1b2e20ea325e0a5cfdcf5346f7511c1ccf49937a438f1305ba7566c383e'
AUDIO='60ce9893c5196e35ba8ee0ba7b491a53882f1e65ba3b1f31c01c052ed8cc7692'
METADATA='34f0f8a4dd14dd0952cb3f9436601be01e585ea964286162d01f894d71679ec3'
FIELD='sredni_source_qa_private_stage'
SCHEMA='earnalism.sredni_source_qa_private_stage.v1'
DISCLOSURE='AI voice: Verse. Music: Heartwarming/Heartbreaking, Kevin MacLeod (https://incompetech.com), CC BY 4.0 https://creativecommons.org/licenses/by/4.0/; edited.'


def metadata_for_package(package,descriptor_sha256,controlled_language):
    if package.get('release_evidence_version')!=scored.POLICY:return None
    descriptor=json.loads((scored.DATA/'prospective-registration/release-descriptor.json').read_text())
    scored.require(descriptor_sha256==scored.DESCRIPTOR_SHA==package.get('release_descriptor_sha256')
                   and package.get('package_version')==PACKAGE,'Exact stored Sredni credits package required')
    scored.validate(descriptor,package,controlled_language,scored.common.DOWNSTREAM)
    assets=package['tracks'][0]['chunks'][0]['assets']
    scored.require(assets['audio']['sha256']==AUDIO and assets['metadata']['sha256']==METADATA
                   and len(DISCLOSURE)==156,'Exact Verse/music credit assets required')
    return {'audiobook_provider':'','audiobook_voice':'Verse','narration_disclosure':DISCLOSURE,
            'duration_ms':package['duration_ms'],'size_bytes':assets['audio']['size_bytes']}


def metadata_for_selected_private_package(document,package,descriptor_sha256,controlled_language):
    """Called only after separate genuine selection/access checks by a future caller.

    This helper does not select a candidate, authenticate a member, authorize a
    lease, enable audio or supply a public override. Unstaged metadata is absent.
    """
    marker=document.get(FIELD)
    if not isinstance(marker,dict):return None
    scored.require(marker.get('schema_version')==SCHEMA
                   and marker.get('status')=='SOURCE_QA_STAGED_PRIVATE'
                   and marker.get('slug')=='sredni-vashtar'
                   and marker.get('candidate_descriptor_sha256')==descriptor_sha256==scored.DESCRIPTOR_SHA
                   and marker.get('candidate_package_version')==package.get('package_version')==PACKAGE
                   and document.get('audiobook_packages',{}).get(descriptor_sha256)==package,
                   'Exact staged selected Sredni package required for credits')
    value=metadata_for_package(package,descriptor_sha256,controlled_language)
    scored.require(marker.get('narrator_metadata')==value,'Stale staged narrator/music disclosure')
    return value
