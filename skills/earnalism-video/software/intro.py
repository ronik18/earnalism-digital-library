"""Version-bound standard brand intro; no publication or review approval transfer."""
import hashlib,json,pathlib,shutil
ROOT=pathlib.Path(__file__).resolve().parent

def shift_cues(cues,seconds):
 if seconds<0:raise ValueError('Negative intro offset')
 return [{**c,'start':round(c['start']+seconds,6),'end':round(c['end']+seconds,6)} for c in cues]

def install(public,asset_root=None,expected_version=None):
 assets=pathlib.Path(asset_root) if asset_root else ROOT/'assets/standard-intro/v1'
 manifest=json.loads((assets/'manifest.json').read_text())
 if manifest['seconds']!=3:raise ValueError('Unexpected standard intro duration')
 if expected_version and manifest['version']!=expected_version:raise ValueError('Standard intro version mismatch')
 result={'seconds':3,'version':manifest['version']}
 for fmt in ('landscape','portrait'):
  name=fmt+'.mp4';source=assets/name
  if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['files'][name]:raise ValueError('Standard intro hash mismatch')
  dest=pathlib.Path(public)/('intro-'+name)
  if dest.exists():raise FileExistsError(dest)
  result[fmt]=f'runs/{pathlib.Path(public).name}/{dest.name}'
 for fmt in ('landscape','portrait'):shutil.copy2(assets/(fmt+'.mp4'),pathlib.Path(public)/('intro-'+fmt+'.mp4'))
 return result,manifest
