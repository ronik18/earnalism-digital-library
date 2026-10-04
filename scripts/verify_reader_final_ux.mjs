#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';
const base = process.env.READER_UX_BASE_URL;
assert.match(base || '', /^http:\/\/127\.0\.0\.1:\d+$/,'Use an isolated loopback build only');
const output = process.env.READER_UX_OUTPUT || '/tmp/reader-final-ux';
fs.mkdirSync(output,{recursive:true});
const slug='reader-ux-fixture';
const chapters=[{id:'c1',title:'The first chapter'},{id:'c2',title:'The second chapter'}];
const pages=[1,2,3].map(n=>{const content=Array.from({length:n===3?32:12},(_,i)=>`<p>Page ${n}, paragraph ${i+1}. This repository-owned verification text checks readable page navigation, viewport layout, and accessible internal scrolling without distributing a manuscript.</p>`).join('');return {book_slug:slug,page_index:n,chapter_id:n===1?'c1':'c2',chapter_title:n===1?chapters[0].title:chapters[1].title,total_pages:3,segmentation_version:'ux-fixture-v1',manifest_version:'ux-fixture-v1',is_preview:true,content,content_sha256:createHash('sha256').update(content).digest('hex')};});
const manifest={book:{slug,title:'Reader verification edition',author:'Earnalism test fixture',language:'English',chapters},chapters,access:{reading_pass:{enabled:true,total_pages:3}},canonical_pages:{page_count:3,manifest_version:'ux-fixture-v1',pages:pages.map(p=>({page_number:p.page_index,chapter_id:p.chapter_id,content_hash:p.content_sha256}))}};
const sizes=[[1440,900],[1280,720],[1024,768],[768,1024],[390,844],[844,390],[1280,600]];
const results=[];
const browser=await chromium.launch({headless:true});
try {
for(const [width,height] of sizes){
 const context=await browser.newContext({viewport:{width,height},serviceWorkers:'block'});
 const page=await context.newPage();const errors=[];const writes=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await context.route('**/*',async route=>{const request=route.request();const url=new URL(request.url());
 if(!['GET','HEAD','OPTIONS'].includes(request.method())){writes.push(url.pathname);return route.abort();}
 if(url.pathname.includes('/api/')){let value={};const apiPath=url.pathname.slice(url.pathname.indexOf('/api/')+4);
 if(apiPath===`/reader/book/${slug}/manifest`)value=manifest;
 if(apiPath.startsWith(`/reading-pass/books/${slug}/pages/`))value=pages[Number(apiPath.split('/').at(-1))-1];
 if(apiPath==='/books')value=[];
 return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)});}
 if(!['127.0.0.1','localhost'].includes(url.hostname))return route.fulfill({status:200,contentType:'image/png',body:fs.readFileSync('frontend/public/assets/brand/earnalism-brand-lockup.png')});
 return route.continue();});
 await page.goto(`${base}/reader/${slug}?p=1`,{waitUntil:'domcontentloaded'});
 const prev=page.locator('.reader-v2__page-arrow--previous');const next=page.locator('.reader-v2__page-arrow--next');
 const select=page.locator('.reader-v2__page-frame select').first();
 const waitPage=async n=>{await page.waitForFunction(n=>document.querySelector('.reader-v2__page-frame select')?.value===String(n),n);};
 const reset=async()=>{await select.selectOption('1');await waitPage(1);};
 await waitPage(1);await page.evaluate(()=>document.fonts.ready);
 assert.equal(await prev.isDisabled(),true);assert.equal(await next.isEnabled(),true);
 await page.screenshot({path:path.join(output,`reader-${width}x${height}-first.png`),animations:"disabled"});
 await next.click();await waitPage(2);assert.equal(await page.locator('.reader-v2__page-content').evaluate(n=>getComputedStyle(n).animationName),'readerPageForward');assert.equal(await page.locator('.reader-v2__chapter h1').innerText(),chapters[1].title);
 await next.click();await waitPage(3);assert.equal(await next.isDisabled(),true);
 await page.screenshot({path:path.join(output,`reader-${width}x${height}-last.png`),animations:"disabled"});
 const geometry=await page.evaluate(()=>{const canvas=document.querySelector('.reader-v2__canvas');const rect=canvas.getBoundingClientRect();const doc=document.documentElement;return {scrollWidth:doc.scrollWidth,clientWidth:doc.clientWidth,outerHeight:doc.scrollHeight,viewportHeight:innerHeight,canvasBottom:rect.bottom,canvasTop:rect.top,scrollHeight:canvas.scrollHeight,clientHeight:canvas.clientHeight};});
 assert.ok(geometry.scrollWidth<=geometry.clientWidth,'No horizontal overflow');assert.ok(geometry.outerHeight<=height+2,'Viewport-sized outer Reader');assert.ok(geometry.canvasBottom<=height+1,'Reader canvas visible');
 await page.locator('.reader-v2__canvas').evaluate(n=>n.scrollTop=n.scrollHeight);assert.ok(await page.locator('.reader-v2__canvas').evaluate(n=>n.scrollTop>0),'Long content can be scrolled');
 await prev.click();await waitPage(2);assert.equal(await page.locator('.reader-v2__page-content').evaluate(n=>getComputedStyle(n).animationName),'readerPageReverse');await page.goBack();await waitPage(3);await page.goForward();await waitPage(2);await page.reload();await waitPage(2);
 await page.evaluate(()=>document.activeElement?.blur());await page.keyboard.press('ArrowLeft');await waitPage(1);await page.keyboard.press('ArrowRight');await waitPage(2);
 for(const tag of ['input','textarea','select','button','div','audio','video']){
  await page.evaluate(tag=>{const n=document.createElement(tag);n.id='ux-keyboard-exclusion';if(tag==='div')n.contentEditable='true';n.tabIndex=0;document.body.appendChild(n);n.focus();},tag);
  await page.keyboard.press('ArrowRight');assert.equal(await select.inputValue(),'2',`${tag} consumes arrow keys`);await page.evaluate(()=>document.getElementById('ux-keyboard-exclusion').remove());
 }
 for(const role of ['slider','combobox','listbox','menu','tablist']){await page.evaluate(role=>{const n=document.createElement('div');n.id='ux-keyboard-exclusion';n.setAttribute('role',role);n.tabIndex=0;document.body.appendChild(n);n.focus();},role);await page.keyboard.press('ArrowRight');assert.equal(await select.inputValue(),'2',`${role} consumes arrow keys`);await page.evaluate(()=>document.getElementById('ux-keyboard-exclusion').remove());}
 await reset();for(let i=0;i<8;i++){await next.click({force:true});}await waitPage(3);for(let i=0;i<8;i++){await prev.click({force:true});}await waitPage(1);
 for(let i=0;i<4;i++){await next.click();await waitPage(2);await prev.click();await waitPage(1);}
 await page.evaluate(()=>document.activeElement?.blur());await page.keyboard.press('Tab');assert.ok(await page.evaluate(()=>document.activeElement!==document.body),'Keyboard focus remains reachable');
 await page.emulateMedia({reducedMotion:'reduce'});await next.click();await waitPage(2);assert.equal(await page.locator('.reader-v2__page-content').evaluate(n=>getComputedStyle(n).animationName),'none');
 assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
 results.push({width,height,result:'PASS',geometry,checks:['boundaries','chapter transition','scrolling','keyboard exclusions','rapid/alternating navigation','history','refresh','focus reachability','reduced motion'],errors,writes});
 await context.close();
}
fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify({result:'PASS',fixture:'repository-owned three-page, two-chapter preview',results},null,2));console.log(JSON.stringify({result:'PASS',viewports:results.length,output}));
}finally{await browser.close();}
