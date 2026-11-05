import assert from 'node:assert/strict';
import {atmosphere,atmosphericPath,pointAlong,elevationAt,relativeScattering,illustrativeTransmission,wavelengths,scatterPacket,packetAtPath,gazeGeometry,sceneKinds,requiredMarks,assertTimeline} from './model.mjs';
import {assertLayout,bodyFrameCount,rectOverlap,supportText} from './layout.mjs';
for(const p of [false,true])assertLayout(p);
assert.equal(bodyFrameCount(90.01,30),2701);
assert.throws(()=>relativeScattering(0));assert.throws(()=>illustrativeTransmission(450,-1));
assert.ok(relativeScattering(405)>relativeScattering(450));assert.ok(relativeScattering(450)>relativeScattering(650));
assert.ok(illustrativeTransmission(450,3)<illustrativeTransmission(450,1));
assert.ok(illustrativeTransmission(450,3)<illustrativeTransmission(650,3));
const high=atmosphericPath(68),low=atmosphericPath(7);assert.ok(low.length>high.length*2);assert.equal(high.earthRadius,low.earthRadius);assert.equal(high.outerRadius,low.outerRadius);assert.deepEqual(high.observer,low.observer);
for(let e=0;e<=90;e+=.25){const path=atmosphericPath(e);assert.ok(Math.abs(Math.hypot(path.entry.x-atmosphere.cx,path.entry.y-atmosphere.cy)-atmosphere.outerRadius)<1e-7);for(let f=0;f<=1;f+=.01){const pt=pointAlong(path,f);assert.ok(Math.hypot(pt.x-atmosphere.cx,pt.y-atmosphere.cy)>=atmosphere.earthRadius-1e-7,'Direct path never penetrates Earth');}}
for(let t=0;t<10;t+=.025){const path=atmosphericPath(elevationAt(t,{lower:1,longer:6}));assert.deepEqual(path.observer,atmosphere.observer);assert.ok(path.length>=high.length-1e-7&&path.length<=low.length+1e-7);}
for(const p of [false,true])assert.ok(gazeGeometry(p).angleDegrees>45,'Sky-view gaze is away from the solar direction');
for(let i=0;i<25;i++){const assigned=wavelengths[i%5];for(let f=0;f<=1;f+=.01){const a=scatterPacket(i,f,false),b=packetAtPath(low,i,f,true);assert.equal(a.color,assigned.color);assert.equal(b.color,assigned.color);assert.equal(a.wavelength_nm,assigned.nm);assert.equal(b.wavelength_nm,assigned.nm);assert.ok(Number.isFinite(b.x)&&Number.isFinite(b.y));}}
for(const long of [false,true]){const counts=Object.fromEntries(wavelengths.map(w=>[w.id,0]));for(let i=0;i<25;i++)if(scatterPacket(i,1,long).redirected)counts[wavelengths[i%5].id]++;assert.ok(counts.blue>counts.red);assert.ok(counts.red>0,'Other colours also scatter');assert.ok(counts.violet>=counts.blue,'Never imply blue is shortest or most scattered');assert.ok(counts.blue<5,'Illustrative beam retains some blue rather than asserting total removal');}
const scenes=sceneKinds.map((scene,i)=>({scene,start:i*15,end:(i+1)*15,marks:Object.fromEntries(requiredMarks[scene].map((k,j)=>[k,j+1]))}));assertTimeline({duration:90,scenes});assert.throws(()=>assertTimeline({duration:91,scenes}));const bad=structuredClone(scenes);delete bad[2].marks.toward;assert.throws(()=>assertTimeline({duration:90,scenes:bad}));
assert.equal(supportText('sunset_path',4,{identity:5}),'A longer path changes the remaining mixture.');assert.equal(supportText('sunset_path',5,{identity:5}),'Blue stays blue. The mixture changes.');
console.log('PASS: fixed-shell intersections, full moving ray trajectory, outward observer geometry, off-Sun gaze, wavelength/colour identity, non-blue scattering, actual-mark gates and distinct caption-safe layouts');
const {labelBounds,sectionAnnotationLayout}=await import('./layout.mjs');
for(let e=7;e<=68;e+=.25){const p=atmosphericPath(e);for(const title of ['Higher Sun','Lowering Sun','Lower Sun','Same air','Direct sunlight']){const labels=sectionAnnotationLayout(p,title,true,true).map(labelBounds);for(let i=0;i<labels.length;i++){const a=labels[i];assert.ok(a.x>=0&&a.y>=0&&a.x+a.width<=900&&a.y+a.height<=760,'Section annotation fits local canvas');for(let j=i+1;j<labels.length;j++)assert.equal(rectOverlap(a,labels[j]),false,'Moving-Sun annotations do not collide');}}}
assert.ok(Math.hypot(740-atmosphere.cx,252-atmosphere.cy)>atmosphere.earthRadius&&Math.hypot(740-atmosphere.cx,252-atmosphere.cy)<atmosphere.outerRadius,'Air leader points into shell, not Earth');
console.log('PASS: actual-renderer annotation bounds swept across full high→low solar motion; Air leader enters real annulus');
const fs=await import('node:fs');const renderer=fs.readFileSync(new URL('./index.tsx',import.meta.url),'utf8');
assert.ok(renderer.includes('Conceptual light receiver, not a person viewing the Sun'));
assert.ok(!renderer.includes('function Observer('));assert.ok(renderer.includes('Two routes for sunlight.'));
assert.ok(renderer.includes('strokeWidth={3} opacity={.26} strokeDasharray="10 12"'),'Direct solar route stays unhighlighted in sky-view scene');
assert.equal(supportText('scattering',5,{shorter:3}),'','Wave comparison avoids redundant conclusion over actual captions');
assert.ok(renderer.includes('cycles={650/450*5}'),'Relative wavelength sketch is consistent with represented450/650nm comparison');
console.log('PASS: conceptual receiver, unhighlighted direct route and reduced wave-caption reading load');
const prediction=renderer.slice(renderer.indexOf('function PathComparison('),renderer.indexOf('function SunsetPath('));
assert.ok(prediction.includes('trace'));assert.ok(!prediction.includes('packets'),'Prediction withholds coloured transmission result; white length highlight only');
assert.ok(renderer.includes('Path-following comparison highlight, not simulated photon speed'));
console.log('PASS: prediction shows geometric journey before coloured redistribution answer');

const {redirectionStarted}=await import('./layout.mjs');
assert.equal(redirectionStarted(6.19,{scatter:6.20,redirect:8.16}),false);
assert.equal(redirectionStarted(6.20,{scatter:6.20,redirect:8.16}),true,'First actual scattering verb drives cause cue rather than its later paraphrase');
assert.equal(redirectionStarted(8.15,{redirect:8.16}),false);
assert.equal(redirectionStarted(8.16,{redirect:8.16}),true,'Unchanged older props keep their documented mark');
assert.equal(redirectionStarted(100,{}),false,'Missing actual timing must not invent onset');
assert.equal(supportText('prediction',2,{predict:8.56}),'','Do not duplicate the in-diagram atmosphere qualification');
assert.equal(supportText('prediction',8.56,{predict:8.56}),'What remains in the direct beam?');
for(let e=7;e<=68;e+=.25){
 const path=atmosphericPath(e),sun={x:path.source.x-32,y:path.source.y-32,width:64,height:64},receiver={x:path.observer.x-20,y:path.observer.y-15,width:40,height:32};
 for(const title of ['Higher Sun','Lowering Sun','Lower Sun','Same air']){
  const labels=sectionAnnotationLayout(path,title,false,true);
  assert.ok(labels.every(l=>l.size>=56),'Essential section labels are at least14px equivalent in a640px landscape player');
  for(const l of labels){const box=labelBounds(l);assert.equal(rectOverlap(box,sun),false,'Actual moving Sun does not meet label backplates');assert.equal(rectOverlap(box,receiver),false,'Receiver icon remains clear of label backplates');}
 }
}
const outputLabels=sectionAnnotationLayout(low,'Direct sunlight',true,false);
assert.ok(outputLabels.some(l=>l.text==='Warmer mix'&&l.size===56));
assert.ok(!outputLabels.some(l=>l.text==='Remaining mixture'));
for(const a of outputLabels)assert.ok(labelBounds(a).x+labelBounds(a).width<=900,'Larger output label remains in scene');
const outputBox=labelBounds(outputLabels.find(l=>l.text==='Warmer mix'));
assert.equal(rectOverlap(outputBox,{x:650,y:445,width:185,height:68}),false,'Output label does not touch its colour swatch');
assert.ok(590-34-56*.84>340+150,'Larger landscape wave labels clear the scattering ellipse');
console.log('PASS: earlier actual-audio cause cue, legacy timing fallback,14px-equivalent section labels, moving Sun/receiver clearance and single schematic qualification');
