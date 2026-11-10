import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {execFileSync} from 'node:child_process';
import {streamPngFrames} from '../src/stream_frames.mjs';
test('ordered PNG pipe encodes exact frames with no image sequence and preserves existing outputs',async()=>{
 const d=fs.mkdtempSync(path.join(os.tmpdir(),'earnalism-stream-unit-'));
 try{
  const image=execFileSync('ffmpeg',['-v','error','-f','lavfi','-i','color=c=teal:s=64x64:r=30','-frames:v','1','-f','image2pipe','-c:v','png','-']);
  const output=path.join(d,'result.mp4');let outputDir,concurrency;
  const renderFrames=async opts=>{outputDir=opts.outputDir;concurrency=opts.concurrency;for(let n=0;n<3;n++)await opts.onFrameBuffer(image,n);};
  const r=await streamPngFrames({renderFrames,renderOptions:{composition:{fps:30}},output,frames:3});
  assert.equal(r.frames,3);assert.equal(r.png_sequence_files_written,0);assert.equal(outputDir,null);assert.equal(concurrency,1);
  assert.equal(fs.readdirSync(d).length,1);
  const before=fs.readFileSync(output);await assert.rejects(()=>streamPngFrames({renderFrames,renderOptions:{composition:{fps:30}},output,frames:3}),/Existing/);assert.deepEqual(fs.readFileSync(output),before);
 }finally{fs.rmSync(d,{recursive:true,force:true});}
});
test('out-of-order capture cannot become a completed output',async()=>{
 const d=fs.mkdtempSync(path.join(os.tmpdir(),'earnalism-stream-order-'));
 try{const output=path.join(d,'bad.mp4');
  await assert.rejects(()=>streamPngFrames({renderFrames:async opts=>opts.onFrameBuffer(Buffer.from('bad'),1),renderOptions:{composition:{fps:30}},output,frames:3}),/Out-of-order/);assert(!fs.existsSync(output));
 }finally{fs.rmSync(d,{recursive:true,force:true});}
});
test('invalid disk reserves are rejected before capture or encoder/filesystem work',async()=>{
 let called=false;
 for(const minFreeBytes of [NaN,Infinity,-Infinity,'629145600',null,true,0,600*1024*1024-1,600*1024*1024+.5,Number.MAX_SAFE_INTEGER+1]){
  await assert.rejects(()=>streamPngFrames({renderFrames:async()=>{called=true;},renderOptions:{composition:{fps:30}},output:'/nonexistent-parent/result.mp4',frames:3,minFreeBytes}),/Disk reserve/);
 }
 assert.equal(called,false);
});
test('missing captured frames never publish a completed output',async()=>{
 const d=fs.mkdtempSync(path.join(os.tmpdir(),'earnalism-stream-missing-'));
 try{
  const image=execFileSync('ffmpeg',['-v','error','-f','lavfi','-i','color=c=teal:s=64x64:r=30','-frames:v','1','-f','image2pipe','-c:v','png','-']);
  const output=path.join(d,'incomplete.mp4');
  await assert.rejects(()=>streamPngFrames({renderFrames:async opts=>{await opts.onFrameBuffer(image,0);await opts.onFrameBuffer(image,1);},renderOptions:{composition:{fps:30}},output,frames:3}),/Captured frame count differs/);
  assert.equal(fs.existsSync(output),false);
 }finally{fs.rmSync(d,{recursive:true,force:true});}
});
test('unsupported or missing frame rate cannot silently change duration',async()=>{
 let called=false;
 for(const fps of [undefined,24,25,29.97,60,'30',NaN]){
  await assert.rejects(()=>streamPngFrames({renderFrames:async()=>{called=true;},renderOptions:{composition:{fps}},output:'/nonexistent-parent/result.mp4',frames:3}),/30 fps/);
 }
 assert.equal(called,false);
});
