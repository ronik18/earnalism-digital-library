"""Replay an existing cleared acoustic arrangement on a new narration timeline.

Only note attacks and authored-rest endpoints are retimed. Instruments, pitches,
velocities, voicing, chord strum offsets and natural note decays are preserved.
No processed music is stretched and no default composition planner is rerun.
"""
from pathlib import Path
import array,bisect,copy,hashlib,json,math,subprocess,sys
import final_chamber_score as base

VERSION='moon-score-v14-preserved-arrangement-retime'
ROOT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def timeline_map(old_scenes,new_scenes,anchor_pairs=()):
    """Build a positive, bounded, piecewise-linear semantic timeline map."""
    if not old_scenes or [s['id'] for s in old_scenes]!=[s['id'] for s in new_scenes]:raise ValueError('Same ordered scene identities required')
    for rows in (old_scenes,new_scenes):
        end=0.0
        for scene in rows:
            if not isinstance(scene.get('start'),(int,float)) or not isinstance(scene.get('end'),(int,float)) or not math.isfinite(scene['start']+scene['end']) or abs(scene['start']-end)>1e-5 or scene['end']<=scene['start']:raise ValueError('Contiguous complete narration scenes required')
            end=scene['end']
    points=[]
    for old,new in zip(old_scenes,new_scenes):
        if old.get('text')!=new.get('text'):raise ValueError('Preserved arrangement requires unchanged spoken scene text')
        for scene in [old,new]:
            if not all(isinstance(scene[k],(int,float)) and math.isfinite(scene[k]) for k in ['start','end']) or not 0<=scene['start']<scene['end']:raise ValueError('Invalid narration scene bounds')
        points.extend([{'old':old['start'],'new':new['start'],'label':old['id']+':start'}, {'old':old['end'],'new':new['end'],'label':old['id']+':end'}])
        oa=old.get('anchors',[]);na=new.get('anchors',[])
        if [{k:v for k,v in a.items() if k!='time'} for a in oa]!=[{k:v for k,v in a.items() if k!='time'} for a in na]:raise ValueError('Actual-word anchor identities changed')
        for i,(a,b) in enumerate(zip(oa,na)):
            if not old['start']<=a['time']<=old['end'] or not new['start']<=b['time']<=new['end']:raise ValueError('Word anchor outside its scene')
            points.append({'old':a['time'],'new':b['time'],'label':old['id']+':'+str(i)+':'+a.get('phrase','word')})
    for p in anchor_pairs:
        if not isinstance(p,dict) or not isinstance(p.get('label'),str) or not p['label'].strip():raise ValueError('Labeled actual-audio extra anchor pair required')
        points.append({k:p[k] for k in ['old','new','label']})
    points.sort(key=lambda p:p['old']);result=[]
    for p in points:
        if any(not isinstance(p[k],(int,float)) or not math.isfinite(p[k]) for k in ['old','new']):raise ValueError('Finite timeline anchors required')
        if not old_scenes[0]['start']<=p['old']<=old_scenes[-1]['end'] or not new_scenes[0]['start']<=p['new']<=new_scenes[-1]['end']:raise ValueError('Anchor outside narration timeline')
        if result and abs(p['old']-result[-1]['old'])<1e-7:
            if abs(p['new']-result[-1]['new'])>1e-5:raise ValueError('Conflicting timeline anchors')
            continue
        result.append(p)
    for a,b in zip(result,result[1:]):
        slope=(b['new']-a['new'])/(b['old']-a['old'])
        if not .5<=slope<=2:raise ValueError('Retiming requires a positive local timeline scale within 0.5–2')
    return result

def map_time(time,points):
    if not isinstance(time,(int,float)) or not math.isfinite(time) or time<points[0]['old']-1e-6 or time>points[-1]['old']+1e-6:raise ValueError('Time outside mapped narration')
    index=max(0,min(len(points)-2,bisect.bisect_right([p['old'] for p in points],time)-1));a,b=points[index:index+2]
    return a['new']+(time-a['old'])*(b['new']-a['new'])/(b['old']-a['old'])

def preserve_events(events,points,seconds):
    if not events:raise ValueError('Source event inventory required')
    output=[];changes=[];group_start=None;group_new=None;previous=None
    for i,event in enumerate(events):
        if previous is not None and event['time']<previous['time']:raise ValueError('Source events must be ordered')
        same=previous is not None and event['phrase']==previous['phrase'] and event['instrument']==previous['instrument'] and event['time']-previous['time']<.25
        if not same:group_start=event['time'];group_new=map_time(group_start,points)
        edited=copy.deepcopy(event);edited['time']=round(group_new+event['time']-group_start,6)
        if not 0<=edited['time']<seconds-.4:raise ValueError('Retimed event outside narration body')
        if output and edited['time']<output[-1]['time']:raise ValueError('Fixed chord strum would reorder events; inspect semantic timing')
        output.append(edited);changes.append({'index':i,'old_time':event['time'],'new_time':edited['time'],'phrase':event['phrase'],'instrument':event['instrument'],'midi':event['midi']});previous=event
    if [{k:v for k,v in e.items() if k!='time'} for e in output]!=[{k:v for k,v in e.items() if k!='time'} for e in events]:raise ValueError('Retiming changed musical content')
    return output,changes

def map_intervals(intervals,points):
    output=[]
    for a,b in intervals:
        if not 0<=a<b:raise ValueError('Invalid source rest')
        output.append([round(map_time(a,points),6),round(map_time(b,points),6)])
    return output

def covered(interval,rests):
    a,b=interval;cursor=a
    for left,right in sorted(rests):
        if right<cursor:continue
        if left>cursor+1e-5:return False
        cursor=max(cursor,right)
        if cursor>=b-1e-5:return True
    return False

def _verify_parent(parent):
    manifest=load(parent/'delivery-manifest.json')
    if not manifest or any(Path(n).name!=n or sha(parent/n)!=digest for n,digest in manifest.items()):raise ValueError('Parent arrangement delivery changed')
    prov=load(parent/'score.provenance.json')
    if prov.get('recording_sha256')!=sha(parent/'score.wav') or prov.get('kind')!='original acoustic chamber composition' or prov.get('external_compositions'):raise ValueError('Unbound or unsupported parent composition')
    for name,digest in prov.get('stems',{}).items():
        if Path(name).name!=name or sha(parent/name)!=digest:raise ValueError('Parent music stem changed')
    return manifest,prov

def compose(path,seconds,quiet_intervals=(),rate=24000,scenes=(),asset_root=base.ASSETS,speech_intervals=(),palette='acoustic_editorial_v12',*,parent_folder=None,anchor_pairs=()):
    """Drop-in composer: functools.partial(compose,parent_folder=old_candidate).

    The returned provenance includes mapped_combined_gain_plan. Replay that plan
    only from a freshly ducked stem using music_automation's validated override;
    a changed narration still needs new balance, silence and listening checks.
    """
    if parent_folder is None:raise ValueError('An explicit immutable parent arrangement is required')
    if palette not in ('acoustic_editorial_v12','acoustic_speech_aware_v13','acoustic_preserved_retime_v14'):raise ValueError('Unsupported parent acoustic palette')
    path=Path(path);parent=Path(parent_folder).resolve()
    if path.exists():raise FileExistsError(path)
    if rate!=24000 or not math.isfinite(seconds) or seconds<=0:raise ValueError('Use the source 24kHz acoustic recipe and positive duration')
    manifest,old=_verify_parent(parent);old_props=load(parent/'props.json');points=timeline_map(old_props['scenes'],scenes,anchor_pairs)
    if abs(seconds-scenes[-1]['end'])>.001:raise ValueError('Duration differs from actual narration timeline')
    events,mapping=preserve_events(old['events'],points,seconds);quiet=map_intervals(old['quiet_intervals'],points)
    if any(not covered(q,quiet) for q in quiet_intervals):raise ValueError('Caller requested a new or extended rest; preserve or explicitly review the arrangement')
    expected_base=old.get('helper_base_source_sha256',old.get('base_composition_source_sha256'))
    if expected_base!=sha(base.__file__):raise ValueError('Parent acoustic rendering recipe differs from the retained base source')
    assets=base.validate_assets(asset_root)
    if old.get('asset_manifest_sha256')!=sha(Path(asset_root)/'manifest.json') or any(row not in assets['samples'] for row in old.get('third_party_samples',[])):raise ValueError('Parent sample license inventory changed')
    bound={str(Path(__file__).resolve()):sha(__file__),str(Path(base.__file__).resolve()):sha(base.__file__)}
    voice=path.parent/'narration.wav';voice_hash=sha(voice)
    size=round(seconds*rate)*2;stems={k:array.array('f',[0.])*size for k in ('piano','harp')};cache={};used={}
    for event in events:
        key=(event['instrument'],event['midi'])
        if key not in cache:
            row=min((s for s in assets['samples'] if s['instrument']==key[0]),key=lambda s:abs(s['root_midi']-key[1]));shift=key[1]-row['root_midi']
            if abs(shift)>2:raise ValueError('No licensed closely sampled note')
            ratio=2**(shift/12);raw=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(Path(asset_root)/row['file']),'-af',f'aresample={rate},asetrate={rate*ratio},aresample={rate},highpass=f=85,lowpass=f=7000','-ar',str(rate),'-ac','2','-f','f32le','-']))
            if sys.byteorder!='little':raw.byteswap()
            peak=max(abs(x) for x in raw)
            if peak<1e-7:raise ValueError('Silent acoustic sample')
            original_gain=.075/peak;window=raw[:min(len(raw),round(1.2*rate)*2)];energy=math.sqrt(sum(x*x for x in window)/max(1,len(window)))
            gain=max(original_gain*10**(-4/20),min(original_gain*10**(4/20),.014/max(energy,1e-8)));cache[key]=(raw,gain);used[row['file']]=row
        raw,gain=cache[key];start=round(event['time']*rate);frames=min(len(raw)//2,round((event['duration']+.75)*rate),size//2-start)
        pan=event['pan'];lg=math.cos((pan+1)*math.pi/4)*2**.5;rg=math.sin((pan+1)*math.pi/4)*2**.5
        for i in range(frames):
            dt=i/rate;env=min(1,dt/(.24 if event['phrase']=='soft harmonic support' else (.085 if event['instrument']=='piano' else .11)),max(0,(event['duration']+.75-dt)/.75));g=gain*event['velocity']*env*10**(event.get('arrangement_gain_db',0)/20);index=(start+i)*2
            stems[event['instrument']][index]+=raw[i*2]*g*lg;stems[event['instrument']][index+1]+=raw[i*2+1]*g*rg
    for inst,values in stems.items():base._wav(path.with_name('score-'+inst+'.wav'),values,rate)
    from score import quiet_gain
    total=array.array('f',[0.])*size
    for i in range(size//2):
        t=i/rate;g=quiet_gain(t,quiet)*min(1,t/1.5,max(0,(seconds-.4-t)/1.8))
        for c in (0,1):total[i*2+c]=(stems['piano'][i*2+c]+stems['harp'][i*2+c])*g
    raw_path=path.with_name('score-unmastered.wav');base._wav(raw_path,total,rate)
    subprocess.run(['ffmpeg','-v','error','-n','-i',str(raw_path),'-af','loudnorm=I=-34:TP=-9:LRA=10','-ar',str(rate),'-ac','2','-c:a','pcm_s16le',str(path)],check=True)
    if any(sha(source)!=digest for source,digest in bound.items()) or sha(voice)!=voice_hash:raise ValueError('Narration or composer changed during preserved-score replay')
    _verify_parent(parent)
    result=copy.deepcopy(old);result.update(version=VERSION,title=old.get('title','Preserved chamber arrangement'),source_sha256=sha(ROOT/'score.py'),composition_source_sha256=bound[str(Path(__file__).resolve())],base_composition_source_sha256=bound[str(Path(base.__file__).resolve())],recording_sha256=sha(path),seconds=seconds,quiet_intervals=quiet,events=events,third_party_samples=list(used.values()),stems={n:sha(path.with_name(n)) for n in ['score-piano.wav','score-harp.wav','score-unmastered.wav']},review='Private preserved-arrangement replay; new listening and balance review pending.')
    result['retime']={'method':'Piecewise scene and actual-word-anchor mapping; original samples replayed without time stretching','parent_folder':str(parent),'parent_delivery_manifest_sha256':sha(parent/'delivery-manifest.json'),'parent_score_sha256':sha(parent/'score.wav'),'parent_provenance_sha256':sha(parent/'score.provenance.json'),'parent_version':old['version'],'parent_composition_source_sha256':old['composition_source_sha256'],'timeline_points':points,'event_mapping':mapping,'natural_note_durations_preserved':True,'chord_strum_offsets_preserved':True,'all_non_time_event_fields_preserved':True,'source_events_sha256':canonical(old['events']),'source_rests_sha256':canonical(old['quiet_intervals']),'narration_sha256':voice_hash,'bound_source_sha256':bound}
    if (parent/'music-automation.json').exists():
        result['retime']['mapped_combined_gain_plan']=[dict(k,time=round(map_time(k['time'],points),6)) for k in load(parent/'music-automation.json')['knots']]
        result['retime']['parent_automation_sha256']=sha(parent/'music-automation.json')
    result['retime']['parent_editorial_adjustments']=result.get('editorial_adjustments',[])
    result['editorial_adjustments']=[{'time':e['time'],'midi':e['midi'],'instrument':e['instrument'],'phrase':e['phrase'],'gain_db':e['editorial_gain_db'],'reason':e.get('editorial_reason','Preserved source voicing')} for e in events if e.get('editorial_gain_db')]
    result['retime']['parent_bound_source_sha256']=result.get('bound_source_sha256',{})
    result['bound_source_sha256']=bound
    result['editorial_direction']='Existing source event inventory and written voicing preserved; only attacks and authored rests follow matched scene/word anchors. Natural acoustic decays are replayed without stretching. Fresh balance and listening review required.'
    # Parent placement entries are historical evidence; events above already
    # include them. Never present their old timestamps as new placement actions.
    result['retime']['parent_speech_aware_placement']=result.pop('speech_aware_placement',[])
    path.with_suffix('.provenance.json').write_text(json.dumps(result,indent=2));return result
