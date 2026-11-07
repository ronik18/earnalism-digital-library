"""Evidence-bound production-rights inventory; never grants human publication approval."""
import pathlib,json,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
def digest(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def audit(folder,root=None):
 root=pathlib.Path(root) if root else ROOT;folder=pathlib.Path(folder)
 owner_path=root/'config/rights-owner.json';owner=json.loads(owner_path.read_text()) if owner_path.exists() else {}
 evidence=json.loads((root/'rights/evidence.json').read_text());checks=[]
 for record in evidence:
  path=root/'rights'/record['file']
  if digest(path)!=record['sha256']:raise ValueError('Rights evidence changed: '+record['file'])
  checks.append({'document':record['file'],'sha256':record['sha256'],'source':record['url']})
 if 'license: apache-2.0' not in (root/'rights/qwen-model-card.md').read_text():raise ValueError('Model license not verified')
 narration=[]
 for meta_path in sorted((folder/'raw').glob('*.wav.json')):
  meta=json.loads(meta_path.read_text());prov=meta.get('provenance',{});audio=meta_path.with_suffix('')
  if meta.get('status')=='DERIVED_REQUIRES_REVIEW':
   from audio_derivation import check_unit
   check_unit(folder,audio.stem)
  if prov.get('model_id')!='Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice' or prov.get('model_revision')!='0c0e3051f131929182e2c023b9537f8b1c68adfe':raise ValueError('Narration model not covered by license evidence')
  if meta['wav_sha256']!=digest(audio):raise ValueError('Narration audio binding changed')
  card=next((v for v in prov.get('snapshot',{}).get('files',[]) if v['path']=='README.md'),None)
  if not card or card['sha256']!=digest(root/'rights/qwen-model-card.md'):raise ValueError('Narration model card differs from archived licensing evidence')
  narration.append({'file':audio.name,'sha256':meta['wav_sha256'],'model_revision':prov['model_revision']})
 assets=root/'assets/standard-intro/v1';manifest=json.loads((assets/'manifest.json').read_text())
 for name,expected in manifest['files'].items():
  if digest(assets/name)!=expected:raise ValueError('Brand asset changed: '+name)
 score=json.loads((folder/'score.provenance.json').read_text())
 if score['source_sha256']!=digest(root/'score.py') or score['recording_sha256']!=digest(folder/'score.wav'):raise ValueError('Stale music provenance')
 music_description='Original oscillator synthesis and documented source events; no imported samples or external melody. Source inspection does not guarantee no resemblance to any existing work.'
 music_licenses=[]
 if score['external_compositions']:raise ValueError('Imported compositions require individual licenses')
 if score['third_party_samples']:
  if score.get('kind')!='original acoustic chamber composition':raise ValueError('Imported music requires individual licenses')
  from acoustic_score import validate_assets
  bank=root/'assets/music/vcsl-piano-harp-v1';assets_manifest=validate_assets(bank)
  composers={'moon-score-v14-preserved-arrangement-retime':'retime_score.py','moon-score-v13-speech-aware-phrase-placement':'phrase_music_repair.py','moon-score-v12-editorial-orchestration':'editorial_score.py','moon-score-v4-acoustic-chamber':'acoustic_score.py','moon-score-v5-balanced-acoustic-chamber':'chamber_score.py','moon-score-v6-phrase-arrangement':'chamber_arrangement.py','moon-score-v7-balanced-arrangement':'balanced_score.py','moon-score-v8-refined-voicing':'final_chamber_score.py','moon-score-v9-final-note-balance':'chamber_score_v9.py','moon-score-v10-body-refinement':'chamber_score_v10.py','moon-score-v11-body-refinement':'final_chamber_score.py'}
  composer=composers.get(score.get('version'))
  if not composer or score.get('composition_source_sha256')!=digest(root/composer) or score.get('asset_manifest_sha256')!=digest(bank/'manifest.json'):raise ValueError('Acoustic composition source changed')
  if score.get('version')=='moon-score-v12-editorial-orchestration' and score.get('base_composition_source_sha256')!=digest(root/'final_chamber_score.py'):raise ValueError('Editorial base composer source changed')
  if score.get('version')=='moon-score-v13-speech-aware-phrase-placement':
   if score.get('helper_base_source_sha256')!=digest(root/'final_chamber_score.py') or score.get('helper_editorial_source_sha256')!=digest(root/'editorial_score.py'):raise ValueError('Speech-aware base/editorial composer source changed')
  if score.get('version')=='moon-score-v14-preserved-arrangement-retime':
   from retime_score import _verify_parent,canonical,map_intervals,preserve_events,timeline_map
   retime=score.get('retime',{});parent=pathlib.Path(retime['parent_folder']);_,old=_verify_parent(parent)
   if score.get('base_composition_source_sha256')!=digest(root/'final_chamber_score.py'):raise ValueError('Preserved acoustic base changed')
   expected={str((root/n).resolve()):digest(root/n) for n in ['retime_score.py','final_chamber_score.py']}
   if score.get('bound_source_sha256')!=expected or retime.get('bound_source_sha256')!=expected:raise ValueError('Preserved-score source bindings changed')
   for key,name in [('parent_delivery_manifest_sha256','delivery-manifest.json'),('parent_score_sha256','score.wav'),('parent_provenance_sha256','score.provenance.json')]:
    if retime.get(key)!=digest(parent/name):raise ValueError('Preserved-score parent binding changed')
   if retime.get('source_events_sha256')!=canonical(old['events']) or retime.get('source_rests_sha256')!=canonical(old['quiet_intervals']):raise ValueError('Preserved musical inventory changed')
   if [{k:v for k,v in e.items() if k!='time'} for e in score['events']]!=[{k:v for k,v in e.items() if k!='time'} for e in old['events']]:raise ValueError('Preserved arrangement revoiced')
   points=retime['timeline_points']
   parent_scenes=json.loads((parent/'props.json').read_text())['scenes'];current_props=json.loads((folder/'props.json').read_text());current_scenes=current_props['scenes']
   if abs(score['seconds']-current_props['duration'])>.001:raise ValueError('Preserved score duration differs from current voice timeline')
   checked=timeline_map(parent_scenes,current_scenes,points)
   if [(p['old'],p['new']) for p in checked]!=[(p['old'],p['new']) for p in points]:raise ValueError('Preserved score timeline lacks semantic anchors')
   expected_events,expected_mapping=preserve_events(old['events'],points,score['seconds'])
   if score['events']!=expected_events or retime.get('event_mapping')!=expected_mapping:raise ValueError('Preserved musical attack map changed')
   if score['quiet_intervals']!=map_intervals(old['quiet_intervals'],points):raise ValueError('Preserved authored rests changed')
   if retime.get('narration_sha256')!=digest(folder/'narration.wav'):raise ValueError('Preserved score has stale voice binding')
  if score.get('license')!='CC0-1.0' or score.get('license_sha256')!=digest(bank/'LICENSE') or score.get('readme_sha256')!=digest(bank/'README.md'):raise ValueError('Acoustic license evidence changed')
  if any(row not in assets_manifest['samples'] for row in score['third_party_samples']):raise ValueError('Unlicensed acoustic sample')
  for name,value in score.get('stems',{}).items():
   if pathlib.PurePath(name).name!=name or digest(folder/name)!=value:raise ValueError('Acoustic source stem changed')
  music_licenses=assets_manifest['documents'];music_description='Original computer-arranged composition using pinned VCSL acoustic piano and harp one-shot notes under CC0-1.0. No imported compositions. Full listening and resemblance review pending.'
 elif score.get('kind')=='original acoustic chamber composition':raise ValueError('Acoustic sample inventory missing')
 if owner.get('brand_commercial_rights') and owner.get('brand_logo_sha256')!=manifest['files']['production-lockup.png']:raise ValueError('Owner confirmation does not cover this logo')
 mechanical='COMPLETE' if owner.get('brand_commercial_rights') and owner.get('remotion_eligibility') in ('individual_or_up_to_3_employees','company_license_verified') else 'OWNER_EVIDENCE_PENDING'
 return {'status':mechanical,'scope':'Documented source, licensing, asset provenance and owner attestations; not a legal opinion or owner AV approval.','owner_confirmations':owner,'narration_bindings':narration,'documents':checks,'model':'Pinned Qwen stock Ryan, Apache-2.0 metadata and code license; no clone input','visuals':'Original procedural lunar diagrams, factual references paraphrased; no NASA imagery or logo used','font':'System Arial rendered into video pixels; no font binaries distributed','brand_assets':manifest['files'],'score_recording_sha256':score['recording_sha256'],'music':music_description,'music_license_documents':music_licenses,'remaining_review':['Owner complete listening and resemblance review of this score/mix','Owner audiovisual review of landscape and Shorts','Current artifact-bound episode publication approval'],'publication_authorized':False}
