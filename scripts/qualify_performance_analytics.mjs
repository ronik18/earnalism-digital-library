import fs from 'node:fs';import path from 'node:path';import http from 'node:http';
import {createRequire} from 'node:module';
const require=createRequire(path.resolve('frontend/package.json'));const {chromium}=require('playwright');
const build=path.resolve(process.env.PERF_BUILD_ROOT||'frontend/build');
const apiOrigin=process.env.PERF_UAT_API_ORIGIN;
if(!apiOrigin||new URL(apiOrigin).hostname!=='127.0.0.1')throw Error('Explicit disposable loopback API required');
const server=http.createServer((req,res)=>{const p=new URL(req.url,'http://localhost').pathname;const candidate=path.resolve(build,'.'+p);if(candidate!==build&&!candidate.startsWith(build+'/')){res.writeHead(403).end();return;}const file=fs.existsSync(candidate)&&fs.statSync(candidate).isFile()?candidate:build+'/index.html';const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.woff2':'font/woff2','.png':'image/png','.avif':'image/avif','.webp':'image/webp'};res.setHeader('content-type',types[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({headless:true});const events=[],mutations=[],errors=[];
try{
 const context=await browser.newContext();const page=await context.newPage();
 await page.addInitScript(()=>{window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__=true;Object.defineProperty(navigator,'sendBeacon',{value:()=>false});});
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{const req=route.request(),url=new URL(req.url());
  if(url.pathname.startsWith('/api/')){
   if(req.method()!=='GET'&&!url.pathname.startsWith('/api/analytics/')){mutations.push({path:url.pathname,method:req.method()});return route.fulfill({status:403,json:{detail:'Guarded qualification'}});}
   const response=await route.fetch({url:apiOrigin+url.pathname+url.search});
   if(url.pathname.startsWith('/api/analytics/'))events.push({event:req.postDataJSON().event,status:response.status(),route:req.postDataJSON().route});
   return route.fulfill({response});
  }
  if(url.origin===base)return route.continue();return route.fulfill({status:200,json:[]});
 });
 await page.goto(base+'/');await page.waitForTimeout(2000);const before=events.length;
 const link=page.locator('a[href="/library"]').first();await link.hover();await link.focus();await page.waitForTimeout(800);
 if(events.length!==before)throw Error('Prefetch analytics side effect');
 await link.click();await page.waitForTimeout(1500);
 await page.evaluate(()=>{history.pushState({},'','/book/a-ghost-story');dispatchEvent(new PopStateEvent('popstate'));});await page.waitForTimeout(1500);
 if(mutations.length)throw Error('Unexpected mutation');
 for(const event of ['homepage_view','library_view','title_view'])if(events.filter(x=>x.event===event).length!==1)throw Error('Missing/duplicate '+event);
 if(events.some(x=>x.status!==200))throw Error('Analytics rejected');
 console.log(JSON.stringify({events,prefetchFalseEvents:0,mutations:0,errors,logoAlt:await page.locator('[data-testid="earnalism-brand-lockup"] img').first().getAttribute('alt')}));
 await context.close();
}finally{await browser.close();await new Promise(r=>server.close(r));}
