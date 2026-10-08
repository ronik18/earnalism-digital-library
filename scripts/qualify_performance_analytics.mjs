import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(path.resolve('frontend/package.json'));const {chromium}=require('playwright');
const apiOrigin=process.env.PERF_UAT_API_ORIGIN;
if(!apiOrigin||new URL(apiOrigin).hostname!=='127.0.0.1')throw Error('Explicit disposable loopback API required');
const frontendOrigin=process.env.PERF_UAT_FRONTEND_ORIGIN;
if(!frontendOrigin||new URL(frontendOrigin).hostname!=='127.0.0.1')throw Error('Explicit disposable loopback frontend required');
const base=frontendOrigin.replace(/\/$/,"");
const browser=await chromium.launch({headless:true});const events=[],mutations=[],errors=[];
try{
 const context=await browser.newContext();const page=await context.newPage();const apiRequests=[],apiResponses=[],failedApiRequests=[],forwardingErrors=[];
 await page.addInitScript(()=>{window.__EARNALISM_ENABLE_FUNNEL_ANALYTICS__=true;Object.defineProperty(navigator,'sendBeacon',{value:()=>false});});
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',request=>{const url=new URL(request.url());if(url.pathname.startsWith('/api/'))apiRequests.push({path:url.pathname,method:request.method()});});
 page.on('response',response=>{const url=new URL(response.url());if(url.pathname.startsWith('/api/')){apiResponses.push({path:url.pathname,status:response.status()});if(url.pathname.startsWith('/api/analytics/')){try{const payload=response.request().postDataJSON();events.push({event:payload.event,status:response.status(),route:payload.route});}catch{}}}});
 page.on('requestfailed',request=>{const url=new URL(request.url());if(url.pathname.startsWith('/api/'))failedApiRequests.push({path:url.pathname,error:String(request.failure()?.errorText||'unknown')});});
 await page.route('**/*',async route=>{const req=route.request(),url=new URL(req.url());
  if(url.pathname.startsWith('/api/')){
   if(req.method()!=='GET'&&!url.pathname.startsWith('/api/analytics/')){mutations.push({path:url.pathname,method:req.method()});return route.fulfill({status:403,json:{detail:'Guarded qualification'}});}
   // The UAT frontend is built with its approved loopback API origin and the
   // disposable backend permits that exact origin. Continue normal browser
   // traffic so this qualification exercises the same CORS path as UAT rather
   // than introducing a synthetic Playwright proxy.
   return route.continue();
  }
  if(url.origin===base)return route.continue();return route.fulfill({status:200,json:[]});
 });
 await page.goto(base+'/');await page.waitForTimeout(2000);const before=events.length;
 const link=page.locator('a[href="/library"]').first();await link.hover();await link.focus();await page.waitForTimeout(800);
 if(events.length!==before)throw Error('Prefetch analytics side effect');
 await link.click();await page.waitForTimeout(1500);
 // Use an actual browser navigation for the detail route. Calling history APIs
 // directly does not invoke React Router's navigator, so it cannot qualify the
 // BookDetail data load or its title-view analytics effect.
 await page.goto(base+'/book/a-ghost-story');
 try{await page.getByRole('heading',{name:'A Ghost Story',exact:true}).waitFor();}
 catch(error){throw Error(`${error.message}; diagnostics=${JSON.stringify({apiRequests,apiResponses,failedApiRequests,forwardingErrors,errors,body:(await page.locator('body').innerText()).slice(0,1200)})}`);}
 await page.waitForTimeout(500);
 if(mutations.length)throw Error('Unexpected mutation');
 for(const event of ['homepage_view','library_view','title_view'])if(events.filter(x=>x.event===event).length!==1)throw Error('Missing/duplicate '+event);
 if(events.some(x=>x.status!==200))throw Error('Analytics rejected');
 console.log(JSON.stringify({events,prefetchFalseEvents:0,mutations:0,errors,logoAlt:await page.locator('[data-testid="earnalism-brand-lockup"] img').first().getAttribute('alt')}));
 await context.close();
}finally{await browser.close();}
