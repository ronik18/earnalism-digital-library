"""Isolated Earnalism video pipeline. Standard library controller + FFmpeg/Remotion."""
import argparse, hashlib, html, json, pathlib, re, shutil, subprocess, sys, uuid, zipfile, urllib.request
BASE=pathlib.Path(__file__).resolve().parent
ORIGINAL_SHA='62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4'
VIDEO_DISCLOSURE='Produced by Earnalism with AI-generated narration and illustrative animation. Sources below.'
PLAYER_DISCLOSURE='AI-generated narration · Illustrative animation'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def write(p,x):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False)
def run(args):return subprocess.run([str(a) for a in args],check=True,capture_output=True,text=True,cwd=BASE).stdout
def duration(p):return float(json.loads(run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',p]))['format']['duration'])
def verify_original():
 p=BASE.parent/'Earnalism_English_Audiobook_Pipeline_Qwew&Ace.ipynb'
 if sha(p)!=ORIGINAL_SHA:raise ValueError('Original audiobook checksum changed')
 return ORIGINAL_SHA
def validate(ep):
 if not ep.get('topic') or not ep.get('scenes') or not ep.get('sources'):raise ValueError('Topic, storyboard and research required')
 ids={s['id'] for s in ep['sources']}
 for s in ep['scenes']:
  if any(not text.strip() or len(text.split())>65 or len(text)>520 for text in (s['text'],s.get('tts_text',s['text']))):raise ValueError('Use complete sentence chunks <=65 words / 520 characters')
  if not set(s['source_ids'])<=ids:raise ValueError('Unknown claim source')
  if s['diagram'] not in ('question','sunlight','orbit','phases','eclipse','cycle','callback'):raise ValueError('Implement and review a topic-specific renderer before proceeding')
 if 'moon' not in ep['topic'].lower():raise ValueError('This renderer explains lunar geometry only; add a tested topic-specific renderer')
 return ep
def normalize_episode(ep,policy=None):
 ep=json.loads(json.dumps(ep))
 if (policy if policy is not None else load(BASE/'config/defaults.json')).get('spoken_brand_name') is False:
  for scene in ep['scenes']:
   scene['text']=omit_spoken_brand(scene['text'])
   if scene.get('tts_text'):scene['tts_text']=omit_spoken_brand(scene['tts_text'])
   scene.pop('narration_instruction',None)
 return ep

def prepare(ep_path):
 verify_original();ep=validate(normalize_episode(load(ep_path)))
 folder=BASE/'outputs'/f"{ep['id']}-{uuid.uuid4().hex[:8]}";folder.mkdir(parents=True)
 write(folder/'episode.json',ep)
 (folder/'transcript.txt').write_text('\n\n'.join(s['text'] for s in ep['scenes']))
 write(folder/'review.json',{'binding':sha(folder/'episode.json'),'factual':False,'rights':False,'voice':False,'audiovisual':False,'technical':False,'delivery':False,'reviewer':'','note':'Review after actual narration and render; approvals must bind current delivery manifest.'})
 from strict_quality import pending as pending_strict
 write(folder/'strict-quality-review.json',pending_strict())
 write(folder/'youtube.json',youtube_metadata(ep))
 from audience_plan import initialize as initialize_audience
 initialize_audience(folder)
 write(folder/'sources.json',ep['sources']);return folder

def youtube_metadata(ep):
 # Editorial guidance only; these fields do not set YouTube Studio controls or grant approval.
 context=ep.get('diagram_context','Illustrative diagrams; model assumptions and scale limitations are stated in the source notes.')
 return {'title':ep['topic']+' | Earnalism','description':'Earnalism — See differently.\n\n'+VIDEO_DISCLOSURE+'\n\nDiagram note: '+context+'\n\nSources:\n'+'\n'.join(s['url'] for s in ep['sources']),'tags':ep.get('tags',[ep['topic'],'Earnalism']),'privacyStatus':'private','language':'en','upload_automatically':False,'synthetic_narration':True,'ai_disclosure_recommendation':'Select Yes in YouTube Studio AI use for this realistic synthetic narrator; verify against the final video and current policy at manual upload. Description text does not set the platform control.','manual_upload_review':['Confirm AI use setting for the final audio and visuals.','Determine made-for-kids status from the actual intended audience.','Declare any sponsorship or affiliate relationship and include required credits.','Obtain final artifact-bound publication approval before uploading.']}

def omit_spoken_brand(text):
 return re.sub(r"\s+", " ", re.sub(r"\b(?:Earnalism|Earn Al-ism)\b[.,:;!?]?", "", text, flags=re.I)).strip()

def speech_text(scene,policy):
 text=scene.get('tts_text',scene['text'])
 if policy.get('spoken_brand_name') is False:text=omit_spoken_brand(text)
 if not scene.get('tts_text'):
  for name,rule in policy.get('pronunciation',{}).items():
   if rule.get('tts_form'):text=re.sub(r'\b'+re.escape(name)+r'\b',rule['tts_form'],text,flags=re.I)
 if len(text.split())>65 or len(text)>520:raise ValueError('Phonetic speech text exceeds 65 words / 520 characters; resegment')
 return text

def narration_instruction(scene,policy):
 profile=scene.get('voice_profile',policy.get('default_voice_profile'))
 if profile:
  if profile not in policy.get('voice_profiles',{}):raise ValueError('Unknown voice profile')
  return policy['voice_profiles'][profile]['instruction']
 if policy.get('spoken_brand_name') is False:return policy['instruction']
 if scene.get('narration_instruction'):return scene['narration_instruction']
 value=policy['instruction']
 for name,rule in policy.get('pronunciation',{}).items():
  if name.lower() in scene['text'].lower():value+=' '+rule['instruction']
 return value

def make_job(folder,model):
 folder=pathlib.Path(folder).resolve()
 from audience_plan import validate_generation
 validate_generation(folder)
 ep=load(folder/'episode.json');raw=folder/'raw';raw.mkdir(exist_ok=True)
 policy=load(BASE/'config/defaults.json');segments=[]
 for s in ep['scenes']:
  segments.append({'segment_id':s['id'],'text':speech_text(s,policy),'instruct':narration_instruction(s,policy),'speaker':'Ryan','seed':s.get('narration_seed',20261026),'cache_key':hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest(),'output_path':str(raw/(s['id']+'.wav'))})
 profiles={s.get('voice_profile',policy.get('default_voice_profile')) for s in ep['scenes']}
 generation=policy.get('generation',{}).copy()
 if len(profiles)==1:generation.update(policy.get('voice_profiles',{}).get(next(iter(profiles)),{}).get('generation',{}))
 return {**model,'generation':generation,'slug':ep['id'],'journal_path':str(folder/'logs/qwen.jsonl'),'report_path':str(folder/'logs/qwen-report.json'),'stop_flag_path':str(folder/'STOP'),'max_attempts':3,'device':'cuda:0','dtype':'auto','attention':'eager','segments':segments}

def timestamp(t,comma=False):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}{"," if comma else "."}{ms%1000:03}'
def captions(cues,folder):
 last=0
 for c in cues:
  if not (last<=c['start']<c['end']) or not c['text'].strip():raise ValueError('Invalid caption timing')
  last=c['end']
 (folder/'captions.srt').write_text('\n\n'.join(f'{i+1}\n{timestamp(c["start"],True)} --> {timestamp(c["end"],True)}\n{c["text"]}' for i,c in enumerate(cues))+'\n')
 (folder/'captions.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f'{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}' for c in cues)+'\n')
def mix_score(folder,gain_db=12):
 folder=pathlib.Path(folder).resolve()
 if not -6<=gain_db<=18:raise ValueError('Review score gain outside bounded range')
 score=load(folder/'score.provenance.json') if (folder/'score.provenance.json').exists() else {}
 acoustic=score.get('kind')=='original acoustic chamber composition'
 duck={'threshold':.06,'ratio':2.5,'attack':45,'release':750} if acoustic else {'threshold':.015,'ratio':6,'attack':20,'release':600}
 seconds=duration(folder/'narration.wav')
 filters=f'[0:a]volume={gain_db}dB,apad=pad_dur=1[score];[1:a]apad=pad_dur=1[voice];[score][voice]sidechaincompress=threshold={duck["threshold"]}:ratio={duck["ratio"]}:attack={duck["attack"]}:release={duck["release"]},atrim=duration={seconds}[bed]'
 run(['ffmpeg','-v','error','-n','-i',folder/'score.wav','-i',folder/'narration.wav','-filter_complex',filters,'-map','[bed]','-ar','48000',folder/'score-ducked.wav'])
 if load(BASE/'config/defaults.json').get('music',{}).get('selective_automation',True):
  from music_automation import apply
  apply(folder)
 run(['ffmpeg','-v','error','-n','-i',folder/'score-ducked.wav','-i',folder/'narration.wav','-filter_complex','[0:a][1:a]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[out]','-map','[out]','-ar','48000',folder/'mix.wav'])
 from audio_balance import audit
 balance=audit(folder);write(folder/'music-balance.json',balance)
 if balance['issues']:
  if not load(folder/'episode.json').get('private_test'):raise ValueError('Music balance needs review: '+str(balance['issues']))
  balance['private_review_only']=True; (folder/'music-balance.json').write_text(json.dumps(balance,indent=2))
 write(folder/'mix-provenance.json',{'bed_gain_db':gain_db,'speech_ducking':duck,'post_ducked_stem_sha256':sha(folder/'score-ducked.wav'),'narration_sha256':sha(folder/'narration.wav'),'score_sha256':sha(folder/'score.wav'),'mix_sha256':sha(folder/'mix.wav'),'source_sha256':sha(BASE/'studio.py'),'human_listening_review':'PENDING'})

def assemble(folder):
 folder=pathlib.Path(folder).resolve();ep=load(folder/'episode.json');scenes=[];cues=[];offset=0;audio=[];asr_reviews=[];pace_reports=[];speech_intervals=[]
 for s in ep['scenes']:
  wav=folder/'raw'/(s['id']+'.wav')
  from audio_derivation import check_unit
  meta=check_unit(folder,s['id'])
  d=duration(wav);audio.append(wav)
  # Actual audio chunk boundaries, not fabricated word timestamps. Shorter ASR cues replace these below.
  asr=load(folder/'alignment'/(s['id']+'.json'))
  if asr['audio_sha256']!=sha(wav):raise ValueError('Stale ASR')
  if asr.get('unresolved_asr_edits'):raise ValueError('Unresolved ASR edits require audio-bound review')
  from asr_review import require_script_match
  require_script_match(asr,s['text'])
  from pace_review import review as review_pace
  pace_reports.append({'scene':s['id'],'audio_sha256':sha(wav),**review_pace(asr,wav,s['text'],load(BASE/'config/defaults.json').get('pace_review',{}))})
  asr_reviews.append({'scene':s['id'],'similarity':asr['similarity'],'edits':asr.get('unresolved_asr_edits',[]),'recognized':asr['recognized'],'expected':s['text'],'human_listening_required':True,'resolution_status':asr.get('resolution_status'),'resolutions':asr.get('resolution',{})})
  speech_intervals.extend((offset+w['start'],offset+w['end']) for w in asr['word_times'])
  from score import anchors
  scenes.append({**s,'start':offset,'end':offset+d,'anchors':anchors(s,asr.get('word_times',[]),offset)})
  from caption_layout import compose as compose_captions, punctuate
  for c in compose_captions(punctuate(asr.get('display_word_times',asr['word_times']),s['text'])):
   if c['start']<0 or c['end']>d+.1:raise ValueError('ASR cue outside audio')
   cues.append({**c,'start':c['start']+offset,'end':c['end']+offset})
  offset+=d
 concat=folder/'concat.txt';concat.write_text('\n'.join("file '"+str(p).replace("'","'\\''")+"'" for p in audio))
 voice_filter='loudnorm=I=-16:TP=-1.5:LRA=11'
 if ep.get('narration_mastering')=='mature_teacher_v8':
  voice_filter='highpass=f=65,equalizer=f=140:t=q:w=0.8:g=1.2,acompressor=threshold=0.12:ratio=1.5:attack=25:release=180,'+voice_filter
 run(['ffmpeg','-v','error','-n','-f','concat','-safe','0','-i',concat,'-af',voice_filter,'-ar','48000',folder/'narration.wav'])
 write(folder/'narration-mastering.json',{'profile':ep.get('narration_mastering','standard'),'filters':voice_filter,'pitch_shift':False,'source_scenes':{s['id']:sha(folder/'raw'/(s['id']+'.wav')) for s in ep['scenes']},'output_sha256':sha(folder/'narration.wav'),'human_voice_tone_and_naturalness_review':'PENDING'})
 if abs(duration(folder/'narration.wav')-offset)>.05:raise ValueError('Concatenated narration duration mismatch; check input audio codecs')
 write(folder/'asr-review.json',asr_reviews)
 from pace_review import compare_scene_rates
 write(folder/'pace-review.json',{'scenes':pace_reports,'consistency':compare_scene_rates(pace_reports,load(BASE/'config/defaults.json').get('pace_review',{}).get('max_scene_rate_deviation',.12)),'human_listening_required':True})
 write(folder/'rights-manifest.json',{'assets':ep.get('rights',{}),'status':'PRIVATE; publication rights and resemblance review pending','third_party_images':[],'third_party_music':[],'voice':'Pinned Qwen stock Ryan; no clone input'})
 props={'scenes':scenes,'captions':cues,'duration':duration(folder/'narration.wav'),'preview':False,'burnCaptions':False}
 soundtrack='narration.wav'
 if ep.get('music',load(BASE/'config/defaults.json').get('music',{})).get('enabled'):
  from score import compose
  quiet=[(s['start'],min(s['end'],s['start']+(5 if s['diagram']=='eclipse' else 3))) for s in scenes if s['diagram'] in ('question','eclipse','callback')]
  compose(folder/'score.wav',props['duration'],quiet,scenes=scenes,palette=ep.get('music',{}).get('palette',load(BASE/'config/defaults.json').get('music',{}).get('palette','legacy')),speech_intervals=speech_intervals)
  mix_score(folder,ep.get('music',{}).get('bed_gain_db',load(BASE/'config/defaults.json').get('music',{}).get('bed_gain_db',12)))
  run(['ffmpeg','-v','error','-n','-i',folder/'score.wav','-af','loudnorm=I=-20:TP=-2:LRA=8','-c:a','aac','-b:a','192k',folder/'score-audition.m4a'])
  soundtrack='mix.wav'
 public=BASE/'public/runs'/folder.name;public.mkdir(parents=True)
 intro_settings=ep.get('intro',load(BASE/'config/defaults.json').get('intro',{}))
 intro_seconds=0
 if intro_settings.get('enabled'):
  from intro import install
  props['intro'],intro_manifest=install(public,BASE/intro_settings.get('asset_root','assets/standard-intro/v1'),intro_settings.get('version'))
  props['intro']['placement']='end';intro_seconds=props['intro']['seconds'];write(folder/'intro-manifest.json',intro_manifest)
 from intro import shift_cues
 captions(cues,folder)
 from caption_layout import quality as caption_quality
 write(folder/'caption-quality.json',{'issues':caption_quality(cues),'count':len(cues),'narration_sha256':sha(folder/'narration.wav'),'word_times_preserved':True})
 write(folder/'timeline.json',{'intro_seconds':0,'outro_seconds':intro_seconds,'narration_seconds':props['duration'],'total_seconds':props['duration']+intro_seconds,'brand_placement':'end','brand_start_seconds':props['duration'],'captions_offset_seconds':0,'scenes':[dict(s,start=s['start'],end=s['end'],anchors=[dict(a,time=a['time']) for a in s.get('anchors',[])]) for s in scenes]})
 shutil.copy2(folder/soundtrack,public/soundtrack);props['audio']=f'runs/{folder.name}/{soundtrack}';write(folder/'props.json',props);return props

def preview(folder):
 folder=pathlib.Path(folder).resolve();ep=load(folder/'episode.json');s=ep['scenes'][0];write(folder/'preview-props.json',{'scenes':[{**s,'start':0,'end':4}],'duration':4,'preview':True})
 run(['node',BASE/'render.mjs',folder/'preview-props.json',folder/'visual-test.mp4','Portrait'])
def _verify_media_once(p,expect_audio=True):
 path=pathlib.Path(p)
 def fingerprint():
  q=path.stat();return q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_ctime_ns
 before=fingerprint()
 probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',p]));streams=probe['streams'];v=next(s for s in streams if s['codec_type']=='video')
 if v['codec_name']!='h264' or v['pix_fmt']!='yuv420p':raise ValueError('Unsupported video encoding')
 if expect_audio:
  if not any(s['codec_type']=='audio' for s in streams):raise ValueError('Narration audio missing')
  # One checked decode covers BOTH streams and audio statistics.
  stats=subprocess.run(['ffmpeg','-hide_banner','-xerror','-i',str(p),'-map','0:v:0','-map','0:a:0','-af','volumedetect','-f','null','-'],capture_output=True,text=True,check=True).stderr
  m=re.search(r'mean_volume: ([-\w.]+) dB',stats)
  if not m or float(m[1]) < -55:raise ValueError('Silent or inaudible soundtrack')
  peak=re.search(r'max_volume: ([-\w.]+) dB',stats)
  if not peak or float(peak[1])>-.3:raise ValueError('Encoded audio peak too high')
  a=next(s for s in streams if s['codec_type']=='audio')
  if a['codec_name']!='aac':raise ValueError('Expected AAC audio')
  if abs(float(a.get('duration',probe['format']['duration']))-float(v.get('duration',probe['format']['duration'])))>.15:raise ValueError('Audio/video duration mismatch')
 else:run(['ffmpeg','-v','error','-xerror','-i',p,'-map','0:v:0','-f','null','-'])
 digest=sha(p)
 if fingerprint()!=before:raise ValueError('Media changed during verification')
 return {'file':pathlib.Path(p).name,'sha256':digest,'width':v['width'],'height':v['height'],'seconds':float(probe['format']['duration']),'audio_present':any(s['codec_type']=='audio' for s in streams),'decode':'PASS'}
def verify_media(p,expect_audio=True):
 # Filesystem indexing can alter metadata without changing media bytes. Retain
 # the identity guard, discard that attempt and allow one fully checked retry
 # only when the exact content digest is still the expected one.
 expected=sha(p);retried=False
 try:record=_verify_media_once(p,expect_audio)
 except ValueError as error:
  if str(error)!='Media changed during verification' or sha(p)!=expected:raise
  retried=True;record=_verify_media_once(p,expect_audio)
 if record['sha256']!=expected:raise ValueError('Media content changed during verification')
 if retried:record['metadata_only_retry']=True
 return record

def render(folder,frozen=False,expected_narration_sha256=None):
 folder=pathlib.Path(folder).resolve()
 from expectations import audit as audit_expectations
 audit_expectations(BASE)
 from audience_plan import initialize as initialize_audience
 initialize_audience(folder)
 from audience_plan import referenced_assets
 referenced_assets(folder)
 if frozen:
  from frozen_edition import verify
  p=verify(folder)
 else:p=assemble(folder)
 if expected_narration_sha256 is not None and sha(folder/'narration.wav')!=expected_narration_sha256:raise ValueError('Narration changed during presentation-only render')
 from audience_plan import validate_story_timing
 validate_story_timing(folder)
 records=[]
 for fmt in ('Landscape','Portrait'):
  out=folder/(fmt.lower()+'.mp4');run(['node',BASE/'render.mjs',folder/'props.json',out,fmt])
  if frozen:
   from frozen_edition import copy_frozen_soundtrack
   copy_frozen_soundtrack(folder,out)
  records.append(verify_media(out))
 p['burnCaptions']=True;write(folder/'caption-props.json',p);out=folder/'portrait-captioned.mp4';run(['node',BASE/'render.mjs',folder/'caption-props.json',out,'Portrait'])
 if frozen:
  from frozen_edition import copy_frozen_soundtrack
  copy_frozen_soundtrack(folder,out)
 records.append(verify_media(out));write(folder/'technical.json',records)
 if (folder/'mix.wav').exists():
  dry=folder/'landscape-narration-only.mp4'
  dry_audio=folder/'narration.wav'
  if p.get('intro'):
   dry_audio=folder/'intro-and-dry-narration.wav'
   run(['ffmpeg','-v','error','-n','-i',BASE/'public'/p['intro']['landscape'],'-i',folder/'narration.wav','-filter_complex','[0:a]atrim=duration=3,asetpts=PTS-STARTPTS,aresample=48000[a];[1:a]aresample=48000[b];[b][a]concat=n=2:v=0:a=1[out]','-map','[out]',dry_audio])
  run(['ffmpeg','-v','error','-n','-i',folder/'landscape.mp4','-i',dry_audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-shortest',dry])
  verify_media(dry)
 create_web_preview(folder)
 draft_watch(folder)
 if load(folder/'episode.json').get('requires_learning_acceptance'):
  from participant_preview import make
  make(folder)
 if (folder/'score.provenance.json').exists() and (BASE/'rights/evidence.json').exists():
  from rights_audit import audit
  write(folder/'rights-audit.json',audit(folder,BASE))
 from audience_plan import write_metadata
 write_metadata(folder)
 write(folder/'delivery-manifest.json',{x.name:sha(x) for x in folder.iterdir() if x.is_file() and x.suffix in ('.mp4','.png','.wav','.srt','.vtt','.txt','.json','.html','.webm','.m4a') and x.name not in ('review.json','acceptance-review.json','strict-quality-review.json','delivery-manifest.json','publication-handoff.json','viewer-study.json')})
 from audience_plan import reset_handoff
 reset_handoff(folder)
 if load(folder/'episode.json').get('requires_learning_acceptance'):
  from learning_acceptance import pending
  plan=load(folder/'audience-plan.json');old=load(folder/'acceptance-review.json') if (folder/'acceptance-review.json').exists() else None
  side=pending(plan if plan.get('study',{}).get('questions') else None,previous=old)
  side['delivery_manifest_sha256']=sha(folder/'delivery-manifest.json');(folder/'acceptance-review.json').write_text(json.dumps(side,indent=2))
 from strict_quality import reset as reset_strict,capture as capture_strict
 reset_strict(folder)
 capture_strict(folder)

def create_faststart_previews(folder):
 folder=pathlib.Path(folder)
 for source,target in [('landscape.mp4','landscape-preview.mp4'),('portrait-captioned.mp4','portrait-preview.mp4')]:
  run(['ffmpeg','-v','error','-n','-i',folder/source,'-map','0:v:0','-map','0:a:0','-c','copy','-movflags','+faststart',folder/target])

def create_web_preview(folder):
 folder=pathlib.Path(folder)
 create_faststart_previews(folder)
 for source,target in [('landscape.mp4','landscape-preview.webm'),('portrait-captioned.mp4','portrait-preview.webm')]:
  output=folder/target
  if output.exists():raise FileExistsError(output)
  run(['ffmpeg','-v','error','-n','-i',folder/source,'-c:v','libvpx-vp9','-b:v','0','-crf','28','-deadline','realtime','-cpu-used','6','-row-mt','1','-c:a','libopus','-b:a','96k',output])
  probe=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',output]))
  if {s['codec_name'] for s in probe['streams']}!={'vp9','opus'}:raise ValueError('Preview codecs mismatch')
  run(['ffmpeg','-v','error','-i',output,'-f','null','-'])

def draft_watch(folder):
 folder=pathlib.Path(folder).resolve();ep=load(folder/'episode.json')
 if not (folder/'landscape.mp4').exists():raise ValueError('Render narration first')
 page=(BASE/'watch-template.html').read_text()
 page=page.replace('{{DISCLOSURE}}',html.escape(PLAYER_DISCLOSURE))
 page=page.replace('{{DIAGRAM_CONTEXT}}',html.escape(ep.get('diagram_context','Illustrative diagrams; see the stated model assumptions in the source notes.')))
 plan=load(folder/'audience-plan.json') if (folder/'audience-plan.json').exists() else ep.get('audience_plan',{})
 answers={s.get('id'):s.get('text','') for s in ep['scenes']}
 checks=''.join('<p><strong>'+html.escape(q['prompt'])+'</strong></p><p>'+html.escape(answers.get(q.get('answer_scene'),''))+'</p>' for q in plan.get('study',{}).get('questions',[]))
 page=page.replace('{{UNDERSTANDING_CHECKS}}',checks)
 description=ep.get('visual_description')
 if not description and ep['topic']=='Why does the Moon have phases?':
  description={'title':'Why is a half-lit Moon called first quarter?','text':'First quarter means the Moon is one quarter of the way through its phase cycle, measured from new Moon. Half of the disk we see is illuminated. The fraction of the cycle and the fraction of the visible disk describe different things.'}
 accessible='<section aria-labelledby="visual-heading"><h2 id="visual-heading">'+html.escape(description['title'])+'</h2><p>'+html.escape(description['text'])+'</p><p class="note">Accessible visual explanation. The verbatim narration is available below.</p></section>' if description else ''
 page=page.replace('{{VISUAL_DESCRIPTION}}',accessible)
 from caption_preview import label_timeline
 props=load(folder/'props.json') if (folder/'props.json').exists() else {'scenes':[]}
 profile=ep.get('label_profile','moon-phases-v1' if ep['topic']=='Why does the Moon have phases?' else 'none')
 page=page.replace('{{LABEL_TIMELINE}}',json.dumps(label_timeline(props,profile=profile),ensure_ascii=False).replace('<','\\u003c'))
 if not (folder/'score-audition.m4a').exists():page=page.replace('<a href="score-audition.m4a">Instrumental alone (amplified for review)</a>','')
 page=page.replace('{{TOPIC}}',html.escape(ep['topic'])).replace('{{TRANSCRIPT}}',' '.join(html.escape(s['text']) for s in ep['scenes']))
 page=page.replace('{{SOURCES}}',''.join('<p><a href="'+html.escape(s['url'],quote=True)+'">'+html.escape(s['publisher'])+'</a></p>' for s in ep['sources']))
 reviews=load(folder/'asr-review.json') if (folder/'asr-review.json').exists() else []
 review_html=''.join('<p><b>'+html.escape(r['scene'])+'</b>: '+html.escape(str(r['similarity']))+' raw similarity; '+html.escape(str(r['edits']))+'</p>' for r in reviews if r['edits'] or (r['similarity']<1 and not r.get('resolution_status')))
 review_html+=''.join('<p><b>'+html.escape(r['scene'])+'</b>: '+html.escape(str(r['resolution_status']))+' — '+html.escape(str(r['resolutions']))+'</p>' for r in reviews if r.get('resolution_status'))
 page=page.replace('{{ASR_REVIEW}}',review_html or '<p>No automated text differences detected. Complete listening still required.</p>')
 (folder/'watch.html').write_text(page)
 portrait=page.replace('max-width:100%;aspect-ratio:16/9','max-width:min(480px,42vh);aspect-ratio:9/16').replace('width="1920" height="1080" poster="landscape.png"','width="1080" height="1920" poster="portrait-captioned.png"').replace('landscape-preview.mp4?v=7','portrait-preview.mp4?v=7').replace('landscape-preview.webm?v=4','portrait-preview.webm?v=4').replace('landscape.mp4?v=4','portrait-captioned.mp4?v=4')
 portrait=portrait.replace('<main>', '<body data-portrait><main>').replace('<track kind="captions" src="captions.vtt" srclang="en" label="English" default>', '').replace('<button id="toggle-captions" type="button" aria-pressed="true">Captions: on</button>', '<button id="toggle-captions" type="button" aria-pressed="true" disabled>Captions: burned in</button>')
 (folder/'portrait-short.html').write_text(portrait)

def release_check(folder):
 folder=pathlib.Path(folder).resolve()
 if folder.is_file():
  if load(folder).get('schema')=='earnalism.thermal-publication-profile.v1':
   from thermal_touch.release import check
  else:
   from refraction_release import check
  return check(folder,BASE.parent)
 if (folder/'delivery-manifest.json').is_file() and load(folder/'delivery-manifest.json').get('schema')=='earnalism.condensation-private-kit.v1':
  from condensation.release import check_private
  return check_private(folder,BASE.parent)
 if (folder/'delivery-manifest.json').is_file() and load(folder/'delivery-manifest.json').get('schema')=='earnalism.sky-colour-private-kit.v1':
  from sky_colour.release import check_private
  return check_private(folder,BASE.parent)
 if (folder/'delivery-manifest.json').is_file() and load(folder/'delivery-manifest.json').get('schema')=='earnalism.rainbow-private-kit.v1':
  from rainbow.release import check_private
  return check_private(folder,BASE.parent)
 if (folder/'delivery-manifest.json').is_file() and load(folder/'delivery-manifest.json').get('schema')=='earnalism.diwali-private-kit.v1':
  from diwali_v5.release import check_private
  return check_private(folder,BASE.parent)
 ep=load(folder/'episode.json')
 if ep['private_test']:raise ValueError('Test fixtures can never publish')
 r=load(folder/'review.json')
 manifest=load(folder/'delivery-manifest.json')
 if any(sha(folder/k)!=v for k,v in manifest.items()):raise ValueError('Delivery changed')
 from learning_acceptance import validate_release_findings
 acceptance=load(folder/'acceptance-review.json') if (folder/'acceptance-review.json').exists() else None
 validate_release_findings(acceptance,sha(folder/'delivery-manifest.json'),r,folder)
 if ep.get('requires_independent_learning_study') is True:
  from learning_acceptance import validate as validate_learning
  if acceptance is None:raise ValueError('Explicitly required independent learning study missing')
  if acceptance.get('schema')!='earnalism.learning-acceptance.v2':raise ValueError('Explicit independent study needs current topic-bound v2 evidence')
  validate_learning(acceptance,sha(folder/'delivery-manifest.json'),plan=load(folder/'audience-plan.json'))
 if r.get('delivery_manifest_sha256')!=sha(folder/'delivery-manifest.json') or not r.get('reviewer') or not all(r.get(k) is True for k in ('factual','rights','voice','audiovisual','technical','delivery')):raise ValueError('Current factual/rights/voice/AV/technical/delivery human review required')
 from caption_layout import quality
 if not load(folder/'props.json').get('captions') or quality(load(folder/'props.json')['captions']):raise ValueError('Caption readability failed')
 required={'landscape.mp4','portrait.mp4','portrait-captioned.mp4','captions.srt','captions.vtt','props.json','asr-review.json','pace-review.json','technical.json','transcript.txt','sources.json','youtube.json','landscape.png','portrait.png'}
 if not required.issubset(manifest):raise ValueError('Incomplete delivery manifest')
 if ep.get('music',{}).get('enabled') or (folder/'score.wav').exists():
  if 'music-balance.json' not in manifest:raise ValueError('Current post-ducking music review required')
  balance=load(folder/'music-balance.json')
  if 'music-automation.json' not in manifest or load(folder/'music-automation.json').get('transition_check',{}).get('issues') or load(folder/'music-automation.json').get('transition_check',{}).get('maximum_phrase_gain_rate_db_per_second',999)>1.001:raise ValueError('Current slow music transition evidence required')
  if balance.get('issues') or any(balance.get('stem_sha256',{}).get(name)!=sha(folder/name) for name in ['narration.wav','score-ducked.wav']):raise ValueError('Stale or failed music balance evidence')
 if any(v.get('edits') for v in load(folder/'asr-review.json')):raise ValueError('Unresolved ASR edits')
 pace=load(folder/'pace-review.json')
 if any(v.get('flags') for v in pace['scenes']) or not pace['consistency']['consistent']:
  if r.get('pace_review_sha256')!=sha(folder/'pace-review.json'):raise ValueError('Flagged pacing requires current audio-bound listening review')
 if 'rights-audit.json' not in manifest or load(folder/'rights-audit.json').get('status')!='COMPLETE':raise ValueError('Completed rights audit must bind this delivery')
 props=load(folder/'props.json')
 from audio_derivation import check_unit
 for scene in ep['scenes']:
  check_unit(folder,scene['id'])
  record=load(folder/'alignment'/(scene['id']+'.json'))
  pace_record=next((v for v in pace['scenes'] if v['scene']==scene['id']),{})
  if pace_record.get('audio_sha256')!=sha(folder/'raw'/(scene['id']+'.wav')):raise ValueError('Stale pacing evidence')
  if record.get('audio_sha256')!=sha(folder/'raw'/(scene['id']+'.wav')) or record.get('unresolved_asr_edits'):raise ValueError('Stale or unresolved source alignment')
  from asr_review import require_script_match
  require_script_match(record,scene['text'])
 records={v['file']:v for v in load(folder/'technical.json')}
 for name in ('landscape.mp4','portrait.mp4','portrait-captioned.mp4'):
  if name not in records or records[name].get('sha256')!=sha(folder/name) or records[name].get('decode')!='PASS':raise ValueError('Stale technical evidence')
 if not props.get('intro') or props['intro'].get('placement')!='end':raise ValueError('Published videos require the standard brand outro')
 if any(re.search(r'\b(?:Earnalism|Earn Al-ism)\b',scene['text'],re.I) for scene in ep['scenes']):raise ValueError('Remove spoken brand name before publication')
 from strict_quality import validate as validate_strict
 validate_strict(folder)
 from audience_plan import validate_package,PLAN,PACKAGE
 if not {PLAN,PACKAGE,'youtube-landscape.json','youtube-shorts.json'}.issubset(manifest):raise ValueError('Current audience and packaging delivery required')
 validate_package(folder)
 return 'READY_FOR_WEBSITE_ADAPTER_REVIEW'
def main():
 a=argparse.ArgumentParser();a.add_argument('command',choices=['prepare','preview','render','render-frozen','check','checksum','import','download','verify']);a.add_argument('path',nargs='?');a.add_argument('destination',nargs='?');a.add_argument('--sha256');x=a.parse_args()
 if x.command=='checksum':print(verify_original())
 elif x.command=='prepare':print(prepare(x.path))
 elif x.command=='preview':preview(x.path)
 elif x.command=='render':render(x.path)
 elif x.command=='render-frozen':render(x.path,frozen=True)
 elif x.command=='check':
  result=release_check(x.path)
  print(json.dumps(result,indent=2,ensure_ascii=False) if isinstance(result,dict) else result)
 elif x.command=='verify':print(json.dumps(verify_media(x.path),indent=2))
 elif x.command=='import':
  if not x.destination:a.error('import requires archive and new destination')
  print(import_narration(x.path,x.destination))
 elif x.command=='download':
  if not x.destination or not x.sha256:a.error('download requires URL, new destination and --sha256')
  print(json.dumps(verify_download(x.path,x.sha256,x.destination),indent=2))

def verify_download(url,expected_sha,destination):
 """Download, hash and decode an actual artifact. No invented delivery URLs."""
 destination=pathlib.Path(destination)
 if destination.exists():raise FileExistsError(destination)
 with urllib.request.urlopen(url,timeout=60) as response, destination.open('xb') as out:shutil.copyfileobj(response,out)
 if sha(destination)!=expected_sha:raise ValueError('Downloaded SHA256 mismatch; artifact quarantined at '+str(destination))
 return verify_media(destination)

def import_narration(archive,destination):
 """Reject traversal, symlinks, duplicate entries, unknown and modified files."""
 destination=pathlib.Path(destination)
 if destination.exists():raise FileExistsError(destination)
 with zipfile.ZipFile(archive) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or sum(i.file_size for i in z.infolist())>512*1024*1024:raise ValueError('Invalid archive size/duplicates')
  for info in z.infolist():
   p=pathlib.PurePosixPath(info.filename)
   if p.is_absolute() or '..' in p.parts or '\\' in info.filename or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe archive')
  manifest=json.loads(z.read('transfer-manifest.json'))
  if set(names)!=set(manifest)|{'transfer-manifest.json'}:raise ValueError('Unmanifested transfer')
  for name,digest in manifest.items():
   if hashlib.sha256(z.read(name)).hexdigest()!=digest:raise ValueError('Transfer hash mismatch')
  destination.mkdir(parents=True)
  z.extractall(destination)
 validate(load(destination/'episode.json'));return destination

if __name__=="__main__":main()
