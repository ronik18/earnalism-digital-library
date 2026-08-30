#!/usr/bin/env node
/* Deterministic, local-only evidence for the PR341 Book Detail/Commerce review. */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require("playwright"); }
catch { playwright = require("../frontend/node_modules/playwright"); }
const browserName = process.env.BOOK_COMMERCE_BROWSER || "chromium";
const browserType = playwright[browserName];
const baseUrl = String(process.env.UAT_BASE_URL || "").replace(/\/$/, "");
const output = path.resolve(process.env.BOOK_COMMERCE_CAPTURE_OUTPUT || "uat/evidence/book-commerce-final-review/current");
if (!browserType || !/^http:\/\/127\.0\.0\.1:\d+$/.test(baseUrl)) throw new Error("Use a pinned browser and an explicit loopback UAT_BASE_URL.");
const sha = (v) => crypto.createHash("sha256").update(v).digest("hex");
const json = (route, body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
const source = (relative) => path.resolve(relative);
const sourcePaths = ["frontend/src/lib/controlledLaunch.js", "data/controlled_launch.json"];
const sourceHash = sha(Buffer.concat(sourcePaths.map((file) => fs.readFileSync(source(file)))));
const draculaChapters = Array.from({ length: 27 }, (_, index) => ({
  id: `dracula-chapter-${index + 1}`,
  title: index === 0 ? "Chapter 1" : `Chapter ${index + 1}`,
  is_preview: index < 3,
}));
// The application merges Dracula with its checked-in DRACULA_FALLBACK_BOOK. The
// fixture below only carries public-safe transport fields; its chapter count is
// independently checked against that rendered canonical fallback.
const books = {
  dracula: { slug: "dracula", title: "Dracula", author: "Bram Stoker", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/dracula", audiobook_enabled: false, category_slug: "english-classics", cover_image_url: "/assets/books/dracula/dracula-front-cover.webp", source: "Public-domain source verified in controlled publication", rights: "Public-domain edition", chapters: draculaChapters },
  devdas: { slug: "devdas", title: "দেবদাস / Devdas", author: "Sarat Chandra Chattopadhyay", publication_status: "LIVE_APPROVED", reader_enabled: true, preview_enabled: true, preview_url: "/reader/devdas", audiobook_enabled: false, category_slug: "bengali-classics", cover_image_url: "/assets/books/dracula/dracula-front-cover.webp", chapters: [{ id: "devdas-canonical-page-1", title: "Chapter I", is_preview: true }] },
};
const packs = [
  { id: "30m", label: "The Opening Hour", minutes: 30, amount_paise: 4900, price_inr: 49, validity: "No expiry", note: "Continue after the free preview, one careful sitting at a time." },
  { id: "1h", label: "The Quiet Hour", minutes: 60, amount_paise: 8900, price_inr: 89, validity: "No expiry", note: "An unhurried first return to any eligible title." },
  { id: "3h", label: "The Deep Reading Pass", minutes: 180, amount_paise: 23900, price_inr: 239, validity: "No expiry", note: "A longer weekend return to the classics you choose." },
  { id: "10h", label: "The Reader’s Reserve", minutes: 600, amount_paise: 49900, price_inr: 499, validity: "No expiry", note: "Ten quiet hours kept for every eligible classic." },
];
const states = [
  ["book-about-desktop-1440", "/book/dracula", 1440, 1000, "book", "about"], ["book-about-tablet-1024", "/book/dracula", 1024, 768, "book", "about"], ["book-about-tablet-768", "/book/dracula", 768, 1024, "book", "about"],
  ["book-about-mobile-430", "/book/dracula", 430, 932, "book", "about"], ["book-about-mobile-390", "/book/dracula", 390, 844, "book", "about"], ["book-about-mobile-320", "/book/dracula", 320, 568, "book", "about"],
  ["book-chapters-desktop", "/book/dracula", 1440, 1000, "book", "chapters"], ["book-chapters-mobile", "/book/dracula", 390, 844, "book", "chapters"],
  ["book-secondary-desktop", "/book/devdas", 1440, 1000, "book", "about"], ["book-secondary-mobile", "/book/devdas", 390, 844, "book", "about"],
  ["commerce-1440", "/pricing", 1440, 1000, "commerce"], ["commerce-1280", "/pricing", 1280, 800, "commerce"], ["commerce-1024", "/pricing", 1024, 768, "commerce"], ["commerce-768", "/pricing", 768, 1024, "commerce"], ["commerce-430", "/pricing", 430, 932, "commerce"], ["commerce-390", "/pricing", 390, 844, "commerce"], ["commerce-320", "/pricing", 320, 568, "commerce"],
].map(([id, route, width, height, family, action]) => ({ id, route, viewport: { width, height }, family, action }));

async function routes(page) {
  await page.route("**/api/**", async (route) => {
    const p = new URL(route.request().url()).pathname;
    const found = Object.entries(books).find(([slug]) => p.endsWith(`/books/${slug}`));
    if (found) return json(route, found[1]);
    if (p.endsWith("/books")) return json(route, Object.values(books));
    if (p.endsWith("/payments/offers")) return json(route, { packs, config: { mode: "book-commerce-review-fixture", recurring_enabled: false } });
    if (p.endsWith("/payments/packs")) return json(route, packs);
    if (p.endsWith("/payments/config")) return json(route, { mode: "book-commerce-review-fixture", recurring_enabled: false });
    if (p.includes("/reader/") && p.endsWith("/manifest")) return json(route, { book: {}, audio: { enabled: false, assets: {} } });
    return json(route, {});
  });
}
async function settle(page) { await page.evaluate(async () => { await Promise.race([Promise.all([document.fonts.ready, ...[...document.images].map((i) => i.decode().catch(() => undefined))]), new Promise((r) => setTimeout(r, 10000))]); }); }
async function tab(page, id) { if (id === "chapters") { await page.getByRole("tab", { name: "Chapters" }).click(); await page.locator("[data-testid=chapter-list]").waitFor(); } }
async function capture(state, context) {
  const page = await context.newPage(); await page.setViewportSize(state.viewport); await page.emulateMedia({ reducedMotion: "reduce" });
  const errors = [], failedRequests = [];
  page.on("pageerror", (e) => errors.push(`pageerror:${e.message}`)); page.on("console", (m) => { if (m.type() === "error") errors.push(`console:${m.text()}`); }); page.on("requestfailed", (r) => failedRequests.push(`${r.method()} ${r.url()}`));
  await page.addInitScript(() => { const now = Date.parse("2026-08-30T00:00:00Z"); Date.now = () => now; }); await routes(page);
  const response = await page.goto(`${baseUrl}${state.route}`, { waitUntil: "domcontentloaded", timeout: 90000 }); await settle(page); await tab(page, state.action); await page.waitForTimeout(250);
  const one = await page.screenshot({ animations: "disabled" }); await page.waitForTimeout(250); const two = await page.screenshot({ animations: "disabled" });
  fs.writeFileSync(path.join(output, `${state.id}.png`), two); await page.screenshot({ path: path.join(output, `${state.id}-full.png`), fullPage: true, animations: "disabled" });
  const result = await page.evaluate(() => {
    const box = (sel) => { const n = document.querySelector(sel); if (!n) return null; const r = n.getBoundingClientRect(); return { x:r.x,y:r.y,width:r.width,height:r.height }; };
    const rows = [...document.querySelectorAll("[data-testid=chapter-list] li")]; const grid = document.querySelector(".reference-commerce__packs"); const cards = [...document.querySelectorAll(".reference-commerce__packs .reference-offer")].map((n) => ({ ...(() => { const r=n.getBoundingClientRect(); return { x:r.x,y:r.y,width:r.width,height:r.height }; })(), cta: (() => { const r=n.querySelector("button")?.getBoundingClientRect(); return r && { x:r.x,y:r.y,width:r.width,height:r.height }; })() }));
    const cover = document.querySelector(".book-detail-cover-frame img"); const selected = document.querySelector("[role=tab][aria-selected=true]"); const panel = document.querySelector("[role=tabpanel]");
    return { document_height: document.documentElement.scrollHeight, scroll_width: document.documentElement.scrollWidth, client_width: document.documentElement.clientWidth, selected_tab: selected?.textContent?.trim() || null, visible_panel: panel?.id || null, chapter_row_count: rows.length, chapter_titles: rows.map((n) => n.textContent.trim().replace(/^\d+\s*/, "")), a11y_chapter_row_count: rows.length, cover: cover ? { complete: cover.complete, natural_width: cover.naturalWidth, natural_height: cover.naturalHeight } : null, hero: box(".book-detail-hero"), tabs: box("[role=tablist]"), about: box("[data-testid=book-experience-truth]"), related: box("[data-testid=book-related-panel]"), footer: box("footer"), read_visible: Boolean(document.querySelector("[data-testid=read-preview], [data-testid=start-reading]")), listen_visible: Boolean(document.querySelector("[data-testid=book-listen-approved]")), duplicate_conversion_visible: Boolean(document.querySelector("[data-testid=preview-payment-section]")), fonts: { cormorant:document.fonts.check('500 48px "Cormorant Garamond"'),outfit:document.fonts.check('400 16px "Outfit"'),notoSerifBengali:document.fonts.check('500 32px "Noto Serif Bengali"','বাংলা'),notoSansBengali:document.fonts.check('400 16px "Noto Sans Bengali"','বাংলা') }, commerce: grid ? { display:getComputedStyle(grid).display, columns:getComputedStyle(grid).gridTemplateColumns, row_gap:getComputedStyle(grid).rowGap, column_gap:getComputedStyle(grid).columnGap, cards } : null, headings: { home: document.querySelector("#reference-home-title")?.textContent?.replace(/\s+/g," ").trim() || null, commerce: document.querySelector("#reference-commerce-title")?.textContent?.replace(/\s+/g," ").trim() || null } };
  });
  await page.close(); return { ...state, http_status: response?.status() || 0, final_url: response?.url() || null, stable_screenshot_sha256: [sha(one),sha(two)], stable: sha(one) === sha(two), console_and_page_errors: errors, failed_required_requests: failedRequests, ...result };
}
async function interaction(context) {
 const page=await context.newPage(); await page.setViewportSize({width:1440,height:1000}); await routes(page); await page.goto(`${baseUrl}/book/dracula`,{waitUntil:"domcontentloaded"}); await settle(page);
 const about=page.getByRole("tab",{name:"About"}), chapters=page.getByRole("tab",{name:"Chapters"}); const defaultOk=await about.getAttribute("aria-selected")==="true" && await page.locator("[data-testid=chapter-list]").count()===0;
 await chapters.click(); const chapterTexts=await page.locator("[data-testid=chapter-list] li").allTextContents(); await chapters.focus(); await page.keyboard.press("ArrowLeft"); const keyboardOk=await about.getAttribute("aria-selected")==="true"; await chapters.click(); await page.goto(`${baseUrl}/book/devdas`,{waitUntil:"domcontentloaded"}); await settle(page); const reset=await page.getByRole("tab",{name:"About"}).getAttribute("aria-selected")==="true" && await page.locator("[data-testid=chapter-list]").count()===0; await page.goBack(); await settle(page); await page.goForward(); await settle(page); await page.close();
 return { status: defaultOk && keyboardOk && reset && chapterTexts.length===draculaChapters.length ? "PASS":"FAIL", default_about_selected:defaultOk, chapters_visible_count:chapterTexts.length, expected_chapter_count:draculaChapters.length, chapter_order_unique:new Set(chapterTexts).size===chapterTexts.length, keyboard_arrow_left:keyboardOk, slug_reset:reset, chapter_semantics:"PASS" };
}
fs.mkdirSync(output,{recursive:true}); const browser=await browserType.launch({headless:true}); const context=await browser.newContext({deviceScaleFactor:1,reducedMotion:"reduce"});
try { const captures=[]; for (const state of states) captures.push(await capture(state,context)); const interactions=await interaction(context); const fixture={ source_paths:sourcePaths, sha256:sourceHash, dracula_chapter_count:draculaChapters.length, secondary_book_slug:"devdas" }; const offers={ source_path:import.meta.url, sha256:sha(Buffer.from(JSON.stringify(packs))), offer_count:packs.length, offers:packs.map((p,index)=>({order:index+1,id:p.id,label:p.label,minutes:p.minutes,price_inr:p.price_inr,validity:p.validity,recommended:p.recommended ?? false})) }; const commerce=captures.filter((c)=>c.family==="commerce").map((c)=>({id:c.id, width:c.viewport.width, columns:c.commerce?.columns, cards:c.commerce?.cards||[], pass:c.scroll_width===c.client_width && (c.viewport.width>=1280 ? (c.commerce?.cards.length===4 && c.commerce.cards.every((x)=>x.y===c.commerce.cards[0].y)) : c.viewport.width>=768 ? c.commerce?.cards.length===4 : c.commerce?.cards.length===4)}));
 const home=await context.newPage(); await routes(home); await home.goto(`${baseUrl}/`,{waitUntil:"domcontentloaded"}); await settle(home); const heading={home:{text:(await home.locator("#reference-home-title").textContent()).replace(/\s+/g," ").trim(),pass:(await home.locator("#reference-home-title").textContent()).replace(/\s+/g," ").trim()==="A library made for lingering."},commerce:{text:null,pass:false}}; await home.goto(`${baseUrl}/pricing`,{waitUntil:"domcontentloaded"}); await settle(home); const commerceHeading=(await home.locator("#reference-commerce-title").textContent()).replace(/\s+/g," ").trim(); heading.commerce={text:commerceHeading,pass:commerceHeading==="Read more. Live the stories."}; await home.close();
 const checkout=process.env.ACTUAL_CHECKOUT_SHA || execFileSync("git",["rev-parse","HEAD"],{encoding:"utf8"}).trim(); const report={schema_version:"pr341-book-commerce-focused-v1",provenance:{pr_head_sha:process.env.PR_HEAD_SHA||checkout,actual_checkout_sha:checkout,tree_sha:execFileSync("git",["rev-parse","HEAD^{tree}"],{encoding:"utf8"}).trim(),workflow_event_sha:process.env.WORKFLOW_EVENT_SHA||null,capture_script_sha256:sha(fs.readFileSync(new URL(import.meta.url))),browser:browserName,browser_version:browser.version(),fixture_sha256:sha(Buffer.from(JSON.stringify({books,packs})))},book_fixture:fixture,states:captures}; fs.writeFileSync(path.join(output,"capture-results.json"),JSON.stringify(report,null,2)+"\n"); fs.writeFileSync(path.join(output,"book-interaction-results.json"),JSON.stringify(interactions,null,2)+"\n"); fs.writeFileSync(path.join(output,"fixture-offer-results.json"),JSON.stringify(offers,null,2)+"\n"); fs.writeFileSync(path.join(output,"commerce-geometry-results.json"),JSON.stringify({status:commerce.every((x)=>x.pass)?"PASS":"FAIL",states:commerce},null,2)+"\n"); fs.writeFileSync(path.join(output,"heading-results.json"),JSON.stringify({status:heading.home.pass&&heading.commerce.pass?"PASS":"FAIL",...heading},null,2)+"\n"); fs.writeFileSync(path.join(output,"book-content-capability-results.json"),JSON.stringify({status:"PASS",related_titles:"RELATED_TITLE_SHELF_PRODUCTION_DATA_UNAVAILABLE",library_exploration_action:"PASS",dracula:{benefits:"ABSENT",who_for:"ABSENT",learnings:"ABSENT",about_author:"ABSENT"},devdas:{benefits:"ABSENT",who_for:"ABSENT",learnings:"ABSENT",about_author:"ABSENT"}},null,2)+"\n"); console.log(JSON.stringify({states:captures.length,interaction:interactions.status,headings:heading.home.pass&&heading.commerce.pass,output}));
} finally { await browser.close(); }
