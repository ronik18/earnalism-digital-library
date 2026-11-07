"""Read-only release check for the actual thermal-touch package, not lunar fixtures.

Reuses source/audio/package validation. Never uploads or invents owner/listening
or platform outcomes; recorded owner acceptance remains distinct from tests.
"""
import json
from pathlib import Path
from .assemble import sha, require
from .package import validate_inputs

SCHEMA = 'earnalism.thermal-publication-profile.v1'
ORIGINAL_SHA = '62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4'


def load(path):
    return json.loads(Path(path).read_text())


def inside(root, relative):
    path = (root / relative).resolve()
    require(path.is_relative_to(root), 'Release evidence escapes project')
    return path


def bound(root, record):
    path = inside(root, record['path'])
    require(sha(path) == record['sha256'], 'Release evidence changed: ' + record['path'])
    return path


def platform_check(value, kit, owner, manifest_hash):
    require(value.get('delivery_manifest_sha256') == manifest_hash, 'Stale platform review')
    formats = value.get('formats', {})
    require(set(formats) == {'landscape', 'shorts'}, 'Both destination checks required')
    for fmt, source in [('landscape', 'landscape/video.mp4'), ('shorts', 'clean-shorts/video.mp4')]:
        item = formats[fmt]
        require(item.get('video_id') and item.get('uploaded_media_sha256') == sha(kit / source), 'Wrong uploaded master')
        require(item.get('manual_english_captions_sha256') == sha(kit / 'captions.srt'), 'Unverified English captions')
        cover = 'thumbnail-landscape.png' if fmt == 'landscape' else 'thumbnail-shorts.png'
        require(item.get('reviewed_cover_sha256') == sha(kit / cover) and item.get('cover_verified') is True, 'Cover not verified')
        require(item.get('copyright_check') == 'NO_ISSUES' and item.get('community_check') == 'NO_ISSUES', 'Unresolved platform check')
        require(item.get('playback_verified') is True and item.get('caption_display_verified') is True, 'Playback/caption review incomplete')
        settings = item.get('settings', {})
        required = {'made_for_kids': False, 'age_restricted': False, 'video_language': 'English',
                    'ai_disclosure': True, 'paid_promotion': False, 'automatic_chapters': False,
                    'automatic_places': False, 'automatic_concepts': False, 'automatic_dubbing': False,
                    'visual_enhancement': False, 'audio_enhancement': False}
        require(all(type(settings.get(k)) is type(v) and settings.get(k) == v for k, v in required.items()), 'Unverified or incorrect upload setting')
        require(settings.get('remixing') in ('none', 'audio_only'), 'Remixing not restricted where available')
        require(item.get('saved_title') and '#earnalism' in item.get('saved_description', '') and
                '#learnalism' in item['saved_description'], 'Saved copy incomplete')
    require(owner.get('audience') == {'selfDeclaredMadeForKids': False, 'ageRestriction': False}, 'Audience requires owner confirmation')


def check(profile_path, project_root):
    root = Path(project_root).resolve(); profile = load(profile_path)
    require(profile.get('schema') == SCHEMA, 'Wrong release profile')
    require(sha(root / 'Earnalism_English_Audiobook_Pipeline_Qwew&Ace.ipynb') == ORIGINAL_SHA, 'Original notebook changed')
    kit = inside(root, profile['candidate'])
    require(kit.parent.name == '04-thermal-touch', 'Wrong topic adapter')
    mh = sha(kit / 'delivery-manifest.json')
    require(mh == profile['delivery_manifest_sha256'], 'Changed final candidate')
    manifest = load(kit / 'delivery-manifest.json')
    require(manifest.get('schema') == 'earnalism.thermal-private-kit.v1', 'Not an actual thermal package')
    for name, digest in manifest['files'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Invalid manifest member')
        require(sha(inside(root, str(kit.relative_to(root) / name))) == digest, 'Changed final media/evidence: ' + name)
    validate_inputs(kit)
    owner = load(bound(root, profile['owner_decision']))
    require(owner.get('delivery_manifest_sha256') == mh and owner.get('owner_release_quote') and
            owner.get('owner_acceptance_quote'), 'Current explicit owner decision required')
    report = load(bound(root, profile['review_report']))
    require(report.get('delivery_manifest_sha256') == mh, 'Stale graphical/technical review')
    require(all(v.get('ended') is True and v.get('error') is None for v in
                report['complete_browser_playback_checks'].values()) and
            set(report['complete_browser_playback_checks']) == {'landscape', 'portrait'}, 'Both full playback checks required')
    research = inside(root, profile['research_root'])
    for name, digest in load(research / 'research-manifest.json').items():
        require(sha(inside(research, name)) == digest, 'Research evidence changed')
    spoken = [{k: u[k] for k in ('id', 'scene', 'text')} for u in load(kit / 'units.json')]
    require(spoken == load(research / 'script-units.json'), 'Spoken script differs from verified research')
    claims = load(research / 'fact-claim-map.json')
    require(claims.get('state') == 'RESEARCH_VERIFIED_PRODUCTION_REVIEW_PENDING', 'Research review missing')
    source_ids = {s['id'] for s in load(kit / 'sources.json')}
    for claim in claims['claims']:
        if claim['sources'] == ['LOCAL_STRATEGY']:
            require(claim['id'] == 'C7' and claim['units'] == ['s06'] and
                    claim['claim'] == 'Next lesson is cold-glass condensation', 'Unverified local claim')
            bound(root, profile['next_preparation'])
        else:
            require(set(claim['sources']) <= source_ids, 'Unverified claim citation')
    require({u for c in claims['claims'] for u in c['units']} >= {u['id'] for u in load(kit / 'units.json')}, 'Missing spoken-claim coverage')
    from .finish import acoustic_score
    score = load(kit / 'score.provenance.json')
    require(score['license'] == 'CC0-1.0' and score['external_compositions'] == [], 'Score rights unresolved')
    for field, file in [('asset_manifest_sha256', 'manifest.json'), ('license_sha256', 'LICENSE'), ('readme_sha256', 'README.md')]:
        require(sha(acoustic_score.ASSETS / file) == score[field], 'Score rights evidence changed')
    require(sha(kit / 'score.wav') == score['recording_sha256'], 'Score recording changed')
    rights = load(root / 'video_studio/config/rights-owner.json')
    require(rights.get('brand_commercial_rights') is True and rights.get('remotion_eligibility') == 'individual_or_up_to_3_employees', 'Owner rights/renderer eligibility missing')
    for r in load(root / 'video_studio/rights/evidence.json'):
        require(sha(root / 'video_studio/rights' / r['file']) == r['sha256'], 'Model/tool rights evidence changed')
    for evidence in profile['evidence']:
        bound(root, evidence)
    platform = load(bound(root, profile['platform_review']))
    platform_check(platform, kit, owner, mh)
    return {'state': 'READY_FOR_MANUAL_YOUTUBE_PUBLICATION', 'delivery_manifest_sha256': mh,
            'owner_decision': profile['owner_decision']['sha256'], 'formats': ['landscape', 'shorts'],
            'scope': 'Current source, facts, rights, recorded review/owner decision and actual platform evidence. No publication action performed.'}
