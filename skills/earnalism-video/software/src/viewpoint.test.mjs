import test from 'node:test';import assert from 'node:assert/strict';
import {observerBridge,layout,quarterState} from './viewpoint.mjs';
test('observer bridge starts on Earth, lands on matching observer view, stays bounded',()=>{for(const portrait of [false,true]){const q=layout(portrait),a={x:q.cx,y:q.cy};const start=observerBridge(0,3,a,q.disk),end=observerBridge(8,3,a,q.disk);assert.equal(start.x,a.x);assert.equal(start.y,a.y);assert.equal(start.p,0);assert.equal(end.x,q.disk.x);assert.ok(Math.abs(end.y-q.disk.y)<1e-9);assert.equal(end.scale,1);for(let t=0;t<9;t+=.01){const b=observerBridge(t,3,a,q.disk);assert.ok(b.p>=0&&b.p<=1&&b.scale>=.08&&b.scale<=1);}}});
test('first-quarter comparison only appears at first quarter; portrait card labels fit',()=>{assert.ok(quarterState(.25));for(const x of [0,.12,.5,.75,1])assert.equal(quarterState(x),false);const q=layout(true);assert.ok(q.card.y>q.cy+q.radius+170);assert.ok(q.disk.y-q.disk.r>q.card.y+60);assert.ok(q.disk.y+q.disk.r<q.diskLabelY-48);assert.ok(q.labelSize>=48);});
import {quarterComparison,showReviewMark} from './viewpoint.mjs';
test('quarter labels follow canonical audio anchors and clean overlays are explicit',()=>{
 const scene={diagram:'phases',anchors:[{phrase:'At first quarter',time:10},{phrase:'First quarter means',time:15}]};
 assert.equal(quarterComparison(scene,9,.25).halfOpacity,0);
 assert.equal(quarterComparison(scene,11,.25).halfOpacity,1);
 assert.equal(quarterComparison(scene,11,.25).cycleOpacity,0);
 assert.equal(quarterComparison(scene,16,.25).cycleOpacity,1);
 assert.equal(quarterComparison(scene,16,.5).active,false);
 assert.throws(()=>quarterComparison({diagram:'phases'},12,.25),/anchors/);
 assert.equal(showReviewMark({}),true);assert.equal(showReviewMark({reviewOverlay:false}),false);
});

import {observerLabelsOpacity,nearFull} from './viewpoint.mjs';
test('observer card bands stay separated and labels wait for arriving disk on every frame',()=>{for(const portrait of [false,true]){const q=layout(portrait);assert.ok(q.disk.y-q.disk.r>q.card.y+60+20);assert.ok(q.disk.y+q.disk.r<q.diskLabelY-48);assert.ok(q.diskLabelY+20<q.card.y+q.card.h);for(let f=0;f<90;f++){const t=f/30;const b=observerBridge(t,0,{x:q.cx,y:q.cy},q.disk);if(observerLabelsOpacity(t,0,true)>0)assert.equal(b.p,1);}}});
test('full-Moon wording never appears at last quarter or waning crescent',()=>{assert.ok(nearFull(.5));for(const phase of [0,.12,.25,.75,.9,1])assert.equal(nearFull(phase),false);});

test('portrait moving observer disk bypasses Earth and sightline label bands',()=>{
 const q=layout(true);
 for(let i=0;i<=165;i++){
  const b=observerBridge(i/100,0,{x:q.cx,y:q.cy},q.disk),r=q.disk.r*b.scale;
  for(const band of [{x:q.cx-75,y:q.cy+60,w:150,h:55},{x:q.cx-200,y:595,w:400,h:60}]){
   const dx=Math.max(band.x-b.x,0,b.x-band.x-band.w),dy=Math.max(band.y-b.y,0,b.y-band.y-band.h);
   assert.ok(dx*dx+dy*dy>r*r,'moving disk intersects label at '+i/100);
  }
 }
});
