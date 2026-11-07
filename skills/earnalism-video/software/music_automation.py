"""Slow phrase automation on freshly ducked music only; never change the voice."""
import math,array,subprocess,sys,json,statistics
from pathlib import Path
from audio_balance import samples,analyze

def gain_plan(report,target=24):
 rows=report['windows'];knots=[]
 for start in range(0,len(rows),6):
  block=rows[start:start+6];gaps=[r['voice_dbfs']-r['music_dbfs'] for r in block if r['active_overlap']]
  eligible=[r for r in block if r['active_overlap']]
  energy_gap=10*math.log10(sum(10**(r['voice_dbfs']/10) for r in eligible)/sum(10**(r['music_dbfs']/10) for r in eligible)) if eligible else None
  correction=max(-12,min(8,energy_gap-target)) if eligible else (knots[-1]['gain_db'] if knots else 0)
  time=start+len(block)/2
  knots.append({'time':time,'gain_db':round(correction,4)})
 # Look ahead before a strong phrase; never chase its attack with a fast correction.
 for i in range(len(knots)-2,-1,-1):
  limit=(knots[i+1]['time']-knots[i]['time'])*2/3
  knots[i]['gain_db']=min(knots[i]['gain_db'],knots[i+1]['gain_db']+limit)
 for i in range(1,len(knots)):
  limit=(knots[i]['time']-knots[i-1]['time'])*2/3
  knots[i]['gain_db']=min(knots[i]['gain_db'],knots[i-1]['gain_db']+limit)
 return knots

def gain_at(time,knots):
 if time<=knots[0]['time']:return knots[0]['gain_db']
 for a,b in zip(knots,knots[1:]):
  if time<=b['time']:
   x=(time-a['time'])/(b['time']-a['time']);x=x*x*(3-2*x)
   return a['gain_db']+(b['gain_db']-a['gain_db'])*x
 return knots[-1]['gain_db']

def reentries(values,rate):
 hop=rate//10;quiet=[]
 for i in range(0,len(values)-hop+1,hop):quiet.append(max(abs(v) for v in values[i:i+hop])<1e-5)
 entries=[];i=0
 while i<len(quiet):
  if not quiet[i]:i+=1;continue
  start=i
  while i<len(quiet) and quiet[i]:i+=1
  if i-start>=5 and i<len(quiet):entries.append(round(i/10,3))
 return entries

def transition_check(knots,entries,reentry_seconds=1.25):
 slopes=[1.5*abs(b['gain_db']-a['gain_db'])/(b['time']-a['time']) for a,b in zip(knots,knots[1:])]
 maximum=max(slopes,default=0)
 return {'maximum_phrase_gain_rate_db_per_second':round(maximum,4),'limit_db_per_second':1.001,'reentry_fade_seconds':reentry_seconds,'reentries_seconds':entries,'issues':[] if maximum<=1.001 else ['Phrase gain slew exceeds limit'],'human_listening_required':True}

def apply_scene_trims(plan,scenes,trim_map):
 if any(not -3<=float(g)<=3 for g in trim_map.values()):raise ValueError('Unbounded musical phrase trim')
 plan=[dict(k) for k in plan]
 for knot in plan:
  for scene in scenes:
   if scene['start']-3<=knot['time']<=scene['end'] and scene['diagram'] in trim_map:knot['gain_db']+=float(trim_map[scene['diagram']])
  knot['gain_db']=max(-12,min(8,knot['gain_db']))
 for i in range(len(plan)-2,-1,-1):plan[i]['gain_db']=min(plan[i]['gain_db'],plan[i+1]['gain_db']+(plan[i+1]['time']-plan[i]['time'])*2/3)
 for i in range(1,len(plan)):plan[i]['gain_db']=min(plan[i]['gain_db'],plan[i-1]['gain_db']+(plan[i]['time']-plan[i-1]['time'])*2/3)
 return plan

def entry_gain(x,smoother=False):
 x=max(0,min(1,x))
 return x*x*x*(x*(x*6-15)+10) if smoother else x*x*(3-2*x)

def validate_plan(plan,seconds):
 """Reject invalid combined phrase curves before any stem is renamed/written."""
 if not isinstance(plan,list) or len(plan)<2:raise ValueError('At least two phrase gain knots required')
 result=[];previous=-1
 for knot in plan:
  if not isinstance(knot,dict) or set(knot)!={'time','gain_db'}:raise ValueError('Exact phrase knot fields required')
  t,g=knot['time'],knot['gain_db']
  if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (t,g)):raise ValueError('Finite numeric phrase knots required')
  if not previous<t<=seconds or t<0 or not -12<=g<=8:raise ValueError('Phrase knot outside time/gain bounds')
  previous=t;result.append({'time':float(t),'gain_db':float(g)})
 if transition_check(result,[])['issues']:raise ValueError('Phrase gain slew exceeds limit')
 return result


def respace_retimed_plan(plan,seconds,max_shift_seconds=.1):
 """Retain authored gains; move compressed knots slightly to preserve slew."""
 if not 0<=max_shift_seconds<=.1:raise ValueError('Unreviewed retimed-knot shift')
 if not isinstance(plan,list) or len(plan)<2:raise ValueError('At least two phrase gain knots required')
 # Validate original domains and order without silently relaxing slew limits.
 for i,k in enumerate(plan):
  if not isinstance(k,dict) or set(k)!={'time','gain_db'} or any(isinstance(k[f],bool) or not isinstance(k[f],(int,float)) or not math.isfinite(k[f]) for f in ['time','gain_db']):raise ValueError('Finite exact phrase knots required')
  if not 0<=k['time']<=seconds or not -12<=k['gain_db']<=8 or (i and k['time']<=plan[i-1]['time']):raise ValueError('Invalid retimed phrase knot')
 result=[dict(plan[0])]
 for k in plan[1:]:
  required=1.5*abs(k['gain_db']-result[-1]['gain_db'])
  time=max(k['time'],result[-1]['time']+required)
  if time-k['time']>max_shift_seconds+1e-8 or time>seconds:raise ValueError('Retimed curve needs a reviewed larger timing change')
  result.append(dict(k,time=time))
 return validate_plan(result,seconds)


def apply(folder,plan_override=None):
 from studio import sha
 p=Path(folder);source=p/'score-ducked.wav';before=p/'score-ducked-before-automation.wav'
 if before.exists():raise FileExistsError('Fresh original post-ducking source required; preserve previous automation')
 v=samples(p/'narration.wav');b=samples(source);n=max(len(v),len(b));v.extend([0.]*(n-len(v)));b.extend([0.]*(n-len(b)))
 plan=validate_plan(plan_override,n/24000) if plan_override is not None else gain_plan(analyze(v,b))
 source.rename(before)
 entries=reentries(b,24000);rate=48000
 episode=json.loads((p/'episode.json').read_text());trim_map=episode.get('music',{}).get('scene_gain_db',{})
 if trim_map and plan_override is None:
  if (p/'timeline.json').exists():scenes=json.loads((p/'timeline.json').read_text())['scenes']
  else:
   from studio import duration
   scenes=[];offset=0
   for scene in episode['scenes']:
    end=offset+duration(p/'raw'/(scene['id']+'.wav'));scenes.append({**scene,'start':offset,'end':end});offset=end
  plan=apply_scene_trims(plan,scenes,trim_map)
 provenance=json.loads((p/'score.provenance.json').read_text());entry_seconds=.6 if provenance.get('version') in ['moon-score-v5-balanced-acoustic-chamber','moon-score-v6-phrase-arrangement','moon-score-v7-balanced-arrangement','moon-score-v8-refined-voicing','moon-score-v9-final-note-balance'] else 1.25
 if provenance.get('version') in ('moon-score-v10-body-refinement','moon-score-v11-body-refinement','moon-score-v12-editorial-orchestration','moon-score-v13-speech-aware-phrase-placement','moon-score-v14-preserved-arrangement-retime'):entry_seconds=.25
 raw=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(before),'-ar',str(rate),'-ac','2','-f','f32le','-']))
 if sys.byteorder!='little':raw.byteswap()
 # Evaluate control gain at 10 ms resolution, then interpolate continuously per sample.
 controls=[gain_at(i/100,plan) for i in range(math.ceil(len(raw)/2/rate*100)+2)]
 for i in range(len(raw)//2):
  time=i/rate;position=time*100;j=int(position);fraction=position-j;db=controls[j]+(controls[j+1]-controls[j])*fraction;gain=10**(db/20)
  for entry in entries:
   if entry<=time<entry+entry_seconds:
    x=(time-entry)/entry_seconds;gain*=entry_gain(x,provenance.get('version') in ('moon-score-v10-body-refinement','moon-score-v11-body-refinement','moon-score-v12-editorial-orchestration','moon-score-v13-speech-aware-phrase-placement','moon-score-v14-preserved-arrangement-retime'))
  raw[i*2]*=gain;raw[i*2+1]*=gain
 if sys.byteorder!='little':raw.byteswap()
 subprocess.run(['ffmpeg','-v','error','-n','-f','f32le','-ar','48000','-ac','2','-i','pipe:0','-c:a','pcm_f32le',str(source)],input=raw.tobytes(),check=True)
 transition=transition_check(plan,entries,entry_seconds)
 (p/'music-automation.json').write_text(json.dumps({'method':'Six-second phrase energy with look-ahead, cubic smoothstep, peak gain slew <=1 dB/s; source-aware shaped re-entry','target_gap_db':24,'combined_plan_override':plan_override is not None,'override_includes_scene_trims':plan_override is not None,'gain_bounds_db':[-12,8],'knots':plan,'written_scene_trims_db':trim_map,'reentry_shape':('smootherstep' if provenance.get('version') in ('moon-score-v10-body-refinement','moon-score-v11-body-refinement','moon-score-v12-editorial-orchestration','moon-score-v13-speech-aware-phrase-placement','moon-score-v14-preserved-arrangement-retime') else 'smoothstep'),'transition_check':transition,'source_sha256':sha(before),'output_sha256':sha(source),'narration_sha256':sha(p/'narration.wav'),'human_mix_review':'PENDING','zero_samples_remain_zero':True},indent=2))
 if transition['issues']:raise ValueError('Unsafe music transition plan')
