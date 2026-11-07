"""Post-ducking engineering screen; perceptual listening approval stays separate."""
import array,subprocess,math,statistics,sys

def samples(path,rate=24000):
 x=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ar',str(rate),'-ac','1','-f','f32le','-']))
 if sys.byteorder!='little':x.byteswap()
 return x

def analyze(voice,bed,rate=24000):
 if len(voice)!=len(bed):raise ValueError('Music and narration stems must have identical sample counts')
 db=lambda x:20*math.log10(max(1e-12,math.sqrt(sum(v*v for v in x)/max(1,len(x)))))
 rows=[];gaps=[]
 for start in range(0,len(voice),rate):
  v=db(voice[start:start+rate]);b=db(bed[start:start+rate]);active=v>-45 and b>-65
  rows.append({'start':start/rate,'voice_dbfs':round(v,2),'music_dbfs':round(b,2),'active_overlap':active})
  if active:gaps.append(v-b)
 median=statistics.median(gaps) if gaps else None;issues=[]
 if median is None:issues.append('No active voice/music overlap to assess')
 elif not 18<=median<=28:issues.append('Post-ducking median music/voice gap outside 18–28 dB review band')
 passage_issues=[]
 for i,row in enumerate(rows):
  if not row['active_overlap']:continue
  # Retain fade diagnostics, but do not force intentional fade-to-silence into a flat bed.
  fade=any(not r['active_overlap'] and r['music_dbfs']<=-65 for r in rows[max(0,i-1):i+2])
  # A real zero-valued music tail is also a silence boundary. The final
  # analysis window has no following row; do not misclassify its authored fade.
  terminal_silence=i==len(rows)-1 and len(bed)>=rate//4 and max(abs(v) for v in bed[-max(1,rate//4):])<1e-5
  fade=fade or terminal_silence
  row['terminal_music_silence']=terminal_silence
  gap=row['voice_dbfs']-row['music_dbfs'];row['music_below_voice_db']=round(gap,2);row['fade_boundary']=fade
  if not fade and not 16<=gap<=32:passage_issues.append({'start':row['start'],'gap_db':round(gap,2)})
 if passage_issues:issues.append('Individual music passages outside 16–32 dB review band')
 return {'passage_issues':passage_issues,'passage_review_band_db':[16,32],'median_music_below_voice_db':round(median,2) if median is not None else None,'active_overlap_windows':len(gaps),'review_band_db':[18,28],'issues':issues,'windows':rows,'human_listening_required':True,'limitation':'Engineering screen only. Does not certify audibility on every device, musical quality or a perceptually ideal balance. Intentional silent windows excluded.'}

def audit(folder):
 from pathlib import Path
 p=Path(folder);voice=samples(p/'narration.wav');bed=samples(p/'score-ducked.wav');delta=len(voice)-len(bed)
 if abs(delta)>24:raise ValueError('Stems differ by more than one millisecond')
 if delta>0:bed.extend([0.]*delta)
 elif delta<0:voice.extend([0.]*(-delta))
 result=analyze(voice,bed);result['analysis_only_tail_padding_samples']=abs(delta)
 import hashlib
 result['stem_sha256']={name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ['narration.wav','score-ducked.wav']}
 return result
