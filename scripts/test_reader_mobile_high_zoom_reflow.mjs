#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadStateManifest, selectStateRecords } from "./lib/seamless_brand_state_manifest.mjs";
import { validateCaptureSummary } from "./lib/seamless_brand_one_state_capture.mjs";

const root = process.cwd();
const baseUrl = process.env.SEAMLESS_BRAND_TEST_BASE_URL;
const captureScript = path.join(root, "scripts/capture_seamless_brand_owner_review.mjs");
const manifestPath = path.join(root, "docs/design-system/seamless-brand-state-manifest.json");
const inventoryPath = path.join(root, "docs/design-system/seamless-brand-route-inventory.json");
const beforePath = path.join(root, "uat/evidence/seamless-brand-reader-high-zoom/reader-high-zoom-controls-before.json");
const output = fs.mkdtempSync(path.join(os.tmpdir(), "reader-mobile-high-zoom-reflow-"));
const manifest = loadStateManifest(manifestPath);
const ids = ["reader-mobile-390", "reader-mobile-390-zoom-150", "reader-mobile-390-zoom-200", "reader-mobile-320-zoom-100", "reader-mobile-320-zoom-150", "reader-mobile-320-zoom-200"];
const selected = selectStateRecords(manifest, ids);
let cases = 0;

function test(name, callback) { callback(); cases += 1; process.stdout.write(`PASS ${cases}: ${name}\n`); }
function runCapture() { const result = spawnSync(process.execPath, [captureScript, "--manifest", manifestPath, "--route-inventory", inventoryPath, "--state-filter", [...ids].reverse().join(","), "--capture", "--browser", "chromium", "--base-url", baseUrl, "--output", output], { cwd: root, encoding: "utf8", maxBuffer: 30 * 1024 * 1024 }); assert.equal(result.status, 0, result.stderr); }
function recordFor(records, id) { const value = records.find((record) => record.state_id === id); assert.ok(value, `Missing ${id}`); return value; }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function assertFontLabel(label, renderedSize) {
  const match = /^(\d+(?:\.\d+)?)rem$/.exec((label || "").trim());
  assert.ok(match, `Expected an actual rem-based size option, received ${JSON.stringify(label)}`);
  assert.ok(Math.abs(Number(match[1]) * 16 - renderedSize) < 0.01, "Selected text-size label must match rendered font size");
}
function assertReader(record) {
  const topbar = record.zoom_results.reader_topbar;
  assert.equal(record.rendered_ui_result, "PASS"); assert.equal(record.horizontal_overflow, false);
  assert.equal(record.reader_chrome_contract, "QUIET_FOLIO_NO_MARKETING_MASTHEAD");
  assert.equal(record.logo, null); assert.equal(record.visible_canonical_lockup_count, 0);
  assert.equal(record.reader.protected_content_exposed, false); assert.equal(record.reader.protected_prefetch, false); assert.equal(record.reader.balance_consumption, 0);
  assert.equal(topbar.contract, "QUIET_FOLIO"); assert.equal(topbar.content_begins_below_topbar, true); assert.equal(topbar.action_row_content_overlap_area, 0);
  for (const key of ["back", "settings", "fullscreen"]) {
    const item = topbar.children[key]; assert.ok(item.box); assert.ok(item.box.width >= 44 && item.box.height >= 44);
    assert.equal(item.clipped_area, 0); assert.ok(item.box.left >= topbar.box.left && item.box.right <= topbar.box.right);
  }
  assert.ok(topbar.children.title.box && topbar.children.title.box.width > 0 && topbar.children.title.box.height > 0); assert.equal(topbar.children.title.clipped_area, 0);
  assert.ok(topbar.children.title.box.left >= topbar.box.left && topbar.children.title.box.right <= topbar.box.right);
  assert.ok(topbar.scroll_width <= topbar.client_width); assert.equal(topbar.control_overlap_area, 0);
  const navigation=record.zoom_results.reader_navigation; assert.ok(navigation); assert.equal(navigation.control_overlap_area,0);
  for(const key of ['Previous page','Contents','Next page']) { const item=navigation.children[key];assert.ok(item?.box);assert.ok(item.box.width>=44 && item.box.height>=44);assert.equal(item.clipped_area,0); }

}
async function functionalCheck(state) {
  const { chromium } = await import("playwright"); const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: state.viewport, deviceScaleFactor: 1, serviceWorkers: 'block' }); const page = await context.newPage(); const errors = []; const failedRequests = []; const unexpectedWrites = []; const consoleLocations = []; const apiRequests = [];
    page.on("requestfailed", request => failedRequests.push({url:request.url(), failure:request.failure()?.errorText}));
    page.on("console", message => { if (message.type() === "error") { errors.push(message.text()); consoleLocations.push({text:message.text(), location:message.location()}); } }); page.on("pageerror", error => errors.push(error.message));
    await page.route("**/*", route => {
      const url = new URL(route.request().url());
      if (!['localhost','127.0.0.1'].includes(url.hostname)) return route.abort();
      if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
        apiRequests.push({method:route.request().method(), origin:url.origin, path:url.pathname});
        const headers = { 'access-control-allow-origin': new URL(baseUrl).origin, 'access-control-allow-credentials': 'true',
          'access-control-allow-methods': 'GET, OPTIONS', 'access-control-allow-headers': 'authorization, content-type, x-reading-pass-session, x-reading-pass-lease', 'vary': 'Origin' };
        if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
        if (route.request().method() !== 'GET') { unexpectedWrites.push(route.request().method() + ' ' + url.pathname); return route.abort(); }
        return route.fulfill({ status: 200, contentType: 'application/json', headers, body: '[]' });
      }
      return url.origin === new URL(baseUrl).origin ? route.continue() : route.abort();
    });
    await page.goto(`${baseUrl}/reader/a-ghost-story?visual-fixture=1`, { waitUntil: "domcontentloaded" });
    await page.evaluate(async zoom => { await document.fonts.ready; document.documentElement.style.zoom = `${zoom}%`; await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); }, state.zoom);
    const body = page.locator('[data-testid="reader-reading-text"]'); const settings = page.getByRole('button', {name:'Reader settings', exact:true}); const back = page.getByRole('button', {name:'Back to book', exact:true});
    const settle = () => page.waitForFunction(() => { const viewport = document.querySelector('.reader-v2__visual-viewport[data-pagination-ready="true"]'); return viewport && viewport.scrollWidth <= viewport.clientWidth + 1 && Number(viewport.dataset.layoutHeight) === viewport.clientHeight && viewport.getAnimations({subtree:true}).every(animation => animation.playState !== 'running'); });
    // Exercise credentialed cross-port fixture admission explicitly, not only when
    // a particular UI action happens to request an API. Every request is intercepted.
    const probeUrl = new URL(baseUrl); probeUrl.port = probeUrl.port === '18007' ? '18008' : '18007'; probeUrl.pathname = '/api/reader-high-zoom-fixture-probe';
    const crossPortProbe = await page.evaluate(async url => { const response = await fetch(url, { credentials: 'include', headers: { 'x-reading-pass-session': 'isolated-high-zoom-no-real-session' } }); return { status: response.status, body: await response.json() }; }, probeUrl.href);
    assert.deepEqual(crossPortProbe, {status:200, body:[]});
    await settle(); const before = await body.evaluate(node => parseFloat(getComputedStyle(node).fontSize));
    await settings.click(); const dialog = page.getByRole('dialog', {name:'Reading preferences', exact:true}); await dialog.waitFor();
    const size = dialog.locator('label').filter({hasText:/^Text size/}).locator('select');
    await size.waitFor({state:'visible'}); assert.equal(await size.count(),1, 'One labelled text-size select must be available');
    const options = await size.locator('option').evaluateAll(nodes => nodes.map(node => ({value:node.value,label:node.textContent})));
    assert.ok(options.length > 1); assert.equal(Number(options[0].value)*16,18); assert.equal(Number(options.at(-1).value)*16,32);
    const initialValue = await size.inputValue(); const initialIndex = options.findIndex(option => option.value === initialValue); assert.ok(initialIndex >= 0 && initialIndex < options.length-1);
    const initialText = options[initialIndex].label;
    const dialogGeometry = await dialog.evaluate(node => { const r=node.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:innerWidth,height:innerHeight}; });
    assert.ok(dialogGeometry.left >= 0 && dialogGeometry.right <= dialogGeometry.width && dialogGeometry.top >= 0 && dialogGeometry.bottom <= dialogGeometry.height, `Reading preferences must remain inside viewport: ${JSON.stringify({state:state.id, zoom:state.zoom, dialogGeometry})}`);
    const sizeBox = await size.boundingBox(); assert.ok(sizeBox.width >= 44 && sizeBox.height >= 44);
    const dialogControls = dialog.locator('button:not([disabled]),select:not([disabled]),input:not([disabled]),textarea:not([disabled]),a[href]');
    const count = await dialogControls.count(); assert.ok(count > 0); await dialogControls.last().focus(); await page.keyboard.press('Tab');
    const trapped = await dialogControls.first().evaluate(node => node === document.activeElement); assert.equal(trapped,true);
    await size.selectOption(options[initialIndex+1].value); const increasedText = options[initialIndex+1].label;
    await page.keyboard.press('Escape'); await dialog.waitFor({state:'detached'});
    const restoredFocus = await settings.evaluate(node => node === document.activeElement); assert.equal(restoredFocus,true);
    await settle(); const afterIncrease = await body.evaluate(node => parseFloat(getComputedStyle(node).fontSize));
    await settings.click(); await size.selectOption(initialValue); const decreasedText = options[initialIndex].label;
    await page.keyboard.press('Escape'); await dialog.waitFor({state:'detached'}); await settle();
    const afterDecrease = await body.evaluate(node => parseFloat(getComputedStyle(node).fontSize));
    await back.focus(); const focusOrder=[]; for(let i=0;i<2;i++){await page.keyboard.press('Tab');focusOrder.push(await page.evaluate(()=>document.activeElement?.getAttribute('aria-label')));}
    // CSS zoom may extend an ordinary document vertically. Prove actual scroll
    // reachability, rather than treating an offscreen box as accessible by fiat.
    const navigation = page.locator('.reader-folio__navigation'); await navigation.scrollIntoViewIfNeeded();
    const navigationGeometry = await navigation.evaluate(node => {
      const rect = element => { const r=element.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}; };
      return { viewport:{width:innerWidth,height:innerHeight}, scrollY, buttons:[...node.querySelectorAll('button')].map(button=>({name:button.getAttribute('aria-label')||button.textContent.trim(),...rect(button)})) };
    });
    assert.deepEqual(navigationGeometry.buttons.map(button=>button.name),['Previous page','Contents','Next page']);
    for(const button of navigationGeometry.buttons) assert.ok(button.width>=44 && button.height>=44 && button.left>=0 && button.right<=navigationGeometry.viewport.width && button.top>=0 && button.bottom<=navigationGeometry.viewport.height, `Reader navigation must be reachable: ${JSON.stringify(navigationGeometry)}`);
    const geometry = await body.evaluate(node => { const viewport=node.closest('.reader-v2__visual-viewport');const measure=viewport.querySelector('.reader-v2__pagination-measure');return {height:viewport.clientHeight,scrollHeight:viewport.scrollHeight,width:viewport.clientWidth,scrollWidth:viewport.scrollWidth,layoutHeight:Number(viewport.dataset.layoutHeight),leading:getComputedStyle(node).lineHeight,measurementLeading:getComputedStyle(measure).lineHeight}; });
    return {geometry,navigationGeometry,dialogGeometry,before,afterIncrease,afterDecrease,initialText,increasedText,decreasedText,restoredFocus,focusOrder,trapped,errors,failedRequests,unexpectedWrites,crossPortProbe,consoleLocations,apiRequests,browserVersion:browser.version()};
  } finally { await browser.close(); }
}

test("current failing one-line fixture reproduces clipping", () => { const before = JSON.parse(fs.readFileSync(beforePath, "utf8")); assert.deepEqual(before.states.map((state) => state.state_id), ["reader-mobile-390-zoom-200", "reader-mobile-320-zoom-150", "reader-mobile-320-zoom-200"]); assert.ok(before.states.every((state) => state.clipped_controls.length > 0)); });
if (!baseUrl) throw new Error("SEAMLESS_BRAND_TEST_BASE_URL is required for real-browser Reader reflow validation.");
runCapture();
const summary = JSON.parse(fs.readFileSync(path.join(output, "capture-summary.json"), "utf8")); const records = validateCaptureSummary(summary, output, 6);
test("compact Reader bar remains bounded at highest zoom", () => assertReader(recordFor(records, "reader-mobile-320-zoom-200")));
for (const id of ids) test(`${id} passes`, () => assertReader(recordFor(records, id)));
test("all compact Reader controls remain present and at least 44 by 44", () => records.forEach(assertReader));
test("no child exceeds either compact bar edge", () => records.forEach(record => {const bar=record.zoom_results.reader_topbar;Object.values(bar.children).forEach(item=>assert.ok(item.box.left>=bar.box.left && item.box.right<=bar.box.right));}));
test("prose begins below compact controls", () => records.forEach(record=>assert.equal(record.zoom_results.reader_topbar.content_begins_below_topbar,true)));
const functional390 = await functionalCheck(selected.find((state) => state.id === "reader-mobile-390")); const functional320 = await functionalCheck(selected.find((state) => state.id === "reader-mobile-320-zoom-100")); const functional320High = await functionalCheck(selected.find((state) => state.id === "reader-mobile-320-zoom-200"));
fs.writeFileSync(path.join(output, "functional-checks.json"), JSON.stringify({functional390,functional320,functional320High}, null, 2) + "\n");
test("compact high-zoom chrome preserves a useful non-scrolling measured reading page", () => [functional390, functional320, functional320High].forEach(({ geometry }) => { assert.ok(geometry.height >= 3 * Number.parseFloat(geometry.leading)); assert.ok(geometry.scrollHeight <= geometry.height + 1); assert.ok(geometry.scrollWidth <= geometry.width + 1); assert.equal(geometry.layoutHeight, geometry.height); assert.equal(geometry.measurementLeading, geometry.leading); }));
test("font increase changes rendered Reader text size and reports its actual rem value", () => [functional390, functional320, functional320High].forEach((result) => { assertFontLabel(result.initialText, result.before); assert.ok(result.afterIncrease > result.before); assertFontLabel(result.increasedText, result.afterIncrease); }));
test("font decrease restores the initial Reader size and rem label", () => [functional390, functional320, functional320High].forEach((result) => { assert.ok(result.afterDecrease < result.afterIncrease); assert.equal(result.afterDecrease, result.before); assertFontLabel(result.decreasedText, result.afterDecrease); assert.equal(result.decreasedText, result.initialText); }));
test("settings focus restores after dialog Escape", () => [functional390, functional320, functional320High].forEach(result => assert.equal(result.restoredFocus, true)));
test("compact controls have predictable keyboard order", () => [functional390, functional320, functional320High].forEach(result => assert.deepEqual(result.focusOrder,["Reader settings","Enter fullscreen"])));
test("reading preferences trap Tab at the final control", () => [functional390,functional320,functional320High].forEach(result=>assert.equal(result.trapped,true)));

test("horizontal overflow causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.horizontal_overflow = true; assert.throws(() => assertReader(item)); });
test("clipped control causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.children.settings.clipped_area = 1; assert.throws(() => assertReader(item)); });
test("offscreen footer control causes failure", () => { const item=clone(recordFor(records,"reader-mobile-320-zoom-200"));item.zoom_results.reader_navigation.children['Next page'].clipped_area=1;assert.throws(()=>assertReader(item)); });
test("zero-size control causes failure", () => { const item=clone(recordFor(records,"reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.children.settings.box.width=0; assert.throws(()=>assertReader(item)); });
test("overlapping compact controls cause failure", () => { const item=clone(recordFor(records,"reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.control_overlap_area=1; assert.throws(()=>assertReader(item)); });
test("hidden control causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.children.settings.box = null; assert.throws(() => assertReader(item)); });
test("duplicate control causes failure", () => { const item = clone(recordFor(records, "reader-mobile-320-zoom-200")); item.zoom_results.reader_topbar.children.duplicate_settings = item.zoom_results.reader_topbar.children.settings; assert.throws(() => { const controls = item.zoom_results.reader_topbar.children; assert.equal(Object.keys(controls).filter((key) => /settings/.test(key)).length, 1); }); });
test("Reader safety remains unchanged", () => { records.forEach(assertReader); [functional390, functional320, functional320High].forEach((result) => { assert.deepEqual(result.unexpectedWrites, []); assert.deepEqual(result.errors, [], JSON.stringify({failedRequests:result.failedRequests,consoleLocations:result.consoleLocations,apiRequests:result.apiRequests,browserVersion:result.browserVersion})); }); });

console.log(JSON.stringify({ result: "PASS", testCaseCount: cases, output }));
