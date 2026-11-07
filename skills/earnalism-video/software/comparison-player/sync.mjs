export function createSyncPair(earlier,latest,onStatus=()=>{}) {
 let wanted=false,starting=false,closed=false;
 earlier.muted=true;latest.muted=false;
 const pause=()=>{wanted=false;earlier.pause();latest.pause();if(Number.isFinite(latest.currentTime)&&Math.abs(earlier.currentTime-latest.currentTime)>.001)earlier.currentTime=latest.currentTime;onStatus('Paused');};
 async function start(){
  if(starting||closed||!wanted)return;
  if(earlier.readyState<3||latest.readyState<3){onStatus('Buffering both videos…');return;}
  starting=true;earlier.muted=true;
  if(Math.abs(earlier.currentTime-latest.currentTime)>.015)earlier.currentTime=latest.currentTime;
  try{await Promise.all([earlier.play(),latest.play()]);if(!wanted){earlier.pause();latest.pause();}else onStatus('Playing together · one soundtrack');}
  catch{pause();onStatus('Press Play to start both videos.');}finally{starting=false;}
 }
 const play=async()=>{wanted=true;if(latest.ended)seek(0);await start();};
 function seek(t){const duration=Math.min(earlier.duration||Infinity,latest.duration||Infinity);t=Math.max(0,Math.min(t,duration));earlier.currentTime=t;latest.currentTime=t;}
 function buffer(){if(!wanted)return;earlier.pause();latest.pause();onStatus('Buffering both videos…');}
 function tick(){if(wanted&&!starting&&earlier.readyState>=3&&latest.readyState>=3){if(earlier.paused||latest.paused)start();else if(Math.abs(earlier.currentTime-latest.currentTime)>.045)earlier.currentTime=latest.currentTime;}return Math.abs(earlier.currentTime-latest.currentTime);}
 earlier.addEventListener('volumechange',()=>{if(!earlier.muted)earlier.muted=true;});
 for(const v of [earlier,latest]){v.addEventListener('waiting',buffer);v.addEventListener('canplay',()=>{if(wanted)start();});v.addEventListener('ended',()=>{pause();onStatus('Finished · Replay starts both again');});v.addEventListener('error',()=>{pause();onStatus('Video could not load. Reload this private page.');});}
 return {play,pause,seek,tick,replay:async()=>{seek(0);await play();},get playing(){return wanted;},close:()=>{pause();closed=true;}};
}
