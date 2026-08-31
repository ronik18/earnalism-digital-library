#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const baseUrl = String(process.env.UAT_BASE_URL || "http://127.0.0.1:13007").replace(/\/$/, "");
process.env.UAT_BASE_URL ||= baseUrl;
const { openActualMobileMenu, assertMobileMenuGeometry, closeActualMobileMenu } = await import("./capture_exact_primary_owner_review.mjs");

const baseFixture = ({ duplicate = false, corrected = false } = {}) => `<!doctype html><style>
  body { margin:0 }
  :root { --site-header-height: 64px; }
  header { position:sticky;top:0;height:64px;${corrected ? "backdrop-filter:none" : "backdrop-filter:blur(18px)"} }
  .menu { position:fixed;top:var(--site-header-height);right:0;${corrected ? "bottom:auto;left:0;width:100%;height:calc(100dvh - var(--site-header-height));min-height:calc(100dvh - var(--site-header-height));max-height:calc(100dvh - var(--site-header-height));" : "bottom:0;left:0;"}overflow-y:auto;background:#240c14;color:#f6ead7;z-index:80 }
  .menu a { display:flex;min-height:52px;align-items:center;color:#f6ead7 } .menu button { width:44px;height:44px }
</style><header data-testid="site-header"><button data-testid="mobile-menu-toggle" aria-expanded="false" aria-controls="mobile-menu">Menu</button></header>
<main id="main-content">Main</main><footer>Footer</footer>
<header data-testid="site-header" hidden><button data-testid="mobile-menu-toggle" aria-expanded="false" aria-controls="mobile-menu">Hidden fixture</button><div id="mobile-menu" data-testid="mobile-menu" role="dialog" aria-modal="true">Hidden</div></header>
<div id="mobile-menu" data-testid="mobile-menu" role="dialog" aria-modal="true" hidden>Outside fixture</div>
<script>
 const toggle=document.querySelector('header[data-testid="site-header"] [data-testid="mobile-menu-toggle"]');
 const close=()=>{document.querySelectorAll('header[data-testid="site-header"] > [data-testid="mobile-menu"]').forEach(n=>n.remove());toggle.setAttribute('aria-expanded','false');document.body.style.overflow='';['#main-content','footer'].map(s=>document.querySelector(s)).forEach(n=>{n.removeAttribute('inert');n.removeAttribute('aria-hidden')});toggle.focus()};
 toggle.addEventListener('click',()=>{toggle.setAttribute('aria-expanded','true');document.body.style.overflow='hidden';['#main-content','footer'].map(s=>document.querySelector(s)).forEach(n=>{n.setAttribute('inert','');n.setAttribute('aria-hidden','true')});for(let i=0;i<${duplicate ? 2 : 1};i++){const menu=document.createElement('div');menu.id='mobile-menu';menu.className='menu';menu.dataset.testid='mobile-menu';menu.setAttribute('role','dialog');menu.setAttribute('aria-modal','true');menu.innerHTML='<button aria-label="Close menu">Close</button><a data-testid="mobile-nav-home">Home</a><a data-testid="mobile-nav-library">Library</a><a data-testid="mobile-nav-reading-passes">Reading Passes</a>';toggle.closest('header').append(menu);menu.querySelector('button').addEventListener('click',close);}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
</script>`;

async function installPublicFixture(page) {
  await page.route("**/api/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
}

const browser = await chromium.launch({ headless: true });
const result = { baselineContainingBlock: false, correctedFixture: false, hiddenFixturesIgnored: false, duplicateOwnerDialogRejected: false, viewports: [], desktop: [], routeAction: null };
try {
  const baseline = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await baseline.setContent(baseFixture());
  const baselineDiagnostics = await openActualMobileMenu(baseline);
  result.baselineContainingBlock = baselineDiagnostics.header.backdropFilter !== "none" && baselineDiagnostics.dialog.box.height === 0;
  assert.equal(result.baselineContainingBlock, true);
  await closeActualMobileMenu(baseline);
  await baseline.close();

  const corrected = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await corrected.setContent(baseFixture({ corrected: true }));
  const correctedDiagnostics = await openActualMobileMenu(corrected);
  assertMobileMenuGeometry(correctedDiagnostics);
  result.correctedFixture = true;
  result.hiddenFixturesIgnored = correctedDiagnostics.visibleToggleCount === 1 && correctedDiagnostics.activeVisibleOwnerDialogCount === 1;
  assert.deepEqual(await closeActualMobileMenu(corrected), { escapeClose: true, focusRestored: true, activeVisibleDialogCount: 0, bodyScrollRestored: true, backgroundRestored: true });
  await corrected.close();

  const duplicate = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await duplicate.setContent(baseFixture({ corrected: true, duplicate: true }));
  await assert.rejects(() => openActualMobileMenu(duplicate), /Owner-scoped active mobile-menu dialog selection failed/);
  result.duplicateOwnerDialogRejected = true;
  await duplicate.close();

  for (const viewport of [{ width: 320, height: 568 }, { width: 390, height: 844 }, { width: 430, height: 932 }, { width: 768, height: 1024 }, { width: 1024, height: 768 }, { width: 1279, height: 800 }]) {
    const page = await browser.newPage({ viewport });
    await installPublicFixture(page);
    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    const navigation = await openActualMobileMenu(page);
    const geometry = assertMobileMenuGeometry(navigation);
    assert.equal(navigation.header.backdropFilter, "none");
    if (viewport.width === 320) assert.equal(navigation.dialog.scrollHeight > navigation.dialog.clientHeight, true);
    const close = await closeActualMobileMenu(page);
    assert.equal(close.escapeClose && close.focusRestored && close.bodyScrollRestored && close.backgroundRestored, true);
    result.viewports.push({ viewport, dialog: navigation.dialog.box, availableHeight: geometry.availableHeight, close });
    await page.close();
  }

  const routeAction = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await installPublicFixture(routeAction);
  await routeAction.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await openActualMobileMenu(routeAction);
  await routeAction.evaluate(() => window.__earnalismOwnerReviewDialog.querySelector('[data-testid="mobile-nav-library"]').click());
  await routeAction.waitForFunction(() => location.pathname === "/library" && document.querySelector('[data-testid="mobile-menu-toggle"]')?.getAttribute("aria-expanded") === "false" && !document.querySelector('[data-testid="mobile-menu"]'));
  await routeAction.goBack({ waitUntil: "domcontentloaded" });
  result.routeAction = await routeAction.evaluate(() => ({ route: location.pathname, menuClosed: !document.querySelector('[data-testid="mobile-menu"]') }));
  assert.deepEqual(result.routeAction, { route: "/", menuClosed: true });
  await routeAction.close();

  for (const width of [1280, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await installPublicFixture(page);
    await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
    const desktop = await page.evaluate(() => ({ navVisible: (() => { const node = document.querySelector(".premium-header-nav"); const box = node?.getBoundingClientRect(); return Boolean(node && getComputedStyle(node).display !== "none" && box.width > 0); })(), mobileToggleCount: [...document.querySelectorAll('[data-testid="mobile-menu-toggle"]')].filter((node) => getComputedStyle(node).display !== "none" && node.getBoundingClientRect().width > 0).length, dialogCount: document.querySelectorAll('[data-testid="mobile-menu"]').length }));
    assert.deepEqual(desktop, { navVisible: true, mobileToggleCount: 0, dialogCount: 0 });
    result.desktop.push({ width, ...desktop });
    await page.close();
  }
  const report = { schema_version: "earnalism-mobile-menu-viewport-geometry-v1", result, pass: true };
  if (process.env.MOBILE_MENU_GEOMETRY_RESULTS_OUTPUT) {
    const reportPath = path.resolve(process.env.MOBILE_MENU_GEOMETRY_RESULTS_OUTPUT);
    fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
  }
  console.log(JSON.stringify(report));
} finally { await browser.close(); }
