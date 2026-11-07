"""Source-aware musical phrase repair; never modifies narration or hides audit flags.

The unchanged licensed base sample renderer is reused in an isolated function
namespace. Its planner is supplied explicitly so there is no global patch and
its asset, note-bound, source-event, waveform and silence safeguards still run.
"""
from pathlib import Path
import copy,hashlib,json,math,types
import final_chamber_score as base
import editorial_score
from audio_balance import samples
VERSION='moon-score-v13-speech-aware-phrase-placement'

def source_bindings(paths=None):
    paths=paths or [Path(__file__),Path(base.__file__),Path(editorial_score.__file__)]
    return {str(Path(path).resolve()):hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}

def require_source_bindings(bindings):
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest for path,digest in bindings.items()):
        raise ValueError('Music source changed during composition; retain attempt and rebuild from stable sources')
    return True


def db_at(values,rate,start,seconds=.5):
    chunk=values[max(0,round(start*rate)):max(0,round((start+seconds)*rate))]
    return 20*math.log10(max(1e-12,math.sqrt(sum(v*v for v in chunk)/max(1,len(chunk)))))


def phrase_energy(voice,rate,start):
    # Look through the first natural note decay as well as its onset.
    return min(db_at(voice,rate,start+offset,.5) for offset in (0,.4,.8))


def adjust_plan(events,quiet,voice,rate,seconds,max_shift=.9):
    """Move existing principal attacks locally; preserve content, order and rests.

    Only a meaningful >=4 dB phrase-energy improvement triggers placement. A
    shared chord remains one chord. Candidate placement never crosses a rest or
    another principal group, and no music is added to a declared silence.
    """
    if not 0<=max_shift<=.9:raise ValueError('Source attack shift outside bounded local phrase placement')
    output=copy.deepcopy(events);groups=[]
    for i,event in enumerate(output):
        if groups and event['phrase']==output[groups[-1][-1]]['phrase'] and event['time']-output[groups[-1][-1]]['time']<.25:
            groups[-1].append(i)
        else:groups.append([i])
    changes=[]
    for gi,group in enumerate(groups):
        start=output[group[0]]['time'];end=output[group[-1]]['time']
        if any(a<=start<=b for a,b in quiet):continue
        current=phrase_energy(voice,rate,start)
        # Consider phrase interiors close to the current score; do not move an
        # already clear attack just to pursue the mathematically loudest word.
        if current>=-21:continue
        candidates=[]
        for n in range(-9,10):
            shift=n/10
            if abs(shift)>max_shift:continue
            a=start+shift;b=end+shift
            if a<0 or b>=seconds-.65:continue
            if gi and a<=output[groups[gi-1][-1]]['time']+.08:continue
            if gi+1<len(groups) and b>=output[groups[gi+1][0]]['time']-.08:continue
            # Neither crossing nor entering an authored rest is allowed.
            if any(max(min(start,a),qa)<min(max(end,b)+.12,qb) for qa,qb in quiet):continue
            energy=phrase_energy(voice,rate,a)
            candidates.append((energy-.7*abs(shift),energy,shift))
        if not candidates:continue
        _,energy,shift=max(candidates)
        if energy-current<4 or abs(shift)<.099:continue
        for index in group:
            output[index]['time']=round(output[index]['time']+shift,4)
        changes.append({'phrase':output[group[0]]['phrase'],'old_time':start,'new_time':output[group[0]]['time'],
                        'shift_seconds':shift,'voice_window_before_dbfs':round(current,2),'voice_window_after_dbfs':round(energy,2),
                        'reason':'Move existing attack from weak speech into a nearby connected spoken phrase; no reactive gain chase'})
    if [(e['midi'],e['instrument'],e['phrase']) for e in output]!=[(e['midi'],e['instrument'],e['phrase']) for e in events]:raise ValueError('Musical content changed')
    return output,changes


def feasibility(report,max_slew_db_per_second=1):
    """Explain impossible blanket-gain requests; never changes the audit result."""
    rows=[r for r in report['windows'] if r['active_overlap'] and not r.get('fade_boundary')]
    conflicts=[]
    for a,b in zip(rows,rows[1:]):
        alo=a['music_below_voice_db']-32;ahi=a['music_below_voice_db']-16
        blo=b['music_below_voice_db']-32;bhi=b['music_below_voice_db']-16
        required=max(0,blo-ahi,alo-bhi);allowed=(b['start']-a['start'])*max_slew_db_per_second
        if required>allowed+.05:conflicts.append({'before_seconds':a['start'],'after_seconds':b['start'],'required_gain_change_db':round(required,2),'allowed_db':round(allowed,2)})
    return {'max_slew_db_per_second':max_slew_db_per_second,'adjacent_constraints_feasible':not conflicts,'conflicts':conflicts,
            'interpretation':'A failed interval requires a source/phrase or narration-timing repair. Do not accelerate gain motion or erase a passage flag.'}


def compose(path,seconds,quiet_intervals=(),rate=24000,scenes=(),asset_root=base.ASSETS,speech_intervals=(),palette='acoustic_editorial_v12'):
    if palette not in ('acoustic_editorial_v12','acoustic_speech_aware_v13'):raise ValueError('Speech-aware repair requires the licensed editorial chamber source')
    bound_sources=source_bindings()
    path=Path(path);voice_path=path.parent/'narration.wav';voice=samples(voice_path,rate);before=hashlib.sha256(voice_path.read_bytes()).hexdigest();changes=[]
    def planner(length,current_scenes):
        events,planned=base.plan(length,current_scenes)
        edited,rows=adjust_plan(events,sorted(set(tuple(q) for q in [*quiet_intervals,*planned])),voice,rate,length)
        changes.extend(rows);return edited,planned
    def dynamics(events,current_scenes):
        # Preserve v12 note voicing. Static reductions supplement weak attacks;
        # they apply to notes, never to a millisecond speech-following envelope.
        edited=editorial_score.adjust_events(events,current_scenes)
        for original,event in zip(events,edited):
            at=phrase_energy(voice,rate,event['time'])
            if at<-23 and event['phrase']=='soft harmonic support':
                existing=event.get('arrangement_gain_db',0)-original.get('arrangement_gain_db',0)
                delta=max(-3-existing,-2.5)
                if delta<0:
                    event['arrangement_gain_db']+=delta
                    event['editorial_gain_db']=existing+delta
                    event['editorial_reason']='Static voicing reduction for a support attack in a weak spoken phrase; timing and authored rest preserved'
        return edited
    namespace=dict(base.compose.__globals__);namespace['plan']=planner
    renderer=types.FunctionType(base.compose.__code__,namespace,base.compose.__name__,base.compose.__defaults__,base.compose.__closure__)
    result=renderer(path,seconds,quiet_intervals,rate,scenes,asset_root,speech_intervals,event_adjuster=dynamics,
      provenance_overrides={'version':VERSION,'title':'Light, Seen Again — Speech-aware chamber',
      'composition_source_sha256':bound_sources[str(Path(__file__).resolve())],
      'editorial_direction':'Existing motif/chord attacks placed locally within 0.9 second into clearer spoken phrases, without crossing notes or authored rests; bounded static weak-support voicing, unchanged licensed samples. Fresh slow automation and unchanged per-window audit required. Human listening pending.'})
    result['speech_aware_placement']=changes;result['narration_sha256']=before
    require_source_bindings(bound_sources)
    result['bound_source_sha256']=bound_sources
    result['helper_editorial_source_sha256']=bound_sources[str(Path(editorial_score.__file__).resolve())]
    result['helper_base_source_sha256']=bound_sources[str(Path(base.__file__).resolve())]
    if hashlib.sha256(voice_path.read_bytes()).hexdigest()!=before:raise ValueError('Narration changed during source repair')
    path.with_suffix('.provenance.json').write_text(json.dumps(result,indent=2));return result
