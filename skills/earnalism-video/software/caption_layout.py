"""Phrase captions from immutable actual-audio word times. No fabricated word timing."""
import re

def quality(cues):
 issues=[];last=0
 for i,c in enumerate(cues):
  seconds=c['end']-c['start'];text=c['text'].strip()
  if c['start']<last or seconds<=0 or not text:issues.append(f'{i}: invalid timing/text')
  if seconds<1:issues.append(f'{i}: duration below one second')
  if len(text)>72:issues.append(f'{i}: more than 72 characters')
  if seconds>0 and len(text)/seconds>22:issues.append(f'{i}: above 22 characters/second')
  last=c['end']
 return issues

def punctuate(words,script):
 """Restore punctuation/case only when every corresponding lexical word matches."""
 expected=script.replace('—','— ').split()
 norm=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
 if len(expected)==len(words) and all(norm(a)==norm(b['word']) for a,b in zip(expected,words)):
  return [dict(w,word=text) for w,text in zip(words,expected)]
 return words

def compose(words):
 if not words:raise ValueError('Actual word times required')
 n=len(words);best={n:(0,[])}
 for i in range(n-1,-1,-1):
  for j in range(i+1,min(n,i+14)+1):
   if j not in best:continue
   text=' '.join(w['word'].strip() for w in words[i:j]).replace('— ','—');start=words[i]['start'];end=words[j-1]['end'];seconds=end-start
   if seconds<1 or len(text)>72 or len(text)/seconds>22:continue
   penalty=abs(seconds-3)*.3
   penalty+=max(0,1-seconds)*100+max(0,len(text)/seconds-22)*10
   if not re.search(r'[.!?]$',text):penalty+=1 if re.search(r'[,;:]$',text) else 4
   if re.search(r'[.!?]\s',text):penalty+=5
   if words[j-1]['word'].lower().strip('.,') in {'a','the','of','to','and','is','its','by','from','when','because','while','if','that','as','but','or','with'}:penalty+=8
   cost=penalty+best[j][0]
   if i not in best or cost<best[i][0]:best[i]=(cost,[{'start':start,'end':end,'text':text}]+best[j][1])
 if 0 not in best:raise ValueError('No caption partition meets readability constraints')
 cues=best[0][1]
 if quality(cues):raise ValueError('Caption readability requires review: '+str(quality(cues)))
 return cues
