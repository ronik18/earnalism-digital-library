"""Actual-scene label key for narrow landscape review; never alters spoken captions."""
def label_timeline(props,profile='moon-phases-v1'):
 # Legacy callers select the lunar implementation explicitly by default. New
 # watch pages pass the actual topic profile; unknown models invent no labels.
 if profile!='moon-phases-v1':return []
 out=[]
 for s in props.get('scenes',[]):
  if s['diagram'] not in ('orbit','phases','cycle'):continue
  start,end=s['start'],s['end'];base='Diagram key: FROM ABOVE · FROM EARTH · Sunlight'
  if s['diagram']=='orbit':
   ground=next((a['time'] for a in s.get('anchors',[]) if a['phrase']=='From the ground'),start)
   landed=min(end,ground+1.95)
   out.extend([{'start':start,'end':landed,'text':'Diagram key: FROM ABOVE · Sunlight'},{'start':landed,'end':end,'text':base}])
  elif s['diagram']=='phases':
   anchors={a['phrase']:a['time'] for a in s.get('anchors',[])}
   half=anchors['At first quarter']+.5;quarter=anchors['First quarter means']+.5;full=anchors['Near full Moon']
   transition=max(quarter,full-.8)
   out.extend([{'start':start,'end':half,'text':base},{'start':half,'end':quarter,'text':'Diagram key: ½ of the visible disk'},{'start':quarter,'end':transition,'text':'Diagram key: ¼ of the cycle → ½ of the visible disk'},{'start':transition,'end':full,'text':base+' · Changing view'},{'start':full,'end':end,'text':'Diagram key: FULL MOON · Almost fully lit'}])
  else:out.append({'start':start,'end':end,'text':base})
 for row in out:row.update(reading_cards(row['text']))
 return out

def reading_cards(text):
 """Readable companion labels outside the raster video; no extra spoken captions."""
 if '¼ of the cycle' in text:
  return {'cards':[{'label':'Cycle position','value':'¼ of the cycle'},{'label':'Earth’s view','value':'½ of the visible disk'}],'note':''}
 if '½ of the visible disk' in text:
  return {'cards':[{'label':'Earth’s view','value':'½ of the visible disk'}],'note':''}
 if 'FULL MOON' in text:
  return {'cards':[{'label':'FULL MOON','value':'Almost fully lit'}],'note':''}
 cards=[{'label':'FROM ABOVE','value':'Orbit diagram'}]
 if 'FROM EARTH' in text:cards.append({'label':'FROM EARTH','value':'Moon seen from Earth'})
 return {'cards':cards,'note':'Sunlight: incoming arrows'+(' · Changing view' if 'Changing view' in text else '')}
