// Primary-bow geometric optics. Water indices are illustrative visible-light
// values, not a laboratory calibration. Sources checked 4 November 2026:
// https://www.weather.gov/fgz/Rainbow
// https://journals.ametsoc.org/doi/10.1175/BAMS-D-20-0101.1
// One *partial* internal reflection, not total internal reflection.
export const sceneKinds = ['question','conditions','droplet','cone','move','circle','callback'];
export const requiredMarks = {
 question:['question','step','change'], conditions:['behind','rain'],
 droplet:['enter','reflect','leave','dispersion'], cone:['axis','angle','violet','cone','many'],
 move:['move','different'], circle:['circle','ground','unobstructed','below'], callback:['callback'],
};
export const clamp = (x,a=0,b=1)=>Math.max(a,Math.min(b,x));
export const mix = (a,b,p)=>a+(b-a)*p;
export function smooth(t,a,b){if(!Number.isFinite(a)||!Number.isFinite(b))return 0;const p=clamp((t-a)/(b-a));return p*p*(3-2*p);}
export const radians = d=>d*Math.PI/180;
export const degrees = r=>r*180/Math.PI;
export const dot=(a,b)=>a.x*b.x+a.y*b.y;
export const length=a=>Math.hypot(a.x,a.y);
export const add=(a,b)=>({x:a.x+b.x,y:a.y+b.y});
export const scale=(a,s)=>({x:a.x*s,y:a.y*s});
export const unit=a=>scale(a,1/length(a));
export const reflect=(ray,normal)=>add(ray,scale(normal,-2*dot(ray,normal)));
export function refract(ray,normal,nFrom,nTo){
 const eta=nFrom/nTo,c=-dot(ray,normal),k=1-eta*eta*(1-c*c);
 if(k<0)throw Error('Total internal reflection is not the primary rainbow exit');
 return unit(add(scale(ray,eta),scale(normal,eta*c-Math.sqrt(k))));
}
export function rainbowIncidence(n=1.331){
 if(n<=1||n>=2)throw Error('Invalid water refractive index');
 return Math.asin(Math.sqrt((4-n*n)/3));
}
export function primaryRay(n=1.331,incidence=rainbowIncidence(1.331)){
 const entry={x:-Math.cos(incidence),y:-Math.sin(incidence)},incoming={x:1,y:0};
 const inside=refract(incoming,entry,1,n);
 const reflection=add(entry,scale(inside,-2*dot(entry,inside)));
 const reflected=unit(reflect(inside,reflection));
 const exit=add(reflection,scale(reflected,-2*dot(reflection,reflected)));
 const outgoing=refract(reflected,scale(exit,-1),n,1);
 // Backward continuation of the incoming sunlight points toward the Sun.
 // The returning ray is about 42 degrees from that backward direction.
 const returnAngle=degrees(Math.acos(clamp(dot(outgoing,{x:-1,y:0}),-1,1)));
 return {n,incidence,entry,reflection,exit,incoming,inside,reflected,outgoing,
  refractedAngle:Math.asin(Math.sin(incidence)/n),returnAngle,
  reflectionCount:1,reflectionIsTotal:false};
}
export const spectrum=Array.from({length:49},(_,i)=>({
 fraction:i/48,n:mix(1.331,1.343,i/48),colour:`hsl(${mix(0,280,i/48)} 90% 66%)`,
}));
export function displayRay(n,portrait=true){
 const ray=primaryRay(n),cx=portrait?460:900,cy=320,r=225;
 const at=p=>({x:cx+p.x*r,y:cy+p.y*r});
 const entry=at(ray.entry),reflection=at(ray.reflection),exit=at(ray.exit);
 const start={x:portrait?55:300,y:entry.y};
 const end=add(exit,scale(ray.outgoing,245));
 return {...ray,cx,cy,r,start,entry,reflection,exit,end};
}
export function exitDetail(portrait=true){
 const ray=displayRay(1.331,portrait),centre=add(ray.exit,scale(ray.outgoing,135));
 const frame=portrait?{x:685,y:370,width:200,height:375}:{x:1250,y:230,width:300,height:500};
 const size=portrait?180:260,x=frame.x+(frame.width-size)/2,y=portrait?430:315,magnification=8;
 return {frame,target:{x,y,width:size,height:size},centre,magnification,
  source:{x:centre.x-size/magnification/2,y:centre.y-size/magnification/2,width:size/magnification,height:size/magnification}};
}
export function magnifiedExitPoint(point,detail){return {
 x:detail.target.x+detail.target.width/2+(point.x-detail.centre.x)*detail.magnification,
 y:detail.target.y+detail.target.height/2+(point.y-detail.centre.y)*detail.magnification,
};}
export function polylinePoint(points,progress){
 const parts=points.slice(1).map((p,i)=>length({x:p.x-points[i].x,y:p.y-points[i].y}));
 const total=parts.reduce((a,b)=>a+b,0);let d=clamp(progress)*total;
 for(let i=0;i<parts.length;i++){if(d<=parts[i]||i===parts.length-1){const q=parts[i]?d/parts[i]:0;return {x:mix(points[i].x,points[i+1].x,q),y:mix(points[i].y,points[i+1].y,q)};}d-=parts[i];}
 return points[0];
}
// World geometry: Sun rays travel along +z, observer at cone tip. A plane of
// droplets in front of the observer intersects the viewing cone in a circle.
// Moving sideways translates the cone's centre on that *fixed* rain plane.
export function coneDrop(eye,planeZ,angleDegrees,azimuth){
 const depth=planeZ-eye.z;if(depth<=0)throw Error('Drops must be ahead');
 const radius=depth*Math.tan(radians(angleDegrees));
 return {x:eye.x+radius*Math.cos(azimuth),y:eye.y+radius*Math.sin(azimuth),z:planeZ};
}
export function viewingAngle(eye,drop){
 const dz=drop.z-eye.z;if(dz<=0)throw Error('Drops must be ahead');
 return degrees(Math.atan2(Math.hypot(drop.x-eye.x,drop.y-eye.y),dz));
}
export const redAngle=42, violetAngle=40;
export function movingEye(progress){return {x:mix(-85,85,smooth(progress,0,1)),y:0,z:0};}
export function approachingEye(progress){return {x:0,y:0,z:80*clamp(progress)};}
export function projectFixedDrop(eye,drop,{cx,cy,r}){
 const depth=drop.z-eye.z;if(depth<=0)throw Error('Projection requires drops ahead');
 const focal=r/Math.tan(radians(redAngle));
 return {x:cx+(drop.x-eye.x)*focal/depth,y:cy+(drop.y-eye.y)*focal/depth};
}
export function fixedDropField(){
 const points=[];for(let y=-390;y<=30;y+=30)for(let x=-410;x<=410;x+=30)
  points.push({x:x+Math.sin(y*.17+x*.04)*5,y:y+Math.cos(x*.12)*5,z:390});
 return points;
}
export function dropLight(eye,drop){
 const angle=viewingAngle(eye,drop),fraction=(redAngle-angle)/(redAngle-violetAngle);
 return {angle,selected:angle>=violetAngle-.7&&angle<=redAngle+.7,
  fraction:clamp(fraction),colour:`hsl(${mix(0,280,clamp(fraction))} 92% 67%)`};
}
export function coneSlice(portrait=true){
 const eye={x:portrait?170:330,y:380},depth=330,r=depth*Math.tan(radians(redAngle));
 return {eye,plane:{x:eye.x+depth,y:eye.y},radius:r,
  upper:{x:eye.x+depth,y:eye.y-r},lower:{x:eye.x+depth,y:eye.y+r},
  angle:redAngle};
}
export function arcPoints(cx,cy,r,start=180,end=360,n=100){
 return Array.from({length:n+1},(_,i)=>{const a=radians(mix(start,end,i/n));return {x:cx+r*Math.cos(a),y:cy+r*Math.sin(a)};});
}
export function circleReveal(t,m={}){
 // A dashed construction shows the missing circle before an unobstructed,
 // elevated view actually reveals sunlit droplets below the observer.
 return smooth(t,Math.max(m.unobstructed??Infinity,m.below??Infinity),Math.max(m.unobstructed??Infinity,m.below??Infinity)+.8);
}
export function assertTimeline(props){
 if(!Number.isFinite(props.duration)||props.duration<=0)throw Error('Actual audio duration required');
 if(!Array.isArray(props.scenes)||props.scenes.length!==sceneKinds.length)throw Error('Seven researched scenes required');
 let end=0;
 for(const [i,s] of props.scenes.entries()){
  if(s.scene!==sceneKinds[i]||![s.start,s.end].every(Number.isFinite)||Math.abs(s.start-end)>.001||s.end<=s.start||s.end>props.duration+.05)throw Error('Invalid scene timeline');
  const marks=requiredMarks[s.scene].map(k=>s.marks?.[k]);
  if(marks.some(v=>!Number.isFinite(v)||v<0||v>s.end-s.start+.05)||marks.some((v,j)=>j&&v<marks[j-1]-.001))throw Error('Missing, outside or reordered actual-word mark '+s.scene);
  end=s.end;
 }
 if(props.scenes[0].start!==0||Math.abs(end-props.duration)>.05)throw Error('Scenes must cover actual audio');
 if(!Array.isArray(props.captions)||!props.captions.length)throw Error('Actual audio captions required');
 let cueEnd=0;for(const c of props.captions){if(![c.start,c.end].every(Number.isFinite)||c.start<cueEnd-.001||c.end<=c.start||c.end>props.duration+.05||typeof c.text!=='string'||!c.text.trim())throw Error('Invalid actual-audio captions');cueEnd=c.end;}
 return props;
}
