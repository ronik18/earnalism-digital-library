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

test('actual component default places the full exact emblem inside portrait reservations',()=>{
 dimensions={width:1080,height:1920};const tree=BrandWatermark(),q=branding.watermarkLayout(1080,1920),s=tree.props.style;
 assert.equal(s.top,292);assert.equal(s.right,192);assert.equal(s.width,56);assert.equal(s.height,56);
 assert.equal(s.overflow,'hidden');assert.equal(tree.props['aria-label'],'Earnalism emblem');
 const img=tree.children[0],c=branding.watermarkAsset.crop;
 assert.equal(img.type,'Img');assert.equal(img.props.src,'/'+branding.watermarkAsset.path);
 assert.equal(img.props.style.left,-c.x*q.scale);assert.equal(img.props.style.top,-c.y*q.scale);
 assert.equal(img.props.style.width,branding.watermarkAsset.sourceWidth*q.scale);
 assert.equal(img.props.style.height,branding.watermarkAsset.sourceHeight*q.scale);
});
test('actual component validates override, content collision and separate cover branch',()=>{
 dimensions={width:1080,height:1920};
 assert.throws(()=>BrandWatermark({placement:{left:943,top:44,size:72}}),/reserved mobile UI/);
 assert.throws(()=>BrandWatermark({occupiedRects:[{x:820,y:280,width:80,height:90}]}),/protected content/);
 const p={left:800,top:350,size:60},tree=BrandWatermark({placement:p}),s=tree.props.style;
 assert.equal(s.top,p.top);assert.equal(s.right,1080-p.left-p.size);assert.equal(s.width,p.size);
 const cover=BrandWatermark({surface:'cover'}).props.style;
 assert.equal(cover.top,44);assert.equal(cover.right,65);assert.equal(cover.width,72);
 dimensions={width:1920,height:1080};const landscape=BrandWatermark().props.style;
 assert.equal(landscape.top,48);assert.equal(landscape.right,70);assert.equal(landscape.width,82);
});
