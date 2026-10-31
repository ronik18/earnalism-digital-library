from pathlib import Path
import wave,json,numpy as np
D=Path(__file__).parent
with wave.open(str(D/'both-joins-review.wav')) as w:x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float);sr=w.getframerate()
rows=[]
for name,t in [('incoming_cut',5.59),('replacement_start_after_padding',5.74),('outgoing_cut',15.34),('review_reported_click',6.02)]:
 i=round(t*sr);r=x[max(0,i-240):i+240];rows.append({'location':name,'clip_seconds':t,'adjacent_sample_jump':float(abs(x[i]-x[i-1])),'within_20ms_peak_dbfs':float(20*np.log10(max(np.max(abs(r)),1)/32768))})
rec={'measurements':rows,'interpretation':'No inference of audible quality from low boundary amplitude. Whole prefix/suffix PCM equality disproves removal of the preceding word by this splice. Automated claims of clipped preceding speech and a 1.5-second pause are not independently established. Reported 6.02-second click falls inside replacement speech, not an edit boundary; do not erase a phoneme on that basis. Abrupt/timbre/expression findings remain unresolved auditory concerns; keep private and BLOCKED.','non_generating_repairs_performed_after_review':False,'reason':'No verified deterministic repair addresses reported emotional flatness or uncertain auditory effects. Both one-request grants are consumed; preserve candidate for qualified listening rather than speculative edits.'}
(D/'critical-review-adjudication.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec,indent=2))
