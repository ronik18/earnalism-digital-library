"""Restrained written-note orchestration; no voice input or added recordings."""
from pathlib import Path
import copy,hashlib,math
from final_chamber_score import compose as chamber_compose,ASSETS
VERSION='moon-score-v12-editorial-orchestration'
PALETTE='acoustic_editorial_v12'
NEAR_PRINCIPAL_SECONDS=.3
SUPPORT_TRIM_DB=-2.0
CYCLE_A4_TRIM_DB=-1.0

def adjust_events(events,scenes=()):
 """Leave timing, notes and silences intact; trim only identified collisions."""
 result=copy.deepcopy(events)
 principal=[e['time'] for e in result if e['phrase']!='soft harmonic support']
 for e in result:
  if 'arrangement_gain_db' not in e:raise ValueError('Base written dynamics must precede editorial orchestration')
  delta=0.0;reason=None
  if e['phrase']=='soft harmonic support' and any(abs(e['time']-t)<NEAR_PRINCIPAL_SECONDS for t in principal):
   delta=SUPPORT_TRIM_DB;reason='Support attack within 300 ms of a principal motif or reveal'
  elif e['phrase']=='return: F E A D' and e['instrument']=='piano' and e['midi']==69:
   delta=CYCLE_A4_TRIM_DB;reason='Restrain the cycle A4 lead during explanatory speech'
  if delta:
   e['arrangement_gain_db']+=delta;e['editorial_gain_db']=delta;e['editorial_reason']=reason
 return result

def compose(path,seconds,quiet_intervals=(),rate=24000,scenes=(),asset_root=ASSETS,speech_intervals=()):
 """Compose a new accompaniment only, with bounded source-event dynamics.

 Same source instruments, phrase plan, silence envelopes and -34 LUFS score
 target as the base composer. No narration is read or changed; speech_intervals
 carry timestamps only. Full mix and human listening checks remain mandatory.
 """
 return chamber_compose(path,seconds,quiet_intervals,rate,scenes,asset_root,speech_intervals,
  event_adjuster=adjust_events,
  provenance_overrides={'version':VERSION,'title':'Light, Seen Again — Editorial chamber',
   'composition_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
   'editorial_direction':'Preserve D A E F / F E A D identity and authored silence. Trim accompaniment attacks within 300 ms of principal events by 2 dB, and the returning A4 lead by 1 dB. No new assets, notes, timing, global gain boost or voice processing. Listening and resemblance review pending.'})
