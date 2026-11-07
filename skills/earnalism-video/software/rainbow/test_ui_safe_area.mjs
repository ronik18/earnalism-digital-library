import assert from 'node:assert/strict';
import {assertLayout,layoutFor,headingFor,labelBounds,conditionLabels,coneLabels,rectOverlap,circleSceneLayout} from './layout.mjs';
import {assertUiClear} from '../src/social-safe-area.mjs';
import {watermarkLayout} from '../src/branding.mjs';
import {sceneKinds} from './model.mjs';
import {coneSlice} from './model.mjs';
for(const p of [true,false]){const l=assertLayout(p);for(const kind of sceneKinds){const text=headingFor(kind,p),lines=text.split('\n');assert.ok(lines.length<=2);assert.ok(lines.every(t=>t.length*l.headingFont*.56<l.heading.width),`Heading too wide: ${kind}`);assert.ok(lines.length*l.headingFont*1.08<=l.heading.height);}
 conditionLabels(p);const labels=coneLabels(p),violet=labelBounds(labels[3]),cone=coneSlice(p);assert.ok(violet.x>cone.plane.x+75+10,'Violet label must not cover the cone/drop rim');
 const wm=watermarkLayout(p?1080:1920,p?1920:1080,{placement:p?l.watermark:undefined,occupiedRects:['heading','diagram','support','captions'].map(k=>l[k])});assert.ok(wm.size>0);
 if(p){const fullLockup={x:wm.left,y:wm.top,width:wm.width,height:wm.height};for(const k of ['heading','diagram','support','captions'])assertUiClear(k,l[k]);assertUiClear('watermark',fullLockup);assert.equal(rectOverlap(fullLockup,l.heading),false);assert.ok(Math.abs(wm.width/wm.height-10/3)<1e-9,'Validate the complete rectangular lockup, not a legacy square icon');}
}
for(const [name,r] of [['legacy heading',{x:70,y:125,width:860,height:190}],['legacy watermark',{x:943,y:44,width:72,height:72}],['native-rail intruder',{x:850,y:650,width:150,height:500}]])assert.throws(()=>assertUiClear(name,r),/reserved mobile UI/);
assert.equal(layoutFor(true).captionFont,47);assert.equal(layoutFor(true).captions.y+layoutFor(true).captions.height,1490);
console.log('PASS: separately composed layouts, readable heading bounds, complete watermark/UI reservation, protected caption area and regression rejection of legacy corner overlaps');

assert.match(headingFor('question',false),/rainbow’s end/);
assert.match(headingFor('question',true),/rainbow’s end/);
assert.ok(!headingFor('question',true).includes('reach it'));

// Exercise the actual staged label plan and SVG-to-composition transform,
// including the previously failing almost-revealed full-circle frame.
for(const portrait of [false,true]){
 const l=layoutFor(portrait),svgWidth=portrait?900:1600,svgHeight=760;
 const scale=Math.min(l.diagram.width/svgWidth,l.diagram.height/svgHeight);
 const origin={x:l.diagram.x+(l.diagram.width-svgWidth*scale)/2,y:l.diagram.y+(l.diagram.height-svgHeight*scale)/2};
 for(const reveal of [0,.1,.3,.300001,.5,.9,.99,1])for(const ground of [0,1]){
  const plan=circleSceneLayout(portrait,reveal,ground);assert.equal(plan.labels.length,1,'Stage must have one label');
  const label=plan.labels[0],b=labelBounds(label);
  assert.equal(label.text.startsWith('Unobstructed'),reveal>.3,'Mutually exclusive label stages');
  assert.equal(rectOverlap(b,plan.protectedCircle),false,'Label must clear visible ring plus padding');
  assert.ok(b.y>=0&&b.y+b.height<=svgHeight&&b.x>=0&&b.x+b.width<=svgWidth,'Actual Label background fits SVG');
  const projected={x:origin.x+b.x*scale,y:origin.y+b.y*scale,width:b.width*scale,height:b.height*scale};
  assert.equal(rectOverlap(projected,l.captions),false,'Circle label clears caption region');
  assert.equal(rectOverlap(projected,l.heading),false,'Circle label clears heading region');
 }
 const final=circleSceneLayout(portrait,1,1).labels[0];assert.equal(final.y,portrait?730:735);assert.equal(final.size,portrait?43:50);
}
assert.throws(()=>circleSceneLayout(false,NaN),/Invalid circle/);
assert.throws(()=>circleSceneLayout(true,1.1),/Invalid circle/);
console.log('PASS: exclusive circle labels clear actual visible ring, SVG bounds, headings and captions in both formats');
