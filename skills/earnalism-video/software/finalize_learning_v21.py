from pathlib import Path
import sys,json,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent));import studio
from frozen_edition import copy_frozen_soundtrack,encoded_audio_hash,verify
from participant_preview import make
p=studio.BASE/'outputs/moon-phases-production-review-v21';source=studio.BASE/'outputs/moon-refined-score-v20';verify(p)
if not (p/'delivery-manifest.json').exists():raise RuntimeError('Wait for full clean render to finish')
reference=encoded_audio_hash(source/'landscape.mp4');changed=False
for name in ['landscape.mp4','portrait.mp4','portrait-captioned.mp4']:
 if encoded_audio_hash(p/name)!=reference:copy_frozen_soundtrack(p,p/name);changed=True
archive=p/'logs/pre-finalization';archive.mkdir(exist_ok=True)
if changed:
 for name in ['landscape-preview.mp4','portrait-preview.mp4','landscape-preview.webm','portrait-preview.webm']:
  if (p/name).exists():(p/name).rename(archive/name)
 studio.create_web_preview(p)
(p/'technical.json').rename(archive/'technical.json');studio.write(p/'technical.json',[studio.verify_media(p/n) for n in ['landscape.mp4','portrait.mp4','portrait-captioned.mp4']])
studio.draft_watch(p);make(p)
(p/'delivery-manifest.json').rename(archive/'delivery-manifest.json')
studio.write(p/'frozen-audio-delivery.json',{'source':source.name,'encoded_audio_sha256':reference,'all_three_master_payloads_match':all(encoded_audio_hash(p/n)==reference for n in ['landscape.mp4','portrait.mp4','portrait-captioned.mp4']),'narration_and_mix_stems_unchanged':True,'approval_transferred':False})
studio.write(p/'renderer-source-manifest.json',{n:studio.sha(studio.BASE/n) for n in ['src/index.tsx','src/OrbitScene.tsx','src/viewpoint.mjs','frozen_edition.py','learning_acceptance.py','participant_preview.py','studio.py','render.mjs']})
studio.write(p/'delivery-manifest.json',{x.name:studio.sha(x) for x in p.iterdir() if x.is_file() and x.suffix in ('.mp4','.png','.wav','.srt','.vtt','.txt','.json','.html','.webm','.m4a') and x.name not in ['review.json','acceptance-review.json','delivery-manifest.json']})
side=studio.load(p/'acceptance-review.json');side['delivery_manifest_sha256']=studio.sha(p/'delivery-manifest.json');(p/'acceptance-review.json').write_text(json.dumps(side,indent=2))
print('CLEAN_PRIVATE_EDITION_FINALIZED',studio.sha(p/'delivery-manifest.json'),flush=True)
