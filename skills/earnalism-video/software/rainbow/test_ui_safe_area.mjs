import assert from 'node:assert/strict';
import {assertLayout,layoutFor,headingFor,labelBounds,conditionLabels,coneLabels,rectOverlap} from './layout.mjs';
import {assertUiClear} from '../src/social-safe-area.mjs';
import {watermarkLayout} from '../src/branding.mjs';
import {sceneKinds} from './model.mjs';
import {coneSlice} from './model.mjs';
for(const p of [true,false]){const l=assertLayout(p);for(const kind of sceneKinds){const text=headingFor(kind,p),lines=text.split('\n');assert.ok(lines.length<=2);assert.ok(lines.every(t=>t.length*l.headingFont*.56<l.heading.width),`Heading too wide: ${kind}`);assert.ok(lines.length*l.headingFont*1.08<=l.heading.height);}
 conditionLabels(p);const labels=coneLabels(p),violet=labelBounds(labels[3]),cone=coneSlice(p);assert.ok(violet.x>cone.plane.x+75+10,'Violet label must not cover the cone/drop rim');
 const wm=watermarkLayout(p?1080:1920,p?1920:1080,{placement:p?l.watermark:undefined,occupiedRects:['heading','diagram','support','captions'].map(k=>l[k])});assert.ok(wm.size>0);
 if(p){for(const k of ['heading','diagram','support','captions'])assertUiClear(k,l[k]);assertUiClear('watermark',{x:wm.left,y:wm.top,width:wm.size,height:wm.size});assert.equal(rectOverlap({x:wm.left,y:wm.top,width:wm.size,height:wm.size},l.heading),false);}
}
for(const [name,r] of [['legacy heading',{x:70,y:125,width:860,height:190}],['legacy watermark',{x:943,y:44,width:72,height:72}],['native-rail intruder',{x:850,y:650,width:150,height:500}]])assert.throws(()=>assertUiClear(name,r),/reserved mobile UI/);
assert.equal(layoutFor(true).captionFont,47);assert.equal(layoutFor(true).captions.y+layoutFor(true).captions.height,1490);
console.log('PASS: separately composed layouts, readable heading bounds, complete watermark/UI reservation, protected caption area and regression rejection of legacy corner overlaps');
