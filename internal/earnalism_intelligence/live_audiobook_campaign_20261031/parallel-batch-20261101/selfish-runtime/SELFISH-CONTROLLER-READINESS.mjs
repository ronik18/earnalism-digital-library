export function quantizeSeekTarget(value, min, max, step) {
  if (![value,min,max,step].every(Number.isFinite) || step <= 0 || value < min || value > max) throw Error('Invalid seek contract');
  return Math.min(max, Number((min + Math.round((value-min)/step)*step).toFixed(6)));
}
export async function waitForAdvancingNativePlayback({read,poll,now,maximumMs,segment,rate=1}) {
  const deadline=now()+maximumMs; let prior=null;
  while(now()<deadline) {
    const a=await read();
    const ready=a && a.segment===segment && a.rate===rate && !a.paused && !a.ended && a.readyState>=2 && Number.isFinite(a.currentTime);
    if(ready && prior && a.currentTime-prior.currentTime>=0.04) return a;
    prior=ready?a:null;
    await poll();
  }
  throw Error('Native playback did not advance at expected segment/rate');
}
export async function awaitBoundedTerminalAck({capture,confirmed,poll,now,startedAt,maximumMs=12000}) {
  const deadline=Math.min(now()+maximumMs,startedAt+67000);
  while(!confirmed() && now()<deadline) { await capture(); if(!confirmed()) await poll(); }
  return confirmed();
}
