import {resolveRenderBrowser, resolveRenderPublic} from '../src/render-browser.mjs';
import {loadRenderLibraries} from '../src/render-runtime.mjs';
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {assertTimeline} from './model.mjs';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [propsFile,out,format='SkyColourLandscape',stillFrame]=process.argv.slice(2);
if(!propsFile||!out)throw Error('Usage: node sky_colour/render.mjs props.json output SkyColourLandscape|SkyColourShorts|SkyColourCleanShorts|CoverLandscape|CoverShorts [frame,...]');
if(fs.existsSync(out))throw Error('Refusing overwrite '+out);
const inputProps=JSON.parse(fs.readFileSync(propsFile,'utf8'));if(!format.startsWith('Cover'))assertTimeline(inputProps);
const browserExecutable=resolveRenderBrowser();
console.log('Bundling '+format);
const {selectComposition,renderMedia,renderStill,bundle,runtimeRoot}=await loadRenderLibraries(base);
const serveUrl=await bundle({entryPoint:path.join(base,'sky_colour/index.tsx'),publicDir:resolveRenderPublic(base),rootDir:runtimeRoot});
console.log('Bundle ready; selecting '+format);
const composition=await selectComposition({serveUrl,id:format,inputProps,browserExecutable});fs.mkdirSync(path.dirname(path.resolve(out)),{recursive:true});
console.log('Composition ready: '+composition.durationInFrames+' frames');
if(stillFrame!==undefined){for(const value of stillFrame.split(',')){const frame=Number(value);if(!Number.isInteger(frame)||frame<0||frame>=composition.durationInFrames)throw Error('Frame outside composition');const output=stillFrame.includes(',')?out.replace(/\.png$/i,'-'+value+'.png'):out;if(fs.existsSync(output))throw Error('Refusing overwrite '+output);await renderStill({serveUrl,composition,inputProps,browserExecutable,output,frame,imageFormat:'png'});}}
else{let threshold=.2;await renderMedia({serveUrl,composition,inputProps,browserExecutable,outputLocation:out,codec:'h264',pixelFormat:'yuv420p',colorSpace:'bt709',crf:20,disableSharedMemoryCapture:true,imageFormat:'png',frameRange:process.env.SKY_COLOUR_FRAME_RANGE?JSON.parse(process.env.SKY_COLOUR_FRAME_RANGE):undefined,concurrency:4,onProgress:({progress})=>{if(progress>=threshold){console.log(Math.round(progress*100)+'%');threshold+=.2;}}});console.log('SILENT ENGINEERING ANIMATION ONLY. This is not narration integration.');}console.log(out);
