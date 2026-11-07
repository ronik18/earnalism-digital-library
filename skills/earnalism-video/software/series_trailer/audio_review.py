"""Local PCM splice diagnostics. Measurements never substitute for listening."""
import array, hashlib, json, math, wave
from pathlib import Path

def pcm(path):
    with wave.open(str(path)) as w:
        if w.getsampwidth()!=2 or w.getcomptype()!='NONE':
            raise ValueError('Expected uncompressed signed 16-bit PCM')
        return array.array('h',w.readframes(w.getnframes())),w.getframerate(),w.getnchannels()

def db(value):
    return round(20*math.log10(value/32768),3) if value else None

def rms(a):
    return math.sqrt(sum(x*x for x in a)/len(a)) if a else 0

def splice(a,rate,channels,time):
    i=round(time*rate)*channels
    if i<channels or i+channels>len(a):raise ValueError('Join outside signal')
    width=round(.2*rate)*channels
    jump=max(abs(a[i+c]-a[i-channels+c]) for c in range(channels))
    return {'seconds':time,'sample_jump_dbfs':db(jump),
            'before_200ms_rms_dbfs':db(rms(a[max(0,i-width):i])),
            'after_200ms_rms_dbfs':db(rms(a[i:i+width]))}

def review(root):
    root=Path(root);plan=json.loads((root/'edit-plan.json').read_text())
    a,rate,ch=pcm(root/'narration.wav')
    result={'scope':'PCM splice and preservation diagnostics only; no perceptual PASS',
            'joins':[splice(a,rate,ch,c['trailer_start']) for c in plan['clips'][1:]],
            'static_gain_integrity':[],'listening':'PENDING'}
    gains=json.loads((root/'voice-level-review.json').read_text())['rows']
    for row in gains:
        raw=root/(row['clip']+'.wav');derived=root/(row['clip']+'-levelled.wav')
        x,r,c=pcm(raw);y,rr,cc=pcm(derived)
        assert (r,c,len(x))==(rr,cc,len(y)),'Voice sample count/format changed'
        assert hashlib.sha256(raw.read_bytes()).hexdigest()==row['source_sha256']
        gain=10**(row['static_gain_db']/20)
        error=max(abs(v-u*gain) for u,v in zip(x,y))
        assert error<=1.1,'Unexpected alteration beyond static gain and PCM rounding'
        result['static_gain_integrity'].append({'clip':row['clip'],'max_error_pcm_units':round(error,4),'same_sample_count':True})
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('output');args=parser.parse_args()
    target=Path(args.output)
    if target.exists():raise FileExistsError('Refusing overwrite: '+str(target))
    target.write_text(json.dumps(review(args.root),indent=2)+'\n')
    print(target)
