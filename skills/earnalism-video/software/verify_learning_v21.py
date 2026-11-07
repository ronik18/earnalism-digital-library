from pathlib import Path
import sys,json,subprocess,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent));import studio
from frozen_edition import verify,FROZEN
p=studio.BASE/'outputs/moon-phases-production-review-v21';old=studio.BASE/'outputs/moon-refined-score-v20';verify(p)
manifest=studio.load(p/'delivery-manifest.json');assert all(studio.sha(p/n)==h for n,h in manifest.items());assert 'acceptance-review.json' not in manifest
assert all(studio.sha(p/n)==studio.sha(old/n) for n in FROZEN)
def audio_hash(path):return hashlib.sha256(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','adts','-'])).hexdigest()
ref=audio_hash(old/'landscape.mp4');records=[];dest=studio.BASE.parent/'evidence/v21-downloads';dest.mkdir(exist_ok=True)
for name in ['landscape.mp4','portrait-captioned.mp4']:
 assert audio_hash(p/name)==ref,'Encoded soundtrack changed during visual-only render'
 target=dest/name
 if target.exists():assert studio.sha(target)==studio.sha(p/name);record=studio.verify_media(target)
 else:record=studio.verify_download('http://127.0.0.1:8793/'+name,studio.sha(p/name),target)
 records.append(record)
try:studio.release_check(p);raise AssertionError('Pending human acceptance must block publication')
except ValueError as ex:blocked=str(ex)
assert studio.verify_original()=='62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4'
r={'edition':p.name,'status':'CLEAN_PRIVATE_PRODUCTION_REVIEW','technical':records,'frozen_stems_and_captions_unchanged':True,'encoded_audio_byte_identical_to_v20':True,'clean_review_overlay':True,'release_block':blocked,'owner_approval':'PENDING','first_time_viewer_results':'NOT RUN','physical_headphone_speaker_listening':'NOT RUN','website_storage_public_delivery':'NOT RUN','published':False};studio.write(studio.BASE.parent/'evidence/v21-verification.json',r);print(json.dumps(r,indent=2))
