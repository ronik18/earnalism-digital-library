// Uses installed Chromium via its documented DevTools Protocol; no packages,
// production connections, browser profile, or downloaded renderer are needed.
import {spawn} from 'node:child_process';
import {mkdtempSync,readFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {renderReceipt} from './renderer.mjs';
const executable=process.env.CHROMIUM_EXECUTABLE;
if(!executable)throw new Error('Set CHROMIUM_EXECUTABLE to an already installed supported Chromium');
const profile=mkdtempSync(join(tmpdir(),'earnalism-receipt-browser-'));
const proc=spawn(executable,['--headless','--no-sandbox','--disable-gpu','--no-first-run','--disable-background-networking','--disable-component-update','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank']);
let socket;
try {
 const endpoint=await new Promise((resolve,reject)=>{let output='';const timer=setTimeout(()=>reject(Error('Chromium startup timed out')),20000);proc.stderr.on('data',x=>{output+=x;const m=output.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(m){clearTimeout(timer);resolve(m[1]);}});proc.on('exit',c=>reject(Error(`Chromium exited ${c}`)));});
 socket=new WebSocket(endpoint);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let seq=0;const pending=new Map();
 socket.onmessage=({data})=>{const r=JSON.parse(data);if(r.id){const p=pending.get(r.id);pending.delete(r.id);r.error?p.reject(Error(JSON.stringify(r.error))):p.resolve(r.result);}};
 const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));});
 const {targetId}=await send('Target.createTarget',{url:'about:blank'});
 const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
 const call=(m,p)=>send(m,p,sessionId);
 await call('Page.enable');await call('Network.enable');await call('Network.setBlockedURLs',{urls:['http://*','https://*']});
 const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const evidence={renderer:await send('Browser.getVersion'),networkAssets:'HTTP(S) blocked by CDP; embedded local image only',checks:[]};
 for(const name of ['receipt','email']){
  await call('Page.navigate',{url:pathToFileURL(new URL(`./output/${name}.html`,import.meta.url).pathname).href});
  for(let i=0;i<100;i++){if(await evaluate('document.readyState === "complete"'))break;await new Promise(r=>setTimeout(r,50));}
  await evaluate('document.fonts.ready.then(()=>Promise.all([...document.images].map(i=>i.decode())))');
  for(const width of [1100,390,320]){
   await call('Emulation.setDeviceMetricsOverride',{width,height:1123,deviceScaleFactor:1,mobile:false});
   const metrics=await evaluate(`(()=>{const all=[...document.querySelectorAll('main *')].filter(e=>!e.classList.contains('sr-only'));return {width:innerWidth,scroll:document.documentElement.scrollWidth,badImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length,overflow:all.filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>e.tagName),text:document.body.innerText,links:[...document.querySelectorAll('a')].map(a=>a.href)};})()`);
   assert.ok(metrics.scroll<=width,`${name} horizontal overflow at ${width}`);assert.equal(metrics.badImages,0);assert.deepEqual(metrics.overflow,[]);assert.ok(metrics.text.includes('₹49.00'));assert.ok(!metrics.text.includes('�'));
   const ax=await call('Accessibility.getFullAXTree');
   assert.ok(ax.nodes.some(n=>n.role?.value==='main'));assert.ok(ax.nodes.some(n=>n.role?.value==='heading'&&n.name?.value.includes(name==='receipt'?'Payment receipt':'Payment received')));
   const {contentSize}=await call('Page.getLayoutMetrics');
   const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:Math.ceil(contentSize.height),scale:1}});
   writeFileSync(new URL(`./output/${name}-${width}.png`,import.meta.url),Buffer.from(shot.data,'base64'));
   evidence.checks.push({name,width,scroll:metrics.scroll,brokenImages:metrics.badImages,overflow:metrics.overflow,accessibleMain:true,accessibleHeading:true});
  }
  if(name==='receipt'){
   await call('Emulation.setDeviceMetricsOverride',{width:794,height:1123,deviceScaleFactor:1,mobile:false});
   await call('Emulation.setEmulatedMedia',{media:'print'});
   const printMetrics=await evaluate('({height:document.querySelector("main").getBoundingClientRect().height,bottom:document.querySelector("footer").getBoundingClientRect().bottom,width:document.documentElement.scrollWidth})');
   assert.ok(printMetrics.bottom<1123,`A4 footer beyond page: ${printMetrics.bottom}`);
   const pdf=await call('Page.printToPDF',{printBackground:true,preferCSSPageSize:true,displayHeaderFooter:false,generateTaggedPDF:true,generateDocumentOutline:true,paperWidth:8.2677165354,paperHeight:11.692913386,marginTop:0,marginBottom:0,marginLeft:0,marginRight:0});
   writeFileSync(new URL('./output/receipt.pdf',import.meta.url),Buffer.from(pdf.data,'base64'));
   const shot=await call('Page.captureScreenshot',{format:'png',clip:{x:0,y:0,width:794,height:1123,scale:1}});writeFileSync(new URL('./output/receipt-a4.png',import.meta.url),Buffer.from(shot.data,'base64'));
   evidence.printMetrics=printMetrics;
   await call('Emulation.setEmulatedMedia',{media:'screen'});
  }
 }
 // Exercise maximum allowed identity/reference lengths independently of samples.
 const stress=JSON.parse(readFileSync(new URL('./sample.v1.json',import.meta.url)));
 stress.buyerSnapshot.name='W'.repeat(70);stress.buyerSnapshot.email='w'.repeat(104)+'@example.invalid';stress.capturedPaymentReference='W'.repeat(80);
 await call('Page.navigate',{url:'about:blank'});
 await call('Page.setDocumentContent',{frameId:(await call('Page.getFrameTree')).frameTree.frame.id,html:renderReceipt(stress)});
 await evaluate('document.fonts.ready.then(()=>Promise.all([...document.images].map(i=>i.decode())))');
 await call('Emulation.setDeviceMetricsOverride',{width:794,height:1123,deviceScaleFactor:1,mobile:false});
 await call('Emulation.setEmulatedMedia',{media:'print'});
 const stressBottom=await evaluate('document.querySelector("footer").getBoundingClientRect().bottom');
 assert.ok(stressBottom<1123,`Maximum length content exceeds A4: ${stressBottom}`);evidence.maximumLengthA4Footer=stressBottom;
 // WCAG 2 AA text pairs. Gold is decoration only; never used as body text.
 const rgb=h=>h.match(/\w\w/g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
 const lum=h=>rgb(h).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
 evidence.contrast=[];for(const fg of ['35292B','521D32','3E1727'])for(const bg of ['FFFAF3','F0E4D5']){const ratio=(Math.max(lum(fg),lum(bg))+.05)/(Math.min(lum(fg),lum(bg))+.05);assert.ok(ratio>=4.5);evidence.contrast.push({foreground:'#'+fg,background:'#'+bg,ratio:Number(ratio.toFixed(2))});}
 writeFileSync(new URL('./output/browser-verification.json',import.meta.url),JSON.stringify(evidence,null,2)+'\n');
 console.log(JSON.stringify(evidence,null,2));
} finally {if(socket)socket.close();proc.kill();proc.stdout.destroy();proc.stderr.destroy();proc.unref();setTimeout(()=>rmSync(profile,{recursive:true,force:true}),500).unref();}
