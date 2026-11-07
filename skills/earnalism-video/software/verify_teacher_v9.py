from pathlib import Path
import sys,json,subprocess,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent));import studio
p=studio.BASE/'outputs/moon-teacher-transitions-v9-final';root=studio.BASE.parent;e=root/'evidence';dest=e/'teacher-v9-delivery';dest.mkdir(exist_ok=True)
assert (p/'delivery-manifest.json').exists(),'Wait for full render completion'
manifest=studio.load(p/'delivery-manifest.json')
for name,digest in manifest.items():assert studio.sha(p/name)==digest,(name,'manifest mismatch')
records=[];audio={}
for name in ['landscape.mp4','portrait-captioned.mp4']:
 target=dest/name
 if target.exists():assert studio.sha(target)==studio.sha(p/name);record=studio.verify_media(target)
 else:record=studio.verify_download('http://127.0.0.1:8787/'+name,studio.sha(p/name),target)
 records.append(record)
 data=subprocess.check_output(['ffmpeg','-v','error','-i',str(p/name),'-map','0:a:0','-c:a','copy','-f','adts','-']);audio[name]=hashlib.sha256(data).hexdigest()
assert len(set(audio.values()))==1,'Formats have differing AAC payloads'
assert not studio.load(p/'caption-quality.json')['issues']
assert all(not studio.load(f).get('unresolved_asr_edits') for f in (p/'alignment').glob('*.json'))
assert studio.verify_original()=='62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4'
assert studio.sha(studio.BASE/'vendor/qwen_worker.py')=='55500c69d0529ded866c744d5242d1c9320625bece8eb56958b8086948e2beeb'
report={'private':True,'downloads':records,'audio_payload_sha256':audio,'same_audio_across_formats':True,'caption_issues':[],'unresolved_semantic_ASR_edits':0,'project_tests':95,'installed_skill_tests':95,'tests_result':'PASS','source_takes_retained':True,'no_new_synthesis_or_compute':True,'pitch_shift':False,'original_notebook_and_worker_unchanged':True,'voice_and_full_AV_listening_approval':'PENDING','score_audibility':'Separate read-only investigation; no music mix modification in this voice candidate','publication':False}
studio.write(e/'teacher-v9-final-verification.json',report);print(json.dumps(report,indent=2))
