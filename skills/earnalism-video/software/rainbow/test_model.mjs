import assert from 'node:assert/strict';
import {primaryRay,rainbowIncidence,length,dot,refract,displayRay,exitDetail,magnifiedExitPoint,spectrum,coneDrop,viewingAngle,movingEye,approachingEye,projectFixedDrop,dropLight,fixedDropField,coneSlice,circleReveal,polylinePoint,assertTimeline,sceneKinds,requiredMarks} from './model.mjs';
const near=(a,b,t=1e-9)=>assert.ok(Math.abs(a-b)<t,`${a} != ${b}`);
for(const s of spectrum){const r=primaryRay(s.n);for(const p of [r.entry,r.reflection,r.exit])near(length(p),1);for(const d of [r.inside,r.reflected,r.outgoing])near(length(d),1);assert.equal(r.reflectionCount,1);assert.equal(r.reflectionIsTotal,false);
 near(Math.sin(r.incidence),s.n*Math.sin(r.refractedAngle));
 const incidenceCos=dot(r.inside,r.reflection),reflectionCos=-dot(r.reflected,r.reflection);near(incidenceCos,reflectionCos);
 assert.ok(r.refractedAngle<Math.asin(1/s.n),'Primary internal incidence must be below TIR critical angle');
 const q=displayRay(s.n,true);for(const p of [q.start,q.entry,q.reflection,q.exit,q.end])assert.ok(p.x>=0&&p.x<=900&&p.y>=0&&p.y<=760,'Actual ray leaves portrait diagram');
}
const red=primaryRay(1.331),violet=primaryRay(1.343);assert.ok(red.returnAngle>42&&red.returnAngle<43);assert.ok(violet.returnAngle>40&&violet.returnAngle<42);assert.ok(red.returnAngle>violet.returnAngle);assert.ok(violet.refractedAngle<red.refractedAngle);
near(red.entry.x,violet.entry.x);near(red.entry.y,violet.entry.y); // same incoming white ray
assert.ok(Math.abs(rainbowIncidence(1.331)-red.incidence)<1e-12);
assert.throws(()=>refract({x:Math.sin(1.2),y:Math.cos(1.2)},{x:0,y:-1},1.343,1),/Total/);
for(let i=0;i<=40;i++)for(let a=0;a<Math.PI*2;a+=.2){const eye=movingEye(i/40),drop=coneDrop(eye,390,42,a);near(viewingAngle(eye,drop),42,1e-10);}
const originalEye=movingEye(0),movedEye=movingEye(1),fixedDrop=coneDrop(originalEye,390,42,Math.PI);assert.ok(dropLight(originalEye,fixedDrop).selected);assert.equal(dropLight(movedEye,fixedDrop).selected,false,'Changing observer must select different stationary drops');
const field=fixedDropField();assert.deepEqual(field,fixedDropField());for(let p=0;p<=1;p+=.025){const e=movingEye(p);const selected=field.filter(d=>dropLight(e,d).selected);assert.ok(selected.length>0);assert.ok(selected.length<field.length/3);}
const selectedAt=e=>field.flatMap((d,i)=>dropLight(e,d).selected?[i]:[]);
assert.notDeepEqual(selectedAt(approachingEye(0)),selectedAt(approachingEye(1)),'Approaching changes the actual selected fixed droplet IDs, not only their colour');
for(let p=0;p<=1;p+=.05){const eye=approachingEye(p);for(let a=Math.PI;a<=2*Math.PI;a+=.1){const drop=coneDrop(eye,390,42,a),screen=projectFixedDrop(eye,drop,{cx:450,cy:610,r:335});near(Math.hypot(screen.x-450,screen.y-610),335,1e-9);}}
for(const p of [true,false]){const c=coneSlice(p);near(Math.atan2(c.eye.y-c.upper.y,c.upper.x-c.eye.x)*180/Math.PI,42);assert.ok(c.upper.y>0&&c.lower.y<760);}
for(const p of [true,false]){const d=exitDetail(p),r=displayRay(1.331,p),a=magnifiedExitPoint(r.exit,d),b=magnifiedExitPoint(r.end,d);near(Math.hypot(b.x-a.x,b.y-a.y),Math.hypot(r.end.x-r.exit.x,r.end.y-r.exit.y)*8,1e-9);near((b.y-a.y)/(b.x-a.x),(r.end.y-r.exit.y)/(r.end.x-r.exit.x));assert.ok(d.frame.x>=r.cx+r.r-1,'Inset must sit outside the drop');assert.ok(d.frame.y+d.frame.height<=760);}
assert.equal(circleReveal(4,{unobstructed:5,below:7}),0);assert.equal(circleReveal(6,{unobstructed:5,below:7}),0);assert.equal(circleReveal(9,{unobstructed:5,below:7}),1);assert.equal(circleReveal(100,{}),0);
const pts=[{x:0,y:0},{x:1,y:0},{x:1,y:1}];assert.deepEqual(polylinePoint(pts,0),pts[0]);assert.deepEqual(polylinePoint(pts,1),pts[2]);assert.deepEqual(polylinePoint(pts,.5),pts[1]);
const valid={duration:70,scenes:sceneKinds.map((scene,i)=>({scene,start:i*10,end:(i+1)*10,marks:Object.fromEntries(requiredMarks[scene].map(k=>[k,1]))})),captions:[{start:0,end:1,text:'Structural test fixture'}]};assertTimeline(valid);
const gap=structuredClone(valid);gap.scenes[1].start+=1;assert.throws(()=>assertTimeline(gap),/scene timeline/);
const missing=structuredClone(valid);delete missing.scenes[0].marks.step;assert.throws(()=>assertTimeline(missing),/actual-word mark/);
console.log('PASS: Snell entry/exit, one partial reflection, primary spectral order, actual ray bounds, 42-degree observer cone, moving-observer/drop selection, and qualified full-circle reveal');
