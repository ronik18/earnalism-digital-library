"""Mandatory, artifact-bound fact and graphical review. Never grants human approval."""
from pathlib import Path
import json,hashlib,math,argparse,datetime,urllib.parse,re,os
from contextvars import ContextVar
from functools import wraps
NAME='strict-quality-review.json'
FORMATS=('Landscape','Portrait')
GRAPHIC_CHECKS=('topic_model_accuracy','object_label_clearance','caption_safe_area','mobile_legibility','transition_continuity','watermark_branding','source_context','packaging_truth_and_readability','opening_visual_payoff','scene_question_answer_continuity','cognitive_reading_load','title_payoff_alignment')
# '@' cannot occur in a valid body scene ID, so ending samples cannot collide.
BRAND_ENDING_SCENE='@brand-ending'
PLAYER_CHECKS=('reopen_seek','fullscreen_fit','captions_and_gaps','replay_after_ending','explanatory_overlay_sync')
def _uncached_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
_HASH_SESSION=ContextVar('earnalism_strict_hash_session',default=None)
class _HashSession:
 """Reuse digests only for unchanged files during one read-only operation."""
 def __init__(self):self.files={}
 @staticmethod
 def fingerprint(path):
  try:s=path.stat()
  except OSError as error:raise ValueError('File changed during strict quality operation: '+str(path)) from error
  return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 def digest(self,path):
  # Keep the lexical path so replacing a symlink cannot evade identity checks.
  path=Path(os.path.abspath(path));before=self.fingerprint(path)
  if path in self.files:
   previous,digest=self.files[path]
   if before!=previous:raise ValueError('File changed during strict quality operation: '+str(path))
   return digest
  digest=_uncached_sha(path)
  if self.fingerprint(path)!=before:raise ValueError('File changed during strict quality operation: '+str(path))
  self.files[path]=(before,digest);return digest
 def verify(self):
  for path,(before,_) in self.files.items():
   if self.fingerprint(path)!=before:raise ValueError('File changed during strict quality operation: '+str(path))
def _scoped_hashes(function):
 @wraps(function)
 def scoped(*args,**kwargs):
  if _HASH_SESSION.get() is not None:return function(*args,**kwargs)
  session=_HashSession();token=_HASH_SESSION.set(session)
  try:
   result=function(*args,**kwargs);session.verify();return result
  finally:_HASH_SESSION.reset(token)
 return scoped
def _assert_hashes_unchanged():
 session=_HASH_SESSION.get()
 if session is not None:session.verify()
def sha(p):
 session=_HASH_SESSION.get()
 return session.digest(p) if session is not None else _uncached_sha(p)
def load(p):return json.loads(Path(p).read_text())
def nonblank(value):return isinstance(value,str) and bool(value.strip())
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def plan(folder):
 from delivery_conform import sentences
 p=Path(folder);ep=load(p/'episode.json');props=load(p/'props.json');claims=[];samples=[]
 for rows in (ep.get('scenes',[]),props.get('scenes',[]),ep.get('sources',[])):
  ids=[v.get('id') for v in rows]
  if any(not nonblank(v) for v in ids) or len(ids)!=len(set(ids)):raise ValueError('Unique scene/source identifiers required')
 if not isinstance(props.get('duration'),(float,int)) or not math.isfinite(props['duration']) or props['duration']<=0:raise ValueError('Valid duration required')
 for scene in ep.get('scenes',[])+props.get('scenes',[]):
  if not re.fullmatch(r'[A-Za-z0-9_-]+',scene['id']):raise ValueError('Safe scene identifiers required')
 previous=0.0
 for scene in props.get('scenes',[]):
  if abs(scene['start']-previous)>.001:raise ValueError('Contiguous scene coverage required')
  previous=scene['end']
 if abs(previous-props['duration'])>.001:raise ValueError('Complete body duration coverage required')
 for scene in ep.get('scenes',[]):
  for i,text in enumerate(sentences(scene['text'])):claims.append({'id':f"{scene['id']}:speech:{i}",'scene':scene['id'],'text':text,'source_ids':scene['source_ids']})
 for scene in props.get('scenes',[]):
  a,b=scene['start'],scene['end']
  if not math.isfinite(a+b) or not 0<=a<b:raise ValueError('Invalid scene timing for strict review')
  times={'entry':a,'hold':(a+b)/2,'exit':max(a,b-1/30)}
  for i,anchor in enumerate(scene.get('anchors',[])):
   t=anchor['time']
   for label,offset in [('before',-.25),('during',.4),('after',2.0)]:times[f'anchor-{i}-{label}']=max(a,min(b-1/30,t+offset))
  seen=set()
  for point in scene.get('review_checkpoints',[]):
   if not isinstance(point,dict):raise ValueError('Valid named motion checkpoint required')
   key=point.get('id','');offset=point.get('offset_seconds')
   if not re.fullmatch(r'[A-Za-z0-9_-]+',key) or key in seen or not nonblank(point.get('reason')):raise ValueError('Unique named motion checkpoint and reason required')
   if isinstance(offset,bool) or not isinstance(offset,(int,float)) or not math.isfinite(offset) or not 0<=offset<b-a:raise ValueError('Motion checkpoint must lie inside its actual scene')
   seen.add(key);times['regression-'+key]=a+offset
  for fmt in FORMATS:
   for label,t in times.items():
    first,last=math.ceil(a*30),math.ceil(b*30)-1
    if first>last:raise ValueError('Scene has no visible rendered frame')
    frame=min(last,max(first,round(t*30)))
    samples.append({'id':f"{scene['id']}:{fmt}:{label}",'scene':scene['id'],'format':fmt,'seconds':round(frame/30,6)})
 if not claims or not samples or {s['id'] for s in ep['scenes']}!={s['id'] for s in props['scenes']}:raise ValueError('Complete scene and spoken-claim coverage required')
 # Topic-agnostic checkpoints complement scene/anchor samples. An opening
 # promise is inspected at its actual scene-relative visual reveal time.
 audience=p/'audience-plan.json'
 if audience.exists() and load(audience).get('schema')=='earnalism.audience-plan.v2' and ep.get('private_test') is not True:
  from audience_plan import validate_story_timing
  timing=validate_story_timing(p)
  for fmt in FORMATS:
   for label,t in [('first-subject',0),('before-payoff',max(0,timing['early_payoff_seconds']-.2)),('visual-payoff',timing['early_payoff_seconds']),('after-payoff',min(props['duration']-1/30,timing['early_payoff_seconds']+.5))]:
    frame=min(math.ceil(props['duration']*30)-1,max(0,round(t*30)))
    visible=next(v for v in props['scenes'] if math.ceil(v['start']*30)<=frame<math.ceil(v['end']*30))
    samples.append({'id':f"{visible['id']}:{fmt}:{label}",'scene':visible['id'],'format':fmt,'seconds':round(frame/30,6)})
 body_frames=math.ceil(props['duration']*30);ending=props.get('intro') or {};ending_frames=0
 if ending:
  seconds=ending.get('seconds')
  if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<=0 or ending.get('placement')!='end':raise ValueError('Valid end-placed brand duration required for strict review')
  ending_frames=round(seconds*30)
  if ending_frames<3:raise ValueError('Brand ending needs entry, middle and final frames')
  # The renderer appends the ident after ceil(body_seconds * fps), not at the
  # unquantized speech duration. Review its actual first/middle/last frames.
  for fmt in FORMATS:
   for label,frame in [('entry',body_frames),('middle',body_frames+ending_frames//2),('final',body_frames+ending_frames-1)]:
    samples.append({'id':f'{BRAND_ENDING_SCENE}:{fmt}:{label}','scene':BRAND_ENDING_SCENE,'format':fmt,'seconds':round(frame/30,6)})
 expected_seconds=(body_frames+ending_frames)/30
 return {'expected_seconds':expected_seconds,'schema':'earnalism.strict-quality-plan.v2','episode_sha256':sha(p/'episode.json'),'props_sha256':sha(p/'props.json'),'claims':claims,'frames':samples,'formats':list(FORMATS),'graphic_checks':list(GRAPHIC_CHECKS),'player_checks':list(PLAYER_CHECKS)}
def reset(folder):
 p=Path(folder);record=initialize(p);old=p/NAME
 if old.exists():
  history=p/'logs/strict-quality-history';history.mkdir(parents=True,exist_ok=True);copy=history/(sha(old)+'.json')
  if not copy.exists():copy.write_bytes(old.read_bytes())
 old.write_text(json.dumps(record,indent=2));return record

def pending():
 return {'schema':'earnalism.strict-quality-review.v1','delivery_manifest_sha256':None,'plan_sha256':None,'factual':{'decision':'PENDING','reviewer':'','reviewed_at':'','human_confirmed':False,'unresolved':[],'sources':{},'claims':{},'visual_claims':{}},'graphical':{'decision':'PENDING','reviewer':'','reviewed_at':'','human_confirmed':False,'unresolved':[],'frames':{},'checks':{},'players':{},'complete_playback':{}},'note':'Pending real reviews. Do not fill human approval from tests or an agent self-score.'}
def initialize(folder):
 p=Path(folder);r=pending();q=plan(p);r['plan_sha256']=canonical(q)
 if (p/'delivery-manifest.json').exists():r['delivery_manifest_sha256']=sha(p/'delivery-manifest.json')
 r['factual']['claims']={v['id']:{'verdict':'PENDING','source_ids':[],'reason':'','evidence':[]} for v in q['claims']}
 r['factual']['visual_claims']={s['id']:{'coverage_confirmed':False,'assertions':[]} for s in load(p/'episode.json')['scenes']}
 r['graphical']['frames']={v['id']:{'verdict':'PENDING','seconds':v['seconds'],'media_sha256':None,'evidence':[]} for v in q['frames']}
 for section,keys in [('checks',GRAPHIC_CHECKS),('players',PLAYER_CHECKS)]:r['graphical'][section]={f'{fmt}:{key}':{'verdict':'PENDING','evidence':[]} for fmt in FORMATS for key in keys}
 r['graphical']['complete_playback']={fmt:{'verdict':'PENDING','device':'','watched_seconds':0,'complete_uninterrupted_view':False,'media_sha256':None,'evidence':[]} for fmt in FORMATS}
 return r

@_scoped_hashes
def evidence(folder,refs,frame=False):
 if not isinstance(refs,list) or not refs:raise ValueError('Strict review evidence missing')
 root=Path(folder).resolve()
 for ref in refs:
  if not isinstance(ref,dict):raise ValueError('Invalid strict evidence reference')
  raw=Path(ref.get('path',''))
  if raw.is_absolute() or '..' in raw.parts or raw.as_posix() in ('.',NAME):raise ValueError('Unsafe strict review evidence path')
  p=(root/raw).resolve()
  if not p.is_relative_to(root) or not p.is_file() or p.stat().st_size==0 or sha(p)!=ref.get('sha256'):raise ValueError('Missing or changed strict review evidence')
  if frame and p.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValueError('Rendered frame evidence required')
def verdict(folder,row,frame=False):
 if not isinstance(row,dict) or row.get('verdict')!='PASS':raise ValueError('Strict review contains failed, pending or unreviewed item')
 evidence(folder,row.get('evidence'),frame)
def human(section):
 if section.get('decision')!='PASS' or not nonblank(section.get('reviewer')) or section.get('human_confirmed') is not True or section.get('unresolved')!=[]:raise ValueError('Strict human review incomplete or unresolved')
 try:stamp=datetime.datetime.fromisoformat(section['reviewed_at'].replace('Z','+00:00'));assert stamp.tzinfo is not None;assert stamp<=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=5)
 except (KeyError,ValueError,AssertionError,AttributeError):raise ValueError('Timestamped strict human review required')
@_scoped_hashes
def validate(folder):
 p=Path(folder);path=p/NAME
 if not path.exists():raise ValueError('Mandatory strict factual/graphical review missing')
 r=load(path)
 if not isinstance(r,dict) or any(not isinstance(r.get(k),dict) for k in ('factual','graphical')):raise ValueError('Invalid strict review schema')
 if any(not isinstance(r['factual'].get(k),dict) for k in ('sources','claims','visual_claims')) or any(not isinstance(r['graphical'].get(k),dict) for k in ('frames','checks','players','complete_playback')):raise ValueError('Invalid strict review coverage schema')
 q=plan(p);manifest=load(p/'delivery-manifest.json')
 if not {'episode.json','props.json','landscape.mp4','portrait-captioned.mp4'}.issubset(manifest):raise ValueError('Strict review requires a complete bound media/storyboard manifest')
 if NAME in manifest:raise ValueError('Strict review sidecar must be outside delivery manifest')
 if r.get('schema')!='earnalism.strict-quality-review.v1' or r.get('delivery_manifest_sha256')!=sha(p/'delivery-manifest.json') or r.get('plan_sha256')!=canonical(q):raise ValueError('Stale strict review binding')
 if any(Path(n).name!=n or not (p/n).is_file() or sha(p/n)!=h for n,h in manifest.items()):raise ValueError('Delivery changed during strict review')
 factual=r.get('factual',{});graphic=r.get('graphical',{});human(factual);human(graphic)
 sources={s['id']:s for s in load(p/'episode.json')['sources']};checked=factual.get('sources',{})
 def checked_sources(ids):
  if not isinstance(ids,list) or not ids or any(s not in sources for s in ids):raise ValueError('Claim source coverage incomplete')
  for sid in ids:
   source=checked.get(sid,{})
   if not isinstance(source,dict):raise ValueError('Invalid authoritative source review')
   u=urllib.parse.urlsplit(source.get('url',''))
   if source.get('url')!=sources[sid]['url'] or u.scheme not in ('http','https') or not u.hostname or source.get('primary_or_authoritative') is not True or not nonblank(source.get('retrieved_at')):raise ValueError('Reviewed authoritative source required')
   verdict(p,source)
 if set(factual.get('claims',{}))!={v['id'] for v in q['claims']}:raise ValueError('Spoken claim coverage incomplete')
 for claim in q['claims']:
  row=factual['claims'][claim['id']];verdict(p,row);checked_sources(row.get('source_ids'))
  if not nonblank(row.get('reason')):raise ValueError('Claim verification reason required')
 scene_ids={s['id'] for s in load(p/'episode.json')['scenes']}
 if set(factual.get('visual_claims',{}))!=scene_ids:raise ValueError('Visual claim coverage incomplete')
 for row in factual['visual_claims'].values():
  if not isinstance(row,dict) or row.get('coverage_confirmed') is not True or not isinstance(row.get('assertions'),list) or not row['assertions']:raise ValueError('Every diagram needs explicit visual-claim inventory')
  for assertion in row['assertions']:
   verdict(p,assertion);checked_sources(assertion.get('source_ids'))
   if not nonblank(assertion.get('text')) or not nonblank(assertion.get('reason')):raise ValueError('Visual claim and verification reason required')
 if set(graphic.get('frames',{}))!={v['id'] for v in q['frames']}:raise ValueError('Scene/transition/brand-ending frame review coverage incomplete')
 for sample in q['frames']:
  row=graphic['frames'][sample['id']];verdict(p,row,frame=True)
  media='landscape.mp4' if sample['format']=='Landscape' else 'portrait-captioned.mp4'
  if row.get('seconds')!=sample['seconds'] or row.get('media_sha256')!=sha(p/media):raise ValueError('Frame review time/media binding mismatch')
 for section,keys in [('checks',GRAPHIC_CHECKS),('players',PLAYER_CHECKS)]:
  if set(graphic.get(section,{}))!={f'{fmt}:{key}' for fmt in FORMATS for key in keys}:raise ValueError('Graphical/player checklist coverage incomplete')
  for row in graphic[section].values():verdict(p,row)
 if set(graphic.get('complete_playback',{}))!=set(FORMATS):raise ValueError('Both full-format playthroughs required')
 for fmt,row in graphic['complete_playback'].items():
  verdict(p,row)
  media='landscape.mp4' if fmt=='Landscape' else 'portrait-captioned.mp4'
  seconds=row.get('watched_seconds',0)
  if row.get('complete_uninterrupted_view') is not True or isinstance(seconds,bool) or not isinstance(seconds,(float,int)) or not math.isfinite(seconds) or seconds<q['expected_seconds']-1/30 or row.get('media_sha256')!=sha(p/media):raise ValueError('Complete artifact-bound playback required')
  if not nonblank(row.get('device')):raise ValueError('Full-playback device evidence required')
 return {'status':'STRICT_FACTUAL_AND_GRAPHICAL_REVIEW_PASS','publication_approval':False,'spoken_claims':len(q['claims']),'frame_reviews':len(q['frames'])}
@_scoped_hashes
def capture(folder):
 """Extract required frames from final MP4s; attach evidence without approving it."""
 import subprocess
 p=Path(folder);q=plan(p);r=load(p/NAME)
 if r['graphical']['decision']!='PENDING' or any(v.get('verdict')!='PENDING' for v in r['graphical']['frames'].values()) or r['plan_sha256']!=canonical(q) or r['delivery_manifest_sha256']!=sha(p/'delivery-manifest.json'):raise ValueError('Fresh pending review required for frame capture')
 manifest=load(p/'delivery-manifest.json')
 if any(Path(n).name!=n or sha(p/n)!=h for n,h in manifest.items()):raise ValueError('Delivery changed before frame capture')
 target=p/'quality-evidence'/('frames-'+r['delivery_manifest_sha256'][:16]);target.mkdir(parents=True,exist_ok=True);rows=[]
 for sample in q['frames']:
  name='landscape.mp4' if sample['format']=='Landscape' else 'portrait-captioned.mp4';image=target/(sample['id'].replace(':','-')+'.png')
  if image.exists():raise FileExistsError('Preserve existing evidence: '+str(image))
  subprocess.run(['ffmpeg','-v','error','-n','-ss',str(max(0,round(sample['seconds']*30)/30-1e-5)),'-i',str(p/name),'-frames:v','1',str(image)],check=True)
  row={**sample,'media_sha256':sha(p/name),'evidence':[{'path':str(image.relative_to(p)),'sha256':_uncached_sha(image)}]};rows.append(row)
 # Persist only once every extraction succeeded and the inputs remain unchanged;
 # no partial or stale set can appear complete. All decisions remain pending.
 _assert_hashes_unchanged()
 # Generated output metadata may be updated by filesystem indexing. Verify its
 # bytes again before committing; keep identity guards on all source inputs.
 for row in rows:
  for ref in row['evidence']:
   if _uncached_sha(p/ref['path'])!=ref['sha256']:raise ValueError('Generated frame changed before evidence commit')
 for row in rows:r['graphical']['frames'][row['id']].update(seconds=row['seconds'],media_sha256=row['media_sha256'],evidence=row['evidence'])
 (target/'index.json').write_text(json.dumps(rows,indent=2));(p/NAME).write_text(json.dumps(r,indent=2));return {'frames':len(rows),'directory':str(target),'all_decisions':'PENDING'}

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['plan','init','capture','check']);a.add_argument('folder');x=a.parse_args();p=Path(x.folder)
 if x.command=='plan':print(json.dumps(plan(p),indent=2))
 elif x.command=='check':print(json.dumps(validate(p),indent=2))
 elif x.command=='capture':print(json.dumps(capture(p),indent=2))
 else:
  with (p/NAME).open('x') as f:json.dump(initialize(p),f,indent=2)
  print(p/NAME)
