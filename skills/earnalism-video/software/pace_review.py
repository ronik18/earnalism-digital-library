"""Measured pacing diagnostics from actual-audio ASR; never grants listening approval."""
import re,statistics,hashlib,pathlib,math

def review(record,wav,text,policy):
 if record['audio_sha256']!=hashlib.sha256(pathlib.Path(wav).read_bytes()).hexdigest():raise ValueError('Stale pacing alignment')
 words=record.get('word_times',[])
 if not words:raise ValueError('Actual word times required for pacing review')
 if any(w['end']<w['start'] for w in words):raise ValueError('Invalid word times')
 duration=words[-1]['end']-words[0]['start']
 if duration<=0:raise ValueError('Invalid spoken duration')
 rate=len(text.split())*60/duration;pauses=[];sentences=[];begin=0
 for i,w in enumerate(words):
  if i:
   gap=w['start']-words[i-1]['end'];limit=policy.get('max_between_words_pause_seconds',.9)
   # Decimal ASR times can subtract to limit+3e-16; that is not a real overage.
   if gap>limit and not math.isclose(gap,limit,rel_tol=0,abs_tol=1e-9):pauses.append({'after':words[i-1]['word'],'before':w['word'],'seconds':round(gap,3),'sentence_boundary':bool(re.search(r'[.!?]$',words[i-1]['word']))})
  if re.search(r'[.!?]$',w['word']) or i==len(words)-1:
   seconds=w['end']-words[begin]['start']
   if seconds>0:sentences.append({'words':i-begin+1,'seconds':round(seconds,3),'wpm':round((i-begin+1)*60/seconds,1)})
   begin=i+1
 flags=[]
 if not policy.get('minimum_wpm',110)<=rate<=policy.get('maximum_wpm',140):flags.append('Overall pace outside target band')
 if any(not p['sentence_boundary'] for p in pauses):flags.append('Long pause inside a sentence: listen and inspect')
 canonical=canonical_sentence_rates(record.get('display_word_times',words),text)
 if canonical is None:flags.append('Canonical sentence timing unavailable: inspect transcript alignment')
 else:sentences=canonical
 short_items=[{**v,'requires_listening':True,'outside_general_band':not policy.get('minimum_wpm',110)<=v['wpm']<=policy.get('maximum_wpm',140),'note':'Short-phrase WPM is timing-sensitive; retain purposeful emphasis but review explicitly.'} for v in sentences if v['words']<6]
 if any(v['outside_general_band'] for v in short_items):flags.append('Short-sentence pace needs explicit listening review')
 meaningful=[v['wpm'] for v in sentences if v['words']>=6]
 if len(meaningful)>1 and max(meaningful)/min(meaningful)>policy.get('max_sentence_rate_ratio',1.35):flags.append('Large within-take sentence-rate variation: listen and inspect')
 return {'spoken_wpm':round(rate,1),'target_wpm':policy.get('target_wpm',125),'sentence_rates':sentences,'sentence_timing_basis':'Canonical script boundaries mapped to actual-audio word times','long_pauses':pauses,'short_sentence_review_items':short_items,'flags':flags,'human_listening_required':True,'note':'ASR timing is approximate. Consistent overall tempo should retain natural phrasing, not equal duration for every word.'}

def compare_scene_rates(reports,maximum_deviation=.12):
 rates=[r['spoken_wpm'] for r in reports];median=statistics.median(rates)
 return {'median_wpm':median,'deviations':[round(abs(r/median-1),4) for r in rates],'consistent':all(abs(r/median-1)<=maximum_deviation for r in rates)}

def canonical_sentence_rates(words,text):
 """Keep ASR punctuation from hiding sentence-level pace changes."""
 from asr_review import tokens
 from delivery_conform import sentences
 flattened=[]
 for word in words:
  for token in tokens(word['word']):flattened.append((token,word['start'],word['end']))
 if [v[0] for v in flattened]!=tokens(text):return None
 cursor=0;rates=[]
 for phrase in sentences(text):
  n=len(tokens(phrase));span=flattened[cursor:cursor+n];cursor+=n;seconds=span[-1][2]-span[0][1]
  if seconds>0:rates.append({'text':phrase,'words':len(phrase.split()),'seconds':round(seconds,3),'wpm':round(len(phrase.split())*60/seconds,1)})
 return rates
