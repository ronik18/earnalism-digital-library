import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadRenderLibraries} from './render-runtime.mjs';
const folder=fs.mkdtempSync(path.join(os.tmpdir(),'earnalism-runtime-pin-'));
const previous=process.env.EARNALISM_REMOTION_RUNTIME;
try{
 fs.writeFileSync(path.join(folder,'package.json'),'{}');
 const dependency=path.join(folder,'node_modules/remotion');fs.mkdirSync(dependency,{recursive:true});
 fs.writeFileSync(path.join(dependency,'package.json'),JSON.stringify({name:'remotion',version:'0.0.0'}));
 process.env.EARNALISM_REMOTION_RUNTIME=folder;
 await assert.rejects(loadRenderLibraries(fileURLToPath(new URL('../',import.meta.url))),/differs from pinned project dependency: remotion/);
}finally{
 if(previous===undefined)delete process.env.EARNALISM_REMOTION_RUNTIME;else process.env.EARNALISM_REMOTION_RUNTIME=previous;
 fs.rmSync(folder,{recursive:true,force:true});
}
console.log('PASS: isolated runtime with a different package version is rejected before renderer loading');
