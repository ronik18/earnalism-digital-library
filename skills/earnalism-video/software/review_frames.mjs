// Inspect the actual renderer before expensive full exports; no media overwrite.
import {bundle} from '@remotion/bundler';
import {selectComposition,renderStill} from '@remotion/renderer';
import fs from 'node:fs';import path from 'node:path';
const [propsFile,directory]=process.argv.slice(2);if(!propsFile||!directory||fs.existsSync(directory))throw Error('Provide props and a new review frame directory'); 
const props=JSON.parse(fs.readFileSync(propsFile));fs.mkdirSync(directory,{recursive:true});props.burnCaptions=true;
const browserExecutable=process.env.EARNALISM_RENDER_BROWSER||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const serveUrl=await bundle({entryPoint:path.resolve('src/index.tsx'),publicDir:path.resolve('public')});
const shots=props.scenes.map(s=>({name:s.id,time:s.start+.58*(s.end-s.start)}));
for(const s of props.scenes){if(s.diagram==='orbit'){const a=s.anchors.find(a=>a.phrase==='From the ground');if(a)for(const dt of [-.1,.7,1.9])shots.push({name:'bridge-'+String(dt),time:a.time+dt});}if(s.diagram==='phases'){const a=s.anchors.find(a=>a.phrase==='At first quarter');if(a)shots.push({name:'quarter',time:a.time+.6});}}
for(const id of ['Landscape','Portrait']){const composition=await selectComposition({browserExecutable,serveUrl,id,inputProps:props});for(const s of shots)await renderStill({browserExecutable,serveUrl,composition,inputProps:props,frame:Math.round(s.time*30),output:path.join(directory,`${id}-${s.name}.png`),scale:.5});}
console.log(JSON.stringify({directory,frames:shots.length*2}));
