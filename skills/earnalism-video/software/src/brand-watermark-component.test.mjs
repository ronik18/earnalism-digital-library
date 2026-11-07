import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import * as branding from './branding.mjs';

// Exercise the actual TSX component without opening a browser or rendering media.
// esbuild comes from the existing locked renderer installation; no install here.
const requireRuntime=createRequire(process.env.EARNALISM_REMOTION_RUNTIME?
 path.join(path.resolve(process.env.EARNALISM_REMOTION_RUNTIME),'package.json'):new URL('../package.json',import.meta.url));
const {transformSync}=requireRuntime('esbuild');
const source=fs.readFileSync(new URL('./BrandWatermark.tsx',import.meta.url),'utf8');
const {code}=transformSync(source,{loader:'tsx',format:'cjs',jsx:'transform'});
let dimensions={width:1080,height:1920};
const module={exports:{}};
vm.runInNewContext(code,{module,exports:module.exports,require(id){
 if(id==='react')return {createElement:(type,props,...children)=>({type,props,children})};
 if(id==='remotion')return {Img:'Img',staticFile:p=>'/'+p,useVideoConfig:()=>dimensions};
 if(id==='./branding.mjs')return branding;
 throw Error('Unexpected component dependency '+id);
}});
const {BrandWatermark}=module.exports;

test('actual wrapper contains complete logo and lettering without a clipping crop',()=>{
 dimensions={width:1080,height:1920};const tree=BrandWatermark(),s=tree.props.style;
 assert.equal(s.width,300);assert.equal(s.height,90);assert.equal(s.top,280);
 assert.equal(s.overflow,undefined);assert.equal(s.background,'#fff9ed');
 const img=tree.children.find(child=>child&&child.type==='Img');assert.ok(img,'complete logo image exists');assert.equal(img.props.src,'/'+branding.watermarkAsset.path);
 assert.equal(img.props.style.objectFit,'contain');assert.equal(img.props.style.width,'100%');
 assert.equal(img.props.style.left,undefined);assert.equal(img.props.style.top,undefined);
});
test('component rejects stale icon placement and collisions; safe override retains aspect',()=>{
 dimensions={width:1080,height:1920};
 assert.throws(()=>BrandWatermark({placement:{left:832,top:292,size:56}}));
 assert.throws(()=>BrandWatermark({occupiedRects:[{x:80,y:300,width:730,height:145}]}),/protected content/);
 const q=BrandWatermark({placement:{left:80,top:280,width:320}}).props.style;
 assert.equal(q.width,320);assert.equal(q.height,96);
 dimensions={width:1920,height:1080};assert.equal(BrandWatermark().props.style.width,340);
});
