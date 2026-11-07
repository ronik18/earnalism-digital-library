// One compile and one explicitly closed headless browser for a fresh candidate.
// Rendering produces silent animation; root pipeline must mux the protected B
// soundtrack and qualify the actual final audiovisual files separately.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {loadRenderLibraries} from '../src/render-runtime.mjs';
import {assertTimeline} from './model.mjs';
const folder=process.argv[2];if(!folder)throw Error('Usage: node rainbow/render-batch.mjs FRESH_ASSEMBLED_ROOT');
if(process.argv.length>3)throw Error('Unknown rendering argument');
const root=path.resolve(folder),base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const lock=path.join(root,'.rainbow-render-batch-lock.json');
if(fs.existsSync(lock)||fs.existsSync(path.join(root,'render-bundle')))throw Error('Existing/partial batch preserved; use a fresh candidate');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const jobs=[['landscape','props.json','RainbowLandscape'],['shorts','shorts-props.json','RainbowShorts'],['clean-shorts','clean-shorts-props.json','RainbowCleanShorts']];
const inputs={},sourcePaths=Object.fromEntries(['index.tsx','model.mjs','layout.mjs','render-batch.mjs'].map(n=>[n,path.join(base,'rainbow',n)]));
for(const n of ['BrandWatermark.tsx','branding.mjs','social-safe-area.mjs','render-runtime.mjs'])sourcePaths['src/'+n]=path.join(base,'src',n);
sourcePaths['shared/append_ident.py']=path.join(base,'sky_colour/append_ident.py');
for(const [format,props] of jobs){const p=path.join(root,props);assertTimeline(JSON.parse(fs.readFileSync(p,'utf8')));inputs[props]=hash(p);for(const n of ['animation.mp4','body-animation.mp4'])if(fs.existsSync(path.join(root,format,n)))throw Error('Refusing overwrite '+format+'/'+n);}
for(const format of ['landscape','shorts'])if(fs.existsSync(path.join(root,'thumbnail-'+format+'.png')))throw Error('Refusing overwrite thumbnail');
for(const [n,p] of Object.entries(sourcePaths))inputs['source/'+n]=hash(p);
fs.writeFileSync(lock,JSON.stringify({state:'PRIVATE_RENDERING',inputs,publication_approved:false},null,2),{flag:'wx'});
const {bundle,selectComposition,renderMedia,renderStill,openBrowser,runtimeRoot,versions}=await loadRenderLibraries(base);
let compileNext=20;
const serveUrl=await bundle({entryPoint:path.join(base,'rainbow/index.tsx'),publicDir:path.join(base,'refraction/public'),rootDir:runtimeRoot,outDir:path.join(root,'render-bundle'),onProgress:p=>{if(p>=compileNext){console.log('Compile '+Math.round(p)+'%');compileNext+=20;}}});
const browser=await openBrowser('chrome',{browserExecutable:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const results=[];
try{
 for(const [format,props,id] of jobs){
  if(hash(path.join(root,props))!==inputs[props])throw Error('Timing props changed during render');
  const input=JSON.parse(fs.readFileSync(path.join(root,props),'utf8')),appendPortrait=format!=='landscape';
  if(input.outro!==true)throw Error('Final delivery must include its approved end ident');
  const inputProps=appendPortrait?{...input,outro:false}:input;
  const composition=await selectComposition({serveUrl,id,inputProps,puppeteerInstance:browser});
  const outputLocation=path.join(root,format,appendPortrait?'body-animation.mp4':'animation.mp4');fs.mkdirSync(path.dirname(outputLocation),{recursive:true});
  let next=.2;console.log(format+': '+composition.durationInFrames+' frames');
  await renderMedia({serveUrl,composition,inputProps,puppeteerInstance:browser,outputLocation,codec:'h264',pixelFormat:'yuv420p',colorSpace:'bt709',crf:20,disableSharedMemoryCapture:true,imageFormat:'png',concurrency:4,onProgress:({progress})=>{if(progress>=next){console.log(format+' '+Math.round(progress*100)+'%');next+=.2;}}});
  if(appendPortrait)execFileSync('python3',[path.join(base,'sky_colour/append_ident.py'),path.join(root,format),String(composition.durationInFrames)],{stdio:'inherit'});
  results.push({format,frames:composition.durationInFrames+(appendPortrait?90:0),body_frames:appendPortrait?composition.durationInFrames:null,ident_method:appendPortrait?'Pinned tested FFmpeg visual append':'Remotion sequence',animation_sha256:hash(path.join(root,format,'animation.mp4'))});
 }
 for(const [format,id] of [['landscape','CoverLandscape'],['shorts','CoverShorts']]){
  const composition=await selectComposition({serveUrl,id,puppeteerInstance:browser}),output=path.join(root,'thumbnail-'+format+'.png');
  await renderStill({serveUrl,composition,puppeteerInstance:browser,output,frame:0,imageFormat:'png'});
  results.push({format:format+'-cover',sha256:hash(output)});
 }
}finally{await browser.close({silent:true});}
for(const [n,p] of Object.entries(sourcePaths))if(hash(p)!==inputs['source/'+n])throw Error('Source changed during render');
fs.writeFileSync(path.join(root,'render-batch.json'),JSON.stringify({state:'SILENT_ANIMATIONS_RENDERED_REQUIRES_SOUNDTRACK_MUX',inputs,results,compile_count:1,browser_closed:true,runtimeRoot,versions,publication_approved:false},null,2),{flag:'wx'});
console.log('Private silent animations/covers complete. B soundtrack mux and actual AV qualification remain.');
