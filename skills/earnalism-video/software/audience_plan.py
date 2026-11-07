"""Audience-led generation and private publication handoff. No uploads or approvals."""
from pathlib import Path
import argparse,datetime,hashlib,json,math,re,subprocess,urllib.parse

PLAN='audience-plan.json'
PACKAGE='packaging.json'
HANDOFF='publication-handoff.json'
SIDECARS={HANDOFF,'production-journal.jsonl','viewer-study.json'}
FORMATS=('landscape','shorts')
POLICIES={
 'packaging':'https://support.google.com/youtube/answer/12340300?hl=en',
 'originality':'https://support.google.com/youtube/answer/1311392?hl=en',
 'shorts':'https://support.google.com/youtube/answer/15424877?hl=en',
 'ai':'https://support.google.com/youtube/answer/14328491?hl=en',
 'related':'https://support.google.com/youtube/answer/14075157?hl=en',
 'eligibility':'https://support.google.com/youtube/answer/72851?hl=en',
 'analytics':'https://support.google.com/youtubecreatorstudio/answer/12220281',
}
YOUTUBE_CASES=('processing_both_formats','processed_playback','private_visibility','copyright_claims','audience_setting','ai_use_setting','paid_promotion_assessment','landscape_uploaded_captions','shorts_classification','shorts_interface_clearance','final_titles_and_covers','related_video')
WEBSITE_CASES=('storage_hash_readback','actual_watch_route','caption_and_access_behavior')

def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def content_binding(ep):
 # IDs/status/music may change between editions without changing the lesson.
 return canonical({'topic':ep.get('topic'),'scenes':[{k:s.get(k) for k in ('id','text','tts_text','heading','diagram','anchors','source_ids')} for s in ep.get('scenes',[])],'sources':ep.get('sources')})
def text(v):return isinstance(v,str) and bool(v.strip()) and v.strip().lower() not in ('todo','fill in','tbd')
def need(v,label):
 if not text(v):raise ValueError('Audience plan incomplete: '+label)
def stamp(v):
 try:
  t=datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
  if t.tzinfo is None or t>datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=5):raise ValueError()
  return t
 except (ValueError,TypeError,AttributeError):raise ValueError('Actual timezone-aware observation date required')
def file_ref(folder,ref):
 if not isinstance(ref,dict):raise ValueError('Local hashed evidence required')
 raw=Path(ref.get('path',''));root=Path(folder).resolve();p=(root/raw).resolve()
 if raw.is_absolute() or '..' in raw.parts or not p.is_relative_to(root) or not p.is_file() or not p.stat().st_size or sha(p)!=ref.get('sha256'):raise ValueError('Missing, unsafe or stale audience evidence')
 return p
def create(ep):
 return {'schema':'earnalism.audience-plan.v2','content_sha256':content_binding(ep),
  'audience':{k:'' for k in ('primary_viewer','language','prior_knowledge','viewing_need','learning_promise','misconception','original_contribution','discovery_context','why_choose_this_explanation')},
  'formats':{f:{'purpose':'','composition':'','duration_rationale':'','titles':[{'id':'primary','text':ep.get('topic',''),'rationale':'A clear factual title; alternatives are optional','promise_scene':ep.get('scenes',[{}])[-1].get('id','') if ep.get('scenes') else ''}],'cover_brief':{'concept':'','text':'','meaning_without_text':''}} for f in FORMATS},
  'story':{'opening':{'scene_id':'','first_frame_visual':'','early_visual_payoff':'','payoff_scene':'','payoff_offset_seconds':None},'scenes':[],'retrieval':{'mode':'not_applicable','prompt':'','answer_scene':'','reason':'No extra prediction is needed for the core explanation'},'closing_callback':''},
  'study':{'questions':[],'card_choice_protocol':'','measurement_basis':'genuine_participants_and_observed_analytics'},
  'series':{'viewer_promise':'','sustainable_cadence':'','viewer_led_topic_method':'','next_lesson':{'status':'none','topic':'','url':None,'availability_observation':None,'reason':'No available follow-up has been selected'}},
  'note':'Editorial hypotheses, not real viewer responses or human approval. Creator completes these choices before narration; never ask the owner to assemble a form.'}
def initialize(folder):
 p=Path(folder);ep=load(p/'episode.json');plan=ep.get('audience_plan') or create(ep)
 plan={**plan,'content_sha256':content_binding(ep)}
 if not (p/PLAN).exists():(p/PLAN).write_text(json.dumps(plan,indent=2)+'\n')
 if not (p/PACKAGE).exists():
  q={'schema':'earnalism.packaging.v1','audience_plan_sha256':sha(p/PLAN),'formats':{f:{'selected_title_id':None,'selection_reason':'','kind':'designed_thumbnail' if f=='landscape' else 'cover_frame','master':None,'small_previews':[],'design_rationale':''} for f in FORMATS},'audience_test_result':'UNKNOWN; no viewer evidence supplied'}
  (p/PACKAGE).write_text(json.dumps(q,indent=2)+'\n')
 return p/PLAN
def validate_generation(folder):
 p=Path(folder);ep=load(p/'episode.json')
 if ep.get('private_test') is True:return {'status':'ENGINEERING_FIXTURE_ONLY','publication_approval':False}
 if not (p/PLAN).exists():raise ValueError('Audience plan required before narration setup')
 r=load(p/PLAN)
 if r.get('schema')!='earnalism.audience-plan.v2' or r.get('content_sha256')!=content_binding(ep):raise ValueError('Stale audience-plan content binding or obsolete schema; retain history and complete a fresh v2 brief')
 for key in ('primary_viewer','language','prior_knowledge','viewing_need','learning_promise','misconception','original_contribution'):need(r.get('audience',{}).get(key),key)
 ids={s['id'] for s in ep['scenes']}
 for fmt in FORMATS:
  f=r.get('formats',{}).get(fmt,{})
  for key in ('purpose','composition','duration_rationale'):need(f.get(key),fmt+':'+key)
  titles=f.get('titles',[])
  if not isinstance(titles,list) or not titles or any(not isinstance(t,dict) for t in titles):raise ValueError('One truthful title per format required; alternatives are optional')
  if len({t.get('id') for t in titles})!=len(titles) or len({t.get('text','').casefold() for t in titles})!=len(titles):raise ValueError('Distinct title hypotheses required')
  for t in titles:
   for key in ('id','text','rationale'):need(t.get(key),fmt+':title:'+key)
   if t.get('promise_scene') not in ids:raise ValueError('Title promise must map to actual lesson scene')
 if r['formats']['landscape']['composition']==r['formats']['shorts']['composition']:raise ValueError('Independently composed formats required')
 story=r.get('story',{});opening=story.get('opening',{})
 if opening.get('scene_id')!=ep['scenes'][0]['id'] or opening.get('payoff_scene') not in ids:raise ValueError('Opening must bind actual first/payoff scenes')
 for key in ('first_frame_visual','early_visual_payoff'):need(opening.get(key),key)
 offset=opening.get('payoff_offset_seconds')
 if isinstance(offset,bool) or not isinstance(offset,(float,int)) or not math.isfinite(offset) or offset<0:raise ValueError('Scene-relative early-payoff timing required')
 beats=story.get('scenes',[]);order=[s['id'] for s in ep['scenes']]
 if not isinstance(beats,list) or [b.get('scene_id') for b in beats]!=order:raise ValueError('Every actual scene needs one ordered question-answer-bridge plan')
 for i,b in enumerate(beats):
  for key in ('viewer_question','visible_answer','new_understanding','narration_economy','transition_reason'):need(b.get(key),'scene '+b['scene_id']+':'+key)
  if b.get('next_scene')!=(order[i+1] if i+1<len(order) else None):raise ValueError('Scene bridge must lead to the actual next scene or final closure')
  for fmt in FORMATS:
   f=b.get('formats',{}).get(fmt,{})
   for key in ('visual_action','reading_strategy','caption_clearance'):need(f.get(key),fmt+':scene:'+key)
   labels=f.get('essential_labels');hold=f.get('minimum_read_seconds')
   if not isinstance(labels,list) or any(not text(v) for v in labels):raise ValueError('Declare only essential scene labels; empty is valid for text-free explanation')
   if isinstance(hold,bool) or not isinstance(hold,(float,int)) or not math.isfinite(hold) or hold<0 or (labels and hold==0):raise ValueError('Finite reading time required for essential labels')
 retrieval=story.get('retrieval',{})
 if retrieval.get('mode') not in ('prediction','retrieval','not_applicable'):raise ValueError('Learning application decision required')
 if retrieval['mode']=='not_applicable':need(retrieval.get('reason'),'retrieval exception reason')
 else:
  need(retrieval.get('prompt'),'neutral prediction/retrieval prompt')
  if retrieval.get('answer_scene') not in ids:raise ValueError('Learning check needs an actual answer scene')
 need(story.get('closing_callback'),'closing callback')
 study=r.get('study',{});questions=study.get('questions',[])
 if not isinstance(questions,list) or len({q.get('id') for q in questions})!=len(questions):raise ValueError('Distinct topic-specific study questions required when research is used')
 if ep.get('requires_independent_learning_study') is True and not questions:raise ValueError('Explicitly required independent study needs neutral questions')
 for q in questions:
  need(q.get('id'),'study question id');need(q.get('prompt'),'neutral study question')
  if q.get('answer_scene') not in ids:raise ValueError('Study questions must map to actual explanation scenes')
 if study.get('measurement_basis') not in (None,'genuine_participants_and_observed_analytics'):raise ValueError('Simulated personas cannot supply audience evidence')
 n=r.get('series',{}).get('next_lesson',{'status':'none','reason':'Standalone episode'})
 if n.get('status') not in ('available','planned','none'):raise ValueError('Honest next-lesson status required')
 if n['status']=='available':
  u=urllib.parse.urlsplit(n.get('url') or '')
  if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('Available lesson needs real HTTPS route')
  need(n.get('topic'),'next lesson topic')
  observation=n.get('availability_observation') or {}
  if observation.get('url')!=n['url'] or observation.get('access') not in ('public','unlisted') or not observation.get('evidence'):raise ValueError('Available lesson needs URL-bound accessibility evidence')
  observed=stamp(observation.get('observed_at'))
  for ref in observation['evidence']:file_ref(p,ref)
 elif n.get('url'):raise ValueError('Planned/unavailable lessons cannot masquerade as watch links')
 elif n['status']=='planned':need(n.get('topic'),'planned next question')
 else:need(n.get('reason'),'standalone lesson reason')
 return {'status':'GENERATION_BRIEF_COMPLETE','audience_effectiveness':'UNPROVEN','publication_approval':False}
def validate_story_timing(folder):
 p=Path(folder);ep=load(p/'episode.json')
 if ep.get('private_test') is True:return
 validate_generation(p);r=load(p/PLAN);props=load(p/'props.json');scenes={s['id']:s for s in props['scenes']}
 for beat in r['story']['scenes']:
  s=scenes.get(beat['scene_id'])
  if not s or any(f['minimum_read_seconds']>s['end']-s['start'] for f in beat['formats'].values()):raise ValueError('Declared reading time does not fit actual scene; revise staging, never silently retime accepted speech')
 opening=r['story']['opening'];s=scenes[opening['payoff_scene']]
 if opening['payoff_offset_seconds']>=s['end']-s['start']:raise ValueError('Early-payoff checkpoint is outside the actual scene')
 return {'early_payoff_seconds':s['start']+opening['payoff_offset_seconds'],'reading_time':'Fits actual scene durations; perceptual review pending'}
def dimensions(p):
 data=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,codec_name','-of','json',str(p)],text=True))
 s=data['streams'][0]
 if p.suffix.lower() not in ('.png','.jpg','.jpeg') or s.get('codec_name') not in ('png','mjpeg'):raise ValueError('Static PNG/JPEG cover evidence required')
 return s['width'],s['height']
def referenced_assets(folder):
 """Check existing claims early and preserve their files across visual editions."""
 p=Path(folder).resolve();refs=[]
 if (p/PACKAGE).exists():
  for q in load(p/PACKAGE).get('formats',{}).values():
   if q.get('master'):refs.append(q['master'])
   refs.extend(q.get('small_previews',[]))
 if (p/PLAN).exists():refs.extend((load(p/PLAN).get('series',{}).get('next_lesson',{}).get('availability_observation') or {}).get('evidence',[]))
 return {str(file_ref(p,ref).relative_to(p)) for ref in refs}
def validate_package(folder):
 p=Path(folder);validate_generation(p);plan=load(p/PLAN);r=load(p/PACKAGE)
 if r.get('schema')!='earnalism.packaging.v1' or r.get('audience_plan_sha256')!=sha(p/PLAN):raise ValueError('Stale packaging plan binding')
 for fmt in FORMATS:
  q=r.get('formats',{}).get(fmt,{});choices={t['id'] for t in plan['formats'][fmt]['titles']}
  if q.get('selected_title_id') not in choices:raise ValueError('Select a title hypothesis for each format')
  need(q.get('selection_reason'),'title selection reason')
  if q.get('kind') not in (('designed_thumbnail',) if fmt=='landscape' else ('cover_frame','designed_cover')):raise ValueError('Dedicated landscape thumbnail and Shorts cover required')
  need(q.get('design_rationale'),'cover design rationale')
  if (q.get('master') or {}).get('path') in ('landscape.png','portrait.png','portrait-captioned.png'):raise ValueError('Use a dedicated selected-cover filename, separate from generated review posters')
  w,h=dimensions(file_ref(p,q.get('master')))
  if (w*9!=h*16 if fmt=='landscape' else w*16!=h*9):raise ValueError('Incorrect cover composition aspect ratio')
  if min(w,h)<720:raise ValueError('High-resolution cover master required')
  expected={(320,180),(160,90)} if fmt=='landscape' else {(180,320),(90,160)}
  actual={dimensions(file_ref(p,ref)) for ref in q.get('small_previews',[])}
  if not expected.issubset(actual):raise ValueError('Actual small-size cover previews required')
  metadata=load(p/('youtube-'+fmt+'.json'))
  selected=next(t['text'] for t in plan['formats'][fmt]['titles'] if t['id']==q['selected_title_id'])
  if metadata.get('title')!=selected or metadata.get('cover_sha256')!=q['master']['sha256'] or metadata.get('privacyStatus')!='private' or metadata.get('upload_automatically') is not False:raise ValueError('Final format metadata does not match selected private packaging')
 return {'status':'PACKAGING_ASSETS_COMPLETE','click_appeal':'UNPROVEN; real graphic/audience review remains required','publication_approval':False}
def write_metadata(folder):
 p=Path(folder);base=load(p/'youtube.json');plan=load(p/PLAN);package=load(p/PACKAGE)
 for fmt in FORMATS:
  q=package.get('formats',{}).get(fmt,{})
  selected=next((t for t in plan.get('formats',{}).get(fmt,{}).get('titles',[]) if t.get('id')==q.get('selected_title_id')),None)
  out={**base,'delivery_format':fmt,'privacyStatus':'private','upload_automatically':False,'title':selected['text'] if selected else base['title'],'packaging_status':'SELECTED_HYPOTHESIS_NOT_AUDIENCE_TESTED' if selected else 'UNSELECTED_PRIVATE_DRAFT','cover_sha256':(q.get('master') or {}).get('sha256'),'caption_delivery':'Upload captions.vtt separately and inspect YouTube CC' if fmt=='landscape' else 'Burned-in captions; inspect actual Shorts interface clearance','next_lesson_status':plan.get('series',{}).get('next_lesson',{}).get('status','unknown')}
  dest=p/('youtube-'+fmt+'.json')
  if dest.exists():raise FileExistsError('Preserve existing format metadata: '+str(dest))
  dest.write_text(json.dumps(out,indent=2)+'\n')
def fresh_handoff(folder):
 p=Path(folder);digest=sha(p/'delivery-manifest.json')
 return {'schema':'earnalism.publication-handoff.v1','delivery_manifest_sha256':digest,'local_qualification':'NOT_RUN','policy_review':{'reviewed_at':None,'reviewer':'','sources':POLICIES,'notes':''},'platform_video_ids':{f:None for f in FORMATS},'uploaded_source_sha256':{f:None for f in FORMATS},'youtube':{k:{'decision':'PENDING','reviewer':'','reviewed_at':None,'evidence':[],'note':''} for k in YOUTUBE_CASES},'website':{k:{'decision':'PENDING','reviewer':'','reviewed_at':None,'evidence':[],'note':''} for k in WEBSITE_CASES},'channel_monetization':'UNKNOWN; consult current Studio Earn totals; no eligibility thresholds inferred','publication_authorized':False}
def reset_handoff(folder):
 p=Path(folder);old=p/HANDOFF
 if old.exists():
  history=p/'logs/publication-handoff-history';history.mkdir(parents=True,exist_ok=True);dest=history/(sha(old)+'.json')
  if not dest.exists():dest.write_bytes(old.read_bytes())
 old.write_text(json.dumps(fresh_handoff(p),indent=2)+'\n')
 if (p/'viewer-study.json').exists():
  from viewer_study import reset
  reset(p,load(p/'viewer-study.json')['cards'])
def validate_handoff(folder,target='youtube'):
 p=Path(folder);r=load(p/HANDOFF);m=p/'delivery-manifest.json';manifest=load(m)
 if r.get('schema')!='earnalism.publication-handoff.v1' or r.get('delivery_manifest_sha256')!=sha(m):raise ValueError('Stale publication handoff')
 if SIDECARS.intersection(manifest):raise ValueError('Mutable operational sidecars must stay outside media manifest')
 for name,digest in manifest.items():file_ref(p,{'path':name,'sha256':digest})
 # Recompute local qualification; a handwritten PASS cannot replace the gate.
 import studio
 studio.release_check(p)
 sections=['youtube'] if target=='youtube' else ['website'] if target=='website' else ['youtube','website'] if target=='both' else []
 if not sections:raise ValueError('Choose youtube, website or both handoff target')
 if 'youtube' in sections:
  review=r.get('policy_review',{});stamp(review.get('reviewed_at'));need(review.get('reviewer'),'policy reviewer');need(review.get('notes'),'current policy applicability notes')
  if any(review.get('sources',{}).get(k)!=POLICIES[k] for k in ('ai','shorts','originality')):raise ValueError('Relevant official YouTube policy sources required')
  ids=[r.get('platform_video_ids',{}).get(f) for f in FORMATS]
  if any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}',v) for v in ids) or len(set(ids))!=2:raise ValueError('Distinct actual YouTube video IDs required')
  for fmt,name in [('landscape','landscape.mp4'),('shorts','portrait-captioned.mp4')]:
   if r.get('uploaded_source_sha256',{}).get(fmt)!=sha(p/name):raise ValueError('Uploaded source must bind the exact final format master')
 for section in sections:
  for key in YOUTUBE_CASES if section=='youtube' else WEBSITE_CASES:
   item=r.get(section,{}).get(key,{})
   if key=='related_video' and load(p/PLAN).get('series',{}).get('next_lesson',{}).get('status','none')!='available' and item.get('decision')=='NOT_APPLICABLE':
    need(item.get('note'),'unavailable next lesson explanation');need(item.get('reviewer'),'N/A reviewer');stamp(item.get('reviewed_at'));continue
   if item.get('decision')!='PASS' or not text(item.get('reviewer')) or not item.get('evidence'):raise ValueError('Manual platform/delivery check incomplete: '+key)
   stamp(item.get('reviewed_at'))
   for ref in item['evidence']:file_ref(p,ref)
 return {'status':'MANUAL_DELIVERY_EVIDENCE_COMPLETE','target':target,'publication_approval':False,'note':'No upload, publish, revenue eligibility or final owner authorization supplied by this check.'}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['init','generation','package','handoff-init','handoff-check']);a.add_argument('folder');a.add_argument('--target',choices=['youtube','website','both'],default='youtube');x=a.parse_args()
 if x.command=='init':print(initialize(x.folder))
 elif x.command=='handoff-init':reset_handoff(x.folder);print('Fresh pending handoff; no approvals transferred')
 else:print(json.dumps((validate_generation if x.command=='generation' else validate_package)(x.folder) if x.command in ('generation','package') else validate_handoff(x.folder,x.target),indent=2))
