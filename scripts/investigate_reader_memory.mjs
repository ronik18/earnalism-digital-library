// Compile the actual selected Reader sources without editing that branch.
// Existing owned API fixture is required explicitly; this is NOT backend auth proof.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const target = path.resolve(process.env.PERF_READER_WORKTREE || '.');
const fixture = path.resolve(process.env.PERF_READER_FIXTURE || '');
if (!process.env.PERF_READER_FIXTURE || !fs.existsSync(fixture)) throw Error('Explicit owned Reader API fixture required');
const require = createRequire(path.join(target, 'frontend/package.json'));
const webpack = require('webpack'); const {chromium} = require('playwright');
const output = fs.mkdtempSync(path.join(os.tmpdir(), 'earnalism-reader-performance-'));
// The retained owned fixture predates the current 3-page preview contract.
// Adapt ONLY its mock boundary consistently; never change runtime enforcement.
const fixtureSource = fs.readFileSync(fixture, 'utf8');
const adaptedFixture = fixtureSource.replaceAll('public_limit:2', 'public_limit:3')
  .replaceAll('n>2&&!full', 'n>3&&!full').replaceAll('is_preview:n<=2', 'is_preview:n<=3');
const adaptedPath = path.join(output, 'mock.js');fs.writeFileSync(adaptedPath, adaptedFixture.replace("export const userApi={get:async()=>({data:manifest()})", "export const userApi={get:async()=>{if(window.__auditShellOnly)throw Error('Controlled metadata-only arm');return({data:manifest()})}") );
const entry = path.join(output, 'entry.jsx');
fs.writeFileSync(entry, `import React from 'react';import {createRoot} from 'react-dom/client';import {BrowserRouter,Routes,Route} from 'react-router-dom';import Reader from ${JSON.stringify(path.join(target,'frontend/src/experiences-v2/reader/ReaderExperienceV2Route.jsx'))};createRoot(document.getElementById('root')).render(<BrowserRouter><Routes><Route path="/reader/:slug" element={<Reader/>}/><Route path="/bench-empty" element={<main>Disposed Reader fixture</main>}/><Route path="/" element={<main>Control Home</main>}/><Route path="/library" element={<main>Control Library</main>}/><Route path="/book/:slug" element={<main>Control detail</main>}/></Routes></BrowserRouter>);`);
const modules = path.join(target, 'frontend/node_modules');
const mode = process.env.PERF_READER_MODE === 'development' ? 'development' : 'production';
await new Promise((resolve,reject) => webpack({mode,devtool:false,entry,output:{path:output,filename:'fixture.js'},resolve:{modules:[modules],extensions:['.js','.jsx']},module:{rules:[{test:/\.[jt]sx?$/,exclude:/node_modules/,use:{loader:path.join(modules,'babel-loader'),options:{presets:[[path.join(modules,'@babel/preset-react'),{runtime:'automatic'}]]}}},{test:/\.css$/,use:[path.join(modules,'style-loader'),path.join(modules,'css-loader')]}]},plugins:[new webpack.DefinePlugin({'process.env':JSON.stringify({NODE_ENV:mode})}),new webpack.NormalModuleReplacementPlugin(/(lib\/api|lib\/readingPassApi|context\/AuthContext|lib\/funnelAnalytics)$/,r=>{r.request=adaptedPath;})]},(e,s)=>e||s.hasErrors()?reject(e||Error(s.toString({all:false,errors:true}))):resolve()));
const build = path.join(target,'frontend/build');
const manifest = JSON.parse(fs.readFileSync(path.join(build,'asset-manifest.json')));
fs.writeFileSync(path.join(output,'index.html'),`<html><head><link rel="stylesheet" href="${manifest.files['main.css']}"></head><body><div id="root"></div><script src="/fixture.js"></script></body></html>`);
const server = http.createServer((req,res)=>{
 const pathname=new URL(req.url,'http://localhost').pathname;
 const root=pathname.startsWith('/static/')||pathname.startsWith('/assets/')?build:output;
 const candidate=path.resolve(root,'.'+pathname);
 if (!candidate.startsWith(root+path.sep)) {res.writeHead(403).end();return;}
 const file=fs.existsSync(candidate)&&fs.statSync(candidate).isFile()?candidate:path.join(output,'index.html');
 const type={'.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.ttf':'font/ttf','.png':'image/png','.webp':'image/webp','.svg':'image/svg+xml','.html':'text/html'};
 res.setHeader('content-type',type[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
const evidence=process.env.MEMORY_EVIDENCE_DIR||'/tmp/earnalism-reader-memory-evidence';fs.mkdirSync(evidence,{recursive:true});
const browser=await chromium.launch({headless:true});const rows=[];
const instrumentation=()=>{
 const audit={events:[],timers:new Map(),rafs:new Set(),observers:[],pendingFetch:0};window.__memoryAudit=audit;
 for(const name of ['ResizeObserver','MutationObserver','IntersectionObserver']){const Native=window[name];if(!Native)continue;window[name]=class extends Native{constructor(cb){super(cb);this.auditActive=true;audit.observers.push({kind:name,ref:new WeakRef(this)});}disconnect(){this.auditActive=false;return super.disconnect();}};}
 const add=EventTarget.prototype.addEventListener,remove=EventTarget.prototype.removeEventListener;
 for(const [op,original] of [['add',add],['remove',remove]])EventTarget.prototype[op==='add'?'addEventListener':'removeEventListener']=function(type,fn,options){if(this===window||this===document||this===visualViewport)audit.events.push({op,type,target:this===window?'window':this===document?'document':'visualViewport'});return original.call(this,type,fn,options)};
 for(const [set,clear,kind] of [['setTimeout','clearTimeout','timeout'],['setInterval','clearInterval','interval']]){const nativeSet=window[set],nativeClear=window[clear];window[set]=(cb,ms,...args)=>{let id=nativeSet(()=>{if(kind==='timeout')audit.timers.delete(id);cb(...args)},ms);audit.timers.set(id,kind);return id};window[clear]=id=>{audit.timers.delete(id);return nativeClear(id)}}
 const request=window.requestAnimationFrame,cancel=window.cancelAnimationFrame;window.requestAnimationFrame=cb=>{let id=request(ts=>{audit.rafs.delete(id);cb(ts)});audit.rafs.add(id);return id};window.cancelAnimationFrame=id=>{audit.rafs.delete(id);return cancel(id)};
};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
try{
 for(const arm of ['idle','router-shell','reader-shell','reader-handles','reader-nohandles','reader-handles-released']){
  const context=await browser.newContext({viewport:{width:1440,height:900}});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.fulfill({status:200,json:[]}));await page.addInitScript(instrumentation);const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');let held=[];
  await page.goto(base+'/reader/agentic-ai-with-python?p=3&full=1');const consent=page.getByRole('button',{name:'Continue to this page',exact:true});await consent.or(page.getByTestId('reader-reading-text')).first().waitFor({timeout:30000});if(await consent.count())await consent.click();await page.locator('[data-pagination-ready="true"]').waitFor({timeout:30000});
  const navigate=async route=>{await page.evaluate(p=>{history.pushState({},'',p);dispatchEvent(new PopStateEvent('popstate'))},route);if(route.startsWith('/reader/')){if(arm==='reader-shell')await page.waitForTimeout(200);else if(arm==='reader-handles'||arm==='reader-handles-released'){held.push(await page.waitForSelector('[data-testid="reader-reading-text"]'));held.push(await page.waitForSelector('[data-pagination-ready="true"]'));}else{await page.locator('[data-testid="reader-reading-text"]').waitFor();await page.locator('[data-pagination-ready="true"]').waitFor();}}else await page.locator('.reader-v2__visual-viewport').waitFor({state:'detached'});};
  await navigate('/bench-empty');await delay(300);
  const snapshot=async cycle=>{let chunks=[];const listener=m=>chunks.push(m.chunk);cdp.on('HeapProfiler.addHeapSnapshotChunk',listener);await cdp.send('HeapProfiler.takeHeapSnapshot',{reportProgress:false});cdp.off('HeapProfiler.addHeapSnapshotChunk',listener);fs.writeFileSync(path.join(evidence,`${arm}-${cycle}.heapsnapshot`),chunks.join(''));chunks=[];};
  const sample=async cycle=>{await cdp.send('HeapProfiler.collectGarbage');await cdp.send('HeapProfiler.collectGarbage');const metrics=(await cdp.send('Performance.getMetrics')).metrics;return{cycle,heap:metrics.find(x=>x.name==='JSHeapUsedSize')?.value,totalHeap:metrics.find(x=>x.name==='JSHeapTotalSize')?.value,...await cdp.send('Memory.getDOMCounters'),...await page.evaluate(()=>{const a=window.__memoryAudit;return{attachedNodes:document.querySelectorAll('*').length,mountedPages:document.querySelectorAll('[data-testid="reader-reading-text"]').length,images:document.images.length,timers:a.timers.size,rafs:a.rafs.size,activeObservers:a.observers.filter(x=>x.ref.deref()?.auditActive).reduce((a,x)=>(a[x.kind]=(a[x.kind]||0)+1,a),{}),eventBalance:a.events.reduce((a,x)=>{const key=x.target+':'+x.type;a[key]=(a[key]||0)+(x.op==='add'?1:-1);return a},{})}})};};
  const samples=[await sample(0)];await snapshot(0);
  for(let cycle=1;cycle<=20;cycle++){
   if(arm==='idle')await delay(500);
   else if(arm==='router-shell'){for(const route of ['/','/library','/book/agentic-ai-with-python','/library','/'])await navigate(route);await navigate('/bench-empty');}
   else{if(arm==='reader-shell')await page.evaluate(()=>window.__auditShellOnly=true);await navigate('/reader/agentic-ai-with-python?p=3&full=1');if(arm!=='reader-shell'){for(let turn=0;turn<5;turn++){const next=page.getByRole('button',{name:'Next page',exact:true}).first();const previous=page.getByRole('button',{name:'Previous page',exact:true}).first();await(await next.isDisabled()?previous:next).click();await delay(30);}}await navigate('/bench-empty');}
   await delay(300);if(arm==='reader-handles-released'){for(const handle of held)await handle.dispose();held=[];}
   samples.push(await sample(cycle));if([5,10,15,20].includes(cycle))await snapshot(cycle);
  }
  if(held.length){for(const handle of held)await handle.dispose();held=[];await delay(300);samples.push({...await sample(21),handlesReleased:true});await snapshot(21);}
  rows.push({arm,samples,errors});fs.writeFileSync(path.join(evidence,'results.json'),JSON.stringify({source_revision:execFileSync('git',['-C',target,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),browser:browser.version(),fixture_sha256:createHash('sha256').update(fs.readFileSync(fixture)).digest('hex'),scope:'Owned synthetic full Reader fixture; router controls use same React/router shell, not full production Home/Library components',rows},null,2));await context.close();console.error(arm+' complete');
 }
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
