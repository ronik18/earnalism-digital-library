"""Make a separate private mix edition while retaining rendered H.264 video streams."""
import pathlib,shutil,json,math,sys
import studio

def remix(source,destination,gain_db=12,score_override=None,scene_gain_db=None):
 source=pathlib.Path(source).resolve();destination=pathlib.Path(destination).resolve()
 if destination.exists():raise FileExistsError(destination)
 for name in ('landscape.mp4','portrait.mp4','portrait-captioned.mp4','delivery-manifest.json'):
  if not (source/name).exists():raise ValueError('Complete the source render first')
 manifest=studio.load(source/'delivery-manifest.json')
 if any(studio.sha(source/name)!=value for name,value in manifest.items()):raise ValueError('Source delivery changed')
 excluded={'viewer-study.json','youtube-landscape.json','youtube-shorts.json','publication-handoff.json','production-journal.jsonl','strict-quality-review.json','mix.wav','mix-provenance.json','delivery-manifest.json','technical.json','rights-audit.json','watch.html','portrait-short.html','verified-downloads','measured-audio-levels.json','score-ducked.wav','remix-provenance.json','review.json','acceptance-review.json','music-balance.json','music-automation.json','score-ducked-before-automation.wav'}
 shutil.copytree(source,destination,ignore=lambda path,names:[n for n in names if n in excluded or n.endswith('.webm') or (n.endswith('.mp4') and n!='landscape-narration-only.mp4')])
 from audience_plan import initialize as initialize_audience
 initialize_audience(destination)
 from audience_plan import validate_generation
 validate_generation(destination)
 from strict_quality import pending as pending_strict
 studio.write(destination/'strict-quality-review.json',pending_strict())
 studio.write(destination/'review.json',{'reviewer':'','delivery_manifest_sha256':None,**{name:False for name in ('factual','rights','voice','audiovisual','technical','delivery')},'note':'Fresh edition; approvals from the source do not transfer.'})
 if (source/'acceptance-review.json').exists() or studio.load(destination/'episode.json').get('private_test') is not True:
  from learning_acceptance import pending
  studio.write(destination/'acceptance-review.json',pending(studio.load(destination/'audience-plan.json') if studio.load(destination/'audience-plan.json').get('study',{}).get('questions') else None,previous=studio.load(source/'acceptance-review.json') if (source/'acceptance-review.json').exists() else None))
 if score_override is not None:
  replacement=pathlib.Path(score_override).resolve();provenance=studio.load(replacement.with_suffix('.provenance.json'))
  if studio.sha(replacement)!=provenance['recording_sha256']:raise ValueError('Replacement score hash mismatch')
  shutil.copy2(replacement,destination/'score.wav');shutil.copy2(replacement.with_suffix('.provenance.json'),destination/'score.provenance.json')
  for name in provenance.get('stems',{}):shutil.copy2(replacement.parent/name,destination/name)
  (destination/'score-audition.m4a').unlink(missing_ok=True)
  studio.run(['ffmpeg','-v','error','-n','-i',destination/'score.wav','-af','loudnorm=I=-20:TP=-2:LRA=8','-c:a','aac','-b:a','192k',destination/'score-audition.m4a'])
  ep=studio.load(destination/'episode.json');ep['music'].update({'kind':'original-acoustic-chamber-composition','palette':('acoustic_v8' if provenance.get('version') in ('moon-score-v9-final-note-balance','moon-score-v10-body-refinement','moon-score-v11-body-refinement') else 'acoustic_v8' if provenance.get('version')=='moon-score-v8-refined-voicing' else 'acoustic_v7' if provenance.get('version')=='moon-score-v7-balanced-arrangement' else 'acoustic_v6' if provenance.get('version')=='moon-score-v6-phrase-arrangement' else 'acoustic_v5' if provenance.get('version')=='moon-score-v5-balanced-acoustic-chamber' else 'acoustic_v4'),'no_third_party_recordings':False,'bed_gain_db':gain_db,'listening_review':'pending'});ep['rights']['score']='Original composition using pinned VCSL CC0 acoustic piano and harp one-shot recordings; hashes and license retained; listening/resemblance review pending.';(destination/'episode.json').write_text(json.dumps(ep,indent=2))
  (destination/'rights-manifest.json').write_text(json.dumps({'assets':ep['rights'],'status':'PRIVATE; updated score requires fresh review','third_party_music':[],'third_party_samples':'Pinned VCSL CC0 acoustic notes'},indent=2))
 ep=studio.load(destination/'episode.json');ep.setdefault('music',{}).update({'bed_gain_db':gain_db,'listening_review':'pending; current mix requires review'});(destination/'episode.json').write_text(json.dumps(ep,indent=2))
 if scene_gain_db is not None:
  ep['music']['scene_gain_db']=scene_gain_db;(destination/'episode.json').write_text(json.dumps(ep,indent=2))
 studio.mix_score(destination,gain_db)
 props=studio.load(destination/'props.json');public=studio.BASE/'public/runs'/destination.name;public.mkdir(parents=True)
 from intro import install
 props['intro'],brand=install(public,studio.BASE/'assets/standard-intro/v1','earnalism-flowing-paired-v1');props['intro']['placement']='end';shutil.copy2(destination/'mix.wav',public/'mix.wav');props['audio']=f'runs/{destination.name}/mix.wav';props['burnCaptions']=False
 (destination/'props.json').write_text(json.dumps(props,indent=2));(destination/'caption-props.json').write_text(json.dumps({**props,'burnCaptions':True},indent=2))
 body_seconds=math.ceil(props['duration']*30)/30;checks=[]
 for name in ('landscape.mp4','portrait.mp4','portrait-captioned.mp4'):
  outro=studio.BASE/'public'/props['intro']['portrait' if name.startswith('portrait') else 'landscape']
  studio.run(['ffmpeg','-v','error','-n','-i',source/name,'-i',destination/'mix.wav','-i',outro,'-filter_complex',f'[1:a]aresample=48000,apad=whole_dur={body_seconds},atrim=duration={body_seconds},asetpts=PTS-STARTPTS[b];[2:a]atrim=duration=3,asetpts=PTS-STARTPTS,aresample=48000[o];[b][o]concat=n=2:v=0:a=1[a]','-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-shortest',destination/name])
  before=studio.run(['ffmpeg','-v','error','-i',source/name,'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).strip();after=studio.run(['ffmpeg','-v','error','-i',destination/name,'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).strip()
  if before!=after:raise ValueError('Video stream changed during audio-only remix')
  checks.append({**studio.verify_media(destination/name),'video_stream_unchanged':True,'source_mp4_sha256':studio.sha(source/name)})
 studio.write(destination/'technical.json',checks);studio.write(destination/'remix-provenance.json',{'source_folder':source.name,'gain_db':gain_db,'rendered_video_streams_unchanged':True,'narration_unchanged':studio.sha(source/'narration.wav')==studio.sha(destination/'narration.wav'),'source_sha256':studio.sha(__file__),'human_av_review':'PENDING'})
 studio.create_web_preview(destination);studio.draft_watch(destination)
 from rights_audit import audit
 studio.write(destination/'rights-audit.json',audit(destination));(destination/'renderer-source-manifest.json').write_text(json.dumps({name:studio.sha(studio.BASE/name) for name in ['src/index.tsx','src/OrbitScene.tsx','src/viewpoint.mjs','src/lunar-geometry.mjs','score.py','acoustic_score.py','balanced_score.py','final_chamber_score.py','render.mjs','studio.py','remix.py']},indent=2))
 from audience_plan import write_metadata
 write_metadata(destination)
 studio.write(destination/'delivery-manifest.json',{p.name:studio.sha(p) for p in destination.iterdir() if p.is_file() and p.suffix in ('.mp4','.png','.wav','.srt','.vtt','.txt','.json','.html','.webm','.m4a') and p.name not in ('review.json','acceptance-review.json','strict-quality-review.json','delivery-manifest.json','publication-handoff.json','viewer-study.json')})
 from audience_plan import reset_handoff
 reset_handoff(destination)
 from strict_quality import reset as reset_strict,capture as capture_strict
 reset_strict(destination)
 capture_strict(destination)
 if (destination/'acceptance-review.json').exists():
  side=pending(studio.load(destination/'audience-plan.json') if studio.load(destination/'audience-plan.json').get('study',{}).get('questions') else None,previous=studio.load(source/'acceptance-review.json') if (source/'acceptance-review.json').exists() else None);side['delivery_manifest_sha256']=studio.sha(destination/'delivery-manifest.json');(destination/'acceptance-review.json').write_text(json.dumps(side,indent=2))
 return destination
if __name__=='__main__':print(remix(sys.argv[1],sys.argv[2],float(sys.argv[3]) if len(sys.argv)>3 else 12,sys.argv[4] if len(sys.argv)>4 else None))
