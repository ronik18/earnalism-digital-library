import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const script=fileURLToPath(new URL('./render-batch.mjs',import.meta.url));
const missing=spawnSync(process.execPath,[script],{encoding:'utf8',timeout:8000,maxBuffer:1024*1024});
assert.equal(missing.error,undefined);assert.equal(missing.status,1);assert.match(missing.stderr,/Usage: node rainbow\/render-batch/);
const folder=fs.mkdtempSync(path.join(os.tmpdir(),'rainbow-batch-preservation-'));
try{
 const lock=path.join(folder,'.rainbow-render-batch-lock.json'),before='{"preserve":"existing attempt"}';fs.writeFileSync(lock,before);
 const result=spawnSync(process.execPath,[script,folder],{encoding:'utf8',timeout:8000,maxBuffer:1024*1024});
 assert.equal(result.error,undefined);assert.equal(result.status,1);assert.match(result.stderr,/Existing\/partial batch preserved/);
 assert.equal(fs.readFileSync(lock,'utf8'),before);assert.deepEqual(fs.readdirSync(folder),['.rainbow-render-batch-lock.json']);
}finally{fs.rmSync(folder,{recursive:true,force:true});}
console.log('PASS: batch CLI validates early and preserves existing/partial candidate before compilation or browser launch');
