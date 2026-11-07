// One immutable compile and one explicitly closed browser for this private set.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {assertTimeline} from './model.mjs';
import {loadRenderLibraries} from '../src/render-runtime.mjs';

const folder=process.argv[2];
if(!folder)throw Error('Usage: node sky_colour/render-batch.mjs FRESH_ASSEMBLED_ROOT');
if(process.argv[3]&&process.argv[3]!=='--portrait-only')throw Error('Unknown render mode');
const root=path.resolve(folder),base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const jobs=[['landscape','props.json','SkyColourLandscape'],['shorts','shorts-props.json','SkyColourShorts'],['clean-shorts','clean-shorts-props.json','SkyColourCleanShorts']].filter(([fmt])=>process.argv[3]!=='--portrait-only'||fmt!=='landscape');
const lock=path.join(root,'.sky-render-batch-lock.json');
if(fs.existsSync(lock)||fs.existsSync(path.join(root,'render-bundle')))throw Error('Existing/partial batch preserved; use a fresh candidate');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const inputs={};
for(const [fmt,props] of jobs){assertTimeline(JSON.parse(fs.readFileSync(path.join(root,props),'utf8')));inputs[props]=hash(path.join(root,props));if(fs.existsSync(path.join(root,fmt,'animation.mp4')))throw Error('Refusing overwrite '+fmt);}
const sourcePaths=Object.fromEntries(['index.tsx','model.mjs','layout.mjs','append_ident.py'].map(n=>[n,path.join(base,'sky_colour',n)]));
for(const n of ['BrandWatermark.tsx','branding.mjs','social-safe-area.mjs','render-runtime.mjs'])sourcePaths['src/'+n]=path.join(base,'src',n);
for(const [n,p] of Object.entries(sourcePaths))inputs['source/'+n]=hash(p);
fs.writeFileSync(lock,JSON.stringify({state:'PRIVATE_RENDERING',inputs,publication_approved:false},null,2),{flag:'wx'});
const {openBrowser,selectComposition,renderMedia,bundle,runtimeRoot,versions}=await loadRenderLibraries(base);
console.log('One compile for selected formats');
let compileNext=20;
const serveUrl=await bundle({entryPoint:path.join(base,'sky_colour/index.tsx'),publicDir:path.join(base,'refraction/public'),rootDir:runtimeRoot,outDir:path.join(root,'render-bundle'),onProgress:p=>{if(p>=compileNext){console.log('Compile '+Math.round(p)+'%');compileNext+=20;}}});
console.log('Compile complete; opening one rendering browser');
const browser=await openBrowser('chrome',{browserExecutable:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const results=[];
try{
 for(const [fmt,props,id] of jobs){
  if(hash(path.join(root,props))!==inputs[props])throw Error('Timing props changed during render');
  const inputProps=JSON.parse(fs.readFileSync(path.join(root,props),'utf8'));
  const appendPortraitIdent=fmt!=='landscape';
  if(appendPortraitIdent&&inputProps.outro!==true)throw Error('Full portrait delivery requires its approved end ident');
  const renderProps=appendPortraitIdent?{...inputProps,outro:false}:inputProps;
  const composition=await selectComposition({serveUrl,id,inputProps:renderProps,puppeteerInstance:browser});
  const outputLocation=path.join(root,fmt,appendPortraitIdent?'body-animation.mp4':'animation.mp4');fs.mkdirSync(path.dirname(outputLocation),{recursive:true});let next=.2;
  console.log(fmt+': '+composition.durationInFrames+' frames');
  await renderMedia({serveUrl,composition,inputProps:renderProps,puppeteerInstance:browser,outputLocation,codec:'h264',pixelFormat:'yuv420p',colorSpace:'bt709',crf:20,disableSharedMemoryCapture:true,imageFormat:'png',concurrency:4,onProgress:({progress})=>{if(progress>=next){console.log(fmt+' '+Math.round(progress*100)+'%');next+=.2;}}});
  if(appendPortraitIdent){console.log(fmt+': appending pinned silent ident through FFmpeg');execFileSync('python3',[path.join(base,'sky_colour/append_ident.py'),path.join(root,fmt),String(composition.durationInFrames)],{stdio:'inherit'});}
  results.push({format:fmt,frames:composition.durationInFrames+(appendPortraitIdent?90:0),body_frames:appendPortraitIdent?composition.durationInFrames:null,ident_method:appendPortraitIdent?'Pinned FFmpeg visual append; no audio processing':'Remotion sequence',animation_sha256:hash(path.join(root,fmt,'animation.mp4'))});
 }
}finally{await browser.close({silent:true});}
for(const [n,p] of Object.entries(sourcePaths))if(hash(p)!==inputs['source/'+n])throw Error('Source changed during render');
fs.writeFileSync(path.join(root,'render-batch.json'),JSON.stringify({state:'SILENT_ANIMATIONS_RENDERED_REQUIRES_SOUNDTRACK_MUX',inputs,results,compile_count:1,browser_closed:true,runtimeRoot,versions,publication_approved:false},null,2),{flag:'wx'});
console.log('All private animations complete; browser closed; narration integration still requires mux');
