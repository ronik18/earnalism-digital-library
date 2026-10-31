from pathlib import Path
import numpy as np,subprocess as s,json,hashlib,wave
D=Path(__file__).parent
parent=Path('/tmp/earnalism-audiobook-recovery-followup-20261031/sredni-retained.mp3')
def decode(p):return s.check_output(['ffmpeg','-v','error','-i',str(p),'-ac','1','-ar','24000','-f','s16le','-'])
def save(name,b):
 with wave.open(str(D/name),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b)
a=decode(parent);b=decode(D/'replacement-canonical.wav');x=np.frombuffer(a,dtype='<i2');y=np.frombuffer(b,dtype='<i2');start=round(149.59*24000);end=round(158.075*24000)
# Entire sentence, quiet mid-pause boundaries. Retain original decoded PCM outside those boundaries.
# New audio includes 0.339s ending pause; retaining parent suffix adds 0.238s before next speech.
# A 0.15s lead-in avoids a shortened preceding sentence pause; no healthy speech is faded.
old=x[start:end].astype(float);new=y.astype(float)
active_old=old[np.abs(old)>260];active_new=new[np.abs(new)>260]
rms=lambda v:float(np.sqrt(np.mean(v*v)))
gain=rms(active_old)/rms(active_new)
assert .5<gain<2
z=np.rint(np.clip(new*gain,-32768,32767)).astype('<i2');assert np.max(np.abs(z.astype(float)))<32767
insert=bytes(7200)+z.tobytes();candidate=a[:2*start]+insert+a[2*end:]
assert candidate[:2*start]==a[:2*start] and candidate[2*start+len(insert):]==a[2*end:]
save('candidate-private.wav',candidate)
lo=round(144.0*24000);hi=round((158.075+9)*24000);save('both-joins-review.wav',a[2*lo:2*start]+insert+a[2*end:2*hi])
rec={'status':'PRIVATE_DRAFT_NOT_QUALIFIED','parent_sha256':hashlib.sha256(parent.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256((D/'candidate-private.wav').read_bytes()).hexdigest(),'replacement_raw_sha256':hashlib.sha256((D/'replacement.wav').read_bytes()).hexdigest(),'decoded_healthy_prefix_sha256':hashlib.sha256(a[:2*start]).hexdigest(),'decoded_healthy_suffix_sha256':hashlib.sha256(a[2*end:]).hexdigest(),'healthy_prefix_suffix_bitwise_preserved':True,'edit_start_seconds':149.59,'edit_end_seconds':158.075,'cut_basis':'Measured -42dB silence:149.172–150.011708 and157.83925–158.312875','gain_applied_replacement_only':gain,'added_leading_silence_seconds':.15,'duration_delta_seconds':len(insert)/48000-(end-start)/24000,'candidate_seconds':len(candidate)/48000,'no_time_stretch':True,'no_music_added':True,'both_joins_listening':'UNVERIFIED','voice_continuity':'UNVERIFIED','full_title_gate':'BLOCKED','publication':False}
(D/'splice-evidence.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec,indent=2))
