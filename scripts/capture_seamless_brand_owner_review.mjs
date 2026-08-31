#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import {
  listStateRecords,
  loadStateManifest,
  selectStateRecords,
  validateStateManifest,
} from "./lib/seamless_brand_state_manifest.mjs";

const DEFAULT_MANIFEST = "docs/design-system/seamless-brand-state-manifest.json";
const DEFAULT_ROUTE_INVENTORY = "docs/design-system/seamless-brand-route-inventory.json";

function parseCliArgs(argv) {
  const options = { manifest: DEFAULT_MANIFEST, routeInventory: DEFAULT_ROUTE_INVENTORY, listStates: false, dryRun: false, stateFilter: undefined };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--manifest" || arg === "--route-inventory" || arg === "--state-filter") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error(`${arg} requires a value.`);
      if (arg === "--manifest") options.manifest = value;
      if (arg === "--route-inventory") options.routeInventory = value;
      if (arg === "--state-filter") options.stateFilter = value.split(",").map((item) => item.trim());
      index += 1;
    } else if (arg === "--list-states") {
      options.listStates = true;
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (options.listStates && options.dryRun) throw new Error("Use either --list-states or --dry-run, not both.");
  if (options.stateFilter && !options.listStates && !options.dryRun) throw new Error("--state-filter requires --list-states or --dry-run.");
  return options;
}

function digest(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function runManifestCli(options) {
  const manifestPath = path.resolve(options.manifest);
  const routeInventoryPath = path.resolve(options.routeInventory);
  const manifest = loadStateManifest(manifestPath);
  const routeInventory = JSON.parse(fs.readFileSync(routeInventoryPath, "utf8"));
  validateStateManifest(manifest, routeInventory);
  if (routeInventory.routes.length !== 19) throw new Error(`Route inventory: invalid route count; received ${routeInventory.routes.length}; expected 19.`);
  if (manifest.states.length !== 5) throw new Error(`State manifest: invalid representative state count; received ${manifest.states.length}; expected 5.`);
  const requestedIds = options.stateFilter === undefined ? undefined : options.stateFilter;
  const selected = requestedIds === undefined ? listStateRecords(manifest) : selectStateRecords(manifest, requestedIds);
  if (options.listStates) {
    for (const state of selected) {
      console.log(JSON.stringify({ id: state.id, route: state.route, viewport: state.viewport, zoom: state.zoom, fixture: state.fixture, interaction: state.interaction, capture: state.capture }));
    }
    return;
  }
  const captureTypeCounts = {};
  for (const state of selected) {
    for (const [captureType, enabled] of Object.entries(state.capture)) {
      if (enabled) captureTypeCounts[captureType] = (captureTypeCounts[captureType] || 0) + 1;
    }
  }
  console.log(JSON.stringify({
    schema_version: manifest.schema_version,
    total_states: manifest.states.length,
    selected_states: selected.map((state) => state.id),
    unique_routes: [...new Set(selected.map((state) => state.route))],
    fixtures: [...new Set(selected.map((state) => state.fixture))],
    interactions: [...new Set(selected.map((state) => state.interaction))],
    capture_type_counts: captureTypeCounts,
    manifest_sha256: digest(manifestPath),
    route_inventory_sha256: digest(routeInventoryPath),
  }));
}

const cli = parseCliArgs(process.argv.slice(2));
if (cli.listStates || cli.dryRun) {
  runManifestCli(cli);
  process.exit(0);
}

const base = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const out = path.resolve(process.env.SEAMLESS_BRAND_CAPTURE_OUTPUT || "uat/evidence/seamless-brand-pilot/current");
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw new Error("UAT_BASE_URL must be loopback.");
fs.mkdirSync(path.join(out, "screenshots"), { recursive: true });
const states = [
  ["home-desktop", "/", 1440, 1000, 100], ["home-mobile", "/", 390, 844, 100], ["home-mobile-zoom-200", "/", 390, 844, 200],
  ["reader-mobile-390", "/reader/dracula?visual-fixture=1", 390, 844, 100], ["reader-mobile-320", "/reader/dracula?visual-fixture=1", 320, 568, 100],
  ["listener-mobile-390", "/listener/a-ghost-story?visual-fixture=1", 390, 844, 100], ["listener-mobile-320", "/listener/a-ghost-story?visual-fixture=1", 320, 568, 100],
  ["account-mobile", "/account?visual-fixture=1", 390, 844, 100], ["library-footer-mobile", "/library", 390, 844, 100],
];
const books = [{slug:"dracula",title:"Dracula",author:"Bram Stoker",publication_status:"LIVE_APPROVED",reader_enabled:true,preview_enabled:true,chapters:[{id:"p1",is_preview:true}]},{slug:"a-ghost-story",title:"A Ghost Story",author:"Mark Twain",publication_status:"LIVE_APPROVED",reader_enabled:true,audiobook_enabled:false,preview_enabled:true,chapters:[{id:"p1",is_preview:true}]}];
if (process.env.SEAMLESS_BRAND_BROWSER_IMPORT_SENTINEL === "1") throw new Error("Browser import sentinel reached outside the manifest CLI.");
const { chromium } = await import("playwright");
const browser = await chromium.launch({ headless: true }); const version = browser.version(); const results=[];
for (const [id, route, width, height, zoom] of states) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 }); const errors=[];
  page.on("console", m => { if (m.type()==="error") errors.push(m.text()); }); page.on("pageerror", e => errors.push(e.message));
  await page.route("**/api/**", r => { const u=new URL(r.request().url()); const body=u.pathname.endsWith("/books")?books:u.pathname.includes("auth")?{id:"fixture",email:"fixture@invalid.example"}:[]; r.fulfill({status:200,contentType:"application/json",body:JSON.stringify(body)}); });
  await page.goto(base+route,{waitUntil:"networkidle"}); await page.evaluate(async z=>{ document.documentElement.style.zoom=`${z}%`; await document.fonts.ready; },zoom); await page.emulateMedia({ reducedMotion:"reduce" });
  const file=path.join(out,"screenshots",`${id}.png`); await page.screenshot({path:file,fullPage:id==="library-footer-mobile",animations:"disabled"});
  const data=await page.evaluate(()=>{const lock=[...document.querySelectorAll('[data-testid="earnalism-brand-lockup"]')].filter(n=>{const s=getComputedStyle(n),r=n.getBoundingClientRect();return s.display!=="none"&&r.width>0&&r.height>0}); const l=lock[0], img=l?.querySelector("img"), r=l?.getBoundingClientRect(), s=l&&getComputedStyle(l); const header=document.querySelector(".experience-header")||document.querySelector('[data-testid="site-header"]'); return {scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,headerVisible:!!header&&getComputedStyle(header).display!=="none",lockupCount:lock.length,logo:l?{width:r.width,height:r.height,naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight,aspectRatio:r.width/r.height,transform:getComputedStyle(img).transform,clipped:r.left<0||r.right>innerWidth,wrapper:{background:s.backgroundColor,border:s.borderWidth,radius:s.borderRadius,shadow:s.boxShadow}}:null,footer:!!document.querySelector('[data-testid="footer-brand-paper-row"]')}; });
  results.push({id,route,viewport:{width,height},zoom,browser:"chromium",browserVersion:version,screenshot:path.relative(out,file),screenshotSha256:digest(file),consoleErrors:errors,overflow:data.scrollWidth>data.clientWidth,...data}); await page.close();
}
await browser.close(); fs.writeFileSync(path.join(out,"capture-results.json"),JSON.stringify({states:results,expected:states.map(s=>s[0])},null,2)+"\n"); console.log(JSON.stringify({captured:results.length,out}));
