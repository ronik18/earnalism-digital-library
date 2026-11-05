import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertUiClear,safeContentRect,portraitReviewProfile,uiMasks} from '../src/social-safe-area.mjs';
import {assertLayout,layoutFor,rectOverlap,labelBounds} from './layout.mjs';

assert.deepEqual(safeContentRect(),{x:72,y:270,width:828,height:1230});
// Reproduce the observed class of failure; bare-frame bounds used to accept it.
for(const [name,rect] of [
 ['legacy heading',{x:70,y:125,width:860,height:190}],
 ['legacy watermark',{x:943,y:44,width:72,height:72}],
 ['legacy caption',{x:70,y:1420,width:870,height:205}],
 ['right rail text',{x:850,y:700,width:100,height:50}],
]) assert.throws(()=>assertUiClear(name,rect),/reserved mobile UI/);
const p=assertLayout(true),safe=safeContentRect();
for(const name of ['heading','diagram','support','captions'])assertUiClear(name,p[name]);
const mark={x:p.watermark.left,y:p.watermark.top,width:p.watermark.size,height:p.watermark.size};
assertUiClear('watermark',mark);assert.equal(rectOverlap(mark,p.heading),false);
assert.equal(p.captionFont,47,'UI repair must not solve space by shrinking speech captions');
assert.equal(p.captions.height,205);
assert.equal(p.headingFont,62);
assertUiClear('boundary',safe);
for(const rect of [{...safe,x:safe.x-1},{...safe,y:safe.y-1},{...safe,width:safe.width+1},{...safe,height:safe.height+1}])assert.throws(()=>assertUiClear('one pixel intrusion',rect));
assert.throws(()=>safeContentRect({...portraitReviewProfile,right:1080}));
assert.throws(()=>assertUiClear('NaN',{x:NaN,y:300,width:100,height:100}));
assert.equal(uiMasks().length,4);
// Existing landscape composition remains exactly as before this portrait repair.
assert.deepEqual(layoutFor(false),{heading:{x:90,y:76,width:1660,height:170},diagram:{x:80,y:265,width:1760,height:570},support:{x:90,y:850,width:1740,height:75},captions:{x:100,y:950,width:1720,height:110},headingFont:78,captionFont:47});
const renderer=fs.readFileSync(new URL('./index.tsx',import.meta.url),'utf8');
assert.ok(renderer.includes('BrandWatermark placement={portrait?l.watermark:undefined}'));
assert.ok(renderer.includes("left:80,top:270,width:820,height:1230,objectFit:'contain'"),'Portrait ident also respects the reserved content area');
assert.ok(renderer.includes('labelSize={portrait?46:56}'),'Receiver retains readable type after portrait reflow');
const mixed=labelBounds({x:230,y:80,size:50,text:'Mixed sunlight'}),air=labelBounds({x:560,y:115,size:54,text:'Air'});
assert.ok(mixed.x>=0&&mixed.x+mixed.width<=900,'Enlarged incoming-light label stays inside actual SVG');
assert.equal(rectOverlap(mixed,air),false,'Larger mixed-light and Air backplates stay separate');
assert.ok(renderer.includes('x={portrait?230:265}')&&renderer.includes('x={portrait?560:cx}'),'Renderer uses the checked label positions');
console.log('PASS: legacy top/right/lower overlaps rejected; all reflowed portrait regions and mark clear reserved UI; readable captions, ident and unchanged landscape retained');
