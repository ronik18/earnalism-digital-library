"""Actual-word overlap context for music flags; never a listening verdict."""
import math

def interval_gap(voice, music, intervals, rate):
 """Energy ratio on the union of supplied actual-word intervals, excluding gaps."""
 if rate<=0:raise ValueError('Positive sample rate required')
 spans=[]
 for start,end in intervals:
  if not (0<=start<end) or int(end*rate)>min(len(voice),len(music)):
   raise ValueError('Word interval is empty or outside aligned stems')
  lo,hi=int(start*rate),int(end*rate)
  if hi<=lo:raise ValueError('Word interval has no samples')
  spans.append((lo,hi))
 if not spans:raise ValueError('At least one actual-word interval required')
 merged=[]
 for lo,hi in sorted(spans):
  if merged and lo<=merged[-1][1]:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
  else:merged.append((lo,hi))
 ve=be=0.;count=0
 for lo,hi in merged:
  ve+=sum(x*x for x in voice[lo:hi]);be+=sum(x*x for x in music[lo:hi]);count+=hi-lo
 return {'gap_db':round(10*math.log10(ve/be),2) if ve>0 and be>0 else None,'word_samples':count,'music_zero':be==0,'voice_zero':ve==0}


def flag_context(voice, music, flags, words, rate, window_seconds=1):
 """Keep original flags separate from within-word measurements; never resolve them."""
 if window_seconds<=0:raise ValueError('Positive window required')
 rows=[]
 for flag in flags:
  start=float(flag['start']);end=start+window_seconds
  if start<0 or int(end*rate)>min(len(voice),len(music)):raise ValueError('Flag outside aligned stems')
  matched=[w for w in words if min(end,w['end'])>max(start,w['start'])]
  spans=[(max(start,w['start']),min(end,w['end'])) for w in matched]
  context=interval_gap(voice,music,spans,rate) if spans else {'gap_db':None,'word_samples':0,'music_zero':None,'voice_zero':None}
  context.update(coverage_fraction=round(context['word_samples']/(rate*window_seconds),4),words=' '.join(w['word'] for w in matched))
  rows.append({'original_flag':dict(flag),'word_context':context,'listening_status':'UNRESOLVED'})
 return rows
