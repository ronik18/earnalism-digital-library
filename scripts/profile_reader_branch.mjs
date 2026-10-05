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
const adaptedPath = path.join(output, 'mock.js');fs.writeFileSync(adaptedPath, adaptedFixture);
const entry = path.join(output, 'entry.jsx');
fs.writeFileSync(entry, `import React from 'react';import {createRoot} from 'react-dom/client';import {BrowserRouter,Routes,Route} from 'react-router-dom';import Reader from ${JSON.stringify(path.join(target,'frontend/src/experiences-v2/reader/ReaderExperienceV2Route.jsx'))};createRoot(document.getElementById('root')).render(<BrowserRouter><Routes><Route path="/reader/:slug" element={<Reader/>}/><Route path="/bench-empty" element={<main>Disposed Reader fixture</main>}/></Routes></BrowserRouter>);`);
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
const browser=await chromium.launch({headless:true}); const rows=[];
try {
 for (const [width,height] of [[1440,900],[390,844],[844,390]]) {
  const context=await browser.newContext({viewport:{width,height}});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>new URL(r.request().url()).origin===base?r.continue():r.fulfill({status:200,json:[]}));
  await page.addInitScript(() => {
   window.__readerTurnPaints = [];
   let pending;
   document.addEventListener('click', event => {
    if (!window.__readerMeasureTurn) return;
    window.__readerMeasureTurn = false;
    pending = {input_at: event.timeStamp, index: document.querySelector('.reader-v2__visual-viewport')?.dataset.visualPageIndex, text: document.querySelector('[data-testid="reader-reading-text"]')?.textContent};
   }, true);
   new MutationObserver(() => {
    if (!pending) return;
    const text = document.querySelector('[data-testid="reader-reading-text"]');
    const index = document.querySelector('.reader-v2__visual-viewport')?.dataset.visualPageIndex;
    if (!text || (text.textContent === pending.text && index === pending.index)) return;
    const input = pending; pending = null;
    const committed = performance.now();
    requestAnimationFrame(() => requestAnimationFrame(() => window.__readerTurnPaints.push({
     input_to_content_commit_ms: committed - input.input_at,
     input_to_second_frame_ms: performance.now() - input.input_at,
     active_animation_durations_ms: text.getAnimations({subtree:true}).map(a => a.effect?.getComputedTiming().duration).filter(Number.isFinite),
    })));
   }).observe(document, {subtree:true,childList:true,characterData:true,attributes:true});
  });
  const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');
  const started=performance.now();await page.goto(base+'/reader/agentic-ai-with-python?p=3&full=1');
  const consent=page.getByRole('button',{name:'Continue to this page',exact:true});
  const readable=await consent.or(page.getByTestId('reader-reading-text')).first().waitFor({timeout:10000}).then(()=>true).catch(()=>false);
  if(!readable){rows.push({width,height,fixture_compatible:false,errors,diagnostic:(await page.locator('body').innerText()).slice(0,1000)});await context.close();continue;}
  if(await consent.count())await consent.click();
  await page.waitForSelector('[data-testid="reader-reading-text"]',{timeout:30000});
  const firstReadable=performance.now()-started;
  const pagination=await page.locator('[data-pagination-ready]').count();
  if(pagination)await page.waitForSelector('[data-pagination-ready="true"]',{timeout:30000});
  const sample=async()=>page.evaluate(()=>{const n=document.querySelector('.reader-v2__visual-viewport');const text=document.querySelector('[data-testid="reader-reading-text"]');return {dataset:n?{...n.dataset}:null,mounted_text_pages:document.querySelectorAll('[data-testid="reader-reading-text"]').length,client_height:n?.clientHeight,scroll_height:n?.scrollHeight,text_characters:text?.textContent.length,overflow:document.documentElement.scrollWidth>innerWidth};});
  const initial=await sample();const count=Number(initial.dataset?.pageCount||8);const turns=[];const heap=[];
  for(let cycle=0;cycle<5;cycle++) {
   for(let i=0;i<40;i++) {
    const current=await sample();const at=Number(current.dataset?.visualPageIndex||0);const backwards=at>=count-1;
    const button=page.getByRole('button',{name:backwards?'Previous page':'Next page',exact:true}).first();
    if(!await button.count()||await button.isDisabled())break;
    const measured = await page.evaluate(() => {window.__readerMeasureTurn=true;return window.__readerTurnPaints.length;});
    const start=performance.now();await button.click();
    await page.waitForFunction(n => window.__readerTurnPaints.length > n, measured, {timeout:3000});
    turns.push(performance.now()-start);
   }
   // Real SPA disposal/re-entry (not a document reload or a forced heap reset).
   await page.evaluate(() => {history.pushState({}, '', '/bench-empty');dispatchEvent(new PopStateEvent('popstate'));});
   await page.getByText('Disposed Reader fixture').waitFor();
   // Let passive effects and cancelled animation callbacks actually dispose.
   await page.waitForTimeout(150);
   await cdp.send('HeapProfiler.collectGarbage');const metrics=(await cdp.send('Performance.getMetrics')).metrics;
   heap.push({cycle:cycle+1,phase:'after_reader_disposal',heap_bytes:metrics.find(m=>m.name==='JSHeapUsedSize')?.value,...await cdp.send('Memory.getDOMCounters')});
   await page.evaluate(() => {history.pushState({}, '', '/reader/agentic-ai-with-python?p=3&full=1');dispatchEvent(new PopStateEvent('popstate'));});
   await consent.or(page.getByTestId('reader-reading-text')).first().waitFor();
   if(await consent.count())await consent.click();
   await page.waitForSelector('[data-testid="reader-reading-text"]');
   if(pagination)await page.waitForSelector('[data-pagination-ready="true"]');
  }
  const resize=performance.now();await page.setViewportSize({width:width===390?1440:390,height:width===390?900:844});
  let resizeReady=true;
  await page.waitForTimeout(250);if(pagination)await page.waitForSelector('[data-pagination-ready="true"]',{timeout:10000}).catch(()=>{resizeReady=false;});
  const resized=await sample();
  const ordered=turns.toSorted((a,b)=>a-b);
  const paints=await page.evaluate(()=>window.__readerTurnPaints);
  const paintTimes=paints.map(x=>x.input_to_second_frame_ms).toSorted((a,b)=>a-b);
  rows.push({width,height,first_readable_ms:firstReadable,initial,resized,resize_ready:resizeReady,resize_diagnostic:resizeReady?null:(await page.locator('body').innerText()).slice(0,1000),resize_settle_ms:performance.now()-resize,turns:turns.length,input_to_second_frame_ms:{samples:paintTimes.length,p50:paintTimes[Math.floor(paintTimes.length*.5)]??null,p95:paintTimes[Math.ceil(paintTimes.length*.95)-1]??null,p99:paintTimes[Math.ceil(paintTimes.length*.99)-1]??null,max:paintTimes.at(-1)??null},paint_samples:paints,page_turn_driver_plus_two_frames_ms:{p50:ordered[Math.floor(ordered.length*.5)]??null,p95:ordered[Math.ceil(ordered.length*.95)-1]??null,max:ordered.at(-1)??null},heap,errors});
  await context.close();
 }
 console.log(JSON.stringify({mode,source_revision:execFileSync('git',['-C',target,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),fixture_sha256:createHash('sha256').update(fs.readFileSync(fixture)).digest('hex'),scope:'CURRENT_READER_SOURCE_WITH_EXPLICIT_OWNED_MOCK_API_NO_PRODUCTION_REQUESTS',rows,limitations:['Mock auth/lease is not genuine server authorization; real Mongo API benchmark is separate.','Standalone build timings are diagnostic, not production deployment latency.','Input-to-second-frame is browser-event/DOM timing, not field INP or GPU presentation time.','Five 40-turn cycles include SPA disposal/reentry; chapter, notes, font changes and live timers still require a broader soak.']},null,2));
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
