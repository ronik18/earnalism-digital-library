import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

// Exercise the actual CLI's early validation before slow renderer dependencies.
// Full render/still checks separately exercise the real dependency/browser path.
// Missing arguments must fail promptly without opening Chrome or a server.
const result=spawnSync(process.execPath,[fileURLToPath(new URL('./render.mjs',import.meta.url))],{encoding:'utf8',timeout:8000,maxBuffer:1024*1024});
assert.equal(result.error,undefined,'Renderer startup stalled before argument validation');
assert.equal(result.status,1);
assert.match(result.stderr,/Usage: node sky_colour\/render\.mjs/);
console.log('PASS: real renderer CLI validates arguments before loading renderer dependencies within the bounded startup window; no browser/server launched');
const batch=fileURLToPath(new URL('./render-batch.mjs',import.meta.url));
const missing=spawnSync(process.execPath,[batch],{encoding:'utf8',timeout:8000,maxBuffer:1024*1024});
assert.equal(missing.error,undefined);assert.equal(missing.status,1);assert.match(missing.stderr,/Usage: node sky_colour\/render-batch\.mjs/);
const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'sky-batch-protection-'));
try{
 const lock=path.join(temporary,'.sky-render-batch-lock.json'),original='{"preserve":"existing attempt"}';fs.writeFileSync(lock,original);
 const result=spawnSync(process.execPath,[batch,temporary],{encoding:'utf8',timeout:8000,maxBuffer:1024*1024});
 assert.equal(result.error,undefined);assert.equal(result.status,1);assert.match(result.stderr,/Existing\/partial batch preserved/);
 assert.equal(fs.readFileSync(lock,'utf8'),original);assert.deepEqual(fs.readdirSync(temporary),['.sky-render-batch-lock.json']);
}finally{fs.rmSync(temporary,{recursive:true,force:true});}
console.log('PASS: batch CLI fails promptly without arguments and preserves an existing attempt before any compile/browser work');
