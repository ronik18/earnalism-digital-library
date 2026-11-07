import assert from 'node:assert/strict';import test from 'node:test';import fs from 'node:fs';import crypto from 'node:crypto';
import {watermarkAsset,watermarkLayout,schematicContext} from './branding.mjs';
import {assertUiClear,reviewProfileForFrame} from './social-safe-area.mjs';
import {assertLayout} from '../rainbow/layout.mjs';
test('full website header asset is byte-bound without cropping lettering',()=>{
 const bytes=fs.readFileSync(new URL('../public/'+watermarkAsset.path,import.meta.url));
 assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),watermarkAsset.sha256);
 assert.deepEqual(watermarkAsset.crop,{x:0,y:0,width:2400,height:720});
});
test('complete rectangular logo clears scaled portrait UI',()=>{
 for(const [w,h] of [[1080,1920],[720,1280],[2160,3840],[1080,1440]]){const q=watermarkLayout(w,h);assertUiClear('full lockup',{x:q.left,y:q.top,width:q.width,height:q.height},reviewProfileForFrame(w,h));assert.equal(q.width/q.height,2400/720);}
 const q=watermarkLayout(1080,1920);assert.deepEqual([q.left,q.top,q.width,q.height],[600,280,300,90]);
});
test('legacy icon overrides, edge clipping and content collisions fail',()=>{
 for(const placement of [{left:832,top:292,size:56},{left:80,top:44,width:300},{left:850,top:280,width:300},{left:80,top:280,width:NaN}])assert.throws(()=>watermarkLayout(1080,1920,{placement}));
 assert.throws(()=>watermarkLayout(1080,1920,{occupiedRects:[{x:600,y:300,width:300,height:145}]}),/protected content/);
 assert.throws(()=>watermarkLayout(1080,1920,{occupiedRects:null}));
});
test('both explanatory layouts reserve the complete logo without covering lesson regions',()=>{
 for(const p of [true,false]){const l=assertLayout(p),q=watermarkLayout(p?1080:1920,p?1920:1080,{placement:p?l.watermark:undefined,occupiedRects:[l.heading,l.diagram,l.support,l.captions]});assert(q.height<110);}
});
test('covers and landscape preserve aspect ratio; exact source remains intact',()=>{
 for(const [w,h,surface] of [[1080,1920,'cover'],[1920,1080,'cover'],[1920,1080,'video']]){const q=watermarkLayout(w,h,{surface});assert.equal(q.width/q.height,2400/720);assert(q.left+q.width<=w);assert(q.top+q.height<=h);}
});
test('schematic context remains brief',()=>{assert(schematicContext({diagram:'orbit',start:10},10.5));assert.equal(schematicContext({diagram:'orbit',start:10},14),null);});

test("portrait brand remains right anchored inside scaled action-rail reserve",()=>{for(const [w,h] of [[1080,1920],[720,1280],[2160,3840],[1080,1440]]){const q=watermarkLayout(w,h);assert(Math.abs(w-q.left-q.width-180*w/1080)<1e-8);}});
