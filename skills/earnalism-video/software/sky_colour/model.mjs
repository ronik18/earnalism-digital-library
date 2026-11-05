/** Original explanatory geometry. Distances, packet counts and density are
 * deliberately schematic; no quantitative radiative-transfer/air-mass claim. */
export const sceneKinds=['question','scattering','sky_path','prediction','sunset_path','callback'];
export const requiredMarks={question:['question','light'],scattering:['mixed','redirect','shorter','red'],sky_path:['away','toward','direct'],prediction:['lower','longer','predict'],sunset_path:['scatter','warm','identity','mixture'],callback:['variation','sky','direct','callback']};
export const wavelengths=[{id:'violet',nm:405,color:'#b49cff'},{id:'blue',nm:450,color:'#62bfff'},{id:'green',nm:530,color:'#83e0b5'},{id:'amber',nm:590,color:'#ffd37d'},{id:'red',nm:650,color:'#ff7e72'}];
export const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
export function smooth(t,a,b){if(!Number.isFinite(a)||!Number.isFinite(b))return 0;if(b<=a)return t>=a?1:0;const x=clamp((t-a)/(b-a));return x*x*(3-2*x);}
export const mix=(a,b,p)=>a+(b-a)*clamp(p);
export function relativeScattering(nm,reference=550){if(!(Number.isFinite(nm)&&nm>0&&Number.isFinite(reference)&&reference>0))throw Error('Positive wavelengths required');return (reference/nm)**4;}
export function illustrativeTransmission(nm,path){if(!(Number.isFinite(path)&&path>=0))throw Error('Nonnegative schematic path required');return Math.exp(-.16*path*relativeScattering(nm));}
export const atmosphere={cx:520,cy:950,earthRadius:650,outerRadius:780,observer:{x:520,y:300}};
/** Observer→Sun outward ray intersects a fixed concentric shell. Incoming light
 * runs in the reverse direction. No path enters the opaque Earth. */
export function atmosphericPath(elevation,shape=atmosphere){
 if(!Number.isFinite(elevation)||elevation<0||elevation>90)throw Error('Sun elevation must be0–90°');
 const a=elevation*Math.PI/180,d={x:-Math.cos(a),y:-Math.sin(a)},o=shape.observer,q={x:o.x-shape.cx,y:o.y-shape.cy};
 if(Math.abs(Math.hypot(q.x,q.y)-shape.earthRadius)>1e-7||shape.outerRadius<=shape.earthRadius)throw Error('Observer must lie on surface of fixed shell');
 const projection=q.x*d.x+q.y*d.y,discriminant=projection**2+shape.outerRadius**2-shape.earthRadius**2;
 const length=-projection+Math.sqrt(discriminant),entry={x:o.x+length*d.x,y:o.y+length*d.y};
 return {elevation,observer:{...o},entry,length,directionToSun:d,incoming:{x:-d.x,y:-d.y},source:{x:entry.x+95*d.x,y:entry.y+95*d.y},earthRadius:shape.earthRadius,outerRadius:shape.outerRadius};
}
export function pointAlong(path,p){return {x:mix(path.entry.x,path.observer.x,p),y:mix(path.entry.y,path.observer.y,p)};}
export function rayPoint(path,p,distance=1){const v=pointAlong(path,p);return {x:v.x+path.incoming.x*distance,y:v.y+path.incoming.y*distance};}
export function elevationAt(t,marks){return mix(68,7,smooth(t,marks.lower??Infinity,marks.longer??Infinity));}
export function gazeGeometry(portrait=false){const source=portrait?{x:80,y:120}:{x:130,y:120},observer=portrait?{x:370,y:630}:{x:400,y:630},patch=portrait?{x:720,y:200}:{x:1120,y:190};const a={x:source.x-observer.x,y:source.y-observer.y},b={x:patch.x-observer.x,y:patch.y-observer.y};const cosine=(a.x*b.x+a.y*b.y)/(Math.hypot(a.x,a.y)*Math.hypot(b.x,b.y));return {source,observer,patch,angleDegrees:Math.acos(clamp(cosine,-1,1))*180/Math.PI};}
/** One fixed wavelength per packet for its complete trajectory. Blue/violet
 * redirect more often than red; green/amber/red also scatter. Not data counts. */
export function scatterPacket(index,phase,longPath=false){const w=wavelengths[index%wavelengths.length];const f=clamp(phase),choice=(Math.floor(index/wavelengths.length)%5)*.2+.04,probability=clamp(.16*(longPath?3:1)*relativeScattering(w.nm),.06,.80),redirected=choice<probability;const turn=.30+(index%4)*.12,after=clamp((f-turn)/(1-turn)),sign=index%2?1:-1;return {id:index,wavelength_nm:w.nm,color:w.color,redirected,phase:f,along:f,sideways:redirected?sign*after*190:0,turn,probability};}
export function packetAtPath(path,index,phase,longPath=false){const p=scatterPacket(index,phase,longPath),pos=pointAlong(path,p.along),normal={x:-path.incoming.y,y:path.incoming.x};return {...p,x:pos.x+normal.x*p.sideways,y:pos.y+normal.y*p.sideways};}
export function assertTimeline(props){if(!props||!Number.isFinite(props.duration)||props.duration<=0||!Array.isArray(props.scenes)||props.scenes.length!==6)throw Error('Six actual-audio semantic scenes required');let end=0;props.scenes.forEach((s,i)=>{if(s.scene!==sceneKinds[i]||!Number.isFinite(s.start)||!Number.isFinite(s.end)||Math.abs(s.start-end)>1/30||s.end<=s.start)throw Error('Invalid or reordered semantic timeline');for(const key of requiredMarks[s.scene])if(!Number.isFinite(s.marks?.[key])||s.marks[key]<0||s.marks[key]>=s.end-s.start)throw Error('Missing/out-of-range actual audio mark '+s.scene+'.'+key);if(s.scene==='scattering'&&Object.hasOwn(s.marks,'scatter')){const a=s.marks.scatter;if(!Number.isFinite(a)||a<s.marks.mixed||a>=s.marks.redirect)throw Error('Invalid actual first-scatter anchor');}end=s.end;});if(Math.abs(end-props.duration)>.1)throw Error('Actual timeline/body mismatch');return true;}
