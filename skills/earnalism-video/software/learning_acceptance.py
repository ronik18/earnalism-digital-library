"""Human evidence sidecar; never manufactures study results or owner approval."""
import json,hashlib

# The original contract remains readable for archived Moon evidence only.
CASES=('landscape_complete','shorts_complete','headphones','physical_speakers','scored_vs_dry','caption_reading','quarter_scene','desktop_reopen_seek','mobile_reopen_seek','brand_ending')
TOPIC_CASES=tuple('critical_explanations' if key=='quarter_scene' else key for key in CASES)

def _text(value):return isinstance(value,str) and bool(value.strip())
def _canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def _questions(plan):
 if not isinstance(plan,dict) or not isinstance(plan.get('study'),dict):raise ValueError('Current topic study plan required')
 questions=plan['study'].get('questions')
 if not isinstance(questions,list) or not questions:raise ValueError('Topic study questions required')
 normalized=[]
 for question in questions:
  if not isinstance(question,dict) or any(not _text(question.get(key)) for key in ('id','prompt','answer_scene')):raise ValueError('Complete neutral question IDs, prompts and answer scenes required')
  normalized.append({key:question[key] for key in ('id','prompt','answer_scene')})
 if len({question['id'] for question in normalized})!=len(normalized):raise ValueError('Unique study question identifiers required')
 return normalized

def pending(plan=None,previous=None):
 questions=_questions(plan) if plan is not None else None
 record={'schema':'earnalism.learning-acceptance.v2' if questions is not None else 'earnalism.learning-acceptance.v1','delivery_manifest_sha256':None,'learning':{'decision':'PENDING','reviewer':'','unresolved_confusions':[],'participants':[]},'acceptance':{'reviewer':'','cases':{k:{'status':'NOT_RUN','evidence':'','device':''} for k in (TOPIC_CASES if questions is not None else CASES)}},'note':'Owner coordinates real viewers and listening. Preparation, tests and scripted playback are not human acceptance.'}
 if questions is not None:
  record['study_sha256']=_canonical(questions)
  record['learning'].update(questions=questions,human_confirmed=False)
  record['acceptance']['human_confirmed']=False
 record['open_primary_findings']=primary_findings(previous) if previous else []
 return record

def primary_findings(record):
 """Known defects survive stale manifests and fresh pending study records."""
 if not isinstance(record,dict):raise ValueError('Invalid optional learning record')
 findings={}
 for row in record.get('open_primary_findings',[]):
  if not isinstance(row,dict) or not _text(row.get('id')) or not _text(row.get('detail')):raise ValueError('Invalid carried primary finding')
  findings[row['id']]=row
 rows=[('learning',v) for v in record.get('learning',{}).get('unresolved_confusions',[])]
 for key,label in [('learning','critical-explanation'),('acceptance','audiovisual')]:
  section=record.get(key,{})
  if section.get('decision') in ('FAIL','FAILED'):rows.append((key+':decision',section.get('reason') or section.get('note') or 'Recorded '+label+' review failed'))
 rows += [('device:'+key,'Recorded '+key+' failure') for key,value in record.get('acceptance',{}).get('cases',{}).items() if isinstance(value,dict) and value.get('status') in ('FAIL','FAILED')]
 for kind,detail in rows:
  value=detail if isinstance(detail,str) else json.dumps(detail,sort_keys=True,ensure_ascii=False)
  if not value.strip():continue
  key=_canonical([kind,value]);findings[key]={'id':key,'detail':value,'origin_manifest_sha256':record.get('delivery_manifest_sha256')}
 return list(findings.values())

def validate_release_findings(record,manifest_sha,review=None,folder=None):
 """Optional studies never gate release; known failures need resolution.
 The existing final candidate review can resolve named defects with evidence;
 no new participants, study PASS or separate permission is required.
 """
 if record is None:return {'study':'NOT_RUN_OPTIONAL','open_primary_findings':[]}
 findings=primary_findings(record);resolved={}
 if review and review.get('delivery_manifest_sha256')==manifest_sha and _text(review.get('reviewer')) and review.get('audiovisual') is True:
  for item in review.get('resolved_findings',[]):
   if not isinstance(item,dict) or not _text(item.get('id')) or not _text(item.get('resolution')) or not folder:raise ValueError('Named finding resolution and current evidence required')
   from strict_quality import evidence
   evidence(folder,item.get('evidence'));resolved[item['id']]=item
 remaining=[row for row in findings if row['id'] not in resolved]
 if remaining:raise ValueError('Known primary findings unresolved: '+'; '.join(row['detail'] for row in remaining))
 return {'study':'OPTIONAL_EVIDENCE_NOT_RELEASE_APPROVAL','open_primary_findings':[]}

def validate(record,manifest_sha,plan=None):
 if not isinstance(record,dict) or record.get('delivery_manifest_sha256')!=manifest_sha:raise ValueError('Learning/acceptance review is not bound to current delivery')
 version=record.get('schema')
 learning=record.get('learning',{});acceptance=record.get('acceptance',{})
 if not isinstance(learning,dict) or not isinstance(acceptance,dict):raise ValueError('Invalid learning/device acceptance schema')
 if version=='earnalism.learning-acceptance.v2':
  questions=_questions(plan)
  if record.get('study_sha256')!=_canonical(questions) or learning.get('questions')!=questions:raise ValueError('Learning review is not bound to current study questions')
  question_ids=[question['id'] for question in questions];cases=TOPIC_CASES
  if learning.get('human_confirmed') is not True or acceptance.get('human_confirmed') is not True:raise ValueError('Explicit human learning and device decisions required')
 elif version=='earnalism.learning-acceptance.v1':
  question_ids=('q1','q2','q3');cases=CASES
 else:raise ValueError('Unknown learning acceptance schema')
 if learning.get('decision')!='PASS' or not _text(learning.get('reviewer')) or learning.get('unresolved_confusions')!=[]:raise ValueError('Learning review incomplete or unresolved')
 participants=learning.get('participants',[])
 eligible=[participant for participant in participants if isinstance(participant,dict) and participant.get('first_time') is True and participant.get('single_uninterrupted_view') is True and _text(participant.get('id')) and isinstance(participant.get('responses'),dict) and all(_text(participant['responses'].get(question)) for question in question_ids)] if isinstance(participants,list) else []
 if not eligible:raise ValueError('Actual first-time viewer responses required')
 reviews=acceptance.get('cases',{})
 if not isinstance(reviews,dict) or not _text(acceptance.get('reviewer')) or any(not isinstance(reviews.get(key),dict) or reviews[key].get('status')!='PASS' or not _text(reviews[key].get('evidence')) or not _text(reviews[key].get('device')) for key in cases):raise ValueError('Full device/listening acceptance is incomplete')
 return True
