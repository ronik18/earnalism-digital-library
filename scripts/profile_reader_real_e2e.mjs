// Native Reader/AuthProvider/API code; no replacement modules or response mocks.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const target=process.env.PERF_READER_WORKTREE;
const base=process.env.UAT_BASE_URL;
const api=process.env.UAT_API_BASE_URL;
if(!target || !base || !api || !base.startsWith('http://127.0.0.1:') || !api.startsWith('http://127.0.0.1:') || process.env.ENVIRONMENT!=='uat')throw Error('Explicit disposable UAT and read-only Reader worktree required');
const require=createRequire(path.join(target,'frontend/package.json'));
const webpack=require('webpack'),{chromium}=require('playwright');
const modules=path.join(target,'frontend/node_modules');
const output=path.resolve('frontend/build');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'reader-real-entry-'));
const entry=path.join(temp,'entry.jsx');
fs.writeFileSync(entry,`import React from 'react';import {createRoot} from 'react-dom/client';import {BrowserRouter,Routes,Route} from 'react-router-dom';import Reader from ${JSON.stringify(path.join(target,'frontend/src/experiences-v2/reader/ReaderExperienceV2Route.jsx'))};import {AuthProvider,useAuth} from ${JSON.stringify(path.join(target,'frontend/src/context/AuthContext.jsx'))};function Control(){const auth=useAuth();return <main><button onClick={()=>auth.userSignup('Disposable E2E Reader','reader-e2e-'+Date.now()+'@example.com','local-fixture-password')}>Create disposable reader</button><output data-testid="identity">{auth.user?.id||'anonymous'}</output></main>}createRoot(document.getElementById('root')).render(<BrowserRouter><AuthProvider><Routes><Route path="/reader/:slug" element={<Reader/>}/><Route path="*" element={<Control/>}/></Routes></AuthProvider></BrowserRouter>);`);
await new Promise((resolve,reject)=>webpack({mode:'production',devtool:false,entry,output:{path:output,filename:'perf-reader-entry.js'},resolve:{modules:[modules],extensions:['.js','.jsx']},module:{rules:[{test:/\.[jt]sx?$/,exclude:/node_modules/,use:{loader:path.join(modules,'babel-loader'),options:{presets:[[path.join(modules,'@babel/preset-react'),{runtime:'automatic'}]]}}},{test:/\.css$/,use:[path.join(modules,'style-loader'),path.join(modules,'css-loader')]}]},plugins:[new webpack.DefinePlugin({'process.env':JSON.stringify({NODE_ENV:'production',REACT_APP_UAT_LOCAL:'true',REACT_APP_BACKEND_URL:api.replace(/\/api$/,'')})})]},(e,s)=>e||s.hasErrors()?reject(e||Error(s.toString({all:false,errors:true}))):resolve()));
const manifest=JSON.parse(fs.readFileSync(path.join(output,'asset-manifest.json')));
fs.writeFileSync(path.join(output,'perf-reader.html'),`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="${manifest.files['main.css']}"></head><body><div id="root"></div><script src="/perf-reader-entry.js"></script></body></html>`);
const evidence={scope:'DISPOSABLE_NATIVE_AUTH_READER_API_NO_MOCKS',reader_sha:execFileSync('git',['-C',target,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),backend_sha:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),rows:[],errors:[],production_changed:false};
const browser=await chromium.launch({headless:true});evidence.chromium=browser.version();
try {
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 const page=await context.newPage();
 page.on('pageerror',e=>evidence.errors.push(e.message));
 const requests=[],byRequest=new Map();evidence.requests=requests;
 page.on('request',r=>{if(new URL(r.url()).pathname.startsWith('/api/')){const item={path:new URL(r.url()).pathname,at:performance.now(),method:r.method()};requests.push(item);byRequest.set(r,item);}});
 page.on('response',r=>{const item=byRequest.get(r.request());if(item){item.status=r.status();item.cache_control=r.headers()['cache-control'];}});
 page.on('requestfailed',r=>{const item=byRequest.get(r);if(item)item.failure=r.failure()?.errorText;});
 await page.route('**/*',route=>{const url=new URL(route.request().url());return [new URL(base).origin,new URL(api).origin].includes(url.origin)?route.continue():route.abort();});
 await page.goto(base+'/perf-reader.html');
 await page.getByRole('button',{name:'Create disposable reader'}).waitFor();
 await page.getByRole('button',{name:'Create disposable reader'}).click();
 await page.waitForFunction(()=>document.querySelector('[data-testid="identity"]')?.textContent!=='anonymous');
 const user=await page.getByTestId('identity').innerText();
 // Native UAT entitlement seed, scoped to the just-created disposable identity.
 execFileSync(path.resolve('.venv-uat/bin/python'),['-c',`import os,sys;from pymongo import MongoClient;from urllib.parse import urlparse;u=os.environ['MONGODB_URL'];p=urlparse(u);assert p.hostname=='127.0.0.1' and p.port==int(os.environ['UAT_MONGODB_PORT']) and p.path=='/earnalism_uat';c=MongoClient(u);r=c.earnalism_uat.users.update_one({'id':sys.argv[1]},{'$set':{'reading_seconds_balance':3600,'wallet_seconds':3600}});assert r.matched_count==1;c.close()`,user],{stdio:'pipe'});
 const slug=process.env.PERF_READER_SLUG||'dracula';
 const token=await page.evaluate(()=>localStorage.getItem('earnalism_user_token'));
 const realManifest=await context.request.get(api+'/reader/book/'+slug+'/manifest',{headers:{Authorization:'Bearer '+token}});
 evidence.manifest_status=realManifest.status();
 if(realManifest.status()!==200)throw Error('Native manifest rejected: HTTP '+realManifest.status()+' '+(await realManifest.text()).slice(0,300));
 const data=await realManifest.json();
 evidence.fixture={slug,chapter_ids:(data.chapters||[]).map(c=>c.id),canonical_pages:data.canonical_pages?.page_count};
 const denied=await browser.newContext();
 const unauthorized=await denied.request.get(api+'/reading-pass/books/'+slug+'/pages/4');
 evidence.unauthorized_status=unauthorized.status();evidence.unauthorized_protected_content_revealed=unauthorized.status()===200;
 await denied.close();
 if(unauthorized.status()===200)throw Error('Unauthorized protected content disclosed');
 const nav=async()=>page.evaluate(s=>{history.pushState({},'',s);dispatchEvent(new PopStateEvent('popstate'));},'/reader/'+slug+'?p=4');
 for(const [width,height] of [[1440,900],[390,844],[844,390]]){
  await page.setViewportSize({width,height});const started=performance.now();await nav();
  const consent=page.getByRole('button',{name:'Continue to this page',exact:true});
  await consent.or(page.getByTestId('reader-reading-text')).first().waitFor({timeout:30000});
  if(await consent.count())await consent.click();
  await page.locator('[data-pagination-ready="true"]').waitFor({timeout:60000});
  const elapsed=performance.now()-started;
  evidence.rows.push({width,height,reader_ready_ms:elapsed,...await page.evaluate(()=>{const n=document.querySelector('.reader-v2__visual-viewport');return{dataset:{...n.dataset},clientHeight:n.clientHeight,scrollHeight:n.scrollHeight,mountedPages:document.querySelectorAll('[data-testid="reader-reading-text"]').length};})});
  await page.screenshot({path:'/tmp/reader-real-'+width+'-'+height+'.png'});
  const turns=[];
  evidence.rows.at(-1).completed_visual_turns=0;
  for(let i=0;i<100;i++){
   await page.locator('[data-pagination-ready="true"]').waitFor({timeout:30000});
   const before=await page.locator('.reader-v2__visual-viewport').getAttribute('data-visual-page-index');
   const total=Number(await page.locator('.reader-v2__visual-viewport').getAttribute('data-page-count'));
   const next=page.getByRole('button',{name:'Next page',exact:true}).first();
   const previous=page.getByRole('button',{name:'Previous page',exact:true}).first();
   const start=performance.now();await(Number(before)>=total-1||await next.isDisabled()?previous:next).click();
   await page.waitForFunction(value=>{const n=document.querySelector('.reader-v2__visual-viewport');return n&&n.dataset.paginationReady==='true'&&n.dataset.visualPageIndex!==value},before);
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   turns.push(performance.now()-start);
   evidence.rows.at(-1).completed_visual_turns=turns.length;
  }
  turns.sort((a,b)=>a-b);evidence.rows.at(-1).driver_input_to_two_frames_ms={samples:turns.length,p50:turns[49],p95:turns[94],p99:turns[98],max:turns[99]};
  await page.evaluate(()=>{history.pushState({},'','/perf-reader.html');dispatchEvent(new PopStateEvent('popstate'));});
  await page.getByTestId('identity').waitFor();
 }
 // Chapter coordinates come solely from the genuine manifest, not a prose fixture.
 const pages=data.canonical_pages?.pages||[];
 const second=pages.find(p=>p.chapter_id==='chapter-002');
 evidence.multi_chapter=[];
 if(second){
  for(const destination of [4,Number(second.page_number||second.page_index),4]){
   await page.evaluate(p=>{history.pushState({},'','/reader/dracula?p='+p);dispatchEvent(new PopStateEvent('popstate'));},destination);
   const consent=page.getByRole('button',{name:'Continue to this page',exact:true});
   await consent.or(page.getByTestId('reader-reading-text')).first().waitFor({timeout:30000});
   if(await consent.count())await consent.click();
   const chapter=destination===4?'chapter-001':'chapter-002';
   await page.waitForFunction(id=>{const n=document.querySelector('.reader-v2__visual-viewport');return n?.dataset.chapterId===id&&n.dataset.paginationReady==='true'},chapter,{timeout:60000});
   evidence.multi_chapter.push(await page.evaluate(()=>({...document.querySelector('.reader-v2__visual-viewport').dataset})));
  }
 }
 evidence.requests=requests;byRequest.clear();
 await context.close();
}catch(error){evidence.failure=error.message;process.exitCode=1;}
finally{await browser.close();fs.writeFileSync('/tmp/earnalism-reader-real-e2e.json',JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence,null,2));}
