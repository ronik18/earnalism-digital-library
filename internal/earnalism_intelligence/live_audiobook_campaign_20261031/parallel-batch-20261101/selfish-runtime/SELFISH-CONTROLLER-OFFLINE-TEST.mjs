import assert from 'node:assert/strict';
import {waitForAdvancingNativePlayback,quantizeSeekTarget,awaitBoundedTerminalAck} from './SELFISH-CONTROLLER-READINESS.mjs';
const results=[];
for(const latency of [3000,5000]) {
 let t=0, readyAt=null;
 const a=await waitForAdvancingNativePlayback({now:()=>t,maximumMs:12000,segment:'group-01',poll:async()=>{t+=200},read:async()=>({segment:'group-01',paused:t<latency,ended:false,rate:1,readyState:4,currentTime:t<latency?10.722395:(t-latency)/1000})});
 readyAt=t; assert.ok(readyAt>latency);assert.ok(a.currentTime>0); results.push({case:'deferred Play '+latency+'ms cannot release next seek early',pass:true,readyAt});
}
let t=0;await assert.rejects(waitForAdvancingNativePlayback({now:()=>t,maximumMs:1000,segment:'group-01',poll:async()=>{t+=200},read:async()=>({segment:'group-01',paused:true,ended:false,rate:1,readyState:4,currentTime:10.722395})}));results.push({case:'metadata ready but paused never qualifies',pass:true});
t=0;await assert.rejects(waitForAdvancingNativePlayback({now:()=>t,maximumMs:1000,segment:'group-01',poll:async()=>{t+=200},read:async()=>({segment:'group-01',paused:false,ended:false,rate:1.5,readyState:4,currentTime:t/1000})}));results.push({case:'wrong native speed fails closed',pass:true});
for(const x of [0,55,61,773.1])assert.equal(quantizeSeekTarget(x,0,777.12,.1),x);assert.equal(quantizeSeekTarget(60.96,0,777.12,.1),61);assert.ok(58.96-55>3.9);results.push({case:'actual range step and larger transition observation margin',pass:true});
for(const latency of [3000,5000]) {t=0;let ack=false;assert.equal(await awaitBoundedTerminalAck({now:()=>t,startedAt:0,capture:async()=>{ack=t>=latency},confirmed:()=>ack,poll:async()=>{t+=200}}),true);assert.ok(t>=latency);results.push({case:'terminal ACK deferred '+latency+'ms retained before close',pass:true});}
t=65000;let ack=false;assert.equal(await awaitBoundedTerminalAck({now:()=>t,startedAt:0,capture:async()=>{},confirmed:()=>ack,poll:async()=>{t+=200}}),false);assert.equal(t,67000);results.push({case:'missing ACK remains unverified and preserves70s hard-close',pass:true});
for (const latency of [3000,5000]) {
 t=0;let group1Seen=false;
 const read=async()=>{const active=t>=latency;const offset=(t-latency)/1000;return {segment:active&&offset>=3.96?'group-02':'group-01',paused:!active,ended:false,rate:1,readyState:4,currentTime:active?(offset>=3.96?offset-3.96:55+offset):4};};
 await waitForAdvancingNativePlayback({read,poll:async()=>{t+=200},now:()=>t,maximumMs:12000,segment:'group-01'});group1Seen=true;
 await waitForAdvancingNativePlayback({read,poll:async()=>{t+=200},now:()=>t,maximumMs:12000,segment:'group-02'});
 assert.ok(group1Seen);assert.ok(t>=latency+3960);results.push({case:'55s backseek with '+latency+'ms renewal observes Group01 then natural Group02',pass:true});
}
console.log(JSON.stringify({offlineOnly:true,liveAcceptanceProven:false,cases:results},null,2));
