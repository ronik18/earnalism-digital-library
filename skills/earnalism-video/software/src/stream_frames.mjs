// Bounded PNG transport: one screenshot at a time to FFmpeg, no image-sequence files.
import fs from 'node:fs';import path from 'node:path';import {spawn,execFileSync} from 'node:child_process';
export function availableBytes(directory){const s=fs.statfsSync(directory);return Number(s.bavail)*Number(s.bsize);}
export async function streamPngFrames({renderFrames,renderOptions,output,frames,minFreeBytes=600*1024*1024}){
 if(!Number.isSafeInteger(frames)||frames<1)throw Error('Positive exact frame count required');
 if(!Number.isSafeInteger(minFreeBytes)||minFreeBytes<600*1024*1024)throw Error('Disk reserve must be a finite safe integer of at least 600 MiB');
 if(typeof renderFrames!=='function')throw Error('A renderFrames callback is required');
 if(renderOptions?.composition?.fps!==30)throw Error('This tested capture profile requires a 30 fps composition');
 const partial=output+'.partial.mp4',dir=path.dirname(output);
 if(fs.existsSync(output)||fs.existsSync(partial))throw Error('Existing output/partial preserved');
 if(availableBytes(dir)<minFreeBytes+50*1024*1024)throw Error('Insufficient space for bounded capture');
 const encoder=spawn('ffmpeg',['-v','error','-n','-f','image2pipe','-vcodec','png','-framerate','30','-i','pipe:0','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,setsar=1,format=yuv420p','-an','-c:v','libx264','-preset','fast','-crf','20','-r','30','-video_track_timescale','90000','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',partial],{stdio:['pipe','ignore','pipe']});
 let errors='',count=0,peakBufferBytes=0,minObservedFree=availableBytes(dir),failure;
 encoder.stderr.on('data',b=>{errors=(errors+b).slice(-8000);});
 encoder.stdin.on('error',e=>{failure=e;});
 const done=new Promise((resolve,reject)=>{encoder.once('error',reject);encoder.once('close',code=>code===0?resolve():reject(Error('Encoder failed: '+errors)));});
 done.catch(()=>{});
 try{
  await renderFrames({...renderOptions,outputDir:null,imageFormat:'png',concurrency:1,
   onFrameBuffer:async(buffer,frame)=>{
    if(frame!==count)throw Error('Out-of-order or missing capture frame');
    if(failure)throw failure;
    const free=availableBytes(dir);minObservedFree=Math.min(minObservedFree,free);
    if(free<minFreeBytes)throw Error('Disk reserve reached; capture stopped safely');
    peakBufferBytes=Math.max(peakBufferBytes,buffer.length);
    await new Promise((resolve,reject)=>encoder.stdin.write(buffer,e=>e?reject(e):resolve()));count++;
   }});
  if(count!==frames)throw Error('Captured frame count differs from plan');
  encoder.stdin.end();await done;
  const info=JSON.parse(execFileSync('ffprobe',['-v','error','-count_frames','-select_streams','v:0','-show_streams','-of','json',partial],{encoding:'utf8'})).streams[0];
  if(Number(info.nb_read_frames)!==frames||info.pix_fmt!=='yuv420p'||info.r_frame_rate!=='30/1')throw Error('Encoded frame count/format/rate mismatch');
  // Exclusive publication of this local filename; never overwrite a racing candidate.
  fs.linkSync(partial,output);fs.unlinkSync(partial);
  return {frames:count,peak_frame_buffer_bytes:peakBufferBytes,min_observed_free_bytes:minObservedFree,png_sequence_files_written:0,output_bytes:fs.statSync(output).size,codec:'h264',time_base:info.time_base};
 }catch(e){encoder.stdin.destroy();encoder.kill('SIGTERM');await done.catch(()=>{});throw e;}
}
