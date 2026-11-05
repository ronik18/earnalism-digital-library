"""Fail closed on missing or silently truncated audio-model coverage."""
import math

def verify_coverage(duration,windows,input_limit,tolerance=.001):
 if not (math.isfinite(duration) and duration>0 and input_limit>0):raise ValueError('Positive finite duration and input limit required')
 spans=[]
 for row in windows:
  a,b=float(row['start']),float(row['end'])
  if not (math.isfinite(a) and math.isfinite(b) and 0<=a<b<=duration+tolerance):raise ValueError('Invalid review window')
  if b-a>input_limit+tolerance:raise ValueError('Review window exceeds model input limit')
  spans.append((a,b))
 if not spans:raise ValueError('No actual audio exposure windows')
 covered=0.
 for a,b in sorted(spans):
  if a>covered+tolerance:raise ValueError('Unreviewed gap in soundtrack')
  covered=max(covered,b)
 if covered<duration-tolerance:raise ValueError('Soundtrack ending not covered')
 return {'source_seconds':duration,'covered_union_seconds':min(covered,duration),'window_count':len(spans),'input_limit_seconds':input_limit,'interpretation':'Input coverage only, not a listening result or human approval'}
