"""Auditable ASR review decisions. Raw recognition is retained, not replaced by script."""
import re,json,hashlib,pathlib

_EXACT_DECIMAL_HALF=re.compile(r'(?<![\w.+−-])29(?:\.5|[ \t]+\.5)(?![\w%]|\.\d)')

def tokens(text):
 # Only these exact ASR decimal displays mean the existing spoken phrase.
 # Do not infer arbitrary decimals, precision variants, signs or percentages.
 def decimal(match):
  if re.search(r'[-+−]\s*$',text[:match.start()]) or re.match(r'\s*%',text[match.end():]):return match.group()
  return 'twenty nine and a half'
 text=_EXACT_DECIMAL_HALF.sub(decimal,text.lower())
 result=[]
 for word in re.findall(r'[a-z0-9]+',text.lower()):result.extend(['twenty','nine'] if word=='29' else [word])
 return result

def resolve_numeric(record,expected,audio):
 if hashlib.sha256(pathlib.Path(audio).read_bytes()).hexdigest()!=record['audio_sha256']:raise ValueError('Stale ASR audio binding')
 if tokens(record['recognized'])!=tokens(expected):raise ValueError('Not a number-format-only difference')
 if 'word_times' in record and tokens(' '.join(w['word'] for w in record['word_times']))!=tokens(expected):raise ValueError('Not a number-format-only difference in raw word evidence')
 result={**record,'unresolved_asr_edits':[],'resolved_asr_edits':record.get('unresolved_asr_edits',[]),'resolution_status':'resolved_number_format','resolution':{'method':'Exact token equality after 29 -> twenty nine or exact 29.5 / 29 .5 -> twenty nine and a half display normalization only; no pronunciation decision','audio_unchanged':True,'raw_recognition_and_word_times_retained':True},'human_listening_required':True}
 # Merge only the exact adjacent numeric display. Its outer times are real
 # ASR boundaries; never invent timings for five expanded spoken words.
 words=record.get('display_word_times',record.get('word_times',[]));display=[];i=0;merged=False
 while i<len(words):
  if i+1<len(words) and words[i]['word']=='29' and words[i+1]['word']=='.5' and words[i]['start']<=words[i]['end']<=words[i+1]['start']<=words[i+1]['end']:
   display.append({'word':'29.5','start':words[i]['start'],'end':words[i+1]['end']});i+=2;merged=True
  else:display.append(words[i]);i+=1
 if merged:result['display_word_times']=display
 return result

def brand_tokens(text):
 text=re.sub(r'\bearn[ -]+al[ -]*(?:iz[ -]*um|ism)\b','Earnalism',text,flags=re.I)
 text=re.sub(r'\bearn[ -]+alism\b','Earnalism',text,flags=re.I)
 text=re.sub(r'\bernalism\b','Earnalism',text,flags=re.I)
 return tokens(text)

def resolve_brand(record,expected,audio,phonetic):
 digest=hashlib.sha256(pathlib.Path(audio).read_bytes()).hexdigest()
 if record['audio_sha256']!=digest or phonetic['audio_sha256']!=digest:raise ValueError('Stale pronunciation evidence')
 if not re.search(r'n\s+æ\s+l',phonetic['phonetic_labels']):raise ValueError('Requested AL vowel not verified')
 if brand_tokens(record['recognized'])!=brand_tokens(expected):raise ValueError('Unresolved words beyond brand spelling')
 return {**record,'unresolved_asr_edits':[],'resolved_asr_edits':record.get('unresolved_asr_edits',[]),'resolution_status':'resolved_brand_pronunciation_and_spelling','resolution':{'target':'EARN-AL-iz-um; AL as in alphabet','phonetic_labels':phonetic['phonetic_labels'],'phonetic_model':phonetic['model'],'phonetic_revision':phonetic['revision'],'audio_range':phonetic['range'],'method':'Requested AL vowel detected in brand excerpt; remaining script matches after explicit brand-spelling normalization','owner_listening_approval':'pending'},'human_listening_required':True}

def brand_display_captions(record):
 """Canonical brand spelling over its actual recognized word span, after phonetic review."""
 if record.get('resolution_status')!='resolved_brand_pronunciation_and_spelling':raise ValueError('Pronunciation review required before caption normalization')
 words=record['word_times'];world=next(i for i,w in enumerate(words) if w['word'].lower().strip('.,')=='world');see=next(i for i,w in enumerate(words) if i>world and w['word'].lower().strip('.,')=='see')
 if see<=world+1:raise ValueError('Missing recognized brand span')
 span=words[world+1:see];display=words[:world+1]+[{'word':'Earnalism.','start':span[0]['start'],'end':span[-1]['end']}]+words[see:]
 chunks=[];chunk=[]
 for w in display:
  if chunk and (w['start']-chunk[-1]['end']>.35 or len(chunk)>=7):chunks.append(chunk);chunk=[]
  chunk.append(w)
  if w['word'].endswith(('.', '?','!')):chunks.append(chunk);chunk=[]
 if chunk:chunks.append(chunk)
 return {**record,'raw_cues':record['cues'],'display_word_times':display,'cues':[{'start':c[0]['start'],'end':c[-1]['end'],'text':' '.join(w['word'] for w in c)} for c in chunks]}

def resolve_disk_spelling(record,expected,audio):
 """Disc/disk are orthographic variants for this lunar disk, not spoken-word edits."""
 digest=hashlib.sha256(pathlib.Path(audio).read_bytes()).hexdigest()
 if record.get('audio_sha256')!=digest:raise ValueError('Stale ASR audio binding')
 edits=record.get('unresolved_asr_edits',[])
 if not edits or any(e.get('tag')!='replace' or e.get('reference')!=['disk'] or e.get('recognized')!=['disc'] for e in edits):raise ValueError('Not solely disc/disk spelling')
 raw=tokens(record['recognized']);reference=tokens(expected)
 if ['disk' if w=='disc' else w for w in raw]!=reference:raise ValueError('Unrelated speech difference')
 display=[dict(w,word=re.sub(r'\bdisc\b','disk',w['word'],flags=re.I)) for w in record['word_times']]
 return {**record,'unresolved_asr_edits':[],'resolved_asr_edits':edits,'display_word_times':display,'resolution_status':'resolved_lunar_disk_spelling','resolution':{'method':'Only lunar disc -> disk orthographic variants; every other token matches','audio_sha256':digest,'raw_recognition_and_word_times_retained':True},'human_listening_required':True}

def resolve_viewpoint_compound(record,expected,audio):
 """Resolve only view point -> viewpoint tokenization and exact 29 formatting."""
 digest=hashlib.sha256(pathlib.Path(audio).read_bytes()).hexdigest()
 if record.get('audio_sha256')!=digest:raise ValueError('Stale ASR audio binding')
 edits=record.get('unresolved_asr_edits',[])
 allowed=lambda e:e.get('tag')=='replace' and ((e.get('reference')==['viewpoint'] and e.get('recognized')==['view','point']) or (e.get('reference')==['twenty','nine'] and e.get('recognized')==['29']))
 if not edits or not all(allowed(e) for e in edits):raise ValueError('Not solely viewpoint compound/number formatting')
 raw=tokens(record['recognized']);joined=[];i=0
 while i<len(raw):
  if raw[i:i+2]==['view','point']:joined.append('viewpoint');i+=2
  else:joined.append(raw[i]);i+=1
 if joined!=tokens(expected):raise ValueError('Unrelated spoken-word difference')
 words=record['word_times'];display=[];i=0
 while i<len(words):
  if i+1<len(words) and re.sub(r'[^a-z]','',words[i]['word'].lower())=='view' and re.sub(r'[^a-z]','',words[i+1]['word'].lower())=='point':
   display.append({'word':'viewpoint'+''.join(re.findall(r'[^a-zA-Z]+$',words[i+1]['word'])),'start':words[i]['start'],'end':words[i+1]['end']});i+=2
  else:display.append(words[i]);i+=1
 return {**record,'unresolved_asr_edits':[],'resolved_asr_edits':edits,'display_word_times':display,'resolution_status':'resolved_viewpoint_compound_and_number_format','resolution':{'method':'Exact viewpoint compound tokenization and 29 -> twenty nine equivalence only; every other normalized token matches','audio_sha256':digest,'raw_recognition_and_word_times_retained':True},'human_listening_required':True}

def require_script_match(record,expected):
 """Fail closed on stale text even when audio SHA and edits=[] still match.
 Only exact 29 -> twenty nine, literal 29.5 / 29 .5 -> twenty nine and a half,
 and existing disk/viewpoint orthographic equivalences apply. Decimal display
 spans remain actual ASR spans; expanded tokens do not invent spoken-word times.
 raw recognition and actual word spans must both support the current script.
 """
 if record.get('unresolved_asr_edits'):raise ValueError('Unresolved semantic ASR differences')
 reference=tokens(expected)
 def canonical(words):
  words=['disk' if w=='disc' else w for w in words];out=[];i=0
  while i<len(words):
   if words[i:i+2]==['view','point']:out.append('viewpoint');i+=2
   else:out.append(words[i]);i+=1
  return out
 raw=record.get('word_times',[])
 display=record.get('display_word_times',raw)
 if not reference or not raw or not record.get('recognized'):raise ValueError('Complete actual-audio transcript required')
 for values in [tokens(record['recognized']),tokens(' '.join(w['word'] for w in raw))]:
  if canonical(values)!=canonical(reference):raise ValueError('Current script does not match recognized audio')
 if tokens(' '.join(w['word'] for w in display))!=reference:raise ValueError('Caption words do not match current script')
 return True
