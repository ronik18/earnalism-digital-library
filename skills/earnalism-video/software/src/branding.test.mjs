import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import crypto from 'node:crypto';
import {watermarkAsset,watermarkLayout,schematicContext} from './branding.mjs';
import {assertUiClear,reviewProfileForFrame} from './social-safe-area.mjs';
const root=new URL('../',import.meta.url);
test('watermark clips exact approved emblem and excludes lettering',()=>{
 const bytes=fs.readFileSync(new URL('public/'+watermarkAsset.path,root));
 assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),watermarkAsset.sha256);
 const c=watermarkAsset.crop;assert(c.x<=120&&c.y<=87&&c.x+c.width>=696&&c.y+c.height>=663);
 assert(c.x+c.width<717);assert.equal(c.width,c.height);
});
test('complete default video emblem clears scaled portrait UI reservations',()=>{
 for(const [w,h] of [[1080,1920],[720,1280],[2160,3840],[1080,1440]]){
  const q=watermarkLayout(w,h);
  assertUiClear('complete mark',{x:q.left,y:q.top,width:q.size,height:q.size},reviewProfileForFrame(w,h));
  assert.equal(q.right,w-q.left-q.size);assert.equal(q.opacity,.48);
 }
 const q=watermarkLayout(1080,1920);assert.deepEqual([q.left,q.top,q.size],[832,292,56]);
});
test('unsafe overrides and malformed placements fail rather than clipping the emblem',()=>{
 for(const placement of [{left:943,top:44,size:72},{left:832,top:269,size:56},{left:890,top:292,size:56},{left:832,top:292,size:NaN},{left:832,top:292,size:0},{left:-1,top:292,size:56}])
  assert.throws(()=>watermarkLayout(1080,1920,{placement}));
 for(const dimensions of [[0,1920],[1080,NaN],[-1080,1920]])assert.throws(()=>watermarkLayout(...dimensions));
 assert.throws(()=>watermarkLayout(1080,1920,{surface:'unknown'}));
});
test('protected lesson regions must be reflowed, not covered or silently moved',()=>{
 const heading={x:80,y:300,width:730,height:145},placement={left:832,top:292,size:56};
 const before=JSON.stringify({heading,placement});
 const q=watermarkLayout(1080,1920,{placement,occupiedRects:[heading]});assert.equal(q.left,832);
 assert.equal(JSON.stringify({heading,placement}),before);
 assert.throws(()=>watermarkLayout(1080,1920,{occupiedRects:[{x:820,y:280,width:80,height:90}]}),/protected content/);
 assert.throws(()=>watermarkLayout(1080,1920,{occupiedRects:[{x:NaN,y:0,width:80,height:90}]}),/Invalid watermark protected region/);
 assert.throws(()=>watermarkLayout(1080,1920,{occupiedRects:null}),/Invalid watermark protected regions/);
});
test('landscape placement and explicit cover behavior remain unchanged',()=>{
 assert.deepEqual(watermarkLayout(1920,1080),{size:82,right:70,top:48,left:1768,opacity:.48,scale:82/592});
 assert.deepEqual(watermarkLayout(1080,1920,{surface:'cover'}),{size:72,right:65,top:44,left:943,opacity:.48,scale:72/592});
 assert.throws(()=>watermarkLayout(1080,1920,{surface:'cover',placement:{left:1070,top:10,size:72}}),/outside composition/);
});
test('context is brief and does not imply a physical northern-pole camera',()=>{
 assert.equal(schematicContext({diagram:'orbit',start:10},10.5).text,'Illustrative schematic · not to scale');
 assert.equal(schematicContext({diagram:'orbit',start:10},14),null);
 assert.equal(schematicContext({diagram:'question',start:0},1),null);
});
test('brand persists outside body and ident without old footer or progress strip',()=>{
 const s=fs.readFileSync(new URL('src/index.tsx',root),'utf8');
 assert(!s.includes('SEE DIFFERENTLY'));assert(!s.includes('NASA Science'));assert(!s.includes('100*t/p.duration'));
 assert(s.includes('</Sequence><BrandWatermark/></AbsoluteFill>'));
});
