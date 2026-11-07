import assert from 'node:assert/strict';
import {belowDewPoint,vaporPath,dropletPoint,conditionState,assertLayout,bodyFrameCount} from './layout.mjs';
for(const p of [false,true])assertLayout(p);
assert.equal(belowDewPoint(8,16),true);assert.equal(belowDewPoint(8,3),false);assert.equal(belowDewPoint(8,8),false);
assert.throws(()=>belowDewPoint(NaN,8));
for(let i=0;i<6;i++)for(let p=-.1;p<1.2;p+=.01){assert.ok(vaporPath(i,p).x>=568);assert.ok(dropletPoint(i).x-18>540);}
assert.equal(conditionState(false).surface,conditionState(true).surface);assert.equal(conditionState(false).wet,true);assert.equal(conditionState(true).wet,false);
assert.equal(bodyFrameCount(90.01,30),2701);
console.log('PASS: threshold, no wall crossing, constant surface comparison, caption/diagram separation, end-ident boundary');
const {coalescedDrop}=await import('./layout.mjs');
for(let i=0;i<6;i++)for(let p=0;p<=1;p+=.05){const d=coalescedDrop(i,p);assert.ok(d.x-d.r>540);}
for(let i=0;i<6;i+=2){assert.equal(coalescedDrop(i,1).y,coalescedDrop(i+1,1).y);assert.equal(coalescedDrop(i+1,1).opacity,0);}
const {wholeDropPoint}=await import('./layout.mjs');
for(let i=0;i<6;i++){
 const d=wholeDropPoint(i);assert.ok(Math.abs(d.x-d.r-d.wallX-1)<1e-9,'Whole-glass drop contacts the exterior wall stroke');
 for(let p=0;p<=1;p+=.025){const c=coalescedDrop(i,p);assert.ok(Math.abs(c.x-c.r-541)<1e-9,'Coalescence preserves exterior surface contact');}
}
const {sourceFootnote}=await import('./layout.mjs');
assert.ok(sourceFootnote.x-sourceFootnote.maxWidth/2>sourceFootnote.particleRight,'Qualification label clears all source vapor symbols');

const {supportText}=await import('./layout.mjs');
assert.equal(supportText('cooling',6.57,{dewpoint:6.58}),'Heat flows from warmer to colder.');
assert.equal(supportText('cooling',6.58,{dewpoint:6.58}),'Cooling to the dew point.');
assert.equal(supportText('droplets',9.61,{conservation:9.62}),'Below dew point: liquid can grow.');
assert.equal(supportText('droplets',9.62,{conservation:9.62}),'A change of state—not new water.');
const fs=await import('node:fs');const renderer=fs.readFileSync(new URL('./index.tsx',import.meta.url),'utf8');
assert.ok(!renderer.includes('y="745"'),'No duplicate explanatory baseline in the wall-label SVG');
assert.ok(renderer.includes('const support=supportText(kind,t,marks)'),'Actual renderer uses timed support region');

const {openingWallVisible}=await import('./layout.mjs');
assert.equal(openingWallVisible('question',0,{question:5.34}),false);
assert.equal(openingWallVisible('question',5.33,{question:5.34}),false);
assert.equal(openingWallVisible('question',5.34,{question:5.34}),true);
assert.equal(openingWallVisible('question',8,{}),false);
assert.equal(openingWallVisible('callback',0,{}),true);
assert.ok(renderer.includes('openingWallVisible(kind,t,marks)&&<g>'));
assert.equal(supportText('question',0,{question:5.34}),'');
assert.equal(supportText('question',5.34,{question:5.34}),'Through the wall—or from somewhere unseen?');

const {liquidRecallAnchor,portraitCondition}=await import('./layout.mjs');
assert.equal(liquidRecallAnchor([{start:52.46,text:'Here, we are showing liquid droplets on a surface above freezing.'}],45.08),7.380000000000003);
assert.equal(portraitCondition(7.37,{drier:1.86,liquid_recall:7.38}).dry,true);
assert.deepEqual(portraitCondition(7.38,{drier:1.86,liquid_recall:7.38}),{dry:false,recall:true});
assert.equal(liquidRecallAnchor([],45.08),Infinity);
assert.ok(renderer.includes("Liquid-water example"));
