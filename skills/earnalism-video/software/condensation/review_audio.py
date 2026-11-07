"""Read-only canonical music screen and complete private listening-target list.

No gain changes, audio synthesis or listening acceptance. New files only.
"""
from pathlib import Path
import argparse,json,hashlib,math,copy
from ..audio_balance import samples,analyze

def targets_for(screen,rests,duration):
    targets=[]
    for f in screen['passage_issues']:
        t=float(f['start'])
        targets.append({'start':max(0,t-1),'end':min(duration,t+2),'reason':f"Engineering flag at {t:.2f}s: music {f['gap_db']:.2f} dB below voice; listen in context, not a verdict.",'flag_start':t})
    for rest in rests:
        for edge in ['start','end']:
            t=float(rest[edge])
            if 0<t<duration:targets.append({'start':max(0,t-3.2),'end':min(duration,t+4.5),'reason':f"Authored rest {edge}: {rest['reason']}; assess fade/return against intentional silence."})
    return sorted(targets,key=lambda x:(x['start'],x['end']))

def _number(value):
    return type(value) in (int,float) and math.isfinite(value)

def _valid_rests(plan,duration):
    rests=plan.get('rests') if isinstance(plan,dict) else None
    if not isinstance(rests,list):return None
    if any(not isinstance(r,dict) or not all(_number(r.get(k)) for k in ('start','end')) or
           not 0<=r['start']<r['end']<=duration for r in rests):return None
    return rests

def authored_context(screen,plan,duration,reactive_ducking=None):
    """Annotate raw flags from explicit authored intervals; never resolve them.

    Unknown legacy plans remain unavailable. Declared note spans are not
    measurements of an acoustic sample's attack/tail or audible masking.
    """
    stage=('Delivered score/voice stems; reactive ducking explicitly disabled'
           if reactive_ducking is False else 'Post-ducking music/voice stems'
           if reactive_ducking is True else 'Current music/voice stems; ducking stage unverified')
    result={'state':'UNAVAILABLE','analysis_stage':stage,
      'stage_basis':'Explicit mix-provenance reactive_ducking field; not inferred from amplitude',
      'raw_flags':copy.deepcopy(screen.get('passage_issues',[])),
      'display_issues':[s.replace('Post-ducking','Delivered score') if reactive_ducking is False else s
                        for s in screen.get('issues',[])],
      'flags_resolved':False,'listening':'PENDING'}
    rests=_valid_rests(plan,duration)
    fade_in=plan.get('fade_in_seconds') if isinstance(plan,dict) else None
    fade_out=plan.get('fade_out_seconds') if isinstance(plan,dict) else None
    events=plan.get('events') if isinstance(plan,dict) else None
    if rests is None or not all(_number(v) and v>0 for v in (fade_in,fade_out)) or not isinstance(events,list):
        result['reason']='Missing or unsupported authored rest/fade/note declarations; raw findings retained'
        return result
    if any(not isinstance(e,dict) or not _number(e.get('time')) or not _number(e.get('duration')) or
           not 0<=e['time']<duration or e['duration']<=0 for e in events):
        result['reason']='Unsupported note declarations; raw findings retained'
        return result
    shoulders=[]
    for rest in rests:
        reason=rest.get('reason','Authored rest')
        if rest['start']>0:shoulders.append({'kind':'fade_out','start':max(0,rest['start']-fade_out),'end':rest['start'],'reason':reason})
        if rest['end']<duration:shoulders.append({'kind':'fade_in','start':rest['end'],'end':min(duration,rest['end']+fade_in),'reason':reason})
    flags=[]
    for flag in result['raw_flags']:
        a=float(flag['start']);b=min(duration,a+1)
        overlaps=lambda row:a<row['end'] and b>row['start']
        notes=[{'onset':e['time'],'declared_duration':e['duration'],'instrument':e.get('instrument'),
                'age_at_window_start':a-e['time']}
               for e in events if e['time']<b and e['time']+e['duration']>a]
        flags.append({'flag':copy.deepcopy(flag),'interval':[a,b],
          'authored_rest_overlaps':[copy.deepcopy(r) for r in rests if overlaps(r)],
          'authored_shoulder_overlaps':[copy.deepcopy(s) for s in shoulders if overlaps(s)],
          'declared_note_spans':notes,'interpretation':'Authored context only; no audible cause or acceptance inferred'})
    result.update({'state':'AVAILABLE','rests':copy.deepcopy(rests),'shoulders':shoulders,
      'flags':flags,'scope':'Rest shoulders and declared note spans only; other automation and actual acoustic envelopes are not inferred'})
    return result

def merge_targets(targets):
    """Review overlapping context once, retaining every original reason/flag."""
    merged=[]
    for index,target in sorted(enumerate(targets),key=lambda row:(row[1]['start'],row[1]['end'])):
        if not merged or target['start']>merged[-1]['end']:
            merged.append({'start':target['start'],'end':target['end'],'source_indices':[],
                           'source_reasons':[],'flag_starts':[]})
        current=merged[-1];current['end']=max(current['end'],target['end']);current['source_indices'].append(index)
        current['source_reasons'].append(target['reason'])
        if 'flag_start' in target:current['flag_starts'].append(target['flag_start'])
    for target in merged:
        target['reason']=' | '.join(dict.fromkeys(target['source_reasons']))
    return merged

def prepare(root):
    root=Path(root); report_path=root/'music-screen.json';targets_path=root/'listening-targets.json'
    if report_path.exists() or targets_path.exists():raise ValueError('Preserve existing review; use a fresh candidate')
    voice,bed=samples(root/'narration.wav'),samples(root/'score.wav')
    report=analyze(voice,bed)
    report['stem_sha256']={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['narration.wav','score.wav']}
    report['scope']='Current body-only stems; ident excluded. Flags remain unresolved until actual review.'
    plan_path=root/'score-plan.json';plan=json.loads(plan_path.read_text());duration=len(voice)/24000
    mix_path=root/'mix-provenance.json';mix={};mix_digest=None
    if mix_path.is_file():
        try:
            raw_mix=mix_path.read_bytes();mix_digest=hashlib.sha256(raw_mix).hexdigest();candidate=json.loads(raw_mix)
            if isinstance(candidate,dict):mix=candidate
        except (OSError,ValueError):pass  # Optional context is unknown, never a new release gate.
    report['authored_context']=authored_context(report,plan,duration,mix.get('reactive_ducking'))
    report['authored_context']['score_plan_sha256']=hashlib.sha256(plan_path.read_bytes()).hexdigest()
    if mix_digest:report['authored_context']['mix_provenance_sha256']=mix_digest
    raw_targets=targets_for(report,_valid_rests(plan,duration) or [],duration)
    targets={'targets':merge_targets(raw_targets),'raw_targets':raw_targets,
             'music_screen_sha256':None,'listening':'PENDING','flags_resolved':False}
    report_path.write_text(json.dumps(report,indent=2)+'\n');targets['music_screen_sha256']=hashlib.sha256(report_path.read_bytes()).hexdigest()
    targets_path.write_text(json.dumps(targets,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();r=prepare(a.root)
    print(json.dumps({'flags':r['passage_issues'],'median_gap_db':r['median_music_below_voice_db'],'listening':'PENDING'},indent=2))
